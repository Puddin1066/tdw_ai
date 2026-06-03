import fs from "fs";
import path from "path";
import yaml from "js-yaml";
import type {
  ArtifactEnvelope,
  CaseArtifactFile,
  CaseMetadataData,
  CasePacket,
  CaseMetadata,
  ClinicalTrialsData,
  ClinicalTrialRecord,
  DiligenceReportData,
  EvaluationCaseData,
  EvalResultsData,
  EvidenceRow,
  EvidenceTableData,
  GeneratedQualitativeAssessment,
  KnowledgeGraphData,
  QualitativeDimensionKey,
  QualitativeDimensionResult,
  RiCapitalMatchData,
  RiClinicalInflectionData,
  RiFinancingReadinessData,
  RiPhysicianMatchData,
  RiskMapData,
  SourceManifestData,
} from "@/types/artifacts";

const CASES_ROOT = path.join(process.cwd(), "public", "data", "cases");

export const DEMO_CASE_IDS = [
  "sting_pdac",
  "parp_breast",
  "tau_alzheimers",
  "iaip_sepsis",
] as const;

function caseDir(caseId: string): string {
  return path.join(CASES_ROOT, caseId);
}

function readJsonFile<T>(filePath: string): T | null {
  if (!fs.existsSync(filePath)) return null;
  const raw = fs.readFileSync(filePath, "utf-8");
  return JSON.parse(raw) as T;
}

function unwrap<T>(envelope: ArtifactEnvelope<T> | T): T {
  if (envelope && typeof envelope === "object" && "data" in envelope) {
    return (envelope as ArtifactEnvelope<T>).data;
  }
  return envelope as T;
}

function normalizeSourceManifestData(raw: unknown): SourceManifestData | null {
  if (!raw || typeof raw !== "object") return null;
  const data = raw as Record<string, unknown>;
  if (Array.isArray(data.entries)) {
    return data as unknown as SourceManifestData;
  }
  const legacySources = data.sources;
  if (!Array.isArray(legacySources)) return null;
  const entries = legacySources
    .filter((source): source is Record<string, unknown> => !!source && typeof source === "object")
    .map((source) => ({
      connector_name: String(source.connector_name ?? "unknown"),
      source_name: String(source.connector_name ?? "unknown"),
      mode: "fixture" as const,
      query: {
        target: "",
        indication: "",
        raw_query: String(source.query ?? ""),
      },
      retrieved_at: String(source.retrieved_at ?? ""),
      record_count: Number(source.record_count ?? 0),
      raw_record_ref: `raw/${String(source.connector_name ?? "unknown")}_raw.json`,
      warnings: [],
      errors: [],
    }));
  return { entries };
}

function fallbackConnectorsFromManifest(manifest: SourceManifestData | null): {
  fallbackConnectors: number;
  mockWarningCount: number;
} {
  const entries = manifest?.entries ?? [];
  let fallbackConnectors = 0;
  let mockWarningCount = 0;
  for (const entry of entries) {
    const warnings = entry.warnings ?? [];
    const hasMockWarning = warnings.some((warning) => warning.includes("MOCK/SYNTHETIC fallback"));
    const hasBackendFallback = (entry.backend_used ?? "").toLowerCase().includes("fallback");
    if (hasMockWarning) {
      mockWarningCount += 1;
    }
    if (hasMockWarning || hasBackendFallback) {
      fallbackConnectors += 1;
    }
  }
  return { fallbackConnectors, mockWarningCount };
}

