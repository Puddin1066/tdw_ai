"""Global physician–opportunity assignment with clinical-tag relevance and capacity caps."""

from __future__ import annotations

import csv
import re
from dataclasses import dataclass
from functools import lru_cache
from pathlib import Path
from typing import Any

from pipeline.types import repo_root

DATA_ROOT = repo_root() / "data" / "ri"
OPPORTUNITIES_CSV = DATA_ROOT / "ri_opportunities.csv"
PHYSICIANS_CSV = DATA_ROOT / "ri_physicians.csv"
IP_ASSETS_CSV = DATA_ROOT / "ri_ip_assets.csv"

MAX_PHYSICIANS_PER_OPPORTUNITY = 10
MAX_OPPORTUNITIES_PER_PHYSICIAN = 10

# Seeded overrides for known RI opportunities (clinical framing > generic oncology).
OPPORTUNITY_TAG_OVERRIDES: dict[str, dict[str, str]] = {
    "theromics_ri": {
        "clinical_tags": (
            "thermal_ablation|interventional_radiology|surgical_oncology|"
            "radiation_oncology|tumor_ablation"
        ),
        "required_specialties": (
            "interventional radiology|surgical oncology|radiation oncology|medical oncology"
        ),
        "indication": "thermal tumor ablation and accelerated local drug delivery",
    },
    "monaghan_sepsis_diagnostic_ri": {
        "clinical_tags": "sepsis|critical_care|infectious_disease|emergency_medicine|diagnostic",
        "required_specialties": "critical care|infectious disease|emergency medicine",
    },
    "cbt_pain_digital_platform_ri": {
        "clinical_tags": "chronic_pain|pain_medicine|behavioral_health|digital_therapeutic",
        "required_specialties": "pain medicine|behavioral health|primary care",
    },
    "nanode_ri": {
        "clinical_tags": "nucleic_acid_delivery|medical_oncology|clinical_pharmacology|biomedical_engineering",
        "required_specialties": "medical oncology|clinical pharmacology|biomedical engineering",
        "indication": "Janus nucleotide and Nanopieces delivery",
    },
    "phlip_therapeutics_ri": {
        "clinical_tags": "diagnostic|interventional_radiology|oncology|pathology|imaging",
        "required_specialties": "oncology|interventional radiology|pathology",
        "indication": "tumor imaging and diseased tissue detection",
    },
    "prothera_iaip_ri": {
        "clinical_tags": "sepsis|critical_care|infectious_disease|neonatology|therapeutic",
        "required_specialties": "critical care|infectious disease|neonatology|emergency medicine",
        "indication": "early sepsis and critical illness — IAIP biologic therapeutic",
    },
    "mindimmune_therapeutics_ri": {
        "clinical_tags": "neurology|alzheimer|neuroimmunology|therapeutic",
        "required_specialties": "neurology|geriatric psychiatry|memory disorders",
        "indication": "Alzheimer's disease — peripheral neuroimmune blockade (MITI-101)",
    },
    "auto_rhode_island_activity_brain_detecting_pain_using": {
        "clinical_tags": "chronic_pain|pain_medicine|neurology|medical_device",
        "required_specialties": "pain medicine|neurology|physical medicine and rehabilitation",
        "indication": "brain- and spinal-cord–guided pain detection and neuromodulation (Saab cluster)",
    },
}

