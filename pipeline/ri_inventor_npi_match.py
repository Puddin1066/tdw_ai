"""Match patent inventors to CMS NPI physicians in ri_physicians.csv."""

from __future__ import annotations

import csv
import re
from functools import lru_cache
from pathlib import Path
from typing import Any

from pipeline.types import repo_root

DATA = repo_root() / "data" / "ri"
PHYSICIANS_CSV = DATA / "ri_physicians.csv"

RI_INSTITUTION_HINTS = (
    "rhode island hospital",
    "lifespan",
    "brown medicine",
    "brown university",
    "warren alpert",
    "uri",
    "university of rhode island",
    "miriam",
    "providence",
)


def _inventor_display_name(patent_name: str) -> str:
    """USPTO order LAST FIRST [MIDDLE] → readable name."""
    parts = patent_name.strip().split()
    if len(parts) < 2:
        return patent_name.title()
    last = parts[0].replace("-", " ").title()
    rest = " ".join(p.title() for p in parts[1:])
    return f"{rest} {last}".strip()


def _parse_inventor(patent_name: str) -> tuple[str, str, str]:
    """Return (surname, first_token, display_name) from USPTO inventor string."""
    parts = patent_name.strip().split()
    if not parts:
        return "", "", ""
    surname = parts[0].upper()
    first = parts[1].upper() if len(parts) > 1 else ""
    return surname, first, _inventor_display_name(patent_name)


def _normalize_name_key(name: str) -> str:
    return re.sub(r"[^A-Z]", "", (name or "").upper())


def _ri_institution_bonus(institution: str) -> int:
    inst = (institution or "").lower()
    return 15 if any(h in inst for h in RI_INSTITUTION_HINTS) else 0


@lru_cache(maxsize=1)
def _physicians_by_id() -> dict[str, dict[str, str]]:
    by_id: dict[str, dict[str, str]] = {}
    if not PHYSICIANS_CSV.exists():
        return by_id
    with PHYSICIANS_CSV.open(newline="", encoding="utf-8") as handle:
        for row in csv.DictReader(handle):
            pid = (row.get("physician_id") or "").strip().lower().replace("npi_", "")
            if pid:
                by_id[pid] = row
    return by_id


def lead_npi_name_mismatch(row: dict[str, str]) -> bool:
    """True when physician_lead_npi points to a different person than physician_lead_name."""
    npi = (row.get("physician_lead_npi") or "").strip().lower().replace("npi_", "")
    lead = (row.get("physician_lead_name") or "").upper().strip()
    if not npi or not lead:
        return False
    phy = _physicians_by_id().get(npi)
    if not phy:
        return False
    phy_name = (phy.get("name") or "").upper().strip()
    if not phy_name:
        return False
    lead_tokens = set(lead.split())
    phy_tokens = set(phy_name.split())
    if lead_tokens & phy_tokens:
        return False
    return True


@lru_cache(maxsize=1)
def _physicians_by_surname() -> dict[str, list[dict[str, str]]]:
    by_surname: dict[str, list[dict[str, str]]] = {}
    if not PHYSICIANS_CSV.exists():
        return by_surname
    with PHYSICIANS_CSV.open(newline="", encoding="utf-8") as handle:
        for row in csv.DictReader(handle):
            name = (row.get("name") or "").strip()
            if not name:
                continue
            parts = name.split()
            surname = parts[-1].upper() if parts else ""
            if not surname:
                continue
            by_surname.setdefault(surname, []).append(row)
    return by_surname


def score_inventor_physician_match(
    inventor_patent_name: str,
    physician: dict[str, str],
) -> float:
    surname, first, display = _parse_inventor(inventor_patent_name)
    if not surname:
        return 0.0
    phy_name = (physician.get("name") or "").upper()
    phy_parts = phy_name.split()
    if not phy_parts or phy_parts[-1] != surname:
        return 0.0
    score = 50.0
    if first and phy_parts[0].startswith(first[:1]):
        score += 25.0
    if display.upper() == phy_name:
        score += 15.0
    score += _ri_institution_bonus(physician.get("institution", ""))
    roles = (physician.get("roles_willing") or "").lower()
    if "investigator" in roles or "advisor" in roles:
        score += 5.0
    return score


def match_inventors_to_physicians(
    inventors: list[str],
    *,
    min_score: float = 60.0,
) -> list[dict[str, Any]]:
    """Return ranked inventor→NPI matches (best per inventor)."""
    by_surname = _physicians_by_surname()
    hits: list[dict[str, Any]] = []
    for inv in inventors:
        inv = inv.strip()
        if not inv:
            continue
        surname, _, display = _parse_inventor(inv)
        if not surname:
            continue
        candidates = by_surname.get(surname, [])
        best: tuple[float, dict[str, str]] | None = None
        for phy in candidates:
            score = score_inventor_physician_match(inv, phy)
            if score < min_score:
                continue
            if best is None or score > best[0]:
                best = (score, phy)
        if best:
            score, phy = best
            hits.append(
                {
                    "inventor_patent_name": inv,
                    "inventor_display_name": display,
                    "physician_id": phy.get("physician_id", ""),
                    "name": phy.get("name", ""),
                    "specialty": phy.get("specialty", ""),
                    "institution": phy.get("institution", ""),
                    "match_score": round(score, 1),
                    "match_basis": "inventor_surname_npi",
                }
            )
    hits.sort(key=lambda x: x["match_score"], reverse=True)
    return hits


def best_inventor_physician_match(inventors: list[str]) -> dict[str, Any] | None:
    matches = match_inventors_to_physicians(inventors)
    return matches[0] if matches else None
