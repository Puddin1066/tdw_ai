"""Validate minimal fixture examples against JSON Schema and Pydantic models."""

from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path

import pytest
from jsonschema import Draft202012Validator
from jsonschema.exceptions import ValidationError
from referencing import Registry, Resource
from pydantic import ValidationError as PydanticValidationError

from pipeline.types import (
    ARTIFACT_MODEL_BY_TYPE,
    CaseMetadataArtifact,
    ClinicalTrialsArtifact,
    DiligenceReportArtifact,
    EvalResultsArtifact,
    EvidenceTableArtifact,
    KnowledgeGraphArtifact,
    LiteratureRecordsArtifact,
    NormalizedEntitiesArtifact,
    RiskMapArtifact,
    SourceManifestArtifact,
    TargetBiologyArtifact,
)

ROOT = Path(__file__).resolve().parents[2]
SCHEMAS_DIR = ROOT / "schemas"

ISO_TS = "2026-05-15T00:00:00Z"
CASE_ID = "sting_pdac"


def _provenance(
    generated_by: str,
    input_artifacts: list[str] | None = None,
    *,
    ai: bool = False,
) -> dict:
    return {
        "generated_by": generated_by,
        "generated_at": ISO_TS,
        "input_artifacts": input_artifacts or [],
        "model_provider": "openai" if ai else None,
        "model_name": "gpt-4.1-mini" if ai else None,
        "prompt_template": "skills/translational_diligence/prompts/report_generation.md"
        if ai
        else None,
        "prompt_hash": "sha256:placeholder" if ai else None,
        "schema_version": "v0.5",
    }


def _envelope(artifact_type: str, data: dict, provenance: dict) -> dict:
    return {
        "artifact_type": artifact_type,
        "case_id": CASE_ID,
        "schema_version": "v0.5",
        "generated_at": ISO_TS,
        "provenance": provenance,
        "data": data,
    }


