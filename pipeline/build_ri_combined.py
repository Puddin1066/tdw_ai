"""Build UI-ready RI opportunity artifacts from enriched catalog CSV.

Workflow (legacy):
  1. Curate / enrich: data/ri/ri_opportunities_catalog_enrichment.csv
  2. Build precedents: python -m pipeline.build_ri_precedents
  3. Build artifacts:  python -m pipeline.build_ri_combined

Workflow (canonical monolithic CSV):
  1. Bootstrap: python -m pipeline.bootstrap_ri_cases_enriched
  2. Suggest / edit: data/ri/ri_cases_enriched.csv
  3. Validate: python -m pipeline.validate_ri_cases_enriched
  4. Build: python -m pipeline.build_ri_combined --from cases-enriched

Outputs (schema v2):
  - data/ri/ri_opportunities_combined.json
  - web/public/data/ri/opportunities_combined.json
"""

from __future__ import annotations

import argparse
import csv
import json
import shutil
from pathlib import Path
from typing import Any

from pipeline.build_ri_exhibit import build_catalog_card, build_exhibit
from pipeline.comp_site_dossier import case_rollup, dossiers_for_case, load_dossier_bundle
from pipeline.physician_assignment import compute_assignments_for_enriched_rows
from pipeline.ri_cases_enriched_io import (
    CASES_CSV,
    catalog_row_from_enriched,
    comps_from_row,
    evidence_from_row,
    ip_from_row,
    load_cases,
    physicians_from_row,
)

ROOT = Path(__file__).resolve().parents[1]
DATA = ROOT / "data" / "ri"
CATALOG = DATA / "ri_opportunities_catalog_enrichment.csv"
PRECEDENTS = DATA / "ri_program_precedents.csv"
IP_ASSETS = DATA / "ri_ip_assets.csv"
EVIDENCE = DATA / "ri_opportunity_evidence.json"
DOSSIERS = DATA / "ri_comp_site_dossiers.json"
OUT_JSON = DATA / "ri_opportunities_combined.json"
WEB_JSON = ROOT / "web" / "public" / "data" / "ri" / "opportunities_combined.json"

SCHEMA_VERSION = 2


def _bool(value: str | None) -> bool:
    return (value or "").strip().lower() in {"1", "true", "t", "yes", "y"}


def _parse_physicians(row: dict[str, str]) -> list[dict[str, str]]:
    """Build syndicate roster; dedupe by physician_id (lead wins over supporters)."""
    roster: list[dict[str, str]] = []
    seen: set[str] = set()

    def _key(physician_id: str, name: str) -> str:
        pid = physician_id.strip()
        if pid:
            return pid
        return f"name:{name.strip().upper()}"

    lead_npi = (row.get("physician_lead_npi") or "").strip()
    lead_name = (row.get("physician_lead_name") or "").strip()
    if lead_npi or lead_name:
        roster.append(
            {
                "physician_id": lead_npi,
                "name": lead_name,
                "specialty": row.get("physician_lead_specialty", ""),
                "institution": row.get("physician_lead_institution", ""),
                "roles_matched": "lead",
                "is_lead": "true",
            }
        )
        seen.add(_key(lead_npi, lead_name))

    block = row.get("physician_supporters") or ""
    for line in block.splitlines():
        line = line.strip()
        if not line:
            continue
        parts = line.split("|")
        if len(parts) < 4:
            continue
        physician_id = parts[0].strip()
        name = parts[1].strip()
        dedupe_key = _key(physician_id, name)
        if dedupe_key in seen:
            continue
        seen.add(dedupe_key)
        roster.append(
            {
                "physician_id": physician_id,
                "name": name,
                "specialty": parts[2],
                "institution": parts[3],
                "roles_matched": parts[4] if len(parts) > 4 else "reviewer",
                "is_lead": "false",
            }
        )
    return roster


def _load_precedents() -> dict[str, list[dict[str, Any]]]:
    by_case: dict[str, list[dict[str, Any]]] = {}
    if not PRECEDENTS.exists():
        return by_case
    for r in csv.DictReader(PRECEDENTS.open(encoding="utf-8")):
        cid = r["case_id"]
        by_case.setdefault(cid, []).append(
            {
                "rank": int(r.get("precedent_rank") or 0),
                "type": r.get("precedent_type", ""),
                "name": r.get("precedent_name", ""),
                "stage": r.get("precedent_stage", ""),
                "notes": r.get("precedent_notes", ""),
                "url": r.get("precedent_url", ""),
                "inferred_development": r.get("inferred_development", ""),
                "inferred_financing": r.get("inferred_financing", ""),
                "inferred_team": r.get("inferred_team", ""),
                "total_raised_usd_est": r.get("total_raised_usd_est", ""),
                "last_round_usd_est": r.get("last_round_usd_est", ""),
                "value_anchor_usd": r.get("value_anchor_usd", ""),
                "value_anchor_type": r.get("value_anchor_type", ""),
                "value_source_url": r.get("value_source_url", ""),
                "financing_strategy": r.get("financing_strategy", ""),
                "validation_status": r.get("validation_status", ""),
                "confidence": r.get("confidence", ""),
                "source": r.get("source", ""),
            }
        )
    for cid in by_case:
        by_case[cid].sort(key=lambda x: x["rank"])
    return by_case


def _load_evidence() -> dict[str, dict[str, Any]]:
    if not EVIDENCE.exists():
        return {}
    data = json.loads(EVIDENCE.read_text(encoding="utf-8"))
    return data.get("by_case_id") or {}


