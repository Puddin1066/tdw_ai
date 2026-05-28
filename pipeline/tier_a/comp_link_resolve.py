"""Resolve comparable financing citations to primary-source URLs (not search pages)."""

from __future__ import annotations

import csv
import re
import time
import urllib.parse
from pathlib import Path

import httpx

from pipeline.tier_a.comp_financing import resolve_financing_queries
from pipeline.tier_a.paths import TIER_A_ROOT

LINK_CACHE_CSV = TIER_A_ROOT / "comp_review_link_cache.csv"
CACHE_FIELDS = ["case_id", "precedent_rank", "label", "url", "resolved_at", "resolver"]

USER_AGENT = (
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) "
    "AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
)
FETCH_TIMEOUT_S = 15.0
MAX_CANDIDATES = 4
FETCH_DELAY_S = 0.75

# Hosts we treat as acceptable financing / market citations.
PRIMARY_HOST_HINTS = (
    "sec.gov",
    "prnewswire.com",
    "businesswire.com",
    "globenewswire.com",
    "accesswire.com",
    "crunchbase.com",
    "techcrunch.com",
    "fiercebiotech.com",
    "biopharmadive.com",
    "statnews.com",
    "reuters.com",
    "endpoints.news",
    "finance.yahoo.com",
    "stockanalysis.com",
    "macrotrends.net",
    "pitchbook.com",
    "bloomberg.com",
    "marketwatch.com",
    "nasdaq.com",
    "investors.",
    "/investor",
    "/ir/",
    "newsroom.",
)

# Deprioritize bare market-cap pages when hunting VC staging (still allowed for public comps).
MARKET_CAP_ONLY_HOSTS = (
    "finance.yahoo.com/quote",
    "stockanalysis.com",
    "macrotrends.net",
    "google.com/finance",
)

SKIP_HOSTS = (
    "google.com",
    "bing.com",
    "duckduckgo.com",
    "facebook.com",
    "twitter.com",
    "x.com",
    "linkedin.com",
    "wikipedia.org",
    "youtube.com",
)


def _is_discovery_url(url: str) -> bool:
    lower = (url or "").strip().lower()
    return any(
        token in lower
        for token in (
            "google.com/search",
            "bing.com/search",
            "duckduckgo.com",
            "search.yahoo.com/search",
        )
    )


def url_link_label(url: str) -> str:
    """Human label for a URL already stored on the comparable row."""
    lower = url.lower()
    if "sec.gov" in lower:
        return "SEC filing (on file)"
    if "prnewswire.com" in lower or "businesswire.com" in lower or "globenewswire.com" in lower:
        return "Press release (on file)"
    if any(h in lower for h in ("finance.yahoo.com", "stockanalysis.com", "macrotrends.net", "nasdaq.com")):
        return "Market data (on file)"
    if "crunchbase.com" in lower:
        return "Crunchbase (on file)"
    return "Program / company page (on file)"


def _comp_base_name(comp_name: str) -> str:
    return comp_name.split("(")[0].strip()


def _sec_edgar_search_url(company: str) -> str:
    q = urllib.parse.quote(company)
    return f"https://www.sec.gov/edgar/search/#/q={q}"


def _heuristic_links(comp: dict[str, str]) -> list[tuple[str, str]]:
    """Direct URLs we can construct without a search engine."""
    links: list[tuple[str, str]] = []
    seen: set[str] = set()

    def add(label: str, url: str) -> None:
        url = (url or "").strip()
        if not url or _is_discovery_url(url) or url in seen:
            return
        seen.add(url)
        links.append((label, url))

    on_file = (comp.get("precedent_url") or "").strip()
    if on_file:
        add(url_link_label(on_file), on_file)
    financing = (comp.get("value_source_url") or "").strip()
    if financing:
        add("Financing source (verified)" if (comp.get("validation_status") or "").lower() == "verified"
            else "Financing source (on file)", financing)

    name = _comp_base_name(comp.get("precedent_name", ""))
    ptype = (comp.get("precedent_type") or "").lower()
    if name and ptype in {"incumbent", "public", "ri_public", "pharma_deal", "startup"}:
        add("SEC EDGAR search", _sec_edgar_search_url(name))
    return links


def _acceptable_result_url(url: str, *, title: str = "") -> bool:
    if not url.startswith("http"):
        return False
    lower = url.lower()
    title_lower = title.lower()
    if _is_discovery_url(url):
        return False
    if any(skip in lower for skip in SKIP_HOSTS):
        return False
    if not any(hint in lower for hint in PRIMARY_HOST_HINTS):
        return False
    vc_signal = any(
        token in title_lower or token in lower
        for token in (
            "series",
            "seed",
            "venture",
            "funding round",
            "raised",
            "financing",
            "investment",
            "crunchbase",
        )
    )
    market_cap_only = any(host in lower for host in MARKET_CAP_ONLY_HOSTS)
    if market_cap_only and not vc_signal:
        return False
    return True


