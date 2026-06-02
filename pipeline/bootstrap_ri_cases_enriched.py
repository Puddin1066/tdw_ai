"""Bootstrap data/ri/ri_cases_enriched.csv from catalog, IP, comparables, and evidence."""

from __future__ import annotations

import csv
from collections import defaultdict
from datetime import date
from pathlib import Path

from pipeline.ri_cases_enriched_io import (
    CASES_CSV,
    apply_finance_defaults,
    empty_row,
    load_cases,
    write_cases,
)
from pipeline.ri_cases_enriched_schema import COMP_PREFIXES, FIELDNAMES, MAX_COMP_SLOTS

ROOT = Path(__file__).resolve().parents[1]
DATA = ROOT / "data" / "ri"
CATALOG = DATA / "ri_opportunities_catalog_enrichment.csv"
IP_ASSETS = DATA / "ri_ip_assets.csv"
PRECEDENTS = DATA / "ri_program_precedents.csv"
TIER_A_COMPARABLES = DATA / "tier_a" / "comparables.csv"
EVIDENCE = DATA / "ri_opportunity_evidence.json"


def _bool(value: str | None) -> bool:
    return (value or "").strip().lower() in {"1", "true", "t", "yes", "y"}


def _load_csv(path: Path) -> list[dict[str, str]]:
    if not path.exists():
        return []
    with path.open(newline="", encoding="utf-8") as handle:
        return list(csv.DictReader(handle))


def _load_comparables_by_case() -> dict[str, list[dict[str, str]]]:
    """Merge program precedents with tier-A overrides (tier-A wins per case_id)."""
    by_case: dict[str, list[dict[str, str]]] = defaultdict(list)
    for row in _load_csv(PRECEDENTS):
        by_case[row["case_id"]].append(row)
    tier_rows = _load_csv(TIER_A_COMPARABLES) if TIER_A_COMPARABLES.exists() else []
    tier_by_case: dict[str, list[dict[str, str]]] = defaultdict(list)
    for row in tier_rows:
        tier_by_case[row["case_id"]].append(row)
    for case_id, tier_comps in tier_by_case.items():
        tier_comps.sort(key=lambda r: int(r.get("precedent_rank") or 0))
        by_case[case_id] = tier_comps
    for cid in by_case:
        by_case[cid].sort(key=lambda r: int(r.get("precedent_rank") or 0))
    return by_case


def _load_ip_by_case() -> dict[str, list[dict[str, str]]]:
    by_case: dict[str, list[dict[str, str]]] = defaultdict(list)
    for row in _load_csv(IP_ASSETS):
        by_case[row["case_id"]].append(row)
    return by_case


def _assignee_from_owners(owners: str) -> str:
    if not owners:
        return ""
    first = owners.split(";;")[0].split(";")[0].strip()
    return first.split("(")[0].strip()


def _fill_patents(row: dict[str, str], ip_rows: list[dict[str, str]], catalog: dict[str, str]) -> None:
    primary = (catalog.get("primary_lens_id") or "").strip()
    if not ip_rows and primary:
        lens = primary
        row["primary_lens_id"] = lens
        row["primary_display_key"] = catalog.get("primary_display_key", "")
        row["primary_patent_title"] = catalog.get("primary_patent_title", "")
        row["primary_patent_url"] = f"https://lens.org/{lens}"
        row["ip_lens_ids"] = lens
        return
    ordered = ip_rows
    if primary:
        prim = [a for a in ip_rows if a.get("lens_id") == primary]
        rest = [a for a in ip_rows if a.get("lens_id") != primary]
        ordered = prim + rest
    ordered = ordered[:2]
    if not ordered:
        return
    lead = ordered[0]
    lens = lead.get("lens_id", "")
    row["primary_lens_id"] = lens
    row["primary_display_key"] = lead.get("display_key", "")
    row["primary_patent_title"] = lead.get("title", "")
    row["primary_patent_url"] = f"https://lens.org/{lens}" if lens else ""
    row["assignee_company"] = _assignee_from_owners(lead.get("owners", ""))
    row["inventors"] = (lead.get("inventors") or "").replace(";;", "|")
    row["ip_lens_ids"] = "|".join(a.get("lens_id", "") for a in ordered)
    row["ip_titles"] = "\n".join(a.get("title", "") for a in ordered)
    row["ip_urls"] = "\n".join(
        f"https://lens.org/{a.get('lens_id', '')}" for a in ordered if a.get("lens_id")
    )


