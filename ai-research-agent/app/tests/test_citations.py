from app.agent.citations import validate_citations


def test_missing_tag_detected() -> None:
    missing = validate_citations("Finding text [S1] and [S9]", {"S1", "S2"})
    assert missing == ["S9"]
