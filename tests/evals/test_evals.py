"""Deterministic evaluation suite tests."""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from evals.citation_fidelity import evaluate as evaluate_citation_fidelity
from evals.evidence_coverage import evaluate as evaluate_evidence_coverage
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
    assert len(saved["data"]["evaluations"]) >= 4


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
