"""ds_agent.cli — Typer-based command-line interface."""
from __future__ import annotations

import typer
from rich.console import Console
from rich.table import Table

from .config import get_settings
from .db import Database
from .llm import LLMClient, LLMClientError

app = typer.Typer(
    name="ds-agent",
    help="Data Science Agent — natural-language Q&A over the Olist dataset.",
    no_args_is_help=True,
)
console = Console()


@app.callback()
def _root() -> None:
    """Force Typer into subcommand mode so future commands (eval, trace) work."""


@app.command()
def ask(
    question: str = typer.Argument(..., help="Plain-English question for the agent."),
) -> None:
    """Send a one-shot question to Claude (Step 1 — no tools yet)."""
    settings = get_settings()
    client = LLMClient(settings)

    try:
        answer = client.complete(question)
    except LLMClientError as e:
        console.print(f"[red]LLM error:[/red] {e}")
        raise typer.Exit(code=1)

    console.print(f"[bold green]Answer:[/bold green] {answer}")


# ----------------------------------------------------------------------------
# `db` subcommand group — inspect the local DuckDB.
# ----------------------------------------------------------------------------

db_app = typer.Typer(name="db", help="Inspect the local DuckDB.")
app.add_typer(db_app, name="db")


def _open_db() -> Database:
    """Open the project's DuckDB in read-only mode (defense in depth from the CLI)."""
    settings = get_settings()
    return Database(settings.duckdb_path, read_only=True)


@db_app.command("tables")
def db_tables() -> None:
    """List user tables in the local DuckDB."""
    with _open_db() as db:
        tables = db.list_tables()

    rendered = Table(title="Tables")
    rendered.add_column("name", style="cyan")
    for name in tables:
        rendered.add_row(name)
    console.print(rendered)


@db_app.command("schema")
def db_schema(
    table: str = typer.Argument(..., help="Table name."),
) -> None:
    """Show column info for one table."""
    try:
        with _open_db() as db:
            cols = db.describe_table(table)
    except ValueError as e:
        console.print(f"[red]{e}[/red]")
        raise typer.Exit(code=1)

    rendered = Table(title=f"Schema: {table}")
    rendered.add_column("column", style="cyan")
    rendered.add_column("type", style="magenta")
    rendered.add_column("nullable", style="green")
    for col in cols:
        rendered.add_row(col["name"], col["type"], "yes" if col["nullable"] else "no")
    console.print(rendered)
