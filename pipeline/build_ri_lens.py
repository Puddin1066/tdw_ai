"""Build static RI clinical-inflection and financing artifacts from normalized CSVs."""

from __future__ import annotations

import csv
import json
from pathlib import Path
from typing import Any

from pipeline.normalize_ri_sources import ensure_normalized_data
from pipeline.physician_assignment import physician_match_for_case
from pipeline.provenance import build_provenance, utc_now_iso
from pipeline.types import SCHEMA_VERSION, CaseConfig, repo_root

DATA_ROOT = repo_root() / "data" / "ri"
OPPORTUNITIES_CSV = DATA_ROOT / "ri_opportunities.csv"
SEED_OPPORTUNITIES_CSV = DATA_ROOT / "ri_physicians_ip_seed.csv"
PHYSICIANS_CSV = DATA_ROOT / "ri_physicians.csv"
TRIAL_TEMPLATES_CSV = DATA_ROOT / "ri_trial_templates.csv"
CAPITAL_SOURCES_CSV = DATA_ROOT / "ri_capital_sources.csv"
LENS_SIGNALS_CSV = DATA_ROOT / "ri_lens_mock_signals.csv"
PHYSICIAN_CANDIDATE_LIMIT = 10


def _read_csv_rows(path: Path) -> list[dict[str, str]]:
    if not path.exists():
        return []
    with path.open(newline="", encoding="utf-8") as handle:
        return list(csv.DictReader(handle))


def _by_case(rows: list[dict[str, str]]) -> dict[str, dict[str, str]]:
    out: dict[str, dict[str, str]] = {}
    for row in rows:
        case_id = (row.get("case_id") or "").strip()
        if case_id:
            out[case_id] = row
    return out


def _to_int(value: str | None, default: int = 0) -> int:
    try:
        return int((value or "").strip())
    except ValueError:
        return default


def _to_float(value: str | None, default: float = 0.0) -> float:
    try:
        return float((value or "").strip())
    except ValueError:
        return default


def _to_bool(value: str | None, default: bool = False) -> bool:
    normalized = (value or "").strip().lower()
    if not normalized:
        return default
    return normalized in {"1", "true", "t", "yes", "y"}


def _pipe_list(value: str | None) -> list[str]:
    return [item.strip() for item in (value or "").split("|") if item.strip()]


SPECIALTY_STOPWORDS = {"medicine", "clinical", "care", "disease", "health", "surgery"}


def _specialty_tokens(value: str) -> set[str]:
    return {
        token
        for token in (value or "").lower().replace("/", " ").replace("-", " ").split()
        if token and token not in SPECIALTY_STOPWORDS
    }


def _specialty_aligned(specialty: str, required_specialties: list[str]) -> bool:
    if not required_specialties:
        return True
    specialty_norm = specialty.strip().lower()
    if not specialty_norm:
        return False
    specialty_tokens = _specialty_tokens(specialty_norm)
    for required in required_specialties:
        req_norm = required.strip().lower()
        if not req_norm:
            continue
        if specialty_norm == req_norm or specialty_norm in req_norm or req_norm in specialty_norm:
            return True
        req_tokens = _specialty_tokens(req_norm)
        if specialty_tokens and req_tokens and specialty_tokens.intersection(req_tokens):
            return True
    return False


def _rows_source_meta(rows: list[dict[str, str]], default_source: str) -> tuple[str, bool]:
    if not rows:
        return default_source, False
    source = (rows[0].get("source_type") or default_source).strip() or default_source
    mocked_values = {(row.get("mocked") or "").strip().lower() for row in rows}
    mocked = mocked_values == {"true"} if mocked_values else False
    return source, mocked


def _artifact_envelope(case_id: str, artifact_type: str, data: dict[str, Any], *, generated_by: str, input_artifacts: list[str]) -> dict[str, Any]:
    return {
        "artifact_type": artifact_type,
        "case_id": case_id,
        "schema_version": SCHEMA_VERSION,
        "generated_at": utc_now_iso(),
        "provenance": build_provenance(generated_by, input_artifacts),
        "data": data,
    }


