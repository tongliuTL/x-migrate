import typer
from typing import Optional

app = typer.Typer(help="Migrate X (Twitter) lists and follows between accounts.")


@app.command()
def setup():
    """Run the setup wizard to create ~/.x-migrate/config.toml."""
    print("not implemented yet")
    raise SystemExit(0)


@app.command()
def extract(
    source: str = typer.Option("list", help="Source type: 'list' or 'following'"),
    url: Optional[str] = typer.Option(None, help="URL of the X list"),
    account: Optional[str] = typer.Option(None, help="X account handle"),
):
    """Extract members from an X list or following list."""
    print("not implemented yet")
    raise SystemExit(0)


@app.command()
def follow(
    limit: int = typer.Option(20, help="Maximum number of accounts to follow"),
    dry_run: bool = typer.Option(False, "--dry-run", help="Simulate without making changes"),
):
    """Follow accounts from extracted list."""
    print("not implemented yet")
    raise SystemExit(0)


@app.command()
def list_add(
    list_name: str = typer.Option(..., help="Name of the list to add members to"),
):
    """Add members to an X list."""
    print("not implemented yet")
    raise SystemExit(0)


@app.command()
def report():
    """Compare following vs members in lists."""
    print("not implemented yet")
    raise SystemExit(0)
