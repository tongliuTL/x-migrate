import os
import typer
from typing import Optional

from x_migrate import config as cfg

app = typer.Typer(help="Migrate X (Twitter) lists and follows between accounts.")


@app.command()
def setup():
    """Run the setup wizard to create ~/.x-migrate/config.toml."""
    print("=== x-migrate setup ===")

    default_source = os.path.expanduser("~/.x-migrate/profile_source")
    default_dest = os.path.expanduser("~/.x-migrate/profile_dest")
    default_limit = 20

    source_input = input(f"Source profile path [{default_source}]: ").strip()
    source_profile = os.path.expanduser(source_input) if source_input else default_source

    dest_input = input(f"Dest profile path [{default_dest}]: ").strip()
    dest_profile = os.path.expanduser(dest_input) if dest_input else default_dest

    limit_input = input(f"Daily follow limit [{default_limit}]: ").strip()
    try:
        daily_limit = int(limit_input) if limit_input else default_limit
    except ValueError:
        print(f"Invalid number, using default: {default_limit}")
        daily_limit = default_limit

    data = {
        "source_profile": source_profile,
        "dest_profile": dest_profile,
        "active_job": "",
        "daily_limit": daily_limit,
    }
    cfg.save(data)
    print("Config saved to ~/.x-migrate/config.toml")


@app.command()
def extract(
    source: str = typer.Option("list", help="Source type: 'list' or 'following'"),
    url: Optional[str] = typer.Option(None, help="URL of the X list"),
    account: Optional[str] = typer.Option(None, help="X account handle"),
):
    """Extract members from an X list or following list."""
    cfg.load()
    print("not implemented yet")
    raise SystemExit(0)


@app.command()
def follow(
    limit: int = typer.Option(20, help="Maximum number of accounts to follow"),
    dry_run: bool = typer.Option(False, "--dry-run", help="Simulate without making changes"),
):
    """Follow accounts from extracted list."""
    cfg.load()
    print("not implemented yet")
    raise SystemExit(0)


@app.command()
def list_add(
    list_name: str = typer.Option(..., help="Name of the list to add members to"),
):
    """Add members to an X list."""
    cfg.load()
    print("not implemented yet")
    raise SystemExit(0)


@app.command()
def report():
    """Compare following vs members in lists."""
    cfg.load()
    print("not implemented yet")
    raise SystemExit(0)
