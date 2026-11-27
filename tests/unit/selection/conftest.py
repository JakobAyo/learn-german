"""Fixtures for selection tests: a unit of work over an in-memory SQLite database."""

from collections.abc import Iterator

import pytest

from learn_german.adapters.storage.sqlite import MEMORY, SqliteUnitOfWork, open_database


@pytest.fixture
def uow() -> Iterator[SqliteUnitOfWork]:
    unit_of_work = SqliteUnitOfWork(open_database(MEMORY))
    yield unit_of_work
    unit_of_work.close()
