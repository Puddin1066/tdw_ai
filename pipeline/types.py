"""Pydantic v2 models matching JSON schemas in schemas/."""

from __future__ import annotations

from datetime import datetime
from enum import StrEnum
from typing import Generic, Literal, TypeVar

from pydantic import BaseModel, ConfigDict, Field

SCHEMA_VERSION = "v0.5"


class EvidenceDensity(StrEnum):
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"


class EntityType(StrEnum):
    GENE = "gene"
    PROTEIN = "protein"
    DISEASE = "disease"
    PATHWAY = "pathway"
    COMPOUND = "compound"
    MODALITY = "modality"
    BIOMARKER = "biomarker"
    CLINICAL_TRIAL = "clinical_trial"
    PUBLICATION = "publication"
    ORGANIZATION = "organization"
    INVESTIGATOR = "investigator"


class ClaimType(StrEnum):
    MECHANISTIC = "mechanistic"
    TRANSLATIONAL = "translational"
    CLINICAL = "clinical"
    SAFETY = "safety"
    BIOMARKER = "biomarker"
    COMPETITIVE = "competitive"
    REGULATORY = "regulatory"
    COMMERCIAL = "commercial"
    EVIDENCE_GAP = "evidence_gap"


class SupportStatus(StrEnum):
    SUPPORTED = "supported"
    PARTIALLY_SUPPORTED = "partially_supported"
    UNSUPPORTED = "unsupported"
    CONTRADICTED = "contradicted"
    INSUFFICIENT_EVIDENCE = "insufficient_evidence"


class RiskCategory(StrEnum):
    TRANSLATIONAL = "translational"
    CLINICAL = "clinical"
    BIOMARKER = "biomarker"
    SAFETY = "safety"
    COMPETITION = "competition"
    EVIDENCE_GAP = "evidence_gap"
    MANUFACTURING = "manufacturing"
    REGULATORY = "regulatory"


class RiskSeverity(StrEnum):
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    CRITICAL = "critical"


class ConnectorMode(StrEnum):
    FIXTURE = "fixture"
    LIVE = "live"


class BiologySource(StrEnum):
    OPENTARGETS = "opentargets"
    CHEMBL = "chembl"
    BIOTHINGS = "biothings"
    LOCAL = "local"


class GraphNodeType(StrEnum):
    GENE = "gene"
    PROTEIN = "protein"
    DISEASE = "disease"
    PATHWAY = "pathway"
    COMPOUND = "compound"
    TRIAL = "trial"
    PUBLICATION = "publication"
    ORGANIZATION = "organization"
    BIOMARKER = "biomarker"
    OTHER = "other"


class Provenance(BaseModel):
    model_config = ConfigDict(extra="forbid")

    generated_by: str
    generated_at: datetime
    input_artifacts: list[str]
    model_provider: str | None = None
    model_name: str | None = None
    prompt_template: str | None = None
    prompt_hash: str | None = None
    schema_version: str


class NamedEntity(BaseModel):
    model_config = ConfigDict(extra="forbid")

    name: str
    canonical_id: str | None = None
    aliases: list[str] = Field(default_factory=list)


class CaseSources(BaseModel):
    model_config = ConfigDict(extra="forbid")

    pubmed: bool
    clinicaltrials: bool
    opentargets: bool
    chembl: bool
    biothings: bool
    local_docs: bool


class CaseLimits(BaseModel):
    model_config = ConfigDict(extra="forbid")

    max_literature_records: int = Field(ge=1)
    max_trials: int = Field(ge=1)
    max_evidence_rows: int = Field(ge=1)


class RunModeDefaults(BaseModel):
    model_config = ConfigDict(extra="forbid")

    fixture_allowed: bool = True
    live_allowed: bool = True


class CaseMetadataData(BaseModel):
    model_config = ConfigDict(extra="forbid")

    case_id: str
    display_name: str
    workflow: Literal["translational_diligence"] = "translational_diligence"
    version: str
    target: NamedEntity
    indication: NamedEntity
    sources: CaseSources
    limits: CaseLimits
    run_mode_defaults: RunModeDefaults | None = None
    maturity_stage: str | None = None
    confidence_score: float | None = Field(default=None, ge=0, le=1)
    evidence_density: EvidenceDensity | None = None
    top_risk: str | None = None


