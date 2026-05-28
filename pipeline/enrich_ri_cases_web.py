"""Web-search enrichment for data/ri/ri_cases_enriched.csv.

Runs pragmatic DuckDuckGo queries for comparable financing URLs, physician profiles,
and R&D context. Records all queries and hits in web_search_* audit columns;
promotes comp1 financing hits to suggest_comp1_* when main URL is empty.

Does not set review_status=approved or overwrite approved main columns.
"""

from __future__ import annotations

import argparse
import re
import time
from datetime import date
from pathlib import Path

from pipeline.brown_vivo_profiles import fill_brown_profile_url, is_brown_institution
from pipeline.ri_cases_enriched_io import CASES_CSV, load_cases, write_cases
from pipeline.tier_a.comp_financing import comp_base_name, resolve_financing_queries
from pipeline.tier_a.comp_link_resolve import (
    _acceptable_result_url,
    _duckduckgo_html_results,
    _heuristic_links,
    fetch_resolved_links,
    load_link_cache,
    write_link_cache,
)

FETCH_DELAY_S = 0.8


def _bool(value: str | None) -> bool:
    return (value or "").strip().lower() in {"1", "true", "t", "yes", "y"}


def _append_note(notes: list[str], tag: str, label: str, url: str) -> None:
    line = f"[{tag}] {label} | {url}"
    if line not in notes:
        notes.append(line)


def _append_queries(queries: list[str], query: str) -> None:
    q = query.strip()
    if q and q not in queries:
        queries.append(q)


def _comp_dict(row: dict[str, str], prefix: str, rank: str) -> dict[str, str]:
    return {
        "precedent_rank": rank,
        "precedent_name": row.get(f"{prefix}name", ""),
        "precedent_type": row.get(f"{prefix}type", ""),
        "precedent_url": row.get(f"{prefix}url", ""),
        "value_source_url": row.get(f"{prefix}value_source_url", ""),
        "validation_status": row.get(f"{prefix}validation_status", ""),
    }


def _needs_comp_search(row: dict[str, str], prefix: str) -> bool:
    name = (row.get(f"{prefix}name") or "").strip()
    if not name:
        return False
    url = (row.get(f"{prefix}value_source_url") or "").strip()
    status = (row.get(f"{prefix}validation_status") or "").lower()
    if status == "verified" and url:
        return False
    return not url


def _profile_search_queries(row: dict[str, str]) -> list[str]:
    name = (row.get("physician_lead_name") or "").strip()
    if not name or (row.get("physician_lead_profile_url") or "").strip():
        return []
    institution = (
        row.get("physician_lead_institution")
        or row.get("ri_institution")
        or row.get("company")
        or ""
    )
    if is_brown_institution(institution):
        return []

    parts = name.title().split()
    if len(parts) < 2:
        return []
    short = f"{parts[0]} {parts[-1]}"
    return [
        f'"{short}" site:lifespan.org OR site:rhodeislandhospital.org',
        f'"{short}" site:web.uri.edu OR site:ele.uri.edu',
        f'"{short}" Brown Warren Alpert OR "Rhode Island Hospital" physician',
    ]


def _rd_search_queries(row: dict[str, str]) -> list[str]:
    if (row.get("rd_plan_summary") or "").strip():
        return []
    title = (row.get("title_clean") or row.get("display_name") or "").strip()
    indication = (row.get("indication") or "").strip()
    company = (row.get("company") or "").strip()
    if not title:
        return []
    base = f"{company} {title}" if company and company.upper() != "TBD" else title
    queries = [
        f"{base} preclinical development milestone",
        f"{indication} translational research Rhode Island" if indication else "",
    ]
    return [q for q in queries if len(q) > 10]


def _search_top_hit(query: str) -> tuple[str, str] | None:
    time.sleep(FETCH_DELAY_S)
    for title, url in _duckduckgo_html_results(query, limit=3):
        if _acceptable_result_url(url, title=title):
            return title, url
    return None


