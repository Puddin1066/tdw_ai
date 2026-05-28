"""Tests for Tier A canonical source layer."""

from __future__ import annotations

import csv
from pathlib import Path

import pytest

from pipeline.tier_a.backfill import backfill
from pipeline.tier_a.build_from_sources import apply_tier_a_to_precedents, tier_a_precedent_rows_for_catalog
from pipeline.tier_a import paths as tier_a_paths
from pipeline.tier_a.io import load_registry
from pipeline.tier_a.validate_sources import validate_sources


@pytest.fixture()
def tier_a_tmp(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> Path:
    root = tmp_path / "tier_a"
    root.mkdir()
    for mod in (
        "pipeline.tier_a.paths",
        "pipeline.tier_a.io.tier_a_paths",
        "pipeline.tier_a.validate_sources",
    ):
        monkeypatch.setattr(f"{mod}.TIER_A_ROOT", root, raising=False)
        monkeypatch.setattr(f"{mod}.REGISTRY_CSV", root / "registry.csv", raising=False)
        monkeypatch.setattr(f"{mod}.COMPARABLES_CSV", root / "comparables.csv", raising=False)
        monkeypatch.setattr(
            f"{mod}.EVIDENCE_OVERRIDES_CSV", root / "evidence_overrides.csv", raising=False
        )
    monkeypatch.setattr(
        "pipeline.tier_a.paths.FINANCE_POLICY_YAML",
        Path(__file__).resolve().parents[2] / "data" / "ri" / "tier_a" / "finance_policy.yaml",
    )
    opp_path = tmp_path / "ri_opportunities.csv"
    ip_path = tmp_path / "ri_ip_assets.csv"
    for mod in ("pipeline.tier_a.paths", "pipeline.tier_a.validate_sources"):
        monkeypatch.setattr(f"{mod}.OPPORTUNITIES_PATH", opp_path, raising=False)
        monkeypatch.setattr(f"{mod}.IP_ASSETS_PATH", ip_path, raising=False)

    (tmp_path / "ri_opportunities.csv").write_text(
        "case_id,display_name\nalpha_ri,Alpha Program\n",
        encoding="utf-8",
    )
    (tmp_path / "ri_ip_assets.csv").write_text(
        "case_id,lens_id\nalpha_ri,111-222-333\n",
        encoding="utf-8",
    )

    with (root / "registry.csv").open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=tier_a_paths.REGISTRY_FIELDS)
        writer.writeheader()
        writer.writerow(
            {
                "case_id": "alpha_ri",
                "title_clean": "Alpha",
                "program_family": "test_family",
                "company": "Alpha Co",
                "opportunity_type": "platform",
                "indication": "test",
                "primary_lens_id": "111-222-333",
                "physician_lead_name": "DR ALPHA",
                "physician_lead_npi": "",
                "status": "active",
                "promotion_source": "manual",
                "capital_gap_usd": "1500000",
                "budget_ceiling_usd": "",
                "clinical_duration_weeks": "",
                "development_stage": "validation",
                "data_caveat": "",
                "ri_notes": "",
                "reviewed_by": "test",
                "reviewed_at": "2026-05-28",
            }
        )

    comp_fields = [
        "case_id",
        "precedent_rank",
        "precedent_type",
        "precedent_name",
        "precedent_stage",
        "precedent_notes",
        "precedent_url",
        "inferred_development",
        "inferred_financing",
        "inferred_team",
        "total_raised_usd_est",
        "last_round_usd_est",
        "value_anchor_usd",
        "value_anchor_type",
        "value_source_url",
        "financing_strategy",
        "validation_status",
        "confidence",
        "source",
    ]
    with (root / "comparables.csv").open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=comp_fields)
        writer.writeheader()
        writer.writerow(
            {
                "case_id": "alpha_ri",
                "precedent_rank": "1",
                "precedent_type": "startup",
                "precedent_name": "Comp One",
                "precedent_stage": "commercial",
                "precedent_notes": "",
                "precedent_url": "https://example.com",
                "inferred_development": "Pilot",
                "inferred_financing": "VC",
                "inferred_team": "",
                "total_raised_usd_est": "",
                "last_round_usd_est": "",
                "value_anchor_usd": "1000000",
                "value_anchor_type": "total_raised",
                "value_source_url": "https://example.com/pr",
                "financing_strategy": "",
                "validation_status": "verified",
                "confidence": "high",
                "source": "test",
            }
        )

    ev_fields = [
        "case_id",
        "evidence_depth_score_0_100",
        "evidence_grade",
        "review_status",
        "reviewer_note",
        "canonical_evidence_status",
        "min_publication_count",
    ]
    with (root / "evidence_overrides.csv").open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=ev_fields)
        writer.writeheader()
        writer.writerow(
            {
                "case_id": "alpha_ri",
                "evidence_depth_score_0_100": "60",
                "evidence_grade": "B",
                "review_status": "pending",
                "reviewer_note": "",
                "canonical_evidence_status": "patent_linked",
                "min_publication_count": "2",
            }
        )
    return root


def test_validate_sources_ok(tier_a_tmp: Path) -> None:
    report = validate_sources()
    assert report.ok, report.errors


def test_apply_tier_a_replaces_precedents(tier_a_tmp: Path) -> None:
    catalog_row = {"case_id": "alpha_ri", "title_clean": "Alpha", "program_family": "test_family"}
    auto_rows = [
        {
            "case_id": "alpha_ri",
            "title_clean": "Alpha",
            "program_family": "general",
            "precedent_rank": "1",
            "precedent_name": "Auto Comp",
            "precedent_type": "startup",
            "precedent_stage": "seed",
            "precedent_notes": "",
            "precedent_url": "",
            "inferred_development": "",
            "inferred_financing": "",
            "inferred_team": "",
            "total_raised_usd_est": "",
            "last_round_usd_est": "",
            "value_anchor_usd": "",
            "value_anchor_type": "",
            "value_source_url": "",
            "financing_strategy": "",
            "validation_status": "suggested",
            "confidence": "medium",
            "source": "auto",
        }
    ]
    merged = apply_tier_a_to_precedents(auto_rows, [catalog_row])
    alpha = [r for r in merged if r["case_id"] == "alpha_ri"]
    assert len(alpha) == 1
    assert alpha[0]["precedent_name"] == "Comp One"
    assert alpha[0]["validation_status"] == "verified"


def test_comp_web_review_queue(tier_a_tmp: Path) -> None:
    from pipeline.tier_a.comp_web_review import build_queue

    rows = build_queue()
    assert rows
    assert all(r.case_id for r in rows)


def test_backfill_writes_files() -> None:
    if not (Path(__file__).resolve().parents[2] / "data" / "ri" / "ri_opportunities_catalog_enrichment.csv").exists():
        pytest.skip("catalog not present")
    counts = backfill()
    assert counts["registry"] >= 20
    assert tier_a_paths.REGISTRY_CSV.exists()
    assert load_registry(active_only=True)
