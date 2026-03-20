"""Tests for the report_cmd module."""

import pytest
from pathlib import Path

from x_migrate.report_cmd import run_report


@pytest.fixture(autouse=True)
def patch_home(tmp_path, monkeypatch):
    monkeypatch.setattr(Path, "home", lambda: tmp_path)


async def test_report_no_active_job():
    """report exits with error when no active_job is set."""
    # Create config without active_job
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
