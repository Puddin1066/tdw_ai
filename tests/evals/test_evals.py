"""Deterministic evaluation suite tests."""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from evals.citation_fidelity import evaluate as evaluate_citation_fidelity
from evals.evidence_coverage import evaluate as evaluate_evidence_coverage
from evals.artifacts import clinical_trial_nct_ids
from evals.benchmark_contract import evaluate as evaluate_benchmark_contract
from evals.run_evals import run_evaluations, write_eval_results
from evals.trial_hallucination import evaluate as evaluate_trial_hallucination
from evals.unsupported_claims import evaluate as evaluate_unsupported_claims
from tests.fixtures.cases._helpers import bad_nct_packet, base_packet, write_packet


@pytest.fixture
def fixture_sting_pdac() -> Path:
    root = Path(__file__).resolve().parents[1] / "fixtures" / "cases" / "sting_pdac"
    if not (root / "metadata.yaml").exists():
        write_packet(root, base_packet())
    return root


@pytest.fixture
def fixture_sting_pdac_bad_nct(tmp_path: Path) -> Path:
    return write_packet(tmp_path / "sting_pdac_bad_nct", bad_nct_packet())


def test_good_fixture_passes_all_evaluators(fixture_sting_pdac: Path) -> None:
    assert evaluate_citation_fidelity(fixture_sting_pdac).passed
    assert evaluate_unsupported_claims(fixture_sting_pdac).passed
    assert evaluate_trial_hallucination(fixture_sting_pdac).passed
    assert evaluate_evidence_coverage(fixture_sting_pdac).passed
    assert evaluate_benchmark_contract(fixture_sting_pdac).passed


def test_bad_nct_fixture_fails_trial_hallucination(fixture_sting_pdac_bad_nct: Path) -> None:
    result = evaluate_trial_hallucination(fixture_sting_pdac_bad_nct)
    assert not result.passed
    assert any("NCT99999999" in error for error in result.errors)


def test_run_evals_writes_eval_results(fixture_sting_pdac: Path, tmp_path: Path) -> None:
    case_dir = write_packet(tmp_path / "sting_pdac_copy", base_packet())
    payload = run_evaluations(case_dir)
    output_path = write_eval_results(case_dir, payload)

    assert output_path.exists()
    saved = json.loads(output_path.read_text(encoding="utf-8"))
    assert saved["artifact_type"] == "eval_results"
    assert saved["data"]["overall_passed"] is True
    assert saved["data"]["metrics"]["citation_fidelity_score"] >= 0
    assert len(saved["data"]["evaluations"]) >= 5


def test_run_evals_overall_failure_on_hallucinated_nct(
    fixture_sting_pdac_bad_nct: Path,
) -> None:
    payload = run_evaluations(fixture_sting_pdac_bad_nct)
    assert payload["data"]["overall_passed"] is False
    trial_eval = next(
        e for e in payload["data"]["evaluations"] if e["evaluator_name"] == "trial_hallucination"
    )
    assert trial_eval["passed"] is False
    assert any("NCT99999999" in error for error in trial_eval["errors"])


def test_clinical_trial_nct_ids_supports_trials_key() -> None:
    artifact = {
        "artifact_type": "clinical_trials",
        "data": {
            "trials": [
                {"nct_id": "NCT01234567", "source_record_id": "clinicaltrials:NCT01234567"},
                {"source_record_id": "clinicaltrials:NCT07654321"},
            ]
        },
    }
    assert clinical_trial_nct_ids(artifact) == {"NCT01234567", "NCT07654321"}


def test_benchmark_contract_fails_live_packet_with_fallback_and_generic_risk(tmp_path: Path) -> None:
    packet = base_packet("live_contract_fail")
    packet["metadata.yaml"] = (
        "case_id: live_contract_fail\n"
        "display_name: Live contract fail\n"
        "run:\n"
        "  mode: live\n"
    )
    packet["source_manifest.json"]["data"] = {
        "entries": [
            {
                "connector_name": "pubmed",
                "source_name": "PubMed",
                "mode": "live",
                "query": {"target": "STING", "indication": "PDAC", "raw_query": "STING PDAC"},
                "retrieved_at": "2026-05-15T00:00:00Z",
                "record_count": 5,
                "raw_record_ref": "raw/pubmed_raw.json",
                "warnings": ["MOCK/SYNTHETIC fallback in live mode"],
                "errors": [],
            },
            {
                "connector_name": "clinicaltrials",
                "source_name": "ClinicalTrials.gov",
                "mode": "live",
                "query": {"target": "STING", "indication": "PDAC", "raw_query": "STING PDAC"},
                "retrieved_at": "2026-05-15T00:00:00Z",
                "record_count": 1,
                "raw_record_ref": "raw/clinicaltrials_raw.json",
                "warnings": [],
                "errors": [],
            },
        ]
    }
    packet["risk_map.json"]["data"]["risks"][0]["title"] = "Unspecified risk"
    case_dir = write_packet(tmp_path / "live_contract_fail", packet)
    result = evaluate_benchmark_contract(case_dir)
    assert result.passed is False
    assert any("Contract(data_reality)" in msg for msg in result.errors)
    assert any("Contract(specificity)" in msg for msg in result.errors)
