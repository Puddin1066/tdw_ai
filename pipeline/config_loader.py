"""Load and validate YAML case configuration files."""

from __future__ import annotations

from pathlib import Path
from typing import Any

import yaml

from pipeline.types import (
    CaseConfig,
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


def _validate_case_id(case_id: str) -> None:
    if case_id != case_id.lower() or " " in case_id:
        raise ConfigValidationError("case_id must be lowercase snake_case")


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

    target = TargetConfig(
        name=_require_str(target_raw, "name"),
        canonical_id=target_raw.get("canonical_id"),
        aliases=[str(alias) for alias in target_raw.get("aliases", [])],
    )
    indication = IndicationConfig(
        name=_require_str(indication_raw, "name"),
        aliases=[str(alias) for alias in indication_raw.get("aliases", [])],
    )

    sources = SourcesConfig(
        pubmed=bool(sources_raw.get("pubmed", False)),
        clinicaltrials=bool(sources_raw.get("clinicaltrials", False)),
        opentargets=bool(sources_raw.get("opentargets", False)),
        chembl=bool(sources_raw.get("chembl", False)),
        biothings=bool(sources_raw.get("biothings", False)),
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
        config_path=path,
    )
