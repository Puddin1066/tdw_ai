"""Fetch patent-linked literature and trial evidence via BioMCP for RI opportunities.

Writes:
  - data/ri/ri_opportunity_evidence.json   (per-case publications + trials + network hints)
  - updates enrichment CSV columns when catalog rows exist

Publications are kept only when tied to anchored patent inventors and science overlap
(see pipeline.ri_biomcp_relevance).

Usage:
  python -m pipeline.enrich_ri_biomcp --all-opportunities --refresh
  python -m pipeline.enrich_ri_biomcp --case-id theromics_ri --refresh
  python -m pipeline.enrich_ri_biomcp --tier A --article-limit 6
"""

from __future__ import annotations

import argparse
import csv
import json
import re
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from connectors.biomcp_adapter import (
    _biomcp_prefix,
    extract_records,
    run_biomcp_article_get,
    run_biomcp_search,
)
from pipeline.ri_cases_enriched_io import load_cases as load_enriched_cases
from pipeline.ri_biomcp_relevance import (
    build_inventor_case_index,
    build_literature_profile,
    merge_search_terms,
    parse_author_surnames,
    rank_and_filter_publications,
    related_cases_for_profile,
)

DATA = Path(__file__).resolve().parents[1] / "data" / "ri"
CATALOG_PATH = DATA / "ri_opportunities_catalog_enrichment.csv"
CASES_PATH = DATA / "ri_cases_enriched.csv"
OPPORTUNITIES_PATH = DATA / "ri_opportunities.csv"
IP_PATH = DATA / "ri_ip_assets.csv"
EVIDENCE_PATH = DATA / "ri_opportunity_evidence.json"

GENERIC_INDICATION = "ri technology opportunity from patent corpus"
STOPWORDS = {
    "rhode",
    "island",
    "opportunity",
    "medical",
    "device",
    "therapeutic",
    "diagnostic",
    "platform",
    "technology",
    "brown",
    "university",
    "hospital",
}


def _utc_now() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat()


def _utc_now_iso() -> str:
    return _utc_now().replace("+00:00", "Z")


def _bool(value: str | None) -> bool:
    return (value or "").strip().lower() in {"1", "true", "t", "yes", "y"}


def _load_ip_by_case() -> dict[str, list[dict[str, str]]]:
    by_case: dict[str, list[dict[str, str]]] = {}
    if not IP_PATH.exists():
        return by_case
    for row in csv.DictReader(IP_PATH.open(encoding="utf-8")):
        by_case.setdefault(row["case_id"], []).append(row)
    return by_case


def _keywords(text: str, max_words: int = 6) -> str:
    tokens = re.findall(r"[A-Za-z0-9][A-Za-z0-9-]{2,}", text.lower())
    kept = [t for t in tokens if t not in STOPWORDS]
    return " ".join(kept[:max_words])


def build_search_terms(row: dict[str, str], ip_rows: list[dict[str, str]]) -> list[str]:
    terms: list[str] = []
    seen: set[str] = set()

    def add(term: str) -> None:
        t = re.sub(r"\s+", " ", term.strip())
        if len(t) < 4:
            return
        key = t.lower()
        if key in seen:
            return
        seen.add(key)
        terms.append(t)

    title = row.get("title_clean") or row.get("display_name") or row.get("target") or ""
    if title:
        add(title)
        kw = _keywords(title)
        if kw and kw != title.lower():
            add(kw)

    for ip in ip_rows[:2]:
        patent_title = (ip.get("title") or "").strip()
        if patent_title:
            add(patent_title[:120])
            add(_keywords(patent_title, max_words=8))

    indication = (row.get("indication") or "").strip()
    if indication and indication.lower() != GENERIC_INDICATION:
        add(indication)

    family = (row.get("program_family") or "").strip().replace("_", " ")
    if family:
        add(family)

    return terms[:3]


def _coerce_authors(raw: Any) -> list[Any]:
    if isinstance(raw, list):
        return raw
    if isinstance(raw, str) and raw.strip():
        return [part.strip() for part in re.split(r";|,|\|", raw) if part.strip()]
    return []


