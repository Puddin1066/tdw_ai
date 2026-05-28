from pipeline.tier_a.comp_link_resolve import _heuristic_links, url_link_label
from pipeline.tier_a.comp_web_review import _is_discovery_url, _merge_precedent_notes


def test_is_discovery_url():
    assert _is_discovery_url("https://www.google.com/search?q=foo")
    assert not _is_discovery_url("https://www.prnewswire.com/news/foo.html")


def test_heuristic_links_labels():
    assert url_link_label("https://www.sec.gov/foo") == "SEC filing (on file)"
    links = _heuristic_links(
        {
            "precedent_name": "Acme Corp",
            "precedent_type": "startup",
            "precedent_url": "https://example.com/",
            "value_source_url": "https://www.google.com/search?q=x",
        }
    )
    assert any("example.com" in url for _, url in links)
    assert not any("google.com/search" in url for _, url in links)


def test_merge_precedent_notes_search_only():
    target: dict[str, str] = {"precedent_notes": ""}
    _merge_precedent_notes({"search_notes": "Series C $30M Nov 2023."}, target)
    assert target["precedent_notes"] == "Series C $30M Nov 2023."


def test_merge_precedent_notes_appends_search():
    target: dict[str, str] = {"precedent_notes": "FDA-approved pafolacianine."}
    _merge_precedent_notes(
        {
            "precedent_notes": "FDA-approved pafolacianine.",
            "search_notes": "Series C $30M Nov 2023.",
        },
        target,
    )
    assert target["precedent_notes"] == "FDA-approved pafolacianine. — Series C $30M Nov 2023."


def test_merge_precedent_notes_skips_duplicate_search():
    target: dict[str, str] = {"precedent_notes": "Already has Series C $30M Nov 2023."}
    _merge_precedent_notes({"search_notes": "Series C $30M Nov 2023."}, target)
    assert target["precedent_notes"] == "Already has Series C $30M Nov 2023."
