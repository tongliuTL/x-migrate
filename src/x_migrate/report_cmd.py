"""Report module for x-migrate.

Shows migration progress from the local progress store. Optionally
scrapes the destination account's following list for online verification.
"""

import asyncio

from x_migrate import browser, config as cfg, progress as progress_store
from x_migrate.extract import parse_following_from_response


def _print_local_report(data: dict) -> None:
    """Print a report based on local progress data only."""
    total = len(data)
    counts = progress_store.summary(data)
    pending = counts.get("pending", 0)
    followed = counts.get("followed", 0)
    already = counts.get("already_following", 0)
    requested = counts.get("requested", 0)
    unavailable = counts.get("unavailable", 0)
    rate_limited = counts.get("rate_limited", 0)
    error = counts.get("error", 0)
    added_to_list = counts.get("added_to_list", 0)

    done = followed + already + requested + added_to_list

    print(f"\n{'=' * 60}")
    print(f"  Total members       : {total}")
    print(f"  Done                : {done}")
    print(f"    Followed          : {followed}")
    print(f"    Already following : {already}")
    print(f"    Requested         : {requested}")
    if added_to_list:
        print(f"    Added to list     : {added_to_list}")
    print(f"  Pending             : {pending}")
    if rate_limited:
        print(f"  Rate limited        : {rate_limited}")
    if unavailable:
        print(f"  Unavailable         : {unavailable}")
    if error:
        print(f"  Errors (will retry) : {error}")
    print(f"{'=' * 60}")

    pct = (done / total * 100) if total else 0
    print(f"  Progress: {done}/{total} ({pct:.1f}%)\n")


async def run_report(verify: bool = False) -> None:
    """Run the report workflow.

    By default, uses the local progress file. With --verify, launches
    a browser to scrape the destination following list for comparison.
    """
    config = cfg.load()
    active_job = config.get("active_job", "")

    if not active_job:
        print("No extraction found. Run 'x-migrate extract' first.")
        raise SystemExit(1)

    data = progress_store.load(active_job)

    if not data:
        print("No progress data found for active job.")
        raise SystemExit(1)

    if not verify:
        _print_local_report(data)
        print("  Tip: run 'xm report --verify' to cross-check against your live following list.\n")
        return

    # Online verification mode
    dest_profile = config.get("dest_profile", "")
    all_usernames = list(data.keys())

    pw, ctx = await browser.launch_context(dest_profile)
    page = await ctx.new_page()

    following_names: set[str] = set()

    async def handle_response(response):
        try:
            if response.status != 200:
                return
            if "Following" not in response.url and "following" not in response.url:
                return
            resp_data = await response.json()
            new_entries = parse_following_from_response(resp_data)
            for username in new_entries:
                following_names.add(username.lower())
        except Exception:
            pass

    page.on("response", handle_response)

    try:
        await page.goto("https://x.com/home")

        print("=" * 60)
        print("Log into your destination account if needed, then press Enter.")
        print("=" * 60)
        input("\n>>> Press Enter when ready: ")

        try:
            href = await page.locator('a[data-testid="AppTabBar_Profile_Link"]').get_attribute("href", timeout=5000)
            handle = href.rstrip("/").rsplit("/", 1)[-1]
            print(f"\nDetected account: @{handle}")
        except Exception:
            handle = input("Could not detect username. Enter it manually: ").strip("@")

        await page.goto(f"https://x.com/{handle}/following", wait_until="domcontentloaded")
        await asyncio.sleep(3)

        print("Scrolling following list...")
        stall = 0
        last = 0
        while stall < 8:
            await page.mouse.wheel(0, 1500)
            await asyncio.sleep(2.5)
            if len(following_names) == last:
                stall += 1
            else:
                stall = 0
                print(f"  {len(following_names)} followings loaded...")
            last = len(following_names)

    finally:
        await ctx.close()
        await pw.stop()

    following, not_following = [], []
    for u in all_usernames:
        (following if u.lower() in following_names else not_following).append(u)

    print(f"\n{'=' * 60}")
    print(f"  Source list members : {len(all_usernames)}")
    print(f"  Following on X      : {len(following)}")
    print(f"  Not yet following   : {len(not_following)}")
    print(f"{'=' * 60}\n")

    if not_following:
        print(f"Not yet following ({len(not_following)}):")
        for u in not_following:
            print(f"  @{u}")
