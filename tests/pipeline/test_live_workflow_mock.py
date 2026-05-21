"""Live workflow integration using MockProvider (no OpenAI API key)."""

from __future__ import annotations

import json
from pathlib import Path

import pytest
import yaml

from pipeline.artifact_writer import validate_case_dir
from pipeline.run_workflow import run_case_workflow
from pipeline.types import repo_root

ROOT = repo_root()
CONFIG = ROOT / "configs" / "cases" / "sting_pdac.yaml"


@pytest.fixture
def live_case_dir(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> Path:
    from pipeline.config_loader import load_case_config

    monkeypatch.setenv("TDW_SKIP_REPO_ENV", "1")
    monkeypatch.delenv("OPENAI_API_KEY", raising=False)
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


def test_live_workflow_metadata_marks_mocked_api_calls(live_case_dir: Path) -> None:
    metadata = yaml.safe_load((live_case_dir / "metadata.yaml").read_text(encoding="utf-8"))
    run_meta = metadata.get("run", {})
    assert run_meta.get("mode") == "live"
    assert run_meta.get("synthesis_provider") == "mock"
    assert run_meta.get("mocked_api_calls") is True
    assert run_meta.get("using_live_api") is False
    assert run_meta.get("input_primary_complete") is True
    assert isinstance(run_meta.get("input_breadth_count"), int)
    assert run_meta.get("input_quality_band") in {"MINIMAL", "STANDARD", "STRONG", "RICH"}
    assert isinstance(run_meta.get("input_quality_warnings"), list)
    assert run_meta.get("input_preferred_minimum_met") in {True, False}
    assert "OPENAI_API_KEY missing" in (run_meta.get("provider_selection_reason") or "")
    assert metadata.get("maturity_stage")
    assert isinstance(metadata.get("confidence_score"), (int, float))
    assert 0.0 <= float(metadata["confidence_score"]) <= 1.0
    assert metadata.get("evidence_density") in {"low", "medium", "high"}
    assert isinstance(metadata.get("top_risk"), str)
