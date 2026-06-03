"""Clinical trial enrichment for ri_cases_enriched.csv.

Policy (strict — empty beats wrong):
  - Main trial_* columns: ONLY (1) NCT explicitly cited in comp columns, or (2) hand-curated
    CASE_FIELD_PATCHES with trial_nct_ids (including intentional empty lock).
  - No CT.gov keyword or comp-name search auto-matching.

Never search on institution tokens (Brown, Rhode Island, inventor surnames alone).
"""

from __future__ import annotations

import csv
import re
import time
from pathlib import Path
from typing import Any

import httpx

from pipeline.ri_biomcp_relevance import STOPWORDS as MECHANISM_STOPWORDS
from pipeline.ri_cases_enriched_schema import COMP_SUFFIXES, MAX_COMP_SLOTS
from pipeline.tier_a.comp_financing import comp_base_name

ROOT = Path(__file__).resolve().parents[1]
TRIAL_TEMPLATES_CSV = ROOT / "data" / "ri" / "ri_trial_templates.csv"
IP_PATH = ROOT / "data" / "ri" / "ri_ip_assets.csv"

INSTITUTION_TOKENS = frozenset(
    {
        "brown",
        "rhode",
        "island",
        "university",
        "hospital",
        "uri",
        "providence",
        "lifespan",
        "warren",
        "alpert",
        "noramco",
        "rhodes",
        "technologies",
        "pharmaceuticals",
        "pharma",
        "tbd",
        "ri",
        "usa",
        "inc",
        "llc",
        "corp",
    }
)

TRIAL_TITLE_BLOCKLIST = (
    "brown adipose",
    "adipose tissue",
    "intrusive thoughts",
    "obsessive-compulsive disorder",
)

MIN_MAIN_SCORE = 0.22  # retained for tests; not used for auto-assignment
MIN_SUGGEST_SCORE = 0.12
FETCH_DELAY_S = 0.35
NCT_ID_RE = re.compile(r"\bNCT\d{8}\b", re.I)
MIN_COMP_TOKEN_LEN = 4


def _tokenize(text: str) -> set[str]:
    tokens = re.findall(r"[A-Za-z0-9][A-Za-z0-9-]{2,}", (text or "").lower())
    return {
        t
        for t in tokens
        if t not in MECHANISM_STOPWORDS
        and t not in INSTITUTION_TOKENS
        and len(t) >= 3
    }


def _clean_indication(indication: str) -> str:
    text = (indication or "").strip()
    text = re.sub(r"^(brown|rhode|uri)\s*[—–-]\s*", "", text, flags=re.I)
    text = re.sub(r"\brhode island\b", "", text, flags=re.I)
    return re.sub(r"\s+", " ", text).strip()


def _clean_title(title: str) -> str:
    text = (title or "").strip()
    text = re.sub(r"^(brown|rhode|uri)\s*[—–-]\s*", "", text, flags=re.I)
    return re.sub(r"\s+", " ", text).strip()


def _keywords(text: str, *, max_words: int = 6) -> str:
    tokens = re.findall(r"[A-Za-z0-9][A-Za-z0-9-]{2,}", text.lower())
    kept = [
        t
        for t in tokens
        if t not in MECHANISM_STOPWORDS and t not in INSTITUTION_TOKENS
    ]
    return " ".join(kept[:max_words])


def _load_ip_by_case() -> dict[str, list[dict[str, str]]]:
    by_case: dict[str, list[dict[str, str]]] = {}
    if not IP_PATH.exists():
        return by_case
    for row in csv.DictReader(IP_PATH.open(encoding="utf-8")):
        by_case.setdefault(row["case_id"], []).append(row)
    return by_case


def build_trial_profile(row: dict[str, str], ip_rows: list[dict[str, str]]) -> dict[str, Any]:
    """Mechanism-focused tokens and search queries for trial matching."""
    tokens: set[str] = set()
    queries: list[tuple[str, str]] = []

    def add_tokens(text: str) -> None:
        tokens.update(_tokenize(text))

    patent_title = (row.get("primary_patent_title") or "").strip()
    if patent_title:
        add_tokens(patent_title)
    for ip in ip_rows[:2]:
        pt = (ip.get("title") or "").strip()
        if pt:
            add_tokens(pt)

    indication = _clean_indication(row.get("indication") or "")
    title = _clean_title(row.get("title_clean") or row.get("display_name") or "")
    if indication:
        add_tokens(indication)
    if title:
        add_tokens(title)

    tags = (row.get("clinical_tags") or "").replace("|", " ")
    if tags:
        add_tokens(tags)

    kw_patent = _keywords(patent_title or title, max_words=8)
    kw_indication = _keywords(indication, max_words=5)

    for rank in range(1, 4):
        name = (row.get(f"comp{rank}_name") or "").strip()
        if not name:
            continue
        base = comp_base_name(name)
        add_tokens(base)
        if kw_indication:
            queries.append((f"comp{rank}_precedent", f'"{base}" {kw_indication}'))
        queries.append((f"comp{rank}_precedent", f"{base} clinical trial"))

    if kw_patent and kw_indication:
        queries.append(("mechanism", f"{kw_patent} {kw_indication}"))
    elif kw_patent:
        queries.append(("mechanism", kw_patent))
    elif kw_indication:
        queries.append(("mechanism", kw_indication))

    seen_q: set[str] = set()
    unique_queries: list[tuple[str, str]] = []
    for role, q in queries:
        q = re.sub(r"\s+", " ", q.strip())
        if len(q) < 8 or q.lower() in seen_q:
            continue
        if any(inst in q.lower().split() for inst in ("brown", "rhode", "university")):
            continue
        seen_q.add(q.lower())
        unique_queries.append((role, q))

    return {
        "tokens": tokens,
        "queries": unique_queries[:5],
        "kw_indication": kw_indication,
        "kw_patent": kw_patent,
    }


