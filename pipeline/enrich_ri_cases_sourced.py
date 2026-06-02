"""Populate ri_cases_enriched.csv with cited real data and primary-source URLs.

Every enriched main column should have a traceable URL in a structured source field:
  - compN_value_source_url + compN_supporting_citations
  - publication_urls / suggest_publication_urls
  - literature_source_urls
  - rd_milestone_source_urls + rd_plan_source_url
  - trial_urls, physician_lead_profile_url, primary_patent_url

Does not set review_status=approved.
"""

from __future__ import annotations

import argparse
from pathlib import Path

from pipeline.enrich_ri_cases_full_web import enrich_full_web, fill_row_web_gaps
from pipeline.enrich_ri_cases_comps import enrich_comps
from pipeline.ri_biomcp_publications import apply_publications
from pipeline.ri_cases_enriched_io import CASES_CSV, load_cases, write_cases
from pipeline.ri_cases_enriched_schema import COMP_PREFIXES
from pipeline.ri_source_utils import finish_row_sources
from pipeline.apply_tier_a_comps_to_enriched import apply_tier_a_comps
from pipeline.remediate_ri_cases_enriched import remediate


def _bool(value: str | None) -> bool:
    return (value or "").strip().lower() in {"1", "true", "t", "yes", "y"}


def enrich_sourced(
    *,
    path: Path = CASES_CSV,
    tier: str | None = None,
    case_id: str | None = None,
    skip_sync: bool = False,
    skip_remediate: bool = False,
    skip_biomcp: bool = False,
    skip_agent: bool = False,
    prefer_live_agent: bool = True,
    fetch_urls: bool = True,
    limit: int | None = None,
    web_only: bool = False,
) -> dict[str, int | list[str]]:
    """Full cited enrichment pass."""
    steps: list[str] = []

    if not skip_sync:
        _, n = apply_tier_a_comps(path=path, tier="A")
        steps.append(f"tier_a_sync:{n}")

    if not skip_remediate:
        remediate(path=path)
        steps.append("remediate")

    if not skip_biomcp:
        _, n = apply_publications(path=path, tier="A", overwrite=False)
        steps.append(f"biomcp_tier_a:{n}")

    _, n = enrich_comps(path=path, case_id=case_id, fetch_urls=False)
    steps.append(f"comp_seed:{n}")

    if web_only:
        import json

        from pipeline.enrich_ri_cases_full_web import EVIDENCE_PATH
        from pipeline.tier_a.comp_link_resolve import load_link_cache, write_link_cache

        evidence_by = {}
        if EVIDENCE_PATH.exists():
            evidence_by = json.loads(EVIDENCE_PATH.read_text(encoding="utf-8")).get("by_case_id") or {}
        rows = load_cases(path)
        cache = load_link_cache()
        touched = processed = 0
        for row in rows:
            if case_id and row.get("case_id") != case_id:
                continue
            if tier and (row.get("catalog_tier") or "").upper() != tier.upper():
                continue
            if not _bool(row.get("catalog_include", "true")):
                continue
            if (row.get("review_status") or "").lower() == "approved":
                continue
            if limit is not None and processed >= limit:
                break
            processed += 1
            cid = row.get("case_id", "")
            print(f"Sourced enrich: {cid} …", flush=True)
            changes = fill_row_web_gaps(row, evidence_by.get(cid), fetch_urls=fetch_urls, cache=cache)
            changes.extend(finish_row_sources(row, comp_prefixes=COMP_PREFIXES))
            if changes:
                touched += 1
        if cache:
            write_link_cache(cache)
        write_cases(rows, path)
        return {"steps": steps, "processed": processed, "touched": touched, "total_rows": len(rows)}

    summary = enrich_full_web(
        path=path,
        tier=tier,
        case_id=case_id,
        skip_sync=True,
        skip_remediate=True,
        skip_biomcp=True,
        skip_agent=skip_agent,
        prefer_live_agent=prefer_live_agent,
        fetch_urls=fetch_urls,
        limit=limit,
    )
    steps.extend(summary.get("steps", []))

    rows = load_cases(path)
    touched = 0
    for row in rows:
        if case_id and row.get("case_id") != case_id:
            continue
        if tier and (row.get("catalog_tier") or "").upper() != tier.upper():
            continue
        if not _bool(row.get("catalog_include", "true")):
            continue
        if (row.get("review_status") or "").lower() == "approved":
            continue
        if finish_row_sources(row, comp_prefixes=COMP_PREFIXES):
            touched += 1
    write_cases(rows, path)

    return {
        "steps": steps,
        "processed": summary.get("processed", 0),
        "touched": summary.get("touched", 0) + touched,
        "total_rows": summary.get("total_rows", len(rows)),
    }


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--path", type=Path, default=CASES_CSV)
    parser.add_argument("--tier")
    parser.add_argument("--case-id")
    parser.add_argument("--skip-sync", action="store_true")
    parser.add_argument("--skip-remediate", action="store_true")
    parser.add_argument("--skip-biomcp", action="store_true")
    parser.add_argument("--skip-agent", action="store_true")
    parser.add_argument("--no-live-agent", action="store_true")
    parser.add_argument("--no-fetch", action="store_true")
    parser.add_argument("--web-only", action="store_true", help="Skip LLM agent; web + source linking only")
    parser.add_argument("--limit", type=int)
    args = parser.parse_args()

    summary = enrich_sourced(
        path=args.path,
        tier=args.tier,
        case_id=args.case_id,
        skip_sync=args.skip_sync,
        skip_remediate=args.skip_remediate,
        skip_biomcp=args.skip_biomcp,
        skip_agent=args.skip_agent or args.web_only,
        prefer_live_agent=not args.no_live_agent,
        fetch_urls=not args.no_fetch,
        limit=args.limit,
        web_only=args.web_only,
    )
    print(
        f"Sourced enrichment complete: {summary['touched']}/{summary['processed']} rows touched "
        f"({summary['total_rows']} total). Steps: {', '.join(summary['steps'])}"
    )


if __name__ == "__main__":
    main()
