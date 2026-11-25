"""Migrations and database files on disk."""

import sqlite3
from pathlib import Path

import pytest

from learn_german.adapters.storage.sqlite import SqliteUnitOfWork, open_database
from learn_german.adapters.storage.sqlite.database import (
    Migration,
    load_migrations,
    migrate,
    schema_version,
)
from learn_german.domain.errors import DatabaseError
from learn_german.domain.models import (
    Candidate,
    ChunkKey,
    ChunkKind,
    ChunkStatus,
    NoteKind,
    RunId,
    Source,
    SourceKind,
)
from tests.fakes.clock import DEFAULT_NOW

MIGRATIONS = load_migrations()
LATEST = len(MIGRATIONS)
TABLES = {"sources", "candidates", "pushed_notes", "chunk_errors", "llm_cache"}


def _raw(path: Path) -> sqlite3.Connection:
    return sqlite3.connect(path, autocommit=True)


def _tables(connection: sqlite3.Connection) -> set[str]:
    rows = connection.execute("SELECT name FROM sqlite_schema WHERE type = 'table'")
    return {str(row[0]) for row in rows}


def test_migrations_are_numbered_without_gaps() -> None:
    assert [m.version for m in MIGRATIONS] == list(range(1, LATEST + 1))


def test_migrations_bring_empty_database_to_latest(tmp_path: Path) -> None:
    connection = open_database(tmp_path / "a" / "b" / "lg.db")

    assert schema_version(connection) == LATEST
    assert _tables(connection) >= TABLES


def test_migrations_run_again_is_a_no_op(tmp_path: Path) -> None:
    path = tmp_path / "lg.db"
    first = open_database(path)
    first.execute("INSERT INTO llm_cache VALUES ('k', 'p', 'm', '1', 'r', 't')")
    first.close()

    second = open_database(path)

    assert schema_version(second) == LATEST
    assert second.execute("SELECT count(*) FROM llm_cache").fetchone()[0] == 1


@pytest.mark.parametrize("migration", MIGRATIONS, ids=[m.name for m in MIGRATIONS])
def test_each_migration_applies_to_previous_version(tmp_path: Path, migration: Migration) -> None:
    connection = _raw(tmp_path / "lg.db")
    migrate(connection, MIGRATIONS[: migration.version - 1])

    assert migrate(connection, MIGRATIONS[: migration.version]) == migration.version
    assert schema_version(connection) == migration.version


def test_failed_migration_keeps_previous_version(tmp_path: Path) -> None:
    connection = _raw(tmp_path / "lg.db")
    broken = Migration(LATEST + 1, "9999_broken.sql", "CREATE TABLE half (a);\nNOT SQL;")

    with pytest.raises(DatabaseError, match=r"9999_broken\.sql"):
        migrate(connection, [*MIGRATIONS, broken])

    assert schema_version(connection) == LATEST
    assert "half" not in _tables(connection)


def test_database_newer_than_code_is_refused(tmp_path: Path) -> None:
    path = tmp_path / "lg.db"
    _raw(path).execute(f"PRAGMA user_version = {LATEST + 1}")

    with pytest.raises(DatabaseError, match="Upgrade learn-german"):
        open_database(path)


def test_file_that_is_not_a_database_is_refused(tmp_path: Path) -> None:
    path = tmp_path / "lg.db"
    path.write_bytes(b"this is not sqlite" * 100)

    with pytest.raises(DatabaseError, match="Cannot open the database"):
        open_database(path)


def test_directory_as_database_path_is_refused(tmp_path: Path) -> None:
    with pytest.raises(DatabaseError, match="Cannot open the database"):
        open_database(tmp_path)


def test_foreign_keys_are_enforced(tmp_path: Path) -> None:
    connection = open_database(tmp_path / "lg.db")

    with pytest.raises(sqlite3.IntegrityError):
        connection.execute(
            "INSERT INTO candidates (source_id, chunk_key, kind, sentence, context) "
            "VALUES (1, 'rolle|spielen', 'nvv', 's', 'c')"
        )


def test_full_domain_model_survives_reopening(tmp_path: Path) -> None:
    """M1 done-when: everything is stored and loaded through the unit of work."""
    path = tmp_path / "lg.db"
    key = ChunkKey("verfügung|zu|stellen")
    source = Source(
        ref="https://example.org/artikel",
        kind=SourceKind.NEWS_URL,
        title="Erfunden",
        fetched_at=DEFAULT_NOW,
        content_hash="h1",
        text="Die Stadt stellte Räume zur Verfügung.",
    )
    candidate = Candidate(key, ChunkKind.NVV, source.text, source.text)
    writer = SqliteUnitOfWork(open_database(path))
    with writer:
        source_id = writer.sources.add(source)
        writer.candidates.add_all(source_id, [candidate])
        writer.chunk_states.record_pushed(
            key, NoteKind.TRANSFORMATION, run_id=RunId("run-20261124-1530"), at=DEFAULT_NOW
        )
        writer.chunk_states.record_error(key, "Übersetzung fehlte", at=DEFAULT_NOW)
        writer.llm_cache.put(
            "k1", "{}", provider="anthropic", model="m", prompt_version="1", created_at=DEFAULT_NOW
        )
    writer.close()

    reader = SqliteUnitOfWork(open_database(path))
    with reader:
        state = reader.chunk_states.get(key)
        assert reader.sources.all() == [(source_id, source)]
        assert reader.candidates.for_key(key) == [candidate]
        assert state.status is ChunkStatus.PARTIAL
        assert state.missing == {NoteKind.TRANSLATION}
        assert state.last_error is not None
        assert state.last_error.failed_at == DEFAULT_NOW
        assert reader.llm_cache.get("k1") == "{}"
    reader.close()
