"""Infer RI opportunity financing/development package from enriched comparables.

Maps verified precedent anchors and development paths onto catalog columns so each
RI patent-backed program reads as a pragmatic, comparator-grounded investment case.
"""

from __future__ import annotations

import re
from typing import Any

TEMPLATE_CAPITAL_GAP = "1200000"

# Lower rank = earlier (RI program typically trails best comp by one stage)
_STAGE_RANK: dict[str, int] = {
    "research": 0,
    "academic": 0,
    "published": 0,
    "precommercial": 1,
    "pre_seed": 2,
    "seed": 2,
    "early": 2,
    "sbir_seed": 3,
    "sttr_510k_path": 3,
    "investigational_us": 4,
    "clinical": 4,
    "clinical_validation": 4,
    "pilot": 4,
    "ide": 5,
    "fda_breakthrough": 5,
    "fda_cleared": 6,
    "fda_adaptive_dbs": 6,
    "fda_approved": 7,
    "commercial": 8,
    "public": 8,
    "public_spac": 8,
    "growth": 8,
    "late_private": 8,
    "pivotal": 8,
    "pivotal_2026": 8,
    "operating": 8,
    "phase_3_ready": 9,
    "acquired_2026": 9,
    "acquired_2020": 9,
}


def _parse_usd(value: str | None) -> int | None:
    try:
        n = int(float((value or "").strip()))
        return n if n > 0 else None
    except ValueError:
        return None


def _norm_stage(stage: str) -> str:
    return re.sub(r"[^a-z0-9]+", "_", (stage or "").lower()).strip("_")


def _stage_rank(stage: str) -> int:
    key = _norm_stage(stage)
    if key in _STAGE_RANK:
        return _STAGE_RANK[key]
    for prefix, rank in sorted(_STAGE_RANK.items(), key=lambda x: -len(x[0])):
        if key.startswith(prefix):
            return rank
    return 3


def _ri_development_stage(comp_max_rank: int, opportunity_type: str) -> str:
    if comp_max_rank <= 2:
        return "discovery"
    if comp_max_rank <= 4:
        return "validation"
    if comp_max_rank <= 6:
        return "clinical"
    if opportunity_type in {"therapeutic", "diagnostic"}:
        return "validation"
    return "validation"


def _capital_gap_from_comparators(
    median: int | None,
    opportunity_type: str,
    program_family: str,
) -> int:
    if program_family == "ri_pharma_chemistry" or opportunity_type == "pharma_manufacturing":
        return 2_100_000
    if not median:
        return 1_200_000
    if median < 5_000_000:
        return 900_000
    if median < 50_000_000:
        return 1_200_000
    if median < 500_000_000:
        return 1_800_000
    return 2_400_000


def _clinical_weeks(opportunity_type: str, stage: str) -> int:
    if opportunity_type in {"digital_therapeutic", "software"}:
        return 36
    if stage == "clinical":
        return 52
    if stage == "discovery":
        return 24
    return 40


def _pick_lead_precedent(precedents: list[dict[str, str]]) -> dict[str, str]:
    for status in ("verified", "estimated", "suggested"):
        for p in precedents:
            if (p.get("validation_status") or "").lower() == status and _parse_usd(
                p.get("value_anchor_usd")
            ):
                return p
    return precedents[0] if precedents else {}


def _format_anchor(p: dict[str, str]) -> str:
    anchor = _parse_usd(p.get("value_anchor_usd"))
    if not anchor:
        return ""
    atype = (p.get("value_anchor_type") or "value").replace("_", " ")
    return f"{anchor:,} USD ({atype})"


def build_comparable_market_narrative(precedents: list[dict[str, str]]) -> str:
    lines: list[str] = []
    for p in sorted(precedents, key=lambda x: int(x.get("precedent_rank") or 99)):
        name = p.get("precedent_name", "")
        anchor = _format_anchor(p)
        dev = (p.get("inferred_development") or "").strip()
        fin = (p.get("inferred_financing") or "").strip()
        status = (p.get("validation_status") or "suggested").lower()
        chunk = name
        if anchor:
            chunk += f" — {anchor}"
        if dev:
            chunk += f"; path: {dev}"
        elif fin:
            chunk += f"; {fin}"
        chunk += f" [{status}]"
        lines.append(chunk)
    return " || ".join(lines)


def build_investment_thesis(row: dict[str, str], precedents: list[dict[str, str]]) -> str:
    title = row.get("title_clean") or row.get("case_id", "")
    lead = _pick_lead_precedent(precedents)
    lead_name = lead.get("precedent_name", "comparable programs")
    gap = _parse_usd(row.get("capital_gap_usd")) or 0
    vmin = _parse_usd(row.get("value_band_min_usd"))
    vmax = _parse_usd(row.get("value_band_max_usd"))
    specialties = (row.get("required_specialties") or "").replace("|", ", ")
    parts = [
        f"{title} is a Rhode Island patent-backed platform positioned to follow financing and "
        f"development paths proven by {lead_name} and peer comparables.",
    ]
    if vmin and vmax and vmin != vmax:
        parts.append(
            f"Verified comparators span {vmin:,}–{vmax:,} USD in value anchors "
            f"(raises, acquisitions, or public market caps — see precedent panel)."
        )
    elif vmin:
        parts.append(f"Lead comparable value anchor: {vmin:,} USD.")
    if lead.get("inferred_development"):
        parts.append(f"Target path: {lead['inferred_development'].strip()}.")
    if gap:
        parts.append(
            f"Near-term RI package: {gap:,} USD total ({gap // 2:,} physician syndicate + "
            f"{gap // 2:,} Slater SSBCI), sized to the earliest verified comp milestone."
        )
    if specialties:
        parts.append(f"Physician syndicate anchored in {specialties}.")
    return " ".join(parts)