function enrichCaseMetadataFromArtifacts(caseId: string, base: CaseMetadata): CaseMetadata {
  const evalPath = path.join(caseDir(caseId), "eval_results.json");
  const manifestPath = path.join(caseDir(caseId), "source_manifest.json");

  const evalEnvelope = readJsonFile<ArtifactEnvelope<EvalResultsData> | EvalResultsData>(evalPath);
  const manifestEnvelope = readJsonFile<ArtifactEnvelope<SourceManifestData> | SourceManifestData>(
    manifestPath,
  );
  const evalData = evalEnvelope ? unwrap(evalEnvelope) : null;
  const manifestData = manifestEnvelope ? normalizeSourceManifestData(unwrap(manifestEnvelope)) : null;

  const metrics = evalData?.metrics;
  const contractPassed =
    typeof metrics?.benchmark_contract_passed === "boolean"
      ? metrics.benchmark_contract_passed
      : undefined;
  const contractScore =
    typeof metrics?.benchmark_contract_score === "number"
      ? metrics.benchmark_contract_score
      : undefined;
  const connectorsWithRecords =
    typeof metrics?.contract_connectors_with_records === "number"
      ? metrics.contract_connectors_with_records
      : undefined;
  const totalRecords =
    typeof metrics?.contract_total_records === "number" ? metrics.contract_total_records : undefined;
  const metricFallbackCount =
    typeof metrics?.contract_fallback_entries === "number" ? metrics.contract_fallback_entries : undefined;

  const { fallbackConnectors, mockWarningCount } = fallbackConnectorsFromManifest(manifestData);
  const fallbackConnectorCount = metricFallbackCount ?? fallbackConnectors;

  return {
    ...base,
    comparability_passed: contractPassed,
    comparability_score: contractScore,
    connectors_with_records: connectorsWithRecords,
    total_records: totalRecords,
    fallback_connector_count: fallbackConnectorCount,
    mock_fallback_warning_count: mockWarningCount,
  };
}

const CONNECTOR_DEEP_FIELDS: Record<string, string[]> = {
  pubmed: ["abstract", "mesh_terms", "publication_types", "journal", "authors"],
  clinicaltrials: [
    "official_title",
    "detailed_description",
    "eligibility_criteria",
    "outcome_measures",
    "interventions",
    "conditions",
  ],
  opentargets: ["association_score", "summary", "mechanism_of_action", "pathways"],
  chembl: ["mechanism_of_action", "activity_summary", "max_phase", "synonyms"],
  biothings: ["summary", "pathway", "disease", "function"],
  uniprot: ["function", "sequence", "go_terms", "subcellular_location"],
  reactome: ["description", "events", "species", "pathway"],
  gwas: ["p_value", "effect_size", "phenotype", "study_accession"],
  pharmgkb: ["clinical_annotation", "dosing_guideline", "level_of_evidence"],
  openfda: ["boxed_warning", "warnings", "adverse_reactions", "contraindications"],
};

function hasValue(value: unknown): boolean {
  if (value === null || value === undefined) return false;
  if (typeof value === "string") return value.trim().length > 0;
  if (typeof value === "number" || typeof value === "boolean") return true;
  if (Array.isArray(value)) return value.length > 0;
  if (typeof value === "object") return Object.keys(value as Record<string, unknown>).length > 0;
  return false;
}

function recordHasDeepFields(record: Record<string, unknown>, fields: string[]): boolean {
  for (const field of fields) {
    if (hasValue(record[field])) return true;
  }
  return false;
}

function readConnectorRawRecords(caseId: string, connectorName: string): {
  records: Array<Record<string, unknown>>;
  rawPayloadPresent: boolean;
} {
  const rawPath = path.join(caseDir(caseId), "raw", `${connectorName}_raw.json`);
  const payload = readJsonFile<Record<string, unknown>>(rawPath);
  if (!payload) return { records: [], rawPayloadPresent: false };
  const records = payload.records;
  if (!Array.isArray(records)) return { records: [], rawPayloadPresent: true };
  return {
    records: records.filter((row): row is Record<string, unknown> => !!row && typeof row === "object"),
    rawPayloadPresent: true,
  };
}

