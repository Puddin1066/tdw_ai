"""Patent-linked literature relevance for RI BioMCP enrichment."""

from __future__ import annotations

import re
from typing import Any

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
    "method",
    "methods",
    "composition",
    "compositions",
    "system",
    "systems",
    "using",
    "use",
    "thereof",
    "related",
    "treatment",
    "treating",
}


def normalize_surname(value: str) -> str:
    token = re.sub(r"[^A-Za-z-]", "", (value or "").strip()).upper()
    if token.startswith("MC") and len(token) > 2:
        return token[:2] + token[2:].capitalize() if len(token) > 2 else token
    return token


def parse_inventor_surnames(ip_rows: list[dict[str, str]]) -> set[str]:
    """Lens inventors field: LAST FIRST MIDDLE;;LAST2 FIRST2."""
    surnames: set[str] = set()
    for row in ip_rows:
        block = (row.get("inventors") or "").strip()
        if not block:
            continue
        for segment in re.split(r";;+", block):
            segment = segment.strip()
            if not segment:
                continue
            parts = segment.split()
            if parts:
                surname = normalize_surname(parts[0])
                if len(surname) >= 2:
                    surnames.add(surname)
    return surnames


def parse_author_surnames(authors: list[Any]) -> set[str]:
    surnames: set[str] = set()
    for author in authors:
        if isinstance(author, dict):
            last = author.get("lastname") or author.get("last_name") or author.get("family")
            if last:
                surnames.add(normalize_surname(str(last)))
                continue
            name = str(author.get("name") or author.get("full_name") or "")
        else:
            name = str(author)
        name = name.strip()
        if not name:
            continue
        if "," in name:
            surnames.add(normalize_surname(name.split(",", 1)[0]))
        else:
            parts = name.split()
            if parts:
                surnames.add(normalize_surname(parts[0]))
    return surnames


def _tokenize(text: str) -> set[str]:
    tokens = re.findall(r"[A-Za-z][A-Za-z0-9-]{2,}", (text or "").lower())
    return {t for t in tokens if t not in STOPWORDS and len(t) > 2}


def build_literature_profile(
    row: dict[str, str],
    ip_rows: list[dict[str, str]],
) -> dict[str, Any]:
    primary = ip_rows[0] if ip_rows else {}
    patent_text_parts = [
        primary.get("title", ""),
        primary.get("display_key", ""),
        (row.get("title_clean") or ""),
        (row.get("indication") or ""),
    ]
    for ip in ip_rows[:2]:
        patent_text_parts.append(ip.get("title", ""))
        patent_text_parts.append((ip.get("cpc_classifications") or "").replace(";;", " "))

    patent_text = " ".join(patent_text_parts)
    inventor_surnames = parse_inventor_surnames(ip_rows)
    return {
        "case_id": row.get("case_id", ""),
        "primary_lens_id": primary.get("lens_id", ""),
        "primary_display_key": primary.get("display_key", ""),
        "patent_tokens": _tokenize(patent_text),
        "inventor_surnames": inventor_surnames,
        "requires_inventor_match": bool(inventor_surnames),
        "program_only": not ip_rows,
    }


def merge_search_terms(
    row: dict[str, str],
    ip_rows: list[dict[str, str]],
    base_terms: list[str],
) -> list[str]:
    """Prefer inventor-anchored and primary-patent-title queries."""
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

    surnames = sorted(parse_inventor_surnames(ip_rows))
    primary_title = (ip_rows[0].get("title") if ip_rows else "") or ""
    patent_kw = " ".join(sorted(_tokenize(primary_title))[:6])

    for surname in surnames[:4]:
        if patent_kw:
            add(f"{surname} {patent_kw}")
        add(f"{surname} Rhode Island")
        add(f"{surname}[Author]")

    if primary_title:
        add(primary_title[:100])
        kw = " ".join(sorted(_tokenize(primary_title))[:8])
        if kw:
            add(kw)

    for term in base_terms:
        add(term)

    return terms[:6]


def science_overlap_score(pub: dict[str, Any], profile: dict[str, Any]) -> float:
    patent_tokens = profile.get("patent_tokens") or set()
    if not patent_tokens:
        return 1.0
    pub_text = " ".join(
        [
            str(pub.get("title") or ""),
            str(pub.get("abstract_snippet") or ""),
            str(pub.get("journal") or ""),
        ]
    )
    pub_tokens = _tokenize(pub_text)
    if not pub_tokens:
        return 0.0
    overlap = patent_tokens & pub_tokens
    if not overlap:
        return 0.0
    return len(overlap) / max(1, min(len(patent_tokens), 12))


