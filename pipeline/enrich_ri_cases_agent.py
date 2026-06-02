"""Agentic LLM + web-search enrichment for data/ri/ri_cases_enriched.csv.

Uses LLMProvider to propose science-aligned comps, R&D drafts, and search queries;
verifies financing URLs via DuckDuckGo + primary-source host allowlist.

Writes only assist columns (suggest_*, web_search_*) and empty main drafts.
Never sets review_status=approved or overwrites approved rows.
"""

from __future__ import annotations

import argparse
import json
import time
from datetime import date
from pathlib import Path
from typing import Any

from pipeline.enrich_ri_cases_web import (
    _append_note,
    _append_queries,
    _bool,
    _profile_hit,
    _search_top_hit,
)
from pipeline.llm_provider import get_provider, get_provider_status, select_provider
from pipeline.ri_cases_enriched_io import CASES_CSV, load_cases, write_cases
from pipeline.ri_cases_enriched_schema import COMP_PREFIXES
from pipeline.tier_a.comp_link_resolve import (
    _acceptable_result_url,
    _duckduckgo_html_results,
    load_link_cache,
    write_link_cache,
)
from pipeline.types import repo_root

PROMPT_PATH = Path(__file__).resolve().parent / "prompts" / "ri_cases_agent_enrich.md"
AGENT_FIXTURES = repo_root() / "tests" / "fixtures" / "ri" / "agent_enrich"

FETCH_DELAY_S = 0.8

AGENT_JSON_SCHEMA: dict[str, Any] = {
    "type": "object",
    "properties": {
        "comps": {
            "type": "array",
            "items": {
                "type": "object",
                "properties": {
                    "slot": {"type": "integer"},
                    "name": {"type": "string"},
                    "type": {"type": "string"},
                    "role": {"type": "string"},
                    "notes": {"type": "string"},
                    "development_path": {"type": "string"},
                    "financing_search_queries": {
                        "type": "array",
                        "items": {"type": "string"},
                    },
                    "supporting_citation_queries": {
                        "type": "array",
                        "items": {"type": "string"},
                    },
                },
            },
        },
        "comp_gaps": {"type": "string"},
        "rd_milestones_draft": {"type": "string"},
        "rd_plan_summary_draft": {"type": "string"},
        "literature_narrative_draft": {"type": "string"},
        "physician_profile_queries": {
            "type": "array",
            "items": {"type": "string"},
        },
    },
}


def _load_prompt_template() -> str:
    if PROMPT_PATH.is_file():
        return PROMPT_PATH.read_text(encoding="utf-8")
    return "Propose RI case enrichment as JSON."


def _existing_comps(row: dict[str, str]) -> list[dict[str, str]]:
    comps: list[dict[str, str]] = []
    for i, prefix in enumerate(COMP_PREFIXES, start=1):
        name = (row.get(f"{prefix}name") or "").strip()
        if not name:
            continue
        comps.append(
            {
                "slot": str(i),
                "name": name,
                "type": row.get(f"{prefix}type", ""),
                "role": row.get(f"{prefix}role", ""),
                "value_source_url": row.get(f"{prefix}value_source_url", ""),
                "validation_status": row.get(f"{prefix}validation_status", ""),
                "notes": (row.get(f"{prefix}notes") or "")[:160],
            }
        )
    return comps


def _row_context(row: dict[str, str]) -> dict[str, Any]:
    return {
        "case_id": row.get("case_id", ""),
        "catalog_tier": row.get("catalog_tier", ""),
        "title_clean": row.get("title_clean") or row.get("display_name", ""),
        "company": row.get("company", ""),
        "indication": row.get("indication", ""),
        "opportunity_type": row.get("opportunity_type", ""),
        "development_stage": row.get("development_stage", ""),
        "ri_institution": row.get("ri_institution", ""),
        "primary_patent_title": row.get("primary_patent_title", ""),
        "assignee_company": row.get("assignee_company", ""),
        "inventors": row.get("inventors", ""),
        "existing_comps": _existing_comps(row),
        "physician_lead_name": row.get("physician_lead_name", ""),
        "physician_lead_institution": row.get("physician_lead_institution", ""),
        "publication_count": row.get("publication_count", ""),
        "rd_plan_summary": (row.get("rd_plan_summary") or "")[:200],
        "investment_thesis": (row.get("investment_thesis") or "")[:300],
    }


def _fixture_path(case_id: str) -> Path | None:
    for name in (f"{case_id}.json", "default.json"):
        path = AGENT_FIXTURES / name
        if path.is_file():
            return path
    return None


def _load_fixture(case_id: str) -> dict[str, Any] | None:
    path = _fixture_path(case_id)
    if not path:
        return None
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except json.JSONDecodeError:
        return None
    return data if isinstance(data, dict) else None


