"""Tests for the extract module."""

import json
import pytest
from pathlib import Path

from x_migrate.extract import (
    parse_members_from_response,
    parse_following_from_response,
    is_session_expired,
    run_extract,
    _validate_x_url,
    _sanitize_handle,
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


# URL validation tests
def test_validate_x_url_valid():
    """Valid x.com URL passes validation."""
    _validate_x_url("https://x.com/i/lists/123/members")  # should not raise


def test_extract_list_navigates_to_members_tab(monkeypatch):
    """extract --source list appends /members to nav URL if missing."""
    import x_migrate.extract as ext_mod

    navigated_urls = []

    # Stub config, progress, and browser to capture the navigation URL
    monkeypatch.setattr(ext_mod.cfg, "load", lambda: {"source_profile": "/tmp/fake"})
    monkeypatch.setattr(ext_mod.cfg, "save", lambda c: None)
    monkeypatch.setattr(ext_mod.progress, "job_id", lambda s: "abc123")
    monkeypatch.setattr(ext_mod.progress, "load", lambda j: {})
    monkeypatch.setattr(ext_mod.progress, "save", lambda j, d: None)

    class FakePage:
        url = "https://x.com/i/lists/123/members"
        def on(self, *a, **kw):
            pass
        async def route(self, *a, **kw):
            pass
        async def evaluate(self, *a, **kw):
            pass
        async def goto(self, url, **kw):
            navigated_urls.append(url)

    class FakeCtx:
        async def new_page(self):
            return FakePage()
        async def close(self):
            pass

    class FakePw:
        async def stop(self):
            pass

    monkeypatch.setattr(ext_mod.browser, "launch_context", lambda p: _async_val((FakePw(), FakeCtx())))
    monkeypatch.setattr("builtins.input", lambda _: "")
    monkeypatch.setattr(ext_mod.asyncio, "sleep", _async_noop)

    import asyncio
    asyncio.run(ext_mod.run_extract("list", "https://x.com/i/lists/123", None))

    # First goto is the initial navigation, second is after "press Enter"
    assert navigated_urls[0] == "https://x.com/i/lists/123/members"
    assert navigated_urls[1] == "https://x.com/i/lists/123/members"


async def _async_val(val):
    return val


async def _async_noop(*a, **kw):
    pass


def test_validate_x_url_rejects_file():
    """file:// URLs are rejected."""
    with pytest.raises(SystemExit, match="must be an https://x.com/"):
        _validate_x_url("file:///etc/passwd")


def test_validate_x_url_rejects_javascript():
    """javascript: URLs are rejected."""
    with pytest.raises(SystemExit, match="must be an https://x.com/"):
        _validate_x_url("javascript:alert(1)")


def test_validate_x_url_rejects_other_domain():
    """Non-x.com URLs are rejected."""
    with pytest.raises(SystemExit, match="must be an https://x.com/"):
        _validate_x_url("https://evil.com/x.com/lists")


# Handle sanitization tests
def test_sanitize_handle_valid():
    """Valid handle passes sanitization."""
    assert _sanitize_handle("@alice_123") == "alice_123"
    assert _sanitize_handle("bob") == "bob"


def test_sanitize_handle_rejects_slashes():
    """Handles with slashes are rejected."""
    with pytest.raises(SystemExit, match="invalid X handle"):
        _sanitize_handle("alice/../../etc")


def test_sanitize_handle_rejects_empty():
    """Empty handles are rejected."""
    with pytest.raises(SystemExit, match="invalid X handle"):
        _sanitize_handle("@")
