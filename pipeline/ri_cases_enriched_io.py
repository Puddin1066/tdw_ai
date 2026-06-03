"""Load / save ri_cases_enriched.csv and bridge rows to build_exhibit inputs."""

from __future__ import annotations

import csv
from pathlib import Path
from typing import Any

from pipeline.ri_cases_enriched_schema import (
    COMP_PREFIXES,
    DEFAULT_TOTAL_PACKAGE_USD,
    FIELDNAMES,
    MAX_SLATER_SHARE_USD,
    MAX_TOTAL_PACKAGE_USD,
)

ROOT = Path(__file__).resolve().parents[1]
CASES_CSV = ROOT / "data" / "ri" / "ri_cases_enriched.csv"


def empty_row(case_id: str = "") -> dict[str, str]:
    row = {f: "" for f in FIELDNAMES}
    if case_id:
        row["case_id"] = case_id
    return row


def load_cases(path: Path = CASES_CSV) -> list[dict[str, str]]:
    if not path.exists():
        return []
    with path.open(newline="", encoding="utf-8") as handle:
        return list(csv.DictReader(handle))


def write_cases(rows: list[dict[str, str]], path: Path = CASES_CSV) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    normalized = [{f: (r.get(f) or "").strip() for f in FIELDNAMES} for r in rows]
    with path.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=FIELDNAMES, extrasaction="ignore")
        writer.writeheader()
        writer.writerows(normalized)


def _bool(value: str | None) -> bool:
    return (value or "").strip().lower() in {"1", "true", "t", "yes", "y"}


def _int(value: str | None, default: int = 0) -> int:
    try:
        return int(float((value or "").strip()))
    except ValueError:
        return default


def apply_finance_defaults(row: dict[str, str]) -> None:
    """Policy: total ≤ $400K, 50/50 split, Slater ≤ $200K."""
    total = _int(row.get("total_package_usd"))
    if total <= 0:
        total = DEFAULT_TOTAL_PACKAGE_USD
    total = min(total, MAX_TOTAL_PACKAGE_USD)
    half = total // 2
    slater = min(half, MAX_SLATER_SHARE_USD)
    physician = total - slater
    row["total_package_usd"] = str(total)
    row["physician_share_usd"] = str(physician)
    row["slater_share_usd"] = str(slater)
    if not row.get("financing_stage"):
        row["financing_stage"] = "seed"


