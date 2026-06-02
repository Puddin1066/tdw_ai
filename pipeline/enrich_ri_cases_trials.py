"""Re-run clinical trial enrichment for ri_cases_enriched.csv.

Clears poisoned trial_* fields and re-resolves with mechanism/comp-precedent
queries. Use after changing ri_trial_enrichment policy.
"""

from __future__ import annotations

import argparse
from pathlib import Path

from pipeline.enrich_ri_cases_full_web import fill_trials_from_web
from pipeline.ri_cases_enriched_io import CASES_CSV, load_cases, write_cases
from pipeline.remediate_ri_cases_enriched import remediate


def _bool(value: str | None) -> bool:
    return (value or "").strip().lower() in {"1", "true", "t", "yes", "y"}


def enrich_trials(
    *,
    path: Path = CASES_CSV,
    tier: str | None = None,
    case_id: str | None = None,
    limit: int | None = None,
) -> dict[str, int]:
    remediate(path=path)
    rows = load_cases(path)
    touched = 0
    main = suggest = empty = 0
    processed = 0

    for row in rows:
        if case_id and row.get("case_id") != case_id:
            continue
        if tier and (row.get("catalog_tier") or "").upper() != tier.upper():
            continue
        if not _bool(row.get("catalog_include", "true")):
            continue
        if limit is not None and processed >= limit:
            break

        processed += 1
        changes = fill_trials_from_web(row, force=True)
        if not changes:
            continue
        touched += 1
        if "trials_main" in changes:
            main += 1
        if "trials_suggest" in changes:
            suggest += 1
        if "trials_empty" in changes:
            empty += 1

    write_cases(rows, path=path)
    return {
        "processed": processed,
        "touched": touched,
        "trials_main": main,
        "trials_suggest": suggest,
        "trials_empty": empty,
    }


def main() -> None:
    parser = argparse.ArgumentParser(description="Re-run RI case trial enrichment")
    parser.add_argument("--path", type=Path, default=CASES_CSV)
    parser.add_argument("--tier", default=None, help="Catalog tier filter (default: all)")
    parser.add_argument("--case-id")
    parser.add_argument("--limit", type=int)
    args = parser.parse_args()

    stats = enrich_trials(
        path=args.path,
        tier=args.tier or None,
        case_id=args.case_id,
        limit=args.limit,
    )
    print(stats)


if __name__ == "__main__":
    main()