def _jaccard(a: set[str], b: set[str]) -> float:
    if not a or not b:
        return 0.0
    inter = len(a & b)
    union = len(a | b)
    return inter / union if union else 0.0


def score_trial(title: str, profile_tokens: set[str], *, role: str) -> float:
    title_l = (title or "").lower()
    if any(block in title_l for block in TRIAL_TITLE_BLOCKLIST):
        return 0.0
    title_tokens = _tokenize(title)
    if not title_tokens:
        return 0.0
    score = _jaccard(profile_tokens, title_tokens)
    if role.startswith("comp") and score > 0:
        score = min(1.0, score + 0.08)
    return score


def _comp_match_tokens(comp_name: str) -> list[str]:
    """Company / product tokens used to verify a CT.gov hit belongs to a comp."""
    name = (comp_name or "").strip()
    if not name:
        return []
    # Skip generic financing / institution placeholders — not CT.gov search targets.
    lower = name.lower()
    if lower.startswith("nih sbir") or lower.startswith("brown/ri hospital"):
        return []
    if lower.startswith("slater /") or lower.startswith("slater/"):
        return []
    tokens: list[str] = []
    base = comp_base_name(name).strip()
    if len(base) >= MIN_COMP_TOKEN_LEN and base.lower() not in INSTITUTION_TOKENS:
        tokens.append(base.lower())
    paren = re.search(r"\(([^)]+)\)", name)
    if paren:
        for part in re.split(r"[/,&]", paren.group(1)):
            piece = part.strip()
            if len(piece) >= MIN_COMP_TOKEN_LEN:
                tokens.append(piece.lower())
    seen: set[str] = set()
    out: list[str] = []
    for t in tokens:
        if t not in seen:
            seen.add(t)
            out.append(t)
    return out


def _trial_matches_comp(comp_name: str, trial: dict[str, str]) -> bool:
    hay = f"{trial.get('title', '')} {trial.get('sponsor', '')}".lower()
    return any(token in hay for token in _comp_match_tokens(comp_name))


def _parse_ctgov_study(study: dict[str, Any]) -> dict[str, str] | None:
    proto = study.get("protocolSection") or {}
    ident = proto.get("identificationModule") or {}
    design = proto.get("designModule") or {}
    sponsor_mod = proto.get("sponsorCollaboratorsModule") or {}
    nct = (ident.get("nctId") or "").strip()
    title = (ident.get("briefTitle") or ident.get("officialTitle") or "").strip()
    if not nct or not title:
        return None
    phases = design.get("phases") or []
    lead = sponsor_mod.get("leadSponsor") or {}
    sponsor = (lead.get("name") or "").strip()
    return {
        "nct_id": nct.upper(),
        "title": title,
        "phase": ", ".join(phases) if phases else "",
        "url": f"https://clinicaltrials.gov/study/{nct.upper()}",
        "sponsor": sponsor,
    }


def fetch_trial_by_nct(nct_id: str) -> dict[str, str] | None:
    nct = (nct_id or "").strip().upper()
    if not NCT_ID_RE.fullmatch(nct):
        return None
    try:
        with httpx.Client(timeout=20.0, follow_redirects=True) as client:
            response = client.get(
                f"https://clinicaltrials.gov/api/v2/studies/{nct}",
                params={"format": "json"},
            )
            response.raise_for_status()
            payload = response.json()
    except httpx.HTTPError:
        return None
    return _parse_ctgov_study(payload)


def _ncts_from_comp_columns(row: dict[str, str]) -> list[str]:
    seen: set[str] = set()
    ordered: list[str] = []
    for i in range(1, MAX_COMP_SLOTS + 1):
        for suffix in COMP_SUFFIXES:
            text = (row.get(f"comp{i}_{suffix}") or "").strip()
            if not text:
                continue
            for match in NCT_ID_RE.findall(text):
                nct = match.upper()
                if nct not in seen:
                    seen.add(nct)
                    ordered.append(nct)
    return ordered


