"""Generate diligence report artifacts."""

from __future__ import annotations

from pathlib import Path

from pipeline._artifacts import run_synthesis_step
from pipeline.types import CaseConfig, RunMode


def generate_report(config: CaseConfig, case_dir: Path, *, mode: RunMode) -> tuple[Path, Path]:
    md_path = run_synthesis_step(
        config,
        case_dir,
        mode=mode,
        artifact_name="diligence_report.md",
        artifact_type="diligence_report",
        generated_by="pipeline/generate_report.py",
        input_artifacts=["evidence_table.json", "risk_map.json"],
        stub_data={},
    )
    json_path = run_synthesis_step(
        config,
        case_dir,
        mode=mode,
        artifact_name="diligence_report.json",
        artifact_type="diligence_report",
        generated_by="pipeline/generate_report.py",
        input_artifacts=["evidence_table.json", "risk_map.json"],
        stub_data={
            "title": config.display_name,
            "summary": f"Live synthesis stub for {config.case_id}.",
            "sections": [],
            "confidence": "low",
        },
    )
    return md_path, json_path