def _load_ip() -> dict[str, list[dict[str, str]]]:
    by_case: dict[str, list[dict[str, str]]] = {}
    if not IP_ASSETS.exists():
        return by_case
    for r in csv.DictReader(IP_ASSETS.open(encoding="utf-8")):
        cid = r["case_id"]
        lens = r.get("lens_id", "")
        by_case.setdefault(cid, []).append(
            {
                "lens_id": lens,
                "display_key": r.get("display_key", ""),
                "title": r.get("title", ""),
                "owners": (r.get("owners") or "").replace(";;", "; "),
                "url": f"https://lens.org/{lens}" if lens else "",
            }
        )
    return by_case


def build_legacy(dossier_bundle: dict[str, Any] | None = None) -> tuple[list[dict[str, Any]], list[dict[str, Any]]]:
    precedents_by = _load_precedents()
    ip_by = _load_ip()
    evidence_by = _load_evidence()
    dossiers_bundle = dossier_bundle if dossier_bundle is not None else load_dossier_bundle(DOSSIERS)
    opportunities: list[dict[str, Any]] = []
    catalog_cards: list[dict[str, Any]] = []

    for row in csv.DictReader(CATALOG.open(encoding="utf-8")):
        if not _bool(row.get("catalog_include", "true")):
            continue
        case_id = row["case_id"]
        precedents = precedents_by.get(case_id, [])
        ip_assets = ip_by.get(case_id, [])
        physicians = _parse_physicians(row)
        case_dossiers = dossiers_for_case(dossiers_bundle, case_id)
        exhibit = build_exhibit(
            row,
            precedents,
            ip_assets,
            physicians,
            evidence_by.get(case_id),
            comp_dossiers=case_dossiers,
            comp_rollup=case_rollup(dossiers_bundle, case_id),
        )

        opportunities.append({"case_id": case_id, "exhibit": exhibit})
        catalog_cards.append(build_catalog_card(case_id, exhibit))

    return opportunities, catalog_cards


def build_from_cases_enriched(
    dossier_bundle: dict[str, Any] | None = None,
    *,
    approved_only: bool = False,
) -> tuple[list[dict[str, Any]], list[dict[str, Any]]]:
    dossiers_bundle = dossier_bundle if dossier_bundle is not None else load_dossier_bundle(DOSSIERS)
    catalog_rows = [
        raw
        for raw in load_cases(CASES_CSV)
        if _bool(raw.get("catalog_include", "true"))
        and (not approved_only or (raw.get("review_status") or "").lower() == "approved")
    ]
    physician_assignments = compute_assignments_for_enriched_rows(catalog_rows, catalog_only=False)
    opportunities: list[dict[str, Any]] = []
    catalog_cards: list[dict[str, Any]] = []

    for raw in catalog_rows:
        case_id = raw["case_id"]
        row = catalog_row_from_enriched(dict(raw))
        precedents = comps_from_row(raw)
        ip_assets = ip_from_row(raw)
        physicians = physicians_from_row(raw)
        evidence = evidence_from_row(raw)
        case_dossiers = dossiers_for_case(dossiers_bundle, case_id)
        exhibit = build_exhibit(
            row,
            precedents,
            ip_assets,
            physicians,
            evidence,
            comp_dossiers=case_dossiers,
            comp_rollup=case_rollup(dossiers_bundle, case_id),
            physician_match=physician_assignments.get(case_id),
        )
        opportunities.append({"case_id": case_id, "exhibit": exhibit})
        catalog_cards.append(build_catalog_card(case_id, exhibit))

    return opportunities, catalog_cards


def build(
    *,
    source: str = "legacy",
    dossier_bundle: dict[str, Any] | None = None,
    approved_only: bool = False,
) -> tuple[list[dict[str, Any]], list[dict[str, Any]]]:
    if source == "cases-enriched":
        return build_from_cases_enriched(dossier_bundle, approved_only=approved_only)
    return build_legacy(dossier_bundle)


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--from",
        dest="source",
        choices=("legacy", "cases-enriched"),
        default="cases-enriched",
        help="Input source (default: cases-enriched monolithic CSV)",
    )
    parser.add_argument(
        "--approved-only",
        action="store_true",
        help="Only include review_status=approved rows",
    )
    args = parser.parse_args()

    opportunities, catalog_cards = build(
        source=args.source,
        approved_only=args.approved_only,
    )
    generated_from = (
        ["data/ri/ri_cases_enriched.csv", "data/ri/ri_comp_site_dossiers.json"]
        if args.source == "cases-enriched"
        else [
            "data/ri/ri_opportunities_catalog_enrichment.csv",
            "data/ri/ri_program_precedents.csv",
            "data/ri/ri_ip_assets.csv",
            "data/ri/ri_opportunity_evidence.json",
            "data/ri/ri_comp_site_dossiers.json",
        ]
    )
    payload = {
        "schema_version": SCHEMA_VERSION,
        "generated_from": generated_from,
        "source_mode": args.source,
        "opportunity_count": len(opportunities),
        "catalog_cards": catalog_cards,
        "opportunities": opportunities,
    }
    OUT_JSON.write_text(json.dumps(payload, indent=2), encoding="utf-8")
    WEB_JSON.parent.mkdir(parents=True, exist_ok=True)
    shutil.copy2(OUT_JSON, WEB_JSON)
    print(f"Wrote schema v{SCHEMA_VERSION} ({args.source}): {len(opportunities)} opportunities -> {OUT_JSON}")
    print(f"Catalog cards: {len(catalog_cards)}")
    print(f"Copied -> {WEB_JSON}")


if __name__ == "__main__":
    main()
