"""Tests for the follow module."""

import pytest
from unittest.mock import AsyncMock, MagicMock, patch, call
from contextlib import contextmanager

from x_migrate.follow import (
    classify_buttons,
    human_delay,
    follow_user,
    parse_backoff,
    run_follow,
)
from x_migrate.progress import FINAL_STATUSES


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

_CFG = {"dest_profile": "/tmp/p", "active_job": "testjob123"}


def _fresh_data():
    """Fresh pending data for each test — avoids in-place mutation contaminating later tests."""
    return {
        "alice": {"status": "pending", "name": "Alice", "id": "1"},
        "bob":   {"status": "pending", "name": "Bob",   "id": "2"},
    }


def _make_page(handle="destuser"):
    """Return an AsyncMock page with handle detection wired up."""
    page = AsyncMock()
    locator = MagicMock()
    locator.get_attribute = AsyncMock(return_value=f"/users/{handle}")
    page.locator = MagicMock(return_value=locator)
    return page


def _make_browser(page):
    """Return (pw, ctx) mocks that vend the given page."""
    ctx = AsyncMock()
    ctx.new_page = AsyncMock(return_value=page)
    pw = AsyncMock()
    return AsyncMock(return_value=(pw, ctx))


def _make_progress():
    prog = MagicMock()
    prog.add_task = MagicMock(return_value=0)
    return prog


def _std_patches(page, follow_results):
    """Return (patches, follow_mock, sleep_mock) for run_follow integration tests.

    load_mock uses a factory lambda so each call returns a *fresh* dict,
    preventing in-place status mutations from leaking between loop iterations
    or between tests.
    """
    follow_mock = AsyncMock(side_effect=follow_results)
    sleep_mock = AsyncMock()
    load_mock = MagicMock(side_effect=lambda _: _fresh_data())
    prog_mock = _make_progress()

    patches = [
        patch("x_migrate.follow.config.load", return_value=_CFG),          # 0
        patch("x_migrate.follow.progress_store.load", load_mock),           # 1
        patch("x_migrate.follow.progress_store.save"),                      # 2
        patch("x_migrate.follow.browser.launch_context", _make_browser(page)),  # 3
        patch("x_migrate.follow.follow_user", follow_mock),                 # 4
        patch("x_migrate.follow.asyncio.sleep", sleep_mock),               # 5
        patch("x_migrate.follow.ui.print_summary"),                         # 6
        patch("x_migrate.follow.ui.make_progress", return_value=prog_mock), # 7
        patch("x_migrate.follow.ui.console"),                               # 8
        patch("x_migrate.follow.Live"),                                     # 9
    ]
    return patches, follow_mock, sleep_mock


# T4: test_classify_buttons_all_states
def test_classify_buttons_all_states():
    """Test all 5 classification states."""
    # "following" → already_following
    assert classify_buttons(["Following", "Message"]) == "already_following"
    # "unfollow" → already_following
    assert classify_buttons(["Unfollow"]) == "already_following"
    # "requested" → requested
    assert classify_buttons(["Requested"]) == "requested"
    # "follow" → can_follow
    assert classify_buttons(["Follow"]) == "can_follow"
    # no relevant button → no_button
    assert classify_buttons(["Message"]) == "no_button"


# T8: test_human_delay_always_positive
def test_human_delay_always_positive():
    """human_delay() must always return >= 3.0 (guards against negative gauss)."""
    results = [human_delay() for _ in range(100)]
    for r in results:
        assert r >= 3.0, f"human_delay() returned {r}, expected >= 3.0"


# T10: test_dry_run_no_browser
@pytest.mark.asyncio
async def test_dry_run_no_browser(capsys):
    """Dry run should print plan and NOT launch a browser."""
    fake_progress = {
        "alice": {"status": "pending", "name": "Alice", "id": "1"},
        "bob": {"status": "pending", "name": "Bob", "id": "2"},
        "carol": {"status": "pending", "name": "Carol", "id": "3"},
    }

    mock_browser_launch = MagicMock()

    with (
        patch("x_migrate.follow.config.load", return_value={"dest_profile": "/tmp/p", "active_job": "testjob123"}),
        patch("x_migrate.follow.progress_store.load", return_value=fake_progress),
        patch("x_migrate.follow.browser.launch_context", mock_browser_launch),
    ):
        await run_follow(dry_run=True, limit=5)

    # Browser must NOT have been launched
    mock_browser_launch.assert_not_called()

    # All 3 usernames should appear in stdout
    captured = capsys.readouterr()
    assert "@alice" in captured.out
    assert "@bob" in captured.out
    assert "@carol" in captured.out


