"""Tests for monolithic ri_cases_enriched pipeline."""

from pipeline.ri_cases_enriched_io import (
    apply_finance_defaults,
    catalog_row_from_enriched,
    comps_from_row,
    empty_row,
    evidence_from_row,
)
from pipeline.validate_ri_cases_enriched import validate_row


def test_finance_defaults_cap():
    row = empty_row("test_ri")
    row["total_package_usd"] = "900000"
    apply_finance_defaults(row)
    assert int(row["total_package_usd"]) == 400_000
    assert int(row["slater_share_usd"]) <= 200_000
    assert int(row["physician_share_usd"]) + int(row["slater_share_usd"]) == 400_000


def test_catalog_row_clears_value_band():
    row = empty_row("test_ri")
    row["total_package_usd"] = "400000"
    row["enrichment_status"] = "canonical_csv"
    cat = catalog_row_from_enriched(row)
    assert cat["capital_gap_usd"] == "400000"
    assert cat["value_band_min_usd"] == ""
    assert cat["opportunity_enrichment_source"] == "ri_cases_enriched.csv"


def test_comps_from_row():
    row = empty_row("x")
    row["comp1_name"] = "Acme"
    row["comp1_value_anchor_usd"] = "1000000"
    row["comp1_validation_status"] = "verified"
    comps = comps_from_row(row)
    assert len(comps) == 1
    assert comps[0]["name"] == "Acme"


def test_evidence_from_publications():
    row = empty_row("x")
    row["publication_titles"] = "Paper A\nPaper B"
    row["publication_urls"] = "https://pubmed.ncbi.nlm.nih.gov/1/\nhttps://pubmed.ncbi.nlm.nih.gov/2/"
    row["publication_lead_authors"] = "Smith\nJones"
    row["publication_ri_affiliations"] = "Brown University\nRhode Island Hospital"
    ev = evidence_from_row(row)
    assert ev["publication_count"] == 2
    assert len(ev["publications"]) == 2


def test_build_thesis_uses_policy_package():
    row = empty_row("theromics_ri")
    row["title_clean"] = "HeatSYNC"
    row["company"] = "Theromics Inc"
    row["total_package_usd"] = "400000"
    row["comp1_name"] = "Profound Medical"
    from pipeline.ri_cases_enriched_io import build_thesis

    thesis = build_thesis(row)
    assert "400,000" in thesis
    assert "1,800,000" not in thesis
    assert "Profound Medical" in thesis
    assert "Theromics Inc — Theromics" not in thesis


def test_build_thesis_skips_duplicate_indication():
    row = empty_row("x")
    row["title_clean"] = "Brain electrode system"
    row["indication"] = "Brain electrode system"
    row["total_package_usd"] = "400000"
    from pipeline.ri_cases_enriched_io import build_thesis

    thesis = build_thesis(row)
    assert "focused on" not in thesis


def test_validate_approved_requires_pubs_tier_a():
    row = empty_row("tier_a_case")
    row["review_status"] = "approved"
    row["catalog_tier"] = "A"
    row["primary_patent_url"] = "https://lens.org/123"
    row["publication_count"] = "1"
    row["total_package_usd"] = "400000"
    row["physician_share_usd"] = "200000"
    row["slater_share_usd"] = "200000"
    report = validate_row(row, ["Brown University"])
    assert any("publication_count" in e for e in report.errors)


def test_catalog_row_preserves_approved_thesis():
    row = empty_row("prothera_iaip_ri")
    row["review_status"] = "approved"
    row["total_package_usd"] = "400000"
    row["investment_thesis"] = "Curated investor thesis for ProThera."
    cat = catalog_row_from_enriched(row)
    assert cat["investment_thesis"] == "Curated investor thesis for ProThera."
