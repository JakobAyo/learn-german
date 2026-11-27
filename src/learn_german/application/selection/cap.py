"""The per-run cap (R12, 0012): it counts chunks, not notes."""

from collections.abc import Sequence


def cap[T](ranked: Sequence[T], limit: int) -> list[T]:
    """The first `limit` items of an already ranked sequence, or all of them if fewer.

    Raises ValueError if `limit` is negative.
    """
    if limit < 0:
        raise ValueError(f"the cap must be 0 or more, got {limit}")
    return list(ranked[:limit])
