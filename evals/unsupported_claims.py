"""Detect supported claims without evidence backing."""

from __future__ import annotations

from pathlib import Path

from evals.artifacts import (
    SUPPORTED_STATUSES,
    case_id_from_dir,
    evidence_rows,
    load_json,
    report_claims,
)
from evals.types import EvaluationResult

UNSUPPORTED_STATUSES = frozenset(
    {"unsupported", "contradicted", "insufficient_evidence"}
)


def evaluate(case_dir: Path) -> EvaluationResult:
    case_id = case_id_from_dir(case_dir)
    checked = ["evidence_table.json", "diligence_report.json"]
    errors: list[str] = []
    warnings: list[str] = []

    evidence_table = load_json(case_dir / "evidence_table.json")
    report_json = load_json(case_dir / "diligence_report.json")

    evidence_by_id = {
        str(row.get("evidence_id")): row
        for row in evidence_rows(evidence_table)
        if row.get("evidence_id")
    }

    unsupported_in_table = 0
    for row in evidence_rows(evidence_table):
        status = str(row.get("support_status", "")).lower()
        if status in UNSUPPORTED_STATUSES:
            unsupported_in_table += 1
            evidence_id = row.get("evidence_id", "unknown")
            warnings.append(f"Evidence row {evidence_id} marked {status}")

    promoted_unsupported = 0
    for claim in report_claims(report_json):
        status = str(claim.get("support_status", "")).lower()
        evidence_id = claim.get("evidence_id")
        if status in SUPPORTED_STATUSES and evidence_id:
            backing = evidence_by_id.get(str(evidence_id))
            if backing is None:
                promoted_unsupported += 1
                errors.append(
                    f"Report claim references missing evidence_id {evidence_id} while marked {status}"
                )
                continue
            backing_status = str(backing.get("support_status", "")).lower()
            if backing_status in UNSUPPORTED_STATUSES:
                promoted_unsupported += 1
                errors.append(
                    f"Report claim {claim.get('claim_id', evidence_id)} is {status} "
                    f"but evidence row {evidence_id} is {backing_status}"
                )

    falsely_supported_rows = 0
    for row in evidence_rows(evidence_table):
        status = str(row.get("support_status", "")).lower()
        if status not in SUPPORTED_STATUSES:
            continue
        source_ids = row.get("source_record_ids") or []
        if not source_ids:
            falsely_supported_rows += 1
            evidence_id = row.get("evidence_id", "unknown")
            errors.append(
                f"Evidence row {evidence_id} marked {status} without source_record_ids"
            )

    total_rows = max(len(evidence_rows(evidence_table)), 1)
    issue_count = promoted_unsupported + falsely_supported_rows
    score = round(max(0.0, 1.0 - issue_count / total_rows), 4)
    passed = issue_count == 0

    return EvaluationResult(
        evaluator_name="unsupported_claims",
        case_id=case_id,
        passed=passed,
        score=score,
        errors=errors,
        warnings=warnings,
        checked_artifacts=checked,
        metrics={
            "unsupported_evidence_rows": unsupported_in_table,
            "promoted_unsupported_claims": promoted_unsupported,
            "falsely_supported_rows": falsely_supported_rows,
        },
    )
