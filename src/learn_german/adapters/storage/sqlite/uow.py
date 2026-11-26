"""Unit of work over one SQLite connection."""

import logging
import sqlite3
from types import TracebackType
from typing import Self

from learn_german.adapters.storage.sqlite.repositories import (
    SqliteCandidateRepository,
    SqliteChunkStateRepository,
    SqliteLLMCacheRepository,
    SqliteSourceRepository,
)
from learn_german.domain.errors import DatabaseError

logger = logging.getLogger(__name__)

_RETRY = (
    "Check that the disk has space and that no other learn-german command is running, then "
    "run the command again."
)


class SqliteUnitOfWork:
    """One transaction per `with` block across all repositories (see `ports.UnitOfWork`).

    The connection must come from `open_database`, which puts it in autocommit mode so this
    class controls transactions explicitly. The block commits on normal exit and rolls back
    if it raises. Raises `DatabaseError` if the commit fails or the block raised a SQLite
    error, and `RuntimeError` if blocks are nested.
    """

    def __init__(self, connection: sqlite3.Connection) -> None:
        self._connection = connection
        self.sources = SqliteSourceRepository(connection)
        self.candidates = SqliteCandidateRepository(connection)
        self.chunk_states = SqliteChunkStateRepository(connection)
        self.llm_cache = SqliteLLMCacheRepository(connection)

    def __enter__(self) -> Self:
        if self._connection.in_transaction:
            raise RuntimeError("a unit of work is already active on this connection")
        # IMMEDIATE takes the write lock now. A deferred BEGIN that reads and then writes can
        # get "database is locked" at once, without busy_timeout, when another command writes.
        self._connection.execute("BEGIN IMMEDIATE")
        return self

    def __exit__(
        self,
        exc_type: type[BaseException] | None,
        exc: BaseException | None,
        tb: TracebackType | None,
    ) -> None:
        if exc is not None:
            self._rollback()
            if isinstance(exc, sqlite3.Error):
                raise DatabaseError(
                    f"A database write failed and was undone: {exc}. {_RETRY}"
                ) from exc
            return
        try:
            self._connection.execute("COMMIT")
        except sqlite3.Error as commit_exc:
            self._rollback()
            raise DatabaseError(
                f"Saving to the database failed: {commit_exc}. {_RETRY}"
            ) from commit_exc

    def _rollback(self) -> None:
        # After disk-full, I/O errors or interrupts SQLite has already rolled back by itself,
        # and a second ROLLBACK would raise and hide the original error.
        if not self._connection.in_transaction:
            return
        try:
            self._connection.execute("ROLLBACK")
        except sqlite3.Error:
            logger.warning("Rollback failed after an earlier error", exc_info=True)

    def close(self) -> None:
        """Close the connection. Call once, when the command ends."""
        self._connection.close()
