from app.fetcher.http import is_url_safe


def test_block_localhost() -> None:
    assert not is_url_safe("http://localhost:8000")
    assert not is_url_safe("http://127.0.0.1")


def test_allow_public_url() -> None:
    assert is_url_safe("https://example.com")
