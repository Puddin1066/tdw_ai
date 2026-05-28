"""Tests for enrich_ri_cases_web helpers."""

from __future__ import annotations

from pipeline.enrich_ri_cases_web import (
    _draft_rd_summary,
    _needs_comp_search,
    _profile_search_queries,
    _rd_search_queries,
)
from pipeline.ri_cases_enriched_io import empty_row


def test_needs_comp_search_when_url_missing():
    row = empty_row("x")
    row["comp1_name"] = "Acme Therapeutics"
    assert _needs_comp_search(row, "comp1_")
    row["comp1_value_source_url"] = "https://www.prnewswire.com/news/example"
    row["comp1_validation_status"] = "verified"
    assert not _needs_comp_search(row, "comp1_")


def test_profile_queries_skip_brown():
    row = empty_row("x")
    row["physician_lead_name"] = "JACK A ELIAS"
    row["physician_lead_institution"] = "Brown University"
    assert _profile_search_queries(row) == []


def test_rd_draft_from_metadata():
    row = empty_row("theromics_ri")
    row.update(
        {
            "title_clean": "Tumor thermal ablation",
            "development_stage": "validation",
            "comp1_name": "Profound Medical",
            "comp1_development_path": "PMA → commercial",
        }
    )
    summary = _draft_rd_summary(row)
    assert "thermal ablation" in summary.lower()
    assert "Profound" in summary


def test_rd_search_queries_when_empty():
    row = empty_row("x")
    row["title_clean"] = "Sepsis diagnostic"
    row["indication"] = "sepsis"
    qs = _rd_search_queries(row)
    assert any("preclinical" in q for q in qs)
