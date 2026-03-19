"""Tests for the extract module."""

import json
import pytest
from pathlib import Path

from x_migrate.extract import (
    parse_members_from_response,
    parse_following_from_response,
    is_session_expired,
    run_extract,
)

FIXTURES = Path(__file__).parent / "fixtures"


# T1: parse_members_from_response with valid fixture
def test_parse_members_valid():
    data = json.loads((FIXTURES / "list_members_response.json").read_text())
    result = parse_members_from_response(data)

    assert "alice" in result
    assert result["alice"]["name"] == "Alice Example"
    assert result["alice"]["id"] == "123456"
    assert result["alice"]["status"] == "pending"


# T2: parse_members_from_response with malformed input
def test_parse_members_malformed():
    assert parse_members_from_response({}) == {}
    assert parse_members_from_response({"data": "not a dict"}) == {}


# T3: parse_following_from_response with valid fixture
def test_parse_following_valid():
    data = json.loads((FIXTURES / "following_response.json").read_text())
    result = parse_following_from_response(data)

    assert "bob" in result
    assert result["bob"]["name"] == "Bob Example"
    assert result["bob"]["id"] == "789012"
    assert result["bob"]["status"] == "pending"


# T16: is_session_expired helper
def test_session_expired_url_detection():
    assert is_session_expired("https://x.com/login") is True
    assert is_session_expired("https://x.com/i/flow/login") is True
    assert is_session_expired("https://x.com/i/lists/123") is False
    assert is_session_expired("https://x.com/home") is False


# Input validation tests
async def test_extract_invalid_source():
    """extract with invalid --source exits with error."""
    with pytest.raises(SystemExit) as exc:
        await run_extract("invalid", None, None)
    assert exc.value.code == 1


async def test_extract_list_without_url():
    """extract --source list without --url exits with error."""
    with pytest.raises(SystemExit) as exc:
        await run_extract("list", None, None)
    assert exc.value.code == 1


async def test_extract_following_without_account():
    """extract --source following without --account exits with error."""
    with pytest.raises(SystemExit) as exc:
        await run_extract("following", None, None)
    assert exc.value.code == 1
