"""Typer application. Commands parse arguments and delegate; they hold no logic."""

from importlib.metadata import version
from typing import Annotated

import typer

app = typer.Typer(
    name="learn-german",
    help="Mine German texts for Nomen-Verb-Verbindungen and push production cards into Anki.",
    no_args_is_help=True,
    add_completion=False,
)


def _print_version(value: bool) -> None:
    if value:
        typer.echo(f"learn-german {version('learn-german')}")
        raise typer.Exit


@app.callback()
def root(
    show_version: Annotated[
        bool,
        typer.Option(
            "--version",
            help="Show the installed version and exit.",
            callback=_print_version,
            is_eager=True,
        ),
    ] = False,
) -> None:
    """Mine German texts for Nomen-Verb-Verbindungen and push production cards into Anki."""


def main() -> None:
    """Console-script entry point."""
    app()
