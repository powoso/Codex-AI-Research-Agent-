from app.agent.scoring import rank_urls


def test_ranking_deterministic() -> None:
    urls = [
        "https://www.nist.gov/artificial-intelligence",
        "https://www.nasa.gov/artificial-intelligence/",
        "https://www.example.org/cooking",
    ]
    a = rank_urls("artificial intelligence risk governance", urls)
    b = rank_urls("artificial intelligence risk governance", urls)
    assert a == b
    assert a[0][0] != "https://www.example.org/cooking"
