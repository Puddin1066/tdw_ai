"""Physician syndicate matching enrichment for ri_cases_enriched.csv.

Runs NPI-based clinical-tag matching (physician_assignment) and writes:
  - clinical_tags / required_specialties (when empty)
  - suggest_physician_* assist columns for curator promotion
  - staffing_feasibility_score

Does not overwrite physician_lead_* or physician_supporters on approved rows.
"""

from __future__ import annotations

import argparse
from datetime import date
from pathlib import Path

from pipeline.physician_assignment import (
    _merge_opportunity_baseline,
    _load_opportunities_lookup,
    compute_assignments_for_enriched_rows,
    enrich_opportunity_row,
    load_ip_by_case,
)
from pipeline.remediate_ri_cases_enriched import PLACEHOLDER_LEADS
from pipeline.ri_cases_enriched_io import CASES_CSV, apply_use_of_funds, load_cases, write_cases
from pipeline.ri_inventor_npi_match import (
    _inventor_display_name,
    best_inventor_physician_match,
    lead_npi_name_mismatch,
    match_inventors_to_physicians,
)


def _bool(value: str | None) -> bool:
    return (value or "").strip().lower() in {"1", "true", "t", "yes", "y"}


def _npi_key(value: str) -> str:
    return (value or "").strip().lower().replace("npi_", "")


def _match_to_supporter_line(match: dict) -> str:
    pid = (match.get("physician_id") or "").strip()
    name = (match.get("name") or "").strip()
    specialty = (match.get("specialty") or "").strip()
    institution = (match.get("institution") or "").strip()
    roles = match.get("roles_matched") or []
    role = roles[0] if roles else "reviewer"
    return f"{pid}|{name}|{specialty}|{institution}|{role}"


def _is_placeholder_lead(row: dict[str, str]) -> bool:
    lead = (row.get("physician_lead_name") or "").upper().strip()
    if not lead:
        return True
    return lead in PLACEHOLDER_LEADS


def _apply_inventor_npi_lead(row: dict[str, str]) -> bool:
    """Promote patent inventor NPI match to lead when lead is placeholder or missing NPI."""
    if (row.get("review_status") or "").lower() == "approved":
        return False
    inventors = [x.strip() for x in (row.get("inventors") or "").split("|") if x.strip()]
    if not inventors:
        return False

    first_surname = inventors[0].split()[0].upper()
    lead_up = (row.get("physician_lead_name") or "").upper()
    if first_surname and lead_up and first_surname not in lead_up and not _is_placeholder_lead(row):
        row["physician_lead_name"] = _inventor_display_name(inventors[0])
        row["physician_lead_npi"] = ""
        changed_name = True
    else:
        changed_name = False

    best = best_inventor_physician_match([inventors[0]])
    lead = (row.get("physician_lead_name") or "").strip()

    if lead and not _is_placeholder_lead(row) and first_surname:
        matched_name = (best.get("name") or "").upper() if best else ""
        if first_surname not in matched_name:
            if lead_npi_name_mismatch(row) or changed_name:
                row["physician_lead_npi"] = ""
                return True
            return False

    if not best:
        if lead_npi_name_mismatch(row) or changed_name:
            row["physician_lead_npi"] = ""
            return True
        return False
    if (
        not _is_placeholder_lead(row)
        and (row.get("physician_lead_npi") or "").strip()
        and not lead_npi_name_mismatch(row)
    ):
        return False
    if lead_npi_name_mismatch(row):
        row["physician_lead_npi"] = ""
    row["physician_lead_npi"] = str(best.get("physician_id") or "").replace("npi_", "")
    row["physician_lead_name"] = str(best.get("name") or "")
    row["physician_lead_specialty"] = str(best.get("specialty") or "")
    row["physician_lead_institution"] = str(best.get("institution") or "")
    note = (
        f"inventor_match: {best.get('inventor_display_name')} → NPI "
        f"(score={best.get('match_score')})"
    )
    existing = (row.get("suggest_physician_notes") or "").strip()
    row["suggest_physician_notes"] = f"{existing}\n{note}".strip() if existing else note
    return True


