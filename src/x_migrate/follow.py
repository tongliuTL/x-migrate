"""Follow module for x-migrate.

Follows pending members from a job's progress store using the destination
X account opened in a Playwright browser session.
"""

import asyncio
import random
import re

from x_migrate import browser, config, progress as progress_store, ui
from x_migrate.progress import FINAL_STATUSES
from rich.live import Live


def parse_backoff(value: str) -> int:
    """Parse a backoff string like '2h', '90m', '3600s', or '0' into seconds."""
    value = value.strip().lower()
    if value in ("0", ""):
        return 0
    m = re.fullmatch(r"(\d+(?:\.\d+)?)(h|m|s)?", value)
    if not m:
        raise ValueError(f"Cannot parse backoff duration: {value!r}. Use e.g. 2h, 90m, 3600s.")
    amount, unit = float(m.group(1)), m.group(2) or "s"
    multipliers = {"h": 3600, "m": 60, "s": 1}
    return int(amount * multipliers[unit])


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

        if state == "requested":
            return "requested"

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


async def run_follow(limit: int = 20, dry_run: bool = False, auto: bool = False, backoff: str = "0") -> None:
    """Main runner for the follow workflow."""
    backoff_secs = parse_backoff(backoff)

    cfg = config.load()
    active_job = cfg.get("active_job", "")
    dest_profile = cfg.get("dest_profile", "")

    if not active_job:
        print("No extraction found. Run 'x-migrate extract' first.")
        raise SystemExit(1)

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

    pw, ctx = await browser.launch_context(dest_profile)
    page = await ctx.new_page()

    try:
        await page.goto("https://x.com/home")

        if not auto:
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
            handle = href.rstrip("/").rsplit("/", 1)[-1]
        except Exception:
            if auto:
                print("Could not detect logged-in handle. Run once without --auto to log in first.")
                raise SystemExit(1)
            handle = input("Could not detect handle. Enter your dest account @handle: ").strip("@")

        if not auto:
            confirm = input(f"Confirm: following as @{handle}? [y/N] ").strip().lower()
            if confirm != "y":
                print("Aborted.")
                return
        else:
            ui.console.print(f"  Auto mode — following as [bold]@{handle}[/bold]")

        session = 0
        remaining = limit
        while True:
            data = progress_store.load(active_job)
            pending = progress_store.pending(data)
            if not pending or remaining <= 0:
                break

            to_process = pending[:remaining]
            total = len(to_process)
            session += 1

            if backoff_secs and session > 1:
                ui.console.print(f"\n  [dim]Session {session} — {total} remaining (cap: {remaining})[/dim]")
            else:
                print(f"\nProcessing {total} members (session limit: {limit} follows)...")
                print("Do not interact with the browser while this runs.\n")

            progress = ui.make_progress()
            task_id = progress.add_task("Following...", total=total)
            hit_rate_limit = False

            with Live(progress, console=ui.console, refresh_per_second=4):
                for username in to_process:
                    progress.update(task_id, description=f"@{username}")

                    result = await follow_user(page, username)
                    data[username]["status"] = result
                    progress_store.save(active_job, data)

                    progress.update(task_id, advance=1)
                    ui.console.print(f"  @{username}: {ui.status_style(result)}")

                    if result == "rate_limited":
                        hit_rate_limit = True
                        break

                    remaining -= 1
                    delay = human_delay()
                    await asyncio.sleep(delay)

            if hit_rate_limit:
                if backoff_secs:
                    jitter_cap = min(300, backoff_secs // 4)
                    jitter = random.randint(-jitter_cap, jitter_cap)
                    sleep_secs = max(1, backoff_secs + jitter)
                    resume_in = f"{sleep_secs // 60}m {sleep_secs % 60}s"
                    ui.console.print(f"\n  [bold yellow]Rate limited. Sleeping {resume_in} then resuming automatically.[/bold yellow]")
                    ui.console.print("  Progress is saved. Safe to Ctrl-C if you want to stop.\n")
                    await asyncio.sleep(sleep_secs)
                    await page.goto("https://x.com/home")
                    await asyncio.sleep(3)
                    continue
                else:
                    ui.console.print("\n  [bold red]X has throttled this account. Stopping now to protect it.[/bold red]")
                    ui.console.print("  Re-run tomorrow (or use --backoff 2h to resume automatically). Progress is saved.\n")
                    break
            else:
                break

        ui.print_summary(data, "Follow Session")

    finally:
        await ctx.close()
        await pw.stop()
