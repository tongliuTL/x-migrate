"""Rich TUI module for x-migrate.

Provides progress bar, live status updates, and summary table display.
"""

from collections import Counter

from rich.console import Console
from rich.progress import Progress, SpinnerColumn, BarColumn, TextColumn, TimeElapsedColumn
from rich.table import Table

console = Console()


def make_progress() -> Progress:
    """Create a Rich Progress instance for the follow/list-add loop."""
    return Progress(
        SpinnerColumn(),
        TextColumn("[progress.description]{task.description}"),
        BarColumn(),
        TextColumn("{task.completed}/{task.total}"),
        TimeElapsedColumn(),
        console=console,
    )


def print_summary(progress_data: dict, title: str = "Session Summary") -> None:
    """Print a Rich summary table of the progress data.

    progress_data format: {username: {status: str, name: str, id: str}}
    """
    counts = Counter(d.get("status", "unknown") for d in progress_data.values())

    table = Table(title=title, show_header=True, header_style="bold cyan")
    table.add_column("Status", style="dim")
    table.add_column("Count", justify="right")

    status_order = ["followed", "already_following", "requested", "unavailable",
                    "added_to_list", "error", "rate_limited", "pending", "list_add_failed"]

    for status in status_order:
        if status in counts:
            color = {
                "followed": "green",
                "already_following": "blue",
                "requested": "yellow",
                "unavailable": "red",
                "added_to_list": "green",
                "error": "red",
                "rate_limited": "bold red",
                "list_add_failed": "red",
                "pending": "dim",
            }.get(status, "white")
            table.add_row(f"[{color}]{status}[/{color}]", str(counts[status]))

    console.print(table)


def status_style(status: str) -> str:
    """Return Rich markup style for a given status string."""
    styles = {
        "followed": "[green]followed[/green]",
        "already_following": "[blue]already following[/blue]",
        "requested": "[yellow]requested[/yellow]",
        "unavailable": "[red]unavailable[/red]",
        "added_to_list": "[green]added to list[/green]",
        "list_add_failed": "[red]list add failed[/red]",
        "error": "[red]error[/red]",
        "rate_limited": "[bold red]RATE LIMITED[/bold red]",
    }
    return styles.get(status, status)
