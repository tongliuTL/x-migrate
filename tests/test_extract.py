"""Tests for the extract module."""

import json
from pathlib import Path

from x_migrate.extract import (
    parse_members_from_response,
    parse_following_from_response,
    is_session_expired,
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
