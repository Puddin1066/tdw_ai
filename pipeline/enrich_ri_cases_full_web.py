"""Full web-search enrichment pass for data/ri/ri_cases_enriched.csv.

Orchestrates tier-A comp sync, BioMCP, comp URL resolution, web search,
ClinicalTrials.gov, and optional live LLM agent to fill remaining gaps with
verified primary-source data.

Does not set review_status=approved.
"""

from __future__ import annotations

import argparse
import json
import re
import time
from datetime import date
from pathlib import Path
from typing import Any

from pipeline.apply_tier_a_comps_to_enriched import apply_tier_a_comps
from pipeline.brown_vivo_profiles import fill_brown_profile_url
from pipeline.enrich_ri_cases_agent import enrich_row_agent
from pipeline.enrich_ri_cases_comps import enrich_comps, resolve_comp_urls
from pipeline.enrich_ri_cases_web import (
    _append_note,
    _append_queries,
    _bool,
    _profile_hit,
    _rd_search_queries,
    _search_top_hit,
    enrich_row as enrich_row_web,
)
from pipeline.ri_cases_enriched_schema import COMP_PREFIXES
from pipeline.ri_source_utils import finish_row_sources as _finish_row_sources
from pipeline.ri_biomcp_publications import apply_publications
from pipeline.ri_cases_enriched_io import CASES_CSV, load_cases, write_cases
from pipeline.ri_cases_enriched_schema import COMP_PREFIXES
from pipeline.tier_a.comp_financing import comp_base_name
from pipeline.ri_trial_enrichment import (
    _load_ip_by_case,
    enrich_trials_for_row,
    load_trial_templates,
)

ROOT = Path(__file__).resolve().parents[1]
EVIDENCE_PATH = ROOT / "data" / "ri" / "ri_opportunity_evidence.json"
FETCH_DELAY_S = 0.75

ROLE_BY_TYPE: dict[str, str] = {
    "incumbent": "incumbent",
    "public": "platform",
    "ri_public": "platform",
    "ri_operating": "operating",
    "pharma_deal": "pharma_deal",
    "research": "research",
    "startup": "platform",
}


def _split_lines(value: str) -> list[str]:
    return [x.strip() for x in (value or "").replace("\r", "").split("\n") if x.strip()]


def _merge_audit(row: dict[str, str]) -> tuple[list[str], list[str]]:
    queries: list[str] = []
    notes: list[str] = []
    if row.get("web_search_queries"):
        queries.extend(q.strip() for q in row["web_search_queries"].split("|") if q.strip())
    if row.get("web_search_notes"):
        notes.extend(n.strip() for n in row["web_search_notes"].split("\n") if n.strip())
    return queries, notes


def _write_audit(row: dict[str, str], queries: list[str], notes: list[str]) -> None:
    if queries:
        row["web_search_queries"] = " | ".join(queries)
    if notes:
        row["web_search_notes"] = "\n".join(notes)


def _apply_comp_url(row: dict[str, str], prefix: str, label: str, url: str) -> bool:
    if not url or (row.get(f"{prefix}value_source_url") or "").strip():
        return False
    status = (row.get(f"{prefix}validation_status") or "").lower()
    if status == "verified":
        return False
    row[f"{prefix}value_source_url"] = url
    if not (row.get(f"{prefix}validation_status") or "").strip():
        row[f"{prefix}validation_status"] = "suggested"
    return True


def _resolve_incumbent_or_public(comp: dict[str, str]) -> tuple[str, str] | None:
    """Market-cap / IR URL for incumbents and public comps without VC rounds."""
    base = comp_base_name(comp.get("precedent_name", ""))
    ptype = (comp.get("precedent_type") or "").lower()
    if ptype not in {"incumbent", "public", "ri_public", "ri_operating"}:
        return None
    queries = [
        f'"{base}" market cap site:finance.yahoo.com OR site:stockanalysis.com',
        f"{base} investor relations site:investors OR site:newsroom",
    ]
    if ptype == "ri_operating":
        purl = (comp.get("precedent_url") or "").strip()
        if purl:
            return f"{base} program page", purl
    for query in queries:
        time.sleep(FETCH_DELAY_S)
        for title, url in _duckduckgo_html_results(query, limit=3):
            if _acceptable_result_url(url, title=title):
                return title, url
    return None


