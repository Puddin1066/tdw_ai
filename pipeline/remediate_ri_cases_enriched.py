"""Web-informed remediation pass for data/ri/ri_cases_enriched.csv.

Fixes systematic bootstrap errors: stale thesis text, npi_ prefixes in supporters,
irrelevant suggest_publication_* blobs (remediation no longer clears BioMCP suggest columns),
indications, auto-matched trial placeholders, ri_operating comp types, and selected
comparable evidence updates verified via public sources.
"""

from __future__ import annotations

import argparse
import re
from datetime import date
from pathlib import Path

from pipeline.brown_vivo_profiles import fill_brown_profile_url
from pipeline.ri_cases_enriched_io import (
    CASES_CSV,
    apply_finance_defaults,
    build_thesis,
    load_cases,
    write_cases,
)

GENERIC_INDICATION = "RI technology opportunity from patent corpus"

# Tier-A registry placeholders — not patent inventors; replaced via PHYSICIAN_FIXES or inventors.
PLACEHOLDER_LEADS = frozenset(
    {
        "EUGENIE ATALLAH",
        "TODD ROBERTS",
        "SHANTHI MOGALI",
        "HEINRICH ELINZANO",
        "BLAISE BAXTER",
        "BENJAMIN POLLOCK",
        "SETH CLARK",
        "GERARDO CARINO",
        "MAHER EL KHATIB",
        "LAERT RUSHA",
    }
)

# Curated physician / inventor alignment (sources: Brown VIVO, USPTO inventors, NPI registry).
PHYSICIAN_FIXES: dict[str, dict[str, str]] = {
    "auto_brown_university_drug_overdose": {
        "physician_lead_name": "CAROLINA HAASS-KOFFLER",
        "physician_lead_npi": "",
        "physician_lead_specialty": "Addiction medicine / translational pharmacology",
        "physician_lead_institution": "Brown University",
        "physician_lead_profile_url": "https://vivo.brown.edu/display/chaassko",
    },
    "auto_brown_university_anti_antibody_bispecific_chi3l1_reagents_relatin": {
        "physician_lead_name": "JACK A ELIAS",
        "physician_lead_npi": "",
        "physician_lead_specialty": "Pulmonary / critical care medicine",
        "physician_lead_institution": "Brown University",
        "physician_lead_profile_url": "https://vivo.brown.edu/display/jaelias",
    },
    "auto_brown_university_brain_chemotherapeutic_drug_enhancing_tumors_upt": {
        "physician_lead_name": "SEAN LAWLER",
        "physician_lead_npi": "",
        "physician_lead_specialty": "Neuro-oncology",
        "physician_lead_institution": "Brown University",
        "physician_lead_profile_url": "https://vivo.brown.edu/display/slawler",
    },
    "theromics_ri": {
        "physician_lead_name": "DAMIAN E DUPUY",
        "physician_lead_npi": "1861480733",
        "physician_lead_specialty": "Interventional radiology / tumor ablation",
        "physician_lead_institution": "Rhode Island Hospital (Theromics co-founder)",
        "physician_lead_profile_url": "https://www.theromicsinc.com/",
    },
    "nanode_ri": {
        "physician_lead_name": "QIAN CHEN",
        "physician_lead_npi": "",
        "physician_lead_specialty": "Biomedical engineering / nucleic acid delivery",
        "physician_lead_institution": "Rhode Island Hospital / NanoDe Therapeutics",
        "physician_lead_profile_url": "https://nanodetherapeutics.com/",
    },
    "cbt_pain_digital_platform_ri": {
        "physician_lead_name": "FREDERIKE PETZSCHNER",
        "physician_lead_npi": "",
        "physician_lead_specialty": "Psychiatry / digital pain therapeutics",
        "physician_lead_institution": "Brown University",
        "physician_lead_profile_url": "https://vivo.brown.edu/display/fpetzsch",
    },
    "monaghan_sepsis_diagnostic_ri": {
        "physician_lead_name": "SEAN MONAGHAN",
        "physician_lead_npi": "1871795906",
        "physician_lead_specialty": "Critical care / sepsis diagnostics",
        "physician_lead_institution": "Rhode Island Hospital",
        "physician_lead_profile_url": "",
    },
    "phlip_therapeutics_ri": {
        "physician_lead_name": "YANA K RESHETNYAK",
        "physician_lead_npi": "",
        "physician_lead_specialty": "Biophysics / pH-targeted imaging",
        "physician_lead_institution": "University of Rhode Island",
        "physician_lead_profile_url": "https://web.uri.edu/pharmacy/meet/yana-reshetnyak/",
    },
    "auto_rhode_island_biomedical_detecting_electrical_electrode_locali": {
        "physician_lead_name": "WALTER G BESIO",
        "physician_lead_npi": "",
        "physician_lead_specialty": "Biomedical engineering / neural interfaces",
        "physician_lead_institution": "University of Rhode Island",
        "physician_lead_profile_url": "https://www.ele.uri.edu/faculty/besio/",
    },
}