# NPPES specialty string -> clinical tags (no bare "oncology" — use sub-disciplines).
SPECIALTY_TAG_MAP: list[tuple[tuple[str, ...], list[str]]] = [
    (("interventional radiology", "vascular radiology"), ["interventional_radiology", "thermal_ablation", "tumor_ablation"]),
    (("radiation oncology",), ["radiation_oncology", "thermal_ablation", "tumor_ablation"]),
    (("surgical oncology",), ["surgical_oncology", "tumor_ablation"]),
    (("hematology/oncology", "hematology oncology"), ["hematology_oncology", "medical_oncology"]),
    (("medical oncology",), ["medical_oncology"]),
    (("pathology", "anatomic pathology"), ["pathology"]),
    (("critical care", "intensive care"), ["critical_care"]),
    (("infectious disease",), ["infectious_disease"]),
    (("emergency medicine",), ["emergency_medicine"]),
    (("pain medicine",), ["pain_medicine"]),
    (("behavioral health", "psychiatry"), ["behavioral_health"]),
    (("primary care", "family medicine", "internal medicine"), ["primary_care"]),
    (("biomedical engineering",), ["biomedical_engineering"]),
    (("hospital medicine",), ["hospital_medicine"]),
    (("cardiology", "cardiovascular"), ["cardiology"]),
    (("neurology",), ["neurology"]),
    (("orthopedic",), ["orthopedics"]),
    (("urology",), ["urology"]),
    (("dermatology",), ["dermatology"]),
    (("anesthesiology",), ["anesthesiology"]),
    (("diagnostic radiology",), ["diagnostic_radiology", "interventional_radiology"]),
]

OPPORTUNITY_TYPE_DEFAULT_TAGS: dict[str, list[str]] = {
    "diagnostic": ["diagnostic", "pathology", "critical_care", "infectious_disease"],
    "digital_therapeutic": ["digital_therapeutic", "pain_medicine", "behavioral_health", "primary_care"],
    "medical_device": ["medical_device", "critical_care", "hospital_medicine", "biomedical_engineering"],
    "therapeutic": ["medical_oncology", "clinical_pharmacology", "hospital_medicine"],
    "platform": ["medical_oncology", "pathology"],  # narrow fallback; patents should refine
}


def _read_csv(path: Path) -> list[dict[str, str]]:
    if not path.exists():
        return []
    with path.open(newline="", encoding="utf-8") as handle:
        return list(csv.DictReader(handle))


def _pipe_list(value: str | None) -> list[str]:
    return [item.strip() for item in (value or "").replace(",", "|").split("|") if item.strip()]


def _pipe_join(items: list[str]) -> str:
    return "|".join(dict.fromkeys(item for item in items if item))


def _to_int(value: str | None, default: int = 0) -> int:
    try:
        return int((value or "").strip())
    except ValueError:
        return default


def _to_bool(value: str | None, default: bool = False) -> bool:
    normalized = (value or "").strip().lower()
    if not normalized:
        return default
    return normalized in {"1", "true", "t", "yes", "y"}


def _normalize_tag(tag: str) -> str:
    return re.sub(r"[^a-z0-9]+", "_", tag.strip().lower()).strip("_")


def _tags_from_pipe(value: str | None) -> set[str]:
    return {_normalize_tag(t) for t in _pipe_list(value) if _normalize_tag(t)}


def physician_clinical_tags(specialty: str) -> set[str]:
    s = (specialty or "").strip().lower()
    tags: set[str] = set()
    for needles, mapped in SPECIALTY_TAG_MAP:
        if any(needle in s for needle in needles):
            tags.update(_normalize_tag(t) for t in mapped)
    return tags


def infer_clinical_tags_from_patent_text(*texts: str) -> set[str]:
    blob = " ".join(texts).lower()
    tags: set[str] = set()
    if not blob.strip():
        return tags

    if any(
        token in blob
        for token in (
            "a61b18",
            "thermal",
            "ablat",
            "radiofrequency",
            "microwave",
            "hypertherm",
            "cryoablat",
            "tumor ablat",
        )
    ):
        tags.update(
            {
                "thermal_ablation",
                "tumor_ablation",
                "interventional_radiology",
                "radiation_oncology",
                "surgical_oncology",
            }
        )
    if any(token in blob for token in ("interventional", "catheter", "image-guided")):
        tags.add("interventional_radiology")
    if any(token in blob for token in ("sepsis", "septic", "bacteremia")):
        tags.update({"sepsis", "critical_care", "infectious_disease"})
    if any(token in blob for token in ("pain", "analgesic", "opioid")):
        tags.update({"pain_medicine", "chronic_pain"})
    if any(token in blob for token in ("diagnostic", "biomarker", "assay", "detection")):
        tags.update({"diagnostic", "pathology"})
    if any(token in blob for token in ("implant", "prosthetic", "device", "electrode", "sensor")):
        tags.add("medical_device")
    if any(token in blob for token in ("vaccine", "antibody", "compound", "therapeutic", "drug delivery")):
        tags.update({"medical_oncology", "clinical_pharmacology"})
    if "a61p35" in blob or ("oncology" in blob and "tumor" in blob):
        tags.add("medical_oncology")
    return tags


