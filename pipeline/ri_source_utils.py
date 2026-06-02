"""Helpers for cited enrichment — primary URLs paired with field values."""

from __future__ import annotations

import re

from pipeline.tier_a.comp_link_resolve import _is_discovery_url

MOCK_MARKERS = ("MOCK/SYNTHETIC", "mock/synthetic", "see web_search_queries")

# Not acceptable as value_source_url (search UIs, not primary documents).
WEAK_CITATION_HOSTS = (
    "sec.gov/edgar/search",
    "google.com/search",
    "bing.com/search",
    "duckduckgo.com",
)


def is_mock_text(value: str | None) -> bool:
    text = (value or "").strip()
    if not text:
        return False
    return any(marker in text for marker in MOCK_MARKERS)


def is_weak_citation_url(url: str | None) -> bool:
    lower = (url or "").strip().lower()
    if not lower.startswith("http"):
        return True
    if _is_discovery_url(lower):
        return True
    return any(host in lower for host in WEAK_CITATION_HOSTS)


def is_primary_citation_url(url: str | None) -> bool:
    return bool((url or "").strip().startswith("http")) and not is_weak_citation_url(url)


def format_citation(label: str, url: str) -> str:
    return f"{label.strip()} | {url.strip()}"


def split_lines(value: str) -> list[str]:
    return [x.strip() for x in (value or "").replace("\r", "").split("\n") if x.strip()]


def parse_citations(value: str) -> list[tuple[str, str]]:
    out: list[tuple[str, str]] = []
    for line in split_lines(value):
        if " | " not in line:
            continue
        label, url = line.split(" | ", 1)
        label, url = label.strip(), url.strip()
        if label and url.startswith("http"):
            out.append((label, url))
    return out


def append_citation(value: str, label: str, url: str) -> str:
    if not is_primary_citation_url(url):
        return value
    line = format_citation(label, url)
    existing = split_lines(value)
    if line in existing:
        return value
    return f"{value}\n{line}".strip() if value.strip() else line


def best_comp_financing_url(row: dict[str, str], prefix: str) -> tuple[str, str] | None:
    """Pick strongest financing URL for a comp slot."""
    vsrc = (row.get(f"{prefix}value_source_url") or "").strip()
    if is_primary_citation_url(vsrc):
        return "Financing / market source", vsrc
    purl = (row.get(f"{prefix}url") or "").strip()
    if is_primary_citation_url(purl):
        return "Company / program page", purl
    for label, url in parse_citations(row.get(f"{prefix}supporting_citations", "")):
        if is_primary_citation_url(url):
            return label, url
    return None


def ensure_comp_sources(row: dict[str, str], prefix: str) -> list[str]:
    """Ensure comp slot has value_source_url + supporting_citations when name is set."""
    changes: list[str] = []
    name = (row.get(f"{prefix}name") or "").strip()
    if not name:
        return changes

    hit = best_comp_financing_url(row, prefix)
    if hit and not (row.get(f"{prefix}value_source_url") or "").strip():
        row[f"{prefix}value_source_url"] = hit[1]
        if not (row.get(f"{prefix}validation_status") or "").strip():
            row[f"{prefix}validation_status"] = "suggested"
        changes.append(f"{prefix}value_source_url")

    vsrc = (row.get(f"{prefix}value_source_url") or "").strip()
    if vsrc and is_weak_citation_url(vsrc):
        row[f"{prefix}value_source_url"] = ""
        changes.append(f"{prefix}value_source_url_cleared")

    purl = (row.get(f"{prefix}url") or "").strip()
    citations = row.get(f"{prefix}supporting_citations") or ""
    if purl and is_primary_citation_url(purl):
        updated = append_citation(citations, "Program page", purl)
        if updated != citations:
            row[f"{prefix}supporting_citations"] = updated
            changes.append(f"{prefix}supporting_citations")
    if vsrc and is_primary_citation_url(vsrc) and vsrc != purl:
        updated = append_citation(row.get(f"{prefix}supporting_citations", ""), "Financing source", vsrc)
        if updated != row.get(f"{prefix}supporting_citations", ""):
            row[f"{prefix}supporting_citations"] = updated
            changes.append(f"{prefix}supporting_citations")

    return changes


def promote_urls_from_web_search_notes(row: dict[str, str]) -> list[str]:
    """Move resolved http URLs from web_search_notes into structured comp columns."""
    changes: list[str] = []
    notes = row.get("web_search_notes") or ""
    if not notes.strip():
        return changes

    tag_re = re.compile(
        r"^\[(comp(\d)|agent_comp(\d))(?:_url|_heuristic)?\]\s*(.+?)\s*\|\s*(https?://\S+)\s*$",
        re.IGNORECASE,
    )
    for line in split_lines(notes):
        match = tag_re.match(line)
        if not match:
            continue
        slot = match.group(2) or match.group(3)
        if not slot:
            continue
        label = match.group(4).strip()
        url = match.group(5).strip()
        if not is_primary_citation_url(url):
            continue
        prefix = f"comp{slot}_"
        if not (row.get(f"{prefix}name") or "").strip():
            continue
        if not (row.get(f"{prefix}value_source_url") or "").strip():
            row[f"{prefix}value_source_url"] = url
            if not (row.get(f"{prefix}validation_status") or "").strip():
                row[f"{prefix}validation_status"] = "suggested"
            changes.append(f"{prefix}value_source_url")
        updated = append_citation(row.get(f"{prefix}supporting_citations", ""), label[:80], url)
        if updated != (row.get(f"{prefix}supporting_citations") or ""):
            row[f"{prefix}supporting_citations"] = updated
            changes.append(f"{prefix}supporting_citations")

    return changes


