"""Report module for x-migrate.

Fetches the destination account's following list, compares against
the members in the active job's progress store, and prints a report.
"""

import asyncio

from x_migrate import browser, config as cfg, progress as progress_store
from x_migrate.extract import parse_following_from_response


async def run_report() -> None:
    """Run the report workflow.

    Steps:
    1. Load config, get active_job
    2. Load progress to get the members list (keys of the progress dict)
    3. Launch browser (dest profile)
    4. Navigate to x.com/home, prompt for login + Enter
    5. Auto-detect @handle from profile link
    6. Navigate to x.com/{handle}/following
    7. Set up intercept handler using parse_following_from_response() from extract.py
    8. Scroll loop (stall count = 8)
    9. Close browser
    10. Compare: members in progress vs following_names collected
    11. Print report
    """
    config = cfg.load()
    active_job = config.get("active_job", "")
    dest_profile = config.get("dest_profile", "")

    if not active_job:
        print("No extraction found. Run 'x-migrate extract' first.")
        raise SystemExit(1)

    data = progress_store.load(active_job)
    all_usernames = list(data.keys())

    # Launch browser
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

        # Auto-detect logged-in handle
        try:
            href = await page.locator('a[data-testid="AppTabBar_Profile_Link"]').get_attribute("href", timeout=5000)
            handle = href.strip("/")
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

    # Compare
    following = [u for u in all_usernames if u.lower() in following_names]
    not_following = [u for u in all_usernames if u.lower() not in following_names]

    print(f"\n{'=' * 60}")
    print(f"  Source list members : {len(all_usernames)}")
    print(f"  Following on X      : {len(following)}")
    print(f"  Not yet following   : {len(not_following)}")
    print(f"{'=' * 60}\n")

    if not_following:
        print(f"Not yet following ({len(not_following)}):")
        for u in not_following:
            print(f"  @{u}")