function buildDepthAudit(
  caseId: string,
  manifestData: SourceManifestData | null,
): CasePacket["depthAudit"] {
  const entries = manifestData?.entries ?? [];
  const promptRuns = manifestData?.benchmark_plan?.mcp_prompt_runs ?? [];
  const attributedByConnector = new Map<string, Set<string>>();
  for (const run of promptRuns) {
    if (!run.connector_name) continue;
    const existing = attributedByConnector.get(run.connector_name) ?? new Set<string>();
    for (const sourceId of run.source_record_ids ?? []) {
      if (sourceId?.trim()) existing.add(sourceId);
    }
    attributedByConnector.set(run.connector_name, existing);
  }

  let totalRecords = 0;
  let deepRecords = 0;
  let connectorsWithRawPayload = 0;

  const byConnector = entries.map((entry) => {
    const connectorName = entry.connector_name;
    const deepFields = CONNECTOR_DEEP_FIELDS[connectorName] ?? ["title", "summary", "description", "abstract"];
    const { records, rawPayloadPresent } = readConnectorRawRecords(caseId, connectorName);
    if (rawPayloadPresent) connectorsWithRawPayload += 1;

    const recordsSourced = records.length > 0 ? records.length : entry.record_count;
    const recordsWithDeepFields =
      records.length > 0
        ? records.filter((row) => recordHasDeepFields(row, deepFields)).length
        : 0;
    const deepCoverage =
      recordsSourced > 0 ? recordsWithDeepFields / recordsSourced : 0;
    const attributedRecordCount = attributedByConnector.get(connectorName)?.size ?? 0;

    totalRecords += recordsSourced;
    deepRecords += recordsWithDeepFields;

    return {
      connectorName,
      recordsSourced,
      recordsWithDeepFields,
      deepCoverage,
      attributedRecordCount,
      rawPayloadPresent,
      sampledDeepFields: deepFields.slice(0, 4),
    };
  });

  const connectorsAudited = byConnector.length;
  const overallCoverage = totalRecords > 0 ? deepRecords / totalRecords : 0;

  return {
    overall: {
      connectorsAudited,
      connectorsWithRawPayload,
      totalRecords,
      deepRecords,
      deepCoverage: overallCoverage,
    },
    byConnector,
  };
}

export async function loadCaseArtifact<T>(
  caseId: string,
  artifactName: CaseArtifactFile,
): Promise<T | null> {
  const filePath = path.join(caseDir(caseId), artifactName);
  return readJsonFile<T>(filePath);
}

export function listCaseIds(): string[] {
  if (!fs.existsSync(CASES_ROOT)) {
    return [...DEMO_CASE_IDS];
  }
  const entries = fs
    .readdirSync(CASES_ROOT, { withFileTypes: true })
    .filter((e) => e.isDirectory())
    .map((e) => e.name)
    .sort();
  return entries.length > 0 ? entries : [...DEMO_CASE_IDS];
}

function yamlToCaseMetadata(caseId: string, raw: Record<string, unknown>): CaseMetadata {
  const dashboard = (raw.dashboard as Record<string, unknown> | undefined) ?? {};
  const target = (raw.target as { name?: string } | undefined) ?? {};
  const indication = (raw.indication as { name?: string } | undefined) ?? {};
  const benchmark = (raw.benchmark as Record<string, unknown> | undefined) ?? {};
  const run = (raw.run as Record<string, unknown> | undefined) ?? {};
  return {
    case_id: String(raw.case_id ?? caseId),
    display_name: raw.display_name as string | undefined,
    target_name: String(target.name ?? raw.target_name ?? caseId),
    indication_name: String(indication.name ?? raw.indication_name ?? "Unknown"),
    input_profile:
      raw.input_profile && typeof raw.input_profile === "object"
        ? (raw.input_profile as CaseMetadata["input_profile"])
        : undefined,
    is_benchmark: Boolean(benchmark.enabled),
    benchmark_cohort:
      benchmark.cohort === null || benchmark.cohort === undefined
        ? null
        : String(benchmark.cohort),
    maturity_stage: String(dashboard.maturity_stage ?? raw.maturity_stage ?? "unknown"),
    confidence_score: Number(dashboard.confidence_score ?? raw.confidence_score ?? 0),
    evidence_density: (dashboard.evidence_density ??
      raw.evidence_density ??
      "low") as CaseMetadata["evidence_density"],
    top_risk: String(dashboard.top_risk ?? raw.top_risk ?? "—"),
    description: raw.description as string | undefined,
    mocked_api_calls:
      typeof run.mocked_api_calls === "boolean" ? (run.mocked_api_calls as boolean) : undefined,
    using_live_api:
      typeof run.using_live_api === "boolean" ? (run.using_live_api as boolean) : undefined,
  };
}

