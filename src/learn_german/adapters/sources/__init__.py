"""Source adapters: local `.txt` files and news article URLs (R4, R5, 0013).

See docs/system-design/ingest.md.
"""

from learn_german.adapters.sources.local_file import LocalFileSource
from learn_german.adapters.sources.news_url import NewsUrlSource
from learn_german.adapters.sources.text import content_hash, normalise_text

__all__ = ["LocalFileSource", "NewsUrlSource", "content_hash", "normalise_text"]
