"""Tests for the report_cmd module."""

import json
import pytest
from pathlib import Path

from x_migrate.report_cmd import run_report, _print_local_report


@pytest.fixture(autouse=True)
def patch_home(tmp_path, monkeypatch):
    monkeypatch.setattr(Path, "home", lambda: tmp_path)


async def test_report_no_active_job():
    """report exits with error when no active_job is set."""
    config_dir = Path.home() / ".x-migrate"
    config_dir.mkdir(parents=True)
    (config_dir / "config.toml").write_text(
        'source_profile = "/tmp/src"\n'
        'dest_profile = "/tmp/dst"\n'
        'active_job = ""\n'
    )

    with pytest.raises(SystemExit) as exc:
        await run_report()
    assert exc.value.code == 1


async def test_report_no_config():
    """report exits with error when no config exists."""
    with pytest.raises(SystemExit) as exc:
        await run_report()
    assert exc.value.code == 1


async def test_report_local_no_browser(capsys):
    """report without --verify prints local progress, no browser needed."""
    home = Path.home()
    config_dir = home / ".x-migrate"
    config_dir.mkdir(parents=True)
    (config_dir / "config.toml").write_text(
        'source_profile = "/tmp/src"\n'
        'dest_profile = "/tmp/dst"\n'
        'active_job = "abc123def456"\n'
    )

    progress_dir = config_dir / "progress"
    progress_dir.mkdir()
    data = {
        "alice": {"username": "alice", "name": "Alice", "id": "1", "status": "followed"},
        "bob": {"username": "bob", "name": "Bob", "id": "2", "status": "pending"},
        "carol": {"username": "carol", "name": "Carol", "id": "3", "status": "already_following"},
    }
    (progress_dir / "abc123def456.json").write_text(json.dumps(data))

    await run_report(verify=False)

    out = capsys.readouterr().out
    assert "Total members       : 3" in out
    assert "Followed          : 1" in out
    assert "Pending             : 1" in out
    assert "Already following : 1" in out
    assert "66.7%" in out


def test_print_local_report_empty(capsys):
    """_print_local_report handles empty data."""
    _print_local_report({})
    out = capsys.readouterr().out
    assert "Total members       : 0" in out