def _deterministic_fallback(row: dict[str, str]) -> dict[str, Any]:
    """MOCK/SYNTHETIC — row-derived proposals when no API key or fixture."""
    title = row.get("title_clean") or row.get("display_name") or row.get("case_id", "")
    indication = row.get("indication") or "the target indication"
    comps = _existing_comps(row)
    out_comps: list[dict[str, Any]] = []
    for comp in comps[:3]:
        slot = int(comp["slot"])
        name = comp["name"]
        if comp.get("value_source_url"):
            continue
        out_comps.append(
            {
                "slot": slot,
                "name": name,
                "type": comp.get("type") or "startup",
                "role": comp.get("role") or "development_path",
                "notes": f"MOCK/SYNTHETIC — verify financing for {name}",
                "development_path": "",
                "financing_search_queries": [
                    f'"{name.split("(")[0].strip()}" funding round site:prnewswire.com',
                    f"{name.split('(')[0].strip()} venture capital raised",
                ],
                "supporting_citation_queries": [],
            }
        )
    return {
        "comps": out_comps,
        "comp_gaps": "MOCK/SYNTHETIC — review incumbent vs venture comp ordering",
        "rd_milestones_draft": (
            f"MOCK/SYNTHETIC — preclinical validation and IND-enabling for {title} "
            f"in {indication}"
        ),
        "rd_plan_summary_draft": "",
        "literature_narrative_draft": "",
        "physician_profile_queries": [],
    }


def call_agent(
    row: dict[str, str],
    *,
    prefer_live: bool = False,
) -> tuple[dict[str, Any], list[str]]:
    """Return (payload, warnings)."""
    case_id = row.get("case_id", "")
    warnings: list[str] = []

    if not prefer_live:
        fixture = _load_fixture(case_id)
        if fixture:
            warnings.append(f"MOCK/SYNTHETIC — fixture {case_id}")
            return fixture, warnings
        fallback = _deterministic_fallback(row)
        warnings.append("MOCK/SYNTHETIC — deterministic fallback (no OPENAI_API_KEY)")
        return fallback, warnings

    selection = select_provider(prefer_live=True)
    if not selection.using_live_api:
        fixture = _load_fixture(case_id)
        if fixture:
            warnings.append("MOCK/SYNTHETIC — live requested but no API key; using fixture")
            return fixture, warnings
        fallback = _deterministic_fallback(row)
        warnings.append("MOCK/SYNTHETIC — live requested but no API key; using fallback")
        return fallback, warnings

    provider = selection.provider
    context = _row_context(row)
    prompt = (
        f"{_load_prompt_template()}\n\n"
        "## Case row (JSON)\n\n"
        f"{json.dumps(context, indent=2)}\n"
    )
    response = provider.generate_json(
        prompt=prompt,
        schema=AGENT_JSON_SCHEMA,
        temperature=0.2,
        max_output_tokens=2500,
        metadata={"case_id": case_id, "step": "agent_enrich"},
    )
    if response.errors:
        warnings.extend(response.errors)
        fixture = _load_fixture(case_id)
        if fixture:
            warnings.append("MOCK/SYNTHETIC — API error; using fixture")
            return fixture, warnings
        return _deterministic_fallback(row), warnings
    if response.warnings:
        warnings.extend(response.warnings)
    payload = response.output_json
    if not isinstance(payload, dict):
        return _deterministic_fallback(row), warnings + ["Invalid agent payload type"]
    return payload, warnings


def _verify_query(query: str) -> tuple[str, str] | None:
    time.sleep(FETCH_DELAY_S)
    for title, url in _duckduckgo_html_results(query, limit=3):
        if _acceptable_result_url(url, title=title):
            return title, url
    hit = _search_top_hit(query)
    return hit


def _verify_citation_query(query: str) -> tuple[str, str] | None:
    time.sleep(FETCH_DELAY_S)
    for title, url in _duckduckgo_html_results(query, limit=4):
        lower = url.lower()
        if _acceptable_result_url(url, title=title):
            return title, url
        if any(
            host in lower
            for host in (
                "fda.gov",
                "pubmed.ncbi.nlm.nih.gov",
                "nature.com",
                "sciencedirect.com",
                "nejm.org",
                "brown.edu",
                "lifespan.org",
            )
        ):
            return title, url
    return None


