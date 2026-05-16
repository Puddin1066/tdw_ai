"""Verify PMIDs and supported-claim citations resolve to source records."""

from __future__ import annotations

from pathlib import Path

from evals.artifacts import (
    SUPPORTED_STATUSES,
    case_id_from_dir,
    collect_report_text,
    evidence_rows,
    extract_pmids,
    literature_pmids,
    load_json,
    load_text,
    report_claims,
)
from evals.types import EvaluationResult


def evaluate(case_dir: Path) -> EvaluationResult:
    case_id = case_id_from_dir(case_dir)
    checked = [
        "diligence_report.json",
        "diligence_report.md",
        "literature_records.json",
        "evidence_table.json",
    ]
    errors: list[str] = []
    warnings: list[str] = []

    report_path = case_dir / "diligence_report.json"
    literature_path = case_dir / "literature_records.json"
    evidence_path = case_dir / "evidence_table.json"
    report_md_path = case_dir / "diligence_report.md"

    report_json = load_json(report_path)
    literature = load_json(literature_path)
    evidence_table = load_json(evidence_path)
    report_md = load_text(report_md_path) if report_md_path.exists() else None

    valid_pmids = literature_pmids(literature)
    report_text = collect_report_text(report_json, report_md)
    cited_pmids = extract_pmids(report_text)

    hallucinated_pmids = sorted(pmid for pmid in cited_pmids if pmid not in valid_pmids)
    for pmid in hallucinated_pmids:
        errors.append(f"Hallucinated PMID {pmid} cited in report but missing from literature_records.json")

    missing_citation_rows = 0
    supported_rows = 0
    for row in evidence_rows(evidence_table):
        status = str(row.get("support_status", "")).lower()
        if status not in SUPPORTED_STATUSES:
            continue
        supported_rows += 1
        source_ids = row.get("source_record_ids") or []
        quoted = row.get("quoted_evidence") or []
        if not source_ids and not quoted:
            missing_citation_rows += 1
            evidence_id = row.get("evidence_id", "unknown")
            errors.append(
                f"Evidence row {evidence_id} is {status} but has no source_record_ids or quoted_evidence"
            )

    for claim in report_claims(report_json):
        status = str(claim.get("support_status", "")).lower()
        if status not in SUPPORTED_STATUSES:
            continue
        citations = claim.get("citations") or {}
        source_ids = citations.get("source_record_ids") or claim.get("source_record_ids") or []
        pmids = citations.get("pmids") or []
        if not source_ids and not pmids:
            claim_id = claim.get("claim_id", claim.get("evidence_id", "unknown"))
            errors.append(f"Supported report claim {claim_id} has no citations")

    total_checks = max(len(cited_pmids) + supported_rows, 1)
    failed = len(hallucinated_pmids) + missing_citation_rows
    score = round(max(0.0, 1.0 - failed / total_checks), 4)
    passed = not errors

    return EvaluationResult(
        evaluator_name="citation_fidelity",
        case_id=case_id,
        passed=passed,
        score=score,
        errors=errors,
        warnings=warnings,
        checked_artifacts=checked,
        metrics={
            "cited_pmids": len(cited_pmids),
            "valid_pmids": len(valid_pmids),
            "hallucinated_pmids": len(hallucinated_pmids),
            "supported_evidence_rows": supported_rows,
            "supported_rows_missing_citations": missing_citation_rows,
        },
    )