# Comparable patches from primary sources (PR/grant URLs).
COMP_FIXES: dict[str, dict[str, dict[str, str]]] = {
    "nanode_ri": {
        "comp1_": {
            "comp1_value_source_url": (
                "https://www.globenewswire.com/news-release/2025/05/19/"
                "3083947/0/en/Eascra-Biotech-Awarded-100-000-MassVentures-START-Grant.html"
            ),
            "comp1_last_round_usd": "100000",
            "comp1_total_raised_usd": "4500000",
            "comp1_financing_ladder": (
                "NSF SBIR + AFWERX SBIR + >$4.5M grants/awards; "
                "MassVentures START $100K (May 2025)"
            ),
            "comp1_validation_status": "verified",
        },
    },
    "auto_brown_university_brain_chemotherapeutic_drug_enhancing_tumors_upt": {
        "comp2_": {
            "comp2_name": "Insightec (Exablate / tFUS BBB)",
            "comp2_type": "startup",
            "comp2_url": "https://insightec.com/",
            "comp2_value_anchor_usd": "150000000",
            "comp2_value_anchor_type": "last_round",
            "comp2_value_source_url": (
                "https://insightec.com/news/insightec-announces-150m-financing-to-fund-continued-growth/"
            ),
            "comp2_total_raised_usd": "810000000",
            "comp2_last_round_usd": "150000000",
            "comp2_financing_ladder": "$150M equity round (Jun 2024); BBB-opening tFUS platform",
            "comp2_development_path": "Non-invasive FUS BBB modulation → neuro-onc trials",
            "comp2_validation_status": "verified",
        },
    },
    "auto_brown_university_anti_antibody_bispecific_chi3l1_reagents_relatin": {
        "comp3_": {
            "comp3_validation_status": "suggested",
            "comp3_development_path": (
                "Pharma acquisition analog — review therapeutic fit (NASH ≠ CHI3L1); "
                "prefer Ocean Biomedical / bispecific oncology exits"
            ),
        },
    },
}

ASSIGNEE_TO_RI_INSTITUTION: dict[str, str] = {
    "BROWN UNIVERSITY": "Brown University",
    "RHODE ISLAND HOSPITAL": "Rhode Island Hospital",
    "RHODE ISLAND BOARD OF EDUCATION STATE OF RHODE ISLAND AND PROVIDENCE PLANTATIONS": (
        "University of Rhode Island"
    ),
    "UNIVERSITY OF RHODE ISLAND BOARD OF GOVERNORS": "University of Rhode Island",
    "RHODE ISLAND COUNCIL ON POSTSECONDARY EDUCATION": "University of Rhode Island",
    "NORAMCO LLC": "Noramco LLC",
    "RHODES TECHNOLOGIES": "Rhodes Technologies",
    "PURDUE PHARMA L.P": "Purdue Pharma",
    "PURDUE PHARMACEUTICALS L.P": "Purdue Pharmaceuticals",
    "THE REGENTS OF THE UNIVERSITY OF CALIFORNIA": "University of California",
}

