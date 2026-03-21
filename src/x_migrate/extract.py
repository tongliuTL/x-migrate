"""Extract module for x-migrate.

Intercepts GraphQL responses from X to collect list members or following data.
"""

import asyncio
import json
import re

from x_migrate import browser, config as cfg, progress


# Usernames: 1-15 alphanumeric or underscore
_VALID_USERNAME_RE = re.compile(r"^[A-Za-z0-9_]{1,15}$")

def _validate_x_url(url: str) -> None:
    """Ensure URL is an https://x.com/ URL (not file://, javascript:, etc.)."""
    if not url.startswith("https://x.com/"):
        raise SystemExit("Error: --url must be an https://x.com/ URL.")

def _sanitize_handle(handle: str) -> str:
    """Validate and return a clean X handle (no @, alphanumeric + underscore)."""
    clean = handle.lstrip("@")
    if not _VALID_USERNAME_RE.match(clean):
        raise SystemExit(f"Error: invalid X handle '{handle}'.")
    return clean


def parse_members_from_response(data: dict) -> dict:
    """Parse list members. Returns {username: {status, name, id}}."""
    result = {}
    try:
        instructions = (
            data.get("data", {})
                .get("list", {})
                .get("members_timeline", {})
                .get("timeline", {})
                .get("instructions", [])
        )
        if not isinstance(instructions, list):
            return result
        for instruction in instructions:
            if instruction.get("type") != "TimelineAddEntries":
                continue
            for entry in instruction.get("entries", []):
                item = entry.get("content", {}).get("itemContent", {})
                if item.get("itemType") != "TimelineUser":
                    continue
                user_result = item.get("user_results", {}).get("result", {})
                core = user_result.get("core", {})
                screen_name = core.get("screen_name")
                if screen_name:
                    result[screen_name] = {
                        "username": screen_name,
                        "name": core.get("name", ""),
                        "id": user_result.get("rest_id", ""),
                        "status": "pending",
                    }
    except (KeyError, TypeError, AttributeError):
        pass  # Unexpected response structure — skip silently
    return result


def parse_following_from_response(data: dict) -> dict:
    """Parse following list. Returns {username: {status, name, id}}."""
    result = {}
    try:
        instructions = (
            data.get("data", {})
                .get("user", {})
                .get("result", {})
                .get("timeline", {})
                .get("timeline", {})
                .get("instructions", [])
        )
        if not isinstance(instructions, list):
            return result
        for instruction in instructions:
            if instruction.get("type") != "TimelineAddEntries":
                continue
            for entry in instruction.get("entries", []):
                user_result = (
                    entry.get("content", {})
                         .get("itemContent", {})
                         .get("user_results", {})
                         .get("result", {})
                )
                core = user_result.get("core", {})
                screen_name = core.get("screen_name")
                if screen_name:
                    result[screen_name] = {
                        "username": screen_name,
                        "name": core.get("name", ""),
                        "id": user_result.get("rest_id", ""),
                        "status": "pending",
                    }
    except (KeyError, TypeError, AttributeError):
        pass  # Unexpected response structure — skip silently
    return result


def is_session_expired(url: str) -> bool:
    """Return True if the URL indicates a session expiry / login redirect."""
    return "/login" in url or "/i/flow" in url


async def run_extract(source: str, url: str | None, account: str | None) -> None:
    """Run the extract workflow for a list or following page."""
    if source not in ("list", "following"):
        print(f"Invalid source '{source}'. Must be 'list' or 'following'.")
        raise SystemExit(1)

    # Determine source_arg and navigation URL
    if source == "list":
        if not url:
            print("--url is required when --source is 'list'.")
            raise SystemExit(1)
        _validate_x_url(url)
        source_arg = url
        # Ensure we navigate to the members tab, not the list timeline
        nav_url = url.rstrip("/")
        if not nav_url.endswith("/members"):
            nav_url = nav_url + "/members"
    else:
        if not account:
            print("--account is required when --source is 'following'.")
            raise SystemExit(1)
        handle = _sanitize_handle(account)
        source_arg = f"@{handle}"
        nav_url = f"https://x.com/{handle}/following"

    # Load config
    config = cfg.load()
    profile_path = config["source_profile"]

    # Compute job ID and load any existing progress
    job = progress.job_id(source_arg)
    captured: dict = progress.load(job)

    # Launch browser
    pw, ctx = await browser.launch_context(profile_path)
    page = await ctx.new_page()

    # Route-based interception for reliable response body access
    keyword = "ListMembers" if source == "list" else "Following"
    parser = parse_members_from_response if source == "list" else parse_following_from_response

    async def intercept_route(route):
        try:
            response = await route.fetch()
            body = await response.body()
            await route.fulfill(response=response)
            if response.status != 200:
                return
            data = json.loads(body)
            new_entries = parser(data)
            before = len(captured)
            for username, entry in new_entries.items():
                if username not in captured:
                    captured[username] = entry
            added = len(captured) - before
            if added > 0:
                print(f"  [+{added} users, total: {len(captured)}]")
        except Exception as e:
            try:
                await route.continue_()
            except Exception:
                pass
            print(f"  [intercept error: {e}]")

    await page.route(f"**/graphql/**/{keyword}*", intercept_route)

    # Navigate to target page
    await page.goto(nav_url)

    print("=" * 60)
    print("A browser window has opened.")
    print("1. Log into your X account if not already logged in.")
    print("2. Make sure you can see the target page.")
    print("3. Come back here and press Enter to start scrolling.")
    print("=" * 60)
    input("\n>>> Press Enter when ready: ")

    # Re-navigate in case login redirected elsewhere
    print(f"\nNavigating to {nav_url}...")
    await page.goto(nav_url, wait_until="domcontentloaded")
    await asyncio.sleep(3)

    print("Scrolling to load all entries — please don't interact with the browser...")
    stall_count = 0
    last_count = len(captured)

    _SCROLL_JS = """
        () => {
            const col = document.querySelector('[data-testid="primaryColumn"]');
            if (col) col.scrollIntoView(false);
            window.scrollBy(0, 3000);
        }
    """

    while stall_count < 15:
        await page.evaluate(_SCROLL_JS)
        await asyncio.sleep(0.5)
        await page.evaluate(_SCROLL_JS)
        await asyncio.sleep(3.5)

        if len(captured) == last_count:
            stall_count += 1
            if stall_count % 3 == 0:
                print(f"  (no new entries for {stall_count} cycles, still waiting...)")
        else:
            stall_count = 0
            print(f"  Found {len(captured)} entries so far...")
        last_count = len(captured)

    print(f"\nDone scrolling. Total entries found: {len(captured)}")

    # Check for session expiry
    if len(captured) == 0 and is_session_expired(page.url):
        print("\nWARNING: Session may have expired. The page redirected to login.")
        print("Re-run after logging in again.")

    # Save progress
    progress.save(job, captured)
    print(f"Progress saved (job: {job})")

    # Update active_job in config
    config["active_job"] = job
    cfg.save(config)
    print(f"Active job set to: {job}")

    # Close browser
    await ctx.close()
    await pw.stop()