def _fill_comp(row: dict[str, str], prefix: str, comp: dict[str, str]) -> None:
    row[f"{prefix}name"] = comp.get("precedent_name", "")
    row[f"{prefix}type"] = comp.get("precedent_type", "")
    row[f"{prefix}role"] = comp.get("comp_role") or comp.get("precedent_role", "")
    row[f"{prefix}stage"] = comp.get("precedent_stage", "")
    row[f"{prefix}url"] = comp.get("precedent_url", "")
    row[f"{prefix}notes"] = comp.get("precedent_notes", "")
    row[f"{prefix}value_anchor_usd"] = comp.get("value_anchor_usd", "")
    row[f"{prefix}value_anchor_type"] = comp.get("value_anchor_type", "")
    row[f"{prefix}value_source_url"] = comp.get("value_source_url", "")
    row[f"{prefix}total_raised_usd"] = comp.get("total_raised_usd_est", "")
    row[f"{prefix}last_round_usd"] = comp.get("last_round_usd_est", "")
    row[f"{prefix}financing_ladder"] = comp.get("inferred_financing", "")
    row[f"{prefix}development_path"] = comp.get("inferred_development", "")
    row[f"{prefix}validation_status"] = comp.get("validation_status", "suggested")
    row[f"{prefix}supporting_citations"] = comp.get("supporting_citations", "")


def _fill_catalog_identity(row: dict[str, str], cat: dict[str, str]) -> None:
    mapping = {
        "case_id": "case_id",
        "catalog_tier": "catalog_tier",
        "catalog_include": "catalog_include",
        "title_clean": "title_clean",
        "display_name": "display_name",
        "company": "company",
        "indication": "indication",
        "opportunity_type": "opportunity_type",
        "development_stage": "development_stage",
        "data_caveat": "data_caveat",
        "ri_notes": "ri_notes",
        "physician_lead_npi": "physician_lead_npi",
        "physician_lead_name": "physician_lead_name",
        "physician_supporters": "physician_supporters",
        "clinical_study_type": "clinical_study_type",
        "clinical_primary_endpoint": "clinical_primary_endpoint",
        "clinical_duration_weeks": "clinical_duration_weeks",
        "clinical_cost_usd": "clinical_cost_usd",
        "clinical_path_notes": "clinical_path_notes",
        "target_timeline_weeks": "target_timeline_weeks",
        "investment_thesis": "investment_thesis",
        "mcq_lead_pillar": "mcq_lead_pillar",
        "mcq_financing_structure": "mcq_financing_structure",
        "mcq_audience": "mcq_audience",
        "required_specialties": "required_specialties",
        "clinical_tags": "clinical_tags",
        "program_family": "program_family",
    }
    for src, dst in mapping.items():
        if cat.get(src):
            row[dst] = cat[src]
    row["ri_institution"] = cat.get("ri_physician_lead", "") or row.get("ri_institution", "")
    if not row.get("investment_thesis") and cat.get("investment_thesis"):
        row["investment_thesis"] = cat["investment_thesis"]


