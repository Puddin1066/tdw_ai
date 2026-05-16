"""Generate optional diligence questions artifact (not required for case packet)."""

from __future__ import annotations

from pathlib import Path

from pipeline._artifacts import run_synthesis_step
from pipeline.types import CaseConfig, RunMode


def generate_questions(config: CaseConfig, case_dir: Path, *, mode: RunMode) -> Path:
    return run_synthesis_step(
        config,
        case_dir,
        mode=mode,
        artifact_name="diligence_questions.json",
        artifact_type="diligence_questions",
        generated_by="pipeline/generate_questions.py",
        input_artifacts=["evidence_table.json", "diligence_report.json"],
        stub_data={
            "questions": [
                {
                    "question_id": f"question:{config.case_id}:0001",
                    "text": f"What is the strongest clinical signal for {config.target.name} in {config.indication.name}?",
                    "priority": "high",
                }
            ]
        },
    )
