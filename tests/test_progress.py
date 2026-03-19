"""Tests for the progress module."""

import pytest
from pathlib import Path

from x_migrate import progress


@pytest.fixture(autouse=True)
def patch_home(tmp_path, monkeypatch):
    """Redirect Path.home() to a temp directory for all tests."""
    monkeypatch.setattr(Path, "home", lambda: tmp_path)


def test_save_load_roundtrip():
    """T5: Create a progress dict, save it, reload it, assert equality."""
    job = "test_job_123"
    data = {
        "user1": {"status": "followed", "name": "User One", "id": "111"},
        "user2": {"status": "error", "name": "User Two", "id": "222"},
    }

    progress.save(job, data)
    loaded = progress.load(job)

    assert loaded == data


def test_load_missing_file():
    """T6: Calling load() on nonexistent job returns {} (not an error)."""
    result = progress.load("nonexistent_job_id")
    assert result == {}


def test_job_id_same_source():
    """T9a: job_id() returns the same result when called twice with same source."""
    source = "https://x.com/i/lists/123"
    id1 = progress.job_id(source)
    id2 = progress.job_id(source)

    assert id1 == id2
    assert len(id1) == 12  # Verify it's 12 chars


def test_job_id_different_source():
    """T9b: job_id() returns different results for different sources."""
    id1 = progress.job_id("https://x.com/i/lists/123")
    id2 = progress.job_id("@someuser")

    assert id1 != id2


def test_pending():
    """Test pending() returns only usernames not in a final status."""
    data = {
        "user1": {"status": "followed", "name": "User One", "id": "111"},
        "user2": {"status": "unavailable", "name": "User Two", "id": "222"},
        "user3": {"status": "error", "name": "User Three", "id": "333"},
    }

    result = progress.pending(data)

    assert result == ["user3"]


def test_summary():
    """Test summary() returns count per status."""
    data = {
        "user1": {"status": "followed", "name": "User One", "id": "111"},
        "user2": {"status": "followed", "name": "User Two", "id": "222"},
        "user3": {"status": "error", "name": "User Three", "id": "333"},
    }

    result = progress.summary(data)

    assert result == {"followed": 2, "error": 1}
