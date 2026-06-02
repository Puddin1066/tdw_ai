"""Seed and resolve comparable columns in ri_cases_enriched.csv.

1. Copies comp1–comp3 from ri_program_precedents.csv when main comp columns are empty.
2. Optionally web-resolves missing value_source_url via DuckDuckGo (primary PR/SEC hits).

Does not set review_status=approved or overwrite approved comp columns.
"""

from __future__ import annotations

import argparse
import csv
from collections import defaultdict
from datetime import date
from pathlib import Path

from pipeline.bootstrap_ri_cases_enriched import _fill_comp
from pipeline.ri_cases_enriched_io import CASES_CSV, load_cases, write_cases
from pipeline.ri_cases_enriched_schema import COMP_PREFIXES, MAX_COMP_SLOTS
from pipeline.tier_a.comp_link_resolve import fetch_resolved_links, load_link_cache, write_link_cache

ROOT = Path(__file__).resolve().parents[1]
PRECEDENTS = ROOT / "data" / "ri" / "ri_program_precedents.csv"


def _bool(value: str | None) -> bool:
    return (value or "").strip().lower() in {"1", "true", "t", "yes", "y"}


def _load_precedents_by_case() -> dict[str, list[dict[str, str]]]:
    by_case: dict[str, list[dict[str, str]]] = defaultdict(list)
    if not PRECEDENTS.exists():
        return by_case
    with PRECEDENTS.open(newline="", encoding="utf-8") as handle:
        for row in csv.DictReader(handle):
            by_case[row["case_id"]].append(row)
    for cid in by_case:
        by_case[cid].sort(key=lambda r: int(r.get("precedent_rank") or 0))
    return by_case


def _comp_empty(row: dict[str, str], prefix: str) -> bool:
    return not (row.get(f"{prefix}name") or "").strip()


def _needs_url(row: dict[str, str], prefix: str) -> bool:
    name = (row.get(f"{prefix}name") or "").strip()
    if not name:
        return False
    url = (row.get(f"{prefix}value_source_url") or "").strip()
    status = (row.get(f"{prefix}validation_status") or "").lower()
    if status == "verified" and url:
        return False
    return not url


def _comp_dict(row: dict[str, str], prefix: str, rank: str) -> dict[str, str]:
    return {
        "precedent_rank": rank,
        "precedent_name": row.get(f"{prefix}name", ""),
        "precedent_type": row.get(f"{prefix}type", ""),
        "precedent_url": row.get(f"{prefix}url", ""),
        "value_source_url": row.get(f"{prefix}value_source_url", ""),
        "validation_status": row.get(f"{prefix}validation_status", ""),
    }


def _apply_resolved(row: dict[str, str], prefix: str, label: str, url: str) -> bool:
    if not url or (row.get(f"{prefix}value_source_url") or "").strip():
        return False
    row[f"{prefix}value_source_url"] = url
    notes = (row.get("web_search_notes") or "").strip()
    line = f"[comp{prefix[4]}] {label} | {url}"
    if line not in notes:
        row["web_search_notes"] = f"{notes}\n{line}".strip() if notes else line
    return True


def seed_comps_from_precedents(
    row: dict[str, str],
    precedents: list[dict[str, str]],
) -> list[str]:
    """Fill empty comp slots from precedent rows; return change tags."""
    if not precedents:
        return []
    changes: list[str] = []
    for i, comp in enumerate(precedents[:MAX_COMP_SLOTS]):
        prefix = COMP_PREFIXES[i]
        if not _comp_empty(row, prefix):
            continue
        _fill_comp(row, prefix, comp)
        changes.append(f"seed_{prefix.rstrip('_')}")
    return changes


def resolve_comp_urls(
    row: dict[str, str],
    *,
    fetch: bool,
    cache: dict | None,
) -> list[str]:
    if not fetch:
        return []
    changes: list[str] = []
    for rank, prefix in zip((str(i) for i in range(1, MAX_COMP_SLOTS + 1)), COMP_PREFIXES, strict=True):
        if not _needs_url(row, prefix):
            continue
        comp = _comp_dict(row, prefix, rank)
        resolved = fetch_resolved_links(comp)
        if resolved:
            label, url = resolved[0]
            if _apply_resolved(row, prefix, label, url):
                changes.append(f"url_{prefix.rstrip('_')}")
            if cache is not None:
                cache[(row["case_id"], rank)] = resolved
    return changes


def enrich_comps(
    *,
    path: Path = CASES_CSV,
    case_id: str | None = None,
    fetch_urls: bool = False,
    seed_only: bool = False,
    limit: int | None = None,
) -> tuple[int, int]:
    rows = load_cases(path)
    precedents_by = _load_precedents_by_case()
    cache = load_link_cache() if fetch_urls else {}
    today = date.today().isoformat()
    touched = 0
    processed = 0

    for row in rows:
        if not _bool(row.get("catalog_include", "true")):
            continue
        if (row.get("review_status") or "").lower() == "approved":
            continue
        if case_id and row.get("case_id") != case_id:
            continue
        if limit is not None and processed >= limit:
            break
        processed += 1
        cid = row.get("case_id", "")
        print(f"Comp enrich: {cid} …", flush=True)

        changes: list[str] = []
        changes.extend(seed_comps_from_precedents(row, precedents_by.get(cid, [])))
        if fetch_urls and not seed_only:
            changes.extend(resolve_comp_urls(row, fetch=True, cache=cache))

        if changes:
            row["last_refreshed_at"] = today
            row["enrichment_status"] = "comps_enriched"
            touched += 1
            print(f"  -> {', '.join(changes)}", flush=True)

    if cache:
        write_link_cache(cache)
    write_cases(rows, path)
    return len(rows), touched


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--path", type=Path, default=CASES_CSV)
    parser.add_argument("--case-id", help="Single case_id")
    parser.add_argument(
        "--fetch-urls",
        action="store_true",
        help="Web-resolve missing comp value_source_url (slow)",
    )
    parser.add_argument(
        "--seed-only",
        action="store_true",
        help="Only seed from precedents; skip URL fetch even if --fetch-urls",
    )
    parser.add_argument("--limit", type=int, help="Max catalog rows to process")
    args = parser.parse_args()
    total, touched = enrich_comps(
        path=args.path,
        case_id=args.case_id,
        fetch_urls=args.fetch_urls,
        seed_only=args.seed_only,
        limit=args.limit,
    )
    print(f"Comp-enriched {touched} rows -> {args.path} ({total} total)")


if __name__ == "__main__":
    main()