def minimal_examples() -> dict[str, dict]:
    return {
        "case_metadata": _envelope(
            "case_metadata",
            {
                "case_id": CASE_ID,
                "display_name": "STING / Pancreatic Cancer",
                "workflow": "translational_diligence",
                "version": "v0.5",
                "target": {
                    "name": "STING",
                    "canonical_id": None,
                    "aliases": ["TMEM173"],
                },
                "indication": {
                    "name": "pancreatic cancer",
                    "aliases": ["PDAC"],
                },
                "sources": {
                    "pubmed": True,
                    "clinicaltrials": True,
                    "opentargets": True,
                    "chembl": True,
                    "biothings": True,
                    "local_docs": False,
                },
                "limits": {
                    "max_literature_records": 50,
                    "max_trials": 100,
                    "max_evidence_rows": 100,
                },
                "maturity_stage": "preclinical",
                "confidence_score": 0.65,
                "evidence_density": "medium",
                "top_risk": "Limited clinical validation",
            },
            _provenance("pipeline/config_loader.py", ["configs/cases/sting_pdac.yaml"]),
        ),
        "source_manifest": _envelope(
            "source_manifest",
            {
                "entries": [
                    {
                        "connector_name": "pubmed",
                        "source_name": "PubMed",
                        "mode": "fixture",
                        "query": {
                            "target": "STING",
                            "indication": "pancreatic cancer",
                            "raw_query": "(STING OR TMEM173) AND pancreatic cancer",
                        },
                        "retrieved_at": ISO_TS,
                        "record_count": 1,
                        "raw_record_ref": "raw/pubmed_raw.json",
                        "warnings": [],
                        "errors": [],
                    }
                ]
            },
            _provenance("connectors/pubmed.py", []),
        ),
        "normalized_entities": _envelope(
            "normalized_entities",
            {
                "entities": [
                    {
                        "entity_id": "gene:TMEM173",
                        "entity_type": "gene",
                        "canonical_name": "TMEM173",
                        "display_name": "STING",
                        "aliases": ["STING"],
                        "external_ids": {},
                        "source_record_ids": ["pubmed:12345678"],
                        "confidence": 0.9,
                    }
                ]
            },
            _provenance("pipeline/normalize_entities.py", ["literature_records.json"]),
        ),
        "literature_records": _envelope(
            "literature_records",
            {
                "records": [
                    {
                        "source_record_id": "pubmed:12345678",
                        "source_type": "literature",
                        "source_name": "PubMed",
                        "title": "STING pathway in pancreatic cancer",
                        "url": "https://pubmed.ncbi.nlm.nih.gov/12345678/",
                        "publication_date": "2024-01-01",
                        "retrieved_at": ISO_TS,
                        "raw_record_ref": "raw/pubmed_raw.json#records/0",
                        "pmid": "12345678",
                        "doi": None,
                        "authors": ["Smith J"],
                        "journal": "Cancer Research",
                        "abstract": "STING activation study.",
                        "publication_types": ["Journal Article"],
                        "mesh_terms": ["Pancreatic Neoplasms"],
                    }
                ]
            },
            _provenance("connectors/pubmed.py", []),
        ),
        "clinical_trials": _envelope(
            "clinical_trials",
            {
                "trials": [
                    {
                        "source_record_id": "clinicaltrials:NCT01234567",
                        "source_type": "clinical_trial",
                        "source_name": "ClinicalTrials.gov",
                        "title": "STING agonist in pancreatic cancer",
                        "url": "https://clinicaltrials.gov/study/NCT01234567",
                        "publication_date": None,
                        "retrieved_at": ISO_TS,
                        "raw_record_ref": "raw/clinicaltrials_raw.json#records/0",
                        "nct_id": "NCT01234567",
                        "brief_title": "STING agonist in pancreatic cancer",
                        "phase": "Phase 1",
                        "overall_status": "Recruiting",
                        "sponsor": "Example Pharma",
                        "interventions": ["STING agonist"],
                        "conditions": ["Pancreatic Cancer"],
                    }
                ]
            },
            _provenance("connectors/clinicaltrials.py", []),
        ),
        "target_biology": _envelope(
            "target_biology",
            {
                "records": [
                    {
                        "source_record_id": "opentargets:ENSG00000184584",
                        "source_type": "target_biology",
                        "source_name": "Open Targets",
                        "title": "TMEM173 association with pancreatic cancer",
                        "url": None,
                        "publication_date": None,
                        "retrieved_at": ISO_TS,
                        "raw_record_ref": "raw/opentargets_raw.json#records/0",
                        "biology_source": "opentargets",
                        "target_id": "ENSG00000184584",
                        "disease_id": "EFO_0002618",
                        "association_score": 0.42,
                    }
                ]
            },
            _provenance("connectors/opentargets.py", []),
        ),
        "evidence_table": _envelope(
            "evidence_table",
            {
                "rows": [
                    {
                        "evidence_id": "evidence:sting_pdac:0001",
                        "claim_text": "STING activation is associated with innate immune signaling in pancreatic cancer models.",
                        "claim_type": "mechanistic",
                        "support_status": "supported",
                        "confidence": 0.82,
                        "source_record_ids": ["pubmed:12345678"],
                        "quoted_evidence": [
                            {
                                "source_record_id": "pubmed:12345678",
                                "text": "STING activation enhanced innate immunity.",
                                "location": "abstract",
                            }
                        ],
                        "limitations": ["preclinical evidence only"],
                    }
                ]
            },
            _provenance(
                "pipeline/generate_claims.py",
                ["literature_records.json", "clinical_trials.json"],
                ai=True,
            ),
        ),
        "diligence_report": _envelope(
            "diligence_report",
            {
                "title": "STING / Pancreatic Cancer Diligence Memo",
                "executive_summary": "STING remains preclinical with emerging trial activity.",
                "overall_confidence": 0.7,
                "maturity_stage": "preclinical",
                "sections": [
                    {
                        "section_id": "mechanism",
                        "title": "Mechanism",
                        "content": "STING drives type I interferon signaling.",
                        "evidence_ids": ["evidence:sting_pdac:0001"],
                    }
                ],
                "cited_source_record_ids": ["pubmed:12345678"],
                "cited_nct_ids": ["NCT01234567"],
                "cited_pmids": ["12345678"],
            },
            _provenance(
                "pipeline/generate_report.py",
                ["evidence_table.json"],
                ai=True,
            ),
        ),
        "risk_map": _envelope(
            "risk_map",
            {
                "risks": [
                    {
                        "risk_id": "risk:sting_pdac:0001",
                        "title": "Limited clinical validation",
                        "description": "Few late-stage trials test STING agonists in PDAC.",
                        "category": "translational",
                        "severity": "high",
                        "confidence": 0.75,
                        "inferred": False,
                        "evidence_ids": ["evidence:sting_pdac:0001"],
                        "source_record_ids": ["pubmed:12345678"],
                    }
                ]
            },
            _provenance(
                "pipeline/generate_risk_map.py",
                ["evidence_table.json", "clinical_trials.json"],
                ai=True,
            ),
        ),
        "knowledge_graph": _envelope(
            "knowledge_graph",
            {
                "nodes": [
                    {
                        "node_id": "node:gene:TMEM173",
                        "label": "STING",
                        "node_type": "gene",
                        "entity_id": "gene:TMEM173",
                    },
                    {
                        "node_id": "node:disease:pdac",
                        "label": "Pancreatic Cancer",
                        "node_type": "disease",
                        "entity_id": "disease:pdac",
                    },
                ],
                "edges": [
                    {
                        "edge_id": "edge:0001",
                        "source": "node:gene:TMEM173",
                        "target": "node:disease:pdac",
                        "relationship": "associated_with",
                        "confidence": 0.42,
                        "source_record_ids": ["opentargets:ENSG00000184584"],
                    }
                ],
            },
            _provenance("pipeline/build_graph.py", ["normalized_entities.json"]),
        ),
        "eval_results": _envelope(
            "eval_results",
            {
                "overall_passed": True,
                "aggregate_score": 1.0,
                "evaluations": [
                    {
                        "evaluator_name": "trial_hallucination",
                        "case_id": CASE_ID,
                        "passed": True,
                        "score": 1.0,
                        "errors": [],
                        "warnings": [],
                        "checked_artifacts": [
                            "diligence_report.json",
                            "clinical_trials.json",
                        ],
                    }
                ],
                "metrics": {
                    "citation_fidelity_score": 1.0,
                    "unsupported_claim_count": 0,
                    "hallucinated_trial_count": 0,
                    "hallucinated_pmid_count": 0,
                    "evidence_coverage_score": 0.85,
                },
            },
            _provenance("evals/run_evals.py", ["diligence_report.json"]),
        ),
    }