def build_inferred_development_path(precedents: list[dict[str, str]]) -> str:
    steps: list[str] = []
    seen: set[str] = set()
    for p in precedents:
        dev = (p.get("inferred_development") or "").strip()
        if dev and dev not in seen:
            seen.add(dev)
            steps.append(f"{p.get('precedent_name', 'Comp')}: {dev}")
    return " → ".join(steps[:3])


def build_inferred_financing_path(precedents: list[dict[str, str]]) -> str:
    strategies: list[str] = []
    for p in precedents:
        strat = (p.get("financing_strategy") or p.get("inferred_financing") or "").strip()
        if strat:
            strategies.append(f"{p.get('precedent_name', 'Comp')}: {strat}")
    return " | ".join(strategies[:3])


def build_inferred_next_milestone(row: dict[str, str], precedents: list[dict[str, str]]) -> str:
    study = (row.get("clinical_study_type") or "").strip()
    lead = _pick_lead_precedent(precedents)
    dev = (lead.get("inferred_development") or "").strip()
    if study and dev:
        return f"{study} aligned to comp path: {dev}"
    if study:
        return study
    if dev:
        return dev
    return "Pilot validation and syndicate formation"


def infer_opportunity_package(
    row: dict[str, str],
    precedents: list[dict[str, str]],
    *,
    overwrite_template_gap: bool = True,
) -> dict[str, str]:
    """Return catalog column updates inferred from precedents."""
    if not precedents:
        return {}

    ranks = [_stage_rank(p.get("precedent_stage", "")) for p in precedents]
    comp_max = max(ranks) if ranks else 3
    opp_type = row.get("opportunity_type", "medical_device")
    program_family = row.get("program_family", "")
    ri_stage = _ri_development_stage(comp_max, opp_type)

    median = _parse_usd(row.get("value_band_median_usd"))
    gap = _capital_gap_from_comparators(median, opp_type, program_family)
    weeks = _clinical_weeks(opp_type, ri_stage)
    clinical_cost = int(gap * 0.45)
    budget_ceiling = int(gap * 1.15)

    updates: dict[str, str] = {
        "development_stage": ri_stage,
        "inferred_development_path": build_inferred_development_path(precedents),
        "inferred_financing_path": build_inferred_financing_path(precedents),
        "inferred_next_milestone": build_inferred_next_milestone(row, precedents),
        "comparable_market_narrative": build_comparable_market_narrative(precedents),
        "investment_thesis": "",  # filled after gap written
        "opportunity_enrichment_source": "comparator_inferred",
        "target_timeline_weeks": str(weeks),
        "clinical_duration_weeks": str(weeks) if not (row.get("clinical_duration_weeks") or "").strip() else row["clinical_duration_weeks"],
        "clinical_cost_usd": str(clinical_cost) if not (row.get("clinical_cost_usd") or "").strip() else row["clinical_cost_usd"],
        "budget_ceiling_usd": str(budget_ceiling),
    }

    current_gap = (row.get("capital_gap_usd") or "").strip()
    if overwrite_template_gap and (not current_gap or current_gap == TEMPLATE_CAPITAL_GAP):
        updates["capital_gap_usd"] = str(gap)

    row_for_thesis = {**row, **updates}
    updates["investment_thesis"] = build_investment_thesis(row_for_thesis, precedents)

    if not (row.get("clinical_path_notes") or "").strip():
        lead = _pick_lead_precedent(precedents)
        updates["clinical_path_notes"] = (
            f"Comparator-guided path ({lead.get('precedent_name', 'lead comp')}): "
            f"{lead.get('inferred_development') or lead.get('precedent_notes', 'pilot → regulatory')}"
        )

    status = row.get("enrichment_status", "")
    if not status or status == "draft":
        updates["enrichment_status"] = "comparator_enriched"

    return updates


def apply_to_catalog_row(
    row: dict[str, str],
    all_precedent_rows: list[dict[str, str]],
    *,
    overwrite_template_gap: bool = True,
) -> None:
    if row.get("catalog_include", "true").lower() != "true":
        return
    case_id = row["case_id"]
    precedents = [p for p in all_precedent_rows if p["case_id"] == case_id]
    precedents.sort(key=lambda p: int(p.get("precedent_rank") or 0))
    updates = infer_opportunity_package(
        row,
        precedents,
        overwrite_template_gap=overwrite_template_gap,
    )
    row.update(updates)