class ConnectorQuery(BaseModel):
    model_config = ConfigDict(extra="forbid")

    target: str
    indication: str
    raw_query: str


class ManifestEntry(BaseModel):
    model_config = ConfigDict(extra="forbid")

    connector_name: str
    source_name: str
    mode: ConnectorMode
    query: ConnectorQuery
    retrieved_at: datetime
    record_count: int = Field(ge=0)
    raw_record_ref: str
    source_url: str | None = None
    api_endpoint: str | None = None
    api_version: str | None = None
    errors: list[str] = Field(default_factory=list)
    warnings: list[str] = Field(default_factory=list)


class SourceManifestData(BaseModel):
    model_config = ConfigDict(extra="forbid")

    entries: list[ManifestEntry]


class ExternalIds(BaseModel):
    model_config = ConfigDict(extra="forbid")

    entrez: str | None = None
    ensembl: str | None = None
    uniprot: str | None = None
    wikidata: str | None = None
    chembl: str | None = None
    mondo: str | None = None
    mesh: str | None = None


class NormalizedEntity(BaseModel):
    model_config = ConfigDict(extra="forbid")

    entity_id: str
    entity_type: EntityType
    canonical_name: str
    display_name: str
    aliases: list[str]
    external_ids: ExternalIds
    source_record_ids: list[str]
    confidence: float = Field(ge=0, le=1)
    warnings: list[str] = Field(default_factory=list)


class NormalizedEntitiesData(BaseModel):
    model_config = ConfigDict(extra="forbid")

    entities: list[NormalizedEntity]


class SourceRecordBase(BaseModel):
    model_config = ConfigDict(extra="forbid")

    source_record_id: str
    source_type: str
    source_name: str
    title: str
    url: str | None = None
    publication_date: str | None = None
    retrieved_at: datetime
    raw_record_ref: str


class LiteratureRecord(SourceRecordBase):
    source_type: Literal["literature"] = "literature"
    pmid: str | None = None
    doi: str | None = None
    authors: list[str] = Field(default_factory=list)
    journal: str | None = None
    abstract: str | None = None
    publication_types: list[str] = Field(default_factory=list)
    mesh_terms: list[str] = Field(default_factory=list)


class LiteratureRecordsData(BaseModel):
    model_config = ConfigDict(extra="forbid")

    records: list[LiteratureRecord]


class ClinicalTrialRecord(SourceRecordBase):
    source_type: Literal["clinical_trial"] = "clinical_trial"
    nct_id: str = Field(pattern=r"^NCT[0-9]{8}$")
    brief_title: str
    official_title: str | None = None
    phase: str | None = None
    overall_status: str
    study_type: str | None = None
    sponsor: str | None = None
    interventions: list[str] = Field(default_factory=list)
    conditions: list[str] = Field(default_factory=list)
    start_date: str | None = None
    completion_date: str | None = None
    enrollment_count: int | None = Field(default=None, ge=0)


class ClinicalTrialsData(BaseModel):
    model_config = ConfigDict(extra="forbid")

    trials: list[ClinicalTrialRecord]


class TargetBiologyRecord(SourceRecordBase):
    source_type: Literal["target_biology", "compound", "relationship"]
    biology_source: BiologySource
    target_id: str | None = None
    disease_id: str | None = None
    association_score: float | None = Field(default=None, ge=0, le=1)
    molecule_chembl_id: str | None = None
    mechanism_of_action: str | None = None
    activity_summary: str | None = None
    subject: str | None = None
    predicate: str | None = None
    object: str | None = None
    relationship_confidence: float | None = Field(default=None, ge=0, le=1)


class TargetBiologyData(BaseModel):
    model_config = ConfigDict(extra="forbid")

    records: list[TargetBiologyRecord]


class QuotedEvidence(BaseModel):
    model_config = ConfigDict(extra="forbid")

    source_record_id: str
    text: str
    location: str


class EvidenceRow(BaseModel):
    model_config = ConfigDict(extra="forbid")

    evidence_id: str
    claim_text: str
    claim_type: ClaimType
    support_status: SupportStatus
    confidence: float = Field(ge=0, le=1)
    source_record_ids: list[str]
    quoted_evidence: list[QuotedEvidence]
    limitations: list[str]


