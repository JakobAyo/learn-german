"""Run tags that make a bad batch findable in Anki (R22, 0005)."""

import pytest

from learn_german.application.notes import TOOL_TAG, run_tags
from tests.unit.notes.samples import RUN


def test_run_tags_name_tool_provider_model_and_run() -> None:
    assert run_tags(provider="anthropic", model="claude-opus-5-5", run_id=RUN) == (
        "learn-german",
        "provider::anthropic",
        "model::claude-opus-5-5",
        "run::run-20261124-1530",
    )
    assert TOOL_TAG == "learn-german"


def test_run_tags_replace_whitespace_because_anki_splits_tags_on_it() -> None:
    tags = run_tags(provider=" local llm ", model="model\tone  two", run_id=RUN)

    assert tags[1:3] == ("provider::local_llm", "model::model_one_two")


@pytest.mark.parametrize(("provider", "model"), [("", "m"), ("p", "  ")], ids=["provider", "model"])
def test_run_tags_reject_a_blank_name(provider: str, model: str) -> None:
    with pytest.raises(ValueError, match="must not be blank"):
        run_tags(provider=provider, model=model, run_id=RUN)
