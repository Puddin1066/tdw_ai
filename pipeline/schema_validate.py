"""JSON Schema validation for generated artifacts."""

from __future__ import annotations

import json
from functools import lru_cache
from pathlib import Path
from typing import Any

from jsonschema import Draft202012Validator
from referencing import Registry, Resource

from pipeline.types import repo_root

SCHEMAS_DIR = repo_root() / "schemas"

ARTIFACT_SCHEMA_FILES: dict[str, str] = {
    "source_manifest.json": "source_manifest.schema.json",
    "normalized_entities.json": "normalized_entities.schema.json",
    "literature_records.json": "literature_records.schema.json",
    "clinical_trials.json": "clinical_trials.schema.json",
    "target_biology.json": "target_biology.schema.json",
    "evidence_table.json": "evidence_table.schema.json",
    "diligence_report.json": "diligence_report.schema.json",
    "risk_map.json": "risk_map.schema.json",
    "knowledge_graph.json": "knowledge_graph.schema.json",
    "eval_results.json": "eval_results.schema.json",
    "ri_clinical_inflection.json": "ri_clinical_inflection.schema.json",
    "ri_physician_match.json": "ri_physician_match.schema.json",
    "ri_capital_match.json": "ri_capital_match.schema.json",
    "ri_financing_readiness.json": "ri_financing_readiness.schema.json",
}


@lru_cache(maxsize=1)
def _registry() -> Registry:
    resources: list[tuple[str, Resource]] = []
    for path in sorted(SCHEMAS_DIR.glob("*.json")):
        contents = json.loads(path.read_text(encoding="utf-8"))
        resource_id = contents.get("$id") or path.name
        resources.append((resource_id, Resource.from_contents(contents)))
    return Registry().with_resources(resources)


def validator_for_schema_file(schema_file: str) -> Draft202012Validator:
    schema_path = SCHEMAS_DIR / schema_file
    schema = json.loads(schema_path.read_text(encoding="utf-8"))
    return Draft202012Validator(schema, registry=_registry())


def validate_artifact_file(path: Path) -> list[str]:
    """Validate one artifact JSON file; return list of error messages."""
    if path.name not in ARTIFACT_SCHEMA_FILES:
        return []
    payload = json.loads(path.read_text(encoding="utf-8"))
    validator = validator_for_schema_file(ARTIFACT_SCHEMA_FILES[path.name])
    errors = sorted(validator.iter_errors(payload), key=lambda e: list(e.path))
    return [f"{path.name}: {err.message} at {list(err.path)}" for err in errors]


def validate_case_dir(case_dir: Path) -> list[str]:
    messages: list[str] = []
    for name in ARTIFACT_SCHEMA_FILES:
        path = case_dir / name
        if path.is_file():
            messages.extend(validate_artifact_file(path))
    return messages
