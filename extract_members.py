"""
Script 1: Extract all members from a private X list.
Run this while logged into your SOURCE account.
Saves results to members.json.
"""

import asyncio
import json
from playwright.async_api import async_playwright

LIST_URL = "https://x.com/i/lists/1483829129921323008/members"

members = {}


def parse_members_from_response(data):
    """Parse list members from X GraphQL response.
    Structure: data.list.members_timeline.timeline.instructions[]
                 .entries[].content.itemContent.user_results.result
                   .core.screen_name / .core.name / .rest_id
    """
    instructions = (
        data.get("data", {})
            .get("list", {})
            .get("members_timeline", {})
            .get("timeline", {})
            .get("instructions", [])
    )
    for instruction in instructions:
        if instruction.get("type") != "TimelineAddEntries":
            continue
        for entry in instruction.get("entries", []):
            item = entry.get("content", {}).get("itemContent", {})
            if item.get("itemType") != "TimelineUser":
                continue
            result = item.get("user_results", {}).get("result", {})
            core = result.get("core", {})
            screen_name = core.get("screen_name")
            if screen_name:
                members[screen_name] = {
                    "username": screen_name,
                    "name": core.get("name", ""),
                    "id": result.get("rest_id", ""),
                }


async def intercept_members(response):
    if response.status != 200:
        return
    if "ListMembers" not in response.url:
        return
    try:
        data = await response.json()
        before = len(members)
        parse_members_from_response(data)
        added = len(members) - before
        print(f"  [ListMembers: +{added} users, total: {len(members)}]")
    except Exception as e:
        print(f"  [parse error: {e}]")


async def main():
    async with async_playwright() as p:
        # Use real Chrome with a persistent profile so X doesn't flag as bot.
        # Login session is saved in ./profile_source — no need to log in again on reruns.
        context = await p.chromium.launch_persistent_context(
            user_data_dir="./profile_source",
            headless=False,
            channel="chrome",
            args=["--disable-blink-features=AutomationControlled"],
        )
        page = await context.new_page()
        page.on("response", intercept_members)

        await page.goto(LIST_URL)

        print("=" * 60)
        print("A browser window has opened.")
        print("1. Log into your SOURCE X account if not already logged in.")
        print("   (Next time you run this, login will already be saved.)")
        print("2. Make sure you can see the list members page.")
        print("3. Come back here and press Enter to start scrolling.")
        print("=" * 60)
        input("\n>>> Press Enter when ready: ")

        # Re-navigate to list URL in case login redirected to home feed
        print("\nNavigating to list members page...")
        await page.goto(LIST_URL, wait_until="domcontentloaded")
        await asyncio.sleep(3)

        print("Scrolling to load all members — please don't interact with the browser...")
        print("(You should see [net] lines below as members load)\n")
        stall_count = 0
        last_count = 0

        while stall_count < 15:
            # Use mouse wheel only — no click (clicking navigates to a profile)
            await page.mouse.wheel(0, 1500)
            await asyncio.sleep(0.5)
            await page.mouse.wheel(0, 1500)
            await asyncio.sleep(3.5)

            if len(members) == last_count:
                stall_count += 1
                if stall_count % 3 == 0:
                    print(f"  (no new members for {stall_count} cycles, still waiting...)")
            else:
                stall_count = 0
                print(f"  Found {len(members)} members so far...")
            last_count = len(members)

        print(f"\nDone scrolling. Total members found: {len(members)}")

        if not members:
            print("\nWARNING: No members were captured.")
            print("The page may not have loaded correctly, or the list interceptor")
            print("URL pattern may have changed. Try scrolling manually in the browser")
            print("and re-running the script.")
        else:
            with open("data/members.json", "w") as f:
                json.dump(list(members.values()), f, indent=2)
            print("Saved to members.json")

        await context.close()


asyncio.run(main())
