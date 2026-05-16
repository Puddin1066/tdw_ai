"""Generate evidence_table.json from normalized source artifacts."""

from __future__ import annotations

from pathlib import Path

from pipeline._artifacts import run_synthesis_step
from pipeline.types import CaseConfig, RunMode


def generate_claims(config: CaseConfig, case_dir: Path, *, mode: RunMode) -> Path:
    return run_synthesis_step(
        config,
        case_dir,
        mode=mode,
        artifact_name="evidence_table.json",
        artifact_type="evidence_table",
        generated_by="pipeline/generate_claims.py",
        input_artifacts=[
            "literature_records.json",
            "clinical_trials.json",
            "target_biology.json",
            "normalized_entities.json",
        ],
        stub_data={
            "rows": [
                {
                    "evidence_id": f"evidence:{config.case_id}:0001",
                    "claim_text": (
                        f"{config.target.name} has preliminary evidence in "
                        f"{config.indication.name} (live synthesis stub)."
                    ),
                    "claim_type": "translational",
                    "support_status": "insufficient_evidence",
                    "confidence": 0.4,
                    "source_record_ids": [],
                    "quoted_evidence": [],
                    "limitations": ["live synthesis not configured"],
                }
            ]
        },
    )
