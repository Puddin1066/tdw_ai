"""Internal helpers for reading and writing case artifacts."""

from __future__ import annotations

import json
import shutil
from pathlib import Path
from typing import Any

from pipeline.provenance import build_provenance, utc_now_iso
from pipeline.synthesis_runner import run_synthesis_json_step, run_synthesis_report_md
from pipeline.types import SCHEMA_VERSION, CaseConfig, RunMode, fixture_case_dir


def copy_fixture_artifact(case_id: str, artifact_name: str, dest: Path) -> bool:
    source = fixture_case_dir(case_id) / artifact_name
    if not source.exists():
        return False
    dest.parent.mkdir(parents=True, exist_ok=True)
    shutil.copy2(source, dest)
    return True


def write_stub_envelope(
    config: CaseConfig,
    artifact_type: str,
    data: dict[str, Any],
    *,
    generated_by: str,
    input_artifacts: list[str],
    dest: Path,
) -> Path:
    envelope = {
        "artifact_type": artifact_type,
        "case_id": config.case_id,
        "schema_version": SCHEMA_VERSION,
        "generated_at": utc_now_iso(),
        "provenance": build_provenance(generated_by, input_artifacts),
        "data": data,
    }
    dest.write_text(json.dumps(envelope, indent=2) + "\n", encoding="utf-8")
    return dest


_EVIDENCE_SCHEMA: dict[str, Any] = {
    "$defs": {"evidenceTableData": {"type": "object", "properties": {"rows": {"type": "array"}}}}
}
_RISK_SCHEMA: dict[str, Any] = {
    "$defs": {"riskMapData": {"type": "object", "properties": {"risks": {"type": "array"}}}}
}
_REPORT_SCHEMA: dict[str, Any] = {
    "$defs": {
        "diligenceReportData": {
            "type": "object",
            "properties": {"title": {"type": "string"}, "summary": {"type": "string"}},
        }
    }
}


def run_synthesis_step(
    config: CaseConfig,
    case_dir: Path,
    *,
    mode: RunMode,
    artifact_name: str,
    artifact_type: str,
    generated_by: str,
    input_artifacts: list[str],
    stub_data: dict[str, Any],
) -> Path:
    dest = case_dir / artifact_name
    if mode == "fixture" and copy_fixture_artifact(config.case_id, artifact_name, dest):
        return dest

    if mode == "live":
        if artifact_name == "evidence_table.json":
            return run_synthesis_json_step(
                config,
                case_dir,
                mode=mode,
                step="evidence_table",
                prompt_name="claim_extraction",
                artifact_name=artifact_name,
                artifact_type=artifact_type,
                generated_by=generated_by,
                input_artifacts=input_artifacts,
                schema=_EVIDENCE_SCHEMA,
            )
        if artifact_name == "risk_map.json":
            return run_synthesis_json_step(
                config,
                case_dir,
                mode=mode,
                step="risk_map",
                prompt_name="risk_mapping",
                artifact_name=artifact_name,
                artifact_type=artifact_type,
                generated_by=generated_by,
                input_artifacts=input_artifacts,
                schema=_RISK_SCHEMA,
            )
        if artifact_name == "diligence_report.json":
            path = run_synthesis_json_step(
                config,
                case_dir,
                mode=mode,
                step="diligence_report",
                prompt_name="report_generation",
                artifact_name=artifact_name,
                artifact_type=artifact_type,
                generated_by=generated_by,
                input_artifacts=input_artifacts,
                schema=_REPORT_SCHEMA,
            )
            run_synthesis_report_md(config, case_dir, mode=mode)
            return path

    if artifact_name.endswith(".md"):
        dest.write_text(
            f"# {config.display_name}\n\n"
            f"Live synthesis stub for `{artifact_name}`. "
            "Wire OpenAI provider in live mode.\n",
            encoding="utf-8",
        )
        return dest
    return write_stub_envelope(
        config,
        artifact_type,
        stub_data,
        generated_by=generated_by,
        input_artifacts=input_artifacts,
        dest=dest,
    )
