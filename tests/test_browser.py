"""Tests for the browser module."""

import pytest
from unittest.mock import AsyncMock, MagicMock, patch


@pytest.mark.asyncio
async def test_chrome_not_found_raises_system_exit(capsys):
    """T13: Chrome-not-found path triggers SystemExit(1) with install hint."""
    mock_pw = AsyncMock()
    mock_pw.chromium.launch_persistent_context.side_effect = Exception(
        "Executable not found: chrome"
    )

    mock_ap_instance = MagicMock()
    mock_ap_instance.start = AsyncMock(return_value=mock_pw)

    with patch("x_migrate.browser.async_playwright", return_value=mock_ap_instance):
        with pytest.raises(SystemExit) as exc_info:
            from x_migrate.browser import launch_context
            await launch_context("/tmp/test-profile")
        assert exc_info.value.code == 1

    captured = capsys.readouterr()
    assert "Chrome" in captured.out or "chrome" in captured.out