def _fill_biomcp_suggest(row: dict[str, str], evidence: dict | None) -> None:
    if not evidence:
        return
    pubs = evidence.get("publications") or []
    if not pubs:
        return
    titles: list[str] = []
    urls: list[str] = []
    notes: list[str] = []
    for pub in pubs[:8]:
        title = (pub.get("title") or "").strip()
        if not title:
            continue
        pmid = (pub.get("pmid") or "").strip()
        url = (pub.get("url") or "").strip()
        if pmid and not url:
            url = f"https://pubmed.ncbi.nlm.nih.gov/{pmid}/"
        titles.append(title)
        urls.append(url)
        inv = pub.get("patent_link", {}).get("matched_inventor_surnames", [])
        notes.append(f"BioMCP; inventors: {', '.join(inv)}" if inv else "BioMCP suggestion")
    row["suggest_publication_titles"] = "\n".join(titles)
    row["suggest_publication_urls"] = "\n".join(urls)
    row["suggest_publication_notes"] = "\n".join(notes)


def _preserve_manual(existing: dict[str, str], row: dict[str, str]) -> None:
    """Keep curator-approved fields from existing file."""
    if (existing.get("review_status") or "").lower() != "approved":
        return
    preserve = [
        "review_status",
        "reviewer",
        "publication_titles",
        "publication_lead_authors",
        "publication_ri_affiliations",
        "publication_urls",
        "publication_pmids",
        "publication_count",
        "literature_narrative",
        "physician_lead_profile_url",
        "physician_supporter_profile_urls",
        "financing_rationale",
        "rd_plan_summary",
        "rd_milestones",
    ]
    for p in COMP_PREFIXES:
        preserve.extend(
            [
                f"{p}value_source_url",
                f"{p}validation_status",
                f"{p}financing_ladder",
            ]
        )
    preserve.extend(
        [
            "total_package_usd",
            "physician_share_usd",
            "slater_share_usd",
        ]
    )
    for key in preserve:
        if (existing.get(key) or "").strip():
            row[key] = existing[key]


def bootstrap(*, preserve_approved: bool = True) -> list[dict[str, str]]:
    catalog_rows = [r for r in _load_csv(CATALOG) if _bool(r.get("catalog_include", "true"))]
    comps_by = _load_comparables_by_case()
    ip_by = _load_ip_by_case()
    existing_by = {r["case_id"]: r for r in load_cases()} if preserve_approved else {}

    evidence_by: dict = {}
    if EVIDENCE.exists():
        import json

        payload = json.loads(EVIDENCE.read_text(encoding="utf-8"))
        evidence_by = payload.get("by_case_id") or {}

    today = date.today().isoformat()
    out: list[dict[str, str]] = []

    for cat in catalog_rows:
        case_id = cat["case_id"]
        row = empty_row(case_id)
        _fill_catalog_identity(row, cat)
        _fill_patents(row, ip_by.get(case_id, []), cat)
        comps = comps_by.get(case_id, [])[:MAX_COMP_SLOTS]
        for i, comp in enumerate(comps):
            _fill_comp(row, COMP_PREFIXES[i], comp)
        _fill_biomcp_suggest(row, evidence_by.get(case_id))
        apply_finance_defaults(row)
        row["last_refreshed_at"] = today
        row["review_status"] = row.get("review_status") or "pending"
        row["enrichment_status"] = "canonical_csv"
        if not row.get("financing_rationale"):
            row["financing_rationale"] = (
                f"Seed/Series A RI package capped at policy limit; "
                f"50% physician syndicate / 50% Slater SSBCI match."
            )
        if preserve_approved and case_id in existing_by:
            _preserve_manual(existing_by[case_id], row)
        out.append(row)

    write_cases(out)
    return out


def main() -> None:
    rows = bootstrap()
    pending = sum(1 for r in rows if (r.get("review_status") or "").lower() != "approved")
    approved = len(rows) - pending
    print(f"Wrote {len(rows)} rows -> {CASES_CSV}")
    print(f"  approved: {approved}, pending: {pending}")
    print("Next: npm run ri:cases:suggest && edit CSV && npm run ri:cases:validate && npm run ri:cases:build")


if __name__ == "__main__":
    main()
