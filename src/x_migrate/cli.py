import asyncio
import os
import typer
from typing import Optional

from x_migrate import config as cfg
from x_migrate.extract import run_extract
from x_migrate.follow import run_follow
from x_migrate.list_add import run_list_add
from x_migrate.report_cmd import run_report

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
    asyncio.run(run_extract(source, url, account))


@app.command()
def follow(
    limit: int = typer.Option(None, help="Maximum follows (default: daily_limit from config, or 20)"),
    dry_run: bool = typer.Option(False, "--dry-run", help="Simulate without making changes"),
):
    """Follow accounts from extracted list."""
    if limit is None:
        try:
            limit = cfg.load().get("daily_limit", 20)
        except SystemExit:
            limit = 20
    asyncio.run(run_follow(limit=limit, dry_run=dry_run))


@app.command()
def list_add(
    list_name: str = typer.Option(..., help="Name of the list to add members to"),
):
    """Add members to an X list."""
    asyncio.run(run_list_add(list_name))


@app.command()
def report(
    verify: bool = typer.Option(False, "--verify", help="Scrape live following list to cross-check"),
):
    """Show migration progress. Use --verify to check against live data."""
    asyncio.run(run_report(verify=verify))
