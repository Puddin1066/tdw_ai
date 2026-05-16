/** TypeScript interfaces matching JSON schemas in schemas/. */

export const SCHEMA_VERSION = "v0.5" as const;

export type EvidenceDensity = "low" | "medium" | "high";

export type EntityType =
  | "gene"
  | "protein"
  | "disease"
  | "pathway"
  | "compound"
  | "modality"
  | "biomarker"
  | "clinical_trial"
  | "publication"
  | "organization"
  | "investigator";

export type ClaimType =
  | "mechanistic"
  | "translational"
  | "clinical"
  | "safety"
  | "biomarker"
  | "competitive"
  | "regulatory"
  | "commercial"
  | "evidence_gap";

export type SupportStatus =
  | "supported"
  | "partially_supported"
  | "unsupported"
  | "contradicted"
  | "insufficient_evidence";

export type RiskCategory =
  | "translational"
  | "clinical"
  | "biomarker"
  | "safety"
  | "competition"
  | "evidence_gap"
  | "manufacturing"
  | "regulatory";

export type RiskSeverity = "low" | "medium" | "high" | "critical";

export type ConnectorMode = "fixture" | "live";

export type BiologySource = "opentargets" | "chembl" | "biothings" | "local";

export type GraphNodeType =
  | "gene"
  | "protein"
  | "disease"
  | "pathway"
  | "compound"
  | "trial"
  | "publication"
  | "organization"
  | "biomarker"
  | "other";

export interface Provenance {
  generated_by: string;
  generated_at: string;
  input_artifacts: string[];
  model_provider: string | null;
  model_name: string | null;
  prompt_template: string | null;
  prompt_hash: string | null;
  schema_version: string;
}

export interface ArtifactEnvelope<TData> {
  artifact_type: string;
  case_id: string;
  schema_version: typeof SCHEMA_VERSION;
  generated_at: string;
  provenance: Provenance;
  data: TData;
}

export interface NamedEntity {
  name: string;
  canonical_id: string | null;
  aliases?: string[];
}

export interface CaseSources {
  pubmed: boolean;
  clinicaltrials: boolean;
  opentargets: boolean;
  chembl: boolean;
  biothings: boolean;
  local_docs: boolean;
}

export interface CaseLimits {
  max_literature_records: number;
  max_trials: number;
  max_evidence_rows: number;
}

export interface RunModeDefaults {
  fixture_allowed?: boolean;
  live_allowed?: boolean;
}

export interface CaseMetadataData {
  case_id: string;
  display_name: string;
  workflow: "translational_diligence";
  version: string;
  target: NamedEntity;
  indication: NamedEntity;
  sources: CaseSources;
  limits: CaseLimits;
  run_mode_defaults?: RunModeDefaults;
  maturity_stage?: string;
  confidence_score?: number;
  evidence_density?: EvidenceDensity;
  top_risk?: string;
}

export type CaseMetadataArtifact = ArtifactEnvelope<CaseMetadataData> & {
  artifact_type: "case_metadata";
};

export interface ConnectorQuery {
  target: string;
  indication: string;
  raw_query: string;
}

export interface ManifestEntry {
  connector_name: string;
  source_name: string;
  mode: ConnectorMode;
  query: ConnectorQuery;
  retrieved_at: string;
  record_count: number;
  raw_record_ref: string;
  source_url?: string | null;
  api_endpoint?: string | null;
  api_version?: string | null;
  errors?: string[];
  warnings?: string[];
}

export interface SourceManifestData {
  entries: ManifestEntry[];
}

export type SourceManifestArtifact = ArtifactEnvelope<SourceManifestData> & {
  artifact_type: "source_manifest";
};

export interface ExternalIds {
  entrez?: string | null;
  ensembl?: string | null;
  uniprot?: string | null;
  wikidata?: string | null;
  chembl?: string | null;
  mondo?: string | null;
  mesh?: string | null;
}

export interface NormalizedEntity {
  entity_id: string;
  entity_type: EntityType;
  canonical_name: string;
  display_name: string;
  aliases: string[];
  external_ids: ExternalIds;
  source_record_ids: string[];
  confidence: number;
  warnings?: string[];
}

export interface NormalizedEntitiesData {
  entities: NormalizedEntity[];
}

export type NormalizedEntitiesArtifact =
  ArtifactEnvelope<NormalizedEntitiesData> & {
    artifact_type: "normalized_entities";
  };

export interface SourceRecordBase {
  source_record_id: string;
  source_type: string;
  source_name: string;
  title: string;
  url?: string | null;
  publication_date?: string | null;
  retrieved_at: string;
  raw_record_ref: string;
}

export interface LiteratureRecord extends SourceRecordBase {
  source_type: "literature";
  pmid?: string | null;
  doi?: string | null;
  authors?: string[];
  journal?: string | null;
  abstract?: string | null;
  publication_types?: string[];
  mesh_terms?: string[];
}

export interface LiteratureRecordsData {
  records: LiteratureRecord[];
}

export type LiteratureRecordsArtifact =
  ArtifactEnvelope<LiteratureRecordsData> & {
    artifact_type: "literature_records";
  };

export interface ClinicalTrialRecord extends SourceRecordBase {
  source_type: "clinical_trial";
  nct_id: string;
  brief_title: string;
  official_title?: string | null;
  phase?: string | null;
  overall_status: string;
  study_type?: string | null;
  sponsor?: string | null;
  interventions?: string[];
  conditions?: string[];
  start_date?: string | null;
  completion_date?: string | null;
  enrollment_count?: number | null;
}

