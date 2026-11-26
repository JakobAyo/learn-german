"""`configure_logging` and the secret filter (0048)."""

import logging

import pytest

from learn_german.cli.logs import REDACTED, RedactSecrets, configure_logging

KEY = "sk-ant-api03-abcDEF_123-xyz"


def _record(msg: str, *args: object, exc: BaseException | None = None) -> logging.LogRecord:
    exc_info = (type(exc), exc, exc.__traceback__) if exc is not None else None
    return logging.LogRecord("learn_german.test", logging.WARNING, __file__, 1, msg, args, exc_info)


def test_redact_secrets_masks_a_key_in_the_message_and_its_arguments() -> None:
    record = _record("calling with %s and " + KEY, KEY)

    assert RedactSecrets().filter(record)

    assert record.getMessage() == f"calling with {REDACTED} and {REDACTED}"


def test_redact_secrets_masks_a_key_in_a_traceback() -> None:
    try:
        raise RuntimeError(f"bad key {KEY}")
    except RuntimeError as exc:
        record = _record("failed", exc=exc)

    RedactSecrets().filter(record)
    text = logging.Formatter().format(record)

    assert KEY not in text
    assert REDACTED in text
    assert "RuntimeError" in text


def test_redact_secrets_leaves_other_messages_alone() -> None:
    record = _record("Calling Claude %s", "claude-opus-5-5")

    RedactSecrets().filter(record)

    assert record.msg == "Calling Claude %s"
    assert record.args == ("claude-opus-5-5",)


@pytest.mark.parametrize(("verbose", "level"), [(False, logging.WARNING), (True, logging.DEBUG)])
def test_configure_logging_sets_the_package_level(verbose: bool, level: int) -> None:
    configure_logging(verbose=verbose)

    assert logging.getLogger("learn_german.adapters.llm").getEffectiveLevel() == level
    assert logging.getLogger("httpx2").getEffectiveLevel() == logging.WARNING
    assert logging.getLogger("anthropic").getEffectiveLevel() == logging.WARNING


def test_configure_logging_twice_installs_one_handler() -> None:
    before = len(logging.getLogger().handlers)

    configure_logging(verbose=True)
    configure_logging(verbose=False)

    assert len(logging.getLogger().handlers) == before + 1


def test_warnings_reach_stderr_without_verbose(capsys: pytest.CaptureFixture[str]) -> None:
    configure_logging(verbose=False)

    logging.getLogger("learn_german.test").warning("Skipping %s", KEY)
    logging.getLogger("learn_german.test").debug("hidden")

    err = capsys.readouterr().err
    assert f"WARNING: Skipping {REDACTED}" in err
    assert "hidden" not in err
