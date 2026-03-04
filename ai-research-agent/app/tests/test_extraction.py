from pathlib import Path

from app.extract.extract import extract_document


def test_extract_non_empty() -> None:
    html = Path("app/tests/fixtures/sample.html").read_text(encoding="utf-8")
    doc = extract_document(html)
    assert len(doc["cleaned_text"]) > 40
    assert doc["title"]
