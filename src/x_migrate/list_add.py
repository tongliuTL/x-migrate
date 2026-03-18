"""List-add module for x-migrate.

Adds members from the active job's progress store to an X list
on the destination account.
"""

import asyncio
import random

from x_migrate import browser, config, progress as progress_store


async def add_to_list(page, username: str, list_name: str) -> bool:
    try:
        await page.goto(f"https://x.com/{username}", wait_until="domcontentloaded", timeout=20000)
        await asyncio.sleep(random.uniform(1.5, 2.5))
        more_btn = page.locator('[data-testid="userActions"]')
        await more_btn.wait_for(timeout=8000)
        await more_btn.click()
        await asyncio.sleep(0.8)
        list_option = page.get_by_text("Add/remove", exact=False)
        await list_option.first.wait_for(timeout=5000)
        await list_option.first.click()
        await asyncio.sleep(1.2)
        list_item = page.get_by_text(list_name, exact=True)
        await list_item.wait_for(timeout=5000)
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
        try:
            await page.keyboard.press("Escape")
        except Exception:
            pass
        return False


async def run_list_add(list_name: str) -> None:
    """Main runner for the list-add workflow.

    Steps:
    1. Load config, get active_job
    2. Load progress from progress store
    3. Get pending list — if empty, print "All members already processed!" and return
    4. Launch browser (dest profile)
    5. Navigate to x.com/home, prompt for login + Enter
    6. Iterate pending members, call add_to_list() for each
    7. Update progress: success → status="added_to_list", failure → status="list_add_failed"
    8. Save progress after each user (for resume safety)
    9. Print summary at end, close browser
    """
    cfg = config.load()
    active_job = cfg.get("active_job", "")
    dest_profile = cfg.get("dest_profile", "")

    data = progress_store.load(active_job)
    pending = progress_store.pending(data)

    if not pending:
        print("All members already processed!")
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
        print("2. Come back here and press Enter to start adding to list.")
        print("=" * 60)
        input("\n>>> Press Enter when ready: ")
        await asyncio.sleep(2)

        total = len(pending)
        added_count = 0
        failed_count = 0

        print(f"\nAdding {total} members to '{list_name}'...")
        print("Do not interact with the browser while this runs.\n")

        for i, username in enumerate(pending):
            print(f"[{i + 1}/{total}] @{username} ... ", end="", flush=True)

            success = await add_to_list(page, username, list_name)

            if success:
                data[username]["status"] = "added_to_list"
                added_count += 1
                print("OK")
            else:
                data[username]["status"] = "list_add_failed"
                failed_count += 1
                print("FAILED")

            progress_store.save(active_job, data)

        # Print summary
        print(f"\n{'=' * 60}")
        print(f"  Added to list  : {added_count}")
        print(f"  Failed         : {failed_count}")
        print(f"{'=' * 60}")

    finally:
        await ctx.close()
        await pw.stop()