export function loadCaseMetadata(caseId: string): CaseMetadata | null {
  const dir = caseDir(caseId);
  const yamlPath = path.join(dir, "metadata.yaml");
  const jsonPath = path.join(dir, "case_metadata.json");

  if (fs.existsSync(yamlPath)) {
    const parsed = yaml.load(fs.readFileSync(yamlPath, "utf-8")) as Record<string, unknown>;
    return enrichCaseMetadataFromArtifacts(caseId, yamlToCaseMetadata(caseId, parsed));
  }

  if (fs.existsSync(jsonPath)) {
    const parsed = readJsonFile<
      Record<string, unknown> | ArtifactEnvelope<Record<string, unknown>>
    >(jsonPath);
    if (!parsed) return null;
    const data = unwrap(parsed);
    if ("target" in data && typeof data.target === "object") {
      return enrichCaseMetadataFromArtifacts(caseId, yamlToCaseMetadata(caseId, data));
    }
    return enrichCaseMetadataFromArtifacts(caseId, data as unknown as CaseMetadata);
  }

  return null;
}

export async function loadCasePacket(caseId: string): Promise<CasePacket> {
  const loadErrors: string[] = [];
  const metadata = loadCaseMetadata(caseId);

  if (!metadata) {
    loadErrors.push(
      `Missing metadata for case "${caseId}" (metadata.yaml or case_metadata.json).`,
    );
  }

  const reportEnv = await loadCaseArtifact<
    ArtifactEnvelope<DiligenceReportData> | DiligenceReportData
  >(caseId, "diligence_report.json");
  const evidenceEnv = await loadCaseArtifact<
    ArtifactEnvelope<EvidenceTableData> | EvidenceTableData
  >(caseId, "evidence_table.json");
  const trialsEnv = await loadCaseArtifact<
    ArtifactEnvelope<ClinicalTrialsData> | ClinicalTrialsData
  >(caseId, "clinical_trials.json");
  const riskEnv = await loadCaseArtifact<ArtifactEnvelope<RiskMapData> | RiskMapData>(
    caseId,
    "risk_map.json",
  );
  const graphEnv = await loadCaseArtifact<
    ArtifactEnvelope<KnowledgeGraphData> | KnowledgeGraphData
  >(caseId, "knowledge_graph.json");
  const manifestEnv = await loadCaseArtifact<
    ArtifactEnvelope<SourceManifestData> | SourceManifestData
  >(caseId, "source_manifest.json");
  const evalEnv = await loadCaseArtifact<ArtifactEnvelope<EvalResultsData> | EvalResultsData>(
    caseId,
    "eval_results.json",
  );
  const riInflectionEnv = await loadCaseArtifact<
    ArtifactEnvelope<RiClinicalInflectionData> | RiClinicalInflectionData
  >(caseId, "ri_clinical_inflection.json");
  const riPhysicianEnv = await loadCaseArtifact<
    ArtifactEnvelope<RiPhysicianMatchData> | RiPhysicianMatchData
  >(caseId, "ri_physician_match.json");
  const riCapitalEnv = await loadCaseArtifact<
    ArtifactEnvelope<RiCapitalMatchData> | RiCapitalMatchData
  >(caseId, "ri_capital_match.json");
  const riReadinessEnv = await loadCaseArtifact<
    ArtifactEnvelope<RiFinancingReadinessData> | RiFinancingReadinessData
  >(caseId, "ri_financing_readiness.json");

  if (!reportEnv) loadErrors.push("diligence_report.json not found.");
  if (!evidenceEnv) loadErrors.push("evidence_table.json not found.");
  if (!trialsEnv) loadErrors.push("clinical_trials.json not found.");

  const evidenceData = evidenceEnv ? unwrap(evidenceEnv) : null;
  const trialsData = trialsEnv ? unwrap(trialsEnv) : null;
  const manifestData = manifestEnv ? normalizeSourceManifestData(unwrap(manifestEnv)) : null;
  const depthAudit = buildDepthAudit(caseId, manifestData);

  return {
    metadata: metadata ?? {
      case_id: caseId,
      target_name: caseId,
      indication_name: "Unknown",
      maturity_stage: "Unknown",
      confidence_score: 0,
      evidence_density: "low",
      top_risk: "Metadata unavailable",
    },
    diligenceReport: reportEnv ? unwrap(reportEnv) : null,
    evidenceTable: evidenceData?.rows ?? [],
    clinicalTrials: trialsData?.trials ?? [],
    riskMap: riskEnv ? unwrap(riskEnv) : null,
    knowledgeGraph: graphEnv ? unwrap(graphEnv) : null,
    sourceManifest: manifestData,
    evalResults: evalEnv ? unwrap(evalEnv) : null,
    riClinicalInflection: riInflectionEnv ? unwrap(riInflectionEnv) : null,
    riPhysicianMatch: riPhysicianEnv ? unwrap(riPhysicianEnv) : null,
    riCapitalMatch: riCapitalEnv ? unwrap(riCapitalEnv) : null,
    riFinancingReadiness: riReadinessEnv ? unwrap(riReadinessEnv) : null,
    depthAudit,
    loadErrors,
  };
}

