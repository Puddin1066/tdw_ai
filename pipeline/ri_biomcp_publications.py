"""Apply BioMCP patent-linked literature to ri_cases_enriched publication columns.

Tier A rows get 2–6 publications when the lead author has an RI affiliation on the
allowlist (Brown, RIH/Lifespan, URI, …). Patent-linked hits that fail the RI lead
rule remain in suggest_* for curator review.

Uses:
  - data/ri/ri_opportunity_evidence.json (from pipeline.enrich_ri_biomcp)
  - PubMed efetch for first-author affiliations when BioMCP search rows are sparse
  - Supplemental BioMCP article searches: inventor[Author] AND RI affiliation
"""

from __future__ import annotations

import os
import re
import time
from pathlib import Path
from typing import Any
from xml.etree import ElementTree

import httpx
import yaml

from connectors.biomcp_adapter import extract_records, run_biomcp_search
from pipeline.enrich_ri_biomcp import fetch_evidence_for_case
from pipeline.ri_biomcp_relevance import (
    build_literature_profile,
    normalize_surname,
    parse_inventor_surnames,
    patent_link_for_publication,
    rank_and_filter_publications,
)
from pipeline.ri_cases_enriched_io import CASES_CSV, load_cases, write_cases

ROOT = Path(__file__).resolve().parents[1]
EVIDENCE_PATH = ROOT / "data" / "ri" / "ri_opportunity_evidence.json"
IP_PATH = ROOT / "data" / "ri" / "ri_ip_assets.csv"
ALLOWLIST_PATH = ROOT / "data" / "ri" / "ri_institution_allowlist.yaml"

EFETCH_URL = "https://eutils.ncbi.nlm.nih.gov/entrez/eutils/efetch.fcgi"
ESEARCH_URL = "https://eutils.ncbi.nlm.nih.gov/entrez/eutils/esearch.fcgi"

MIN_TIER_A_PUBS = 2
MAX_TIER_A_PUBS = 6

_LAST_NCBI_CALL = 0.0


def _ncbi_params(extra: dict[str, str]) -> dict[str, str]:
    params = dict(extra)
    api_key = (os.environ.get("NCBI_API_KEY") or "").strip()
    if api_key:
        params["api_key"] = api_key
    return params


def _ncbi_throttle() -> None:
    global _LAST_NCBI_CALL
    delay = 0.11 if (os.environ.get("NCBI_API_KEY") or "").strip() else 0.34
    elapsed = time.monotonic() - _LAST_NCBI_CALL
    if elapsed < delay:
        time.sleep(delay - elapsed)
    _LAST_NCBI_CALL = time.monotonic()

RI_AFFILIATION_QUERY = (
    'Brown University[Affiliation] OR "Rhode Island Hospital"[Affiliation] '
    'OR Lifespan[Affiliation] OR "University of Rhode Island"[Affiliation] '
    'OR URI[Affiliation] OR "Women and Infants"[Affiliation]'
)


def _bool(value: str | None) -> bool:
    return (value or "").strip().lower() in {"1", "true", "t", "yes", "y"}


def _split_lines(value: str) -> list[str]:
    return [x.strip() for x in (value or "").replace("\r", "").split("\n") if x.strip()]


def load_allowlist() -> list[str]:
    if not ALLOWLIST_PATH.exists():
        return []
    data = yaml.safe_load(ALLOWLIST_PATH.read_text(encoding="utf-8"))
    return list(data.get("publication_affiliations") or [])


def match_ri_affiliation(text: str, allowlist: list[str]) -> str:
    lower = (text or "").lower()
    for term in allowlist:
        if term.lower() in lower:
            return term
    return ""


def _load_ip_by_case() -> dict[str, list[dict[str, str]]]:
    import csv

    by_case: dict[str, list[dict[str, str]]] = {}
    if not IP_PATH.exists():
        return by_case
    for row in csv.DictReader(IP_PATH.open(encoding="utf-8")):
        by_case.setdefault(row["case_id"], []).append(row)
    return by_case


def _parse_author(author_el: ElementTree.Element) -> dict[str, str]:
    last = author_el.find("LastName")
    fore = author_el.find("ForeName")
    aff_el = author_el.find("AffiliationInfo/Affiliation")
    collective = author_el.find("CollectiveName")
    return {
        "last": (last.text or "").strip() if last is not None else "",
        "first": (fore.text or "").strip() if fore is not None else "",
        "affiliation": (aff_el.text or "").strip() if aff_el is not None else "",
        "collective": (collective.text or "").strip() if collective is not None else "",
    }


