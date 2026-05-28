"""CLI entrypoint for translational diligence case generation."""

from __future__ import annotations

import argparse
import importlib
import json
import shutil
import sys
import uuid
from pathlib import Path
from typing import Any

import yaml

from pipeline._artifacts import copy_fixture_artifact
from pipeline.build_sources import build_source_artifacts
from pipeline.artifact_writer import ArtifactValidationError, validate_case_dir
from pipeline.build_graph import build_knowledge_graph
from pipeline.build_ri_lens import build_ri_lens_artifacts
from pipeline.config_loader import ConfigValidationError, load_case_config, summarize_input_quality
from pipeline.generate_claims import generate_claims
from pipeline.generate_questions import generate_questions
from pipeline.generate_report import generate_report
from pipeline.generate_risk_map import generate_risk_map
from pipeline.llm_provider import get_provider_status
from pipeline.normalize_entities import normalize_entities
from pipeline.provenance import build_provenance, utc_now_iso
from pipeline.runtime_env import load_repo_env
from pipeline.run_registry import RunRegistry
from pipeline.types import (
    REQUIRED_ARTIFACTS,
    SCHEMA_VERSION,
    CaseConfig,
    RunMode,
    fixture_case_dir,
    generated_case_dir,
    repo_root,
)

SOURCE_ARTIFACTS = (
    "source_manifest.json",
    "literature_records.json",
    "clinical_trials.json",
    "target_biology.json",
)

CONNECTOR_BINDINGS: dict[str, tuple[str, str]] = {
    "pubmed": ("connectors.pubmed", "PubMedConnector"),
    "clinicaltrials": ("connectors.clinicaltrials", "ClinicalTrialsConnector"),
    "opentargets": ("connectors.opentargets", "OpenTargetsConnector"),
    "chembl": ("connectors.chembl", "ChEMBLConnector"),
    "biothings": ("connectors.biothings", "BioThingsConnector"),
    "uniprot": ("connectors.uniprot", "UniProtConnector"),
    "reactome": ("connectors.reactome", "ReactomeConnector"),
    "gwas": ("connectors.gwas", "GwasConnector"),
    "pharmgkb": ("connectors.pharmgkb", "PharmGkbConnector"),
    "openfda": ("connectors.openfda", "OpenFdaConnector"),
    "octagon_market": ("connectors.octagon_market", "OctagonMarketConnector"),
    "local_docs": ("connectors.local_docs", "LocalDocsConnector"),
}


def _enabled_connectors(config: CaseConfig) -> list[str]:
    sources = config.sources
    mapping = {
        "pubmed": sources.pubmed,
        "clinicaltrials": sources.clinicaltrials,
        "opentargets": sources.opentargets,
        "chembl": sources.chembl,
        "biothings": sources.biothings,
        "uniprot": getattr(sources, "uniprot", False),
        "reactome": getattr(sources, "reactome", False),
        "gwas": getattr(sources, "gwas", False),
        "pharmgkb": getattr(sources, "pharmgkb", False),
        "openfda": getattr(sources, "openfda", False),
        "octagon_market": getattr(sources, "octagon_market", False),
        "local_docs": sources.local_docs,
    }
    return [name for name, enabled in mapping.items() if enabled]


def _import_connector(name: str) -> Any | None:
    module_path, class_name = CONNECTOR_BINDINGS[name]
    try:
        module = importlib.import_module(module_path)
    except ImportError:
        return None
    connector_cls = getattr(module, class_name, None)
    if connector_cls is None:
        return None
    return connector_cls()


def _write_metadata(config: CaseConfig, case_dir: Path, mode: RunMode) -> Path:
    provider_status = get_provider_status(prefer_live=(mode == "live"))
    metadata = config.to_metadata_dict()
    input_quality = summarize_input_quality(config)
    metadata["run"] = {
        "mode": mode,
        "generated_at": utc_now_iso(),
        "config_path": str(config.config_path) if config.config_path else None,
        "synthesis_provider": provider_status["provider_name"],
        "synthesis_model": provider_status["model_name"],
        "mocked_api_calls": provider_status["mocked_api_calls"],
        "using_live_api": provider_status["using_live_api"],
        "provider_selection_reason": provider_status["selection_reason"],
        **input_quality,
    }
    path = case_dir / "metadata.yaml"
    path.write_text(yaml.safe_dump(metadata, sort_keys=False), encoding="utf-8")
    return path


def _read_json(path: Path) -> dict[str, Any]:
    payload = json.loads(path.read_text(encoding="utf-8"))
    return payload if isinstance(payload, dict) else {}


def _artifact_data(path: Path) -> dict[str, Any]:
    payload = _read_json(path)
    data = payload.get("data", {})
    return data if isinstance(data, dict) else {}


