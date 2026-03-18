"""Config module for x-migrate.

Reads and writes ~/.x-migrate/config.toml.
"""

import tomllib
from pathlib import Path

import tomli_w


def config_path() -> Path:
    """Return the path to the config file."""
    return Path.home() / ".x-migrate" / "config.toml"


def load() -> dict:
    """Load config from ~/.x-migrate/config.toml.

    Exits with a friendly message if the file is missing or malformed.
    """
    path = config_path()
    if not path.exists():
        print("No config found. Run 'x-migrate setup' first.")
        raise SystemExit(1)
    try:
        with open(path, "rb") as f:
            return tomllib.load(f)
    except tomllib.TOMLDecodeError:
        print("Config file is corrupted. Run 'x-migrate setup' to recreate it.")
        raise SystemExit(1)


def save(data: dict) -> None:
    """Write data to ~/.x-migrate/config.toml, creating the directory if needed."""
    path = config_path()
    path.parent.mkdir(parents=True, exist_ok=True)
    with open(path, "wb") as f:
        tomli_w.dump(data, f)
