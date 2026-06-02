"""Tests for single-case enrichment orchestrator."""

from pipeline.enrich_ri_case import RECIPES, _resolve_mode, refresh_approved_copy
from pipeline.ri_cases_enriched_io import empty_row, load_cases, write_cases


def test_resolve_mode_defaults():
    assert _resolve_mode(None, tier=None) == "tier_a_full"
    assert _resolve_mode(None, tier="B") == "tier_b_light"
    assert _resolve_mode("package", tier="A") == "package"


def test_recipes_cover_all_modes():
    assert set(RECIPES) == {
        "tier_a_full",
        "tier_b_light",
        "web_only",
        "package",
        "refresh_copy",
    }


def test_refresh_copy_only_touches_approved(tmp_path):
    path = tmp_path / "cases.csv"
    pending = empty_row("pending_case")
    pending["review_status"] = "pending"
    pending["catalog_include"] = "true"
    pending["publication_titles"] = "Paper A"
    pending["publication_urls"] = "https://pubmed.ncbi.nlm.nih.gov/123/"

    approved = empty_row("approved_case")
    approved["review_status"] = "approved"
    approved["catalog_include"] = "true"
    approved["publication_titles"] = "Paper B"
    approved["publication_urls"] = "https://pubmed.ncbi.nlm.nih.gov/456/"

    write_cases([pending, approved], path)
    summary = refresh_approved_copy(path=path, fetch_urls=False)

    rows = {r["case_id"]: r for r in load_cases(path)}
    assert summary["processed"] == 1
    assert summary["touched"] == 1
    assert "literature_source_urls" in rows["approved_case"]
    assert not rows["pending_case"].get("literature_source_urls")