def inventor_overlap(pub: dict[str, Any], profile: dict[str, Any]) -> set[str]:
    required = profile.get("inventor_surnames") or set()
    if not required:
        return set()
    author_surnames = parse_author_surnames(pub.get("authors") or [])
    abstract = str(pub.get("abstract_snippet") or "")
    # Fallback: surname mentioned in abstract (e.g. "Monaghan et al.")
    for surname in required:
        if surname in author_surnames:
            continue
        if re.search(rf"\b{re.escape(surname)}\b", abstract, re.IGNORECASE):
            author_surnames.add(surname)
    return required & author_surnames


def patent_link_for_publication(
    pub: dict[str, Any],
    profile: dict[str, Any],
    *,
    min_science_overlap: float = 0.08,
) -> tuple[bool, dict[str, Any]]:
    program_only = profile.get("program_only")
    matched = inventor_overlap(pub, profile)
    science = science_overlap_score(pub, profile)
    requires_inventor = profile.get("requires_inventor_match") and not program_only

    link = {
        "primary_lens_id": profile.get("primary_lens_id", ""),
        "primary_display_key": profile.get("primary_display_key", ""),
        "matched_inventor_surnames": sorted(matched),
        "science_overlap_score": round(science, 3),
        "link_basis": [],
    }

    if program_only:
        if science >= min_science_overlap or not profile.get("patent_tokens"):
            link["link_basis"].append("program_topic_match")
            return True, link
        return False, link

    if requires_inventor and not matched:
        return False, link
    if science < min_science_overlap:
        return False, link

    if matched:
        link["link_basis"].append("inventor_match")
    if science >= min_science_overlap:
        link["link_basis"].append("science_overlap")
    return True, link


def rank_and_filter_publications(
    publications: list[dict[str, Any]],
    profile: dict[str, Any],
    *,
    min_score: float = 0.28,
    min_science_overlap: float = 0.08,
    limit: int = 6,
    patent_linked_only: bool = True,
) -> tuple[list[dict[str, Any]], dict[str, int]]:
    """Rank by patent link strength; optionally drop non-linked pubs."""
    stats = {
        "candidates": len(publications),
        "kept": 0,
        "rejected_no_inventor": 0,
        "rejected_low_science": 0,
        "rejected_unlinked": 0,
    }
    scored: list[tuple[float, dict[str, Any]]] = []

    for pub in publications:
        ok, link = patent_link_for_publication(
            pub, profile, min_science_overlap=min_science_overlap
        )
        if not ok:
            if profile.get("requires_inventor_match") and not link.get("matched_inventor_surnames"):
                stats["rejected_no_inventor"] += 1
            elif link.get("science_overlap_score", 0) < min_science_overlap:
                stats["rejected_low_science"] += 1
            else:
                stats["rejected_unlinked"] += 1
            if patent_linked_only:
                continue

        matched = link.get("matched_inventor_surnames") or []
        science = float(link.get("science_overlap_score") or 0)
        score = science + (0.45 if matched else 0.0) + (0.1 if pub.get("pmid") else 0.0)
        if score < min_score and patent_linked_only:
            stats["rejected_unlinked"] += 1
            continue

        pub = dict(pub)
        pub["patent_link"] = link
        scored.append((score, pub))

    scored.sort(key=lambda item: item[0], reverse=True)
    out = [pub for _, pub in scored[:limit]]
    stats["kept"] = len(out)
    return out, stats


def build_inventor_case_index(
    ip_by_case: dict[str, list[dict[str, str]]],
) -> dict[str, set[str]]:
    surname_to_cases: dict[str, set[str]] = {}
    for case_id, rows in ip_by_case.items():
        for surname in parse_inventor_surnames(rows):
            surname_to_cases.setdefault(surname, set()).add(case_id)
    return surname_to_cases


def related_cases_for_profile(
    profile: dict[str, Any],
    case_id: str,
    surname_to_cases: dict[str, set[str]],
) -> list[str]:
    related: set[str] = set()
    for surname in profile.get("inventor_surnames") or set():
        related |= surname_to_cases.get(surname, set())
    related.discard(case_id)
    return sorted(related)
