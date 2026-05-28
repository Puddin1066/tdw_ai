"""Fill suggest_* columns in ri_cases_enriched.csv (never overwrites approved main columns)."""

from __future__ import annotations

import json
from datetime import date
from pathlib import Path

from pipeline.ri_cases_enriched_io import CASES_CSV, load_cases, write_cases
from pipeline.tier_a.comp_link_resolve import fetch_resolved_links, links_for_queue_row, load_link_cache

ROOT = Path(__file__).resolve().parents[1]
EVIDENCE = ROOT / "data" / "ri" / "ri_opportunity_evidence.json"


def _bool(value: str | None) -> bool:
    return (value or "").strip().lower() in {"1", "true", "t", "yes", "y"}


def _fill_biomcp_suggest(row: dict[str, str], evidence: dict | None) -> bool:
    if not evidence:
        return False
    pubs = evidence.get("publications") or []
    if not pubs:
        return False
    titles: list[str] = []
    urls: list[str] = []
    notes: list[str] = []
    for pub in pubs[:8]:
        title = (pub.get("title") or "").strip()
        if not title:
            continue
        pmid = str(pub.get("pmid") or "").strip()
        url = (pub.get("url") or "").strip()
        if pmid and not url:
            url = f"https://pubmed.ncbi.nlm.nih.gov/{pmid}/"
        titles.append(title)
        urls.append(url)
        inv = (pub.get("patent_link") or {}).get("matched_inventor_surnames") or []
        notes.append(f"BioMCP; inventors: {', '.join(inv)}" if inv else "BioMCP suggestion")
    row["suggest_publication_titles"] = "\n".join(titles)
    row["suggest_publication_urls"] = "\n".join(urls)
    row["suggest_publication_notes"] = "\n".join(notes)
    return True


def _fill_comp_suggest(row: dict[str, str], cache: dict) -> bool:
    name = (row.get("comp1_name") or "").strip()
    if not name:
        return False
    comp = {
        "precedent_name": name,
        "precedent_type": row.get("comp1_type", ""),
        "precedent_url": row.get("comp1_url", ""),
        "value_source_url": row.get("comp1_value_source_url", ""),
    }
    links = links_for_queue_row(
        comp,
        case_id=row.get("case_id", ""),
        cache=cache,
        fetch=True,
    )
    for label, url in links:
        if "Resolved:" in label or "prnewswire" in url or "businesswire" in url:
            if not row.get("suggest_comp1_value_source_url"):
                row["suggest_comp1_value_source_url"] = url
                row["suggest_comp1_notes"] = label.replace("Resolved: ", "")
                return True
    resolved = fetch_resolved_links(comp)
    if resolved:
        row["suggest_comp1_value_source_url"] = resolved[0][1]
        row["suggest_comp1_notes"] = resolved[0][0]
        cache[(row.get("case_id", ""), "1")] = resolved
        return True
    return False


def suggest(*, fetch_comp_links: bool = False) -> int:
    rows = load_cases()
    evidence_by: dict = {}
    if EVIDENCE.exists():
        payload = json.loads(EVIDENCE.read_text(encoding="utf-8"))
        evidence_by = payload.get("by_case_id") or {}
    cache = load_link_cache()
    today = date.today().isoformat()
    updated = 0
    for row in rows:
        if not _bool(row.get("catalog_include", "true")):
            continue
        changed = False
        if _fill_biomcp_suggest(row, evidence_by.get(row["case_id"])):
            changed = True
        if fetch_comp_links and (row.get("review_status") or "").lower() != "approved":
            if _fill_comp_suggest(row, cache):
                changed = True
        if changed:
            row["last_refreshed_at"] = today
            updated += 1
    write_cases(rows)
    return updated


def main() -> None:
    import argparse

    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--fetch-comp-links",
        action="store_true",
        help="Web-resolve comp1 financing URL candidates (slow)",
    )
    args = parser.parse_args()
    n = suggest(fetch_comp_links=args.fetch_comp_links)
    print(f"Updated suggest_* on {n} rows -> {CASES_CSV}")


if __name__ == "__main__":
    main()
