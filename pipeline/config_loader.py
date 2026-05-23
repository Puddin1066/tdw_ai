"""Load and validate YAML case configuration files."""

from __future__ import annotations

from pathlib import Path
from typing import Any

import yaml

from pipeline.types import (
    BenchmarkConfig,
    CaseConfig,
    InputBiology,
    InputCommercial,
    InputDisease,
    InputProfile,
    InputProgram,
    IndicationConfig,
    LimitsConfig,
    RunModeDefaults,
    SourcesConfig,
    TargetConfig,
)


class ConfigValidationError(ValueError):
    """Raised when a case config fails validation."""


def _require_mapping(data: dict[str, Any], key: str) -> dict[str, Any]:
    value = data.get(key)
    if not isinstance(value, dict):
        raise ConfigValidationError(f"Missing or invalid mapping: {key}")
    return value


def _require_str(data: dict[str, Any], key: str) -> str:
    value = data.get(key)
    if not isinstance(value, str) or not value.strip():
        raise ConfigValidationError(f"Missing or invalid string: {key}")
    return value.strip()


def _require_positive_int(data: dict[str, Any], key: str) -> int:
    value = data.get(key)
    if not isinstance(value, int) or value <= 0:
        raise ConfigValidationError(f"Expected positive integer for {key}")
    return value


def _optional_str(data: dict[str, Any], key: str) -> str | None:
    value = data.get(key)
    if value is None:
        return None
    text = str(value).strip()
    return text or None


def _str_or_empty(data: dict[str, Any], key: str) -> str:
    value = data.get(key)
    if value is None:
        return ""
    return str(value).strip()


def _optional_str_list(data: dict[str, Any], key: str) -> list[str]:
    value = data.get(key)
    if not isinstance(value, list):
        return []
    out: list[str] = []
    for item in value:
        text = str(item).strip()
        if text:
            out.append(text)
    return out


def _validate_case_id(case_id: str) -> None:
    if case_id != case_id.lower() or " " in case_id:
        raise ConfigValidationError("case_id must be lowercase snake_case")


def summarize_input_quality(config: CaseConfig) -> dict[str, Any]:
    """Compute deterministic input richness metadata for run auditability."""
    preferred_fields: list[str | list[str] | None] = [
        config.input_profile.biology.mechanism_direction,
        config.input_profile.biology.modality,
        config.input_profile.disease.patient_segment,
        config.input_profile.disease.geography,
        config.input_profile.program.asset,
        config.input_profile.program.company,
        config.input_profile.program.development_stage,
        config.input_profile.program.comparators,
        config.input_profile.commercial.strategic_question,
        config.input_profile.commercial.licensing_question,
        config.input_profile.commercial.investment_question,
    ]
    breadth_count = 0
    for value in preferred_fields:
        if isinstance(value, list):
            if any(str(item).strip() for item in value):
                breadth_count += 1
            continue
        if isinstance(value, str) and value.strip():
            breadth_count += 1

    if breadth_count <= 1:
        band = "MINIMAL"
    elif breadth_count <= 3:
        band = "STANDARD"
    elif breadth_count <= 5:
        band = "STRONG"
    else:
        band = "RICH"

    warnings: list[str] = []
    if breadth_count <= 1:
        warnings.append(
            "Low input specificity: add mechanism/modality/segment/stage/commercial fields for better relevance."
        )
    elif breadth_count <= 3:
        warnings.append("Input profile is usable but below preferred richness (target >=4 preferred inputs).")

    biology_or_program_present = any(
        [
            bool(config.input_profile.biology.mechanism_direction),
            bool(config.input_profile.biology.modality),
            bool(config.input_profile.program.asset),
            bool(config.input_profile.program.company),
            bool(config.input_profile.program.development_stage),
        ]
    )
    if breadth_count >= 2 and not biology_or_program_present:
        warnings.append("Add at least one biology/program field to improve translational specificity.")

    if breadth_count >= 4:
        has_commercial = any(
            [
                bool(config.input_profile.commercial.strategic_question),
                bool(config.input_profile.commercial.licensing_question),
                bool(config.input_profile.commercial.investment_question),
            ]
        )
        if not has_commercial:
            warnings.append("Add at least one commercial question for venture/commercial comparability.")

    primary_complete = bool(config.target.name.strip()) and bool(config.indication.name.strip())
    return {
        "input_primary_complete": primary_complete,
        "input_breadth_count": breadth_count,
        "input_quality_band": band,
        "input_quality_warnings": warnings,
        "input_preferred_minimum_met": breadth_count >= 4,
    }


