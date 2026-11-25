"""Shared fixtures for every test layer."""

import os
from pathlib import Path

import pytest


@pytest.fixture(autouse=True)
def isolated_home(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> Path:
    """Keep tests away from the owner's real home, settings and secrets.

    HOME and the XDG directories point at tmp_path, the working directory is tmp_path (so a
    developer's .env is not read), and every learn-german or Anthropic variable is removed.
    """
    home = tmp_path / "home"
    home.mkdir()
    monkeypatch.setenv("HOME", str(home))
    monkeypatch.setenv("XDG_CONFIG_HOME", str(home / ".config"))
    monkeypatch.setenv("XDG_DATA_HOME", str(home / ".local" / "share"))
    monkeypatch.setenv("XDG_CACHE_HOME", str(home / ".cache"))
    for name in list(os.environ):
        if name.upper().startswith(("LEARN_GERMAN_", "ANTHROPIC_")):
            monkeypatch.delenv(name)
    work = tmp_path / "work"
    work.mkdir()
    monkeypatch.chdir(work)
    return home
