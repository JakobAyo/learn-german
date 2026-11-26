"""NLP adapter: the spaCy-based Nomen-Verb-Verbindung extractor (R8, 0011).

`parse` is the only module that touches spaCy. `match` and `keys` work on `TokenView`s,
so the hard rules are unit-tested without the model. See docs/system-design/nvv-extraction.md.
"""

from learn_german.adapters.nlp.extractor import NvvExtractor

__all__ = ["NvvExtractor"]
