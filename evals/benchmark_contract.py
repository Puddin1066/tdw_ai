"""Shared benchmark/future-case comparison contract checks.

These checks are deterministic and run for any live packet so benchmark cases
and future incoming cases are judged with the same quality gates.
"""

from __future__ import annotations

import re
from pathlib import Path
from typing import Any

from evals.artifacts import (
    artifact_data,
    case_id_from_dir,
    evidence_rows,
    load_json,
    load_metadata,
)
from evals.types import EvaluationResult

_GENERIC_TITLE_PATTERNS = (
    re.compile(r"^\s*unspecified risk\s*$", re.IGNORECASE),
    re.compile(r"^\s*risk\s*\d+\s*$", re.IGNORECASE),
    re.compile(r"^\s*untitled\s*$", re.IGNORECASE),
)

_FALLBACK_HINTS = (
    "mock/synthetic fallback",
    "native backend not implemented",
    "fixture fallback",
)


def evaluate(case_dir: Path) -> EvaluationResult:
    case_id = case_id_from_dir(case_dir)
    checked = [
        "metadata.yaml",
        "source_manifest.json",
        "evidence_table.json",
        "risk_map.json",
        "diligence_report.json",
        "literature_records.json",
        "clinical_trials.json",
        "target_biology.json",
    ]
    errors: list[str] = []
    warnings: list[str] = []

    metadata = load_metadata(case_dir)
    run_mode = str((metadata.get("run") or {}).get("mode") or "").strip().lower()
    if run_mode != "live":
        warnings.append("Benchmark contract gates are advisory-only for non-live packets.")
        return EvaluationResult(
            evaluator_name="benchmark_contract",
            case_id=case_id,
            passed=True,
            score=1.0,
            errors=errors,
            warnings=warnings,
            checked_artifacts=checked,
            metrics={"skipped_for_mode": run_mode or "unknown"},
        )

    source_manifest = load_json(case_dir / "source_manifest.json")
    evidence_table = load_json(case_dir / "evidence_table.json")
    risk_map = load_json(case_dir / "risk_map.json")
    report = load_json(case_dir / "diligence_report.json")
    literature = load_json(case_dir / "literature_records.json")
    clinical_trials = load_json(case_dir / "clinical_trials.json")
    target_biology = load_json(case_dir / "target_biology.json")

    entries = _manifest_entries(source_manifest)
    known_source_ids = _known_source_record_ids(literature, clinical_trials, target_biology)

    # Gate 1: data reality / non-fallback.
    if not entries:
        errors.append("Contract(data_reality): source_manifest has no connector entries.")
    connectors_with_records = 0
    total_records = 0
    fallback_entries = 0
    for entry in entries:
        record_count = int(entry.get("record_count") or 0)
        total_records += max(record_count, 0)
        if record_count > 0:
            connectors_with_records += 1
        issues_text = " ".join(str(v) for v in (entry.get("warnings") or []) + (entry.get("errors") or []))
        lowered = issues_text.lower()
        if any(token in lowered for token in _FALLBACK_HINTS):
            fallback_entries += 1
    if connectors_with_records < 3:
        errors.append(
            f"Contract(data_reality): only {connectors_with_records} connectors returned records; minimum is 3."
        )
    if total_records < 10:
        errors.append(
            f"Contract(data_reality): only {total_records} total records found; minimum is 10."
        )
    if fallback_entries > 0:
        errors.append(
            f"Contract(data_reality): {fallback_entries} connector entries reported fallback/mock behavior."
        )

    # Gate 2: grounding.
    broken_evidence_links = 0
    evidence_without_sources = 0
    for row in evidence_rows(evidence_table):
        evidence_id = str(row.get("evidence_id") or "unknown")
        source_ids = [str(v) for v in (row.get("source_record_ids") or []) if str(v).strip()]
        if not source_ids:
            evidence_without_sources += 1
            errors.append(
                f"Contract(grounding): evidence row {evidence_id} has no source_record_ids."
            )
            continue
        for source_id in source_ids:
            if source_id not in known_source_ids:
                broken_evidence_links += 1
                errors.append(
                    f"Contract(grounding): evidence row {evidence_id} cites unknown source_record_id {source_id}."
                )

    risk_rows = _risk_rows(risk_map)
    for risk in risk_rows:
        risk_id = str(risk.get("risk_id") or "unknown")
        source_ids = [str(v) for v in (risk.get("source_record_ids") or []) if str(v).strip()]
        evidence_ids = [str(v) for v in (risk.get("evidence_ids") or []) if str(v).strip()]
        if not source_ids and not evidence_ids:
            errors.append(
                f"Contract(grounding): risk {risk_id} has no source_record_ids/evidence_ids."
            )

    # Gate 3: specificity.
    generic_risk_titles = 0
    seen_titles: set[str] = set()
    duplicate_titles = 0
    for risk in risk_rows:
        title = str(risk.get("title") or "").strip()
        if not title:
            generic_risk_titles += 1
            errors.append("Contract(specificity): risk title is empty.")
            continue
        if _is_generic_title(title):
            generic_risk_titles += 1
            errors.append(f"Contract(specificity): generic risk title '{title}'.")
        key = title.lower()
        if key in seen_titles:
            duplicate_titles += 1
        seen_titles.add(key)
    if len(risk_rows) >= 3 and duplicate_titles > 1:
        errors.append(
            f"Contract(consistency): duplicate risk titles detected ({duplicate_titles} duplicates)."
        )

    report_title = str(artifact_data(report).get("title") or "").strip()
    if not report_title or report_title.lower() in {"diligence report", "report"}:
        errors.append("Contract(specificity): report title is generic or empty.")

    # Aggregate score: weighted gate-style score.
    gate_scores = [
        1.0 if connectors_with_records >= 3 and total_records >= 10 and fallback_entries == 0 else 0.0,
        1.0 if evidence_without_sources == 0 and broken_evidence_links == 0 else 0.0,
        1.0 if generic_risk_titles == 0 and report_title not in {"", "diligence report", "report"} else 0.0,
        1.0 if (len(risk_rows) < 3 or duplicate_titles <= 1) else 0.0,
    ]
    score = round(sum(gate_scores) / len(gate_scores), 4)
    passed = len(errors) == 0

    return EvaluationResult(
        evaluator_name="benchmark_contract",
        case_id=case_id,
        passed=passed,
        score=score,
        errors=errors,
        warnings=warnings,
        checked_artifacts=checked,
        metrics={
            "connectors_with_records": connectors_with_records,
            "total_records": total_records,
            "fallback_entries": fallback_entries,
            "evidence_without_sources": evidence_without_sources,
            "broken_evidence_links": broken_evidence_links,
            "generic_risk_titles": generic_risk_titles,
            "duplicate_risk_titles": duplicate_titles,
        },
    )