def apply_use_of_funds(row: dict[str, str]) -> bool:
    """Split total package into clinical vs R&D allocations with physician-readable rationale."""
    apply_finance_defaults(row)
    total = _int(row.get("total_package_usd"))
    if total <= 0:
        return False

    changed = False
    clinical_cost = _int(row.get("clinical_cost_usd"))
    otype = (row.get("opportunity_type") or "platform").strip().lower()

    if not (row.get("clinical_allocation_usd") or "").strip():
        if otype in ("diagnostic", "digital_therapeutic", "therapeutic"):
            clinical = min(clinical_cost or (total * 45 // 100), total // 2)
        elif otype == "medical_device":
            clinical = min(clinical_cost or (total * 35 // 100), total // 2)
        else:
            clinical = min(clinical_cost or (total // 3), total // 2)
        row["clinical_allocation_usd"] = str(clinical)
        changed = True

    if not (row.get("rd_allocation_usd") or "").strip():
        clinical_alloc = _int(row.get("clinical_allocation_usd"))
        row["rd_allocation_usd"] = str(max(0, total - clinical_alloc))
        changed = True

    if not (row.get("financing_rationale") or "").strip():
        cl = _int(row.get("clinical_allocation_usd"))
        rd = _int(row.get("rd_allocation_usd"))
        half = _int(row.get("physician_share_usd"))
        row["financing_rationale"] = (
            f"${half:,} physician syndicate + ${half:,} Slater SSBCI match; "
            f"${cl:,} toward clinical pilot validation · ${rd:,} toward R&D/preclinical de-risking."
        )
        changed = True

    return changed


def _split_lines(value: str) -> list[str]:
    return [x.strip() for x in (value or "").replace("\r", "").split("\n") if x.strip()]


def _split_pipe(value: str) -> list[str]:
    return [x.strip() for x in (value or "").split("|") if x.strip()]


def _parse_supporting_citations(value: str) -> list[dict[str, str]]:
    """Parse newline 'label | url' supporting citation lines."""
    out: list[dict[str, str]] = []
    for line in _split_lines(value):
        if " | " not in line:
            continue
        label, url = line.split(" | ", 1)
        label = label.strip()
        url = url.strip()
        if label and url:
            out.append({"label": label, "url": url})
    return out


def comps_from_row(row: dict[str, str]) -> list[dict[str, Any]]:
    precedents: list[dict[str, Any]] = []
    for rank, prefix in enumerate(COMP_PREFIXES, start=1):
        name = (row.get(f"{prefix}name") or "").strip()
        if not name:
            continue
        notes = (row.get(f"{prefix}notes") or "").strip()
        ladder = (row.get(f"{prefix}financing_ladder") or "").strip()
        precedents.append(
            {
                "rank": rank,
                "type": row.get(f"{prefix}type", ""),
                "name": name,
                "role": row.get(f"{prefix}role", ""),
                "stage": row.get(f"{prefix}stage", ""),
                "notes": notes or ladder,
                "url": row.get(f"{prefix}url", ""),
                "inferred_development": row.get(f"{prefix}development_path", ""),
                "inferred_financing": ladder,
                "inferred_team": "",
                "total_raised_usd_est": row.get(f"{prefix}total_raised_usd", ""),
                "last_round_usd_est": row.get(f"{prefix}last_round_usd", ""),
                "value_anchor_usd": row.get(f"{prefix}value_anchor_usd", ""),
                "value_anchor_type": row.get(f"{prefix}value_anchor_type", ""),
                "value_source_url": row.get(f"{prefix}value_source_url", ""),
                "financing_strategy": "",
                "validation_status": row.get(f"{prefix}validation_status", "suggested"),
                "confidence": "",
                "source": "ri_cases_enriched.csv",
                "supporting_citations": _parse_supporting_citations(
                    row.get(f"{prefix}supporting_citations", "")
                ),
            }
        )
    return precedents


def ip_from_row(row: dict[str, str]) -> list[dict[str, str]]:
    lens_ids = _split_pipe(row.get("ip_lens_ids", ""))
    titles = _split_lines(row.get("ip_titles", ""))
    urls = _split_lines(row.get("ip_urls", ""))
    display_keys = _split_pipe(row.get("primary_display_key", ""))  # fallback single
    assets: list[dict[str, str]] = []
    primary = (row.get("primary_lens_id") or "").strip()
    if primary:
        assets.append(
            {
                "lens_id": primary,
                "display_key": row.get("primary_display_key", ""),
                "title": row.get("primary_patent_title", ""),
                "owners": row.get("assignee_company", ""),
                "url": row.get("primary_patent_url", "")
                or f"https://lens.org/{primary}",
            }
        )
    elif (row.get("primary_patent_url") or row.get("primary_patent_title") or "").strip():
        # Manual / supplemental intake without Lens ID (e.g. mindimmune_therapeutics_ri)
        assets.append(
            {
                "lens_id": "",
                "display_key": row.get("primary_display_key", ""),
                "title": row.get("primary_patent_title", ""),
                "owners": row.get("assignee_company", ""),
                "url": (row.get("primary_patent_url") or "").strip(),
            }
        )
    for i, lens in enumerate(lens_ids):
        if lens == primary:
            continue
        assets.append(
            {
                "lens_id": lens,
                "display_key": display_keys[i] if i < len(display_keys) else "",
                "title": titles[i] if i < len(titles) else "",
                "owners": row.get("assignee_company", ""),
                "url": urls[i] if i < len(urls) else f"https://lens.org/{lens}",
            }
        )
    return assets[:2]


def evidence_from_row(row: dict[str, str]) -> dict[str, Any]:
    titles = _split_lines(row.get("publication_titles", ""))
    authors = _split_lines(row.get("publication_lead_authors", ""))
    affiliations = _split_lines(row.get("publication_ri_affiliations", ""))
    urls = _split_lines(row.get("publication_urls", ""))
    pmids = _split_lines(row.get("publication_pmids", ""))
    pubs: list[dict[str, Any]] = []
    for i, title in enumerate(titles):
        pmid = pmids[i] if i < len(pmids) else ""
        url = urls[i] if i < len(urls) else ""
        if pmid and not url:
            url = f"https://pubmed.ncbi.nlm.nih.gov/{pmid}/"
        pubs.append(
            {
                "title": title,
                "journal": "",
                "publication_date": "",
                "pmid": pmid,
                "url": url,
                "authors": [authors[i]] if i < len(authors) else [],
                "abstract_snippet": "",
                "ri_affiliation": affiliations[i] if i < len(affiliations) else "",
            }
        )
    trials: list[dict[str, Any]] = []
    ncts = _split_pipe(row.get("trial_nct_ids", ""))
    t_titles = _split_lines(row.get("trial_titles", ""))
    t_urls = _split_lines(row.get("trial_urls", ""))
    t_phases = _split_pipe(row.get("trial_phases", ""))
    t_pis = _split_lines(row.get("trial_pi_names", ""))
    for i, nct in enumerate(ncts):
        url = t_urls[i] if i < len(t_urls) else f"https://clinicaltrials.gov/study/{nct}"
        trials.append(
            {
                "nct_id": nct,
                "title": t_titles[i] if i < len(t_titles) else "",
                "phase": t_phases[i] if i < len(t_phases) else "",
                "status": "",
                "url": url,
                "pi_names": t_pis[i] if i < len(t_pis) else "",
            }
        )
    count = _int(row.get("publication_count")) or len(pubs)
    return {
        "status": "canonical_csv" if pubs else "pending",
        "search_terms": [],
        "publications": pubs,
        "trials": trials,
        "literature_narrative": row.get("literature_narrative", ""),
        "publication_count": count,
        "trial_count": _int(row.get("trial_count")) or len(trials),
        "fetched_at": row.get("last_refreshed_at", ""),
        "warnings": [],
    }


def _first_inventor(inventors: str | None) -> str:
    for line in (inventors or "").splitlines():
        line = line.strip()
        if line:
            return line.split(";")[0].split("|")[0].strip()
    return ""


def _display_title(title: str, company: str) -> str:
    """Strip redundant company prefix from title_clean (e.g. 'Theromics — X' when company is Theromics Inc)."""
    title = title.strip()
    if not title or not company:
        return title
    company_l = company.lower()
    if title.lower().startswith(company_l):
        return title
    co_token = company.split()[0]
    for sep in (" — ", " - ", "—"):
        if sep not in title:
            continue
        prefix, rest = title.split(sep, 1)
        p = prefix.strip().lower()
        if p == co_token.lower() or p == company_l:
            return rest.strip()
    return title


def build_thesis(row: dict[str, str]) -> str:
    """Investor/physician-facing thesis from canonical row (policy package, no legacy gaps)."""
    title = _display_title(
        (row.get("title_clean") or row.get("case_id", "")).strip(),
        (row.get("company") or "").strip(),
    )
    company = (row.get("company") or "").strip()
    institution = (row.get("ri_institution") or "").strip()
    indication = (row.get("indication") or "").strip()
    total = _int(row.get("total_package_usd"))
    comp1 = (row.get("comp1_name") or "").strip()
    ladder = (row.get("comp1_financing_ladder") or "").strip()
    inventor = _first_inventor(row.get("inventors"))
    phys_lead = (row.get("physician_lead_name") or "").strip()

    if company and title and not title.lower().startswith(company.lower()):
        headline = f"{company} — {title}"
    elif title:
        headline = title
    else:
        headline = company

    parts: list[str] = []
    if institution and institution.lower() not in headline.lower():
        parts.append(f"RI anchor: {institution}")
    if headline:
        parts.append(headline)
    if (
        indication
        and indication.lower() not in title.lower()
        and indication.lower() != headline.lower()
        and len(indication) < 120
    ):
        parts.append(f"focused on {indication}")
    if inventor:
        parts.append(f"inventor: {inventor}")
    if comp1 and comp1.lower() not in {company.lower(), title.lower()}:
        parts.append(f"comparable path: {comp1}")
    if ladder:
        parts.append(f"financing ladder: {ladder[:180]}")
    if phys_lead:
        parts.append(f"proposed physician lead: {phys_lead}")
    if total:
        parts.append(
            f"RI co-investment ${total:,} (50% physician syndicate / 50% Slater SSBCI, ≤$400K policy cap)"
        )
    text = ". ".join(p for p in parts if p)
    return text + ("." if text and not text.endswith(".") else "")


def catalog_row_from_enriched(row: dict[str, str]) -> dict[str, str]:
    """Map monolithic row → build_exhibit catalog-shaped dict."""
    apply_use_of_funds(row)
    total = _int(row.get("total_package_usd"))
    out = dict(row)
    out["capital_gap_usd"] = str(total)
    out["budget_ceiling_usd"] = str(int(total * 1.15))
    # No million-dollar value band in UI (locked decision)
    out["value_band_min_usd"] = ""
    out["value_band_max_usd"] = ""
    out["value_band_median_usd"] = ""
    out["value_verification_status"] = ""
    out["value_anchor_verified_count"] = str(
        sum(
            1
            for p in COMP_PREFIXES
            if (row.get(f"{p}validation_status") or "").lower() == "verified"
        )
    )
    out["inferred_development_path"] = row.get("comp1_development_path", "")
    out["inferred_financing_path"] = row.get("comp1_financing_ladder", "")
    out["inferred_next_milestone"] = _split_lines(row.get("rd_milestones", ""))[0] if row.get("rd_milestones") else ""
    out["clinical_path_notes"] = row.get("clinical_path_notes") or row.get("rd_plan_summary", "")
    out["opportunity_enrichment_source"] = "ri_cases_enriched.csv"
    out["enrichment_status"] = row.get("enrichment_status") or "canonical_csv"
    out.setdefault("mcq_lead_pillar", "ip")
    out.setdefault("mcq_financing_structure", "physician_50_slater_ssbci_50")
    out.setdefault("mcq_audience", "mixed_slater_physician_hospital_bd")
    if (row.get("review_status") or "").lower() == "approved" and (row.get("investment_thesis") or "").strip():
        out["investment_thesis"] = row["investment_thesis"]
    else:
        out["investment_thesis"] = build_thesis(row)
    if (row.get("comparable_market_narrative") or "").strip():
        out["comparable_market_narrative"] = row["comparable_market_narrative"]
    if row.get("rd_plan_summary") and not out.get("clinical_study_type"):
        out["clinical_study_type"] = "Proposed R&D plan"
    return out


def physicians_from_row(row: dict[str, str]) -> list[dict[str, str]]:
    roster: list[dict[str, str]] = []
    lead_npi = (row.get("physician_lead_npi") or "").strip()
    lead_name = (row.get("physician_lead_name") or "").strip()
    if lead_npi or lead_name:
        roster.append(
            {
                "physician_id": lead_npi,
                "name": lead_name,
                "specialty": row.get("physician_lead_specialty", ""),
                "institution": row.get("physician_lead_institution", ""),
                "roles_matched": "lead",
                "is_lead": "true",
                "profile_url": row.get("physician_lead_profile_url", ""),
            }
        )
    block = row.get("physician_supporters") or ""
    profile_urls = _split_lines(row.get("physician_supporter_profile_urls", ""))
    idx = 0
    for line in block.splitlines():
        line = line.strip()
        if not line:
            continue
        parts = line.split("|")
        if len(parts) < 4:
            continue
        roster.append(
            {
                "physician_id": parts[0].strip(),
                "name": parts[1].strip(),
                "specialty": parts[2],
                "institution": parts[3],
                "roles_matched": parts[4] if len(parts) > 4 else "reviewer",
                "is_lead": "false",
                "profile_url": profile_urls[idx] if idx < len(profile_urls) else "",
            }
        )
        idx += 1
    return roster
