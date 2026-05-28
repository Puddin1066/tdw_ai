"""Merge Tier A canonical CSV sources into precedent and catalog rows."""

from __future__ import annotations

from pipeline.ri_precedent_common import PRECEDENT_FIELDS, apply_value_anchor
from pipeline.tier_a.finance import active_tier_a_case_ids, registry_finance_patch, should_overwrite_template_gap
from pipeline.tier_a.io import (
    comparables_by_case,
    evidence_by_case,
    load_registry,
    registry_by_case,
)


def _precedent_row_from_comparable(
    *,
    case_id: str,
    title_clean: str,
    program_family: str,
    comparable: dict[str, str],
) -> dict[str, str]:
    row = {
        "case_id": case_id,
        "title_clean": title_clean,
        "program_family": program_family,
        "precedent_rank": comparable.get("precedent_rank", "1"),
        "precedent_type": comparable.get("precedent_type", "startup"),
        "precedent_name": comparable.get("precedent_name", ""),
        "precedent_stage": comparable.get("precedent_stage", ""),
        "precedent_notes": comparable.get("precedent_notes", ""),
        "precedent_url": comparable.get("precedent_url", ""),
        "inferred_development": comparable.get("inferred_development", ""),
        "inferred_financing": comparable.get("inferred_financing", ""),
        "inferred_team": comparable.get("inferred_team", ""),
        "total_raised_usd_est": comparable.get("total_raised_usd_est", ""),
        "last_round_usd_est": comparable.get("last_round_usd_est", ""),
        "value_anchor_usd": comparable.get("value_anchor_usd", ""),
        "value_anchor_type": comparable.get("value_anchor_type", ""),
        "value_source_url": comparable.get("value_source_url", ""),
        "financing_strategy": comparable.get("financing_strategy", ""),
        "validation_status": comparable.get("validation_status", "suggested"),
        "confidence": comparable.get("confidence", "medium"),
        "source": comparable.get("source", "tier_a_curated"),
    }
    apply_value_anchor(row)
    return row


def tier_a_precedent_rows_for_catalog(catalog_row: dict[str, str]) -> list[dict[str, str]]:
    case_id = catalog_row["case_id"]
    registry = registry_by_case().get(case_id, {})
    comps = comparables_by_case().get(case_id, [])
    if not comps:
        return []
    title = registry.get("title_clean") or catalog_row.get("title_clean", case_id)
    family = registry.get("program_family") or catalog_row.get("program_family", "")
    return [
        _precedent_row_from_comparable(
            case_id=case_id,
            title_clean=title,
            program_family=family,
            comparable=c,
        )
        for c in comps
    ]


def apply_tier_a_to_precedents(
    precedent_rows: list[dict[str, str]],
    catalog_rows: list[dict[str, str]],
) -> list[dict[str, str]]:
    """Replace auto-generated precedents for Tier A registry cases."""
    tier_ids = active_tier_a_case_ids()
    if not tier_ids:
        return precedent_rows

    catalog_by_id = {r["case_id"]: r for r in catalog_rows}
    kept = [r for r in precedent_rows if r["case_id"] not in tier_ids]
    curated: list[dict[str, str]] = []
    for case_id in sorted(tier_ids):
        catalog_row = catalog_by_id.get(case_id)
        if not catalog_row:
            continue
        curated.extend(tier_a_precedent_rows_for_catalog(catalog_row))

    # Preserve field order
    out: list[dict[str, str]] = []
    for row in kept + curated:
        out.append({k: row.get(k, "") for k in PRECEDENT_FIELDS})
    return out


def apply_tier_a_to_catalog_row(
    catalog_row: dict[str, str],
    *,
    median_usd: int | None = None,
) -> dict[str, str]:
    """Return patches to apply before comparator inference."""
    case_id = catalog_row["case_id"]
    registry = registry_by_case().get(case_id)
    if not registry or case_id not in active_tier_a_case_ids():
        return {}

    patch = registry_finance_patch(
        registry,
        median_usd=median_usd,
        opportunity_type=catalog_row.get("opportunity_type", ""),
        program_family=catalog_row.get("program_family", "") or registry.get("program_family", ""),
    )

    if (registry.get("title_clean") or "").strip():
        patch["title_clean"] = registry["title_clean"].strip()
    if (registry.get("company") or "").strip():
        patch["company"] = registry["company"].strip()
    if (registry.get("indication") or "").strip():
        patch["indication"] = registry["indication"].strip()
    if (registry.get("opportunity_type") or "").strip():
        patch["opportunity_type"] = registry["opportunity_type"].strip()
    if (registry.get("physician_lead_name") or "").strip():
        patch["physician_lead_name"] = registry["physician_lead_name"].strip()
        patch["ri_physician_lead"] = registry["physician_lead_name"].strip()
    if (registry.get("physician_lead_npi") or "").strip():
        patch["physician_lead_npi"] = registry["physician_lead_npi"].strip()
    if (registry.get("primary_lens_id") or "").strip():
        patch["primary_lens_id"] = registry["primary_lens_id"].strip()

    evidence = evidence_by_case().get(case_id, {})
    if evidence:
        if (evidence.get("evidence_grade") or "").strip():
            patch["tier_a_evidence_grade"] = evidence["evidence_grade"].strip()
        if (evidence.get("review_status") or "").strip():
            patch["tier_a_evidence_review_status"] = evidence["review_status"].strip()
        if (evidence.get("evidence_depth_score_0_100") or "").strip():
            patch["tier_a_evidence_depth_score"] = evidence["evidence_depth_score_0_100"].strip()
        if (evidence.get("canonical_evidence_status") or "").strip():
            patch["biomcp_evidence_status"] = evidence["canonical_evidence_status"].strip()

    patch["opportunity_enrichment_source"] = "tier_a_curated"
    return patch


def tier_a_overwrite_template_gap(case_id: str) -> bool:
    registry = registry_by_case().get(case_id, {})
    if case_id not in active_tier_a_case_ids():
        return True
    return should_overwrite_template_gap(registry)


def tier_a_registry_count() -> int:
    return len(load_registry(active_only=True))
