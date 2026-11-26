"""The per-run cap keeps the first N ranked chunks (R12)."""

import pytest

from learn_german.application.selection import cap
from tests.unit.selection.builders import DECISION, DISPOSAL, FORCE, pending

RANKED = [pending(DECISION), pending(DISPOSAL), pending(FORCE)]


@pytest.mark.parametrize(
    ("limit", "expected"),
    [
        pytest.param(0, [], id="zero"),
        pytest.param(2, RANKED[:2], id="fewer-than-candidates"),
        pytest.param(3, RANKED, id="exactly-all"),
        pytest.param(10, RANKED, id="more-than-candidates"),
    ],
)
def test_cap_keeps_the_first_items(limit: int, expected: list[object]) -> None:
    assert cap(RANKED, limit) == expected


def test_cap_of_nothing_is_empty() -> None:
    assert cap([], 10) == []


def test_cap_rejects_a_negative_limit() -> None:
    with pytest.raises(ValueError, match="0 or more"):
        cap(RANKED, -1)
