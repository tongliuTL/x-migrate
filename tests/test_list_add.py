"""Tests for the list_add module."""

import sys
import os
import pytest
from unittest.mock import AsyncMock, MagicMock, patch

# Ensure src is on the path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "src"))

from x_migrate.list_add import add_to_list


# T12: test_add_to_list_already_in_list
@pytest.mark.asyncio
async def test_add_to_list_already_in_list(capsys):
    """add_to_list() returns True and skips click when aria-checked is 'true'."""
    mock_page = AsyncMock()
    mock_page.goto = AsyncMock()

    # more_btn locator
    mock_more_btn = AsyncMock()
    # list_option locator (get_by_text for "Add/remove")
    mock_list_option = AsyncMock()
    mock_list_option.first = AsyncMock()
    # list_item locator (get_by_text for list name, exact=True)
    mock_list_item = AsyncMock()
    # row locator — returns aria-checked="true"
    mock_row = AsyncMock()
    mock_row.get_attribute = AsyncMock(return_value="true")
    mock_list_item.locator = MagicMock(return_value=mock_row)

    # page.locator returns more_btn
    mock_page.locator = MagicMock(return_value=mock_more_btn)

    # page.get_by_text: first call → list_option, second call → list_item
    mock_page.get_by_text = MagicMock(side_effect=[mock_list_option, mock_list_item])

    result = await add_to_list(mock_page, "alice", "MyList")

    assert result is True

    # list_item.click() must NOT have been called (user already in list)
    mock_list_item.click.assert_not_called()

    # Escape must have been pressed
    mock_page.keyboard.press.assert_awaited_with("Escape")

    # "(already in list)" must appear in stdout
    captured = capsys.readouterr()
    assert "(already in list)" in captured.out
