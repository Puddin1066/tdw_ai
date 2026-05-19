"""Artifact loading and ID extraction helpers."""

from __future__ import annotations

import json
import re
from pathlib import Path
from typing import Any

import yaml

NCT_ID_PATTERN = re.compile(r"\bNCT\d{8}\b", re.IGNORECASE)
PMID_PATTERN = re.compile(r"(?:PMID[:\s]+|pubmed:)(\d{7,8})\b", re.IGNORECASE)
BARE_PMID_PATTERN = re.compile(r"\b(?<![NCTnct])\d{7,8}\b")
NAMESPACED_PMID_PATTERN = re.compile(r"pubmed:(\d{7,8})", re.IGNORECASE)

REQUIRED_ARTIFACTS = [
    "metadata.yaml",
    "source_manifest.json",
    "normalized_entities.json",
    "literature_records.json",
    "clinical_trials.json",
    "target_biology.json",
    "evidence_table.json",
    "diligence_report.md",
    "diligence_report.json",
    "risk_map.json",
    "knowledge_graph.json",
]

SUPPORTED_STATUSES = frozenset({"supported", "partially_supported"})


def load_json(path: Path) -> dict[str, Any]:
    with path.open(encoding="utf-8") as handle:
        return json.load(handle)


def load_text(path: Path) -> str:
    return path.read_text(encoding="utf-8")


def load_metadata(case_dir: Path) -> dict[str, Any]:
    with (case_dir / "metadata.yaml").open(encoding="utf-8") as handle:
        return yaml.safe_load(handle) or {}


def artifact_data(artifact: dict[str, Any]) -> Any:
    return artifact.get("data", artifact)


def case_id_from_dir(case_dir: Path) -> str:
    metadata_path = case_dir / "metadata.yaml"
    if metadata_path.exists():
        meta = load_metadata(case_dir)
        if meta.get("case_id"):
            return str(meta["case_id"])
    return case_dir.name


def missing_artifacts(case_dir: Path) -> list[str]:
    return [name for name in REQUIRED_ARTIFACTS if not (case_dir / name).exists()]


def normalize_nct(nct_id: str) -> str:
    return nct_id.upper()


def extract_nct_ids(text: str) -> set[str]:
    return {normalize_nct(match) for match in NCT_ID_PATTERN.findall(text)}


def extract_pmids(text: str) -> set[str]:
    pmids = set(PMID_PATTERN.findall(text))
    pmids.update(NAMESPACED_PMID_PATTERN.findall(text))
    for match in BARE_PMID_PATTERN.findall(text):
        if not re.search(rf"NCT\d{{0,1}}{match}", text, re.IGNORECASE):
            pmids.add(match)
    return pmids


def collect_report_text(report_json: dict[str, Any], report_md: str | None) -> str:
    chunks: list[str] = [json.dumps(report_json, ensure_ascii=False)]
    if report_md:
        chunks.append(report_md)
    data = artifact_data(report_json)
    if isinstance(data, dict):
        for key in ("executive_summary", "body_text", "conclusion"):
            value = data.get(key)
            if isinstance(value, str):
                chunks.append(value)
        claims = data.get("claims", [])
        if isinstance(claims, list):
            chunks.append(json.dumps(claims, ensure_ascii=False))
    return "\n".join(chunks)


def clinical_trial_nct_ids(clinical_trials: dict[str, Any]) -> set[str]:
    data = artifact_data(clinical_trials)
    records: list[Any] = []
    if isinstance(data, dict):
        if isinstance(data.get("records"), list):
            records.extend(data["records"])
        if isinstance(data.get("trials"), list):
            records.extend(data["trials"])
    ncts: set[str] = set()
    for record in records:
        if not isinstance(record, dict):
            continue
        nct = record.get("nct_id") or record.get("nctId")
        if isinstance(nct, str):
            ncts.add(normalize_nct(nct))
        source_id = record.get("source_record_id", "")
        if isinstance(source_id, str) and source_id.lower().startswith("clinicaltrials:"):
            ncts.add(normalize_nct(source_id.split(":", 1)[1]))
    return ncts


def literature_pmids(literature: dict[str, Any]) -> set[str]:
    data = artifact_data(literature)
    records = data.get("records", []) if isinstance(data, dict) else []
    pmids: set[str] = set()
    for record in records:
        if not isinstance(record, dict):
            continue
        pmid = record.get("pmid")
        if pmid is not None:
            pmids.add(str(pmid))
        source_id = record.get("source_record_id", "")
        if isinstance(source_id, str) and source_id.lower().startswith("pubmed:"):
            pmids.add(source_id.split(":", 1)[1])
    return pmids


def evidence_rows(evidence_table: dict[str, Any]) -> list[dict[str, Any]]:
    data = artifact_data(evidence_table)
    rows = data.get("rows", []) if isinstance(data, dict) else []
    return [row for row in rows if isinstance(row, dict)]


def report_claims(report_json: dict[str, Any]) -> list[dict[str, Any]]:
    data = artifact_data(report_json)
    if not isinstance(data, dict):
        return []
    claims = data.get("claims", [])
    return [claim for claim in claims if isinstance(claim, dict)]