def fetch_pubmed_details(pmids: list[str]) -> dict[str, dict[str, Any]]:
    """Fetch title + first-author affiliation from PubMed XML."""
    clean = [p for p in pmids if p.isdigit()]
    if not clean:
        return {}
    out: dict[str, dict[str, Any]] = {}
    chunk_size = 8
    with httpx.Client(timeout=60.0) as client:
        for i in range(0, len(clean), chunk_size):
            batch = clean[i : i + chunk_size]
            for attempt in range(3):
                _ncbi_throttle()
                resp = client.get(
                    EFETCH_URL,
                    params=_ncbi_params({"db": "pubmed", "id": ",".join(batch), "retmode": "xml"}),
                )
                if resp.status_code == 429:
                    time.sleep(1.5 * (attempt + 1))
                    continue
                resp.raise_for_status()
                break
            else:
                continue
            root = ElementTree.fromstring(resp.text)
            for article in root.findall(".//PubmedArticle"):
                pmid_el = article.find(".//PMID")
                if pmid_el is None or not pmid_el.text:
                    continue
                pmid = pmid_el.text.strip()
                title_el = article.find(".//ArticleTitle")
                title = (
                    "".join(title_el.itertext()).strip()
                    if title_el is not None
                    else f"PubMed {pmid}"
                )
                authors: list[dict[str, str]] = []
                for au in article.findall(".//Author"):
                    authors.append(_parse_author(au))
                year_el = article.find(".//PubDate/Year")
                out[pmid] = {
                    "pmid": pmid,
                    "title": title,
                    "authors": authors,
                    "publication_date": year_el.text.strip() if year_el is not None and year_el.text else "",
                    "url": f"https://pubmed.ncbi.nlm.nih.gov/{pmid}/",
                }
    return out


def _lead_author_display(authors: list[dict[str, str]]) -> str:
    if not authors:
        return ""
    lead = authors[0]
    if lead.get("collective"):
        return lead["collective"]
    parts = [lead.get("first", ""), lead.get("last", "")]
    return " ".join(p for p in parts if p).strip()


def _inventor_on_paper(authors: list[dict[str, str]], inventor_surnames: set[str]) -> set[str]:
    matched: set[str] = set()
    for author in authors:
        surname = normalize_surname(author.get("last", ""))
        if surname in inventor_surnames:
            matched.add(surname)
    return matched


def classify_ri_lead_pub(
    pub: dict[str, Any],
    *,
    allowlist: list[str],
    inventor_surnames: set[str],
    details: dict[str, dict[str, Any]] | None = None,
) -> tuple[bool, str, str, set[str]]:
    """Return (ok, lead_author, ri_affiliation, matched_inventors)."""
    pmid = str(pub.get("pmid") or "").strip()
    detail = (details or {}).get(pmid) if pmid.isdigit() else None
    authors = (detail or pub).get("authors") or []
    if isinstance(authors, list) and authors and isinstance(authors[0], str):
        # BioMCP string authors — treat as non-RI until efetch fills detail
        authors = [{"last": a.split()[0], "first": " ".join(a.split()[1:]), "affiliation": ""} for a in authors]

    if detail and detail.get("authors"):
        authors = detail["authors"]

    if not authors:
        abstract = str(pub.get("abstract_snippet") or "")
        aff = match_ri_affiliation(abstract, allowlist)
        if aff:
            inv = set()
            for surname in inventor_surnames:
                if re.search(rf"\b{re.escape(surname)}\b", abstract, re.I):
                    inv.add(surname)
            if inv:
                return True, "See abstract", aff, inv
        return False, "", "", set()

    lead = authors[0]
    lead_name = _lead_author_display(authors)
    aff_text = lead.get("affiliation", "")
    ri_aff = match_ri_affiliation(aff_text, allowlist)
    if not ri_aff:
        return False, lead_name, "", _inventor_on_paper(authors, inventor_surnames)

    matched = _inventor_on_paper(authors, inventor_surnames)
    return True, lead_name, ri_aff, matched


def _inventor_initials_query(surname: str, ip_rows: list[dict[str, str]]) -> str:
    """Build PubMed author token from Lens inventor line (LAST FIRST M)."""
    for row in ip_rows:
        for segment in re.split(r";;|\|", row.get("inventors") or ""):
            parts = segment.strip().split()
            if not parts:
                continue
            if normalize_surname(parts[0]) != normalize_surname(surname):
                continue
            initials = "".join(p[0] for p in parts[1:3] if p)
            if initials:
                return f"{parts[0].title()} {initials.upper()}"
            return parts[0].title()
    return surname.title()


