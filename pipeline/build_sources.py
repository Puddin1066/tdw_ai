"""Build source artifact JSON from connector payloads (live mode)."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from pipeline._artifacts import copy_fixture_artifact
from pipeline.provenance import build_provenance, utc_now_iso
from pipeline.types import SCHEMA_VERSION, CaseConfig, RunMode


def _envelope(
    config: CaseConfig,
    artifact_type: str,
    data: dict[str, Any],
    *,
    generated_by: str,
    input_artifacts: list[str] | None = None,
) -> dict[str, Any]:
    return {
        "artifact_type": artifact_type,
        "case_id": config.case_id,
        "schema_version": SCHEMA_VERSION,
        "generated_at": utc_now_iso(),
        "provenance": build_provenance(generated_by, input_artifacts or []),
        "data": data,
    }


def _connector_by_name(payloads: list[dict[str, Any]], name: str) -> dict[str, Any] | None:
    for payload in payloads:
        if payload.get("connector_name") == name:
            return payload
    return None


def _normalize_literature_record(record: dict[str, Any], index: int = 0) -> dict[str, Any]:
    pmid = record.get("pmid") or (
        record.get("source_record_id", "").split(":")[-1] if record.get("source_record_id") else ""
    )
    retrieved = record.get("retrieved_at") or utc_now_iso()
    return {
        "source_record_id": record.get("source_record_id") or f"pubmed:{pmid}",
        "source_type": "literature",
        "source_name": record.get("source_name", "PubMed"),
        "title": record.get("title") or f"PubMed {pmid}",
        "url": record.get("url") or (f"https://pubmed.ncbi.nlm.nih.gov/{pmid}/" if pmid else None),
        "publication_date": record.get("publication_date"),
        "retrieved_at": retrieved,
        "raw_record_ref": record.get("raw_record_ref") or f"raw/pubmed_raw.json#records/{index}",
        "pmid": str(pmid) if pmid else None,
        "doi": record.get("doi"),
        "authors": record.get("authors") or [],
        "journal": record.get("journal"),
        "abstract": record.get("abstract"),
        "publication_types": record.get("publication_types") or [],
        "mesh_terms": record.get("mesh_terms") or [],
    }


def _normalize_trial_record(record: dict[str, Any]) -> dict[str, Any]:
    nct = record.get("nct_id") or ""
    if not nct and record.get("source_record_id", "").startswith("clinicaltrials:"):
        nct = record["source_record_id"].split(":", 1)[-1]
    title = record.get("brief_title") or record.get("title") or f"Trial {nct}"
    status = record.get("overall_status") or record.get("status") or "Unknown"
    return {
        "source_record_id": record.get("source_record_id") or f"clinicaltrials:{nct}",
        "source_type": "clinical_trial",
        "source_name": record.get("source_name", "ClinicalTrials.gov"),
        "title": title,
        "url": record.get("url") or f"https://clinicaltrials.gov/study/{nct}",
        "publication_date": record.get("publication_date"),
        "retrieved_at": record.get("retrieved_at") or utc_now_iso(),
        "raw_record_ref": record.get("raw_record_ref") or "raw/clinicaltrials_raw.json",
        "nct_id": nct,
        "brief_title": title,
        "official_title": record.get("official_title"),
        "phase": record.get("phase"),
        "overall_status": status,
        "study_type": record.get("study_type"),
        "sponsor": record.get("sponsor"),
        "interventions": record.get("interventions") or [],
        "conditions": record.get("conditions") or [],
        "start_date": record.get("start_date"),
        "completion_date": record.get("completion_date"),
        "enrollment_count": record.get("enrollment_count"),
    }


def build_literature_records(
    config: CaseConfig,
    case_dir: Path,
    connector_payloads: list[dict[str, Any]],
) -> Path:
    pubmed = _connector_by_name(connector_payloads, "pubmed")
    records: list[dict[str, Any]] = []
    if pubmed:
        for idx, raw in enumerate(pubmed.get("records", [])):
            if isinstance(raw, dict):
                records.append(_normalize_literature_record(raw, idx))
    data = {"records": records}
    path = case_dir / "literature_records.json"
    path.write_text(
        json.dumps(
            _envelope(config, "literature_records", data, generated_by="pipeline/build_sources.py"),
            indent=2,
        )
        + "\n",
        encoding="utf-8",
    )
    return path


def build_clinical_trials(
    config: CaseConfig,
    case_dir: Path,
    connector_payloads: list[dict[str, Any]],
) -> Path:
    ct = _connector_by_name(connector_payloads, "clinicaltrials")
    trials: list[dict[str, Any]] = []
    if ct:
        for raw in ct.get("records", []):
            if isinstance(raw, dict):
                trials.append(_normalize_trial_record(raw))
    data = {"trials": trials}
    path = case_dir / "clinical_trials.json"
    path.write_text(
        json.dumps(
            _envelope(config, "clinical_trials", data, generated_by="pipeline/build_sources.py"),
            indent=2,
        )
        + "\n",
        encoding="utf-8",
    )
    return path


def build_source_manifest(
    config: CaseConfig,
    case_dir: Path,
    connector_payloads: list[dict[str, Any]],
) -> Path:
    entries: list[dict[str, Any]] = []
    for payload in connector_payloads:
        query = payload.get("query", {})
        if isinstance(query, dict):
            q = {
                "target": query.get("target", config.target.name),
                "indication": query.get("indication", config.indication.name),
                "raw_query": query.get("raw_query", ""),
            }
        else:
            q = {"target": config.target.name, "indication": config.indication.name, "raw_query": ""}
        entries.append(
            {
                "connector_name": payload.get("connector_name", "unknown"),
                "source_name": (payload.get("provenance") or {}).get("source_name", ""),
                "mode": payload.get("mode", "live"),
                "query": q,
                "retrieved_at": payload.get("retrieved_at", utc_now_iso()),
                "record_count": len(payload.get("records", [])),
                "raw_record_ref": f"raw/{payload.get('connector_name')}_raw.json",
                "warnings": payload.get("warnings", []),
                "errors": payload.get("errors", []),
            }
        )
    path = case_dir / "source_manifest.json"
    path.write_text(
        json.dumps(
            _envelope(
                config,
                "source_manifest",
                {"entries": entries},
                generated_by="pipeline/build_sources.py",
            ),
            indent=2,
        )
        + "\n",
        encoding="utf-8",
    )
    return path


def _normalize_target_biology_record(record: dict[str, Any], connector_name: str, idx: int) -> dict[str, Any]:
    source_id = str(record.get("source_record_id") or f"{connector_name}:record:{idx}")
    source_type = str(record.get("source_type") or "relationship")
    if source_type not in {"target_biology", "compound", "relationship"}:
        source_type = "relationship"
    biology_source = connector_name if connector_name in {"opentargets", "chembl", "biothings"} else "local"
    confidence = record.get("association_score")
    if confidence is None:
        confidence = record.get("relationship_confidence")
    try:
        parsed_conf = float(confidence) if confidence is not None else None
    except (TypeError, ValueError):
        parsed_conf = None
    if parsed_conf is not None:
        parsed_conf = max(0.0, min(1.0, parsed_conf))
    return {
        "source_record_id": source_id,
        "source_type": source_type,
        "source_name": record.get("source_name") or connector_name.title(),
        "title": record.get("title") or source_id,
        "url": record.get("url"),
        "publication_date": record.get("publication_date"),
        "retrieved_at": record.get("retrieved_at") or utc_now_iso(),
        "raw_record_ref": record.get("raw_record_ref") or f"raw/{connector_name}_raw.json#records/{idx}",
        "biology_source": biology_source,
        "target_id": record.get("target_id"),
        "disease_id": record.get("disease_id"),
        "association_score": parsed_conf if source_type == "target_biology" else None,
        "molecule_chembl_id": record.get("molecule_chembl_id"),
        "mechanism_of_action": record.get("mechanism_of_action"),
        "activity_summary": record.get("activity_summary"),
        "subject": record.get("subject"),
        "predicate": record.get("predicate"),
        "object": record.get("object"),
        "relationship_confidence": parsed_conf if source_type == "relationship" else None,
    }


def build_target_biology(
    config: CaseConfig,
    case_dir: Path,
    connector_payloads: list[dict[str, Any]],
) -> Path:
    records: list[dict[str, Any]] = []
    for connector_name in ("opentargets", "chembl", "biothings"):
        payload = _connector_by_name(connector_payloads, connector_name)
        if not payload:
            continue
        for idx, raw in enumerate(payload.get("records", [])):
            if isinstance(raw, dict):
                records.append(_normalize_target_biology_record(raw, connector_name, idx))
    path = case_dir / "target_biology.json"
    path.write_text(
        json.dumps(
            _envelope(config, "target_biology", {"records": records}, generated_by="pipeline/build_sources.py"),
            indent=2,
        )
        + "\n",
        encoding="utf-8",
    )
    return path


def build_source_artifacts(
    config: CaseConfig,
    case_dir: Path,
    *,
    mode: RunMode,
    connector_payloads: list[dict[str, Any]],
) -> None:
    """Populate source JSON artifacts from live connector payloads."""
    del mode
    if connector_payloads:
        build_source_manifest(config, case_dir, connector_payloads)
        build_literature_records(config, case_dir, connector_payloads)
        build_clinical_trials(config, case_dir, connector_payloads)
        build_target_biology(config, case_dir, connector_payloads)

    for name in ("target_biology.json", "clinical_trials.json", "literature_records.json"):
        dest = case_dir / name
        if not dest.exists():
            copy_fixture_artifact(config.case_id, name, dest)
            continue
        if name.endswith(".json"):
            payload = json.loads(dest.read_text(encoding="utf-8"))
            data = payload.get("data", {})
            key = "trials" if name == "clinical_trials.json" else "records"
            if not data.get(key):
                copy_fixture_artifact(config.case_id, name, dest)
