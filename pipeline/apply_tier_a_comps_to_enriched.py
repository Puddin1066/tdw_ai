"""Sync tier_a/comparables.csv into ri_cases_enriched comp1–comp6 columns.

For each catalog row with curated Tier A comparables, overwrites comp slots
(not review_status=approved rows) with verified tier-A data including roles
and supporting citation lines.
"""

from __future__ import annotations

import argparse
from datetime import date
from pathlib import Path

from pipeline.bootstrap_ri_cases_enriched import _fill_comp
from pipeline.ri_cases_enriched_io import CASES_CSV, load_cases, write_cases
from pipeline.ri_cases_enriched_schema import COMP_PREFIXES, MAX_COMP_SLOTS
from pipeline.tier_a.io import comparables_by_case

PRIMARY_URL_HINTS = (
    "sec.gov",
    "prnewswire.com",
    "businesswire.com",
    "globenewswire.com",
    "accesswire.com",
    "fda.gov",
    "pubmed",
    "pmc.ncbi",
    "clinicaltrials.gov",
    "finance.yahoo.com",
    "stockanalysis.com",
    "macrotrends.net",
    "investors.",
    "/newsroom/",
    "/press-release",
)


def _bool(value: str | None) -> bool:
    return (value or "").strip().lower() in {"1", "true", "t", "yes", "y"}


def _is_primary_url(url: str) -> bool:
    lower = url.lower()
    return any(h in lower for h in PRIMARY_URL_HINTS)


def _infer_role(comp: dict[str, str]) -> str:
    ptype = (comp.get("precedent_type") or "").lower()
    notes = (comp.get("precedent_notes") or "").lower()
    name = (comp.get("precedent_name") or "").lower()
    if comp.get("comp_role"):
        return comp["comp_role"]
    if any(k in notes or k in name for k in ("diagnostic", " dx", "host rna", "host-response", "triage", "lvo")):
        return "diagnostic"
    if any(k in notes or k in name for k in ("therapeutic", "biologic", "opioid", "c1 inhibitor", "plasma-derived")):
        return "therapeutic"
    if ptype in {"pharma_deal", "public"} and "acquisition" in notes:
        return "pharma_deal"
    if ptype == "incumbent":
        return "incumbent"
    if ptype == "ri_operating":
        return "operating"
    if ptype == "research":
        return "research"
    return "platform"


def _supporting_citations(comp: dict[str, str]) -> str:
    if comp.get("supporting_citations"):
        return comp["supporting_citations"]
    lines: list[str] = []
    vsrc = (comp.get("value_source_url") or "").strip()
    purl = (comp.get("precedent_url") or "").strip()
    if vsrc and purl and vsrc.rstrip("/") != purl.rstrip("/"):
        lines.append(f"Company / program | {purl}")
    notes = (comp.get("precedent_notes") or "").strip()
    if notes and len(notes) > 20 and purl and not lines:
        lines.append(f"Program notes (see company) | {purl}")
    return "\n".join(lines)


def _normalize_comp(comp: dict[str, str]) -> dict[str, str]:
    out = dict(comp)
    vsrc = (out.get("value_source_url") or "").strip()
    purl = (out.get("precedent_url") or "").strip()
    if not vsrc and purl and _is_primary_url(purl):
        out["value_source_url"] = purl
    out["comp_role"] = _infer_role(out)
    out["supporting_citations"] = _supporting_citations(out)
    return out


def _clear_comp(row: dict[str, str], prefix: str) -> None:
    for suffix in (
        "name", "type", "role", "stage", "url", "notes",
        "value_anchor_usd", "value_anchor_type", "value_source_url",
        "total_raised_usd", "last_round_usd", "financing_ladder",
        "development_path", "validation_status", "supporting_citations",
    ):
        row[f"{prefix}{suffix}"] = ""


def apply_tier_a_comps(
    *,
    path: Path = CASES_CSV,
    tier: str | None = "A",
    case_id: str | None = None,
) -> tuple[int, int]:
    rows = load_cases(path)
    by_case = comparables_by_case()
    today = date.today().isoformat()
    touched = 0

    for row in rows:
        if not _bool(row.get("catalog_include", "true")):
            continue
        if (row.get("review_status") or "").lower() == "approved":
            continue
        cid = row["case_id"]
        if case_id and cid != case_id:
            continue
        if tier and (row.get("catalog_tier") or "").upper() != tier.upper():
            continue
        comps = by_case.get(cid, [])
        if not comps:
            continue

        for prefix in COMP_PREFIXES:
            _clear_comp(row, prefix)
        for i, comp in enumerate(comps[:MAX_COMP_SLOTS]):
            _fill_comp(row, COMP_PREFIXES[i], _normalize_comp(comp))

        row["last_refreshed_at"] = today
        row["enrichment_status"] = "tier_a_comps_synced"
        touched += 1

    write_cases(rows, path)
    return len(rows), touched


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--path", type=Path, default=CASES_CSV)
    parser.add_argument("--tier", default="A", help="Catalog tier (default A; use ALL to sync every case in tier_a CSV)")
    parser.add_argument("--case-id", help="Single case_id")
    args = parser.parse_args()
    tier = None if (args.tier or "").upper() == "ALL" else args.tier
    total, touched = apply_tier_a_comps(path=args.path, tier=tier, case_id=args.case_id)
    print(f"Synced Tier A comps on {touched} rows -> {args.path} ({total} total)")


if __name__ == "__main__":
    main()
