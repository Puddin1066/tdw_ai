"""Shared fixture builders for eval tests."""

from __future__ import annotations

import json
from copy import deepcopy
from pathlib import Path
from typing import Any


def write_packet(case_dir: Path, packet: dict) -> Path:
    case_dir.mkdir(parents=True, exist_ok=True)
    for name, content in packet.items():
        path = case_dir / name
        if name.endswith(".json"):
            path.write_text(json.dumps(content, indent=2) + "\n", encoding="utf-8")
        else:
            path.write_text(content, encoding="utf-8")
    return case_dir


def provenance(generated_by: str) -> dict[str, Any]:
    return {
        "generated_by": generated_by,
        "generated_at": "2026-05-15T00:00:00Z",
        "input_artifacts": [],
        "model_provider": None,
        "model_name": None,
        "prompt_template": None,
        "prompt_hash": None,
        "schema_version": "v0.5",
    }


def wrap(artifact_type: str, case_id: str, data: dict[str, Any]) -> dict[str, Any]:
    return {
        "artifact_type": artifact_type,
        "case_id": case_id,
        "schema_version": "v0.5",
        "generated_at": "2026-05-15T00:00:00Z",
        "provenance": provenance(f"tests/fixtures/cases/{case_id}"),
        "data": data,
    }


def base_packet(case_id: str = "sting_pdac") -> dict[str, Any]:
    return {
        "metadata.yaml": f"case_id: {case_id}\ndisplay_name: STING / Pancreatic Cancer\n",
        "source_manifest.json": wrap(
            "source_manifest",
            case_id,
            {"sources": [{"name": "pubmed", "record_count": 1}]},
        ),
        "normalized_entities.json": wrap(
            "normalized_entities",
            case_id,
            {"entities": [{"entity_id": "gene:TMEM173", "canonical_name": "TMEM173"}]},
        ),
        "literature_records.json": wrap(
            "literature_records",
            case_id,
            {
                "records": [
                    {
                        "source_record_id": "pubmed:38401234",
                        "source_type": "literature",
                        "source_name": "PubMed",
                        "pmid": "38401234",
                        "title": "STING signaling in PDAC models",
                        "url": "https://pubmed.ncbi.nlm.nih.gov/38401234/",
                    }
                ]
            },
        ),
        "clinical_trials.json": wrap(
            "clinical_trials",
            case_id,
            {
                "records": [
                    {
                        "source_record_id": "clinicaltrials:NCT05234567",
                        "source_type": "clinical_trial",
                        "source_name": "ClinicalTrials.gov",
                        "nct_id": "NCT05234567",
                        "title": "STING agonist in advanced pancreatic cancer",
                        "phase": "Phase 1/2",
                        "status": "Recruiting",
                    }
                ]
            },
        ),
        "target_biology.json": wrap(
            "target_biology",
            case_id,
            {"records": [{"source_record_id": "opentargets:ENSG00000184584", "target": "TMEM173"}]},
        ),
        "evidence_table.json": wrap(
            "evidence_table",
            case_id,
            {
                "rows": [
                    {
                        "evidence_id": "evidence:sting_pdac:0001",
                        "claim_text": "STING activation is associated with innate immune signaling in pancreatic cancer models.",
                        "claim_type": "mechanistic",
                        "support_status": "supported",
                        "confidence": 0.82,
                        "source_record_ids": ["pubmed:38401234"],
                        "quoted_evidence": [
                            {
                                "source_record_id": "pubmed:38401234",
                                "text": "STING pathway activation enhances anti-tumor immunity.",
                                "location": "abstract",
                            }
                        ],
                    },
                    {
                        "evidence_id": "evidence:sting_pdac:0002",
                        "claim_text": "Trial NCT05234567 evaluates a STING agonist in PDAC.",
                        "claim_type": "clinical",
                        "support_status": "supported",
                        "confidence": 0.9,
                        "source_record_ids": ["clinicaltrials:NCT05234567"],
                        "quoted_evidence": [],
                    },
                ]
            },
        ),
        "diligence_report.json": wrap(
            "diligence_report",
            case_id,
            {
                "title": "STING / PDAC translational diligence",
                "summary": "Evidence supports innate immune engagement; trial NCT05234567 is recruiting.",
                "claims": [
                    {
                        "claim_id": "report:sting_pdac:0001",
                        "evidence_id": "evidence:sting_pdac:0001",
                        "text": "STING activation is associated with innate immune signaling in pancreatic cancer models.",
                        "support_status": "supported",
                        "citations": {
                            "source_record_ids": ["pubmed:38401234"],
                            "pmids": ["38401234"],
                        },
                    },
                    {
                        "claim_id": "report:sting_pdac:0002",
                        "evidence_id": "evidence:sting_pdac:0002",
                        "text": "Trial NCT05234567 evaluates a STING agonist in PDAC.",
                        "support_status": "supported",
                        "citations": {
                            "source_record_ids": ["clinicaltrials:NCT05234567"],
                            "nct_ids": ["NCT05234567"],
                        },
                    },
                ],
            },
        ),
        "diligence_report.md": (
            "# STING / PDAC Diligence\n\n"
            "PubMed record 38401234 supports mechanistic engagement. "
            "Clinical trial NCT05234567 is recruiting.\n"
        ),
        "risk_map.json": wrap(
            "risk_map",
            case_id,
            {
                "risks": [
                    {
                        "risk_id": "risk:sting_pdac:0001",
                        "category": "translational",
                        "description": "Limited clinical validation",
                        "confidence": 0.7,
                        "evidence_ids": ["evidence:sting_pdac:0001"],
                    }
                ]
            },
        ),
        "knowledge_graph.json": wrap(
            "knowledge_graph",
            case_id,
            {
                "nodes": [{"id": "gene:TMEM173", "label": "STING"}],
                "edges": [],
            },
        ),
    }


def bad_nct_packet() -> dict[str, Any]:
    packet = deepcopy(base_packet("sting_pdac_bad_nct"))
    packet["metadata.yaml"] = "case_id: sting_pdac_bad_nct\ndisplay_name: STING / PDAC (bad NCT)\n"
    for artifact_name in (
        "source_manifest.json",
        "normalized_entities.json",
        "literature_records.json",
        "clinical_trials.json",
        "target_biology.json",
        "evidence_table.json",
        "diligence_report.json",
        "risk_map.json",
        "knowledge_graph.json",
    ):
        packet[artifact_name]["case_id"] = "sting_pdac_bad_nct"
    report = packet["diligence_report.json"]["data"]
    report["executive_summary"] = "Trial NCT99999999 is falsely cited."
    report["claims"].append(
        {
            "claim_id": "report:sting_pdac_bad_nct:0003",
            "evidence_id": "evidence:sting_pdac:0099",
            "text": "Fabricated trial NCT99999999 is active in PDAC.",
            "support_status": "supported",
            "citations": {"nct_ids": ["NCT99999999"]},
        }
    )
    packet["diligence_report.md"] = (
        "# STING / PDAC Diligence (bad fixture)\n\n"
        "This memo incorrectly cites NCT99999999.\n"
    )
    return packet