SUGGEST_PUB_COLUMNS = ()  # preserved for BioMCP apply (pipeline.ri_biomcp_publications)


def _inventor_display_name(patent_name: str) -> str:
    """USPTO order LAST FIRST [MIDDLE] → readable lead name."""
    parts = patent_name.strip().split()
    if len(parts) < 2:
        return patent_name.title()
    last = parts[0].replace("-", " ").title()
    rest = " ".join(p.title() for p in parts[1:])
    return f"{rest} {last}".strip()


def _first_specialty(row: dict[str, str]) -> str:
    specs = [s.strip() for s in (row.get("required_specialties") or "").split("|") if s.strip()]
    return specs[0].title() if specs else ""


def _align_lead_from_inventors(row: dict[str, str]) -> bool:
    """Replace placeholder physician leads with first patent inventor."""
    case_id = row.get("case_id", "")
    if case_id in PHYSICIAN_FIXES:
        return False
    lead = (row.get("physician_lead_name") or "").upper()
    if lead and lead not in PLACEHOLDER_LEADS:
        return False
    inventors = [x.strip() for x in (row.get("inventors") or "").split("|") if x.strip()]
    if not inventors:
        return False
    row["physician_lead_name"] = _inventor_display_name(inventors[0])
    if not (row.get("physician_lead_institution") or "").strip():
        row["physician_lead_institution"] = (
            row.get("ri_institution") or row.get("company") or ""
        )
    if not (row.get("physician_lead_specialty") or "").strip():
        row["physician_lead_specialty"] = _first_specialty(row)
    return True


def _fill_lead_metadata(row: dict[str, str]) -> bool:
    changed = False
    if (row.get("physician_lead_name") or "").strip():
        if not (row.get("physician_lead_institution") or "").strip():
            row["physician_lead_institution"] = (
                row.get("ri_institution") or row.get("company") or ""
            )
            changed = True
        if not (row.get("physician_lead_specialty") or "").strip():
            spec = _first_specialty(row)
            if spec:
                row["physician_lead_specialty"] = spec
                changed = True
    return changed


def _fix_indication(row: dict[str, str]) -> bool:
    ind = (row.get("indication") or "").strip()
    if ind != GENERIC_INDICATION:
        return False
    title = (row.get("title_clean") or row.get("display_name") or "").strip()
    if title:
        row["indication"] = title
        return True
    return False


def _fix_clinical_path_notes(row: dict[str, str]) -> bool:
    notes = row.get("clinical_path_notes") or ""
    if "trial template auto-matched" not in notes.lower():
        return False
    row["clinical_path_notes"] = (
        "Clinical path draft — confirm trial design, PI, and NCT fit before approval."
    )
    return True


def _fix_ri_operating_comps(row: dict[str, str]) -> bool:
    changed = False
    for prefix in ("comp1_", "comp2_", "comp3_"):
        if (row.get(f"{prefix}type") or "") == "ri_operating":
            row[f"{prefix}type"] = "incumbent"
            changed = True
    return changed


def _title_case_company(assignee: str) -> str:
    key = assignee.strip().upper()
    if key in ASSIGNEE_TO_RI_INSTITUTION:
        return ASSIGNEE_TO_RI_INSTITUTION[key]
    # Title-case fallback
    return assignee.strip().title()


def _normalize_supporters(value: str) -> str:
    if not value.strip():
        return ""
    lines = []
    for line in value.replace("\r", "").split("\n"):
        line = line.strip()
        if not line:
            continue
        parts = line.split("|")
        if parts and parts[0].startswith("npi_"):
            parts[0] = parts[0][4:]
        lines.append("|".join(parts))
    return "\n".join(lines)