def strip_mock_main_columns(row: dict[str, str]) -> list[str]:
    """Remove MOCK/SYNTHETIC placeholders from investor-facing main columns."""
    changes: list[str] = []
    for field in (
        "rd_milestones",
        "rd_plan_summary",
        "literature_narrative",
        "investment_thesis",
    ):
        if is_mock_text(row.get(field)):
            row[field] = ""
            changes.append(f"cleared_mock_{field}")
    return changes


def sync_literature_sources(row: dict[str, str]) -> bool:
    """Build literature_source_urls from publication_urls and narrative context."""
    titles = split_lines(row.get("publication_titles", ""))
    urls = split_lines(row.get("publication_urls", ""))
    lines: list[str] = []
    for i, url in enumerate(urls):
        if not is_primary_citation_url(url):
            continue
        label = titles[i][:80] if i < len(titles) else "Publication"
        lines.append(format_citation(label, url))
    suggest_urls = split_lines(row.get("suggest_publication_urls", ""))
    suggest_titles = split_lines(row.get("suggest_publication_titles", ""))
    for i, url in enumerate(suggest_urls[:4]):
        if not is_primary_citation_url(url):
            continue
        label = suggest_titles[i][:80] if i < len(suggest_titles) else "Suggested publication"
        line = format_citation(f"Suggest: {label}", url)
        if line not in lines:
            lines.append(line)
    patent = (row.get("primary_patent_url") or "").strip()
    if is_primary_citation_url(patent):
        title = (row.get("primary_patent_title") or "Primary patent")[:80]
        line = format_citation(f"Patent: {title}", patent)
        if line not in lines:
            lines.append(line)
    if not lines:
        return False
    row["literature_source_urls"] = "\n".join(lines)
    return True


def sync_rd_milestone_sources(row: dict[str, str]) -> bool:
    """Pair rd_milestones lines with URLs from web_search_notes [rd_milestone] hits."""
    milestones = split_lines(row.get("rd_milestones", ""))
    if not milestones:
        return False
    rd_hits: list[tuple[str, str]] = []
    for line in split_lines(row.get("web_search_notes", "")):
        if not line.lower().startswith("[rd_milestone]"):
            continue
        if " | " not in line:
            continue
        body = line.split("]", 1)[-1].strip()
        label, url = body.rsplit(" | ", 1)
        if is_primary_citation_url(url.strip()):
            rd_hits.append((label.strip(), url.strip()))
    lines: list[str] = []
    for i, milestone in enumerate(milestones):
        if i < len(rd_hits):
            lines.append(format_citation(milestone[:80], rd_hits[i][1]))
        elif is_primary_citation_url(row.get("primary_patent_url", "")):
            lines.append(format_citation(milestone[:80], row["primary_patent_url"].strip()))
        elif (row.get("comp1_value_source_url") or "").strip():
            lines.append(format_citation(milestone[:80], row["comp1_value_source_url"].strip()))
    if lines:
        row["rd_milestone_source_urls"] = "\n".join(lines)
        return True
    return False


def sync_rd_plan_source(row: dict[str, str]) -> bool:
    if not (row.get("rd_plan_summary") or "").strip():
        return False
    for line in split_lines(row.get("web_search_notes", "")):
        if line.lower().startswith("[rd]") and " | " in line:
            _, body = line.split("]", 1)
            label, url = body.strip().rsplit(" | ", 1)
            if is_primary_citation_url(url.strip()):
                row["rd_plan_source_url"] = url.strip()
                return True
    if is_primary_citation_url(row.get("primary_patent_url", "")):
        row["rd_plan_source_url"] = row["primary_patent_url"].strip()
        return True
    return False


def finish_row_sources(row: dict[str, str], *, comp_prefixes: tuple[str, ...]) -> list[str]:
    """Apply source-linking and mock cleanup after web enrichment."""
    from datetime import date

    changes: list[str] = []
    changes.extend(strip_mock_main_columns(row))
    changes.extend(promote_urls_from_web_search_notes(row))
    for prefix in comp_prefixes:
        changes.extend(ensure_comp_sources(row, prefix))
    if sync_literature_sources(row):
        changes.append("literature_source_urls")
    if sync_rd_milestone_sources(row):
        changes.append("rd_milestone_source_urls")
    if sync_rd_plan_source(row):
        changes.append("rd_plan_source_url")
    if changes:
        row["last_refreshed_at"] = date.today().isoformat()
        row["enrichment_status"] = "sourced_enriched"
    return changes
