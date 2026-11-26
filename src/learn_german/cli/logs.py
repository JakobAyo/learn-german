"""Logging setup for the CLI (0048): warnings by default, debug lines with `--verbose`.

Only the `learn_german` loggers go down to DEBUG. Third-party loggers (httpx2, anthropic,
trafilatura) stay at WARNING even with `--verbose`, because their debug output can carry
request details. Every record passes `RedactSecrets` before it is written.
"""

import logging
import re
import sys
from typing import Final

PACKAGE_LOGGER: Final = "learn_german"

_QUIET_FORMAT: Final = "%(levelname)s: %(message)s"
_VERBOSE_FORMAT: Final = "%(levelname)s %(name)s: %(message)s"

_SECRET: Final = re.compile(r"sk-ant-[A-Za-z0-9_-]+")
"""Anthropic API keys (and admin keys) all start with `sk-ant-`."""
REDACTED: Final = "sk-ant-[redacted]"


class RedactSecrets(logging.Filter):
    """Replaces anything that looks like an Anthropic API key in a record's final message.

    A backstop: no learn-german log line includes a key, but an exception text from a
    library might.
    """

    def filter(self, record: logging.LogRecord) -> bool:
        message = record.getMessage()
        if _SECRET.search(message):
            record.msg = _SECRET.sub(REDACTED, message)
            record.args = None
        if record.exc_info and record.exc_info[1] is not None:
            # Formatted here, so the traceback text can be redacted as well.
            text = logging.Formatter().formatException(record.exc_info)
            record.exc_text = _SECRET.sub(REDACTED, text)
            record.exc_info = None
        return True


class _StderrHandler(logging.Handler):
    """Writes to whatever `sys.stderr` is at the time, like `logging.lastResort`.

    Looking the stream up per record keeps output going to typer's test runner, which
    swaps `sys.stderr` for each invocation.
    """

    def emit(self, record: logging.LogRecord) -> None:
        try:
            sys.stderr.write(self.format(record) + "\n")
        except Exception:  # noqa: BLE001 - logging must never crash the command
            self.handleError(record)


def configure_logging(*, verbose: bool) -> None:
    """Install the one stderr handler on the root logger, replacing an earlier one.

    Without `verbose`, warnings and errors of every logger are shown, as Python's default
    does. With it, the `learn_german` loggers also show INFO and DEBUG lines.
    """
    root = logging.getLogger()
    for handler in [h for h in root.handlers if isinstance(h, _StderrHandler)]:
        root.removeHandler(handler)
    handler = _StderrHandler()
    handler.setFormatter(logging.Formatter(_VERBOSE_FORMAT if verbose else _QUIET_FORMAT))
    handler.addFilter(RedactSecrets())
    root.addHandler(handler)
    root.setLevel(logging.WARNING)
    logging.getLogger(PACKAGE_LOGGER).setLevel(logging.DEBUG if verbose else logging.NOTSET)