function clampScore1to5(value: number): number {
  return Math.max(1, Math.min(5, Math.round(value)));
}

function severityToWeight(severity: string): number {
  switch (severity) {
    case "critical":
      return 4;
    case "high":
      return 3;
    case "medium":
      return 2;
    default:
      return 1;
  }
}

function avg(values: number[]): number {
  if (values.length === 0) return 0;
  return values.reduce((sum, value) => sum + value, 0) / values.length;
}

function collectValidSourceIds(packet: CasePacket): Set<string> {
  const ids = new Set<string>();
  for (const row of packet.evidenceTable ?? []) {
    for (const sourceId of row.source_record_ids ?? []) {
      if (sourceId?.trim()) ids.add(sourceId.trim());
    }
    for (const quote of row.quoted_evidence ?? []) {
      if (quote.source_record_id?.trim()) ids.add(quote.source_record_id.trim());
    }
  }
  for (const risk of packet.riskMap?.risks ?? []) {
    for (const sourceId of risk.source_record_ids ?? []) {
      if (sourceId?.trim()) ids.add(sourceId.trim());
    }
  }
  for (const sourceId of packet.diligenceReport?.cited_source_record_ids ?? []) {
    if (sourceId?.trim()) ids.add(sourceId.trim());
  }
  for (const run of packet.sourceManifest?.benchmark_plan?.mcp_prompt_runs ?? []) {
    for (const sourceId of run.source_record_ids ?? []) {
      if (sourceId?.trim()) ids.add(sourceId.trim());
    }
  }
  return ids;
}

function filterKnownSourceIds(candidates: string[], valid: Set<string>, limit = 4): string[] {
  const picked: string[] = [];
  for (const sourceId of candidates) {
    if (!sourceId?.trim()) continue;
    const normalized = sourceId.trim();
    if (!valid.has(normalized)) continue;
    if (picked.includes(normalized)) continue;
    picked.push(normalized);
    if (picked.length >= limit) break;
  }
  return picked;
}

function allEvidenceSourceIds(rows: EvidenceRow[]): string[] {
  const ids: string[] = [];
  for (const row of rows) {
    ids.push(...(row.source_record_ids ?? []));
    ids.push(...(row.quoted_evidence ?? []).map((item) => item.source_record_id));
  }
  return ids;
}

function dimensionResult(
  score: number,
  confidence: number,
  rationale: string,
  sourceRecordIds: string[],
): QualitativeDimensionResult {
  return {
    score_1_5: clampScore1to5(score),
    confidence_0_1: Math.max(0, Math.min(1, confidence)),
    rationale,
    source_record_ids: sourceRecordIds,
  };
}

function deriveScienceDimension(packet: CasePacket, validSourceIds: Set<string>): QualitativeDimensionResult {
  const rows = packet.evidenceTable ?? [];
  const scienceRows = rows.filter((row) =>
    ["mechanistic", "translational", "clinical", "biomarker"].includes(row.claim_type),
  );
  const supported = scienceRows.filter((row) =>
    ["supported", "partially_supported"].includes(row.support_status),
  );
  const supportRatio = scienceRows.length > 0 ? supported.length / scienceRows.length : 0;
  const avgConfidence = avg(supported.map((row) => row.confidence));
  const score = 1 + supportRatio * 2.6 + avgConfidence * 1.4;
  const sourceIds = filterKnownSourceIds(allEvidenceSourceIds(supported), validSourceIds);
  const rationale = `Supported science signals in ${supported.length}/${scienceRows.length || 1} relevant claims with average confidence ${avgConfidence.toFixed(2)}.`;
  return dimensionResult(score, Math.min(1, supportRatio * 0.6 + avgConfidence * 0.4), rationale, sourceIds);
}