def opportunity_clinical_tags(
    opportunity: dict[str, str],
    patent_rows: list[dict[str, str]] | None = None,
) -> set[str]:
    case_id = (opportunity.get("case_id") or "").strip()
    override = OPPORTUNITY_TAG_OVERRIDES.get(case_id, {})
    if override.get("clinical_tags"):
        return _tags_from_pipe(override["clinical_tags"])

    explicit = _tags_from_pipe(opportunity.get("clinical_tags"))
    if explicit:
        return explicit

    tags: set[str] = set()
    for row in patent_rows or []:
        tags |= infer_clinical_tags_from_patent_text(
            row.get("title", ""),
            row.get("cpc_classifications", ""),
            row.get("ipcr_classifications", ""),
            row.get("display_key", ""),
        )
    tags |= infer_clinical_tags_from_patent_text(
        opportunity.get("target", ""),
        opportunity.get("indication", ""),
        opportunity.get("display_name", ""),
        opportunity.get("llm_inferred_label", ""),
    )
    if not tags:
        opp_type = (opportunity.get("opportunity_type") or "platform").strip().lower()
        tags = {_normalize_tag(t) for t in OPPORTUNITY_TYPE_DEFAULT_TAGS.get(opp_type, ["hospital_medicine"])}
    return tags


def _specialty_display_aligned(physician_specialty: str, required_specialties: list[str]) -> bool:
    """Require explicit specialty phrase overlap (stricter than token 'oncology')."""
    if not required_specialties:
        return True
    spec = physician_specialty.strip().lower()
    if not spec:
        return False
    for required in required_specialties:
        req = required.strip().lower()
        if not req:
            continue
        if spec == req or req in spec or spec in req:
            return True
    return False


def tags_overlap(physician_tags: set[str], opportunity_tags: set[str]) -> tuple[bool, list[str]]:
    if not opportunity_tags:
        return True, []
    overlap = sorted(physician_tags & opportunity_tags)
    return (len(overlap) > 0, overlap)


@dataclass(frozen=True)
class PairCandidate:
    case_id: str
    physician_id: str
    score: float
    match: dict[str, Any]


def _score_pair(
    *,
    opportunity: dict[str, str],
    physician: dict[str, str],
    opportunity_tags: set[str],
    physician_tags: set[str],
    overlap_tags: list[str],
) -> float | None:
    required_roles = _pipe_list(opportunity.get("required_roles"))
    roles = _pipe_list(physician.get("roles_willing"))
    conflict_tags = set(_pipe_list(opportunity.get("conflict_tags")))
    physician_conflicts = set(_pipe_list(physician.get("conflict_tags")))
    if conflict_tags and physician_conflicts and (conflict_tags & physician_conflicts):
        return None

    role_overlap = sorted(set(required_roles) & set(roles))
    if not role_overlap:
        return None

    aligned, _ = tags_overlap(physician_tags, opportunity_tags)
    if not aligned:
        return None

    required_specialties = _pipe_list(
        OPPORTUNITY_TAG_OVERRIDES.get(opportunity.get("case_id", ""), {}).get("required_specialties")
        or opportunity.get("required_specialties")
    )
    if required_specialties and not _specialty_display_aligned(physician.get("specialty", ""), required_specialties):
        return None

    availability = _to_int(physician.get("availability_hours_month"), default=0)
    score = 40.0 + min(25, availability) + (12 * len(role_overlap)) + (8 * len(overlap_tags))
    # Prefer stronger tag overlap and more specific matches.
    score += 5 * len(overlap_tags)
    if "thermal_ablation" in overlap_tags or "tumor_ablation" in overlap_tags:
        score += 10
    return score


