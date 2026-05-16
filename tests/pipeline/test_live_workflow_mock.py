"""Live workflow integration using MockProvider (no OpenAI API key)."""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from pipeline.artifact_writer import validate_case_dir
from pipeline.run_workflow import run_case_workflow
from pipeline.types import repo_root

ROOT = repo_root()
CONFIG = ROOT / "configs" / "cases" / "sting_pdac.yaml"


@pytest.fixture
def live_case_dir(tmp_path: Path) -> Path:
    from pipeline.config_loader import load_case_config

    config = load_case_config(CONFIG)
    return run_case_workflow(config, "live", output_dir=tmp_path / "sting_pdac")


def test_live_workflow_produces_synthesis_artifacts(live_case_dir: Path) -> None:
    report = json.loads((live_case_dir / "diligence_report.json").read_text(encoding="utf-8"))
    assert report["provenance"]["model_provider"] == "mock"
    assert report["data"].get("executive_summary")
    provenance = report["provenance"]
    assert "skills/translational_diligence" in (provenance.get("prompt_template") or "")


def test_live_workflow_synthesis_passes_schema(live_case_dir: Path) -> None:
    """Synthesis artifacts from live+mock path must validate against schemas."""
    from pipeline.schema_validate import validate_artifact_file

    for name in ("evidence_table.json", "risk_map.json", "diligence_report.json"):
        errors = validate_artifact_file(live_case_dir / name)
        assert errors == [], f"{name}: {errors}"
