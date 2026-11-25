from datetime import datetime, timedelta, timezone

import pytest

from learn_german.adapters.clock import SystemClock
from learn_german.domain.models import RunId
from learn_german.ports import Clock
from tests.fakes.clock import FixedClock


def test_run_id_from_fixed_clock_uses_utc_minute() -> None:
    clock: Clock = FixedClock()

    assert RunId.from_datetime(clock.now()) == RunId("run-20261124-1530")


def test_run_id_converts_other_timezones_to_utc() -> None:
    vienna_winter = timezone(timedelta(hours=1))

    run_id = RunId.from_datetime(datetime(2026, 11, 25, 0, 15, tzinfo=vienna_winter))

    assert run_id.value == "run-20261124-2315"


def test_run_id_rejects_naive_time() -> None:
    with pytest.raises(ValueError, match="timezone-aware"):
        RunId.from_datetime(datetime(2026, 11, 24, 15, 30))


@pytest.mark.parametrize(
    "value",
    [
        pytest.param("20261124-1530", id="no-prefix"),
        pytest.param("run-2026112-1530", id="short-date"),
        pytest.param("run-20261124-153", id="short-time"),
        pytest.param("run-20261124-1530 ", id="trailing-space"),
        pytest.param("run-20261340-1530", id="impossible-date"),
        pytest.param("run-20261124-2599", id="impossible-time"),
    ],
)
def test_run_id_rejects_malformed_values(value: str) -> None:
    with pytest.raises(ValueError, match="run ID"):
        RunId(value)


def test_run_id_str_is_its_value() -> None:
    assert str(RunId("run-20261124-1530")) == "run-20261124-1530"


def test_system_clock_returns_aware_utc_time() -> None:
    now = SystemClock().now()

    assert now.utcoffset() == timedelta(0)


def test_fixed_clock_advances_on_request() -> None:
    clock = FixedClock()
    start = clock.now()

    clock.advance(timedelta(minutes=5))

    assert clock.now() - start == timedelta(minutes=5)
