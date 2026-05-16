import fs from "fs";
import path from "path";
import { fileURLToPath } from "url";

const __dirname = path.dirname(fileURLToPath(import.meta.url));
const root = path.join(__dirname, "..", "public", "data", "cases");

const cases = [
  {
    case_id: "sting_pdac",
    target_name: "STING (TMEM173)",
    indication_name: "Pancreatic cancer",
    maturity_stage: "preclinical",
    confidence_score: 0.72,
    evidence_density: "medium",
    top_risk: "Limited clinical validation of STING agonists in PDAC",
    description: "Innate immune STING pathway agonism in pancreatic ductal adenocarcinoma.",
  },
  {
    case_id: "parp_breast",
    target_name: "PARP",
    indication_name: "Breast cancer",
    maturity_stage: "clinical",
    confidence_score: 0.85,
    evidence_density: "high",
    top_risk: "Resistance mechanisms in HR-proficient tumors",
    description: "PARP inhibitor landscape in BRCA-mutant and HRD breast cancer.",
  },
  {
    case_id: "tau_alzheimers",
    target_name: "Tau",
    indication_name: "Alzheimer's disease",
    maturity_stage: "clinical",
    confidence_score: 0.58,
    evidence_density: "medium",
    top_risk: "Mixed efficacy signals across anti-tau modalities",
    description: "Tau-targeting approaches in Alzheimer's disease.",
  },
  {
    case_id: "iaip_sepsis",
    target_name: "IAIP",
    indication_name: "Sepsis",
    maturity_stage: "early clinical",
    confidence_score: 0.64,
    evidence_density: "low",
    top_risk: "Heterogeneous sepsis endpoints and trial design risk",
    description: "Inter-alpha inhibitor proteins as acute inflammatory modulators in sepsis.",
  },
];

const provenance = {
  generated_by: "web/scripts/generate-stub-cases.mjs",
  generated_at: "2026-05-15T00:00:00Z",
  input_artifacts: [],
  model_provider: null,
  model_name: null,
  prompt_template: null,
  prompt_hash: null,
  schema_version: "v0.5",
};

function envelope(artifactType, caseId, data) {
  return {
    artifact_type: artifactType,
    case_id: caseId,
    schema_version: "v0.5",
    generated_at: "2026-05-15T00:00:00Z",
    provenance,
    data,
  };
}

