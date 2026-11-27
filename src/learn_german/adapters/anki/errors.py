"""Errors of the Anki adapter, as subclasses of the domain errors (0026)."""

from learn_german.domain.errors import FatalError


class AnkiActionError(FatalError):
    """AnkiConnect answered an action with an error, or with a result of the wrong shape.

    Fatal by default, because a failing setup or search action fails the same way on every
    retry. The gateway narrows it to a `PushError` where only one note is affected (0040).
    """

    def __init__(self, action: str, detail: str) -> None:
        super().__init__(
            f"AnkiConnect action {action!r} failed: {detail}. Check that Anki shows no open "
            "dialog and that AnkiConnect's apiKey is null (Tools, Add-ons, AnkiConnect, "
            "Config), then run the command again."
        )
        self.action = action
        self.detail = detail
