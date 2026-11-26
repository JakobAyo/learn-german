"""Selection: which pending chunks a sync generates cards for, and from which sentence.

Pending chunks from storage pass a filter chain (R11, R14), are ranked (R13), capped (R12),
and get one occurrence picked to feed the cards (0032). See docs/system-design/pipeline.md.
"""

from learn_german.application.selection.cap import cap
from learn_german.application.selection.filters import AlreadyInDeckFilter, FilterChain
from learn_german.application.selection.picker import ShortestSentencePicker
from learn_german.application.selection.ranking import OccurrenceRanker
from learn_german.application.selection.selector import ChunkSelector, SelectedChunk

__all__ = [
    "AlreadyInDeckFilter",
    "ChunkSelector",
    "FilterChain",
    "OccurrenceRanker",
    "SelectedChunk",
    "ShortestSentencePicker",
    "cap",
]
