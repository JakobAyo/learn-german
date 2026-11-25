"""Deliberate failing test for the M0 'broken PR is blocked' check. Never merge."""


def test_fails_on_purpose() -> None:
    assert 1 + 1 == 3
