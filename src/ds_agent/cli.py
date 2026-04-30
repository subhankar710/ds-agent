"""ds_agent.cli — Typer-based command-line interface."""
from __future__ import annotations

import typer
from rich.console import Console

from .config import get_settings
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