def _profile_hit(query: str) -> tuple[str, str] | None:
    time.sleep(FETCH_DELAY_S)
    for title, url in _duckduckgo_html_results(query, limit=4):
        lower = url.lower()
        if any(
            host in lower
            for host in (
                "lifespan.org",
                "rhodeislandhospital",
                "web.uri.edu",
                "ele.uri.edu",
                "vivo.brown.edu",
                "brown.edu",
                "carenewengland",
            )
        ):
            return title, url
    return None


def _draft_rd_summary(row: dict[str, str]) -> str:
    """Pragmatic R&D draft from row metadata (no web required)."""
    title = row.get("title_clean") or row.get("display_name") or row.get("case_id", "")
    stage = row.get("development_stage") or "validation"
    comp = (row.get("comp1_name") or "").strip()
    comp_path = (row.get("comp1_development_path") or "").strip()
    parts = [
        f"Near-term R&D for {title} ({stage} stage).",
    ]
    if comp_path:
        parts.append(f"Development path analog: {comp} — {comp_path[:120]}.")
    elif comp:
        parts.append(f"Benchmark against {comp} staging.")
    parts.append(
        "RI co-investment package targets de-risking experiments and clinical-ready "
        "milestones aligned with physician syndicate diligence."
    )
    return " ".join(parts)


def enrich_row(
    row: dict[str, str],
    *,
    fetch_comps: bool = True,
    comps_heuristic_only: bool = False,
    fetch_profiles: bool = True,
    fetch_rd: bool = True,
    draft_rd: bool = True,
    cache: dict | None = None,
) -> list[str]:
    """Enrich one row; return list of change tags."""
    if not _bool(row.get("catalog_include", "true")):
        return []
    if (row.get("review_status") or "").lower() == "approved":
        return []

    changes: list[str] = []
    queries: list[str] = []
    notes: list[str] = []
    prior_notes = (row.get("web_search_notes") or "").strip()
    prior_queries = (row.get("web_search_queries") or "").strip()

    if row.get("web_search_queries"):
        queries.extend(q.strip() for q in row["web_search_queries"].split("|") if q.strip())
    if row.get("web_search_notes"):
        notes.extend(n.strip() for n in row["web_search_notes"].split("\n") if n.strip())

    # Brown VIVO (fast, no DDG)
    if fill_brown_profile_url(row):
        changes.append("vivo_profile")

    # Comparables
    if fetch_comps:
        for rank, prefix in [("1", "comp1_"), ("2", "comp2_"), ("3", "comp3_")]:
            if not _needs_comp_search(row, prefix):
                continue
            comp = _comp_dict(row, prefix, rank)
            for q in resolve_financing_queries(comp):
                _append_queries(queries, q)

            for label, url in _heuristic_links(comp):
                _append_note(notes, f"comp{rank}_heuristic", label, url)

            resolved = [] if comps_heuristic_only else fetch_resolved_links(comp)
            if resolved:
                label, url = resolved[0]
                _append_note(notes, f"comp{rank}", label, url)
                if rank == "1" and not (row.get("suggest_comp1_value_source_url") or "").strip():
                    row["suggest_comp1_value_source_url"] = url
                    row["suggest_comp1_notes"] = label
                    changes.append("suggest_comp1")
                if cache is not None:
                    cache[(row["case_id"], rank)] = resolved
            else:
                qlist = resolve_financing_queries(comp)
                if qlist and not comps_heuristic_only:
                    hit = _search_top_hit(qlist[0])
                    if hit:
                        label, url = hit
                        _append_note(notes, f"comp{rank}", label, url)
                        if rank == "1" and not (row.get("suggest_comp1_value_source_url") or "").strip():
                            row["suggest_comp1_value_source_url"] = url
                            row["suggest_comp1_notes"] = label
                            changes.append("suggest_comp1")
                    else:
                        _append_note(
                            notes,
                            f"comp{rank}",
                            "no DuckDuckGo primary hit",
                            "see web_search_queries",
                        )

    # Physician profile (non-Brown)
    if fetch_profiles and not (row.get("physician_lead_profile_url") or "").strip():
        profile_qs = _profile_search_queries(row)
        if profile_qs:
            for q in profile_qs:
                _append_queries(queries, q)
            hit = None
            for q in profile_qs:
                hit = _profile_hit(q)
                if hit:
                    break
            if hit:
                label, url = hit
                row["physician_lead_profile_url"] = url
                _append_note(notes, "profile", label, url)
                changes.append("physician_profile")
            else:
                _append_note(notes, "profile", "no profile URL found", "see web_search_queries")

    # R&D web context + draft summary
    if fetch_rd:
        rd_qs = _rd_search_queries(row)
        rd_hit = False
        for q in rd_qs:
            _append_queries(queries, q)
            hit = _search_top_hit(q)
            if hit:
                _append_note(notes, "rd", hit[0], hit[1])
                rd_hit = True
        if rd_qs and not rd_hit:
            _append_note(notes, "rd", "no web context hit", "see web_search_queries")

    if draft_rd and not (row.get("rd_plan_summary") or "").strip():
        row["rd_plan_summary"] = _draft_rd_summary(row)
        changes.append("rd_plan_draft")

    if queries:
        row["web_search_queries"] = " | ".join(queries)
    if notes:
        row["web_search_notes"] = "\n".join(notes)

    if row.get("web_search_queries", "") != prior_queries:
        changes.append("web_search_queries")
    if row.get("web_search_notes", "") != prior_notes:
        changes.append("web_search_notes")

    if changes:
        row["last_refreshed_at"] = date.today().isoformat()
        row["enrichment_status"] = "web_enriched"
    return changes