class EvidenceTableData(BaseModel):
    model_config = ConfigDict(extra="forbid")

    rows: list[EvidenceRow]


class ReportSection(BaseModel):
    model_config = ConfigDict(extra="forbid")

    section_id: str
    title: str
    content: str
    evidence_ids: list[str] = Field(default_factory=list)


class DiligenceReportData(BaseModel):
    model_config = ConfigDict(extra="forbid")

    title: str
    executive_summary: str
    overall_confidence: float = Field(ge=0, le=1)
    maturity_stage: str
    conclusion: str | None = None
    sections: list[ReportSection]
    cited_source_record_ids: list[str]
    cited_nct_ids: list[str]
    cited_pmids: list[str]
    diligence_questions: list[str] = Field(default_factory=list)


class RiskItem(BaseModel):
    model_config = ConfigDict(extra="forbid")

    risk_id: str
    title: str
    description: str
    category: RiskCategory
    severity: RiskSeverity
    confidence: float = Field(ge=0, le=1)
    inferred: bool
    evidence_ids: list[str]
    source_record_ids: list[str]


class RiskMapData(BaseModel):
    model_config = ConfigDict(extra="forbid")

    risks: list[RiskItem] = Field(max_length=10)


class GraphNode(BaseModel):
    model_config = ConfigDict(extra="forbid")

    node_id: str
    label: str
    node_type: GraphNodeType
    entity_id: str | None = None
    source_record_id: str | None = None
    metadata: dict[str, str] = Field(default_factory=dict)


class GraphEdge(BaseModel):
    model_config = ConfigDict(extra="forbid")

    edge_id: str
    source: str
    target: str
    relationship: str
    confidence: float | None = Field(default=None, ge=0, le=1)
    source_record_ids: list[str] = Field(default_factory=list)


class KnowledgeGraphData(BaseModel):
    model_config = ConfigDict(extra="forbid")

    nodes: list[GraphNode]
    edges: list[GraphEdge]


class EvaluationResult(BaseModel):
    model_config = ConfigDict(extra="forbid")

    evaluator_name: str
    case_id: str
    passed: bool
    score: float = Field(ge=0, le=1)
    errors: list[str]
    warnings: list[str]
    checked_artifacts: list[str]


class EvalMetrics(BaseModel):
    model_config = ConfigDict(extra="forbid")

    citation_fidelity_score: float = Field(ge=0, le=1)
    unsupported_claim_count: int = Field(ge=0)
    hallucinated_trial_count: int = Field(ge=0)
    hallucinated_pmid_count: int = Field(ge=0)
    evidence_coverage_score: float = Field(ge=0, le=1)


class EvalResultsData(BaseModel):
    model_config = ConfigDict(extra="forbid")

    overall_passed: bool
    aggregate_score: float = Field(ge=0, le=1)
    evaluations: list[EvaluationResult]
    metrics: EvalMetrics


TData = TypeVar("TData", bound=BaseModel)


class ArtifactEnvelope(BaseModel, Generic[TData]):
    """PRD §24.7 artifact wrapper."""

    model_config = ConfigDict(extra="forbid")

    artifact_type: str
    case_id: str
    schema_version: Literal["v0.5"] = SCHEMA_VERSION
    generated_at: datetime
    provenance: Provenance
    data: TData


class CaseMetadataArtifact(ArtifactEnvelope[CaseMetadataData]):
    artifact_type: Literal["case_metadata"] = "case_metadata"


class SourceManifestArtifact(ArtifactEnvelope[SourceManifestData]):
    artifact_type: Literal["source_manifest"] = "source_manifest"


class NormalizedEntitiesArtifact(ArtifactEnvelope[NormalizedEntitiesData]):
    artifact_type: Literal["normalized_entities"] = "normalized_entities"


class LiteratureRecordsArtifact(ArtifactEnvelope[LiteratureRecordsData]):
    artifact_type: Literal["literature_records"] = "literature_records"


class ClinicalTrialsArtifact(ArtifactEnvelope[ClinicalTrialsData]):
    artifact_type: Literal["clinical_trials"] = "clinical_trials"


class TargetBiologyArtifact(ArtifactEnvelope[TargetBiologyData]):
    artifact_type: Literal["target_biology"] = "target_biology"


