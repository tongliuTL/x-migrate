"""
Script 2 (alt): Follow all extracted members from the destination X account.

Before running:
  1. Run extract_members.py first to produce members.json

Rate limit warning:
  X typically allows ~400 follows/day. The script detects rate limiting
  and pauses automatically. Progress is saved per-user so re-runs safely
  skip everyone already processed.

Run report.py after all members are done for a full comparison.
"""

import asyncio
import json
import math
import random
from playwright.async_api import async_playwright

# Max follows per session. Keep low for new accounts to avoid throttling.
# Increase gradually over days as the account ages and X trusts it more.
DAILY_LIMIT = 20


def classify_buttons(button_texts: list[str]) -> str:
    """Classify the follow state from all visible button texts on the page."""
    normalized = [t.strip().lower() for t in button_texts]
    if any(t in ("following", "unfollow") for t in normalized):
        return "already_following"
    if "requested" in normalized:
        return "requested"
    if "follow" in normalized:
        return "can_follow"
    return "no_button"


async def get_button_texts(page) -> list[str]:
    return await page.evaluate("""
        () => Array.from(document.querySelectorAll('button'))
                   .map(b => b.innerText.trim())
                   .filter(t => t.length > 0)
    """)


async def page_signals_unavailable(page) -> bool:
    try:
        body = await page.inner_text("body", timeout=3000)
        body_l = body.lower()
        return any(s in body_l for s in [
            "account suspended",
            "this account doesn't exist",
            "caution: this account",
            "account is temporarily unavailable",
        ])
    except Exception:
        return False


async def follow_user(page, username: str) -> str:
    """
    Returns one of:
      'followed'          – successfully followed
      'already_following' – was already following
      'requested'         – follow request sent (protected account)
      'unavailable'       – account suspended / deleted (permanent, don't retry)
      'rate_limited'      – X rejected the follow action (stop session, retry later)
      'error'             – any other problem (retry next run)
    """
    try:
        await page.goto(
            f"https://x.com/{username}",
            wait_until="domcontentloaded",
            timeout=25000,
        )
        await asyncio.sleep(random.uniform(2.0, 3.0))

        if await page_signals_unavailable(page):
            return "unavailable"

        # Read button state; wait up to ~6s for JS to render
        state = "no_button"
        for _ in range(3):
            btns = await get_button_texts(page)
            state = classify_buttons(btns)
            if state != "no_button":
                break
            await asyncio.sleep(2.0)

        if state == "already_following":
            return "already_following"

        if state == "no_button":
            # No follow button after waiting → account unavailable or protected with no button
            return "unavailable"

        # Click Follow via JS (avoids Playwright selector fragility)
        clicked = await page.evaluate("""
            () => {
                const btn = Array.from(document.querySelectorAll('button'))
                    .find(b => b.innerText.trim().toLowerCase() === 'follow');
                if (btn) { btn.click(); return true; }
                return false;
            }
        """)

        if not clicked:
            return "error"

        # Wait and verify the state changed
        await asyncio.sleep(2.5)
        btns_after = await get_button_texts(page)
        state_after = classify_buttons(btns_after)

        if state_after == "already_following":
            return "followed"
        if state_after == "requested":
            return "requested"

        # One more wait in case of slow render
        await asyncio.sleep(2.0)
        state_final = classify_buttons(await get_button_texts(page))
        if state_final == "already_following":
            return "followed"
        if state_final == "requested":
            return "requested"

        # Button still shows "Follow" after clicking → X silently rejected = rate limit
        if state_final == "can_follow":
            return "rate_limited"

        return "error"

    except Exception as e:
        print(f"\n  EXCEPTION: {str(e)[:120]}", end="")
        try:
            await page.keyboard.press("Escape")
        except Exception:
            pass
        return "error"


def human_delay() -> float:
    """
    Return a randomized delay (seconds) that mimics human browsing behaviour:
    - Most of the time: 5-15s (reading the profile briefly)
    - Occasionally: 20-45s (distracted, reading bio/tweets)
    - Rarely: 60-120s (stepped away for a moment)
    Uses a weighted choice so the distribution is uneven, not a flat range.
    """
    roll = random.random()
    if roll < 0.65:
        # Normal pace — 5 to 15s with slight gaussian shape
        return random.gauss(9, 2.5)
    elif roll < 0.88:
        # Slower — 20 to 45s
        return random.uniform(20, 45)
    elif roll < 0.97:
        # Distracted — 45 to 90s
        return random.uniform(45, 90)
    else:
        # Long pause — 90 to 180s
        return random.uniform(90, 180)


