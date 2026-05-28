"""Fetch comparator company websites and extract structured dossier signals."""

from __future__ import annotations

import re
from html.parser import HTMLParser
from typing import Any
from urllib.parse import urljoin, urlparse

import httpx

USER_AGENT = "TDW-RI-CompSiteEnrichment/1.0 (+https://tdw.ai; research enrichment)"
FETCH_TIMEOUT_S = 20.0
MAX_HTML_BYTES = 1_500_000
MAX_PAGES_PER_COMP = 5

URL_ROLE_PATTERNS: dict[str, tuple[str, ...]] = {
    "product": ("product", "technology", "platform", "solution", "therapy", "device"),
    "clinical": ("clinical", "evidence", "studies", "trial", "pipeline", "science"),
    "publications": ("publication", "resource", "library", "white-paper", "whitepaper", "peer"),
    "reimbursement": (
        "reimbursement",
        "coverage",
        "coding",
        "payer",
        "billing",
        "hcp",
        "reimburs",
        "access",
        "cpt",
    ),
    "investors": ("investor", "ir/", "/ir", "financial", "sec-filing", "stock"),
    "news": ("newsroom", "news/", "press", "media"),
}

REIMBURSEMENT_KEYWORDS = (
    "reimbursement",
    "coverage",
    "cpt",
    "drg",
    "payer",
    "medicare",
    "medicaid",
    "billing",
    "coding",
    "prior authorization",
)
KOL_KEYWORDS = (
    "advisory board",
    "key opinion leader",
    "kol",
    "thought leader",
    "leading physicians",
    "clinical advisors",
    "medical advisors",
)
CLINICAL_KEYWORDS = (
    "fda cleared",
    "fda-approved",
    "510(k)",
    "510k",
    "ce mark",
    "pivotal",
    "clinical trial",
    "ide",
    "breakthrough",
    "premarket",
)
PUBLICATION_HINTS = ("publication", "peer-reviewed", "journal", "manuscript", "white paper", "pdf")


class _LinkCollector(HTMLParser):
    def __init__(self) -> None:
        super().__init__()
        self.links: list[tuple[str, str]] = []
        self._href: str | None = None
        self._text_parts: list[str] = []

    def handle_starttag(self, tag: str, attrs: list[tuple[str, str | None]]) -> None:
        if tag != "a":
            return
        for key, value in attrs:
            if key == "href" and value:
                self._href = value.strip()
                self._text_parts = []
                return

    def handle_data(self, data: str) -> None:
        if self._href is not None:
            self._text_parts.append(data)

    def handle_endtag(self, tag: str) -> None:
        if tag == "a" and self._href is not None:
            text = re.sub(r"\s+", " ", "".join(self._text_parts)).strip()
            self.links.append((self._href, text))
            self._href = None
            self._text_parts = []


def _same_site(base: str, candidate: str) -> bool:
    try:
        b = urlparse(base)
        c = urlparse(candidate)
    except ValueError:
        return False
    if c.scheme not in {"http", "https"}:
        return False
    return (c.netloc or "").lower() in {(b.netloc or "").lower(), f"www.{(b.netloc or '').lower()}"}


def _normalize_url(base: str, href: str) -> str | None:
    href = href.split("#")[0].strip()
    if not href or href.startswith(("mailto:", "tel:", "javascript:")):
        return None
    try:
        absolute = urljoin(base, href)
        parsed = urlparse(absolute)
        if parsed.scheme not in {"http", "https"}:
            return None
        return absolute
    except ValueError:
        return None


def fetch_html(url: str, *, client: httpx.Client | None = None) -> tuple[str | None, str | None]:
    """Return (html, error_message)."""
    own = client is None
    if own:
        client = httpx.Client(
            timeout=FETCH_TIMEOUT_S,
            follow_redirects=True,
            headers={"User-Agent": USER_AGENT},
        )
    try:
        response = client.get(url)
        response.raise_for_status()
        content = response.content
        if len(content) > MAX_HTML_BYTES:
            content = content[:MAX_HTML_BYTES]
        return content.decode(response.encoding or "utf-8", errors="replace"), None
    except httpx.HTTPError as exc:
        return None, str(exc)
    finally:
        if own:
            client.close()


def extract_links(html: str, base_url: str) -> list[tuple[str, str]]:
    parser = _LinkCollector()
    try:
        parser.feed(html)
    except Exception:
        return []
    out: list[tuple[str, str]] = []
    seen: set[str] = set()
    for href, text in parser.links:
        url = _normalize_url(base_url, href)
        if not url or not _same_site(base_url, url):
            continue
        key = url.lower().rstrip("/")
        if key in seen:
            continue
        seen.add(key)
        out.append((url, text))
    return out


def discover_site_map(corporate_url: str, html: str) -> dict[str, str]:
    site_map: dict[str, str] = {"corporate": corporate_url.rstrip("/")}
    links = extract_links(html, corporate_url)
    for role, patterns in URL_ROLE_PATTERNS.items():
        if role in site_map:
            continue
        best: tuple[int, str] | None = None
        for url, anchor in links:
            blob = f"{url} {anchor}".lower()
            score = sum(1 for p in patterns if p in blob)
            if score <= 0:
                continue
            if best is None or score > best[0]:
                best = (score, url)
        if best:
            site_map[role] = best[1]
    return site_map