def _build_pair_candidate(
    *,
    case_id: str,
    opportunity: dict[str, str],
    physician: dict[str, str],
    opportunity_tags: set[str],
    physician_tags: set[str],
    overlap_tags: list[str],
    score: float,
) -> PairCandidate:
    required_roles = _pipe_list(opportunity.get("required_roles"))
    roles = _pipe_list(physician.get("roles_willing"))
    role_overlap = sorted(set(required_roles) & set(roles))
    availability = _to_int(physician.get("availability_hours_month"), default=0)
    match = {
        "physician_id": physician.get("physician_id"),
        "name": physician.get("name"),
        "specialty": physician.get("specialty"),
        "institution": physician.get("institution"),
        "roles_matched": role_overlap,
        "clinical_tags_matched": overlap_tags,
        "relevance_rationale": (
            f"Clinical fit: {', '.join(overlap_tags)}"
            if overlap_tags
            else "Clinical fit: role overlap only"
        ),
        "availability_hours_month": availability,
        "compensation_floor_usd": _to_int(physician.get("compensation_floor_usd"), default=0),
        "investor_interest_level": physician.get("investor_interest_level", "low"),
        "match_score_0_100": min(100, round(score)),
        "mocked": _to_bool(physician.get("mocked"), default=True),
        "source_type": physician.get("source_type", "csv_mock"),
        "confidence_0_1": float(physician.get("confidence_0_1") or 0.6),
    }
    return PairCandidate(
        case_id=case_id,
        physician_id=str(physician.get("physician_id", "")),
        score=score,
        match=match,
    )


def compute_global_assignments(
    opportunities: dict[str, dict[str, str]],
    physicians: list[dict[str, str]],
    ip_by_case: dict[str, list[dict[str, str]]],
) -> dict[str, dict[str, Any]]:
    """Assign physicians to opportunities with max caps on both sides."""
    candidates: list[PairCandidate] = []

    for case_id, opportunity in opportunities.items():
        opp_tags = opportunity_clinical_tags(opportunity, ip_by_case.get(case_id))
        for physician in physicians:
            phy_tags = _tags_from_pipe(physician.get("clinical_tags")) or physician_clinical_tags(
                physician.get("specialty", "")
            )
            overlap_ok, overlap_tags = tags_overlap(phy_tags, opp_tags)
            if not overlap_ok:
                continue
            score = _score_pair(
                opportunity=opportunity,
                physician=physician,
                opportunity_tags=opp_tags,
                physician_tags=phy_tags,
                overlap_tags=overlap_tags,
            )
            if score is None:
                continue
            candidates.append(
                _build_pair_candidate(
                    case_id=case_id,
                    opportunity=opportunity,
                    physician=physician,
                    opportunity_tags=opp_tags,
                    physician_tags=phy_tags,
                    overlap_tags=overlap_tags,
                    score=score,
                )
            )

    candidates.sort(key=lambda item: (-item.score, item.case_id, item.physician_id))

    opp_matches: dict[str, list[dict[str, Any]]] = {cid: [] for cid in opportunities}
    physician_opp_count: dict[str, int] = {}

    for candidate in candidates:
        if len(opp_matches[candidate.case_id]) >= MAX_PHYSICIANS_PER_OPPORTUNITY:
            continue
        if physician_opp_count.get(candidate.physician_id, 0) >= MAX_OPPORTUNITIES_PER_PHYSICIAN:
            continue
        opp_matches[candidate.case_id].append(candidate.match)
        physician_opp_count[candidate.physician_id] = physician_opp_count.get(candidate.physician_id, 0) + 1

    results: dict[str, dict[str, Any]] = {}
    for case_id, opportunity in opportunities.items():
        matches = opp_matches.get(case_id, [])
        required_roles = _pipe_list(opportunity.get("required_roles"))
        required_specialties = _pipe_list(opportunity.get("required_specialties"))
        opp_tags = opportunity_clinical_tags(opportunity, ip_by_case.get(case_id))
        role_coverage = {
            role: any(role in match["roles_matched"] for match in matches) for role in required_roles
        }
        covered_roles = sum(1 for covered in role_coverage.values() if covered)
        role_coverage_ratio = covered_roles / max(1, len(required_roles))
        results[case_id] = {
            "required_roles": required_roles,
            "required_specialties": required_specialties,
            "required_clinical_tags": sorted(opp_tags),
            "role_coverage": role_coverage,
            "staffing_feasibility_score_0_100": round(role_coverage_ratio * 100, 1),
            "candidate_physicians": matches[:MAX_PHYSICIANS_PER_OPPORTUNITY],
            "staffing_gaps": [role for role, covered in role_coverage.items() if not covered],
            "source_type": "cms_nppes_csv",
            "mocked": False,
            "confidence_0_1": 0.78 if matches else 0.35,
            "assignment_policy": {
                "max_physicians_per_opportunity": MAX_PHYSICIANS_PER_OPPORTUNITY,
                "max_opportunities_per_physician": MAX_OPPORTUNITIES_PER_PHYSICIAN,
                "matching": "clinical_tag_overlap_with_global_caps",
            },
        }
    return results


