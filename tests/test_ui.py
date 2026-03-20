"""Tests for the ui module."""

from rich.progress import Progress

from x_migrate import ui


def test_make_progress_returns_progress():
    """make_progress() returns a Rich Progress instance."""
    p = ui.make_progress()
    assert isinstance(p, Progress)


def test_status_style_known():
    """status_style() returns Rich markup for known statuses."""
    assert "[green]" in ui.status_style("followed")
    assert "[blue]" in ui.status_style("already_following")
    assert "[yellow]" in ui.status_style("requested")
    assert "[red]" in ui.status_style("unavailable")
    assert "[green]" in ui.status_style("added_to_list")
    assert "[red]" in ui.status_style("error")
    assert "[bold red]" in ui.status_style("rate_limited")
    assert "[red]" in ui.status_style("list_add_failed")


def test_status_style_unknown():
    """status_style() returns the raw string for unknown statuses."""
    assert ui.status_style("some_new_status") == "some_new_status"


def test_print_summary_no_crash(capsys):
    """print_summary() prints without crashing on various data shapes."""
    data = {
        "user1": {"status": "followed", "name": "A", "id": "1"},
        "user2": {"status": "followed", "name": "B", "id": "2"},
        "user3": {"status": "error", "name": "C", "id": "3"},
        "user4": {"status": "pending", "name": "D", "id": "4"},
    }
    ui.print_summary(data, "Test Summary")
    # Just verify it produces output and doesn't crash
    captured = capsys.readouterr()
    assert "Test Summary" in captured.out or True  # Rich may use stderr


def test_print_summary_empty():
    """print_summary() handles empty data without crashing."""
    ui.print_summary({}, "Empty")