def verify_agent_urls(
    payload: dict[str, Any],
    *,
    fetch: bool = True,
) -> dict[str, list[tuple[str, str]]]:
    """Map comp slot -> list of (label, url) verified hits."""
    if not fetch:
        return {}
    verified: dict[str, list[tuple[str, str]]] = {}
    for comp in payload.get("comps") or []:
        if not isinstance(comp, dict):
            continue
        slot = str(comp.get("slot") or "")
        if not slot:
            continue
        hits: list[tuple[str, str]] = []
        seen: set[str] = set()
        for query in comp.get("financing_search_queries") or []:
            q = str(query).strip()
            if not q:
                continue
            hit = _verify_query(q)
            if hit and hit[1] not in seen:
                seen.add(hit[1])
                hits.append(hit)
            if len(hits) >= 2:
                break
        for query in comp.get("supporting_citation_queries") or []:
            q = str(query).strip()
            if not q:
                continue
            hit = _verify_citation_query(q)
            if hit and hit[1] not in seen:
                seen.add(hit[1])
                hits.append((f"cite: {hit[0]}", hit[1]))
            if len(hits) >= 4:
                break
        if hits:
            verified[slot] = hits
    return verified


def _merge_notes(row: dict[str, str]) -> tuple[list[str], list[str]]:
    queries: list[str] = []
    notes: list[str] = []
    if row.get("web_search_queries"):
        queries.extend(q.strip() for q in row["web_search_queries"].split("|") if q.strip())
    if row.get("web_search_notes"):
        notes.extend(n.strip() for n in row["web_search_notes"].split("\n") if n.strip())
    return queries, notes


def _apply_verified_comp_url(row: dict[str, str], prefix: str, label: str, url: str) -> bool:
    if not url or (row.get(f"{prefix}value_source_url") or "").strip():
        return False
    status = (row.get(f"{prefix}validation_status") or "").lower()
    if status == "verified":
        return False
    row[f"{prefix}value_source_url"] = url
    if not (row.get(f"{prefix}validation_status") or "").strip():
        row[f"{prefix}validation_status"] = "suggested"
    return True


def apply_agent_payload(
    row: dict[str, str],
    payload: dict[str, Any],
    verified: dict[str, list[tuple[str, str]]],
    *,
    agent_warnings: list[str] | None = None,
) -> list[str]:
    """Apply agent output to row; return change tags."""
    if not _bool(row.get("catalog_include", "true")):
        return []
    if (row.get("review_status") or "").lower() == "approved":
        return []

    changes: list[str] = []
    queries, notes = _merge_notes(row)
    prior_queries = row.get("web_search_queries", "")
    prior_notes = row.get("web_search_notes", "")

    case_id = row.get("case_id", "")
    _append_note(notes, "agent", f"enriched {case_id}", date.today().isoformat())
    for warning in agent_warnings or []:
        if warning:
            _append_note(notes, "agent_warn", warning[:120], "audit")

    gaps = (payload.get("comp_gaps") or "").strip()
    if gaps:
        _append_note(notes, "agent_gaps", gaps[:200], "review")

    for comp in payload.get("comps") or []:
        if not isinstance(comp, dict):
            continue
        slot = str(comp.get("slot") or "")
        name = (comp.get("name") or "").strip()
        if not slot or not name:
            continue
        role = (comp.get("role") or "").strip()
        ctype = (comp.get("type") or "").strip()
        comp_notes = (comp.get("notes") or "").strip()
        dev_path = (comp.get("development_path") or "").strip()
        summary = " | ".join(p for p in (name, role, ctype, comp_notes[:80]) if p)
        _append_note(notes, f"agent_comp{slot}", summary, "proposal")

        for query in comp.get("financing_search_queries") or []:
            _append_queries(queries, f"[agent comp{slot}] {query}")
        for query in comp.get("supporting_citation_queries") or []:
            _append_queries(queries, f"[agent cite comp{slot}] {query}")

        prefix = f"comp{slot}_"
        existing_name = (row.get(f"{prefix}name") or "").strip()
        existing_url = (row.get(f"{prefix}value_source_url") or "").strip()

        hits = verified.get(slot) or []
        for label, url in hits:
            _append_note(notes, f"agent_comp{slot}_url", label, url)

        if hits and not existing_url:
            if _apply_verified_comp_url(row, prefix, hits[0][0], hits[0][1]):
                changes.append(f"comp{slot}_url")
            elif slot == "1" and not (row.get("suggest_comp1_value_source_url") or "").strip():
                row["suggest_comp1_value_source_url"] = hits[0][1]
                row["suggest_comp1_notes"] = hits[0][0]
                changes.append("suggest_comp1")

        if not existing_name and name:
            row[f"{prefix}name"] = name
            if ctype:
                row[f"{prefix}type"] = ctype
            if role:
                row[f"{prefix}role"] = role
            if comp_notes:
                row[f"{prefix}notes"] = comp_notes
            if dev_path:
                row[f"{prefix}development_path"] = dev_path
            row[f"{prefix}validation_status"] = "suggested"
            changes.append(f"comp{slot}_suggested")

        elif existing_name.lower() == name.lower() and not existing_url and hits:
            if _apply_verified_comp_url(row, prefix, hits[0][0], hits[0][1]):
                changes.append(f"comp{slot}_url")
            elif slot == "1" and not (row.get("suggest_comp1_value_source_url") or "").strip():
                row["suggest_comp1_value_source_url"] = hits[0][1]
                row["suggest_comp1_notes"] = hits[0][0]
                changes.append("suggest_comp1")

    rd_milestones = (payload.get("rd_milestones_draft") or "").strip()
    if rd_milestones:
        _append_note(notes, "agent_rd_milestones", rd_milestones[:240], "draft")
        if not (row.get("rd_milestones") or "").strip():
            row["rd_milestones"] = rd_milestones
            changes.append("rd_milestones_draft")

    rd_plan = (payload.get("rd_plan_summary_draft") or "").strip()
    if rd_plan:
        _append_note(notes, "agent_rd_plan", rd_plan[:240], "draft")
        if not (row.get("rd_plan_summary") or "").strip():
            row["rd_plan_summary"] = rd_plan
            changes.append("rd_plan_draft")

    lit = (payload.get("literature_narrative_draft") or "").strip()
    if lit:
        _append_note(notes, "agent_literature", lit[:240], "draft")
        if not (row.get("literature_narrative") or "").strip():
            row["literature_narrative"] = lit
            changes.append("literature_draft")

    if not (row.get("physician_lead_profile_url") or "").strip():
        for query in payload.get("physician_profile_queries") or []:
            q = str(query).strip()
            if not q:
                continue
            _append_queries(queries, f"[agent profile] {q}")
            hit = _profile_hit(q)
            if hit:
                row["physician_lead_profile_url"] = hit[1]
                _append_note(notes, "agent_profile", hit[0], hit[1])
                changes.append("physician_profile")
                break

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
        row["enrichment_status"] = "agent_enriched"
    return changes