def supplemental_ri_author_search_terms(
    ip_rows: list[dict[str, str]],
    row: dict[str, str] | None = None,
    *,
    max_inventors: int = 3,
) -> list[str]:
    surnames = sorted(parse_inventor_surnames(ip_rows))[:max_inventors]
    if not surnames and row:
        lead = (row.get("physician_lead_name") or "").strip()
        if lead:
            parts = lead.split()
            if parts:
                surnames = [normalize_surname(parts[-1])]
    terms: list[str] = []
    for surname in surnames:
        author = _inventor_initials_query(surname, ip_rows) if ip_rows else surname.title()
        terms.append(f"{author}[Author] AND ({RI_AFFILIATION_QUERY})")
    return terms


def search_pubmed_articles(term: str, *, limit: int = 8) -> list[dict[str, Any]]:
    """Direct PubMed esearch — reliable for inventor[Author] AND affiliation queries."""
    try:
        with httpx.Client(timeout=45.0) as client:
            _ncbi_throttle()
            resp = client.get(
                ESEARCH_URL,
                params=_ncbi_params(
                    {"db": "pubmed", "term": term, "retmax": str(limit), "retmode": "json", "sort": "relevance"}
                ),
            )
            if resp.status_code == 429:
                time.sleep(2.0)
                _ncbi_throttle()
                resp = client.get(
                    ESEARCH_URL,
                    params=_ncbi_params(
                        {"db": "pubmed", "term": term, "retmax": str(limit), "retmode": "json", "sort": "relevance"}
                    ),
                )
            resp.raise_for_status()
            idlist = resp.json().get("esearchresult", {}).get("idlist", [])
    except Exception:
        return []
    if not idlist:
        return []
    details = fetch_pubmed_details(idlist)
    pubs: list[dict[str, Any]] = []
    for pmid in idlist:
        detail = details.get(pmid)
        if not detail:
            continue
        pubs.append(
            {
                "pmid": pmid,
                "title": detail.get("title") or f"PubMed {pmid}",
                "url": detail.get("url") or f"https://pubmed.ncbi.nlm.nih.gov/{pmid}/",
                "authors": detail.get("authors") or [],
                "publication_date": detail.get("publication_date") or "",
                "search_term": term,
                "source": "pubmed_ri_author_search",
            }
        )
    return pubs


def search_biomcp_articles(term: str, *, limit: int = 8) -> list[dict[str, Any]]:
    payload, err = run_biomcp_search("article", term, limit=limit, offset=0)
    if err or not payload:
        return []
    pubs: list[dict[str, Any]] = []
    for rec in extract_records(payload):
        pmid = str(rec.get("pmid") or rec.get("id") or "").strip()
        title = str(rec.get("title") or rec.get("name") or "").strip()
        if not title and not pmid:
            continue
        pubs.append(
            {
                "pmid": pmid if pmid.isdigit() else None,
                "title": title or (f"PubMed {pmid}" if pmid else ""),
                "url": rec.get("url")
                or (f"https://pubmed.ncbi.nlm.nih.gov/{pmid}/" if pmid.isdigit() else ""),
                "authors": rec.get("authors") or [],
                "abstract_snippet": str(rec.get("abstract") or rec.get("summary") or "")[:400],
                "search_term": term,
                "source": "biomcp_ri_author_search",
            }
        )
    return pubs


def collect_candidate_publications(
    row: dict[str, str],
    ip_rows: list[dict[str, str]],
    evidence: dict[str, Any] | None,
    *,
    supplemental: bool = True,
) -> tuple[list[dict[str, Any]], list[dict[str, Any]]]:
    """Return (evidence-linked candidates, supplemental RI-author candidates)."""
    profile = build_literature_profile(row, ip_rows)
    evidence_candidates: list[dict[str, Any]] = []
    supplemental_candidates: list[dict[str, Any]] = []
    seen: set[str] = set()

    def add(target: list[dict[str, Any]], pub: dict[str, Any]) -> None:
        key = str(pub.get("pmid") or pub.get("title") or "").lower()
        if not key or key in seen:
            return
        seen.add(key)
        target.append(pub)

    for pub in (evidence or {}).get("publications") or []:
        add(evidence_candidates, dict(pub))

    linked: list[dict[str, Any]] = []
    for pub in evidence_candidates:
        ok, link = patent_link_for_publication(pub, profile)
        if ok:
            pub = dict(pub)
            pub["patent_link"] = link
            linked.append(pub)

    ranked, _ = rank_and_filter_publications(
        linked,
        profile,
        min_score=0.15,
        min_science_overlap=0.05,
        limit=MAX_TIER_A_PUBS * 2,
        patent_linked_only=True,
    )

    if supplemental and (ip_rows or row):
        for term in supplemental_ri_author_search_terms(ip_rows, row):
            for pub in search_pubmed_articles(term, limit=MAX_TIER_A_PUBS):
                add(supplemental_candidates, pub)

    return ranked, supplemental_candidates


