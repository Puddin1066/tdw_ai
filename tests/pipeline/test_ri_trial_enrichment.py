"""Tests for mechanism-focused clinical trial enrichment."""

from pipeline.ri_trial_enrichment import (
    build_trial_profile,
    clear_all_trial_fields,
    enrich_trials_for_row,
    score_trial,
)


def test_build_trial_profile_strips_brown_institution():
    row = {
        "case_id": "x",
        "title_clean": "Brown — Wireless neural interface",
        "indication": "Brown — paralysis",
        "primary_patent_title": "Implantable brain-computer interface electrode array",
        "comp1_name": "Synchron Inc.",
        "clinical_tags": "neurology|medical_device",
    }
    profile = build_trial_profile(row, [])
    queries = " ".join(q for _, q in profile["queries"]).lower()
    assert "brown" not in queries.split()
    assert "synchron" in queries
    assert "implantable" in profile["tokens"] or "interface" in profile["tokens"]


def test_score_trial_blocks_brown_adipose_false_positive():
    tokens = {"wireless", "neural", "interface", "brain", "implantable"}
    score = score_trial(
        "Effect of Chronic Catecholamine Overproduction on Brown Adipose Tissue",
        tokens,
        role="mechanism",
    )
    assert score == 0.0


def test_enrich_trials_clears_without_network(monkeypatch):
    row = {
        "case_id": "test_case",
        "catalog_include": "true",
        "review_status": "",
        "title_clean": "Hydrogel drug delivery",
        "indication": "wound healing",
        "primary_patent_title": "Antibiotic-loaded hydrogel dressing",
        "trial_count": "3",
        "trial_nct_ids": "NCT00000001",
        "trial_titles": "Bad match",
        "trial_urls": "https://clinicaltrials.gov/study/NCT00000001",
    }

    def _no_trials(_query: str, *, limit: int = 5):
        return []

    monkeypatch.setattr(
        "pipeline.ri_trial_enrichment.fetch_trials_ctgov",
        _no_trials,
    )

    clear_all_trial_fields(row)
    changes = enrich_trials_for_row(row, [], [], force=True)
    assert "trials_empty" in changes
    assert row["trial_count"] == "0"
    assert not row.get("trial_nct_ids")
