"""
Fetches the real following list from your destination X account,
compares it against members.json, and prints a full report.

Usage:
  python report.py
"""

import asyncio
import json
from playwright.async_api import async_playwright

following_names = set()


async def intercept_following(response):
    if response.status != 200:
        return
    if "Following" not in response.url and "following" not in response.url:
        return
    try:
        data = await response.json()
        instructions = (
            data.get("data", {})
                .get("user", {})
                .get("result", {})
                .get("timeline", {})
                .get("timeline", {})
                .get("instructions", [])
        )
        for instruction in instructions:
            if instruction.get("type") != "TimelineAddEntries":
                continue
            for entry in instruction.get("entries", []):
                core = (
                    entry.get("content", {})
                         .get("itemContent", {})
                         .get("user_results", {})
                         .get("result", {})
                         .get("core", {})
                )
                screen_name = core.get("screen_name")
                if screen_name:
                    following_names.add(screen_name.lower())
    except Exception:
        pass


async def main():
    try:
        with open("data/members.json") as f:
            members = json.load(f)
    except FileNotFoundError:
        print("ERROR: data/members.json not found. Run extract_members.py first.")
        return

    async with async_playwright() as p:
        context = await p.chromium.launch_persistent_context(
            user_data_dir="./profile_dest",
            headless=False,
            channel="chrome",
            args=["--disable-blink-features=AutomationControlled"],
        )
        page = await context.new_page()
        page.on("response", intercept_following)

        await page.goto("https://x.com/home")

        print("=" * 60)
        print("Log into your destination account if needed, then press Enter.")
        print("=" * 60)
        input("\n>>> Press Enter when ready: ")

        # Auto-detect logged-in username
        try:
            href = await page.locator('a[data-testid="AppTabBar_Profile_Link"]').get_attribute("href")
            dest_username = href.strip("/")
            print(f"\nDetected account: @{dest_username}")
        except Exception:
            dest_username = input("Could not detect username. Enter it manually: ").strip("@")

        await page.goto(f"https://x.com/{dest_username}/following", wait_until="domcontentloaded")
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

        await context.close()

    # Compare
    all_usernames = [m["username"] for m in members]
    following      = [u for u in all_usernames if u.lower() in following_names]
    not_following  = [u for u in all_usernames if u.lower() not in following_names]

    print(f"\n{'=' * 60}")
    print(f"  Source list members : {len(all_usernames)}")
    print(f"  Following on X      : {len(following)}")
    print(f"  Not yet following   : {len(not_following)}")
    print(f"{'=' * 60}\n")

    if not_following:
        print(f"Not yet following ({len(not_following)}):")
        for u in not_following:
            print(f"  @{u}")


asyncio.run(main())