def merge_publication_candidates(
    evidence_linked: list[dict[str, Any]],
    supplemental: list[dict[str, Any]],
) -> list[dict[str, Any]]:
    out: list[dict[str, Any]] = []
    seen: set[str] = set()
    for pub in [*supplemental, *evidence_linked]:
        key = str(pub.get("pmid") or pub.get("title") or "").lower()
        if not key or key in seen:
            continue
        seen.add(key)
        out.append(pub)
    return out


def split_ri_lead_publications(
    publications: list[dict[str, Any]],
    *,
    allowlist: list[str],
    inventor_surnames: set[str],
) -> tuple[list[dict[str, Any]], list[dict[str, Any]]]:
    pmids = [str(p.get("pmid") or "") for p in publications if str(p.get("pmid") or "").isdigit()]
    details = fetch_pubmed_details(pmids)

    promoted: list[tuple[int, dict[str, Any], str, str]] = []
    suggested: list[dict[str, Any]] = []

    for pub in publications:
        pmid = str(pub.get("pmid") or "")
        if pmid.isdigit() and pmid not in details and pub.get("authors"):
            details[pmid] = {
                "pmid": pmid,
                "title": pub.get("title"),
                "authors": pub.get("authors"),
                "url": pub.get("url"),
            }
        ok, lead, ri_aff, matched = classify_ri_lead_pub(
            pub,
            allowlist=allowlist,
            inventor_surnames=inventor_surnames,
            details=details,
        )
        if pmid.isdigit() and pmid in details:
            pub = dict(pub)
            pub["title"] = details[pmid].get("title") or pub.get("title")
            pub["authors"] = details[pmid].get("authors") or pub.get("authors")

        if ok:
            score = len(matched) * 10 + (5 if lead and lead != "See abstract" else 0)
            if pub.get("source") == "pubmed_ri_author_search":
                score += 3
            pub = dict(pub)
            pub["ri_lead_author"] = lead
            pub["ri_affiliation"] = ri_aff
            promoted.append((score, pub, lead, ri_aff))
        else:
            suggested.append(pub)

    promoted.sort(key=lambda item: item[0], reverse=True)
    main = [p for _, p, _, _ in promoted[:MAX_TIER_A_PUBS]]
    return main, suggested


def _write_publication_columns(
    row: dict[str, str],
    main: list[dict[str, Any]],
    suggested: list[dict[str, Any]],
    narrative: str,
) -> None:
    if main:
        row["publication_count"] = str(len(main))
        row["publication_titles"] = "\n".join((p.get("title") or "").strip() for p in main)
        row["publication_lead_authors"] = "\n".join(
            (p.get("ri_lead_author") or _lead_author_display(p.get("authors") or [])).strip()
            for p in main
        )
        row["publication_ri_affiliations"] = "\n".join((p.get("ri_affiliation") or "").strip() for p in main)
        row["publication_urls"] = "\n".join(
            (p.get("url") or f"https://pubmed.ncbi.nlm.nih.gov/{p.get('pmid')}/").strip()
            for p in main
        )
        row["publication_pmids"] = "\n".join(str(p.get("pmid") or "") for p in main)
        row["literature_narrative"] = narrative

    if suggested:
        st: list[str] = []
        su: list[str] = []
        sn: list[str] = []
        for pub in suggested[:8]:
            title = (pub.get("title") or "").strip()
            if not title:
                continue
            pmid = str(pub.get("pmid") or "")
            url = pub.get("url") or (f"https://pubmed.ncbi.nlm.nih.gov/{pmid}/" if pmid.isdigit() else "")
            inv = (pub.get("patent_link") or {}).get("matched_inventor_surnames") or []
            note = "BioMCP patent-linked; not RI lead author"
            if inv:
                note += f"; inventors: {', '.join(inv)}"
            st.append(title)
            su.append(url)
            sn.append(note)
        row["suggest_publication_titles"] = "\n".join(st)
        row["suggest_publication_urls"] = "\n".join(su)
        row["suggest_publication_notes"] = "\n".join(sn)


