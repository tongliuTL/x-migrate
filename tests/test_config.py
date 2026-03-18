"""Tests for the config module."""

import sys
import os
import pytest
from pathlib import Path
from unittest.mock import patch


# Ensure src is on the path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "src"))

from x_migrate import config


def test_load_missing_file(tmp_path):
    """T7: config.load() exits with helpful message when config file is missing."""
    nonexistent = tmp_path / "does_not_exist" / "config.toml"

    with patch.object(config, "config_path", return_value=nonexistent):
        with pytest.raises(SystemExit) as exc_info:
            config.load()

    assert exc_info.value.code == 1


def test_load_missing_file_message(tmp_path, capsys):
    """T7 (message check): printed message contains 'setup'."""
    nonexistent = tmp_path / "does_not_exist" / "config.toml"

    with patch.object(config, "config_path", return_value=nonexistent):
        with pytest.raises(SystemExit):
            config.load()

    captured = capsys.readouterr()
    assert "setup" in captured.out.lower()


def test_load_malformed_toml(tmp_path, capsys):
    """T14: config.load() exits with 'corrupted' message when TOML is invalid."""
    bad_toml = tmp_path / "config.toml"
    bad_toml.write_text("not = [valid toml")

    with patch.object(config, "config_path", return_value=bad_toml):
        with pytest.raises(SystemExit) as exc_info:
            config.load()

    assert exc_info.value.code == 1
    captured = capsys.readouterr()
    assert "corrupted" in captured.out.lower()