DEFAULT_REQUIRED_ROLES = "reviewer|advisor|pilot_designer|investigator"


def opportunity_from_enriched_row(row: dict[str, str]) -> dict[str, str]:
    """Map ri_cases_enriched.csv row to physician_assignment opportunity shape."""
    return {
        "case_id": (row.get("case_id") or "").strip(),
        "display_name": (row.get("display_name") or row.get("title_clean") or "").strip(),
        "target": (row.get("title_clean") or row.get("display_name") or "").strip(),
        "indication": (row.get("indication") or "").strip(),
        "opportunity_type": (row.get("opportunity_type") or "platform").strip(),
        "required_roles": (row.get("required_roles") or DEFAULT_REQUIRED_ROLES).strip(),
        "required_specialties": (row.get("required_specialties") or "").strip(),
        "clinical_tags": (row.get("clinical_tags") or "").strip(),
        "conflict_tags": (row.get("conflict_tags") or "").strip(),
        "llm_inferred_label": (row.get("title_clean") or "").strip(),
    }


def _load_opportunities_lookup() -> dict[str, dict[str, str]]:
    rows = _read_csv(OPPORTUNITIES_CSV)
    return {(row.get("case_id") or "").strip(): row for row in rows if (row.get("case_id") or "").strip()}


def _merge_opportunity_baseline(enriched: dict[str, str], baseline: dict[str, str] | None) -> dict[str, str]:
    """Prefer enriched values; fill required_roles/specialties from ri_opportunities.csv when empty."""
    out = opportunity_from_enriched_row(enriched)
    if not baseline:
        return out
    for key in (
        "required_roles",
        "required_specialties",
        "clinical_tags",
        "conflict_tags",
        "target",
        "display_name",
    ):
        if not (out.get(key) or "").strip() and (baseline.get(key) or "").strip():
            out[key] = baseline[key].strip()
    return out


def load_ip_by_case() -> dict[str, list[dict[str, str]]]:
    by_case: dict[str, list[dict[str, str]]] = {}
    for row in _read_csv(IP_ASSETS_CSV):
        cid = (row.get("case_id") or "").strip()
        if cid:
            by_case.setdefault(cid, []).append(row)
    return by_case