function deriveDifferentiationDimension(packet: CasePacket, validSourceIds: Set<string>): QualitativeDimensionResult {
  const rows = packet.evidenceTable ?? [];
  const competitiveRows = rows.filter((row) => row.claim_type === "competitive");
  const supportedCompetitive = competitiveRows.filter((row) =>
    ["supported", "partially_supported"].includes(row.support_status),
  );
  const competitionRisks = (packet.riskMap?.risks ?? []).filter((risk) => risk.category === "competition");
  const avgCompetitionSeverity = avg(competitionRisks.map((risk) => severityToWeight(risk.severity)));
  const benchmarkTopics = packet.sourceManifest?.benchmark_plan?.comparable_topics?.length ?? 0;

  const strength = supportedCompetitive.length > 0 ? Math.min(1, supportedCompetitive.length / 4) : 0;
  const riskPenalty = avgCompetitionSeverity > 0 ? avgCompetitionSeverity / 4 : 0;
  const topicBoost = Math.min(1, benchmarkTopics / 6);
  const score = 1 + strength * 1.8 + topicBoost * 1.2 + (1 - riskPenalty) * 1.0;
  const sourceIds = filterKnownSourceIds(
    [
      ...allEvidenceSourceIds(supportedCompetitive),
      ...competitionRisks.flatMap((risk) => risk.source_record_ids ?? []),
    ],
    validSourceIds,
  );
  const rationale = `Differentiation uses ${supportedCompetitive.length} supported competitive claims, ${competitionRisks.length} competition risks, and ${benchmarkTopics} benchmark topics.`;
  const confidence = Math.min(1, 0.3 + strength * 0.4 + topicBoost * 0.3);
  return dimensionResult(score, confidence, rationale, sourceIds);
}

function trialPhaseWeight(trials: ClinicalTrialRecord[]): number {
  if (trials.some((trial) => (trial.phase ?? "").toLowerCase().includes("4"))) return 4;
  if (trials.some((trial) => (trial.phase ?? "").toLowerCase().includes("3"))) return 3;
  if (trials.some((trial) => (trial.phase ?? "").toLowerCase().includes("2"))) return 2;
  if (trials.some((trial) => (trial.phase ?? "").toLowerCase().includes("1"))) return 1;
  return 0;
}

function deriveRegulatoryDimension(packet: CasePacket, validSourceIds: Set<string>): QualitativeDimensionResult {
  const trials = packet.clinicalTrials ?? [];
  const regulatoryRisks = (packet.riskMap?.risks ?? []).filter((risk) => risk.category === "regulatory");
  const highSeverityRiskCount = regulatoryRisks.filter((risk) =>
    ["high", "critical"].includes(risk.severity),
  ).length;
  const phaseWeight = trialPhaseWeight(trials);
  const score = 1 + Math.min(1, phaseWeight / 4) * 2.2 + Math.max(0, 1 - highSeverityRiskCount / 3) * 1.8;
  const sourceIds = filterKnownSourceIds(
    [
      ...regulatoryRisks.flatMap((risk) => risk.source_record_ids ?? []),
      ...(packet.diligenceReport?.cited_source_record_ids ?? []),
    ],
    validSourceIds,
  );
  const rationale = `Regulatory posture inferred from ${trials.length} trials (phase signal ${phaseWeight}) and ${regulatoryRisks.length} regulatory risks (${highSeverityRiskCount} high/critical).`;
  const confidence = Math.min(1, 0.25 + Math.min(1, trials.length / 8) * 0.45 + Math.max(0, 1 - highSeverityRiskCount / 4) * 0.3);
  return dimensionResult(score, confidence, rationale, sourceIds);
}

