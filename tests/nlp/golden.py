"""Read the golden corpus and score an extractor against it (0031). No spaCy here."""

import json
from collections.abc import Iterable
from dataclasses import dataclass
from pathlib import Path

DATA = Path(__file__).parent.parent / "data" / "nlp"
CORPUS_FILE = DATA / "golden_corpus.tsv"
BASELINE_FILE = DATA / "golden_baseline.json"
NO_KEYS = "-"


@dataclass(frozen=True, slots=True)
class GoldenSentence:
    sentence: str
    expected: frozenset[str]


@dataclass(frozen=True, slots=True)
class Score:
    true_positives: int
    false_positives: int
    false_negatives: int

    @property
    def precision(self) -> float:
        found = self.true_positives + self.false_positives
        return self.true_positives / found if found else 1.0

    @property
    def recall(self) -> float:
        expected = self.true_positives + self.false_negatives
        return self.true_positives / expected if expected else 1.0


@dataclass(frozen=True, slots=True)
class Baseline:
    precision: float
    recall: float


def read_corpus(content: str) -> list[GoldenSentence]:
    """Tab-separated sentence and space-separated keys; `-` means none, `#` starts a comment."""
    corpus: list[GoldenSentence] = []
    for line in content.splitlines():
        if not line.strip() or line.startswith("#"):
            continue
        sentence, keys = line.split("\t")
        expected = frozenset() if keys == NO_KEYS else frozenset(keys.split(" "))
        corpus.append(GoldenSentence(sentence, expected))
    return corpus


def load_corpus() -> list[GoldenSentence]:
    return read_corpus(CORPUS_FILE.read_text(encoding="utf-8"))


def load_baseline() -> Baseline:
    data = json.loads(BASELINE_FILE.read_text(encoding="utf-8"))
    return Baseline(precision=float(data["precision"]), recall=float(data["recall"]))


def score(results: Iterable[tuple[frozenset[str], frozenset[str]]]) -> Score:
    """Micro-averaged counts over (expected, found) key sets, one pair per sentence."""
    tp = fp = fn = 0
    for expected, found in results:
        tp += len(expected & found)
        fp += len(found - expected)
        fn += len(expected - found)
    return Score(tp, fp, fn)
