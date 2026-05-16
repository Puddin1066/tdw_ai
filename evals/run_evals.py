"""CLI entrypoint for deterministic case packet evaluation."""

from __future__ import annotations

import argparse
import json
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

from evals.artifacts import REQUIRED_ARTIFACTS, missing_artifacts
from evals.citation_fidelity import evaluate as evaluate_citation_fidelity
from evals.evidence_coverage import evaluate as evaluate_evidence_coverage
from evals.trial_hallucination import evaluate as evaluate_trial_hallucination
from evals.types import EvaluationResult
from evals.unsupported_claims import evaluate as evaluate_unsupported_claims

EVALUATORS = [
    evaluate_citation_fidelity,
    evaluate_unsupported_claims,
    evaluate_trial_hallucination,
    evaluate_evidence_coverage,
]

SECTION_15_GATES = [
    {
        "gate_id": "required_artifacts_present",
        "description": "All required case packet artifacts exist before evaluation.",
        "section": "15",
    },
    {
        "gate_id": "report_claims_in_evidence_table",
        "description": "Every report claim appears in evidence_table.json.",
        "section": "15",
        "evaluator": "evidence_coverage",
    },
    {
        "gate_id": "supported_claims_have_citations",
        "description": "Every supported claim has at least one citation.",
        "section": "15",
        "evaluator": "citation_fidelity",
    },
    {
        "gate_id": "nct_ids_in_clinical_trials",
        "description": "Every NCT ID mentioned in report exists in clinical_trials.json.",
        "section": "15",
        "evaluator": "trial_hallucination",
    },
    {
        "gate_id": "pmids_in_literature_records",
        "description": "Every PMID cited in report exists in literature_records.json.",
        "section": "15",
        "evaluator": "citation_fidelity",
    },
    {
        "gate_id": "unsupported_claims_flagged",
        "description": "Unsupported or contradicted claims are not promoted to supported status.",
        "section": "15",
        "evaluator": "unsupported_claims",
    },
]


def _gate_results(
    case_dir: Path,
    evaluator_results: list[EvaluationResult],
    missing: list[str],
) -> list[dict[str, Any]]:
    by_name = {result.evaluator_name: result for result in evaluator_results}
    gates: list[dict[str, Any]] = []

    for gate in SECTION_15_GATES:
        gate_id = gate["gate_id"]
        if gate_id == "required_artifacts_present":
            passed = len(missing) == 0
            issues = [f"Missing artifact: {name}" for name in missing]
        else:
            evaluator_name = gate["evaluator"]
            result = by_name[evaluator_name]
            passed = result.passed
            issues = list(result.errors)

        gates.append(
            {
                "gate_id": gate_id,
                "description": gate["description"],
                "section": gate["section"],
                "passed": passed,
                "issues": issues,
            }
        )
    return gates


def run_evaluations(case_dir: Path) -> dict[str, Any]:
    case_dir = case_dir.resolve()
    if not case_dir.exists():
        raise FileNotFoundError(f"Case directory not found: {case_dir}")

    missing = missing_artifacts(case_dir)
    evaluator_results = [evaluate(case_dir) for evaluate in EVALUATORS]
    case_id = evaluator_results[0].case_id if evaluator_results else case_dir.name

    gates = _gate_results(case_dir, evaluator_results, missing)
    issues = [issue for gate in gates for issue in gate["issues"]]
    for result in evaluator_results:
        issues.extend(result.errors)

    overall_passed = all(gate["passed"] for gate in gates)
    scores = {result.evaluator_name: result.score for result in evaluator_results}

    payload: dict[str, Any] = {
        "artifact_type": "eval_results",
        "case_id": case_id,
        "schema_version": "v0.5",
        "generated_at": datetime.now(UTC).replace(microsecond=0).isoformat().replace("+00:00", "Z"),
        "provenance": {
            "generated_by": "evals/run_evals.py",
            "generated_at": datetime.now(UTC).replace(microsecond=0).isoformat().replace("+00:00", "Z"),
            "input_artifacts": list(REQUIRED_ARTIFACTS),
            "model_provider": None,
            "model_name": None,
            "prompt_template": None,
            "prompt_hash": None,
            "schema_version": "v0.5",
        },
        "data": {
            "passed": overall_passed,
            "scores": scores,
            "issues": issues,
            "gates": gates,
            "evaluators": [result.to_dict() for result in evaluator_results],
            "summary": {
                "evaluator_count": len(evaluator_results),
                "issue_count": len(issues),
                "missing_artifacts": missing,
            },
        },
    }
    return payload


def write_eval_results(case_dir: Path, payload: dict[str, Any]) -> Path:
    output_path = case_dir / "eval_results.json"
    with output_path.open("w", encoding="utf-8") as handle:
        json.dump(payload, handle, indent=2)
        handle.write("\n")
    return output_path


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Run deterministic evaluators on a case packet.")
    parser.add_argument(
        "--case",
        required=True,
        help="Path to generated case directory, e.g. generated/cases/sting_pdac",
    )
    args = parser.parse_args(argv)

    case_dir = Path(args.case)
    payload = run_evaluations(case_dir)
    output_path = write_eval_results(case_dir, payload)

    print(f"Wrote {output_path}")
    print(f"Overall passed: {payload['data']['passed']}")
    print(f"Issues: {payload['data']['summary']['issue_count']}")
    return 0 if payload["data"]["passed"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