function writeCase(meta) {
  const dir = path.join(root, meta.case_id);
  fs.mkdirSync(dir, { recursive: true });
  const targetShort = meta.target_name.split(" ")[0];
  const nct = "NCT00000001";
  const pmid = "pubmed:38400001";

  const yaml = `case_id: ${meta.case_id}
target_name: "${meta.target_name}"
indication_name: "${meta.indication_name}"
maturity_stage: ${meta.maturity_stage}
confidence_score: ${meta.confidence_score}
evidence_density: ${meta.evidence_density}
top_risk: "${meta.top_risk}"
description: "${meta.description}"
`;
  fs.writeFileSync(path.join(dir, "metadata.yaml"), yaml);

  fs.writeFileSync(
    path.join(dir, "diligence_report.json"),
    JSON.stringify(
      envelope("diligence_report", meta.case_id, {
        title: `${targetShort} translational diligence — ${meta.indication_name}`,
        executive_summary: `${targetShort} shows translational interest in ${meta.indication_name} (${meta.evidence_density} evidence density).`,
        overall_confidence: meta.confidence_score,
        maturity_stage: meta.maturity_stage,
        conclusion: `Primary concern: ${meta.top_risk}. Fixture stub — replace with pipeline output.`,
        sections: [
          {
            section_id: "summary",
            title: "Summary",
            content: meta.description,
            evidence_ids: [`evidence:${meta.case_id}:0001`],
          },
        ],
        cited_source_record_ids: [pmid],
        cited_nct_ids: [nct],
        cited_pmids: ["38400001"],
        diligence_questions: ["What is the optimal combination strategy?"],
      }),
      null,
      2,
    ),
  );

  fs.writeFileSync(
    path.join(dir, "evidence_table.json"),
    JSON.stringify(
      envelope("evidence_table", meta.case_id, {
        rows: [
          {
            evidence_id: `evidence:${meta.case_id}:0001`,
            claim_text: `${targetShort} pathway modulation is discussed in preclinical ${meta.indication_name} models.`,
            claim_type: "mechanistic",
            support_status: "partially_supported",
            confidence: 0.75,
            source_record_ids: [pmid],
            quoted_evidence: [
              {
                source_record_id: pmid,
                text: "Stub quoted passage for fixture validation.",
                location: "abstract",
              },
            ],
            limitations: ["preclinical evidence only"],
          },
        ],
      }),
      null,
      2,
    ),
  );

  fs.writeFileSync(
    path.join(dir, "clinical_trials.json"),
    JSON.stringify(
      envelope("clinical_trials", meta.case_id, {
        trials: [
          {
            source_record_id: `clinicaltrials:${nct}`,
            source_type: "clinical_trial",
            source_name: "ClinicalTrials.gov",
            title: `Study of ${targetShort} in ${meta.indication_name}`,
            url: `https://clinicaltrials.gov/study/${nct}`,
            publication_date: null,
            retrieved_at: "2026-05-15T00:00:00Z",
            raw_record_ref: `raw/clinicaltrials_${meta.case_id}.json#0`,
            nct_id: nct,
            brief_title: `Study of ${targetShort} in ${meta.indication_name}`,
            phase: "Phase 2",
            overall_status: "recruiting",
            sponsor: "Academic Consortium (stub)",
            interventions: [`${targetShort} modulator`],
            conditions: [meta.indication_name],
          },
        ],
      }),
      null,
      2,
    ),
  );

  fs.writeFileSync(
    path.join(dir, "risk_map.json"),
    JSON.stringify(
      envelope("risk_map", meta.case_id, {
        risks: [
          {
            risk_id: `risk:${meta.case_id}:001`,
            title: meta.top_risk,
            description: meta.top_risk,
            category: "translational",
            severity: "high",
            confidence: 0.7,
            inferred: false,
            evidence_ids: [`evidence:${meta.case_id}:0001`],
            source_record_ids: [pmid],
          },
          {
            risk_id: `risk:${meta.case_id}:002`,
            title: "Evidence gaps in pivotal endpoints",
            description: "Limited prospective clinical data in this indication.",
            category: "evidence_gap",
            severity: "medium",
            confidence: 0.6,
            inferred: true,
            evidence_ids: [],
            source_record_ids: [],
          },
        ],
      }),
      null,
      2,
    ),
  );

  fs.writeFileSync(
    path.join(dir, "knowledge_graph.json"),
    JSON.stringify(
      envelope("knowledge_graph", meta.case_id, {
        nodes: [
          { node_id: "target", label: targetShort, node_type: "gene" },
          { node_id: "disease", label: meta.indication_name, node_type: "disease" },
          { node_id: "trial", label: nct, node_type: "trial" },
        ],
        edges: [
          {
            edge_id: "e1",
            source: "target",
            target: "disease",
            relationship: "associated_with",
            confidence: 0.8,
            source_record_ids: [pmid],
          },
          {
            edge_id: "e2",
            source: "trial",
            target: "target",
            relationship: "tests",
            confidence: 0.9,
            source_record_ids: [`clinicaltrials:${nct}`],
          },
        ],
      }),
      null,
      2,
    ),
  );

  fs.writeFileSync(
    path.join(dir, "source_manifest.json"),
    JSON.stringify(
      envelope("source_manifest", meta.case_id, {
        entries: [
          {
            connector_name: "pubmed",
            source_name: "PubMed",
            mode: "fixture",
            query: {
              target: targetShort,
              indication: meta.indication_name,
              raw_query: `${targetShort} AND ${meta.indication_name}`,
            },
            retrieved_at: "2026-05-15T00:00:00Z",
            record_count: 8,
            raw_record_ref: `raw/pubmed_${meta.case_id}.json`,
          },
          {
            connector_name: "clinicaltrials",
            source_name: "ClinicalTrials.gov",
            mode: "fixture",
            query: {
              target: targetShort,
              indication: meta.indication_name,
              raw_query: targetShort,
            },
            retrieved_at: "2026-05-15T00:00:00Z",
            record_count: 4,
            raw_record_ref: `raw/clinicaltrials_${meta.case_id}.json`,
          },
        ],
      }),
      null,
      2,
    ),
  );

  fs.writeFileSync(
    path.join(dir, "eval_results.json"),
    JSON.stringify(
      envelope("eval_results", meta.case_id, {
        overall_passed: true,
        aggregate_score: 0.91,
        metrics: {
          citation_fidelity_score: 0.91,
          unsupported_claim_count: 0,
          hallucinated_trial_count: 0,
          hallucinated_pmid_count: 0,
          evidence_coverage_score: 0.85,
        },
        evaluations: [
          {
            evaluator_name: "citation_fidelity",
            case_id: meta.case_id,
            passed: true,
            score: 0.91,
            errors: [],
            warnings: [],
            checked_artifacts: ["diligence_report.json", "evidence_table.json"],
          },
          {
            evaluator_name: "trial_hallucination",
            case_id: meta.case_id,
            passed: true,
            score: 1.0,
            errors: [],
            warnings: [],
            checked_artifacts: ["diligence_report.json", "clinical_trials.json"],
          },
        ],
      }),
      null,
      2,
    ),
  );

  console.log(`Wrote stub case: ${meta.case_id}`);
}

fs.mkdirSync(root, { recursive: true });
for (const meta of cases) {
  writeCase(meta);
}