def _default_opportunity(config: CaseConfig) -> dict[str, str]:
    return {
        "case_id": config.case_id,
        "display_name": config.display_name,
        "opportunity_type": (config.input_profile.program.opportunity_type or "platform"),
        "development_stage": (config.input_profile.program.development_stage or "discovery"),
        "required_roles": "reviewer|advisor",
        "required_specialties": "clinical",
        "target_timeline_weeks": "20",
        "budget_ceiling_usd": "300000",
        "capital_gap_usd": "1000000",
        "ri_institution": "TBD",
        "ri_ip_source": "TBD",
        "ri_notes": "Auto-default from config (no RI CSV row found).",
        "ri_physician_lead": "TBD",
    }


def _build_clinical_inflection(
    *,
    case_id: str,
    opportunity: dict[str, str],
    trial_templates: list[dict[str, str]],
    lens_signal: dict[str, str] | None,
) -> dict[str, Any]:
    opportunity_type = (opportunity.get("opportunity_type") or "platform").strip().lower()
    budget_ceiling = _to_int(opportunity.get("budget_ceiling_usd"), default=0)
    timeline_target = _to_int(opportunity.get("target_timeline_weeks"), default=20)
    required_roles = _pipe_list(opportunity.get("required_roles"))
    required_specialties = _pipe_list(opportunity.get("required_specialties"))

    candidate_templates = [
        row for row in trial_templates if (row.get("opportunity_type") or "").strip().lower() == opportunity_type
    ]

    ranked: list[dict[str, Any]] = []
    for template in candidate_templates:
        duration = _to_int(template.get("duration_weeks"), default=0)
        cost = _to_int(template.get("cost_usd"), default=0)
        weight = _to_float(template.get("expected_inflection_weight_0_1"), default=0.5)
        roles = _pipe_list(template.get("required_roles"))
        specialties = _pipe_list(template.get("required_specialties"))
        role_overlap = len(set(required_roles) & set(roles)) / max(1, len(set(required_roles)))
        specialty_overlap = len(set(required_specialties) & set(specialties)) / max(1, len(set(required_specialties)))
        budget_fit = 1.0 if budget_ceiling <= 0 else max(0.0, min(1.0, (budget_ceiling - cost) / max(1, budget_ceiling)))
        timeline_fit = 1.0 if timeline_target <= 0 else max(0.0, min(1.0, (timeline_target - duration) / max(1, timeline_target)))
        score = (weight * 0.45) + (role_overlap * 0.2) + (specialty_overlap * 0.2) + (budget_fit * 0.1) + (timeline_fit * 0.05)
        ranked.append(
            {
                "template_id": template.get("template_id"),
                "study_type": template.get("study_type"),
                "primary_endpoint_type": template.get("primary_endpoint_type"),
                "duration_weeks": duration,
                "cost_usd": cost,
                "required_roles": roles,
                "required_specialties": specialties,
                "estimated_inflection_score_0_100": round(score * 100, 1),
                "mocked": _to_bool(template.get("mocked"), default=True),
                "source_type": template.get("source_type", "csv_mock"),
            }
        )

    ranked.sort(key=lambda item: item["estimated_inflection_score_0_100"], reverse=True)
    best = ranked[0] if ranked else None
    fallback_score = _to_int(lens_signal.get("ssbci_match_readiness_score_0_100") if lens_signal else None, default=50)
    source_type = best["source_type"] if best else "ri_trial_templates"
    mocked = bool(best["mocked"]) if best else False
    return {
        "clinical_decision_changed": bool(best),
        "clinical_inflection_score_0_100": best["estimated_inflection_score_0_100"] if best else fallback_score,
        "best_validation_event": best,
        "candidate_validation_events": ranked[:4],
        "required_specialties": required_specialties,
        "required_physician_roles": required_roles,
        "estimated_cost_usd": best["cost_usd"] if best else budget_ceiling,
        "estimated_duration_weeks": best["duration_weeks"] if best else timeline_target,
        "financing_milestone": f"De-risk {opportunity_type} via {best['study_type'] if best else 'pilot study'}",
        "source_type": source_type,
        "mocked": mocked,
        "confidence_0_1": 0.74 if best else 0.45,
    }


