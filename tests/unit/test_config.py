from pathlib import Path

import pytest

from learn_german.config import config_dir, default_config_file, load_settings
from learn_german.domain.errors import ConfigError, MissingCredentialsError


@pytest.fixture
def toml_file(tmp_path: Path) -> Path:
    return tmp_path / "config.toml"


@pytest.fixture
def env_file(tmp_path: Path) -> Path:
    return tmp_path / ".env"


# Each case sets `cap` in the listed layers; the highest layer must win (R12, R25).
@pytest.mark.parametrize(
    ("layers", "expected"),
    [
        pytest.param(set(), 10, id="default"),
        pytest.param({"toml"}, 5, id="toml-over-default"),
        pytest.param({"toml", "dotenv"}, 4, id="dotenv-over-toml"),
        pytest.param({"toml", "dotenv", "env"}, 3, id="env-over-dotenv"),
        pytest.param({"toml", "dotenv", "env", "flag"}, 2, id="flag-over-env"),
        pytest.param({"toml", "flag"}, 2, id="flag-over-toml"),
    ],
)
def test_settings_precedence(
    layers: set[str],
    expected: int,
    toml_file: Path,
    env_file: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    if "toml" in layers:
        toml_file.write_text("cap = 5\n", encoding="utf-8")
    if "dotenv" in layers:
        env_file.write_text("LEARN_GERMAN_CAP=4\n", encoding="utf-8")
    if "env" in layers:
        monkeypatch.setenv("LEARN_GERMAN_CAP", "3")
    flags = {"cap": 2} if "flag" in layers else {"cap": None}

    settings = load_settings(flags, config_file=toml_file, env_file=env_file)

    assert settings.cap == expected


def test_settings_defaults(toml_file: Path, env_file: Path) -> None:
    settings = load_settings(config_file=toml_file, env_file=env_file)

    assert settings.model_dump() == {
        "hint_language": None,
        "cap": 10,
        "provider": "anthropic",
        "model": "claude-opus-5-5",
        "deck": "learn-german::chunks",
        "database_path": settings.database_path,
        "anthropic_api_key": None,
    }


def test_settings_paths_follow_xdg(isolated_home: Path) -> None:
    settings = load_settings()

    assert default_config_file() == isolated_home / ".config" / "learn-german" / "config.toml"
    assert settings.database_path == (
        isolated_home / ".local" / "share" / "learn-german" / "learn-german.db"
    )


def test_settings_read_default_config_file() -> None:
    config_dir().mkdir(parents=True)
    default_config_file().write_text('hint_language = "en"\n', encoding="utf-8")

    assert load_settings().hint_language == "en"


def test_settings_read_dotenv_from_working_directory() -> None:
    Path(".env").write_text("LEARN_GERMAN_DECK=Test::Deck\n", encoding="utf-8")

    assert load_settings().deck == "Test::Deck"


def test_settings_ignore_unrelated_dotenv_variables(env_file: Path, toml_file: Path) -> None:
    env_file.write_text("SOME_OTHER_TOOL=1\n", encoding="utf-8")

    assert load_settings(config_file=toml_file, env_file=env_file).cap == 10


def test_settings_expand_home_in_database_path(isolated_home: Path, toml_file: Path) -> None:
    toml_file.write_text('database_path = "~/state/lg.db"\n', encoding="utf-8")

    settings = load_settings(config_file=toml_file, env_file=None)

    assert settings.database_path == isolated_home / "state" / "lg.db"


def test_settings_read_api_key_without_prefix(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("ANTHROPIC_API_KEY", "sk-test")

    assert load_settings().require_anthropic_api_key() == "sk-test"


@pytest.mark.parametrize("value", [None, ""], ids=["unset", "empty"])
def test_settings_require_api_key_when_missing(
    value: str | None, monkeypatch: pytest.MonkeyPatch
) -> None:
    if value is not None:
        monkeypatch.setenv("ANTHROPIC_API_KEY", value)

    with pytest.raises(MissingCredentialsError, match="ANTHROPIC_API_KEY"):
        load_settings().require_anthropic_api_key()


def test_settings_api_key_is_hidden_in_repr(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("ANTHROPIC_API_KEY", "sk-secret")

    assert "sk-secret" not in repr(load_settings())


def test_settings_hint_language_is_optional_until_required() -> None:
    settings = load_settings()

    with pytest.raises(ConfigError, match="hint_language"):
        settings.require_hint_language()


def test_settings_treat_empty_hint_language_as_unset(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("LEARN_GERMAN_HINT_LANGUAGE", "")

    assert load_settings().hint_language is None


def test_settings_require_hint_language_returns_it(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("LEARN_GERMAN_HINT_LANGUAGE", "en")

    assert load_settings().require_hint_language() == "en"


@pytest.mark.parametrize(
    ("content", "message"),
    [
        pytest.param('hint_language = "English"\n', "hint_language", id="hint-not-a-code"),
        pytest.param("cap = -1\n", "cap", id="negative-cap"),
        pytest.param('cap = "many"\n', "cap", id="cap-not-a-number"),
        pytest.param('hint_langauge = "en"\n', "unknown settings: hint_langauge", id="typo"),
        pytest.param("cap = \n", "not valid TOML", id="broken-toml"),
    ],
)
def test_settings_reject_invalid_config(content: str, message: str, toml_file: Path) -> None:
    toml_file.write_text(content, encoding="utf-8")

    with pytest.raises(ConfigError, match=message):
        load_settings(config_file=toml_file, env_file=None)


def test_settings_reject_invalid_environment_value(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("LEARN_GERMAN_CAP", "ten")

    with pytest.raises(ConfigError, match="cap"):
        load_settings()
