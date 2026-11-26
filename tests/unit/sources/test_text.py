import pytest

from learn_german.adapters.sources import content_hash, normalise_text


@pytest.mark.parametrize(
    ("raw", "expected"),
    [
        pytest.param("Ein  Satz.\tNoch einer.", "Ein Satz. Noch einer.", id="spaces"),
        pytest.param("Ein\nSatz.", "Ein Satz.", id="line-break-inside-paragraph"),
        pytest.param("Eins.\n\n\n  \nZwei.", "Eins.\n\nZwei.", id="paragraphs"),
        pytest.param("\n\n  Eins.  \n\n", "Eins.", id="outer-whitespace"),
        pytest.param("Gru\u0308n", "Gr\u00fcn", id="nfc"),
        pytest.param("a\u00a0b", "a b", id="no-break-space"),
        pytest.param(" \n\n ", "", id="blank"),
    ],
)
def test_normalise_text(raw: str, expected: str) -> None:
    assert normalise_text(raw) == expected


def test_content_hash_is_sha256_hex_of_utf8() -> None:
    assert content_hash("") == "e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855"
    assert content_hash("Grün") != content_hash("Grun")