function deriveExecutionDimension(packet: CasePacket, validSourceIds: Set<string>): QualitativeDimensionResult {
  const entries = packet.sourceManifest?.entries ?? [];
  const okRatio =
    entries.length > 0
      ? entries.filter((entry) => (entry.connection_status ?? "ok") === "ok").length / entries.length
      : 0;
  const connectorsWithRecords = packet.evalResults?.metrics?.contract_connectors_with_records ?? 0;
  const fallbackEntries = packet.evalResults?.metrics?.contract_fallback_entries ?? 0;
  const totalRecords = packet.evalResults?.metrics?.contract_total_records ?? 0;
  const score =
    1 +
    okRatio * 1.8 +
    Math.min(1, connectorsWithRecords / 8) * 1.2 +
    Math.min(1, totalRecords / 400) * 1.0 -
    Math.min(1, fallbackEntries / 4) * 1.0;
  const sourceIds = filterKnownSourceIds(
    [
      ...(packet.sourceManifest?.benchmark_plan?.mcp_prompt_runs ?? []).flatMap(
        (run) => run.source_record_ids ?? [],
      ),
      ...(packet.diligenceReport?.cited_source_record_ids ?? []),
    ],
    validSourceIds,
  );
  const rationale = `Execution quality uses connector health (${Math.round(okRatio * 100)}% ok), ${connectorsWithRecords} connectors with records, ${totalRecords} records, and ${fallbackEntries} fallback entries.`;
  const confidence = Math.min(1, 0.4 + okRatio * 0.4 + Math.max(0, 1 - fallbackEntries / 5) * 0.2);
  return dimensionResult(score, confidence, rationale, sourceIds);
}

function deriveStrategicFitDimension(packet: CasePacket, validSourceIds: Set<string>): QualitativeDimensionResult {
  const reportConfidence = packet.diligenceReport?.overall_confidence ?? 0;
  const questionCount = packet.diligenceReport?.diligence_questions?.length ?? 0;
  const maturity = (packet.metadata.maturity_stage ?? "").toLowerCase();
  const maturityBonus =
    maturity.includes("approved") || maturity.includes("phase 3")
      ? 1
      : maturity.includes("early-clinical") || maturity.includes("phase 2")
        ? 0.7
        : 0.4;
  const score = 1 + reportConfidence * 2.2 + Math.min(1, questionCount / 5) * 1.0 + maturityBonus * 0.8;
  const sourceIds = filterKnownSourceIds(
    [
      ...(packet.diligenceReport?.cited_source_record_ids ?? []),
      ...allEvidenceSourceIds(packet.evidenceTable ?? []),
    ],
    validSourceIds,
  );
  const rationale = `Strategic fit uses diligence confidence ${reportConfidence.toFixed(2)}, ${questionCount} tracked diligence questions, and maturity stage ${packet.metadata.maturity_stage}.`;
  const confidence = Math.min(1, 0.35 + reportConfidence * 0.45 + Math.min(1, questionCount / 5) * 0.2);
  return dimensionResult(score, confidence, rationale, sourceIds);
}

function deriveQualitativeAssessment(packet: CasePacket): GeneratedQualitativeAssessment {
  const validSourceIds = collectValidSourceIds(packet);
  const dimensions: Record<QualitativeDimensionKey, QualitativeDimensionResult> = {
    science: deriveScienceDimension(packet, validSourceIds),
    differentiation: deriveDifferentiationDimension(packet, validSourceIds),
    regulatory: deriveRegulatoryDimension(packet, validSourceIds),
    execution: deriveExecutionDimension(packet, validSourceIds),
    strategicFit: deriveStrategicFitDimension(packet, validSourceIds),
  };

  const reportSources = packet.diligenceReport?.cited_source_record_ids ?? [];
  for (const key of Object.keys(dimensions) as QualitativeDimensionKey[]) {
    if (dimensions[key].source_record_ids.length === 0) {
      dimensions[key].source_record_ids = filterKnownSourceIds(reportSources, validSourceIds, 3);
    }
  }

  return {
    generated_from: "cached_artifacts_v1",
    mocked_data_present:
      Boolean(packet.metadata.mocked_api_calls) || (packet.metadata.fallback_connector_count ?? 0) > 0,
    dimensions,
  };
}

export async function loadEvaluationCases(): Promise<EvaluationCaseData[]> {
  const caseIds = listCaseIds();
  const results = await Promise.all(
    caseIds.map(async (caseId) => {
      const packet = await loadCasePacket(caseId);
      return {
        metadata: packet.metadata,
        qualitative_assessment: deriveQualitativeAssessment(packet),
        ri_financing_readiness: packet.riFinancingReadiness,
      } satisfies EvaluationCaseData;
    }),
  );
  return results;
}

export async function loadAllCaseMetadata(): Promise<CaseMetadata[]> {
  const ids = listCaseIds();
  const results = await Promise.all(
    ids.map(async (id) => {
      const meta = loadCaseMetadata(id);
      if (meta) return meta;
      const packet = await loadCasePacket(id);
      return packet.metadata;
    }),
  );
  return results;
}
