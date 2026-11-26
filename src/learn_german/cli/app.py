"""Typer application. Commands parse arguments and delegate; they hold no logic.

Exit codes: 0 everything worked, 1 some sources or chunks failed, 2 a fatal or usage error.
"""

from collections.abc import Iterator
from contextlib import contextmanager
from importlib.metadata import version
from pathlib import Path
from typing import Annotated, Final

import typer

from learn_german.application.add_sources import AddSummary
from learn_german.application.status import DEFAULT_TOP
from learn_german.bootstrap import IngestServices, Overrides, ingest_services
from learn_german.cli import presenters
from learn_german.config import load_settings
from learn_german.domain.errors import FatalError

EXIT_ITEM_FAILED: Final = 1
EXIT_FATAL: Final = 2

_HELP = "Mine German texts for Nomen-Verb-Verbindungen and push production cards into Anki."


def _print_version(value: bool) -> None:
    if value:
        typer.echo(f"learn-german {version('learn-german')}")
        raise typer.Exit


def read_ref_list(path: Path) -> list[str]:
    """One reference per line; blank lines and lines starting with # are skipped."""
    try:
        lines = path.read_text(encoding="utf-8").splitlines()
    except (OSError, UnicodeDecodeError) as exc:
        raise typer.BadParameter(f"cannot read {path}: {exc}", param_hint="--from") from exc
    return [line.strip() for line in lines if line.strip() and not line.lstrip().startswith("#")]


def create_app(overrides: Overrides | None = None) -> typer.Typer:
    """The CLI. Tests pass `overrides` to swap plug-ins for fakes (0018)."""
    app = typer.Typer(name="learn-german", help=_HELP, no_args_is_help=True, add_completion=False)

    @contextmanager
    def services() -> Iterator[IngestServices]:
        try:
            with ingest_services(load_settings(), overrides) as wired:
                yield wired
        except FatalError as exc:
            typer.echo(presenters.fatal_error(exc), err=True)
            raise typer.Exit(EXIT_FATAL) from exc

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

    @app.command()
    def add(
        refs: Annotated[
            list[str] | None,
            typer.Argument(help="Article URLs or paths of UTF-8 .txt files.", show_default=False),
        ] = None,
        from_file: Annotated[
            Path | None,
            typer.Option("--from", help="File with one URL or path per line; # starts a comment."),
        ] = None,
        force: Annotated[
            bool, typer.Option("--force", help="Fetch and extract sources already added again.")
        ] = False,
    ) -> None:
        """Fetch or read sources, find their chunks and store them for `sync`."""
        all_refs = [*(refs or []), *(read_ref_list(from_file) if from_file else [])]
        if not all_refs:
            raise typer.BadParameter("give at least one URL or file, or --from FILE")
        outcomes = []
        with services() as wired:
            for outcome in wired.add_sources.run(all_refs, force=force):
                typer.echo(presenters.source_outcome(outcome))
                outcomes.append(outcome)
        summary = AddSummary(tuple(outcomes))
        typer.echo(presenters.add_summary(summary))
        if summary.has_failures:
            raise typer.Exit(EXIT_ITEM_FAILED)

    @app.command()
    def status(
        top: Annotated[
            int, typer.Option("--top", min=0, help="How many pending chunks to list.")
        ] = DEFAULT_TOP,
    ) -> None:
        """Show stored sources and the pending chunks `sync` would take first."""
        with services() as wired:
            report = wired.show_status.run(top=top)
        typer.echo(presenters.status_report(report))

    @app.command()
    def reextract() -> None:
        """Find chunks again in every stored source's text, without fetching."""
        outcomes = []
        with services() as wired:
            for outcome in wired.reextract.run():
                typer.echo(presenters.reextract_outcome(outcome))
                outcomes.append(outcome)
        typer.echo(presenters.reextract_summary(outcomes))

    return app


app = create_app()


def main() -> None:
    """Console-script entry point."""
    app()
