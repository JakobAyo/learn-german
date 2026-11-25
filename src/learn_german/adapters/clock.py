"""The real clock. Tests use `tests.fakes.clock.FixedClock` instead."""

from datetime import UTC, datetime


class SystemClock:
    """Implements `ports.Clock` with the system time in UTC."""

    def now(self) -> datetime:
        return datetime.now(UTC)
