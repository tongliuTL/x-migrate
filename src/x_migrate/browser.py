"""Browser module for launching persistent Chrome contexts with Playwright."""

from pathlib import Path
from playwright.async_api import async_playwright

CHROME_ARGS = ["--disable-blink-features=AutomationControlled"]


async def launch_context(profile_path: str) -> tuple:
    """
    Launch a persistent Chrome context at the given profile path.
    Returns (playwright_instance, context) — caller must close both.

    Raises SystemExit(1) with a friendly message if Chrome is not installed.

    Usage:
        pw, ctx = await launch_context(profile_path)
        page = await ctx.new_page()
        ...
        await ctx.close()
        await pw.stop()
    """
    Path(profile_path).mkdir(parents=True, exist_ok=True)
    pw = None
    try:
        pw = await async_playwright().start()
        ctx = await pw.chromium.launch_persistent_context(
            user_data_dir=profile_path,
            headless=False,
            channel="chrome",
            args=CHROME_ARGS,
        )
        return pw, ctx
    except Exception as e:
        if pw:
            await pw.stop()
        msg = str(e).lower()
        if "chrome" in msg or "executable" in msg or "not found" in msg:
            print(
                "Chrome not found. Install it: brew install --cask google-chrome"
            )
            raise SystemExit(1)
        raise