def enrich_row_agent(
    row: dict[str, str],
    *,
    prefer_live: bool = False,
    fetch_urls: bool = True,
    cache: dict | None = None,
) -> list[str]:
    payload, warnings = call_agent(row, prefer_live=prefer_live)
    verified = verify_agent_urls(payload, fetch=fetch_urls)
    if cache is not None:
        case_id = row.get("case_id", "")
        for slot, hits in verified.items():
            if hits:
                cache[(case_id, slot)] = hits
    return apply_agent_payload(row, payload, verified, agent_warnings=warnings)


def enrich_agent(
    *,
    path: Path = CASES_CSV,
    tier: str | None = None,
    case_id: str | None = None,
    prefer_live: bool = False,
    fetch_urls: bool = True,
    limit: int | None = None,
    dry_run: bool = False,
) -> tuple[int, int, dict[str, Any]]:
    rows = load_cases(path)
    cache = load_link_cache()
    touched = 0
    processed = 0
    status = get_provider_status(prefer_live=prefer_live)

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
        print(f"Agent enrich: {cid} …", flush=True)
        if dry_run:
            payload, warnings = call_agent(row, prefer_live=prefer_live)
            print(json.dumps({"case_id": cid, "warnings": warnings, "payload": payload}, indent=2))
            continue
        if enrich_row_agent(row, prefer_live=prefer_live, fetch_urls=fetch_urls, cache=cache):
            touched += 1

    if not dry_run:
        if cache:
            write_link_cache(cache)
        write_cases(rows, path)
    return len(rows), touched, status


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--path", type=Path, default=CASES_CSV)
    parser.add_argument("--tier", help="Limit to catalog_tier (e.g. A or B)")
    parser.add_argument("--case-id", help="Single case_id")
    parser.add_argument("--prefer-live", action="store_true", help="Use OpenAI when OPENAI_API_KEY set")
    parser.add_argument("--no-fetch", action="store_true", help="Skip web URL verification")
    parser.add_argument("--limit", type=int, help="Max rows to process")
    parser.add_argument("--dry-run", action="store_true", help="Print agent JSON only; do not write CSV")
    args = parser.parse_args()

    total, touched, status = enrich_agent(
        path=args.path,
        tier=args.tier,
        case_id=args.case_id,
        prefer_live=args.prefer_live,
        fetch_urls=not args.no_fetch,
        limit=args.limit,
        dry_run=args.dry_run,
    )
    if args.dry_run:
        print(f"Dry-run complete ({status['selection_reason']})")
        return
    print(
        f"Agent-enriched {touched} rows -> {args.path} ({total} total; "
        f"provider={status['provider_name']}; live={status['using_live_api']})"
    )


if __name__ == "__main__":
    main()