def html_to_text(html: str, *, max_chars: int = 12_000) -> str:
    text = re.sub(r"(?is)<script.*?>.*?</script>", " ", html)
    text = re.sub(r"(?is)<style.*?>.*?</style>", " ", text)
    text = re.sub(r"<[^>]+>", " ", text)
    text = re.sub(r"\s+", " ", text)
    return text.strip()[:max_chars]


def _sentences_with_keywords(text: str, keywords: tuple[str, ...], limit: int = 4) -> list[str]:
    hits: list[str] = []
    for chunk in re.split(r"(?<=[.!?])\s+", text):
        lower = chunk.lower()
        if any(k in lower for k in keywords) and len(chunk) > 40:
            hits.append(chunk.strip()[:400])
        if len(hits) >= limit:
            break
    return hits


def extract_publications(html: str, page_url: str, limit: int = 6) -> list[dict[str, str]]:
    pubs: list[dict[str, str]] = []
    seen: set[str] = set()
    for href, anchor in extract_links(html, page_url):
        blob = f"{href} {anchor}".lower()
        if not any(h in blob for h in PUBLICATION_HINTS) and ".pdf" not in blob:
            continue
        title = anchor or href.rsplit("/", 1)[-1]
        if len(title) < 8:
            continue
        key = title.lower()[:80]
        if key in seen:
            continue
        seen.add(key)
        pubs.append(
            {
                "title": title[:240],
                "url": href,
                "source_page": page_url,
                "source": "comp_site_link",
            }
        )
        if len(pubs) >= limit:
            break
    return pubs


def extract_dossier_from_pages(
    *,
    precedent_name: str,
    corporate_url: str,
    pages: dict[str, str],
    site_map: dict[str, str],
) -> dict[str, Any]:
    """Build dossier payload from role -> html."""
    all_text = " ".join(pages.values())
    science_pages = [
        pages[k]
        for k in ("product", "clinical", "publications", "corporate")
        if k in pages
    ]
    science_text = html_to_text(" ".join(science_pages), max_chars=8000)

    publications: list[dict[str, str]] = []
    for role in ("publications", "clinical", "product", "corporate"):
        if role in pages:
            publications.extend(extract_publications(pages[role], site_map.get(role, corporate_url)))
    # dedupe by title
    deduped: list[dict[str, str]] = []
    seen: set[str] = set()
    for pub in publications:
        key = pub["title"].lower()[:60]
        if key in seen:
            continue
        seen.add(key)
        deduped.append(pub)
    publications = deduped[:8]

    reimbursement_notes = []
    for role in ("reimbursement", "product", "hcp", "corporate"):
        if role in pages:
            url = site_map.get(role, corporate_url)
            for sent in _sentences_with_keywords(html_to_text(pages[role]), REIMBURSEMENT_KEYWORDS, 3):
                reimbursement_notes.append(
                    {"text": sent, "source_url": url, "source": "comp_site_extract"}
                )

    kol_signals = []
    for role in ("clinical", "product", "corporate", "news"):
        if role in pages:
            url = site_map.get(role, corporate_url)
            for sent in _sentences_with_keywords(html_to_text(pages[role]), KOL_KEYWORDS, 2):
                kol_signals.append({"text": sent, "source_url": url, "source": "comp_site_extract"})

    clinical_milestones = []
    for role in ("clinical", "product", "news", "corporate"):
        if role in pages:
            url = site_map.get(role, corporate_url)
            for sent in _sentences_with_keywords(html_to_text(pages[role]), CLINICAL_KEYWORDS, 3):
                clinical_milestones.append(
                    {"text": sent, "source_url": url, "source": "comp_site_extract"}
                )

    science_summary = ""
    if science_text:
        science_summary = science_text[:480] + ("…" if len(science_text) > 480 else "")

    return {
        "precedent_name": precedent_name,
        "corporate_url": corporate_url,
        "site_map": site_map,
        "science_summary": science_summary,
        "key_publications": publications,
        "clinical_milestones": clinical_milestones[:6],
        "kol_signals": kol_signals[:5],
        "reimbursement_notes": reimbursement_notes[:6],
    }


def fetch_comp_site_dossier(
    *,
    precedent_name: str,
    corporate_url: str,
    client: httpx.Client | None = None,
) -> tuple[dict[str, Any], list[str]]:
    """Fetch corporate + discovered pages; return (dossier_body, warnings)."""
    warnings: list[str] = []
    html, err = fetch_html(corporate_url, client=client)
    if err or not html:
        return (
            {
                "precedent_name": precedent_name,
                "corporate_url": corporate_url,
                "site_map": {"corporate": corporate_url},
                "science_summary": "",
                "key_publications": [],
                "clinical_milestones": [],
                "kol_signals": [],
                "reimbursement_notes": [],
            },
            [f"fetch corporate ({corporate_url}): {err or 'empty'}"],
        )

    site_map = discover_site_map(corporate_url, html)
    pages: dict[str, str] = {"corporate": html}
    fetched = 1
    for role, url in site_map.items():
        if role == "corporate" or fetched >= MAX_PAGES_PER_COMP:
            continue
        page_html, page_err = fetch_html(url, client=client)
        fetched += 1
        if page_err or not page_html:
            warnings.append(f"fetch {role} ({url}): {page_err or 'empty'}")
            continue
        pages[role] = page_html

    body = extract_dossier_from_pages(
        precedent_name=precedent_name,
        corporate_url=corporate_url,
        pages=pages,
        site_map=site_map,
    )
    return body, warnings
