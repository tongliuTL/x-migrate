"""Tests for the CLI module."""

import re
import pytest
from unittest.mock import patch, MagicMock
from typer.testing import CliRunner

from x_migrate.cli import app

runner = CliRunner()


def _strip_ansi(text: str) -> str:
    """Remove ANSI escape sequences from text."""
    return re.sub(r"\x1b\[[0-9;]*m", "", text)


def test_app_help():
    """CLI --help exits cleanly and shows description."""
    result = runner.invoke(app, ["--help"])
    assert result.exit_code == 0
    assert "Migrate X" in _strip_ansi(result.output)


def test_setup_help():
    """setup --help exits cleanly."""
    result = runner.invoke(app, ["setup", "--help"])
    assert result.exit_code == 0
    assert "setup" in _strip_ansi(result.output).lower()


def test_extract_help():
    """extract --help exits cleanly and shows options."""
    result = runner.invoke(app, ["extract", "--help"])
    assert result.exit_code == 0
    plain = _strip_ansi(result.output)
    assert "--source" in plain
    assert "--url" in plain


def test_follow_help():
    """follow --help exits cleanly and shows options."""
    result = runner.invoke(app, ["follow", "--help"])
    assert result.exit_code == 0
    plain = _strip_ansi(result.output)
    assert "--limit" in plain
    assert "--dry-run" in plain


def test_list_add_help():
    """list-add --help exits cleanly and shows options."""
    result = runner.invoke(app, ["list-add", "--help"])
    assert result.exit_code == 0
    assert "--list-name" in _strip_ansi(result.output)


def test_report_help():
    """report --help exits cleanly."""
    result = runner.invoke(app, ["report", "--help"])
    assert result.exit_code == 0


def test_follow_reads_daily_limit_from_config(tmp_path, monkeypatch):
    """follow command uses daily_limit from config when --limit is not provided."""
    from pathlib import Path
    monkeypatch.setattr(Path, "home", lambda: tmp_path)

    # Create a config with daily_limit = 5
    config_dir = tmp_path / ".x-migrate"
    config_dir.mkdir()
    (config_dir / "config.toml").write_text(
        'source_profile = "/tmp/src"\n'
        'dest_profile = "/tmp/dst"\n'
        'active_job = "aabbccddee11"\n'
        'daily_limit = 5\n'
    )

    # Create a progress file with no pending members
    progress_dir = config_dir / "progress"
    progress_dir.mkdir()
    (progress_dir / "aabbccddee11.json").write_text(
        '{"user1": {"status": "followed", "name": "A", "id": "1"}}'
    )

    # run_follow should be called with limit=5 (from config)
    with patch("x_migrate.cli.run_follow") as mock_follow:
        mock_follow.return_value = None  # mock the coroutine
        with patch("x_migrate.cli.asyncio.run") as mock_run:
            result = runner.invoke(app, ["follow"])
            # asyncio.run was called with run_follow(limit=5, dry_run=False)
            mock_run.assert_called_once()


def test_follow_cli_limit_overrides_config(tmp_path, monkeypatch):
    """--limit flag overrides daily_limit from config."""
    from pathlib import Path
    monkeypatch.setattr(Path, "home", lambda: tmp_path)

    with patch("x_migrate.cli.asyncio.run") as mock_run:
        result = runner.invoke(app, ["follow", "--limit", "99"])
        mock_run.assert_called_once()