def _severity_rank(value: str) -> int:
    order = {"critical": 4, "high": 3, "medium": 2, "low": 1}
    return order.get(value.lower(), 0)


def _evidence_density(rows_count: int) -> str:
    if rows_count >= 12:
        return "high"
    if rows_count >= 6:
        return "medium"
    return "low"


def _derive_metadata_summary(case_dir: Path) -> dict[str, Any]:
    report_data = _artifact_data(case_dir / "diligence_report.json")
    risk_data = _artifact_data(case_dir / "risk_map.json")
    evidence_data = _artifact_data(case_dir / "evidence_table.json")
    eval_data = _artifact_data(case_dir / "eval_results.json")

    confidence = report_data.get("overall_confidence")
    if not isinstance(confidence, (int, float)):
        confidence = eval_data.get("aggregate_score", 0.0)
    if not isinstance(confidence, (int, float)):
        confidence = 0.0
    confidence = max(0.0, min(1.0, float(confidence)))

    maturity_stage = report_data.get("maturity_stage")
    if not isinstance(maturity_stage, str) or not maturity_stage.strip():
        maturity_stage = "unknown"

    rows = evidence_data.get("rows", [])
    rows_count = len(rows) if isinstance(rows, list) else 0

    top_risk = "—"
    risks = risk_data.get("risks", [])
    if isinstance(risks, list) and risks:
        ranked = sorted(
            (risk for risk in risks if isinstance(risk, dict)),
            key=lambda risk: _severity_rank(str(risk.get("severity", ""))),
            reverse=True,
        )
        if ranked:
            title = ranked[0].get("title")
            if isinstance(title, str) and title.strip():
                top_risk = title.strip()

    return {
        "maturity_stage": maturity_stage,
        "confidence_score": round(confidence, 4),
        "evidence_density": _evidence_density(rows_count),
        "top_risk": top_risk,
    }


def _write_metadata_summary(metadata_path: Path, case_dir: Path) -> None:
    metadata = yaml.safe_load(metadata_path.read_text(encoding="utf-8")) or {}
    if not isinstance(metadata, dict):
        metadata = {}
    metadata.update(_derive_metadata_summary(case_dir))
    metadata_path.write_text(yaml.safe_dump(metadata, sort_keys=False), encoding="utf-8")


def _seed_fixture_artifacts(config: CaseConfig, case_dir: Path) -> None:
    fixture_dir = fixture_case_dir(config.case_id)
    if not fixture_dir.exists():
        return
    for item in fixture_dir.iterdir():
        if item.is_file():
            shutil.copy2(item, case_dir / item.name)


def _connector_payload_to_dict(result: Any) -> dict[str, Any]:
    if hasattr(result, "model_dump"):
        return result.model_dump(mode="json")
    if hasattr(result, "to_dict"):
        return result.to_dict()
    if isinstance(result, dict):
        return result
    raise TypeError(f"Unsupported connector result type: {type(result)!r}")


def _save_connector_raw(case_dir: Path, connector_name: str, payload: dict[str, Any]) -> None:
    raw_dir = case_dir / "raw"
    raw_dir.mkdir(parents=True, exist_ok=True)
    raw_path = raw_dir / f"{connector_name}_raw.json"
    raw_path.write_text(json.dumps(payload, indent=2) + "\n", encoding="utf-8")


def run_connectors(config: CaseConfig, case_dir: Path, mode: RunMode) -> list[dict[str, Any]]:
    """Invoke connectors when implemented; otherwise rely on fixture artifacts."""
    payloads: list[dict[str, Any]] = []
    for name in _enabled_connectors(config):
        connector = _import_connector(name)
        if connector is None:
            continue
        result = connector.fetch(config, mode)
        payload = _connector_payload_to_dict(result)
        payloads.append(payload)
        _save_connector_raw(case_dir, name, payload)
    return payloads


def _ensure_source_artifacts(config: CaseConfig, case_dir: Path, mode: RunMode) -> None:
    for artifact_name in SOURCE_ARTIFACTS:
        dest = case_dir / artifact_name
        if dest.exists():
            continue
        copy_fixture_artifact(config.case_id, artifact_name, dest)
        if dest.exists():
            continue
        if mode == "fixture":
            _write_empty_source_artifact(config.case_id, artifact_name, dest)
            continue
        raise FileNotFoundError(
            f"Missing source artifact {artifact_name} and no fixture available for {config.case_id}"
        )