def _build_physician_match(
    *,
    opportunity: dict[str, str],
    physicians: list[dict[str, str]],
) -> dict[str, Any]:
    required_roles = _pipe_list(opportunity.get("required_roles"))
    required_specialties = _pipe_list(opportunity.get("required_specialties"))
    conflict_tags = set(_pipe_list(opportunity.get("conflict_tags")))

    matches: list[dict[str, Any]] = []
    for physician in physicians:
        specialty = (physician.get("specialty") or "").strip().lower()
        roles = _pipe_list(physician.get("roles_willing"))
        physician_conflicts = set(_pipe_list(physician.get("conflict_tags")))
        if conflict_tags and physician_conflicts and (conflict_tags & physician_conflicts):
            continue
        role_overlap = sorted(set(required_roles) & set(roles))
        if not role_overlap:
            continue
        specialty_match = _specialty_aligned(specialty, required_specialties)
        if not specialty_match:
            continue
        availability = _to_int(physician.get("availability_hours_month"), default=0)
        score = 50 + min(30, availability) + (10 * len(role_overlap))
        matches.append(
            {
                "physician_id": physician.get("physician_id"),
                "name": physician.get("name"),
                "specialty": physician.get("specialty"),
                "institution": physician.get("institution"),
                "roles_matched": role_overlap,
                "availability_hours_month": availability,
                "compensation_floor_usd": _to_int(physician.get("compensation_floor_usd"), default=0),
                "investor_interest_level": physician.get("investor_interest_level", "low"),
                "match_score_0_100": min(100, score),
                "mocked": _to_bool(physician.get("mocked"), default=True),
                "source_type": physician.get("source_type", "csv_mock"),
                "confidence_0_1": _to_float(physician.get("confidence_0_1"), default=0.6),
            }
        )

    matches.sort(key=lambda item: item["match_score_0_100"], reverse=True)
    role_coverage = {
        role: any(role in match["roles_matched"] for match in matches)
        for role in required_roles
    }
    covered_roles = sum(1 for covered in role_coverage.values() if covered)
    role_coverage_ratio = covered_roles / max(1, len(required_roles))
    source_type, mocked = _rows_source_meta(physicians, "ri_physician_roster")
    return {
        "required_roles": required_roles,
        "required_specialties": required_specialties,
        "role_coverage": role_coverage,
        "staffing_feasibility_score_0_100": round(role_coverage_ratio * 100, 1),
        "candidate_physicians": matches[:PHYSICIAN_CANDIDATE_LIMIT],
        "staffing_gaps": [role for role, covered in role_coverage.items() if not covered],
        "source_type": source_type,
        "mocked": mocked,
        "confidence_0_1": 0.72 if matches else 0.35,
    }


