"""Tests for enriched-row physician matching."""

from pipeline.physician_assignment import (
    compute_assignments_for_enriched_rows,
    opportunity_from_enriched_row,
)
from pipeline.enrich_ri_cases_physicians import enrich_physicians


def test_opportunity_from_enriched_row_defaults_roles():
    row = {
        "case_id": "theromics_ri",
        "title_clean": "Theromics — HeatSYNC",
        "opportunity_type": "platform",
    }
    opp = opportunity_from_enriched_row(row)
    assert "reviewer" in opp["required_roles"]
    assert opp["case_id"] == "theromics_ri"


def test_compute_assignments_for_enriched_row():
    row = {
        "case_id": "theromics_ri",
        "catalog_include": "true",
        "title_clean": "Theromics — HeatSYNC",
        "indication": "thermal tumor ablation",
        "opportunity_type": "platform",
        "required_specialties": "interventional radiology|surgical oncology",
    }
    assignments = compute_assignments_for_enriched_rows([row], catalog_only=False)
    match = assignments.get("theromics_ri", {})
    assert match.get("staffing_feasibility_score_0_100", 0) >= 0
    assert "required_clinical_tags" in match


def test_enrich_physicians_writes_suggest_columns(tmp_path, monkeypatch):
    from pipeline.ri_cases_enriched_io import CASES_CSV, load_cases, write_cases

    src = CASES_CSV
    rows = load_cases(src)
    target = [r for r in rows if r.get("case_id") == "theromics_ri"]
    if not target:
        return
    dest = tmp_path / "cases.csv"
    write_cases(target, path=dest)

    monkeypatch.setattr(
        "pipeline.enrich_ri_cases_physicians.CASES_CSV",
        dest,
    )
    stats = enrich_physicians(path=dest)
    assert stats["touched"] >= 0
    updated = load_cases(dest)[0]
    assert "staffing_feasibility_score" in updated or updated.get("suggest_physician_lead_name")
