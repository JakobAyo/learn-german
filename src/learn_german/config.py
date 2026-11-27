"""Settings, read once in the composition root and passed into constructors.

Precedence, highest first (R12, R25): command-line flag > environment variable > `.env` in the
working directory > `config.toml` in the XDG config directory > default. Environment
variables carry the `LEARN_GERMAN_` prefix, except `ANTHROPIC_API_KEY`. This is the only
module that reads the environment.
"""

import logging
import tomllib
from collections.abc import Mapping
from pathlib import Path
from typing import Any, Final

import platformdirs
from pydantic import AliasChoices, Field, SecretStr, ValidationError, field_validator
from pydantic_settings import (
    BaseSettings,
    PydanticBaseSettingsSource,
    SettingsConfigDict,
    TomlConfigSettingsSource,
)

from learn_german.domain.errors import ConfigError, MissingCredentialsError

logger = logging.getLogger(__name__)

APP_NAME: Final = "learn-german"
ENV_PREFIX: Final = "LEARN_GERMAN_"


def config_dir() -> Path:
    """`~/.config/learn-german` on Linux, or the platform's equivalent."""
    return platformdirs.user_config_path(APP_NAME, appauthor=False)


def data_dir() -> Path:
    """`~/.local/share/learn-german` on Linux, or the platform's equivalent."""
    return platformdirs.user_data_path(APP_NAME, appauthor=False)


def default_config_file() -> Path:
    return config_dir() / "config.toml"


class Settings(BaseSettings):
    """Every setting the tool reads. Build it with `load_settings`, not directly."""

    model_config = SettingsConfigDict(
        env_prefix=ENV_PREFIX,
        env_file_encoding="utf-8",
        extra="ignore",
        frozen=True,
    )

    cap: int = Field(default=10, ge=0, description="Most new chunks per sync (0015).")
    provider: str = Field(default="anthropic", min_length=1, description="LLM provider.")
    model: str = Field(default="claude-opus-5-5", min_length=1, description="LLM model ID.")
    deck: str = Field(default="learn-german::chunks", min_length=1, description="Anki deck.")
    anki_connect_url: str = Field(
        default="http://127.0.0.1:8765",
        pattern=r"^https?://",
        description="AnkiConnect endpoint of the running Anki desktop app (0003).",
    )
    database_path: Path = Field(
        default_factory=lambda: data_dir() / "learn-german.db",
        description="SQLite database file (0007).",
    )
    anthropic_api_key: SecretStr | None = Field(
        default=None,
        validation_alias=AliasChoices("anthropic_api_key", "ANTHROPIC_API_KEY"),
        description="Claude API key. Prefer the environment or .env over config.toml.",
    )

    @field_validator("database_path")
    @classmethod
    def _expand_home(cls, value: Path) -> Path:
        return value.expanduser()

    @classmethod
    def settings_customise_sources(
        cls,
        settings_cls: type[BaseSettings],
        init_settings: PydanticBaseSettingsSource,
        env_settings: PydanticBaseSettingsSource,
        dotenv_settings: PydanticBaseSettingsSource,
        file_secret_settings: PydanticBaseSettingsSource,
    ) -> tuple[PydanticBaseSettingsSource, ...]:
        toml_settings = TomlConfigSettingsSource(settings_cls)
        # extra="ignore" lets .env hold unrelated variables; config.toml is ours, so a key we
        # do not know is a typo and should not be dropped silently.
        unknown = sorted(set(toml_settings.toml_data) - set(cls.model_fields))
        if unknown:
            raise ConfigError(
                f"{toml_settings.toml_file_path} has unknown settings: {', '.join(unknown)}. "
                f"Remove or correct them; the known settings are "
                f"{', '.join(cls.model_fields)}."
            )
        return (init_settings, env_settings, dotenv_settings, toml_settings)

    def require_anthropic_api_key(self) -> str:
        """The Claude API key. Raises `MissingCredentialsError` if unset."""
        if self.anthropic_api_key is None or not self.anthropic_api_key.get_secret_value():
            raise MissingCredentialsError(
                "ANTHROPIC_API_KEY is not set. Create a key in the Claude Console "
                "(platform.claude.com), then export it or put it in a .env file in the "
                "directory you run learn-german from."
            )
        return self.anthropic_api_key.get_secret_value()


def load_settings(
    flags: Mapping[str, object] | None = None,
    *,
    config_file: Path | None = None,
    env_file: Path | None = Path(".env"),
) -> Settings:
    """Merge all setting sources. `flags` holds command-line values; `None` means not given.

    Raises `ConfigError` if a value is invalid, a key is unknown or the TOML cannot be parsed.
    """
    toml_file = default_config_file() if config_file is None else config_file
    logger.debug(
        "Reading settings from %s (%s) and %s (%s)",
        toml_file,
        "found" if toml_file.is_file() else "not found",
        env_file,
        "found" if env_file is not None and env_file.is_file() else "not found",
    )

    class _Sourced(Settings):
        model_config = SettingsConfigDict(toml_file=toml_file, env_file=env_file)

    # Any: pydantic validates the values; the CLI passes them as parsed by typer.
    given: dict[str, Any] = {k: v for k, v in (flags or {}).items() if v is not None}
    try:
        return _Sourced(**given)
    except ValidationError as exc:
        problems = "; ".join(
            f"{'.'.join(str(part) for part in error['loc']) or 'settings'}: {error['msg']}"
            for error in exc.errors()
        )
        raise ConfigError(
            f"Invalid settings ({problems}). Fix the value in {toml_file}, in .env or in "
            f"the {ENV_PREFIX}* environment variables."
        ) from exc
    except tomllib.TOMLDecodeError as exc:
        raise ConfigError(f"{toml_file} is not valid TOML: {exc}. Fix or remove it.") from exc
