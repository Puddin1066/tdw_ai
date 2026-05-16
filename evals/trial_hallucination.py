"""Detect NCT IDs in the diligence report that are absent from clinical_trials.json."""

from __future__ import annotations

from pathlib import Path

from evals.artifacts import (
    case_id_from_dir,
    clinical_trial_nct_ids,
    collect_report_text,
    extract_nct_ids,
    load_json,
    load_text,
)
from evals.types import EvaluationResult


def evaluate(case_dir: Path) -> EvaluationResult:
    case_id = case_id_from_dir(case_dir)
    checked = ["diligence_report.json", "diligence_report.md", "clinical_trials.json"]
    errors: list[str] = []
    warnings: list[str] = []

    report_json = load_json(case_dir / "diligence_report.json")
    clinical_trials = load_json(case_dir / "clinical_trials.json")
    report_md_path = case_dir / "diligence_report.md"
    report_md = load_text(report_md_path) if report_md_path.exists() else None

    valid_ncts = clinical_trial_nct_ids(clinical_trials)
    report_text = collect_report_text(report_json, report_md)
    cited_ncts = extract_nct_ids(report_text)

    hallucinated = sorted(nct for nct in cited_ncts if nct not in valid_ncts)
    for nct in hallucinated:
        errors.append(f"Hallucinated NCT ID {nct} in report but missing from clinical_trials.json")

    if not cited_ncts:
        warnings.append("No NCT IDs found in diligence report text")

    total = max(len(cited_ncts), 1)
    score = round((len(cited_ncts) - len(hallucinated)) / total, 4) if cited_ncts else 1.0
    passed = len(hallucinated) == 0

    return EvaluationResult(
        evaluator_name="trial_hallucination",
        case_id=case_id,
        passed=passed,
        score=score,
        errors=errors,
        warnings=warnings,
        checked_artifacts=checked,
        metrics={
            "cited_nct_ids": len(cited_ncts),
            "valid_nct_ids": len(valid_ncts),
            "hallucinated_nct_ids": len(hallucinated),
            "hallucinated_ncts": hallucinated,
        },
    )
