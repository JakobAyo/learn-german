"""SQLite implementations of the repository ports. Transactions belong to the unit of work."""

import sqlite3
from collections.abc import Iterable
from datetime import UTC, datetime
from typing import Any

from learn_german.domain.errors import DuplicateSourceError
from learn_german.domain.models import (
    Candidate,
    ChunkError,
    ChunkKey,
    ChunkKind,
    ChunkState,
    NoteKind,
    RunId,
    Source,
    SourceId,
    SourceKind,
)


def _to_text(at: datetime) -> str:
    # astimezone() would read a naive time as local time and shift it silently.
    if at.tzinfo is None or at.utcoffset() is None:
        raise ValueError(f"time {at.isoformat()} must be timezone-aware; use the injected Clock")
    return at.astimezone(UTC).isoformat()


def _from_text(value: str) -> datetime:
    return datetime.fromisoformat(value)


class SqliteSourceRepository:
    """Sources in the `sources` table, unique by ref and by content hash."""

    _COLUMNS = "ref, kind, title, fetched_at, content_hash, text"

    def __init__(self, connection: sqlite3.Connection) -> None:
        self._connection = connection

    def add(self, source: Source) -> SourceId:
        """Raises `DuplicateSourceError` if a source with the same ref or hash is stored."""
        try:
            cursor = self._connection.execute(
                f"INSERT INTO sources ({self._COLUMNS}) VALUES (?, ?, ?, ?, ?, ?)",  # noqa: S608
                (
                    source.ref,
                    source.kind.value,
                    source.title,
                    _to_text(source.fetched_at),
                    source.content_hash,
                    source.text,
                ),
            )
        except sqlite3.IntegrityError as exc:
            raise DuplicateSourceError(
                f"{source.ref} is already stored (same address or same text), "
                "so its chunks are already in the database. Nothing to do."
            ) from exc
        return SourceId(_last_row_id(cursor))

    def get(self, source_id: SourceId) -> Source | None:
        row = self._connection.execute(
            f"SELECT {self._COLUMNS} FROM sources WHERE id = ?",  # noqa: S608
            (source_id,),
        ).fetchone()
        return None if row is None else self._source(row)

    def find_id(self, *, ref: str, content_hash: str) -> SourceId | None:
        row = self._connection.execute(
            "SELECT id FROM sources WHERE ref = ? OR content_hash = ? ORDER BY id LIMIT 1",
            (ref, content_hash),
        ).fetchone()
        return None if row is None else SourceId(int(row[0]))

    def all(self) -> list[tuple[SourceId, Source]]:
        rows = self._connection.execute(
            f"SELECT id, {self._COLUMNS} FROM sources ORDER BY id"  # noqa: S608
        )
        return [(SourceId(int(row[0])), self._source(row[1:])) for row in rows]

    @staticmethod
    def _source(row: tuple[Any, ...]) -> Source:
        ref, kind, title, fetched_at, content_hash, text = row
        return Source(
            ref=str(ref),
            kind=SourceKind(kind),
            title=None if title is None else str(title),
            fetched_at=_from_text(fetched_at),
            content_hash=str(content_hash),
            text=str(text),
        )


class SqliteCandidateRepository:
    """Chunk occurrences in the `candidates` table, unique by source, key and sentence."""

    def __init__(self, connection: sqlite3.Connection) -> None:
        self._connection = connection

    def add_all(self, source_id: SourceId, candidates: Iterable[Candidate]) -> None:
        self._connection.executemany(
            """
            INSERT INTO candidates (source_id, chunk_key, kind, sentence, context)
            VALUES (?, ?, ?, ?, ?)
            ON CONFLICT (source_id, chunk_key, sentence)
            DO UPDATE SET kind = excluded.kind, context = excluded.context
            """,
            ((source_id, c.key.value, c.kind.value, c.sentence, c.context) for c in candidates),
        )

    def for_source(self, source_id: SourceId) -> list[Candidate]:
        return self._select("source_id = ?", source_id)

    def for_key(self, key: ChunkKey) -> list[Candidate]:
        return self._select("chunk_key = ?", key.value)

    def _select(self, where: str, value: object) -> list[Candidate]:
        rows = self._connection.execute(
            f"SELECT chunk_key, kind, sentence, context FROM candidates WHERE {where} ORDER BY id",  # noqa: S608
            (value,),
        )
        return [
            Candidate(
                key=ChunkKey(str(key)),
                kind=ChunkKind(kind),
                sentence=str(sentence),
                context=str(context),
            )
            for key, kind, sentence, context in rows
        ]


class SqliteChunkStateRepository:
    """Per-chunk progress in `pushed_notes` and `chunk_errors`."""

    def __init__(self, connection: sqlite3.Connection) -> None:
        self._connection = connection

    def get(self, key: ChunkKey) -> ChunkState:
        pushed = frozenset(
            NoteKind(row[0])
            for row in self._connection.execute(
                "SELECT note_kind FROM pushed_notes WHERE chunk_key = ?", (key.value,)
            )
        )
        row = self._connection.execute(
            "SELECT message, failed_at FROM chunk_errors WHERE chunk_key = ?", (key.value,)
        ).fetchone()
        error = None if row is None else ChunkError(str(row[0]), _from_text(row[1]))
        return ChunkState(key=key, pushed=pushed, last_error=error)

    def record_pushed(
        self, key: ChunkKey, note_kind: NoteKind, *, run_id: RunId, at: datetime
    ) -> None:
        self._connection.execute(
            """
            INSERT INTO pushed_notes (chunk_key, note_kind, run_id, pushed_at)
            VALUES (?, ?, ?, ?)
            ON CONFLICT (chunk_key, note_kind)
            DO UPDATE SET run_id = excluded.run_id, pushed_at = excluded.pushed_at
            """,
            (key.value, note_kind.value, run_id.value, _to_text(at)),
        )

    def record_error(self, key: ChunkKey, message: str, *, at: datetime) -> None:
        self._connection.execute(
            """
            INSERT INTO chunk_errors (chunk_key, message, failed_at) VALUES (?, ?, ?)
            ON CONFLICT (chunk_key)
            DO UPDATE SET message = excluded.message, failed_at = excluded.failed_at
            """,
            (key.value, message, _to_text(at)),
        )

    def clear_error(self, key: ChunkKey) -> None:
        self._connection.execute("DELETE FROM chunk_errors WHERE chunk_key = ?", (key.value,))


class SqliteLLMCacheRepository:
    """Raw LLM responses in `llm_cache`, keyed by the caching decorator's hash."""

    def __init__(self, connection: sqlite3.Connection) -> None:
        self._connection = connection

    def get(self, cache_key: str) -> str | None:
        row = self._connection.execute(
            "SELECT response FROM llm_cache WHERE cache_key = ?", (cache_key,)
        ).fetchone()
        return None if row is None else str(row[0])

    def put(
        self,
        cache_key: str,
        response: str,
        *,
        provider: str,
        model: str,
        prompt_version: str,
        created_at: datetime,
    ) -> None:
        self._connection.execute(
            """
            INSERT OR REPLACE INTO llm_cache
                (cache_key, provider, model, prompt_version, response, created_at)
            VALUES (?, ?, ?, ?, ?, ?)
            """,
            (cache_key, provider, model, prompt_version, response, _to_text(created_at)),
        )


def _last_row_id(cursor: sqlite3.Cursor) -> int:
    if cursor.lastrowid is None:  # pragma: no cover - sqlite always sets it after an INSERT
        raise RuntimeError("INSERT did not report a row id")
    return cursor.lastrowid