def enrich_web(
    *,
    path: Path = CASES_CSV,
    tier: str | None = None,
    fetch_comps: bool = True,
    comps_heuristic_only: bool = False,
    fetch_profiles: bool = True,
    fetch_rd: bool = True,
    draft_rd: bool = True,
    limit: int | None = None,
) -> tuple[int, int]:
    rows = load_cases(path)
    cache = load_link_cache()
    touched = 0
    processed = 0

    for row in rows:
        if tier and (row.get("catalog_tier") or "").upper() != tier.upper():
            continue
        if not _bool(row.get("catalog_include", "true")):
            continue
        if limit is not None and processed >= limit:
            break
        processed += 1
        cid = row.get("case_id", "")
        print(f"Web enrich: {cid} …", flush=True)
        if enrich_row(
            row,
            fetch_comps=fetch_comps,
            comps_heuristic_only=comps_heuristic_only,
            fetch_profiles=fetch_profiles,
            fetch_rd=fetch_rd,
            draft_rd=draft_rd,
            cache=cache,
        ):
            touched += 1

    if cache:
        write_link_cache(cache)
    write_cases(rows, path)
    return len(rows), touched


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--path", type=Path, default=CASES_CSV)
    parser.add_argument("--tier", help="Limit to catalog_tier (e.g. A)")
    parser.add_argument("--no-comps", action="store_true", help="Skip DuckDuckGo comp fetch")
    parser.add_argument("--comps-heuristic-only", action="store_true", help="Record SEC/company heuristic links only")
    parser.add_argument("--no-profiles", action="store_true")
    parser.add_argument("--no-rd", action="store_true")
    parser.add_argument("--no-rd-draft", action="store_true")
    parser.add_argument("--limit", type=int, help="Max catalog rows to process")
    args = parser.parse_args()
    total, touched = enrich_web(
        path=args.path,
        tier=args.tier,
        fetch_comps=not args.no_comps,
        comps_heuristic_only=args.comps_heuristic_only,
        fetch_profiles=not args.no_profiles,
        fetch_rd=not args.no_rd,
        draft_rd=not args.no_rd_draft,
        limit=args.limit,
    )
    print(f"Web-enriched {touched} rows -> {args.path} ({total} total)")


if __name__ == "__main__":
    main()
