"""Single-case enrichment orchestrator for ri_cases_enriched.csv.

Runs existing enrichment modules in a fixed order per case (or tier batch).
Ground-truth CSV feeds first; web search and optional LLM agent fill assist
columns only. Does not set review_status=approved.

Modes:
  tier_a_full   — Tier-A package: comps sync → remediate → BioMCP → physicians
                  → trials → cited web (+ optional agent) → source linking
  tier_b_light  — Assist-only: remediate → BioMCP → comp seed → web (no agent)
  web_only      — Cited URL gap pass without LLM agent
  package       — Tier-A comp sync + physician NPI match (no web/agent)
  refresh_copy  — Approved rows only: source URLs + VIVO profile gaps (no comps/thesis overwrite)

Examples:
  python -m pipeline.enrich_ri_case --case-id prothera_iaip_ri --mode tier_a_full
  python -m pipeline.enrich_ri_case --case-id prothera_iaip_ri --mode refresh_copy --build
  python -m pipeline.enrich_ri_case --tier A --mode tier_a_full --web-only --limit 3
"""

from __future__ import annotations

import argparse
import subprocess
import sys
from dataclasses import dataclass
from datetime import date
from pathlib import Path
from typing import Any

from pipeline.apply_tier_a_comps_to_enriched import apply_tier_a_comps
from pipeline.brown_vivo_profiles import fill_brown_profile_url
from pipeline.enrich_ri_cases_comps import enrich_comps
from pipeline.enrich_ri_cases_trials import TRIAL_LOCKED_CASES
from pipeline.enrich_ri_cases_full_web import fill_trials_from_web
from pipeline.enrich_ri_cases_physicians import enrich_physicians
from pipeline.enrich_ri_cases_sourced import enrich_sourced
from pipeline.ri_biomcp_publications import apply_publications
from pipeline.ri_cases_enriched_io import CASES_CSV, load_cases, write_cases
from pipeline.ri_cases_enriched_schema import COMP_PREFIXES
from pipeline.ri_source_utils import finish_row_sources
from pipeline.remediate_ri_cases_enriched import remediate
from pipeline.tier_a.comp_link_resolve import load_link_cache, write_link_cache

MODES = ("tier_a_full", "tier_b_light", "web_only", "package", "refresh_copy")


@dataclass(frozen=True)
class EnrichRecipe:
    tier_a_sync: bool = False
    remediate: bool = False
    biomcp: bool = False
    comp_seed: bool = False
    physicians: bool = False
    trials: bool = False
    web: bool = False
    agent: bool = False
    web_only: bool = False
    approved_only: bool = False


RECIPES: dict[str, EnrichRecipe] = {
    "tier_a_full": EnrichRecipe(
        tier_a_sync=True,
        remediate=True,
        biomcp=True,
        comp_seed=True,
        physicians=True,
        trials=True,
        web=True,
        agent=True,
    ),
    "tier_b_light": EnrichRecipe(
        remediate=True,
        biomcp=True,
        comp_seed=True,
        web=True,
        web_only=True,
    ),
    "web_only": EnrichRecipe(
        tier_a_sync=True,
        remediate=True,
        biomcp=True,
        comp_seed=True,
        web=True,
        web_only=True,
    ),
    "package": EnrichRecipe(
        tier_a_sync=True,
        physicians=True,
    ),
    "refresh_copy": EnrichRecipe(approved_only=True),
}


def _bool(value: str | None) -> bool:
    return (value or "").strip().lower() in {"1", "true", "t", "yes", "y"}


def _row_matches(
    row: dict[str, str],
    *,
    case_id: str | None,
    tier: str | None,
    approved_only: bool,
) -> bool:
    if case_id and row.get("case_id") != case_id:
        return False
    if tier and (row.get("catalog_tier") or "").upper() != tier.upper():
        return False
    if not _bool(row.get("catalog_include", "true")):
        return False
    is_approved = (row.get("review_status") or "").lower() == "approved"
    if approved_only and not is_approved:
        return False
    if not approved_only and is_approved:
        return False
    return True


def _resolve_mode(mode: str | None, *, tier: str | None) -> str:
    if mode:
        if mode not in RECIPES:
            raise ValueError(f"Unknown mode {mode!r}; choose from {', '.join(MODES)}")
        return mode
    if tier and tier.upper() == "B":
        return "tier_b_light"
    return "tier_a_full"


