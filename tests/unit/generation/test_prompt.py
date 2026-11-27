"""The card prompt: golden rendering and the template hash per PROMPT_VERSION (0035).

When the template changes on purpose: bump PROMPT_VERSION, add the new template file, record
its SHA-256 in tests/data/llm/prompt_hashes.json and update the golden file by hand.
"""

import hashlib
import json
from pathlib import Path

import pytest

from learn_german.adapters.llm import PROMPT_VERSION, load_template, render_prompt
from tests.unit.generation.builders import REQUEST, request

DATA = Path(__file__).parent.parent.parent / "data" / "llm"
GOLDEN_FILE = DATA / "card_v2_prompt.golden.txt"
HASHES_FILE = DATA / "prompt_hashes.json"


def test_rendered_prompt_matches_the_golden_file() -> None:
    expected = GOLDEN_FILE.read_text(encoding="utf-8")

    assert render_prompt(load_template(), REQUEST) == expected


def test_template_hash_is_recorded_for_the_current_version() -> None:
    recorded: dict[str, str] = json.loads(HASHES_FILE.read_text(encoding="utf-8"))
    digest = hashlib.sha256(load_template().encode("utf-8")).hexdigest()

    assert PROMPT_VERSION in recorded, f"record the hash of {PROMPT_VERSION} in {HASHES_FILE}"
    assert recorded[PROMPT_VERSION] == digest, (
        f"The template of {PROMPT_VERSION} changed. Cached answers would no longer match "
        "the prompt: bump PROMPT_VERSION and record the new hash."
    )


def test_empty_context_renders_as_none() -> None:
    rendered = render_prompt(load_template(), request(context="  "))

    assert "<context>\n(none)\n</context>" in rendered


def test_sentence_and_context_are_inserted_verbatim() -> None:
    rendered = render_prompt("$sentence|$context|$key", REQUEST)

    assert rendered == f"{REQUEST.sentence}|{REQUEST.context}|entscheidung|treffen"


def test_dollar_signs_in_the_request_are_kept() -> None:
    rendered = render_prompt("$sentence", request(sentence="Es kostet $5 und ${x}."))

    assert rendered == "Es kostet $5 und ${x}."


def test_unknown_placeholder_raises() -> None:
    with pytest.raises(KeyError):
        render_prompt("$unknown", REQUEST)


def test_the_prompt_no_longer_asks_for_a_translation() -> None:
    template = load_template()

    assert "$hint_language" not in template
    assert "translation" not in template


def test_unknown_version_raises() -> None:
    with pytest.raises(KeyError):
        load_template("card-v1")