def _ensure_supporting_citations(row: dict[str, str], prefix: str) -> bool:
    if (row.get(f"{prefix}supporting_citations") or "").strip():
        return False
    name = (row.get(f"{prefix}name") or "").strip()
    if not name:
        return False
    lines: list[str] = []
    purl = (row.get(f"{prefix}url") or "").strip()
    vsrc = (row.get(f"{prefix}value_source_url") or "").strip()
    if vsrc and purl and vsrc.rstrip("/") != purl.rstrip("/"):
        lines.append(f"Company / program | {purl}")
    elif purl:
        lines.append(f"Program page | {purl}")
    elif vsrc:
        lines.append(f"Financing / market source | {vsrc}")
    if lines:
        row[f"{prefix}supporting_citations"] = "\n".join(lines)
        return True
    return False


def _ensure_comp_role(row: dict[str, str], prefix: str) -> bool:
    if (row.get(f"{prefix}role") or "").strip():
        return False
    name = (row.get(f"{prefix}name") or "").strip()
    if not name:
        return False
    ctype = (row.get(f"{prefix}type") or "").lower()
    notes = (row.get(f"{prefix}notes") or "").lower()
    name_l = name.lower()
    if any(k in notes or k in name_l for k in ("diagnostic", " dx", "sepsis", "triage", "lvo", "host rna")):
        row[f"{prefix}role"] = "diagnostic"
        return True
    if any(k in notes or k in name_l for k in ("therapeutic", "biologic", "opioid", "c1 inhibitor", "plasma")):
        row[f"{prefix}role"] = "therapeutic"
        return True
    role = ROLE_BY_TYPE.get(ctype, "platform")
    row[f"{prefix}role"] = role
    return True


from pipeline.tier_a.comp_link_resolve import (
    _acceptable_result_url,
    _duckduckgo_html_results,
    fetch_resolved_links,
    load_link_cache,
    write_link_cache,
)

_IP_BY_CASE: dict[str, list[dict[str, str]]] | None = None
_TRIAL_TEMPLATES: list[dict[str, str]] | None = None


def _trial_enrichment_context() -> tuple[dict[str, list[dict[str, str]]], list[dict[str, str]]]:
    global _IP_BY_CASE, _TRIAL_TEMPLATES
    if _IP_BY_CASE is None:
        _IP_BY_CASE = _load_ip_by_case()
    if _TRIAL_TEMPLATES is None:
        _TRIAL_TEMPLATES = load_trial_templates()
    return _IP_BY_CASE, _TRIAL_TEMPLATES


def fill_trials_from_web(row: dict[str, str], *, force: bool = False) -> list[str]:
    """Mechanism/comp-precedent trial enrichment; empty main columns when no strong match."""
    if not force and (
        int(row.get("trial_count") or 0) > 0 or _split_lines(row.get("trial_nct_ids", ""))
    ):
        return []
    ip_by, templates = _trial_enrichment_context()
    ip_rows = ip_by.get(row.get("case_id", ""), [])
    return enrich_trials_for_row(row, ip_rows, templates, force=force)


def fill_literature_from_evidence(row: dict[str, str], evidence: dict[str, Any] | None) -> bool:
    if (row.get("literature_narrative") or "").strip():
        return False
    if evidence and (evidence.get("literature_narrative") or "").strip():
        row["literature_narrative"] = evidence["literature_narrative"].strip()
        return True
    pubs = (evidence or {}).get("publications") or []
    if pubs:
        title = row.get("title_clean") or row.get("display_name") or row["case_id"]
        lead = (pubs[0].get("title") or "")[:100]
        row["literature_narrative"] = (
            f"BioMCP found {len(pubs)} patent-linked publication(s) for {title}. "
            f"Lead candidate: {lead}. See suggest_publication_* for curator promotion."
        )
        return True
    return False


def fill_suggest_publications(row: dict[str, str], evidence: dict[str, Any] | None) -> bool:
    if _split_lines(row.get("suggest_publication_titles", "")):
        return False
    pubs = (evidence or {}).get("publications") or []
    if not pubs:
        return False
    titles, urls, notes = [], [], []
    for pub in pubs[:8]:
        title = (pub.get("title") or "").strip()
        if not title:
            continue
        pmid = str(pub.get("pmid") or "").strip()
        url = (pub.get("url") or "").strip() or (
            f"https://pubmed.ncbi.nlm.nih.gov/{pmid}/" if pmid.isdigit() else ""
        )
        inv = (pub.get("patent_link") or {}).get("matched_inventor_surnames") or []
        note = "BioMCP patent-linked"
        if inv:
            note += f"; inventors: {', '.join(inv)}"
        titles.append(title)
        urls.append(url)
        notes.append(note)
    if not titles:
        return False
    row["suggest_publication_titles"] = "\n".join(titles)
    row["suggest_publication_urls"] = "\n".join(urls)
    row["suggest_publication_notes"] = "\n".join(notes)
    return True