def refresh_approved_copy(
    *,
    path: Path = CASES_CSV,
    case_id: str | None = None,
    tier: str | None = None,
    fetch_urls: bool = True,
    limit: int | None = None,
) -> dict[str, Any]:
    """Refresh source-link columns on approved rows without overwriting curated copy."""
    from pipeline.enrich_ri_cases_full_web import (
        _append_note,
        _apply_comp_url,
        _ensure_comp_role,
        _ensure_supporting_citations,
        _merge_audit,
        _write_audit,
        fetch_resolved_links,
    )

    rows = load_cases(path)
    cache = load_link_cache() if fetch_urls else {}
    touched = processed = 0

    for row in rows:
        if not _row_matches(row, case_id=case_id, tier=tier, approved_only=True):
            continue
        if limit is not None and processed >= limit:
            break
        processed += 1
        cid = row.get("case_id", "")
        print(f"Refresh copy: {cid} …", flush=True)

        changes: list[str] = []
        queries, notes = _merge_audit(row)

        if fill_brown_profile_url(row):
            changes.append("vivo_profile")

        for rank, prefix in zip(
            (str(i) for i in range(1, len(COMP_PREFIXES) + 1)), COMP_PREFIXES, strict=True
        ):
            name = (row.get(f"{prefix}name") or "").strip()
            if not name:
                continue
            if _ensure_comp_role(row, prefix):
                changes.append(f"{prefix}role")
            if _ensure_supporting_citations(row, prefix):
                changes.append(f"{prefix}citations")
            if fetch_urls and not (row.get(f"{prefix}value_source_url") or "").strip():
                comp = {
                    "precedent_rank": rank,
                    "precedent_name": name,
                    "precedent_type": row.get(f"{prefix}type", ""),
                    "precedent_url": row.get(f"{prefix}url", ""),
                    "value_source_url": "",
                    "validation_status": row.get(f"{prefix}validation_status", ""),
                }
                resolved = fetch_resolved_links(comp)
                if resolved:
                    label, url = resolved[0]
                    if _apply_comp_url(row, prefix, label, url):
                        changes.append(f"{prefix}url")
                        _append_note(notes, f"comp{rank}", label, url)
                    if cache is not None:
                        cache[(cid, rank)] = resolved

        changes.extend(finish_row_sources(row, comp_prefixes=COMP_PREFIXES))
        _write_audit(row, queries, notes)

        if changes:
            row["last_refreshed_at"] = date.today().isoformat()
            row["enrichment_status"] = "copy_sources_refreshed"
            touched += 1
            print(f"  -> {', '.join(sorted(set(changes)))}", flush=True)

    if cache:
        write_link_cache(cache)
    write_cases(rows, path)
    return {"mode": "refresh_copy", "processed": processed, "touched": touched, "steps": ["refresh_copy"]}


def _enrich_trials_scoped(
    *,
    path: Path,
    case_id: str | None,
    tier: str | None,
    limit: int | None,
) -> dict[str, int]:
    rows = load_cases(path)
    touched = processed = 0
    for row in rows:
        if not _row_matches(row, case_id=case_id, tier=tier, approved_only=False):
            continue
        if limit is not None and processed >= limit:
            break
        processed += 1
        if row.get("case_id", "") in TRIAL_LOCKED_CASES:
            continue
        if fill_trials_from_web(row, force=True):
            touched += 1
    write_cases(rows, path)
    return {"processed": processed, "touched": touched}


def _apply_vivo_scoped(
    *,
    path: Path,
    case_id: str | None,
    tier: str | None,
    approved_only: bool,
) -> int:
    rows = load_cases(path)
    updated = 0
    for row in rows:
        if not _row_matches(row, case_id=case_id, tier=tier, approved_only=approved_only):
            continue
        if fill_brown_profile_url(row):
            updated += 1
    if updated:
        write_cases(rows, path)
    return updated


