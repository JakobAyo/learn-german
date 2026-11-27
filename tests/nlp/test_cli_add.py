"""`add` and `status` on the fixture article with the real NVV extractor (roadmap M3 done-when)."""

import shutil
from pathlib import Path

import pytest
from typer.testing import CliRunner

from learn_german.adapters.nlp import NvvExtractor
from learn_german.bootstrap import Overrides
from learn_german.cli.app import create_app

pytestmark = pytest.mark.nlp

ARTICLE = Path(__file__).parent.parent / "data" / "sources" / "artikel.txt"


def test_add_fixture_article_stores_candidates_that_status_lists(
    nvv_extractor: NvvExtractor,
) -> None:
    shutil.copy(ARTICLE, "artikel.txt")
    app = create_app(Overrides(extractors=[nvv_extractor]))
    runner = CliRunner()

    added = runner.invoke(app, ["add", "artikel.txt"])
    status = runner.invoke(app, ["status"])

    assert added.exit_code == 0, added.output
    assert "added" in added.stdout
    assert status.exit_code == 0, status.output
    for key in ("entscheidung|treffen", "stellung|nehmen", "kritik|üben", "verfügung|zu|stellen"):
        assert key in status.stdout
