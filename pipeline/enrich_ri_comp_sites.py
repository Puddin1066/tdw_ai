"""Enrich RI comparators from company websites (literature, KOL, reimbursement signals).

Writes:
  - data/ri/ri_comp_site_dossiers.json

Usage:
  python -m pipeline.enrich_ri_comp_sites --tier A --fetch
  python -m pipeline.enrich_ri_comp_sites --case-id theromics_ri --fetch --refresh
  python -m pipeline.enrich_ri_comp_sites --seed-fixture
"""

from __future__ import annotations

import argparse
import csv
from pathlib import Path
from typing import Any

import httpx

from pipeline.comp_site_dossier import (
    DOSSIERS_PATH,
    FIXTURE_PATH,
    dossier_key,
    empty_bundle,
    load_dossier_bundle,
    rebuild_by_case_index,
    save_dossier_bundle,
    select_precedents_for_enrichment,
    wrap_dossier_entry,
)
from pipeline.comp_site_extract import fetch_comp_site_dossier

DATA = Path(__file__).resolve().parents[1] / "data" / "ri"
CATALOG_PATH = DATA / "ri_opportunities_catalog_enrichment.csv"
PRECEDENTS_PATH = DATA / "ri_program_precedents.csv"


def _bool(value: str | None) -> bool:
    return (value or "").strip().lower() in {"1", "true", "t", "yes", "y"}


def _load_catalog(*, tier: str | None, case_id: str | None) -> list[dict[str, str]]:
    rows = list(csv.DictReader(CATALOG_PATH.open(encoding="utf-8")))
    out: list[dict[str, str]] = []
    for row in rows:
        if not _bool(row.get("catalog_include", "true")):
            continue
        if case_id and row["case_id"] != case_id:
            continue
        if tier and (row.get("catalog_tier") or "").upper() != tier.upper():
            continue
        out.append(row)
    return out


def _load_precedents_by_case() -> dict[str, list[dict[str, str]]]:
    by_case: dict[str, list[dict[str, str]]] = {}
    if not PRECEDENTS_PATH.exists():
        return by_case
    for row in csv.DictReader(PRECEDENTS_PATH.open(encoding="utf-8")):
        by_case.setdefault(row["case_id"], []).append(row)
    for cid in by_case:
        by_case[cid].sort(key=lambda r: int(r.get("precedent_rank") or 99))
    return by_case


def enrich_case(
    *,
    row: dict[str, str],
    precedents: list[dict[str, str]],
    bundle: dict[str, Any],
    fetch: bool,
    refresh: bool,
    max_comps: int,
    client: httpx.Client | None,
) -> tuple[int, int]:
    case_id = row["case_id"]
    case_title = row.get("title_clean") or row.get("display_name") or case_id
    updated = 0
    skipped = 0

    for precedent in select_precedents_for_enrichment(precedents, max_comps=max_comps):
        name = precedent["precedent_name"]
        key = dossier_key(case_id, name)
        existing = (bundle.get("by_key") or {}).get(key)
        if existing and existing.get("human_reviewed") and not refresh:
            skipped += 1
            continue
        if existing and not refresh:
            skipped += 1
            continue

        url = (precedent.get("precedent_url") or "").strip()
        if not url:
            skipped += 1
            continue

        human_reviewed = bool(existing and existing.get("human_reviewed"))
        if fetch:
            body, warnings = fetch_comp_site_dossier(
                precedent_name=name,
                corporate_url=url,
                client=client,
            )
            entry = wrap_dossier_entry(
                case_id=case_id,
                case_title=case_title,
                precedent=precedent,
                dossier_body=body,
                warnings=warnings,
                fetched=True,
                human_reviewed=human_reviewed,
            )
        else:
            entry = wrap_dossier_entry(
                case_id=case_id,
                case_title=case_title,
                precedent=precedent,
                dossier_body={
                    "precedent_name": name,
                    "corporate_url": url,
                    "site_map": {"corporate": url},
                    "science_summary": (precedent.get("precedent_notes") or "")[:480],
                    "key_publications": [],
                    "clinical_milestones": [],
                    "kol_signals": [],
                    "reimbursement_notes": [],
                },
                warnings=["fetch disabled; corporate URL only"],
                fetched=False,
                human_reviewed=human_reviewed,
            )

        bundle.setdefault("by_key", {})[key] = entry
        updated += 1

    return updated, skipped


def run_enrichment(
    *,
    tier: str | None = "A",
    case_id: str | None = None,
    fetch: bool = False,
    refresh: bool = False,
    max_comps: int = 2,
) -> dict[str, int]:
    if not CATALOG_PATH.exists():
        raise FileNotFoundError(f"Missing catalog CSV: {CATALOG_PATH}")
    if not PRECEDENTS_PATH.exists():
        raise FileNotFoundError(f"Missing precedents CSV: {PRECEDENTS_PATH} (run build_ri_precedents)")

    catalog_rows = _load_catalog(tier=tier if not case_id else None, case_id=case_id)
    precedents_by = _load_precedents_by_case()
    bundle = load_dossier_bundle()

    total_updated = 0
    total_skipped = 0
    client = httpx.Client(timeout=20.0, follow_redirects=True) if fetch else None
    try:
        for row in catalog_rows:
            precedents = precedents_by.get(row["case_id"], [])
            updated, skipped = enrich_case(
                row=row,
                precedents=precedents,
                bundle=bundle,
                fetch=fetch,
                refresh=refresh,
                max_comps=max_comps,
                client=client,
            )
            total_updated += updated
            total_skipped += skipped
    finally:
        if client:
            client.close()

    rebuild_by_case_index(bundle)
    save_dossier_bundle(bundle)
    return {
        "cases": len(catalog_rows),
        "dossiers_updated": total_updated,
        "dossiers_skipped": total_skipped,
        "dossier_count": len(bundle.get("by_key") or {}),
    }


def seed_fixture() -> Path:
    if not FIXTURE_PATH.exists():
        raise FileNotFoundError(f"Missing fixture: {FIXTURE_PATH}")
    import shutil

    DOSSIERS_PATH.parent.mkdir(parents=True, exist_ok=True)
    shutil.copy2(FIXTURE_PATH, DOSSIERS_PATH)
    bundle = load_dossier_bundle(DOSSIERS_PATH)
    save_dossier_bundle(bundle, DOSSIERS_PATH)
    return DOSSIERS_PATH


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Enrich RI comparators from company websites")
    parser.add_argument("--tier", default="A", help="Catalog tier filter (default A)")
    parser.add_argument("--case-id", help="Single case_id")
    parser.add_argument("--fetch", action="store_true", help="HTTP fetch comp websites (default: stub only)")
    parser.add_argument("--refresh", action="store_true", help="Re-fetch even if dossier exists")
    parser.add_argument("--max-comps", type=int, default=2, help="Max comparators per case")
    parser.add_argument("--seed-fixture", action="store_true", help="Copy tests/fixtures/ri/comp_site_dossiers.json")
    args = parser.parse_args(argv)

    if args.seed_fixture:
        path = seed_fixture()
        print(f"Seeded dossier bundle -> {path}")
        return 0

    stats = run_enrichment(
        tier=args.tier,
        case_id=args.case_id,
        fetch=args.fetch,
        refresh=args.refresh,
        max_comps=max(1, args.max_comps),
    )
    print(f"Wrote {stats['dossier_count']} dossier(s) -> {DOSSIERS_PATH}")
    for key, value in stats.items():
        print(f"  {key}: {value}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
