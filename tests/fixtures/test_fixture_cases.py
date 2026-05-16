"""Verify fixture case packets include all 12 required artifacts with valid JSON."""

from __future__ import annotations

import json
from pathlib import Path

import pytest

FIXTURE_ROOT = Path(__file__).resolve().parent / "cases"
WEB_ROOT = Path(__file__).resolve().parents[2] / "web" / "public" / "data" / "cases"

CASE_IDS = ("sting_pdac", "parp_breast", "tau_alzheimers", "iaip_sepsis")

REQUIRED_ARTIFACTS = (
    "metadata.yaml",
    "source_manifest.json",
    "normalized_entities.json",
    "literature_records.json",
    "clinical_trials.json",
    "target_biology.json",
    "evidence_table.json",
    "diligence_report.json",
    "diligence_report.md",
    "risk_map.json",
    "knowledge_graph.json",
    "eval_results.json",
)

JSON_ARTIFACTS = tuple(a for a in REQUIRED_ARTIFACTS if a.endswith(".json"))

RAW_CONNECTOR_FILES = (
    "pubmed_raw.json",
    "clinicaltrials_raw.json",
    "opentargets_raw.json",
    "chembl_raw.json",
    "biothings_raw.json",
)


@pytest.mark.parametrize("case_id", CASE_IDS)
def test_fixture_case_has_all_artifacts(case_id: str) -> None:
    case_dir = FIXTURE_ROOT / case_id
    for artifact in REQUIRED_ARTIFACTS:
        path = case_dir / artifact
        assert path.is_file(), f"missing {case_id}/{artifact}"


@pytest.mark.parametrize("case_id", CASE_IDS)
@pytest.mark.parametrize("artifact", JSON_ARTIFACTS)
def test_fixture_json_parses(case_id: str, artifact: str) -> None:
    path = FIXTURE_ROOT / case_id / artifact
    with path.open(encoding="utf-8") as handle:
        data = json.load(handle)
    assert isinstance(data, dict)
    assert data.get("case_id") == case_id
    assert "artifact_type" in data
    assert "schema_version" in data
    assert "data" in data


@pytest.mark.parametrize("case_id", CASE_IDS)
def test_fixture_raw_connector_samples(case_id: str) -> None:
    raw_dir = FIXTURE_ROOT / case_id / "raw"
    assert raw_dir.is_dir(), f"missing raw/ for {case_id}"
    for raw_file in RAW_CONNECTOR_FILES:
        path = raw_dir / raw_file
        assert path.is_file(), f"missing {case_id}/raw/{raw_file}"
        with path.open(encoding="utf-8") as handle:
            json.load(handle)


@pytest.mark.parametrize("case_id", CASE_IDS)
def test_web_public_copies_match_fixture(case_id: str) -> None:
    web_dir = WEB_ROOT / case_id
    assert web_dir.is_dir(), f"missing web copy for {case_id}"
    for artifact in REQUIRED_ARTIFACTS:
        assert (web_dir / artifact).is_file(), f"missing web/{case_id}/{artifact}"


def test_sting_pdac_marked_mock_synthetic() -> None:
    """sting_pdac is the primary demo case and must be clearly labeled MOCK/SYNTHETIC."""
    metadata = (FIXTURE_ROOT / "sting_pdac" / "metadata.yaml").read_text(encoding="utf-8")
    assert "MOCK/SYNTHETIC" in metadata
    assert "mock_synthetic: true" in metadata

    with (FIXTURE_ROOT / "sting_pdac" / "diligence_report.json").open(encoding="utf-8") as handle:
        report = json.load(handle)
    assert report["data"]["mock_synthetic"] is True

    md = (FIXTURE_ROOT / "sting_pdac" / "diligence_report.md").read_text(encoding="utf-8")
    assert "MOCK/SYNTHETIC" in md
