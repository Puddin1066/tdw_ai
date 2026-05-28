"""Resolve Brown University Researchers@Brown (VIVO) profile URLs.

Canonical format: https://vivo.brown.edu/display/{slug}
Example: Seth Margolis -> https://vivo.brown.edu/display/smargoli
"""

from __future__ import annotations

import re
from functools import lru_cache
from pathlib import Path

import httpx

BROWN_VIVO_BASE = "https://vivo.brown.edu/display/"

# Curated slugs when name heuristics are ambiguous.
KNOWN_SLUGS: dict[str, str] = {
    "CAROLINA HAASS-KOFFLER": "chaassko",
    "JACK A ELIAS": "jaelias",
    "SEAN LAWLER": "slawler",
    "FREDERIKE PETZSCHNER": "fpetzsch",
    "SETH MARGOLIS": "smargoli",
    "SETH A MARGOLIS": "smargoli",
    "WAEL ASAAD": "wasaad",
    "WAEL FAROUK ASAAD": "wasaad",
    "DAVID A BORTON": "dborton",
    "G REES COSGROVE": "gcosgrov",
    "ARTO V NURMIKKO": "anurmikk",
    "ARTO NURMIKKO": "anurmikk",
}


def normalize_person_key(name: str) -> str:
    return re.sub(r"\s+", " ", (name or "").strip()).upper()


def brown_vivo_url(slug: str) -> str:
    return f"{BROWN_VIVO_BASE}{slug.strip().lower()}"


def is_brown_vivo_url(url: str) -> bool:
    return "vivo.brown.edu/display/" in (url or "").lower()


def _name_tokens(display_name: str) -> tuple[str, str]:
    parts = [p for p in re.split(r"\s+", display_name.strip()) if p]
    if not parts:
        return "", ""
    if len(parts) >= 3 and len(parts[1]) == 1:
        first = parts[0]
        last = parts[-1]
    elif len(parts) >= 2:
        first = parts[0]
        last = parts[-1]
    else:
        return parts[0], parts[0]
    first = re.sub(r"[^A-Za-z]", "", first).lower()
    last = re.sub(r"[^A-Za-z]", "", last).lower()
    return first, last


def slug_candidates(display_name: str) -> list[str]:
    """Generate likely VIVO slugs from a display name."""
    key = normalize_person_key(display_name)
    if key in KNOWN_SLUGS:
        return [KNOWN_SLUGS[key]]

    first, last = _name_tokens(display_name)
    if not first or not last:
        return []

    out: list[str] = []
    for length in (len(last), 8, 7, 6, 5):
        out.append(f"{first[0]}{last[:length]}")
    if len(first) >= 2:
        out.append(f"{first[:2]}{last[:6]}")
        out.append(f"{first[:2]}{last[:5]}")

    deduped: list[str] = []
    seen: set[str] = set()
    for slug in out:
        slug = slug.lower()
        if slug and slug not in seen:
            seen.add(slug)
            deduped.append(slug)
    return deduped


@lru_cache(maxsize=256)
def _vivo_slug_exists(slug: str) -> bool:
    try:
        with httpx.Client(timeout=12.0, follow_redirects=True) as client:
            resp = client.head(brown_vivo_url(slug))
            return resp.status_code == 200
    except Exception:
        return False


def resolve_brown_vivo_url(display_name: str, *, verify: bool = True) -> str:
    """Return VIVO profile URL for a Brown faculty member, or empty string."""
    name = (display_name or "").strip()
    if not name:
        return ""

    key = normalize_person_key(name)
    if key in KNOWN_SLUGS:
        slug = KNOWN_SLUGS[key]
        return brown_vivo_url(slug) if not verify or _vivo_slug_exists(slug) else ""

    for slug in slug_candidates(name):
        if not verify or _vivo_slug_exists(slug):
            return brown_vivo_url(slug)
    return ""


def is_brown_institution(institution: str) -> bool:
    lower = (institution or "").lower()
    return "brown university" in lower or lower.strip() == "brown"


def fill_brown_profile_url(row: dict[str, str], *, overwrite: bool = False) -> bool:
    """Set physician_lead_profile_url when lead is Brown-affiliated."""
    institution = (
        row.get("physician_lead_institution")
        or row.get("ri_institution")
        or row.get("company")
        or ""
    )
    if not is_brown_institution(institution):
        return False

    existing = (row.get("physician_lead_profile_url") or "").strip()
    if existing and is_brown_vivo_url(existing) and not overwrite:
        return False
    if existing and not overwrite:
        return False

    name = (row.get("physician_lead_name") or "").strip()
    url = resolve_brown_vivo_url(name)
    if not url:
        return False
    if url == existing:
        return False
    row["physician_lead_profile_url"] = url
    return True


def apply_brown_vivo_profiles(rows: list[dict[str, str]], *, overwrite: bool = False) -> int:
    updated = 0
    for row in rows:
        if fill_brown_profile_url(row, overwrite=overwrite):
            updated += 1
    return updated


def main() -> None:
    import argparse

    from pipeline.ri_cases_enriched_io import CASES_CSV, load_cases, write_cases

    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--path", type=Path, default=CASES_CSV)
    parser.add_argument("--overwrite", action="store_true")
    args = parser.parse_args()
    rows = load_cases(args.path)
    n = apply_brown_vivo_profiles(rows, overwrite=args.overwrite)
    write_cases(rows, args.path)
    print(f"Updated {n} Brown VIVO profile URLs -> {args.path}")


if __name__ == "__main__":
    main()