def enrich_physicians(
    *,
    path: Path = CASES_CSV,
    tier: str | None = None,
    case_id: str | None = None,
) -> dict[str, int]:
    rows = load_cases(path)
    assignments = compute_assignments_for_enriched_rows(rows, catalog_only=True)
    baseline_by = _load_opportunities_lookup()
    ip_by_case = load_ip_by_case()
    today = date.today().isoformat()
    touched = 0

    for row in rows:
        if case_id and row.get("case_id") != case_id:
            continue
        if tier and (row.get("catalog_tier") or "").upper() != tier.upper():
            continue
        if not _bool(row.get("catalog_include", "true")):
            continue
        if (row.get("review_status") or "").lower() == "approved":
            continue

        cid = row["case_id"]
        match = assignments.get(cid, {})
        merged = enrich_opportunity_row(
            _merge_opportunity_baseline(row, baseline_by.get(cid)),
            ip_by_case.get(cid),
        )

        changed = False
        if _apply_inventor_npi_lead(row):
            changed = True
            lead_npi = _npi_key(row.get("physician_lead_npi", ""))
            lead_name = (row.get("physician_lead_name") or "").strip().upper()
        if apply_use_of_funds(row):
            changed = True

        if not (row.get("clinical_tags") or "").strip() and merged.get("clinical_tags"):
            row["clinical_tags"] = merged["clinical_tags"]
            changed = True
        if not (row.get("required_specialties") or "").strip() and merged.get("required_specialties"):
            row["required_specialties"] = merged["required_specialties"]
            changed = True

        score = match.get("staffing_feasibility_score_0_100")
        score_s = str(score) if score is not None else ""
        if score_s and row.get("staffing_feasibility_score") != score_s:
            row["staffing_feasibility_score"] = score_s
            changed = True

        candidates = match.get("candidate_physicians") or []
        lead_npi = _npi_key(row.get("physician_lead_npi", ""))
        lead_name = (row.get("physician_lead_name") or "").strip().upper()

        top = candidates[0] if candidates else None
        inventor_matches = match_inventors_to_physicians(
            [x.strip() for x in (row.get("inventors") or "").split("|") if x.strip()]
        )
        if inventor_matches and not (row.get("physician_lead_npi") or "").strip():
            inv = inventor_matches[0]
            row["suggest_physician_lead_npi"] = str(inv.get("physician_id") or "")
            row["suggest_physician_lead_name"] = str(inv.get("name") or "")
            row["suggest_physician_lead_specialty"] = str(inv.get("specialty") or "")
            row["suggest_physician_lead_institution"] = str(inv.get("institution") or "")
            row["suggest_physician_lead_match_score"] = str(inv.get("match_score") or "")
            changed = True
        elif top:
            top_npi = _npi_key(str(top.get("physician_id", "")))
            top_name = (top.get("name") or "").strip().upper()
            already_lead = lead_npi and top_npi and lead_npi == top_npi
            already_lead = already_lead or (lead_name and top_name and lead_name == top_name)
            if not already_lead:
                row["suggest_physician_lead_npi"] = str(top.get("physician_id") or "")
                row["suggest_physician_lead_name"] = str(top.get("name") or "")
                row["suggest_physician_lead_specialty"] = str(top.get("specialty") or "")
                row["suggest_physician_lead_institution"] = str(top.get("institution") or "")
                row["suggest_physician_lead_match_score"] = str(top.get("match_score_0_100") or "")
                changed = True

        supporter_lines: list[str] = []
        notes: list[str] = []
        for cand in candidates[1:6]:
            cand_npi = _npi_key(str(cand.get("physician_id", "")))
            cand_name = (cand.get("name") or "").strip().upper()
            if lead_npi and cand_npi == lead_npi:
                continue
            if lead_name and cand_name == lead_name:
                continue
            supporter_lines.append(_match_to_supporter_line(cand))
            tags = ", ".join(cand.get("clinical_tags_matched") or [])
            notes.append(
                f"{cand.get('name')} (score={cand.get('match_score_0_100')}; tags={tags})"
            )

        if supporter_lines:
            row["suggest_physician_supporters"] = "\n".join(supporter_lines)
            changed = True
        if notes:
            gaps = match.get("staffing_gaps") or []
            gap_note = f"Gaps: {', '.join(gaps)}" if gaps else ""
            extra = "\n".join(notes + ([gap_note] if gap_note else []))
            existing_notes = (row.get("suggest_physician_notes") or "").strip()
            row["suggest_physician_notes"] = (
                f"{existing_notes}\n{extra}".strip() if existing_notes else extra
            )
            changed = True

        if changed:
            row["last_refreshed_at"] = today
            row["enrichment_status"] = "physician_match_synced"
            touched += 1

    write_cases(rows, path=path)
    return {"processed": len(rows), "touched": touched}


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--path", type=Path, default=CASES_CSV)
    parser.add_argument("--tier", default=None)
    parser.add_argument("--case-id")
    args = parser.parse_args()
    stats = enrich_physicians(path=args.path, tier=args.tier, case_id=args.case_id)
    print(stats)


if __name__ == "__main__":
    main()