def _normalize_publication(raw: dict[str, Any], term: str) -> dict[str, Any]:
    pmid = str(raw.get("pmid") or raw.get("id") or raw.get("identifier") or "").strip()
    title = str(raw.get("title") or raw.get("name") or "").strip()
    clean_pmid = pmid if pmid.isdigit() else None
    abstract = str(
        raw.get("abstract")
        or raw.get("abstract_snippet")
        or raw.get("summary")
        or ""
    )
    url = raw.get("url") or (
        f"https://pubmed.ncbi.nlm.nih.gov/{clean_pmid}/" if clean_pmid else ""
    )
    return {
        "pmid": clean_pmid,
        "doi": raw.get("doi"),
        "title": title or (f"Publication {pmid}" if pmid else ""),
        "url": url,
        "journal": str(raw.get("journal") or ""),
        "publication_date": str(raw.get("publication_date") or raw.get("date") or ""),
        "authors": _coerce_authors(raw.get("authors")),
        "abstract_snippet": abstract[:400] + ("…" if len(abstract) > 400 else ""),
        "search_term": term,
        "source": "biomcp_article",
        "retrieved_at": _utc_now_iso(),
    }


def _enrich_publication_details(
    publications: list[dict[str, Any]],
    warnings: list[str],
    *,
    limit: int | None = None,
) -> None:
    targets = publications if limit is None else publications[:limit]
    for pub in targets:
        pmid = str(pub.get("pmid") or "")
        if not pmid.isdigit():
            continue
        detail_payload, err = run_biomcp_article_get(pmid, full=True)
        if err:
            warnings.append(f"article detail ({pmid}): {err}")
            continue
        if not detail_payload:
            continue
        rows = extract_records(detail_payload)
        if not rows:
            continue
        detail = rows[0]
        if detail.get("abstract"):
            pub["abstract_snippet"] = str(detail["abstract"])[:500]
        if detail.get("journal"):
            pub["journal"] = str(detail["journal"])
        if detail.get("publication_date"):
            pub["publication_date"] = str(detail["publication_date"])
        authors = _coerce_authors(detail.get("authors"))
        if authors:
            pub["authors"] = authors


def _normalize_trial(raw: dict[str, Any], term: str) -> dict[str, Any] | None:
    nct = str(
        raw.get("nct_id")
        or raw.get("nctId")
        or raw.get("nctid")
        or raw.get("id")
        or raw.get("identifier")
        or ""
    ).strip()
    title = str(raw.get("title") or raw.get("brief_title") or raw.get("name") or "").strip()
    if not nct and not title:
        return None
    if nct and not nct.upper().startswith("NCT"):
        nct = f"NCT{nct}" if nct.isdigit() else nct
    url = raw.get("url") or (
        f"https://clinicaltrials.gov/study/{nct}" if nct.upper().startswith("NCT") else ""
    )
    return {
        "nct_id": nct,
        "title": title or nct,
        "status": str(raw.get("status") or raw.get("overall_status") or ""),
        "phase": str(raw.get("phase") or raw.get("phases") or ""),
        "url": url,
        "search_term": term,
        "source": "biomcp_trial",
    }