def fetch_trials_ctgov(query: str, *, limit: int = 5) -> list[dict[str, str]]:
    if len(query.strip()) < 8:
        return []
    try:
        with httpx.Client(timeout=20.0, follow_redirects=True) as client:
            response = client.get(
                "https://clinicaltrials.gov/api/v2/studies",
                params={"query.term": query, "pageSize": limit, "format": "json"},
            )
            response.raise_for_status()
            payload = response.json()
    except httpx.HTTPError:
        return []

    out: list[dict[str, str]] = []
    for study in payload.get("studies") or []:
        parsed = _parse_ctgov_study(study)
        if parsed:
            out.append(parsed)
    return out


def _write_main_trials(
    row: dict[str, str],
    trials: list[tuple[float, str, dict[str, str]]],
) -> None:
    if not trials:
        return
    trials.sort(key=lambda x: x[0], reverse=True)
    top = trials[:3]
    row["trial_count"] = str(len(top))
    row["trial_nct_ids"] = " | ".join(t[2]["nct_id"] for t in top)
    row["trial_titles"] = "\n".join(t[2]["title"] for t in top)
    row["trial_urls"] = "\n".join(t[2]["url"] for t in top)
    row["trial_phases"] = " | ".join(t[2]["phase"] for t in top)
    row["trial_pi_names"] = ""


def _write_suggest_trials(
    row: dict[str, str],
    trials: list[tuple[float, str, dict[str, str]]],
) -> None:
    if not trials:
        return
    trials.sort(key=lambda x: x[0], reverse=True)
    top = trials[:3]
    row["suggest_trial_nct_ids"] = " | ".join(t[2]["nct_id"] for t in top)
    row["suggest_trial_titles"] = "\n".join(t[2]["title"] for t in top)
    row["suggest_trial_urls"] = "\n".join(t[2]["url"] for t in top)
    row["suggest_trial_notes"] = "\n".join(
        f"{t[1]} (score={t[0]:.2f})" for t in top
    )


def clear_all_trial_fields(row: dict[str, str]) -> None:
    for key in (
        "trial_count",
        "trial_nct_ids",
        "trial_titles",
        "trial_pi_names",
        "trial_urls",
        "trial_phases",
        "suggest_trial_nct_ids",
        "suggest_trial_titles",
        "suggest_trial_urls",
        "suggest_trial_notes",
    ):
        row[key] = ""


def fill_clinical_template(row: dict[str, str], templates: list[dict[str, str]]) -> bool:
    """Match RI pilot template by opportunity_type (design precedent, not CT.gov registry)."""
    if (row.get("clinical_study_type") or "").strip():
        return False
    otype = (row.get("opportunity_type") or "platform").strip().lower()
    candidates = [t for t in templates if (t.get("opportunity_type") or "").lower() == otype]
    if not candidates:
        return False
    candidates.sort(
        key=lambda t: (
            0 if (t.get("mocked") or "").lower() == "false" else 1,
            -float(t.get("expected_inflection_weight_0_1") or 0),
        ),
    )
    best = candidates[0]
    row["clinical_study_type"] = best.get("study_type", "")
    row["clinical_primary_endpoint"] = best.get("primary_endpoint_type", "")
    row["clinical_duration_weeks"] = best.get("duration_weeks", "")
    row["clinical_cost_usd"] = best.get("cost_usd", "")
    row["clinical_path_notes"] = (
        f"RI trial template {best.get('template_id', '')} "
        f"({best.get('source_type', 'template')}) — pilot design analog, not program-specific NCT."
    )
    return True


def enrich_trials_for_row(
    row: dict[str, str],
    ip_rows: list[dict[str, str]],
    templates: list[dict[str, str]],
    *,
    force: bool = False,
) -> list[str]:
    changes: list[str] = []
    if not force and (row.get("review_status") or "").lower() == "approved":
        return changes

    clear_all_trial_fields(row)
    main_hits: list[tuple[float, str, dict[str, str]]] = []
    seen_nct: set[str] = set()

    # Layer A: NCT explicitly cited in comp columns (highest confidence).
    for nct in _ncts_from_comp_columns(row):
        time.sleep(FETCH_DELAY_S)
        trial = fetch_trial_by_nct(nct)
        if not trial or trial["nct_id"] in seen_nct:
            continue
        seen_nct.add(trial["nct_id"])
        main_hits.append((1.0, "comp_nct_cited", trial))

    # Layer B disabled: quoted comp-name CT.gov search produced false positives
    # (e.g. any Takeda trial for ProThera, NeuroPace RNS on unrelated DBS rows).
    # Add verified NCT IDs to comp URLs/citations instead; curators lock via CASE_FIELD_PATCHES.

    if main_hits:
        main_hits.sort(key=lambda x: x[0], reverse=True)
        _write_main_trials(row, main_hits[:3])
        changes.append("trials_main")

    if fill_clinical_template(row, templates):
        changes.append("clinical_template")

    if not main_hits:
        row["trial_count"] = "0"
        changes.append("trials_empty")

    return changes


def load_trial_templates() -> list[dict[str, str]]:
    if not TRIAL_TEMPLATES_CSV.exists():
        return []
    return list(csv.DictReader(TRIAL_TEMPLATES_CSV.open(encoding="utf-8")))