export interface ClinicalTrialsData {
  trials: ClinicalTrialRecord[];
}

export type ClinicalTrialsArtifact = ArtifactEnvelope<ClinicalTrialsData> & {
  artifact_type: "clinical_trials";
};

export interface TargetBiologyRecord extends SourceRecordBase {
  source_type: "target_biology" | "compound" | "relationship";
  biology_source: BiologySource;
  target_id?: string | null;
  disease_id?: string | null;
  association_score?: number | null;
  molecule_chembl_id?: string | null;
  mechanism_of_action?: string | null;
  activity_summary?: string | null;
  subject?: string | null;
  predicate?: string | null;
  object?: string | null;
  relationship_confidence?: number | null;
}

export interface TargetBiologyData {
  records: TargetBiologyRecord[];
}

export type TargetBiologyArtifact = ArtifactEnvelope<TargetBiologyData> & {
  artifact_type: "target_biology";
};

export interface QuotedEvidence {
  source_record_id: string;
  text: string;
  location: string;
}

export interface EvidenceRow {
  evidence_id: string;
  claim_text: string;
  claim_type: ClaimType;
  support_status: SupportStatus;
  confidence: number;
  source_record_ids: string[];
  quoted_evidence: QuotedEvidence[];
  limitations: string[];
}

export interface EvidenceTableData {
  rows: EvidenceRow[];
}

export type EvidenceTableArtifact = ArtifactEnvelope<EvidenceTableData> & {
  artifact_type: "evidence_table";
};

export interface ReportSection {
  section_id: string;
  title: string;
  content: string;
  evidence_ids?: string[];
}

export interface DiligenceReportData {
  title: string;
  executive_summary: string;
  overall_confidence: number;
  maturity_stage: string;
  conclusion?: string;
  sections: ReportSection[];
  cited_source_record_ids: string[];
  cited_nct_ids: string[];
  cited_pmids: string[];
  diligence_questions?: string[];
}

export type DiligenceReport = ArtifactEnvelope<DiligenceReportData> & {
  artifact_type: "diligence_report";
};

export interface RiskItem {
  risk_id: string;
  title: string;
  description: string;
  category: RiskCategory;
  severity: RiskSeverity;
  confidence: number;
  inferred: boolean;
  evidence_ids: string[];
  source_record_ids: string[];
}

export interface RiskMapData {
  risks: RiskItem[];
}

export type RiskMap = ArtifactEnvelope<RiskMapData> & {
  artifact_type: "risk_map";
};

export interface GraphNode {
  node_id: string;
  label: string;
  node_type: GraphNodeType;
  entity_id?: string | null;
  source_record_id?: string | null;
  metadata?: Record<string, string>;
}

export interface GraphEdge {
  edge_id: string;
  source: string;
  target: string;
  relationship: string;
  confidence?: number | null;
  source_record_ids?: string[];
}

export interface KnowledgeGraphData {
  nodes: GraphNode[];
  edges: GraphEdge[];
}

export type KnowledgeGraph = ArtifactEnvelope<KnowledgeGraphData> & {
  artifact_type: "knowledge_graph";
};

export interface EvaluationResult {
  evaluator_name: string;
  case_id: string;
  passed: boolean;
  score: number;
  errors: string[];
  warnings: string[];
  checked_artifacts: string[];
}

export interface EvalMetrics {
  citation_fidelity_score: number;
  unsupported_claim_count: number;
  hallucinated_trial_count: number;
  hallucinated_pmid_count: number;
  evidence_coverage_score: number;
}

export interface EvalResultsData {
  overall_passed: boolean;
  aggregate_score: number;
  evaluations: EvaluationResult[];
  metrics: EvalMetrics;
}

export type EvalResults = ArtifactEnvelope<EvalResultsData> & {
  artifact_type: "eval_results";
};

export type CaseArtifact =
  | CaseMetadataArtifact
  | SourceManifestArtifact
  | NormalizedEntitiesArtifact
  | LiteratureRecordsArtifact
  | ClinicalTrialsArtifact
  | TargetBiologyArtifact
  | EvidenceTableArtifact
  | DiligenceReport
  | RiskMap
  | KnowledgeGraph
  | EvalResults;

export type ArtifactType = CaseArtifact["artifact_type"];

/** Flattened metadata for case library cards and dashboard header. */
export interface CaseMetadata {
  case_id: string;
  display_name?: string;
  target_name: string;
  indication_name: string;
  maturity_stage: string;
  confidence_score: number;
  evidence_density: EvidenceDensity;
  top_risk: string;
  description?: string;
}

export type CaseArtifactFile =
  | "source_manifest.json"
  | "normalized_entities.json"
  | "literature_records.json"
  | "clinical_trials.json"
  | "target_biology.json"
  | "evidence_table.json"
  | "diligence_report.json"
  | "risk_map.json"
  | "knowledge_graph.json"
  | "eval_results.json";

/** PRD §12 trials table row (ClinicalTrials.gov normalized record). */
export type ClinicalTrial = ClinicalTrialRecord;

export interface CasePacket {
  metadata: CaseMetadata;
  diligenceReport: DiligenceReportData | null;
  evidenceTable: EvidenceRow[];
  clinicalTrials: ClinicalTrialRecord[];
  riskMap: RiskMapData | null;
  knowledgeGraph: KnowledgeGraphData | null;
  sourceManifest: SourceManifestData | null;
  evalResults: EvalResultsData | null;
  loadErrors: string[];
}
