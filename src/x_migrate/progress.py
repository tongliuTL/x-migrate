"""Progress store module for x-migrate.

Saves and loads job progress to/from ~/.x-migrate/progress/{job}.json.
Format: {username: {status: str, name: str, id: str}}
"""

from pathlib import Path
import hashlib
import json


FINAL_STATUSES = {"followed", "already_following", "requested", "unavailable", "added_to_list"}


def job_id(source_arg: str) -> str:
    """Return 12-char hex job ID stable for a given source URL or handle."""
    return hashlib.sha256(source_arg.encode()).hexdigest()[:12]


def progress_path(job: str) -> Path:
    """Return path to the progress file for a given job ID."""
    return Path.home() / ".x-migrate" / "progress" / f"{job}.json"


def load(job: str) -> dict:
    """
    Load progress for a job. Returns {} if file doesn't exist.
    Format: {username: {status: str, name: str, id: str}}
    """
    path = progress_path(job)
    if not path.exists():
        return {}
    with path.open() as f:
        return json.load(f)


def save(job: str, data: dict) -> None:
    """Save progress dict to ~/.x-migrate/progress/{job}.json"""
    path = progress_path(job)
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w") as f:
        json.dump(data, f, indent=2)


def pending(data: dict) -> list[str]:
    """Return list of usernames not yet in a final status."""
    return [u for u, d in data.items() if d.get("status") not in FINAL_STATUSES]


def summary(data: dict) -> dict:
    """Return count per status, plus 'pending' for not-yet-final entries."""
    counts = {}
    for d in data.values():
        s = d.get("status", "pending")
        counts[s] = counts.get(s, 0) + 1
    return counts