# T11: test_follow_user_rate_limited
@pytest.mark.asyncio
async def test_follow_user_rate_limited():
    """follow_user() returns 'rate_limited' when button stays on 'Follow' after click."""
    mock_page = AsyncMock()
    mock_page.goto = AsyncMock()
    mock_page.inner_text = AsyncMock(return_value="some profile page")  # not unavailable
    # get_button_texts returns ["Follow"] before AND after click
    mock_page.evaluate = AsyncMock(return_value=["Follow"])

    result = await follow_user(mock_page, "someuser")
    assert result == "rate_limited"


# T15: test_follow_zero_pending_exits_early
@pytest.mark.asyncio
async def test_follow_zero_pending_exits_early(capsys):
    """run_follow() exits early with 'All members already processed!' when no pending members."""
    # All users in final statuses
    all_done_progress = {
        "user1": {"status": "followed", "name": "User One", "id": "1"},
        "user2": {"status": "already_following", "name": "User Two", "id": "2"},
        "user3": {"status": "unavailable", "name": "User Three", "id": "3"},
    }

    mock_browser_launch = MagicMock()

    with (
        patch("x_migrate.follow.config.load", return_value={"dest_profile": "/tmp/p", "active_job": "testjob123"}),
        patch("x_migrate.follow.progress_store.load", return_value=all_done_progress),
        patch("x_migrate.follow.browser.launch_context", mock_browser_launch),
    ):
        await run_follow()

    # Browser must NOT have been launched
    mock_browser_launch.assert_not_called()

    # Should print the early exit message
    captured = capsys.readouterr()
    assert "All members already processed!" in captured.out


# ---------------------------------------------------------------------------
# parse_backoff
# ---------------------------------------------------------------------------

@pytest.mark.parametrize("value,expected", [
    ("0",     0),
    ("",      0),
    ("2h",    7200),
    ("90m",   5400),
    ("3600s", 3600),
    ("1.5h",  5400),
    ("30m",   1800),
    ("45s",   45),
    ("1",     1),    # bare number → seconds
])
def test_parse_backoff_valid(value, expected):
    assert parse_backoff(value) == expected


def test_parse_backoff_invalid_raises():
    with pytest.raises(ValueError, match="Cannot parse"):
        parse_backoff("two hours")


# ---------------------------------------------------------------------------
# auto mode
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_auto_mode_skips_all_prompts():
    """--auto should follow without calling input() at all."""
    page = _make_page("myhandle")
    patches, follow_mock, _ = _std_patches(page, ["followed", "followed"])

    with (
        patches[0], patches[1], patches[2], patches[3],
        patches[4], patches[5], patches[6], patches[7],
        patches[8], patches[9],
        patch("builtins.input") as mock_input,
    ):
        await run_follow(limit=10, auto=True, backoff="0")

    mock_input.assert_not_called()
    assert follow_mock.call_count == 2


@pytest.mark.asyncio
async def test_auto_mode_uses_detected_handle():
    """In auto mode the handle is read from the profile link, not prompted."""
    page = _make_page("autouser")
    patches, follow_mock, _ = _std_patches(page, ["followed", "followed"])

    with (
        patches[0], patches[1], patches[2], patches[3],
        patches[4], patches[5], patches[6], patches[7],
        patches[8], patches[9],
    ):
        await run_follow(limit=10, auto=True, backoff="0")

    page.locator.assert_called()
    assert follow_mock.call_count == 2


@pytest.mark.asyncio
async def test_auto_mode_exits_if_not_logged_in():
    """--auto raises SystemExit(1) when the profile link cannot be found."""
    page = _make_page()
    page.locator.return_value.get_attribute = AsyncMock(side_effect=Exception("timeout"))

    patches, _, _ = _std_patches(page, [])

    with (
        patches[0], patches[1], patches[2], patches[3],
        patches[4], patches[5],
        pytest.raises(SystemExit) as exc_info,
    ):
        await run_follow(limit=10, auto=True, backoff="0")

    assert exc_info.value.code == 1


