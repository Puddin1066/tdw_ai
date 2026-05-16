"""Score whether report claims are backed by evidence_table rows."""

from __future__ import annotations

from pathlib import Path

from evals.artifacts import (
    case_id_from_dir,
    evidence_rows,
    load_json,
    report_claims,
)
from evals.types import EvaluationResult


def evaluate(case_dir: Path) -> EvaluationResult:
    case_id = case_id_from_dir(case_dir)
    checked = ["diligence_report.json", "evidence_table.json"]
    errors: list[str] = []
    warnings: list[str] = []

    report_json = load_json(case_dir / "diligence_report.json")
    evidence_table = load_json(case_dir / "evidence_table.json")

    evidence_ids = {
        str(row.get("evidence_id"))
        for row in evidence_rows(evidence_table)
        if row.get("evidence_id")
    }
    evidence_claim_text = {
        str(row.get("claim_text", "")).strip().lower()
        for row in evidence_rows(evidence_table)
        if row.get("claim_text")
    }

    claims = report_claims(report_json)
    if not claims:
        warnings.append("diligence_report.json contains no structured claims")

    uncovered = 0
    for claim in claims:
        evidence_id = claim.get("evidence_id")
        claim_text = str(claim.get("text", claim.get("claim_text", ""))).strip()
        claim_id = claim.get("claim_id", evidence_id or claim_text[:40] or "unknown")

        if evidence_id:
            if str(evidence_id) not in evidence_ids:
                uncovered += 1
                errors.append(f"Report claim {claim_id} references unknown evidence_id {evidence_id}")
            continue

        normalized = claim_text.lower()
        if normalized and normalized not in evidence_claim_text:
            uncovered += 1
            errors.append(f"Report claim {claim_id} not found in evidence_table.json")

    total_claims = len(claims)
    covered = total_claims - uncovered
    score = round(covered / total_claims, 4) if total_claims else 1.0
    passed = uncovered == 0

    return EvaluationResult(
        evaluator_name="evidence_coverage",
        case_id=case_id,
        passed=passed,
        score=score,
        errors=errors,
        warnings=warnings,
        checked_artifacts=checked,
        metrics={
            "report_claims": total_claims,
            "covered_claims": covered,
            "uncovered_claims": uncovered,
            "evidence_rows": len(evidence_rows(evidence_table)),
        },
    )
