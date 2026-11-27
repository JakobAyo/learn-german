"""Run the card prompt on a handful of chunks against the real Claude API, for manual review.

Costs money and needs ANTHROPIC_API_KEY, so it never runs in CI or in the test suite. Each
chunk's card content and the sanity-check problems are written as one JSON line; nothing is
cached, so every run asks again.

    uv run python tools/eval/run_eval.py [--chunks tools/eval/chunks.tsv] [--model ID]
        [--effort low|medium|high|xhigh|max]

The model defaults to the learn-german settings (config.toml, environment).
"""

import argparse
import json
import os
import sys
from dataclasses import asdict
from pathlib import Path
from typing import get_args

from learn_german.adapters.llm import AnthropicProvider
from learn_german.adapters.llm.claude import DEFAULT_EFFORT, Effort
from learn_german.application.generation.checks import problems
from learn_german.config import load_settings
from learn_german.domain.errors import FatalError, ItemError
from learn_german.domain.models import CardRequest, ChunkKey, ChunkKind

DEFAULT_CHUNKS = Path(__file__).with_name("chunks.tsv")


def read_requests(path: Path) -> list[CardRequest]:
    """One request per non-comment line: key, sentence, optional context."""
    requests = []
    for line in path.read_text(encoding="utf-8").splitlines():
        if not line.strip() or line.startswith("#"):
            continue
        key, sentence, *rest = line.split("\t")
        context = rest[0] if rest and rest[0] else sentence
        requests.append(CardRequest(ChunkKey(key), ChunkKind.NVV, sentence, context))
    return requests


def main() -> int:
    if os.environ.get("CI"):
        sys.stderr.write("tools/eval calls the paid Claude API and must not run in CI.\n")
        return 2
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--chunks", type=Path, default=DEFAULT_CHUNKS)
    parser.add_argument("--model")
    parser.add_argument("--effort", choices=get_args(Effort), default=DEFAULT_EFFORT)
    args = parser.parse_args()

    try:
        return _run(args.chunks, args.model, args.effort)
    except FatalError as exc:
        sys.stderr.write(f"{exc}\n")
        return 2


def _run(chunks: Path, model: str | None, effort: Effort) -> int:
    settings = load_settings({"model": model})
    provider = AnthropicProvider.create(
        settings.require_anthropic_api_key(), model=settings.model, effort=effort
    )
    failed = 0
    for request in read_requests(chunks):
        row: dict[str, object] = {"key": request.key.value, "sentence": request.sentence}
        try:
            content = provider.generate(request)
        except ItemError as exc:
            row["error"] = str(exc)
            failed += 1
        else:
            row["content"] = asdict(content)
            row["problems"] = problems(request, content)
            failed += bool(row["problems"])
        sys.stdout.write(json.dumps(row, ensure_ascii=False) + "\n")
    sys.stderr.write(f"{failed} chunk(s) failed or have problems. Model: {provider.model}\n")
    return 1 if failed else 0


if __name__ == "__main__":
    sys.exit(main())