def fetch_evidence_for_case(
    row: dict[str, str],
    ip_rows: list[dict[str, str]],
    *,
    article_limit: int = 6,
    trial_limit: int = 4,
    min_relevance: float = 0.2,
    min_science_overlap: float = 0.08,
    candidate_multiplier: int = 4,
) -> dict[str, Any]:
    case_id = row["case_id"]
    warnings: list[str] = []
    base_terms = build_search_terms(row, ip_rows)
    terms = merge_search_terms(row, ip_rows, base_terms)
    profile = build_literature_profile(row, ip_rows)
    publications: list[dict[str, Any]] = []
    trials: list[dict[str, Any]] = []

    if _biomcp_prefix() is None:
        narrative = (
            f"BioMCP pending for {row.get('title_clean', case_id)}. "
            f"Install BioMCP and run `npm run enrich:ri:biomcp` to fetch patent-linked publications."
        )
        return {
            "case_id": case_id,
            "status": "unavailable",
            "search_terms": terms,
            "publications": [],
            "trials": [],
            "warnings": ["BioMCP not installed (biomcp CLI or python -m biomcp)"],
            "fetched_at": _utc_now(),
            "literature_narrative": narrative,
            "publication_count": 0,
            "trial_count": 0,
            "filter_stats": {},
            "related_case_ids": [],
        }

    per_term_articles = max(4, min(8, article_limit + 2))
    for term in terms:
        payload, err = run_biomcp_search(
            "article",
            term,
            limit=per_term_articles,
            offset=0,
        )
        if err:
            warnings.append(f"article search ({term}): {err}")
            continue
        if payload:
            for idx, rec in enumerate(extract_records(payload)):
                publications.append(_normalize_publication(rec, term))

    for term in terms[:1]:
        payload, err = run_biomcp_search("trial", term, limit=trial_limit, offset=0)
        if err:
            warnings.append(f"trial search ({term}): {err}")
            continue
        if payload:
            for rec in extract_records(payload):
                trial = _normalize_trial(rec, term)
                if trial:
                    trials.append(trial)

    deduped_pubs: list[dict[str, Any]] = []
    seen_pub: set[str] = set()
    for pub in publications:
        title = (pub.get("title") or "").strip()
        if not title:
            continue
        key = str(pub.get("pmid") or title).lower()
        if not key or key in seen_pub:
            continue
        seen_pub.add(key)
        deduped_pubs.append(pub)

    if deduped_pubs:
        _enrich_publication_details(deduped_pubs, warnings, limit=min(10, len(deduped_pubs)))

    filter_stats: dict[str, int] = {"candidates": len(deduped_pubs), "kept": 0}
    deduped_pubs, filter_stats = rank_and_filter_publications(
        deduped_pubs,
        profile,
        min_score=min_relevance,
        min_science_overlap=min_science_overlap,
        limit=article_limit * candidate_multiplier,
        patent_linked_only=True,
    )
    deduped_pubs, filter_stats = rank_and_filter_publications(
        deduped_pubs,
        profile,
        min_score=min_relevance,
        min_science_overlap=min_science_overlap,
        limit=article_limit,
        patent_linked_only=True,
    )

    seen_trial: set[str] = set()
    deduped_trials: list[dict[str, Any]] = []
    for trial in trials:
        key = str(trial.get("nct_id") or trial.get("title", "")).lower()
        if not key or key in seen_trial:
            continue
        seen_trial.add(key)
        deduped_trials.append(trial)
    deduped_trials = deduped_trials[:trial_limit]

    if deduped_pubs:
        status = "patent_linked"
    elif filter_stats.get("candidates", 0) > 0:
        status = "no_patent_linked_matches"
        warnings.append(
            f"Dropped {filter_stats.get('candidates', 0)} candidate(s): "
            f"no inventor match or insufficient science overlap with anchored patent."
        )
    elif trials:
        status = "trials_only"
    elif warnings:
        status = "partial"
    else:
        status = "empty"

    narrative = _literature_narrative(row, deduped_pubs, deduped_trials, profile)

    return {
        "case_id": case_id,
        "status": status,
        "search_terms": terms,
        "publications": deduped_pubs,
        "trials": deduped_trials,
        "warnings": warnings,
        "fetched_at": _utc_now(),
        "literature_narrative": narrative,
        "publication_count": len(deduped_pubs),
        "trial_count": len(deduped_trials),
        "filter_stats": filter_stats,
        "inventor_surnames": sorted(profile.get("inventor_surnames") or []),
        "primary_lens_id": profile.get("primary_lens_id", ""),
    }


def _literature_narrative(
    row: dict[str, str],
    publications: list[dict[str, Any]],
    trials: list[dict[str, Any]],
    profile: dict[str, Any],
) -> str:
    title = row.get("title_clean") or row.get("display_name") or row.get("case_id", "")
    lens = profile.get("primary_display_key") or profile.get("primary_lens_id") or "anchored patent"
    inventors = profile.get("inventor_surnames") or set()

    if not publications and not trials:
        if inventors:
            return (
                f"No patent-linked publications found for {title} "
                f"(inventors: {', '.join(sorted(inventors))}; anchor: {lens})."
            )
        return f"No patent-linked publications or trials for {title}."

    parts = [f"{len(publications)} patent-linked publication(s)"]
    if inventors:
        parts.append(f"sharing inventor surnames ({', '.join(sorted(inventors))})")
    parts.append(f"with {lens}.")
    if trials:
        parts.append(f"{len(trials)} related trial(s) from topic search.")
    if publications:
        link = publications[0].get("patent_link") or {}
        matched = link.get("matched_inventor_surnames") or []
        lead = publications[0].get("title", "")[:100]
        if matched:
            parts.append(f"Lead: {lead} (via {', '.join(matched)}).")
        else:
            parts.append(f"Lead: {lead}.")
    return " ".join(parts)


