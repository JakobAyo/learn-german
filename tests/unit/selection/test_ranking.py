"""OccurrenceRanker: partial chunks first, then most occurrences, then by key (0034)."""

from itertools import permutations

import pytest

from learn_german.application.selection import OccurrenceRanker
from learn_german.domain.models import NoteKind
from learn_german.ports import Ranker
from tests.unit.selection.builders import DECISION, DISPOSAL, FORCE, ROLE, pending

RANKER: Ranker = OccurrenceRanker()


def test_occurrence_ranker_puts_most_frequent_first() -> None:
    chunks = [pending(DECISION, 1), pending(DISPOSAL, 5), pending(FORCE, 3)]

    assert [c.key for c in RANKER.rank(chunks)] == [DISPOSAL, FORCE, DECISION]


@pytest.mark.parametrize(
    "order", list(permutations(range(3))), ids=lambda order: "".join(map(str, order))
)
def test_occurrence_ranker_breaks_ties_by_key_whatever_the_input_order(
    order: tuple[int, ...],
) -> None:
    tied = [pending(ROLE, 2), pending(DECISION, 2), pending(FORCE, 2)]

    ranked = RANKER.rank([tied[index] for index in order])

    assert [c.key for c in ranked] == [DECISION, FORCE, ROLE]


def test_occurrence_ranker_puts_partial_chunks_before_new_ones() -> None:
    partial = pending(ROLE, 1, missing=[NoteKind.TRANSLATION])
    chunks = [pending(DECISION, 7), partial, pending(FORCE, 3)]

    assert [c.key for c in RANKER.rank(chunks)] == [ROLE, DECISION, FORCE]


def test_occurrence_ranker_ranks_partial_chunks_by_occurrences_too() -> None:
    chunks = [
        pending(DECISION, 1, missing=[NoteKind.TRANSFORMATION]),
        pending(FORCE, 4, missing=[NoteKind.TRANSLATION]),
    ]

    assert [c.key for c in RANKER.rank(chunks)] == [FORCE, DECISION]


def test_occurrence_ranker_keeps_the_chunks_unchanged() -> None:
    chunks = [pending(DECISION, 1), pending(FORCE, 2, missing=[NoteKind.TRANSLATION])]

    assert sorted(RANKER.rank(chunks), key=lambda c: c.key.value) == chunks


def test_occurrence_ranker_of_nothing_is_empty() -> None:
    assert RANKER.rank([]) == []