def compute_assignments_for_enriched_rows(
    rows: list[dict[str, str]],
    *,
    catalog_only: bool = True,
) -> dict[str, dict[str, Any]]:
    """Run global physician assignment from monolithic enriched CSV rows."""
    physicians = _read_csv(PHYSICIANS_CSV)
    ip_by_case = load_ip_by_case()
    baseline_by = _load_opportunities_lookup()
    opportunities: dict[str, dict[str, str]] = {}
    for row in rows:
        if catalog_only and not _to_bool(row.get("catalog_include"), default=True):
            continue
        cid = (row.get("case_id") or "").strip()
        if not cid:
            continue
        merged = _merge_opportunity_baseline(row, baseline_by.get(cid))
        merged = enrich_opportunity_row(merged, ip_by_case.get(cid))
        opportunities[cid] = merged
    return compute_global_assignments(opportunities, physicians, ip_by_case)


def physician_match_for_enriched_row(
    row: dict[str, str],
    assignments: dict[str, dict[str, Any]] | None = None,
) -> dict[str, Any]:
    """Physician match bundle for one enriched catalog row."""
    cid = (row.get("case_id") or "").strip()
    if assignments is not None:
        return assignments.get(cid) or physician_match_for_case(cid)
    # Fallback: single-case compute (slower; used in tests).
    single = compute_assignments_for_enriched_rows([row], catalog_only=False)
    return single.get(cid) or physician_match_for_case(cid)


def clear_assignment_cache() -> None:
    load_global_physician_assignments.cache_clear()


@lru_cache(maxsize=1)
def load_global_physician_assignments() -> dict[str, dict[str, Any]]:
    opportunities_rows = _read_csv(OPPORTUNITIES_CSV)
    physicians = _read_csv(PHYSICIANS_CSV)
    ip_rows = _read_csv(IP_ASSETS_CSV)
    opportunities = {
        (row.get("case_id") or "").strip(): row for row in opportunities_rows if (row.get("case_id") or "").strip()
    }
    ip_by_case: dict[str, list[dict[str, str]]] = {}
    for row in ip_rows:
        cid = (row.get("case_id") or "").strip()
        if cid:
            ip_by_case.setdefault(cid, []).append(row)
    return compute_global_assignments(opportunities, physicians, ip_by_case)


def physician_match_for_case(case_id: str) -> dict[str, Any]:
    return load_global_physician_assignments().get(
        case_id,
        {
            "required_roles": [],
            "required_specialties": [],
            "required_clinical_tags": [],
            "role_coverage": {},
            "staffing_feasibility_score_0_100": 0.0,
            "candidate_physicians": [],
            "staffing_gaps": [],
            "source_type": "cms_nppes_csv",
            "mocked": False,
            "confidence_0_1": 0.35,
            "assignment_policy": {
                "max_physicians_per_opportunity": MAX_PHYSICIANS_PER_OPPORTUNITY,
                "max_opportunities_per_physician": MAX_OPPORTUNITIES_PER_PHYSICIAN,
                "matching": "clinical_tag_overlap_with_global_caps",
            },
        },
    )


def enrich_physician_row(row: dict[str, str]) -> dict[str, str]:
    """Add clinical_tags column value for ri_physicians.csv."""
    tags = physician_clinical_tags(row.get("specialty", ""))
    row = dict(row)
    row["clinical_tags"] = _pipe_join(sorted(tags))
    return row


def enrich_opportunity_row(
    row: dict[str, str],
    patent_rows: list[dict[str, str]] | None = None,
) -> dict[str, str]:
    """Add/update clinical_tags and apply seeded overrides."""
    row = dict(row)
    case_id = (row.get("case_id") or "").strip()
    override = OPPORTUNITY_TAG_OVERRIDES.get(case_id, {})
    for key, value in override.items():
        if value:
            row[key] = value
    tags = opportunity_clinical_tags(row, patent_rows)
    row["clinical_tags"] = _pipe_join(sorted(tags))
    return row