def load_progress() -> dict:
    """
    Progress is stored as {username: status} so each user has an explicit record.
    Statuses that are final (won't be retried): followed, already_following,
    requested, unavailable.
    """
    try:
        with open("data/follow_progress.json") as f:
            return json.load(f)
    except FileNotFoundError:
        return {}


def save_progress(progress: dict):
    with open("data/follow_progress.json", "w") as f:
        json.dump(progress, f, indent=2)


FINAL_STATUSES = {"followed", "already_following", "requested", "unavailable"}


def print_summary(progress: dict, members: list):
    all_usernames = {m["username"] for m in members}
    counts = {}
    for status in [*FINAL_STATUSES, "error", "rate_limited"]:
        counts[status] = sum(1 for s in progress.values() if s == status)
    pending = len(all_usernames - set(progress.keys()))

    print(f"\n{'=' * 60}")
    print(f"  followed          : {counts.get('followed', 0)}")
    print(f"  already following : {counts.get('already_following', 0)}")
    print(f"  requested         : {counts.get('requested', 0)}")
    print(f"  unavailable       : {counts.get('unavailable', 0)}")
    print(f"  error (retry)     : {counts.get('error', 0)}")
    print(f"  rate limited      : {counts.get('rate_limited', 0)}")
    print(f"  not yet processed : {pending}")
    print(f"{'=' * 60}")


async def main():
    try:
        with open("data/members.json") as f:
            members = json.load(f)
    except FileNotFoundError:
        print("ERROR: data/members.json not found. Run extract_members.py first.")
        return

    progress = load_progress()

    already_done = sum(1 for s in progress.values() if s in FINAL_STATUSES)
    if already_done:
        print(f"Resuming — {already_done} members already processed (skipping them).")

    # Only process members not yet in a final state
    remaining = [m for m in members if progress.get(m["username"]) not in FINAL_STATUSES]

    async with async_playwright() as p:
        context = await p.chromium.launch_persistent_context(
            user_data_dir="./profile_dest",
            headless=False,
            channel="chrome",
            args=["--disable-blink-features=AutomationControlled"],
        )
        page = await context.new_page()

        await page.goto("https://x.com/home")

        print("=" * 60)
        print("A browser window has opened.")
        print("1. Log into your DESTINATION X account if not already.")
        print("   (Next time you run this, login will be saved.)")
        print("2. Come back here and press Enter to start following.")
        print("=" * 60)
        input("\n>>> Press Enter when ready: ")
        await asyncio.sleep(2)

        total = len(remaining)
        followed_this_run = 0

        print(f"\nProcessing {total} members (session limit: {DAILY_LIMIT} follows)...")
        print("Do not interact with the browser while this runs.\n")

        for i, member in enumerate(remaining):
            username = member["username"]
            print(f"[{i + 1}/{total}] @{username} ... ", end="", flush=True)

            result = await follow_user(page, username)
            progress[username] = result
            save_progress(progress)

            if result == "followed":
                followed_this_run += 1
                consecutive_rate_limits = 0
                print("followed")
            elif result == "already_following":
                consecutive_rate_limits = 0
                print("already following")
            elif result == "requested":
                followed_this_run += 1
                consecutive_rate_limits = 0
                print("requested (protected account)")
            elif result == "unavailable":
                consecutive_rate_limits = 0
                print("unavailable (suspended or deleted)")
            elif result == "rate_limited":
                print("RATE LIMITED")
                print("\n  X has throttled this account. Stopping now to protect it.")
                print("  Re-run tomorrow. All progress is saved.\n")
                break
            else:
                consecutive_rate_limits = 0
                print("error (will retry next run)")

            # Hit daily limit — stop cleanly
            if followed_this_run >= DAILY_LIMIT:
                print(f"\n  [Daily limit of {DAILY_LIMIT} follows reached. Stopping for today.]")
                print("  Re-run tomorrow. All progress is saved.\n")
                break

            delay = max(3.0, human_delay())
            await asyncio.sleep(delay)

        print_summary(progress, members)
        await context.close()


asyncio.run(main())