def apply_to_row(
    row: dict[str, str],
    evidence: dict[str, Any] | None,
    ip_rows: list[dict[str, str]],
    *,
    allowlist: list[str],
    overwrite: bool = False,
    supplemental: bool = True,
) -> bool:
    if (row.get("review_status") or "").lower() == "approved" and not overwrite:
        return False
    if (row.get("catalog_tier") or "").upper() != "A":
        return False
    if not _bool(row.get("catalog_include", "true")):
        return False
    if not overwrite and _split_lines(row.get("publication_titles", "")):
        return False

    profile = build_literature_profile(row, ip_rows)
    inventor_surnames = profile.get("inventor_surnames") or set()
    evidence_linked, supplemental = collect_candidate_publications(
        row, ip_rows, evidence, supplemental=supplemental
    )
    candidates = merge_publication_candidates(evidence_linked, supplemental)
    main, suggested = split_ri_lead_publications(
        candidates,
        allowlist=allowlist,
        inventor_surnames=inventor_surnames,
    )
    # Patent-linked evidence that failed RI lead check — keep in suggest alongside others
    suggested_keys = {str(p.get("pmid") or p.get("title") or "").lower() for p in suggested}
    for pub in evidence_linked:
        key = str(pub.get("pmid") or pub.get("title") or "").lower()
        if key and key not in suggested_keys and key not in {
            str(p.get("pmid") or p.get("title") or "").lower() for p in main
        }:
            suggested.append(pub)
            suggested_keys.add(key)

    narrative = (evidence or {}).get("literature_narrative") or ""
    if main:
        narrative = (
            f"{len(main)} RI lead-author publication(s) via BioMCP/PubMed "
            f"(inventors: {', '.join(sorted(inventor_surnames)) or 'n/a'})."
        )
    elif candidates:
        narrative = (
            f"BioMCP found {len(candidates)} patent-linked candidate(s); "
            "none passed RI lead-author check — see suggest_publication_*."
        )

    _write_publication_columns(row, main, suggested, narrative)
    row["enrichment_status"] = "biomcp_publications_applied"
    return True


def apply_publications(
    *,
    path: Path = CASES_CSV,
    tier: str | None = "A",
    overwrite: bool = False,
    supplemental: bool = True,
    refresh_evidence: bool = False,
) -> tuple[int, int]:
    import json

    _load_env_file()
    rows = load_cases(path)
    ip_by = _load_ip_by_case()
    allowlist = load_allowlist()

    evidence_by: dict[str, Any] = {}
    if EVIDENCE_PATH.exists():
        evidence_by = json.loads(EVIDENCE_PATH.read_text(encoding="utf-8")).get("by_case_id") or {}

    touched = 0
    for row in rows:
        if tier and (row.get("catalog_tier") or "").upper() != tier.upper():
            continue
        if not _bool(row.get("catalog_include", "true")):
            continue

        cid = row["case_id"]
        ip_rows = ip_by.get(cid, [])

        if refresh_evidence:
            evidence = fetch_evidence_for_case(row, ip_rows)
            evidence_by[cid] = evidence
        else:
            evidence = evidence_by.get(cid)

        if apply_to_row(
            row,
            evidence,
            ip_rows,
            allowlist=allowlist,
            overwrite=overwrite,
            supplemental=supplemental,
        ):
            touched += 1

    if refresh_evidence:
        payload = json.loads(EVIDENCE_PATH.read_text(encoding="utf-8")) if EVIDENCE_PATH.exists() else {}
        payload["by_case_id"] = evidence_by
        EVIDENCE_PATH.write_text(json.dumps(payload, indent=2), encoding="utf-8")

    write_cases(rows, path)
    return len(rows), touched


def _load_env_file() -> None:
    env_path = ROOT / ".env"
    if not env_path.exists():
        return
    for line in env_path.read_text(encoding="utf-8").splitlines():
        line = line.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        key, value = line.split("=", 1)
        os.environ.setdefault(key.strip(), value.strip())


def main() -> None:
    import argparse

    _load_env_file()
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--path", type=Path, default=CASES_CSV)
    parser.add_argument("--tier", default="A", help="Catalog tier to update (default A)")
    parser.add_argument("--overwrite", action="store_true", help="Replace existing publication columns")
    parser.add_argument(
        "--no-supplemental",
        action="store_true",
        help="Skip inventor+RI PubMed searches beyond evidence JSON",
    )
    parser.add_argument(
        "--refresh-evidence",
        action="store_true",
        help="Re-run BioMCP fetch per row before apply (slow)",
    )
    args = parser.parse_args()
    total, touched = apply_publications(
        path=args.path,
        tier=args.tier or None,
        overwrite=args.overwrite,
        supplemental=not args.no_supplemental,
        refresh_evidence=args.refresh_evidence,
    )
    print(f"Applied BioMCP publications on {touched} rows -> {args.path} ({total} total)")


if __name__ == "__main__":
    main()