def _merge_catalog_evidence_columns(row: dict[str, str], evidence: dict[str, Any]) -> None:
    pubs = evidence.get("publications") or []
    row["biomcp_evidence_status"] = str(evidence.get("status", ""))
    row["biomcp_publication_count"] = str(evidence.get("publication_count", len(pubs)))
    row["biomcp_trial_count"] = str(evidence.get("trial_count", len(evidence.get("trials") or [])))
    row["biomcp_key_publications"] = " | ".join(
        (p.get("title") or "")[:80] for p in pubs[:3]
    )
    row["biomcp_literature_narrative"] = evidence.get("literature_narrative", "")
    row["biomcp_search_terms"] = " | ".join(evidence.get("search_terms") or [])
    row["biomcp_fetched_at"] = evidence.get("fetched_at", "")


def _row_from_opportunity(opp: dict[str, str], catalog_by_id: dict[str, dict[str, str]]) -> dict[str, str]:
    cid = opp["case_id"]
    if cid in catalog_by_id:
        return dict(catalog_by_id[cid])
    return {
        "case_id": cid,
        "title_clean": opp.get("display_name") or opp.get("target") or cid,
        "display_name": opp.get("display_name", ""),
        "indication": opp.get("indication", ""),
        "program_family": "",
        "catalog_include": "false",
        "catalog_tier": "",
    }


def _iter_enrichment_targets(
    *,
    all_opportunities: bool,
    catalog_rows: list[dict[str, str]],
    catalog_by_id: dict[str, dict[str, str]],
    case_ids: set[str] | None,
    tier: str | None,
    catalog_only: bool,
    cases_rows: list[dict[str, str]] | None = None,
) -> list[dict[str, str]]:
    if cases_rows:
        out: list[dict[str, str]] = []
        for row in cases_rows:
            if catalog_only and not _bool(row.get("catalog_include", "true")):
                continue
            cid = row["case_id"]
            if case_ids and cid not in case_ids:
                continue
            if tier and row.get("catalog_tier", "").upper() != tier.upper():
                continue
            out.append(dict(row))
        return out

    if all_opportunities and OPPORTUNITIES_PATH.exists():
        targets: list[dict[str, str]] = []
        for opp in csv.DictReader(OPPORTUNITIES_PATH.open(encoding="utf-8")):
            row = _row_from_opportunity(opp, catalog_by_id)
            cid = row["case_id"]
            if case_ids and cid not in case_ids:
                continue
            if tier and row.get("catalog_tier", "").upper() != tier.upper():
                continue
            targets.append(row)
        return targets

    out: list[dict[str, str]] = []
    for row in catalog_rows:
        if catalog_only and not _bool(row.get("catalog_include", "true")):
            continue
        cid = row["case_id"]
        if case_ids and cid not in case_ids:
            continue
        if tier and row.get("catalog_tier", "").upper() != tier.upper():
            continue
        out.append(row)
    return out


def _write_evidence_checkpoint(
    by_case: dict[str, Any],
    *,
    biomcp_available: bool,
) -> None:
    network_edges: list[dict[str, str]] = []
    for cid, block in by_case.items():
        for related in block.get("related_case_ids") or []:
            network_edges.append(
                {
                    "source_case_id": cid,
                    "target_case_id": related,
                    "relationship": "shared_patent_inventor",
                }
            )
    payload = {
        "schema_version": 2,
        "generated_by": "pipeline/enrich_ri_biomcp.py",
        "biomcp_available": biomcp_available,
        "patent_linked_only": True,
        "opportunity_count": len(by_case),
        "network_edge_count": len(network_edges),
        "network_edges": network_edges,
        "by_case_id": by_case,
    }
    EVIDENCE_PATH.write_text(json.dumps(payload, indent=2), encoding="utf-8")