def fill_rd_milestones_from_web(row: dict[str, str], queries: list[str], notes: list[str]) -> bool:
    if (row.get("rd_milestones") or "").strip():
        return False
    title = (row.get("title_clean") or row.get("display_name") or "").strip()
    company = (row.get("company") or "").strip()
    indication = (row.get("indication") or "").strip()
    stage = (row.get("development_stage") or "validation").strip()
    comp = (row.get("comp1_name") or "").strip()
    comp_path = (row.get("comp1_development_path") or "").strip()

    milestones: list[str] = []
    search_qs = [
        f"{company} {title} preclinical milestone" if company and company.upper() != "TBD" else "",
        f"{title} {indication} IND enabling" if indication else "",
        f"{comp} development path {stage}" if comp else "",
    ]
    for q in search_qs:
        q = q.strip()
        if not q or len(q) < 12:
            continue
        _append_queries(queries, q)
        hit = _search_top_hit(q)
        if hit:
            label = re.sub(r"\s+", " ", hit[0]).strip()[:140]
            if label and label not in milestones:
                milestones.append(label)
                _append_note(notes, "rd_milestone", label, hit[1])

    if comp_path:
        milestones.insert(0, f"Benchmark: {comp} — {comp_path[:100]}")
    if not milestones:
        milestones.append(
            f"De-risk {title} ({stage}): analytical validation → pilot study → "
            f"regulatory-ready package aligned with {comp or 'path comps'}."
        )

    row["rd_milestones"] = "\n".join(milestones[:4])
    types = []
    for _ in milestones[:4]:
        if "510" in row["rd_milestones"].lower() or "fda" in row["rd_milestones"].lower():
            types.append("regulatory")
        elif "pilot" in row["rd_milestones"].lower() or "clinical" in row["rd_milestones"].lower():
            types.append("clinical")
        else:
            types.append("preclinical")
    row["rd_milestone_types"] = " | ".join(types[:4])
    return True


def fill_row_web_gaps(
    row: dict[str, str],
    evidence: dict[str, Any] | None,
    *,
    fetch_urls: bool = True,
    cache: dict | None = None,
) -> list[str]:
    """Fill missing fields for one row using web search + evidence."""
    if not _bool(row.get("catalog_include", "true")):
        return []
    if (row.get("review_status") or "").lower() == "approved":
        return []

    changes: list[str] = []
    queries, notes = _merge_audit(row)

    if fill_brown_profile_url(row):
        changes.append("vivo_profile")

    for rank, prefix in zip((str(i) for i in range(1, len(COMP_PREFIXES) + 1)), COMP_PREFIXES, strict=True):
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
            if not resolved:
                inc = _resolve_incumbent_or_public(comp)
                if inc:
                    resolved = [inc]
            if resolved:
                label, url = resolved[0]
                if _apply_comp_url(row, prefix, label, url):
                    changes.append(f"{prefix}url")
                    _append_note(notes, f"comp{rank}", label, url)
                if cache is not None:
                    cache[(row["case_id"], rank)] = resolved

    suggest_url = (row.get("suggest_comp1_value_source_url") or "").strip()
    if suggest_url and not (row.get("comp1_value_source_url") or "").strip():
        row["comp1_value_source_url"] = suggest_url
        changes.append("comp1_from_suggest")

    if fill_literature_from_evidence(row, evidence):
        changes.append("literature")
    if fill_suggest_publications(row, evidence):
        changes.append("suggest_pubs")
    trial_changes = fill_trials_from_web(row)
    if trial_changes:
        changes.extend(trial_changes)

    if fill_rd_milestones_from_web(row, queries, notes):
        changes.append("rd_milestones")

    if not (row.get("physician_lead_profile_url") or "").strip():
        name = (row.get("physician_lead_name") or "").strip()
        if name and name.upper() != "TBD":
            parts = name.title().split()
            if len(parts) >= 2:
                short = f"{parts[0]} {parts[-1]}"
                profile_qs = [
                    f'"{short}" site:lifespan.org OR site:rhodeislandhospital.org',
                    f'"{short}" site:web.uri.edu OR site:vivo.brown.edu',
                    f'"{short}" {row.get("physician_lead_institution", "")} physician profile',
                ]
                for q in profile_qs:
                    q = q.strip()
                    if not q:
                        continue
                    _append_queries(queries, q)
                    hit = _profile_hit(q)
                    if hit:
                        row["physician_lead_profile_url"] = hit[1]
                        _append_note(notes, "profile", hit[0], hit[1])
                        changes.append("physician_profile")
                        break

    _write_audit(row, queries, notes)
    if changes:
        row["last_refreshed_at"] = date.today().isoformat()
        row["enrichment_status"] = "full_web_enriched"
    return changes