class EvidenceTableArtifact(ArtifactEnvelope[EvidenceTableData]):
    artifact_type: Literal["evidence_table"] = "evidence_table"


class DiligenceReportArtifact(ArtifactEnvelope[DiligenceReportData]):
    artifact_type: Literal["diligence_report"] = "diligence_report"


class RiskMapArtifact(ArtifactEnvelope[RiskMapData]):
    artifact_type: Literal["risk_map"] = "risk_map"


class KnowledgeGraphArtifact(ArtifactEnvelope[KnowledgeGraphData]):
    artifact_type: Literal["knowledge_graph"] = "knowledge_graph"


class EvalResultsArtifact(ArtifactEnvelope[EvalResultsData]):
    artifact_type: Literal["eval_results"] = "eval_results"


ARTIFACT_MODEL_BY_TYPE: dict[str, type[ArtifactEnvelope[BaseModel]]] = {
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

# --- Pipeline orchestration helpers (Workstream A) ---

from dataclasses import dataclass, field
from pathlib import Path

RunMode = Literal["fixture", "live"]

REQUIRED_ARTIFACTS: tuple[str, ...] = (
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
    "eval_results.json",
)


@dataclass(frozen=True)
class TargetConfig:
    name: str
    canonical_id: str | None = None
    aliases: list[str] = field(default_factory=list)


@dataclass(frozen=True)
class IndicationConfig:
    name: str
    aliases: list[str] = field(default_factory=list)


@dataclass(frozen=True)
class SourcesConfig:
    pubmed: bool = False
    clinicaltrials: bool = False
    opentargets: bool = False
    chembl: bool = False
    biothings: bool = False
    local_docs: bool = False


@dataclass(frozen=True)
class LimitsConfig:
    max_literature_records: int = 50
    max_trials: int = 100
    max_evidence_rows: int = 100


@dataclass(frozen=True)
class CaseConfig:
    case_id: str
    display_name: str
    workflow: str
    version: str
    target: TargetConfig
    indication: IndicationConfig
    sources: SourcesConfig
    limits: LimitsConfig
    run_mode_defaults: RunModeDefaults
    config_path: Path | None = None

    def to_metadata_dict(self) -> dict[str, object]:
        return {
            "case_id": self.case_id,
            "display_name": self.display_name,
            "workflow": self.workflow,
            "version": self.version,
            "target": {
                "name": self.target.name,
                "canonical_id": self.target.canonical_id,
                "aliases": list(self.target.aliases),
            },
            "indication": {
                "name": self.indication.name,
                "aliases": list(self.indication.aliases),
            },
            "sources": {
                "pubmed": self.sources.pubmed,
                "clinicaltrials": self.sources.clinicaltrials,
                "opentargets": self.sources.opentargets,
                "chembl": self.sources.chembl,
                "biothings": self.sources.biothings,
                "local_docs": self.sources.local_docs,
            },
            "limits": {
                "max_literature_records": self.limits.max_literature_records,
                "max_trials": self.limits.max_trials,
                "max_evidence_rows": self.limits.max_evidence_rows,
            },
        }


@dataclass
class ConnectorResult:
    connector_name: str
    case_id: str
    mode: RunMode
    query: dict[str, object]
    retrieved_at: str
    records: list[dict[str, object]] = field(default_factory=list)
    errors: list[str] = field(default_factory=list)
    warnings: list[str] = field(default_factory=list)
    provenance: dict[str, object] = field(default_factory=dict)

    def to_dict(self) -> dict[str, object]:
        return {
            "connector_name": self.connector_name,
            "case_id": self.case_id,
            "mode": self.mode,
            "query": self.query,
            "retrieved_at": self.retrieved_at,
            "records": self.records,
            "errors": self.errors,
            "warnings": self.warnings,
            "provenance": self.provenance,
        }


def repo_root() -> Path:
    return Path(__file__).resolve().parents[1]


def fixture_case_dir(case_id: str) -> Path:
    return repo_root() / "tests" / "fixtures" / "cases" / case_id


def generated_case_dir(case_id: str) -> Path:
    return repo_root() / "generated" / "cases" / case_id


def web_case_dir(case_id: str) -> Path:
    return repo_root() / "web" / "public" / "data" / "cases" / case_id
