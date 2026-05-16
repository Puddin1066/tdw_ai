"""Generate risk_map.json."""

from __future__ import annotations

from pathlib import Path

from pipeline._artifacts import run_synthesis_step
from pipeline.types import CaseConfig, RunMode


def generate_risk_map(config: CaseConfig, case_dir: Path, *, mode: RunMode) -> Path:
    return run_synthesis_step(
        config,
        case_dir,
        mode=mode,
        artifact_name="risk_map.json",
        artifact_type="risk_map",
        generated_by="pipeline/generate_risk_map.py",
        input_artifacts=["evidence_table.json", "clinical_trials.json", "target_biology.json"],
        stub_data={
            "risks": [
                {
                    "risk_id": f"risk:{config.case_id}:0001",
                    "category": "evidence_gap",
                    "title": "Limited live synthesis evidence",
                    "description": "Risk map generated from live-mode stub.",
                    "severity": "medium",
                    "confidence": 0.4,
                    "evidence_ids": [],
                    "inferred": True,
                }
            ]
        },
    )