def _infer_company(row: dict[str, str]) -> str:
    existing = (row.get("company") or "").strip()
    if existing and existing.upper() not in {"TBD", "UNKNOWN"}:
        return existing
    assignee = (row.get("assignee_company") or "").strip()
    if assignee:
        return _title_case_company(assignee)
    return existing


def _infer_ri_institution(row: dict[str, str]) -> str:
    existing = (row.get("ri_institution") or "").strip()
    assignee = (row.get("assignee_company") or "").strip().upper()
    if assignee in ASSIGNEE_TO_RI_INSTITUTION:
        return ASSIGNEE_TO_RI_INSTITUTION[assignee]
    # Person name heuristic: no "University", "Hospital", etc.
    if existing and not re.search(
        r"university|hospital|noramco|rhodes|purdue|institute|college",
        existing,
        re.I,
    ):
        mapped = ASSIGNEE_TO_RI_INSTITUTION.get(assignee)
        if mapped:
            return mapped
    return existing or _title_case_company(row.get("assignee_company", ""))


def remediate_row(row: dict[str, str]) -> list[str]:
    changes: list[str] = []
    case_id = row.get("case_id", "")

    if (row.get("catalog_include") or "").lower() == "false":
        row["ri_notes"] = (row.get("ri_notes") or "").strip()
        if "excluded from catalog" not in row["ri_notes"].lower():
            row["ri_notes"] = (row["ri_notes"] + " [excluded from catalog]").strip()

    company = _infer_company(row)
    if company != (row.get("company") or ""):
        row["company"] = company
        changes.append("company")

    ri_inst = _infer_ri_institution(row)
    if ri_inst and ri_inst != (row.get("ri_institution") or ""):
        row["ri_institution"] = ri_inst
        changes.append("ri_institution")

    for col in SUGGEST_PUB_COLUMNS:
        if (row.get(col) or "").strip():
            row[col] = ""
            changes.append(f"cleared:{col}")

    supporters = _normalize_supporters(row.get("physician_supporters") or "")
    if supporters != (row.get("physician_supporters") or ""):
        row["physician_supporters"] = supporters
        changes.append("physician_supporters")

    if case_id in PHYSICIAN_FIXES:
        for k, v in PHYSICIAN_FIXES[case_id].items():
            if row.get(k) != v:
                row[k] = v
                changes.append(k)
    elif _align_lead_from_inventors(row):
        changes.append("physician_lead_from_inventor")
    elif _fill_lead_metadata(row):
        changes.append("physician_lead_metadata")

    if _fix_indication(row):
        changes.append("indication")

    if _fix_clinical_path_notes(row):
        changes.append("clinical_path_notes")

    if _fix_ri_operating_comps(row):
        changes.append("comp_type_ri_operating")

    if case_id in COMP_FIXES:
        for prefix, patch in COMP_FIXES[case_id].items():
            for k, v in patch.items():
                if row.get(k) != v:
                    row[k] = v
                    changes.append(k)

    # Strip npi_ prefix on lead NPI if present
    npi = (row.get("physician_lead_npi") or "").strip()
    if npi.startswith("npi_"):
        row["physician_lead_npi"] = npi[4:]
        changes.append("physician_lead_npi")

    if fill_brown_profile_url(row):
        changes.append("physician_lead_profile_url")

    apply_finance_defaults(row)
    thesis = build_thesis(row)
    if thesis != (row.get("investment_thesis") or ""):
        row["investment_thesis"] = thesis
        changes.append("investment_thesis")

    row["last_refreshed_at"] = date.today().isoformat()
    row["enrichment_status"] = "remediated_web_pass_v2"
    return changes


def remediate(path: Path = CASES_CSV) -> tuple[int, int]:
    rows = load_cases(path)
    touched = 0
    for row in rows:
        if remediate_row(row):
            touched += 1
    write_cases(rows, path)
    return len(rows), touched


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--path", type=Path, default=CASES_CSV)
    args = parser.parse_args()
    total, touched = remediate(args.path)
    print(f"Remediated {touched}/{total} rows -> {args.path}")


if __name__ == "__main__":
    main()
