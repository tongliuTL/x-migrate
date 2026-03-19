"""Tests for the follow module."""

import pytest
from unittest.mock import AsyncMock, MagicMock, patch

from x_migrate.follow import (
    classify_buttons,
    human_delay,
    follow_user,
    run_follow,
)
from x_migrate.progress import FINAL_STATUSES


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