def _build_capital_match(
    *,
    opportunity: dict[str, str],
    capital_sources: list[dict[str, str]],
    physician_match: dict[str, Any],
) -> dict[str, Any]:
    capital_gap = _to_int(opportunity.get("capital_gap_usd"), default=0)
    candidate_physicians = physician_match.get("candidate_physicians", [])
    candidate_count = len(candidate_physicians) if isinstance(candidate_physicians, list) else 0
    physician_target = int(capital_gap * 0.5)
    slater_target = max(0, capital_gap - physician_target)
    average_physician_ticket = max(25000, capital_gap // max(8, candidate_count * 2 if candidate_count else 8))
    physician_capacity = min(physician_target, candidate_count * average_physician_ticket)
    slater_capacity = slater_target
    capital_committed = min(capital_gap, physician_capacity + slater_capacity)
    gap_remaining = max(0, capital_gap - capital_committed)
    readiness = 0 if capital_gap <= 0 else round((capital_committed / max(1, capital_gap)) * 100, 1)
    source_type, mocked = _rows_source_meta(capital_sources, "ri_capital_policy")
    by_id = {row.get("source_id", ""): row for row in capital_sources}
    physician_source = by_id.get("cap_physician_50", {})
    slater_source = by_id.get("cap_slater_ssbci_50", {})
    candidates = [
        {
            "source_id": physician_source.get("source_id", "cap_physician_50"),
            "source_name": physician_source.get("source_name", "RI Physician Syndicate (Policy 50%)"),
            "source_type": physician_source.get("source_type", "physician_syndicate"),
            "ri_focus": _to_bool(physician_source.get("ri_focus"), default=True),
            "match_eligible": _to_bool(physician_source.get("match_eligible"), default=True),
            "decision_cycle_weeks": _to_int(physician_source.get("decision_cycle_weeks"), default=6),
            "projected_commitment_usd": physician_capacity,
            "mocked": _to_bool(physician_source.get("mocked"), default=False),
            "source_type_detail": physician_source.get("source_type_detail", "static_policy"),
        },
        {
            "source_id": slater_source.get("source_id", "cap_slater_ssbci_50"),
            "source_name": slater_source.get("source_name", "Slater SSBCI Match (Policy 50%)"),
            "source_type": slater_source.get("source_type", "public_program"),
            "ri_focus": _to_bool(slater_source.get("ri_focus"), default=True),
            "match_eligible": _to_bool(slater_source.get("match_eligible"), default=True),
            "decision_cycle_weeks": _to_int(slater_source.get("decision_cycle_weeks"), default=8),
            "projected_commitment_usd": slater_capacity,
            "mocked": _to_bool(slater_source.get("mocked"), default=False),
            "source_type_detail": slater_source.get("source_type_detail", "static_policy"),
        },
    ]
    return {
        "private_match_needed_usd": capital_gap,
        "capital_committed_usd": capital_committed,
        "capital_gap_remaining_usd": gap_remaining,
        "capital_path_score_0_100": readiness,
        "potential_sources": candidates,
        "source_type": source_type,
        "mocked": mocked,
        "confidence_0_1": 0.76 if candidate_count else 0.52,
    }


def _build_financing_readiness(
    *,
    opportunity: dict[str, str],
    inflection: dict[str, Any],
    physician_match: dict[str, Any],
    capital_match: dict[str, Any],
    lens_signal: dict[str, str] | None,
) -> dict[str, Any]:
    inflection_score = _to_float(str(inflection.get("clinical_inflection_score_0_100", 0)), default=0)
    staffing_score = _to_float(str(physician_match.get("staffing_feasibility_score_0_100", 0)), default=0)
    capital_score = _to_float(str(capital_match.get("capital_path_score_0_100", 0)), default=0)
    ri_anchor = _to_float(lens_signal.get("ri_anchor_score_0_100") if lens_signal else None, default=72)
    overall = round((inflection_score * 0.35) + (staffing_score * 0.25) + (capital_score * 0.25) + (ri_anchor * 0.15), 1)
    if overall >= 75:
        state = "financeable_now"
    elif overall >= 55:
        state = "financeable_post_inflection"
    else:
        state = "not_financeable_yet"
    actions: list[str] = []
    if physician_match.get("staffing_gaps"):
        actions.append(f"Fill physician role gaps: {', '.join(physician_match['staffing_gaps'])}.")
    if capital_match.get("capital_gap_remaining_usd", 0) > 0:
        actions.append("Secure additional private match commitments.")
    actions.append(f"Execute validation plan: {inflection.get('financing_milestone', 'Define milestone')}.")
    actions.append("Refresh scores after first validation data tranche.")
    mocked = bool(inflection.get("mocked") or physician_match.get("mocked") or capital_match.get("mocked"))
    return {
        "financing_readiness_state": state,
        "financing_readiness_score_0_100": overall,
        "clinical_inflection_score_0_100": inflection_score,
        "staffing_feasibility_score_0_100": staffing_score,
        "capital_path_score_0_100": capital_score,
        "ri_anchor_score_0_100": ri_anchor,
        "private_match_needed_usd": capital_match.get("private_match_needed_usd", 0),
        "capital_gap_remaining_usd": capital_match.get("capital_gap_remaining_usd", 0),
        "slater_invested": _to_bool(opportunity.get("slater_invested"), default=False),
        "next_actions": actions[:4],
        "source_type": "derived_static_csv",
        "mocked": mocked,
        "confidence_0_1": 0.75,
    }


def build_ri_lens_artifacts(config: CaseConfig, case_dir: Path) -> list[Path]:
    ensure_normalized_data()
    opportunities = _by_case(_read_csv_rows(OPPORTUNITIES_CSV))
    if not opportunities:
        opportunities = _by_case(_read_csv_rows(SEED_OPPORTUNITIES_CSV))
    lens_signals = _by_case(_read_csv_rows(LENS_SIGNALS_CSV))
    trial_templates = _read_csv_rows(TRIAL_TEMPLATES_CSV)
    capital_sources = _read_csv_rows(CAPITAL_SOURCES_CSV)

    opportunity = opportunities.get(config.case_id, _default_opportunity(config))
    lens_signal = lens_signals.get(config.case_id)
    clinical_inflection = _build_clinical_inflection(
        case_id=config.case_id,
        opportunity=opportunity,
        trial_templates=trial_templates,
        lens_signal=lens_signal,
    )
    physician_match = physician_match_for_case(config.case_id)
    capital_match = _build_capital_match(
        opportunity=opportunity,
        capital_sources=capital_sources,
        physician_match=physician_match,
    )
    financing_readiness = _build_financing_readiness(
        opportunity=opportunity,
        inflection=clinical_inflection,
        physician_match=physician_match,
        capital_match=capital_match,
        lens_signal=lens_signal,
    )

    outputs = {
        "ri_clinical_inflection.json": _artifact_envelope(
            config.case_id,
            "ri_clinical_inflection",
            clinical_inflection,
            generated_by="pipeline/build_ri_lens.py",
            input_artifacts=[
                "data/ri/ri_opportunities.csv",
                "data/ri/ri_trial_templates.csv",
            ],
        ),
        "ri_physician_match.json": _artifact_envelope(
            config.case_id,
            "ri_physician_match",
            physician_match,
            generated_by="pipeline/build_ri_lens.py",
            input_artifacts=[
                "data/ri/ri_opportunities.csv",
                "data/ri/ri_physicians.csv",
            ],
        ),
        "ri_capital_match.json": _artifact_envelope(
            config.case_id,
            "ri_capital_match",
            capital_match,
            generated_by="pipeline/build_ri_lens.py",
            input_artifacts=[
                "data/ri/ri_opportunities.csv",
                "data/ri/ri_capital_sources.csv",
            ],
        ),
        "ri_financing_readiness.json": _artifact_envelope(
            config.case_id,
            "ri_financing_readiness",
            financing_readiness,
            generated_by="pipeline/build_ri_lens.py",
            input_artifacts=[
                "ri_clinical_inflection.json",
                "ri_physician_match.json",
                "ri_capital_match.json",
            ],
        ),
    }

    written: list[Path] = []
    for file_name, payload in outputs.items():
        output_path = case_dir / file_name
        output_path.write_text(json.dumps(payload, indent=2) + "\n", encoding="utf-8")
        written.append(output_path)
    return written
