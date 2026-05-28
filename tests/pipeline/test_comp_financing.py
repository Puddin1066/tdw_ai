from pipeline.tier_a.comp_financing import default_anchor_type, resolve_financing_queries


def test_resolve_financing_queries_prioritizes_vc():
    queries = resolve_financing_queries(
        {"precedent_name": "Acme Therapeutics", "precedent_type": "startup"}
    )
    joined = " ".join(queries).lower()
    assert "series" in joined
    assert "venture" in joined
    assert "market cap" not in joined


def test_resolve_financing_queries_public_fallback():
    queries = resolve_financing_queries(
        {"precedent_name": "BigCo", "precedent_type": "public"}
    )
    assert any("market cap" in q.lower() for q in queries)


def test_default_anchor_type_startup():
    assert default_anchor_type({"precedent_type": "startup"}) == "total_raised"
