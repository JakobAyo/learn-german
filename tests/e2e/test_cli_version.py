import re
from importlib.metadata import version

import pytest
from typer.testing import CliRunner

from learn_german.cli.app import app, main

runner = CliRunner()

# Typer forces Rich colour output when GITHUB_ACTIONS is set, so help text in CI
# carries ANSI escape codes that split option names like "--version".
_ANSI_ESCAPE = re.compile(r"\x1b\[[0-9;]*m")


def _plain(text: str) -> str:
    return _ANSI_ESCAPE.sub("", text)


def test_cli_version_prints_package_version() -> None:
    result = runner.invoke(app, ["--version"])

    assert result.exit_code == 0
    assert result.stdout.strip() == f"learn-german {version('learn-german')}"


def test_cli_without_arguments_shows_help() -> None:
    result = runner.invoke(app, [])
    output = _plain(result.output)

    assert "Usage" in output
    assert "--version" in output


def test_cli_main_entry_point_exits_cleanly(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr("sys.argv", ["learn-german", "--version"])

    with pytest.raises(SystemExit) as exc_info:
        main()

    assert exc_info.value.code == 0
