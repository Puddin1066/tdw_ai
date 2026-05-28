"""Tests for RI BioMCP enrichment helpers."""

from __future__ import annotations

from pipeline.enrich_ri_biomcp import build_search_terms
from pipeline.ri_biomcp_relevance import merge_search_terms


def test_build_search_terms_from_title_and_patent() -> None:
    row = {
        "title_clean": "Theromics — tumor thermal ablation",
        "display_name": "HeatSYNC gel",
        "indication": "Hepatic tumor ablation",
        "program_family": "theromics_ablation",
    }
    ip_rows = [
        {
            "title": "Thermal accelerant composition for radiofrequency ablation",
            "inventors": "PARK WILLIAM;;DUPUY DAMIAN",
        },
    ]
    base = build_search_terms(row, ip_rows)
    terms = merge_search_terms(row, ip_rows, base)
    assert any("thermal" in t.lower() for t in terms)
    assert any("DUPUY" in t or "PARK" in t for t in terms)
