from __future__ import annotations

from pipeline.ri_biomcp_relevance import (
    merge_search_terms,
    parse_inventor_surnames,
    patent_link_for_publication,
    rank_and_filter_publications,
    build_literature_profile,
)


def test_parse_inventor_surnames_lens_format() -> None:
    rows = [{"inventors": "PARK WILLIAM KEUN CHAN;;DUPUY DAMIAN E"}]
    assert parse_inventor_surnames(rows) == {"PARK", "DUPUY"}


def test_patent_link_requires_inventor_and_science() -> None:
    ip_rows = [{"inventors": "PARK WILLIAM;;DUPUY DAMIAN", "title": "Thermal accelerant RF ablation gel", "lens_id": "1", "display_key": "US 1"}]
    row = {"case_id": "theromics_ri", "title_clean": "Theromics ablation"}
    profile = build_literature_profile(row, ip_rows)

    ok, link = patent_link_for_publication(
        {
            "title": "Thermal accelerant improves microwave ablation outcomes",
            "authors": ["Dupuy DE", "Park WK"],
            "abstract_snippet": "albumin gel thermal accelerant for RF ablation",
        },
        profile,
    )
    assert ok
    assert "DUPUY" in link["matched_inventor_surnames"]
    assert "inventor_match" in link["link_basis"]

    bad, _ = patent_link_for_publication(
        {
            "title": "Unrelated cardiac surgery outcomes",
            "authors": ["Smith J"],
            "abstract_snippet": "coronary bypass",
        },
        profile,
    )
    assert not bad


def test_rank_filters_unlinked_publications() -> None:
    ip_rows = [{"inventors": "MONAGHAN SEAN", "title": "deep RNA sepsis host response", "lens_id": "2", "display_key": "US 2"}]
    profile = build_literature_profile({"case_id": "monaghan_sepsis_diagnostic_ri"}, ip_rows)
    pubs = [
        {
            "title": "Host response RNA in sepsis by Monaghan laboratory",
            "authors": ["Monaghan S"],
            "abstract_snippet": "deep RNA sequencing host response sepsis",
            "pmid": "1",
        },
        {
            "title": "Generic ICU review",
            "authors": ["Jones A"],
            "abstract_snippet": "critical care",
            "pmid": "2",
        },
    ]
    kept, stats = rank_and_filter_publications(pubs, profile, limit=5)
    assert len(kept) == 1
    assert kept[0]["pmid"] == "1"
    assert stats["rejected_no_inventor"] >= 1


def test_merge_search_terms_prioritizes_inventors() -> None:
    ip_rows = [{"inventors": "DUPUY DAMIAN", "title": "Thermal accelerant compositions"}]
    terms = merge_search_terms({"case_id": "x"}, ip_rows, ["generic ablation review"])
    assert any("DUPUY" in t for t in terms)
    assert any("thermal" in t.lower() for t in terms)
