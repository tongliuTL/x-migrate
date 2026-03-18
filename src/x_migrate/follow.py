"""Follow module for x-migrate.

Follows pending members from a job's progress store using the destination
X account opened in a Playwright browser session.
"""

import asyncio
import random

from x_migrate import browser, config, progress as progress_store

FINAL_STATUSES = {"followed", "already_following", "requested", "unavailable"}


def classify_buttons(button_texts: list[str]) -> str:
    """Classify follow state from visible button texts."""
    normalized = [t.strip().lower() for t in button_texts]
    if any(t in ("following", "unfollow") for t in normalized):
        return "already_following"
    if "requested" in normalized:
        return "requested"
    if "follow" in normalized:
        return "can_follow"
    return "no_button"


def human_delay() -> float:
    """Return a randomized delay (seconds) mimicking human browsing behaviour.

    Always returns at least 3.0 seconds (guards against negative gauss samples).
    """
    roll = random.random()
    if roll < 0.65:
        raw = random.gauss(9, 2.5)
    elif roll < 0.88:
        raw = random.uniform(20, 45)
    elif roll < 0.97:
        raw = random.uniform(45, 90)
    else:
        raw = random.uniform(90, 180)
    return max(3.0, raw)


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


async def run_follow(limit: int = 20, dry_run: bool = False) -> None:
    """Main runner for the follow workflow.

    Steps:
    1. Load config, get active_job
    2. Load progress from progress store
    3. Get pending list — if empty, print "All members already processed!" and return
    4. If dry_run: print plan (list of @usernames to follow, up to limit), return
    5. Launch browser (dest profile)
    6. Navigate to x.com/home
    7. Prompt for login if needed, then Enter
    8. Detect @handle from profile link, ask user to confirm
    9. Process pending members up to limit
    10. On rate_limited: stop, print message, save progress
    11. Print summary, close browser
    """
    cfg = config.load()
    active_job = cfg.get("active_job", "")
    dest_profile = cfg.get("dest_profile", "")

    data = progress_store.load(active_job)
    pending = progress_store.pending(data)

    if not pending:
        print("All members already processed!")
        return

    if dry_run:
        to_follow = pending[:limit]
        print(f"Dry run — would follow {len(to_follow)} accounts (limit={limit}):")
        for username in to_follow:
            print(f"  @{username}")
        return

    # Launch browser
    pw, ctx = await browser.launch_context(dest_profile)
    page = await ctx.new_page()

    try:
        await page.goto("https://x.com/home")

        print("=" * 60)
        print("A browser window has opened.")
        print("1. Log into your DESTINATION X account if not already.")
        print("   (Next time you run this, login will be saved.)")
        print("2. Come back here and press Enter to start following.")
        print("=" * 60)
        input("\n>>> Press Enter when ready: ")
        await asyncio.sleep(2)

        # Detect logged-in handle
        try:
            href = await page.locator('a[data-testid="AppTabBar_Profile_Link"]').get_attribute("href", timeout=5000)
            handle = href.strip("/")
        except Exception:
            handle = input("Could not detect handle. Enter your dest account @handle: ").strip("@")

        confirm = input(f"Confirm: following as @{handle}? [y/N] ").strip().lower()
        if confirm != "y":
            print("Aborted.")
            return

        to_process = pending[:limit]
        total = len(to_process)
        followed_this_run = 0

        print(f"\nProcessing {total} members (session limit: {limit} follows)...")
        print("Do not interact with the browser while this runs.\n")

        for i, username in enumerate(to_process):
            print(f"[{i + 1}/{total}] @{username} ... ", end="", flush=True)

            result = await follow_user(page, username)
            data[username]["status"] = result
            progress_store.save(active_job, data)

            if result == "followed":
                followed_this_run += 1
                print("followed")
            elif result == "already_following":
                print("already following")
            elif result == "requested":
                followed_this_run += 1
                print("requested (protected account)")
            elif result == "unavailable":
                print("unavailable (suspended or deleted)")
            elif result == "rate_limited":
                print("RATE LIMITED")
                print("\n  X has throttled this account. Stopping now to protect it.")
                print("  Re-run tomorrow. All progress is saved.\n")
                break
            else:
                print("error (will retry next run)")

            if followed_this_run >= limit:
                print(f"\n  [Session limit of {limit} follows reached. Stopping for today.]")
                print("  Re-run tomorrow. All progress is saved.\n")
                break

            delay = human_delay()
            await asyncio.sleep(delay)

        # Print summary
        counts = progress_store.summary(data)
        remaining_pending = len(progress_store.pending(data))
        print(f"\n{'=' * 60}")
        print(f"  followed          : {counts.get('followed', 0)}")
        print(f"  already following : {counts.get('already_following', 0)}")
        print(f"  requested         : {counts.get('requested', 0)}")
        print(f"  unavailable       : {counts.get('unavailable', 0)}")
        print(f"  error (retry)     : {counts.get('error', 0)}")
        print(f"  not yet processed : {remaining_pending}")
        print(f"{'=' * 60}")

    finally:
        await ctx.close()
        await pw.stop()