def _duckduckgo_html_results(query: str, *, limit: int = MAX_CANDIDATES) -> list[tuple[str, str]]:
    """Return (title, url) from DuckDuckGo HTML (no API key)."""
    url = "https://html.duckduckgo.com/html/"
    try:
        with httpx.Client(
            timeout=FETCH_TIMEOUT_S,
            headers={"User-Agent": USER_AGENT},
            follow_redirects=True,
        ) as client:
            response = client.post(url, data={"q": query})
            response.raise_for_status()
            html = response.text
    except httpx.HTTPError:
        return []

    # DDG wraps redirects: //duckduckgo.com/l/?uddg=ENCODED
    pattern = re.compile(
        r'class="result__a"[^>]*href="([^"]+)"[^>]*>([^<]+)</a>',
        re.IGNORECASE,
    )
    out: list[tuple[str, str]] = []
    for href, title in pattern.findall(html):
        target = href
        if "uddg=" in href:
            parsed = urllib.parse.urlparse(href)
            qs = urllib.parse.parse_qs(parsed.query)
            if "uddg" in qs:
                target = urllib.parse.unquote(qs["uddg"][0])
        if not target.startswith("http"):
            target = "https:" + target if target.startswith("//") else href
        if not _acceptable_result_url(target, title=title):
            continue
        label = re.sub(r"\s+", " ", title).strip()[:80] or "Source"
        out.append((label, target))
        if len(out) >= limit:
            break
    return out


def fetch_resolved_links(comp: dict[str, str]) -> list[tuple[str, str]]:
    """Web-resolve primary-source candidates for one comparable."""
    found: list[tuple[str, str]] = []
    seen: set[str] = set()
    for query in resolve_financing_queries(comp):
        time.sleep(FETCH_DELAY_S)
        for title, url in _duckduckgo_html_results(query, limit=2):
            if url in seen:
                continue
            seen.add(url)
            found.append((title, url))
            if len(found) >= MAX_CANDIDATES:
                return found
    return found


def load_link_cache() -> dict[tuple[str, str], list[tuple[str, str]]]:
    if not LINK_CACHE_CSV.exists():
        return {}
    by_key: dict[tuple[str, str], list[tuple[str, str]]] = {}
    with LINK_CACHE_CSV.open(encoding="utf-8") as handle:
        for row in csv.DictReader(handle):
            key = (row["case_id"], row["precedent_rank"])
            by_key.setdefault(key, []).append((row["label"], row["url"]))
    return by_key


def write_link_cache(
    entries: dict[tuple[str, str], list[tuple[str, str]]],
    *,
    merge: bool = True,
) -> None:
    TIER_A_ROOT.mkdir(parents=True, exist_ok=True)
    if merge:
        merged = load_link_cache()
        for key, links in entries.items():
            if links:
                merged[key] = links
        entries = merged
    rows: list[dict[str, str]] = []
    from datetime import date

    today = date.today().isoformat()
    for (case_id, rank), links in sorted(entries.items()):
        if not links:
            continue
        for label, url in links:
            rows.append(
                {
                    "case_id": case_id,
                    "precedent_rank": rank,
                    "label": label,
                    "url": url,
                    "resolved_at": today,
                    "resolver": "duckduckgo_html",
                }
            )
    with LINK_CACHE_CSV.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=CACHE_FIELDS)
        writer.writeheader()
        writer.writerows(rows)


def links_for_queue_row(
    comp: dict[str, str],
    *,
    case_id: str,
    cache: dict[tuple[str, str], list[tuple[str, str]]],
    fetch: bool = False,
) -> list[tuple[str, str]]:
    """All direct links to show in the review workbook (on file + cached/fetched)."""
    links = _heuristic_links(comp)
    seen = {url for _, url in links}
    rank = comp.get("precedent_rank", "")
    key = (case_id, rank)

    resolved: list[tuple[str, str]] = []
    if fetch:
        resolved = fetch_resolved_links(comp)
        if resolved:
            cache[key] = resolved
        elif key in cache:
            resolved = cache[key]
    elif key in cache:
        resolved = cache[key]

    for label, url in resolved:
        if url in seen or _is_discovery_url(url):
            continue
        seen.add(url)
        links.append((f"Resolved: {label}", url))
    return links