def enrich_case(
    *,
    path: Path = CASES_CSV,
    case_id: str | None = None,
    tier: str | None = None,
    mode: str | None = None,
    fetch_urls: bool = True,
    prefer_live_agent: bool = True,
    limit: int | None = None,
    skip_build: bool = True,
    skip_validate: bool = True,
) -> dict[str, Any]:
    """Run the enrichment recipe for one case (or filtered batch)."""
    resolved_mode = _resolve_mode(mode, tier=tier)
    recipe = RECIPES[resolved_mode]
    steps: list[str] = []
    summary: dict[str, Any] = {"mode": resolved_mode, "steps": steps}

    if recipe.approved_only:
        result = refresh_approved_copy(
            path=path,
            case_id=case_id,
            tier=tier,
            fetch_urls=fetch_urls,
            limit=limit,
        )
        summary.update(result)
        if not skip_validate:
            summary["validate_ok"] = _run_validate(path)
        if not skip_build:
            _run_build()
            summary["built"] = True
        return summary

    if recipe.tier_a_sync:
        _, n = apply_tier_a_comps(path=path, tier="A")
        steps.append(f"tier_a_sync:{n}")

    if recipe.remediate:
        remediate(path=path)
        steps.append("remediate")

    if recipe.biomcp:
        _, n = apply_publications(path=path, tier="A", overwrite=False)
        steps.append(f"biomcp_apply:{n}")

    if recipe.comp_seed:
        _, n = enrich_comps(path=path, case_id=case_id, fetch_urls=False)
        steps.append(f"comp_seed:{n}")

    if recipe.physicians:
        stats = enrich_physicians(path=path, tier=tier, case_id=case_id)
        steps.append(f"physicians:{stats.get('touched', 0)}")

    if recipe.trials:
        stats = _enrich_trials_scoped(path=path, case_id=case_id, tier=tier, limit=limit)
        steps.append(f"trials:{stats.get('touched', 0)}")

    if recipe.web:
        web_summary = enrich_sourced(
            path=path,
            tier=tier,
            case_id=case_id,
            skip_sync=True,
            skip_remediate=True,
            skip_biomcp=True,
            skip_agent=not recipe.agent,
            prefer_live_agent=prefer_live_agent,
            fetch_urls=fetch_urls,
            limit=limit,
            web_only=recipe.web_only or not recipe.agent,
        )
        steps.extend(web_summary.get("steps", []))
        summary["processed"] = web_summary.get("processed", 0)
        summary["touched"] = web_summary.get("touched", 0)
    else:
        n = _apply_vivo_scoped(path=path, case_id=case_id, tier=tier, approved_only=False)
        if n:
            steps.append(f"vivo:{n}")

    if not skip_validate:
        summary["validate_ok"] = _run_validate(path)
    if not skip_build:
        _run_build()
        summary["built"] = True

    summary["steps"] = steps
    return summary


def _run_validate(path: Path) -> bool:
    from pipeline.validate_ri_cases_enriched import validate

    report = validate(path)
    for err in report.errors:
        print(f"VALIDATE ERROR: {err}", flush=True)
    for warn in report.warnings:
        print(f"VALIDATE WARN: {warn}", flush=True)
    return report.ok


def _run_build() -> None:
    subprocess.run([sys.executable, "-m", "pipeline.export_ri_cases_enriched_json"], check=True)
    subprocess.run(
        [sys.executable, "-m", "pipeline.build_ri_combined", "--from", "cases-enriched"],
        check=True,
    )


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--path", type=Path, default=CASES_CSV)
    parser.add_argument("--case-id", help="Single case_id (recommended)")
    parser.add_argument("--tier", help="Filter by catalog_tier (A or B)")
    parser.add_argument(
        "--mode",
        choices=MODES,
        help="Enrichment recipe (default: tier_a_full, or tier_b_light when --tier B)",
    )
    parser.add_argument("--web-only", action="store_true", help="Force web_only mode (no LLM agent)")
    parser.add_argument("--no-fetch", action="store_true", help="Skip DuckDuckGo URL fetches")
    parser.add_argument("--no-live-agent", action="store_true", help="Use fixture agent when agent enabled")
    parser.add_argument("--limit", type=int, help="Max rows to process in web/trial steps")
    parser.add_argument("--validate", action="store_true", help="Run validate_ri_cases_enriched after enrich")
    parser.add_argument("--build", action="store_true", help="Export JSON + build opportunities_combined.json")
    args = parser.parse_args()

    mode = "web_only" if args.web_only else args.mode
    summary = enrich_case(
        path=args.path,
        case_id=args.case_id,
        tier=args.tier,
        mode=mode,
        fetch_urls=not args.no_fetch,
        prefer_live_agent=not args.no_live_agent,
        limit=args.limit,
        skip_build=not args.build,
        skip_validate=not args.validate,
    )
    steps = ", ".join(summary.get("steps", []))
    processed = summary.get("processed", "?")
    touched = summary.get("touched", "?")
    print(
        f"Case enrich complete [{summary.get('mode')}]: "
        f"{touched}/{processed} rows touched. Steps: {steps}",
        flush=True,
    )
    if summary.get("validate_ok") is False:
        sys.exit(1)


if __name__ == "__main__":
    main()
