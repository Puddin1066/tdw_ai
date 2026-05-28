"""Apply Tier A finance policy from registry + comparables."""

from __future__ import annotations

from typing import Any

from pipeline.infer_ri_opportunity_package import TEMPLATE_CAPITAL_GAP, _parse_usd
from pipeline.tier_a.io import load_finance_policy, load_registry


def capital_gap_from_policy(
    *,
    median_usd: int | None,
    opportunity_type: str,
    program_family: str,
    policy: dict[str, Any] | None = None,
) -> int:
    policy = policy or load_finance_policy()
    defaults = policy.get("defaults") or {}
    pharma_families = set(policy.get("program_families_using_pharma_gap") or [])
    pharma_types = set(policy.get("opportunity_types_using_pharma_gap") or [])

    if program_family in pharma_families or opportunity_type in pharma_types:
        return int(defaults.get("pharma_chemistry_gap_usd", 2_100_000))

    if not median_usd:
        return int(defaults.get("gap_usd_no_anchor", 1_200_000))

    for bucket in policy.get("capital_gap_buckets") or []:
        cap = bucket.get("max_median_usd")
        if cap is None:
            return int(bucket.get("gap_usd", 2_400_000))
        if median_usd < int(cap):
            return int(bucket.get("gap_usd", 1_200_000))
    return int(defaults.get("gap_usd_no_anchor", 1_200_000))


def registry_finance_patch(
    registry_row: dict[str, str],
    *,
    median_usd: int | None = None,
    opportunity_type: str = "",
    program_family: str = "",
) -> dict[str, str]:
    """Catalog column updates from registry overrides + policy."""
    patch: dict[str, str] = {}
    gap_raw = (registry_row.get("capital_gap_usd") or "").strip()
    if gap_raw:
        gap = _parse_usd(gap_raw) or 0
        patch["capital_gap_usd"] = str(gap)
    else:
        gap = capital_gap_from_policy(
            median_usd=median_usd,
            opportunity_type=opportunity_type or registry_row.get("opportunity_type", ""),
            program_family=program_family or registry_row.get("program_family", ""),
        )
        patch["capital_gap_usd"] = str(gap)
    policy = load_finance_policy()
    defaults = policy.get("defaults") or {}

    if not (registry_row.get("budget_ceiling_usd") or "").strip():
        mult = float(defaults.get("budget_ceiling_multiplier", 1.15))
        patch["budget_ceiling_usd"] = str(int(gap * mult))
    else:
        patch["budget_ceiling_usd"] = registry_row["budget_ceiling_usd"].strip()

    if not (registry_row.get("clinical_duration_weeks") or "").strip():
        patch["clinical_duration_weeks"] = str(defaults.get("default_validation", 40))
    else:
        patch["clinical_duration_weeks"] = registry_row["clinical_duration_weeks"].strip()

    if (registry_row.get("development_stage") or "").strip():
        patch["development_stage"] = registry_row["development_stage"].strip()

    if (registry_row.get("data_caveat") or "").strip():
        patch["data_caveat"] = registry_row["data_caveat"].strip()
    if (registry_row.get("ri_notes") or "").strip():
        patch["ri_notes"] = registry_row["ri_notes"].strip()

    status = (registry_row.get("status") or "active").lower()
    if status == "draft":
        patch["enrichment_status"] = "tier_a_draft"
    elif status == "active":
        patch["enrichment_status"] = "tier_a_curated"

    return patch


def active_tier_a_case_ids() -> set[str]:
    return {
        (r.get("case_id") or "").strip()
        for r in load_registry(active_only=True)
        if (r.get("case_id") or "").strip()
    }


def should_overwrite_template_gap(registry_row: dict[str, str]) -> bool:
    gap = (registry_row.get("capital_gap_usd") or "").strip()
    return not gap or gap == TEMPLATE_CAPITAL_GAP
