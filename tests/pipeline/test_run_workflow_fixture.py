"""Fixture-mode pipeline integration tests."""

from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path

import pytest
import yaml

from pipeline.artifact_writer import validate_case_dir
from pipeline.types import REQUIRED_ARTIFACTS, generated_case_dir, repo_root

ROOT = repo_root()
CONFIG = ROOT / "configs" / "cases" / "sting_pdac.yaml"


@pytest.fixture()
def generated_sting_pdac() -> Path:
    case_dir = generated_case_dir("sting_pdac")
    if case_dir.exists():
        import shutil

        shutil.rmtree(case_dir)

    result = subprocess.run(
        [
            sys.executable,
            "-m",
            "pipeline.run_workflow",
            "--config",
            str(CONFIG),
            "--mode",
            "fixture",
        ],
        cwd=ROOT,
        capture_output=True,
        text=True,
    )
    assert result.returncode == 0, result.stderr or result.stdout
    return case_dir


def test_fixture_run_produces_twelve_artifacts(generated_sting_pdac: Path) -> None:
    artifacts = validate_case_dir(generated_sting_pdac, validate_schemas=False)
    assert len(artifacts) == 12
    assert set(artifacts) == set(REQUIRED_ARTIFACTS)


def test_fixture_metadata_matches_config(generated_sting_pdac: Path) -> None:
    metadata_path = generated_sting_pdac / "metadata.yaml"
    assert metadata_path.exists()
    text = metadata_path.read_text(encoding="utf-8")
    assert "case_id: sting_pdac" in text
    assert "STING" in text
    metadata = yaml.safe_load(text)
    run_meta = metadata.get("run", {})
    assert run_meta.get("mode") == "fixture"
    assert run_meta.get("synthesis_provider") == "mock"
    assert run_meta.get("mocked_api_calls") is True
    assert run_meta.get("using_live_api") is False
    assert run_meta.get("input_primary_complete") is True
    assert isinstance(run_meta.get("input_breadth_count"), int)
    assert run_meta.get("input_quality_band") in {"MINIMAL", "STANDARD", "STRONG", "RICH"}
    assert isinstance(run_meta.get("input_quality_warnings"), list)
    assert run_meta.get("input_preferred_minimum_met") in {True, False}
    assert metadata.get("maturity_stage")
    assert isinstance(metadata.get("confidence_score"), (int, float))
    assert 0.0 <= float(metadata["confidence_score"]) <= 1.0
    assert metadata.get("evidence_density") in {"low", "medium", "high"}
    assert isinstance(metadata.get("top_risk"), str)


def test_knowledge_graph_built_from_entities(generated_sting_pdac: Path) -> None:
    graph = json.loads((generated_sting_pdac / "knowledge_graph.json").read_text(encoding="utf-8"))
    nodes = graph["data"]["nodes"]
    edges = graph["data"]["edges"]
    assert any(node["node_id"] == "gene:TMEM173" for node in nodes)
    assert len(edges) >= 3
    assert any(edge["relationship"] in {"supports_target", "tested_in"} for edge in edges)
    assert graph["provenance"]["generated_by"] == "pipeline/build_graph.py"
