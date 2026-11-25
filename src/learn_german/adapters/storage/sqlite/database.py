"""Open the database and bring its schema up to date.

Migrations are numbered `.sql` files shipped as package data and applied in order, each in
its own transaction. `PRAGMA user_version` records the last one applied.
"""

import logging
import re
import sqlite3
from dataclasses import dataclass
from importlib.resources import files
from pathlib import Path
from typing import Final, Literal

from learn_german.domain.errors import DatabaseError

logger = logging.getLogger(__name__)

MEMORY: Final[Literal[":memory:"]] = ":memory:"
_MIGRATION_FILE = re.compile(r"(\d{4})_[a-z0-9_]+\.sql")


@dataclass(frozen=True, slots=True)
class Migration:
    version: int
    name: str
    sql: str


def load_migrations() -> list[Migration]:
    """The packaged migrations in order. Raises ValueError if their numbers have a gap."""
    folder = files(__package__ or __name__).joinpath("migrations")
    migrations = sorted(
        (
            Migration(int(match.group(1)), entry.name, entry.read_text(encoding="utf-8"))
            for entry in folder.iterdir()
            if (match := _MIGRATION_FILE.fullmatch(entry.name))
        ),
        key=lambda migration: migration.version,
    )
    versions = [migration.version for migration in migrations]
    if versions != list(range(1, len(versions) + 1)):
        raise ValueError(f"migrations must be numbered 1, 2, 3 ... without gaps, got {versions}")
    return migrations


def schema_version(connection: sqlite3.Connection) -> int:
    row = connection.execute("PRAGMA user_version").fetchone()
    return int(row[0])


def migrate(connection: sqlite3.Connection, migrations: list[Migration] | None = None) -> int:
    """Apply every migration newer than the database and return the resulting version.

    The connection must be in autocommit mode. Raises `DatabaseError` if the database is
    newer than this code or a migration fails; a failed migration leaves the previous version.
    """
    migrations = load_migrations() if migrations is None else migrations
    latest = migrations[-1].version if migrations else 0
    current = schema_version(connection)
    if current > latest:
        raise DatabaseError(
            f"The database has schema version {current}, but this learn-german only knows up to "
            f"{latest}. Upgrade learn-german."
        )
    for migration in migrations[current:]:
        logger.info("Applying database migration %s", migration.name)
        try:
            connection.executescript(
                f"BEGIN;\n{migration.sql}\nPRAGMA user_version = {migration.version};\nCOMMIT;"
            )
        except sqlite3.Error as exc:
            if connection.in_transaction:
                connection.execute("ROLLBACK")
            raise DatabaseError(f"Database migration {migration.name} failed: {exc}") from exc
    return latest


def open_database(location: Path | Literal[":memory:"]) -> sqlite3.Connection:
    """Open (creating if needed) and migrate the database. Raises `DatabaseError`."""
    if isinstance(location, Path):
        location.parent.mkdir(parents=True, exist_ok=True)
    try:
        connection = sqlite3.connect(location, autocommit=True)
    except sqlite3.Error as exc:
        raise _cannot_open(location, exc) from exc
    try:
        connection.execute("PRAGMA foreign_keys = ON")
        connection.execute("PRAGMA busy_timeout = 5000")
        migrate(connection)
    except sqlite3.Error as exc:
        connection.close()
        raise _cannot_open(location, exc) from exc
    except DatabaseError:
        connection.close()
        raise
    return connection


def _cannot_open(location: Path | str, exc: sqlite3.Error) -> DatabaseError:
    return DatabaseError(
        f"Cannot open the database at {location}: {exc}. Check that the file is a "
        "learn-german database and is writable, or set LEARN_GERMAN_DATABASE_PATH."
    )