def enrich_full_web(
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
) -> dict[str, Any]:
    summary: dict[str, Any] = {"steps": []}

    if not skip_sync:
        _, n = apply_tier_a_comps(path=path, tier="A")
        summary["steps"].append(f"tier_a_sync:{n}")

    if not skip_remediate:
        remediate(path=path)
        summary["steps"].append("remediate")

    if not skip_biomcp:
        _, n = apply_publications(path=path, tier="A", overwrite=False)
        summary["steps"].append(f"biomcp_tier_a:{n}")

    _, n = enrich_comps(path=path, case_id=case_id, fetch_urls=False, seed_only=False)
    summary["steps"].append(f"comp_seed:{n}")

    evidence_by: dict[str, Any] = {}
    if EVIDENCE_PATH.exists():
        evidence_by = json.loads(EVIDENCE_PATH.read_text(encoding="utf-8")).get("by_case_id") or {}

    rows = load_cases(path)
    cache = load_link_cache()
    touched = 0
    processed = 0

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
        print(f"Full web enrich: {cid} …", flush=True)

        changes = fill_row_web_gaps(
            row,
            evidence_by.get(cid),
            fetch_urls=fetch_urls,
            cache=cache,
        )
        enrich_row_web(
            row,
            fetch_comps=fetch_urls,
            comps_heuristic_only=not fetch_urls,
            fetch_profiles=True,
            fetch_rd=True,
            draft_rd=not (row.get("rd_plan_summary") or "").strip(),
            cache=cache,
        )
        if not skip_agent:
            agent_changes = enrich_row_agent(
                row,
                prefer_live=prefer_live_agent,
                fetch_urls=fetch_urls,
                cache=cache,
            )
            changes.extend(agent_changes)

        changes.extend(_finish_row_sources(row, comp_prefixes=COMP_PREFIXES))

        if changes:
            touched += 1
            print(f"  -> {', '.join(sorted(set(changes)))}", flush=True)

    if cache:
        write_link_cache(cache)
    write_cases(rows, path)
    summary["processed"] = processed
    summary["touched"] = touched
    summary["total_rows"] = len(rows)
    return summary


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--path", type=Path, default=CASES_CSV)
    parser.add_argument("--tier", help="Limit to catalog_tier (A or B)")
    parser.add_argument("--case-id", help="Single case_id")
    parser.add_argument("--skip-sync", action="store_true")
    parser.add_argument("--skip-remediate", action="store_true")
    parser.add_argument("--skip-biomcp", action="store_true")
    parser.add_argument("--skip-agent", action="store_true")
    parser.add_argument("--no-live-agent", action="store_true", help="Use mock/fixture agent")
    parser.add_argument("--no-fetch", action="store_true", help="Skip DuckDuckGo URL fetches")
    parser.add_argument("--limit", type=int)
    args = parser.parse_args()

    summary = enrich_full_web(
        path=args.path,
        tier=args.tier,
        case_id=args.case_id,
        skip_sync=args.skip_sync,
        skip_remediate=args.skip_remediate,
        skip_biomcp=args.skip_biomcp,
        skip_agent=args.skip_agent,
        prefer_live_agent=not args.no_live_agent,
        fetch_urls=not args.no_fetch,
        limit=args.limit,
    )
    print(
        f"Full web enrichment complete: {summary['touched']}/{summary['processed']} rows touched "
        f"({summary['total_rows']} total). Steps: {', '.join(summary['steps'])}"
    )


if __name__ == "__main__":
    main()
