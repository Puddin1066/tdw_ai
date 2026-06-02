"""Tests for cited enrichment source helpers."""

from pipeline.ri_cases_enriched_io import empty_row
from pipeline.ri_cases_enriched_schema import COMP_PREFIXES
from pipeline.ri_source_utils import (
    finish_row_sources,
    is_mock_text,
    is_primary_citation_url,
    promote_urls_from_web_search_notes,
    strip_mock_main_columns,
    sync_literature_sources,
)


def test_is_mock_text():
    assert is_mock_text("MOCK/SYNTHETIC — verify financing")
    assert not is_mock_text("Preclinical validation milestone")


def test_is_primary_citation_url_rejects_search():
    assert not is_primary_citation_url("https://www.google.com/search?q=test")
    assert not is_primary_citation_url("https://www.sec.gov/edgar/search/#/q=Acme")
    assert is_primary_citation_url("https://www.prnewswire.com/news-releases/acme-123.html")


def test_promote_urls_from_web_search_notes():
    row = empty_row("x")
    row["comp1_name"] = "Acme Bio"
    row["web_search_notes"] = (
        "[comp1] Acme raises Series A | https://www.prnewswire.com/news/acme-series-a.html"
    )
    changes = promote_urls_from_web_search_notes(row)
    assert "comp1_value_source_url" in changes
    assert "prnewswire.com" in row["comp1_value_source_url"]


def test_strip_mock_main_columns():
    row = empty_row("x")
    row["rd_milestones"] = "MOCK/SYNTHETIC — preclinical validation"
    assert strip_mock_main_columns(row)
    assert row["rd_milestones"] == ""


def test_sync_literature_sources_from_publications():
    row = empty_row("x")
    row["publication_titles"] = "Paper A"
    row["publication_urls"] = "https://pubmed.ncbi.nlm.nih.gov/123/"
    row["literature_narrative"] = "One RI lead-author paper."
    assert sync_literature_sources(row)
    assert "pubmed.ncbi.nlm.nih.gov" in row["literature_source_urls"]


def test_finish_row_sources():
    row = empty_row("x")
    row["comp1_name"] = "Acme"
    row["comp1_url"] = "https://acme.example.com/"
    row["rd_milestones"] = "Complete tox study"
    row["primary_patent_url"] = "https://lens.org/123"
    changes = finish_row_sources(row, comp_prefixes=COMP_PREFIXES)
    assert "comp1_supporting_citations" in changes or "comp1_value_source_url" in changes
