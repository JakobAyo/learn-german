"""Error hierarchy that puts the partial-failure rules of 0014 into the type system.

`FatalError` means every further step would fail: stop the command at once.
`ItemError` means only this source or chunk failed: record it and continue.
Adapters wrap third-party exceptions in one of these with `raise ... from exc`.
"""


class LearnGermanError(Exception):
    """Base of every error the tool raises on purpose. The message tells the user what to do."""


class FatalError(LearnGermanError):
    """Every further step would fail, so the command stops and exits with code 2."""


class ItemError(LearnGermanError):
    """Only one source or chunk failed; the command records it, continues and exits with code 1."""


class ConfigError(FatalError):
    """A setting is missing or invalid."""


class MissingCredentialsError(FatalError):
    """An API key that the requested step needs is not set."""


class DatabaseError(FatalError):
    """The local database cannot be opened, migrated or written."""


class DuplicateSourceError(ItemError):
    """A source with the same reference or content hash is already stored (R6)."""
