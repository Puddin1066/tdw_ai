"""Synthesis tests using MockProvider only (no paid API)."""

from __future__ import annotations

import json
import shutil
from pathlib import Path

import pytest

from pipeline.config_loader import load_case_config
from pipeline.generate_claims import generate_claims
from pipeline.generate_report import generate_report
from pipeline.generate_risk_map import generate_risk_map
from pipeline.llm_provider import MockProvider
from pipeline.types import repo_root

ROOT = repo_root()
CONFIG = ROOT / "configs" / "cases" / "sting_pdac.yaml"


def test_mock_provider_loads_synthesis_fixture() -> None:
    provider = MockProvider()
    response = provider.generate_json(
        "test",
        {},
        0.0,
        100,
        {"case_id": "sting_pdac", "step": "evidence_table"},
    )
    assert not response.errors
    assert response.output_json.get("rows")


@pytest.mark.parametrize("step", ["evidence_table", "risk_map", "diligence_report"])
def test_synthesis_fixture_files_exist(step: str) -> None:
    path = ROOT / "tests" / "fixtures" / "synthesis" / f"sting_pdac_{step}_data.json"
    assert path.is_file(), f"missing {path}"
    data = json.loads(path.read_text(encoding="utf-8"))
    assert isinstance(data, dict)


def test_live_mode_synthesis_chain_mock_provider(tmp_path: Path) -> None:
    """Live mode with MockProvider produces schema-valid synthesis artifacts."""
    config = load_case_config(CONFIG)
    case_dir = tmp_path / "sting_pdac"
    case_dir.mkdir()
    fixture_dir = ROOT / "tests" / "fixtures" / "cases" / "sting_pdac"
    for name in (
        "literature_records.json",
        "clinical_trials.json",
        "target_biology.json",
        "normalized_entities.json",
    ):
        shutil.copy2(fixture_dir / name, case_dir / name)

    generate_claims(config, case_dir, mode="live")
    generate_risk_map(config, case_dir, mode="live")
    generate_report(config, case_dir, mode="live")

    evidence = json.loads((case_dir / "evidence_table.json").read_text(encoding="utf-8"))
    assert evidence["provenance"]["model_provider"] == "mock"
    assert evidence["data"]["rows"]
    report = json.loads((case_dir / "diligence_report.json").read_text(encoding="utf-8"))
    assert report["data"]["executive_summary"]
    assert (case_dir / "diligence_report.md").is_file()