def run_enrichment(
    *,
    case_ids: set[str] | None = None,
    tier: str | None = None,
    refresh: bool = False,
    article_limit: int = 6,
    trial_limit: int = 4,
    all_opportunities: bool = False,
    catalog_only: bool = True,
) -> dict[str, Any]:
    existing: dict[str, Any] = {}
    if EVIDENCE_PATH.exists() and not refresh:
        existing = json.loads(EVIDENCE_PATH.read_text(encoding="utf-8")).get("by_case_id", {})

    ip_by_case = _load_ip_by_case()
    catalog_rows = list(csv.DictReader(CATALOG_PATH.open(encoding="utf-8"))) if CATALOG_PATH.exists() else []
    catalog_by_id = {r["case_id"]: r for r in catalog_rows}
    cases_rows: list[dict[str, str]] | None = None
    if CASES_PATH.exists():
        cases_rows = load_enriched_cases(CASES_PATH)
        for row in cases_rows:
            catalog_by_id.setdefault(row["case_id"], row)
    surname_index = build_inventor_case_index(ip_by_case)

    targets = _iter_enrichment_targets(
        all_opportunities=all_opportunities,
        catalog_rows=catalog_rows,
        catalog_by_id=catalog_by_id,
        case_ids=case_ids,
        tier=tier,
        catalog_only=catalog_only and not all_opportunities,
        cases_rows=cases_rows,
    )

    by_case: dict[str, Any] = dict(existing) if not refresh else {}
    biomcp_cols = [
        "biomcp_evidence_status",
        "biomcp_publication_count",
        "biomcp_trial_count",
        "biomcp_key_publications",
        "biomcp_literature_narrative",
        "biomcp_search_terms",
        "biomcp_fetched_at",
    ]

    fetched = 0
    skipped = 0
    for row in targets:
        cid = row["case_id"]
        if not refresh and cid in by_case and by_case[cid].get("status") in {
            "patent_linked",
            "fetched",
            "trials_only",
        }:
            if cid in catalog_by_id:
                _merge_catalog_evidence_columns(catalog_by_id[cid], by_case[cid])
            skipped += 1
            continue

        ip_rows = ip_by_case.get(cid, [])
        if all_opportunities and not ip_rows:
            continue

        print(f"BioMCP: {cid} …", flush=True)
        evidence = fetch_evidence_for_case(
            row,
            ip_rows,
            article_limit=article_limit,
            trial_limit=trial_limit,
        )
        profile = build_literature_profile(row, ip_rows)
        evidence["related_case_ids"] = related_cases_for_profile(profile, cid, surname_index)
        by_case[cid] = evidence
        if cid in catalog_by_id:
            _merge_catalog_evidence_columns(catalog_by_id[cid], evidence)
        fetched += 1
        print(
            f"  -> {evidence.get('status')} "
            f"({evidence.get('publication_count', 0)} patent-linked pubs, "
            f"{evidence.get('trial_count', 0)} trials, "
            f"{len(evidence.get('related_case_ids') or [])} related cases)",
            flush=True,
        )
        _write_evidence_checkpoint(by_case, biomcp_available=_biomcp_prefix() is not None)

    if catalog_rows:
        fieldnames = list(catalog_rows[0].keys())
        for col in biomcp_cols:
            if col not in fieldnames:
                fieldnames.append(col)
        with CATALOG_PATH.open("w", newline="", encoding="utf-8") as f:
            writer = csv.DictWriter(f, fieldnames=fieldnames, extrasaction="ignore")
            writer.writeheader()
            writer.writerows(catalog_rows)

    _write_evidence_checkpoint(by_case, biomcp_available=_biomcp_prefix() is not None)
    network_edges = json.loads(EVIDENCE_PATH.read_text(encoding="utf-8")).get("network_edges", [])
    return {
        "fetched": fetched,
        "skipped": skipped,
        "total": len(by_case),
        "network_edges": len(network_edges),
        "path": str(EVIDENCE_PATH),
    }


def main() -> None:
    parser = argparse.ArgumentParser(description="Patent-linked BioMCP enrichment for RI opportunities")
    parser.add_argument("--case-id", action="append", dest="case_ids", default=[])
    parser.add_argument("--tier", help="Only enrich catalog_tier (e.g. A)")
    parser.add_argument("--refresh", action="store_true", help="Re-fetch all targets")
    parser.add_argument("--article-limit", type=int, default=6)
    parser.add_argument("--trial-limit", type=int, default=4)
    parser.add_argument(
        "--all-opportunities",
        action="store_true",
        help="Enrich every case in ri_opportunities.csv that has ri_ip_assets (not only catalog_include)",
    )
    parser.add_argument(
        "--include-catalog-only",
        action="store_true",
        help="When not using --all-opportunities, only catalog_include=true rows (default)",
    )
    args = parser.parse_args()
    case_ids = set(args.case_ids) if args.case_ids else None
    result = run_enrichment(
        case_ids=case_ids,
        tier=args.tier,
        refresh=args.refresh,
        article_limit=args.article_limit,
        trial_limit=args.trial_limit,
        all_opportunities=args.all_opportunities,
        catalog_only=not args.all_opportunities,
    )
    print(
        f"BioMCP evidence: fetched {result['fetched']}, skipped {result['skipped']}, "
        f"{result['total']} cases, {result['network_edges']} inventor-network edges -> {result['path']}"
    )
    if CATALOG_PATH.exists():
        print(f"Updated catalog columns -> {CATALOG_PATH}")


if __name__ == "__main__":
    main()
