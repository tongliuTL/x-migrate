"""
Script 2: Add extracted members to a new list on your destination X account.

Before running:
  1. Run extract_members.py first to produce members.json
  2. Manually create an empty list on your destination account on X
  3. Set LIST_NAME below to the exact name of that new list

The script saves progress to progress.json after each user,
so it's safe to interrupt and re-run — it will skip already-added members.
"""

import asyncio
import json
import random
from playwright.async_api import async_playwright

# ------------------------------------------------------------------ #
#  CONFIGURE THIS before running                                       #
LIST_NAME = "YOUR_NEW_LIST_NAME_HERE"   # exact name of the new list  #
# ------------------------------------------------------------------ #


async def add_to_list(page, username: str, list_name: str) -> bool:
    try:
        await page.goto(
            f"https://x.com/{username}",
            wait_until="domcontentloaded",
            timeout=20000,
        )
        await asyncio.sleep(random.uniform(1.5, 2.5))

        # Click the "..." (More) button on the profile header
        more_btn = page.locator('[data-testid="userActions"]')
        await more_btn.wait_for(timeout=8000)
        await more_btn.click()
        await asyncio.sleep(0.8)

        # Click "Add/remove from Lists"
        list_option = page.get_by_text("Add/remove", exact=False)
        await list_option.first.wait_for(timeout=5000)
        await list_option.first.click()
        await asyncio.sleep(1.2)

        # Find the target list by name
        list_item = page.get_by_text(list_name, exact=True)
        await list_item.wait_for(timeout=5000)

        # Only click if not already added (aria-checked != "true")
        row = list_item.locator("xpath=ancestor::div[@role='menuitem' or @role='option'][1]")
        checked = await row.get_attribute("aria-checked")
        if checked != "true":
            await list_item.click()
            await asyncio.sleep(0.8)
        else:
            print("(already in list)", end=" ", flush=True)

        await page.keyboard.press("Escape")
        return True

    except Exception as e:
        print(f"ERROR: {e}", end=" ", flush=True)
        # Try to dismiss any open modal before continuing
        try:
            await page.keyboard.press("Escape")
        except Exception:
            pass
        return False


async def main():
    if LIST_NAME == "YOUR_NEW_LIST_NAME_HERE":
        print("ERROR: Please set LIST_NAME in the script before running.")
        return

    try:
        with open("data/members.json") as f:
            members = json.load(f)
    except FileNotFoundError:
        print("ERROR: data/members.json not found. Run extract_members.py first.")
        return

    # Resume support
    try:
        with open("data/progress.json") as f:
            done = set(json.load(f))
        print(f"Resuming — {len(done)} members already added previously.")
    except FileNotFoundError:
        done = set()

    failed = []

    async with async_playwright() as p:
        # Use real Chrome with a persistent profile so X doesn't flag as bot.
        # Login session is saved in ./profile_dest — no need to log in again on reruns.
        context = await p.chromium.launch_persistent_context(
            user_data_dir="./profile_dest",
            headless=False,
            channel="chrome",
            args=["--disable-blink-features=AutomationControlled"],
        )
        page = await context.new_page()

        await page.goto("https://x.com/login")

        print("=" * 60)
        print("A browser window has opened.")
        print("1. Log into your DESTINATION X account.")
        print("   (Next time you run this, login will already be saved.)")
        print("2. Make sure you have already created the new list.")
        print("3. Come back here and press Enter to start.")
        print("=" * 60)
        input("\n>>> Press Enter when ready: ")
        await asyncio.sleep(2)

        remaining = [m for m in members if m["username"] not in done]
        total = len(remaining)
        print(f"\nAdding {total} members to '{LIST_NAME}' (skipping {len(done)} already done)...")
        print("Do not interact with the browser while this runs.\n")

        for i, member in enumerate(remaining):
            username = member["username"]
            print(f"[{i + 1}/{total}] @{username} ... ", end="", flush=True)

            success = await add_to_list(page, username, LIST_NAME)

            if success:
                done.add(username)
                print("OK")
            else:
                failed.append(username)
                print("FAILED")

            # Save progress after every user so we can resume safely
            with open("data/progress.json", "w") as f:
                json.dump(list(done), f)

            # Random delay — keeps pace human-like to avoid bot detection
            await asyncio.sleep(random.uniform(4, 8))

        print(f"\n{'=' * 60}")
        print(f"Done:   {len(done)} members added successfully")
        print(f"Failed: {len(failed)} members")

        if failed:
            with open("data/failed.json", "w") as f:
                json.dump(failed, f, indent=2)
            print("Failed usernames saved to data/failed.json")
            print("Re-run this script to retry them (progress is saved).")

        await context.close()


asyncio.run(main())