# ---------------------------------------------------------------------------
# backoff retry loop
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_backoff_sleeps_and_resumes_after_rate_limit():
    """On rate_limited with a backoff set, the runner sleeps then processes remaining users."""
    page = _make_page()
    # Session 1: alice → rate_limited; Session 2: alice → followed, bob → followed
    patches, follow_mock, sleep_mock = _std_patches(
        page,
        follow_results=["rate_limited", "followed", "followed"],
    )

    with (
        patches[0], patches[1], patches[2], patches[3],
        patches[4], patches[5], patches[6], patches[7],
        patches[8], patches[9],
    ):
        await run_follow(limit=10, auto=True, backoff="1h")

    assert follow_mock.call_count == 3  # alice×2 + bob×1

    # asyncio.sleep must have been called with ~3600s (backoff + jitter ≤ ±300)
    backoff_calls = [c for c in sleep_mock.call_args_list if c.args and c.args[0] >= 3300]
    assert len(backoff_calls) >= 1, "Expected at least one backoff sleep ~3600s"


@pytest.mark.asyncio
async def test_no_backoff_stops_on_rate_limit():
    """Without --backoff (or backoff=0), rate_limited halts the session and does not retry."""
    page = _make_page()
    patches, follow_mock, sleep_mock = _std_patches(page, follow_results=["rate_limited"])

    with (
        patches[0], patches[1], patches[2], patches[3],
        patches[4], patches[5], patches[6], patches[7],
        patches[8], patches[9],
    ):
        await run_follow(limit=10, auto=True, backoff="0")

    assert follow_mock.call_count == 1
    # No long sleep — backoff disabled
    backoff_calls = [c for c in sleep_mock.call_args_list if c.args and c.args[0] >= 3300]
    assert len(backoff_calls) == 0


@pytest.mark.asyncio
async def test_backoff_terminates_when_all_pending_done():
    """After a successful session (no rate limit), the while loop exits without sleeping."""
    page = _make_page()
    patches, follow_mock, sleep_mock = _std_patches(page, follow_results=["followed", "followed"])

    with (
        patches[0], patches[1], patches[2], patches[3],
        patches[4], patches[5], patches[6], patches[7],
        patches[8], patches[9],
    ):
        await run_follow(limit=10, auto=True, backoff="2h")

    assert follow_mock.call_count == 2

    # No long sleep — backoff never triggered
    backoff_calls = [c for c in sleep_mock.call_args_list if c.args and c.args[0] >= 3300]
    assert len(backoff_calls) == 0


@pytest.mark.asyncio
async def test_backoff_multiple_rate_limits_keep_retrying():
    """Runner continues through multiple rate-limit / sleep cycles until done."""
    page = _make_page()
    # Three rate limits before finally succeeding on alice, then bob follows
    patches, follow_mock, sleep_mock = _std_patches(
        page,
        follow_results=["rate_limited", "rate_limited", "rate_limited", "followed", "followed"],
    )

    with (
        patches[0], patches[1], patches[2], patches[3],
        patches[4], patches[5], patches[6], patches[7],
        patches[8], patches[9],
    ):
        await run_follow(limit=10, auto=True, backoff="30m")

    assert follow_mock.call_count == 5

    backoff_calls = [c for c in sleep_mock.call_args_list if c.args and c.args[0] >= 1500]
    assert len(backoff_calls) == 3


# ---------------------------------------------------------------------------
# CLI flags
# ---------------------------------------------------------------------------

def test_follow_help_shows_auto_and_backoff():
    """follow --help must advertise the new --auto and --backoff flags."""
    import re
    from typer.testing import CliRunner
    from x_migrate.cli import app

    runner = CliRunner()
    result = runner.invoke(app, ["follow", "--help"])
    assert result.exit_code == 0
    plain = re.sub(r"\x1b\[[0-9;]*m", "", result.output)
    assert "--auto" in plain
    assert "--backoff" in plain
