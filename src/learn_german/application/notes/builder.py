"""`NoteBuilder`: one chunk's card content becomes its two notes (0012, 0028).

The field names are the ones in docs/learning-design/note-types.md. The Anki adapter holds
the same names in its note type specs; a test checks that the two agree.
"""

from collections.abc import Sequence
from dataclasses import dataclass
from typing import Final, Self

from learn_german.application.notes.tags import run_tags
from learn_german.domain.models import (
    CHUNK_KEY_FIELD,
    CardContent,
    CardRequest,
    NoteDraft,
    NoteKind,
    RunId,
)

CHUNK_FIELD: Final = "Chunk"
MEANING_FIELD: Final = "Meaning"
ANSWER_FIELD: Final = "Answer"
PROMPT_FIELD: Final = "Prompt"
HINT_LANGUAGE_FIELD: Final = "HintLanguage"


@dataclass(frozen=True, slots=True)
class NoteBuilder:
    """Builds the notes of one run, all carrying the run's tags (R22)."""

    tags: tuple[str, ...]

    @classmethod
    def for_run(cls, *, provider: str, model: str, run_id: RunId) -> Self:
        """A builder whose notes are tagged with the provider, model and run ID.

        Raises ValueError if the provider or model is blank.
        """
        return cls(run_tags(provider=provider, model=model, run_id=run_id))

    def build(
        self,
        request: CardRequest,
        content: CardContent,
        kinds: Sequence[NoteKind] = tuple(NoteKind),
    ) -> tuple[NoteDraft, ...]:
        """The chunk's notes of the given kinds, in the given order; both kinds by default.

        `sync` passes the chunk's missing kinds, so a chunk with one note gets only the other.
        """
        return tuple(self._draft(kind, request, content) for kind in kinds)

    def _draft(self, kind: NoteKind, request: CardRequest, content: CardContent) -> NoteDraft:
        shared = (
            (CHUNK_KEY_FIELD, request.key.value),
            (CHUNK_FIELD, content.citation_form),
            (MEANING_FIELD, content.meaning),
            (ANSWER_FIELD, content.shortened_sentence),
        )
        extra: tuple[tuple[str, str], ...]
        match kind:
            case NoteKind.TRANSFORMATION:
                extra = ((PROMPT_FIELD, content.verbal_rewrite),)
            case NoteKind.TRANSLATION:
                extra = (
                    (PROMPT_FIELD, content.translation),
                    (HINT_LANGUAGE_FIELD, request.hint_language),
                )
        return NoteDraft(note_kind=kind, key=request.key, fields=shared + extra, tags=self.tags)