def _manifest_entries(source_manifest: dict[str, Any]) -> list[dict[str, Any]]:
    data = artifact_data(source_manifest)
    if not isinstance(data, dict):
        return []
    entries = data.get("entries")
    if isinstance(entries, list):
        return [e for e in entries if isinstance(e, dict)]
    # Legacy fixtures keep a "sources" list.
    legacy = data.get("sources")
    if isinstance(legacy, list):
        normalized: list[dict[str, Any]] = []
        for row in legacy:
            if not isinstance(row, dict):
                continue
            normalized.append(
                {
                    "record_count": row.get("record_count", 0),
                    "warnings": [],
                    "errors": [],
                }
            )
        return normalized
    return []


def _known_source_record_ids(
    literature: dict[str, Any],
    clinical_trials: dict[str, Any],
    target_biology: dict[str, Any],
) -> set[str]:
    known: set[str] = set()
    for artifact in (literature, clinical_trials, target_biology):
        data = artifact_data(artifact)
        if not isinstance(data, dict):
            continue
        for key in ("records", "trials"):
            rows = data.get(key)
            if not isinstance(rows, list):
                continue
            for row in rows:
                if not isinstance(row, dict):
                    continue
                source_record_id = str(row.get("source_record_id") or "").strip()
                if source_record_id:
                    known.add(source_record_id)
    return known


def _risk_rows(risk_map: dict[str, Any]) -> list[dict[str, Any]]:
    data = artifact_data(risk_map)
    if not isinstance(data, dict):
        return []
    rows = data.get("risks")
    if not isinstance(rows, list):
        return []
    return [row for row in rows if isinstance(row, dict)]


def _is_generic_title(title: str) -> bool:
    text = title.strip()
    if not text:
        return True
    return any(pattern.match(text) for pattern in _GENERIC_TITLE_PATTERNS)