SCHEMA_FILES = {
    "case_metadata": "case_metadata.schema.json",
    "source_manifest": "source_manifest.schema.json",
    "normalized_entities": "normalized_entities.schema.json",
    "literature_records": "literature_records.schema.json",
    "clinical_trials": "clinical_trials.schema.json",
    "target_biology": "target_biology.schema.json",
    "evidence_table": "evidence_table.schema.json",
    "diligence_report": "diligence_report.schema.json",
    "risk_map": "risk_map.schema.json",
    "knowledge_graph": "knowledge_graph.schema.json",
    "eval_results": "eval_results.schema.json",
}

PYDANTIC_MODELS = {
    "case_metadata": CaseMetadataArtifact,
    "source_manifest": SourceManifestArtifact,
    "normalized_entities": NormalizedEntitiesArtifact,
    "literature_records": LiteratureRecordsArtifact,
    "clinical_trials": ClinicalTrialsArtifact,
    "target_biology": TargetBiologyArtifact,
    "evidence_table": EvidenceTableArtifact,
    "diligence_report": DiligenceReportArtifact,
    "risk_map": RiskMapArtifact,
    "knowledge_graph": KnowledgeGraphArtifact,
    "eval_results": EvalResultsArtifact,
}


def _build_schema_registry() -> Registry:
    registry = Registry()
    for path in sorted(SCHEMAS_DIR.glob("*.json")):
        document = json.loads(path.read_text())
        schema_id = document["$id"]
        registry = registry.with_resource(
            schema_id,
            Resource.from_contents(document),
        )
    return registry


@pytest.fixture(scope="module")
def validators() -> dict[str, Draft202012Validator]:
    registry = _build_schema_registry()
    result: dict[str, Draft202012Validator] = {}
    for key, filename in SCHEMA_FILES.items():
        schema = json.loads((SCHEMAS_DIR / filename).read_text())
        Draft202012Validator.check_schema(schema)
        result[key] = Draft202012Validator(schema, registry=registry)
    return result


@pytest.fixture(scope="module")
def examples() -> dict[str, dict]:
    return minimal_examples()


@pytest.mark.parametrize("artifact_key", list(SCHEMA_FILES.keys()))
def test_json_schema_validation(
    artifact_key: str, validators: dict[str, Draft202012Validator], examples: dict[str, dict]
) -> None:
    payload = examples[artifact_key]
    validator = validators[artifact_key]
    errors = sorted(validator.iter_errors(payload), key=lambda e: e.message)
    assert not errors, "\n".join(e.message for e in errors)


@pytest.mark.parametrize("artifact_key", list(PYDANTIC_MODELS.keys()))
def test_pydantic_round_trip(artifact_key: str, examples: dict[str, dict]) -> None:
    payload = examples[artifact_key]
    model_cls = PYDANTIC_MODELS[artifact_key]
    model = model_cls.model_validate(payload)
    dumped = json.loads(model.model_dump_json())
    assert dumped["artifact_type"] == artifact_key
    assert dumped["case_id"] == CASE_ID
    revalidated = model_cls.model_validate(dumped)
    assert revalidated == model


def test_artifact_model_registry_covers_all_schemas() -> None:
    assert set(ARTIFACT_MODEL_BY_TYPE) == set(SCHEMA_FILES)


def test_invalid_example_rejected_by_schema(
    validators: dict[str, Draft202012Validator], examples: dict[str, dict]
) -> None:
    bad = json.loads(json.dumps(examples["evidence_table"]))
    bad["data"]["rows"][0]["claim_type"] = "not_a_real_type"
    with pytest.raises(ValidationError):
        validators["evidence_table"].validate(bad)


def test_invalid_example_rejected_by_pydantic(examples: dict[str, dict]) -> None:
    bad = json.loads(json.dumps(examples["clinical_trials"]))
    bad["data"]["trials"][0]["nct_id"] = "INVALID"
    with pytest.raises(PydanticValidationError):
        ClinicalTrialsArtifact.model_validate(bad)


def test_serialization_uses_utc_isoformat(examples: dict[str, dict]) -> None:
    model = SourceManifestArtifact.model_validate(examples["source_manifest"])
    ts = model.data.entries[0].retrieved_at
    assert ts == datetime(2026, 5, 15, 0, 0, tzinfo=timezone.utc)