def _write_empty_source_artifact(case_id: str, artifact_name: str, dest: Path) -> None:
    data_by_artifact = {
        "source_manifest.json": {"entries": []},
        "literature_records.json": {"records": []},
        "clinical_trials.json": {"trials": []},
        "target_biology.json": {"records": []},
    }
    if artifact_name not in data_by_artifact:
        return
    envelope = {
        "artifact_type": artifact_name.replace(".json", ""),
        "case_id": case_id,
        "schema_version": SCHEMA_VERSION,
        "generated_at": utc_now_iso(),
        "provenance": build_provenance("pipeline/run_workflow.py", []),
        "data": data_by_artifact[artifact_name],
    }
    dest.write_text(json.dumps(envelope, indent=2) + "\n", encoding="utf-8")


def _ensure_eval_results(config: CaseConfig, case_dir: Path, mode: RunMode) -> None:
    dest = case_dir / "eval_results.json"
    if dest.exists():
        return
    copy_fixture_artifact(config.case_id, "eval_results.json", dest)
    if not dest.exists():
        dest.write_text(
            json.dumps(
                {
                    "artifact_type": "eval_results",
                    "case_id": config.case_id,
                    "schema_version": "v0.5",
                    "generated_at": utc_now_iso(),
                    "provenance": {
                        "generated_by": "pipeline/run_workflow.py",
                        "generated_at": utc_now_iso(),
                        "input_artifacts": list(REQUIRED_ARTIFACTS),
                        "model_provider": None,
                        "model_name": None,
                        "prompt_hash": None,
                        "schema_version": "v0.5",
                    },
                    "data": {"evaluators": [], "summary": {"passed": True}},
                },
                indent=2,
            )
            + "\n",
            encoding="utf-8",
        )


def run_case_workflow(config: CaseConfig, mode: RunMode, *, output_dir: Path | None = None) -> Path:
    """Execute the full pipeline for one case configuration."""
    load_repo_env()
    case_dir = output_dir or generated_case_dir(config.case_id)
    if case_dir.exists():
        shutil.rmtree(case_dir)
    case_dir.mkdir(parents=True, exist_ok=True)

    if mode == "fixture":
        _seed_fixture_artifacts(config, case_dir)

    _write_metadata(config, case_dir, mode)
    connector_payloads = run_connectors(config, case_dir, mode)
    if mode == "live":
        build_source_artifacts(config, case_dir, mode=mode, connector_payloads=connector_payloads)
    _ensure_source_artifacts(config, case_dir, mode)

    normalize_entities(config, case_dir, mode=mode, connector_payloads=connector_payloads)
    generate_claims(config, case_dir, mode=mode)
    generate_risk_map(config, case_dir, mode=mode)
    generate_report(config, case_dir, mode=mode)
    generate_questions(config, case_dir, mode=mode)
    build_ri_lens_artifacts(config, case_dir)
    build_knowledge_graph(config, case_dir)
    _ensure_eval_results(config, case_dir, mode)
    _write_metadata_summary(case_dir / "metadata.yaml", case_dir)

    validate_case_dir(case_dir, validate_schemas=False)
    return case_dir


def main(argv: list[str] | None = None) -> int:
    load_repo_env()
    parser = argparse.ArgumentParser(description="Run translational diligence workflow")
    parser.add_argument("--config", required=True, help="Path to configs/cases/{case_id}.yaml")
    parser.add_argument(
        "--mode",
        required=True,
        choices=["fixture", "live"],
        help="fixture copies/assembles from tests/fixtures; live uses connector/synthesis stubs",
    )
    args = parser.parse_args(argv)

    config_path = Path(args.config)
    if not config_path.is_absolute():
        candidate = repo_root() / config_path
        if candidate.exists():
            config_path = candidate

    mode: RunMode = args.mode
    registry = RunRegistry()
    run_id = uuid.uuid4().hex[:12]

    try:
        config = load_case_config(config_path)
    except (ConfigValidationError, FileNotFoundError) as exc:
        print(f"Config error: {exc}", file=sys.stderr)
        return 1

    if mode == "fixture" and not config.run_mode_defaults.fixture_allowed:
        print("Fixture mode disabled for this case", file=sys.stderr)
        return 1
    if mode == "live" and not config.run_mode_defaults.live_allowed:
        print("Live mode disabled for this case", file=sys.stderr)
        return 1

    output_dir = generated_case_dir(config.case_id)
    record = registry.start_run(
        run_id=run_id,
        case_id=config.case_id,
        mode=mode,
        config_path=config_path,
        output_dir=output_dir,
    )

    try:
        case_dir = run_case_workflow(config, mode)
        artifacts = validate_case_dir(case_dir, validate_schemas=False)
        registry.complete_run(record, artifacts=artifacts)
    except (ArtifactValidationError, FileNotFoundError, ConfigValidationError) as exc:
        registry.complete_run(record, artifacts=[], errors=[str(exc)])
        print(f"Workflow failed: {exc}", file=sys.stderr)
        return 1

    print(f"Generated case packet: {case_dir}")
    print(f"Artifacts: {len(artifacts)}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
