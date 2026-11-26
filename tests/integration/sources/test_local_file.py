"""LocalFileSource on real files in tmp_path: encoding, empty files, refs and hashes."""

from pathlib import Path

import pytest

from learn_german.adapters.sources import LocalFileSource, content_hash
from learn_german.domain.errors import SourceFetchError
from learn_german.domain.models import SourceKind
from tests.fakes.clock import DEFAULT_NOW, FixedClock

TEXT = "Die Regierung traf eine Entscheidung.\n\nSie stellte Geld zur Verfügung."


@pytest.fixture
def source() -> LocalFileSource:
    return LocalFileSource(FixedClock())


@pytest.mark.parametrize(
    ("ref", "handled"),
    [
        pytest.param("artikel.txt", True, id="relative"),
        pytest.param("/srv/texte/ARTIKEL.TXT", True, id="upper-case-suffix"),
        pytest.param("notizen.md", False, id="other-suffix"),
        pytest.param("https://zeitung.example/artikel.txt", False, id="url"),
    ],
)
def test_local_file_handles_txt_paths_only(
    source: LocalFileSource, ref: str, handled: bool
) -> None:
    assert source.can_handle(ref) is handled


def test_local_file_reads_normalised_text_under_its_absolute_path(
    source: LocalFileSource, tmp_path: Path
) -> None:
    (tmp_path / "work" / "artikel.txt").write_text(
        "  Die Regierung traf\n  eine Entscheidung.\n\n\n Sie stellte Geld zur Verfügung.\n",
        encoding="utf-8",
    )

    result = source.fetch("artikel.txt")

    assert result.ref == str(tmp_path / "work" / "artikel.txt")
    assert (result.kind, result.title, result.fetched_at) == (
        SourceKind.LOCAL_FILE,
        "artikel",
        DEFAULT_NOW,
    )
    assert result.text == TEXT
    assert result.content_hash == content_hash(TEXT)


def test_local_file_drops_a_byte_order_mark(source: LocalFileSource, tmp_path: Path) -> None:
    path = tmp_path / "bom.txt"
    path.write_bytes(b"\xef\xbb\xbf" + TEXT.encode())

    assert source.fetch(str(path)).text == TEXT


def test_local_file_rejects_an_empty_file(source: LocalFileSource, tmp_path: Path) -> None:
    path = tmp_path / "leer.txt"
    path.write_text(" \n\n \t\n", encoding="utf-8")

    with pytest.raises(SourceFetchError, match="holds no text"):
        source.fetch(str(path))


def test_local_file_rejects_invalid_encoding(source: LocalFileSource, tmp_path: Path) -> None:
    path = tmp_path / "latin1.txt"
    path.write_bytes("Die Bürgermeisterin nahm Stellung.".encode("latin-1"))

    with pytest.raises(SourceFetchError, match=r"not UTF-8.*Save it again"):
        source.fetch(str(path))


def test_local_file_reports_a_missing_file(source: LocalFileSource, tmp_path: Path) -> None:
    with pytest.raises(SourceFetchError, match="does not exist"):
        source.fetch(str(tmp_path / "fehlt.txt"))


def test_local_file_reports_a_directory(source: LocalFileSource, tmp_path: Path) -> None:
    (tmp_path / "ordner.txt").mkdir()

    with pytest.raises(SourceFetchError, match="Cannot read"):
        source.fetch(str(tmp_path / "ordner.txt"))