def load_case_config(config_path: Path | str) -> CaseConfig:
    """Load a case YAML config from disk and validate required fields."""
    path = Path(config_path).resolve()
    if not path.exists():
        raise FileNotFoundError(f"Config not found: {path}")

    with path.open(encoding="utf-8") as handle:
        raw = yaml.safe_load(handle)

    if not isinstance(raw, dict):
        raise ConfigValidationError("Case config root must be a mapping")

    case_id = _require_str(raw, "case_id")
    _validate_case_id(case_id)

    workflow = _require_str(raw, "workflow")
    if workflow != "translational_diligence":
        raise ConfigValidationError("workflow must be translational_diligence for MVP")

    target_raw = _require_mapping(raw, "target")
    indication_raw = _require_mapping(raw, "indication")
    sources_raw = _require_mapping(raw, "sources")
    limits_raw = _require_mapping(raw, "limits")
    run_defaults_raw = _require_mapping(raw, "run_mode_defaults")
    biology_raw = raw.get("biology") if isinstance(raw.get("biology"), dict) else {}
    disease_input_raw = raw.get("disease") if isinstance(raw.get("disease"), dict) else {}
    program_raw = raw.get("program") if isinstance(raw.get("program"), dict) else {}
    commercial_raw = raw.get("commercial") if isinstance(raw.get("commercial"), dict) else {}
    benchmark_raw = raw.get("benchmark") if isinstance(raw.get("benchmark"), dict) else {}

    target = TargetConfig(
        name=_str_or_empty(target_raw, "name"),
        canonical_id=target_raw.get("canonical_id"),
        aliases=[str(alias) for alias in target_raw.get("aliases", [])],
    )
    indication = IndicationConfig(
        name=_str_or_empty(indication_raw, "name"),
        aliases=[str(alias) for alias in indication_raw.get("aliases", [])],
    )

    sources = SourcesConfig(
        pubmed=bool(sources_raw.get("pubmed", False)),
        clinicaltrials=bool(sources_raw.get("clinicaltrials", False)),
        opentargets=bool(sources_raw.get("opentargets", False)),
        chembl=bool(sources_raw.get("chembl", False)),
        biothings=bool(sources_raw.get("biothings", False)),
        uniprot=bool(sources_raw.get("uniprot", False)),
        reactome=bool(sources_raw.get("reactome", False)),
        gwas=bool(sources_raw.get("gwas", False)),
        pharmgkb=bool(sources_raw.get("pharmgkb", False)),
        openfda=bool(sources_raw.get("openfda", False)),
        octagon_market=bool(sources_raw.get("octagon_market", False)),
        local_docs=bool(sources_raw.get("local_docs", False)),
    )

    limits = LimitsConfig(
        max_literature_records=_require_positive_int(limits_raw, "max_literature_records"),
        max_trials=_require_positive_int(limits_raw, "max_trials"),
        max_evidence_rows=_require_positive_int(limits_raw, "max_evidence_rows"),
    )

    run_mode_defaults = RunModeDefaults(
        fixture_allowed=bool(run_defaults_raw.get("fixture_allowed", True)),
        live_allowed=bool(run_defaults_raw.get("live_allowed", True)),
    )
    input_profile = InputProfile(
        biology=InputBiology(
            mechanism_direction=_optional_str(biology_raw, "mechanism_direction"),
            modality=_optional_str(biology_raw, "modality"),
            target_alias=_optional_str(biology_raw, "target_alias"),
        ),
        disease=InputDisease(
            patient_segment=_optional_str(disease_input_raw, "patient_segment"),
            geography=_optional_str(disease_input_raw, "geography"),
        ),
        program=InputProgram(
            asset=_optional_str(program_raw, "asset"),
            company=_optional_str(program_raw, "company"),
            development_stage=_optional_str(program_raw, "development_stage"),
            comparators=_optional_str_list(program_raw, "comparators"),
        ),
        commercial=InputCommercial(
            strategic_question=_optional_str(commercial_raw, "strategic_question"),
            licensing_question=_optional_str(commercial_raw, "licensing_question"),
            investment_question=_optional_str(commercial_raw, "investment_question"),
        ),
    )
    benchmark = BenchmarkConfig(
        enabled=bool(benchmark_raw.get("enabled", False)),
        cohort=_optional_str(benchmark_raw, "cohort"),
    )

    return CaseConfig(
        case_id=case_id,
        display_name=_require_str(raw, "display_name"),
        workflow=workflow,
        version=_require_str(raw, "version"),
        target=target,
        indication=indication,
        sources=sources,
        limits=limits,
        run_mode_defaults=run_mode_defaults,
        input_profile=input_profile,
        benchmark=benchmark,
        config_path=path,
    )
