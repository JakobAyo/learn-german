from datetime import UTC, datetime, timedelta

DEFAULT_NOW = datetime(2026, 11, 24, 15, 30, 12, tzinfo=UTC)


class FixedClock:
    """Implements `ports.Clock` with a time that changes only when the test says so."""

    def __init__(self, now: datetime = DEFAULT_NOW) -> None:
        self._now = now

    def now(self) -> datetime:
        return self._now

    def advance(self, delta: timedelta) -> None:
        self._now += delta
