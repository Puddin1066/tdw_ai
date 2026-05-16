Version: v0.7

Date: 2026-05-15

Status: Canonical implementation PRD draft

Owner: Jay Round

## 0. Implementation Contract

This PRD is written so multiple Cursor agents can build the product in parallel. Each module must expose explicit file paths, schemas, function contracts, fixture data, test commands, and acceptance criteria. No agent should depend on private assumptions. If a module needs another module, it must depend only on the documented interface.

The PRD is the source of truth. Cursor agents should not invent additional product scope unless that scope is added here first.

## 1. Product Definition

Build a static-first, AI-assisted translational diligence workbench that accepts arbitrary target-indication pairs and generates reproducible, evidence-grounded intelligence packages for life-science diligence workflows.

The product is not a chatbot. It is a structured scientific workflow system that converts heterogeneous biomedical sources into auditable artifacts: reports, evidence tables, risk maps, clinical-trial landscapes, knowledge graphs, source manifests, and evaluation outputs.

## 2. Primary Positioning

Primary positioning: reusable scientific AI workflow infrastructure.

Secondary use case: translational diligence for investors, BD teams, pharma scouts, research operations groups, and translational science teams.

Tertiary use case: optional regional ecosystem intelligence overlays, including Rhode Island-linked translational technologies, institutions, investigators, startups, grants, patents, and relationships.

## 3. Non-Negotiable Design Principles

1. Static-first artifact generation.
2. Structured outputs over conversational outputs.
3. Evidence-first synthesis.
4. Every material claim must map to evidence rows.
5. AI enriches and synthesizes; it is not treated as a source of truth.
6. All artifacts must be reproducible from config plus source snapshots.
7. Frontend must run entirely from static artifacts in MVP.
8. No monolithic prompt may generate all artifacts in one pass.
9. Each module must have fixture-based tests.
10. Interfaces must be stable enough for parallel agent development.

## 3A. Scope Control and Job-Description Alignment Gate

The objective of this project is to service the Anthropic Applied AI / Life Sciences job positioning. The PRD must not expand into a general biotech platform, investment platform, regional atlas, or broad product company roadmap unless that scope directly strengthens the job demonstration.

### 3A.1 Primary Objective

Build a portfolio-grade, static-first scientific AI workflow platform that demonstrates the ability to design and implement:

- tool-using scientific workflows
- structured AI synthesis
- evidence-grounded outputs
- provenance-aware artifacts
- evaluation and hallucination checks
- frontend presentation of AI-generated scientific intelligence
- modular architecture suitable for parallel agent development

The system should be impressive because it shows applied AI engineering judgment, not because it accumulates unrelated biotech features.

### 3A.2 Scope Admission Test

Any proposed feature must answer yes to at least one of these questions:

1. Does it demonstrate applied AI workflow engineering?
2. Does it improve evidence grounding, provenance, or evaluation?
3. Does it make the static end-to-end demo more credible?
4. Does it help explain life-science AI deployment to a technical interviewer?
5. Does it improve the ability of multiple agents to build the repo correctly?
6. Does it strengthen the Anthropic job narrative?

If the answer is no, the feature is out of scope.

### 3A.3 Explicitly Deferred Scope

The following are deferred unless explicitly re-admitted by the scope admission test:

- Rhode Island regional atlas features
- investor CRM features
- user accounts and authentication
- editable dashboards
- runtime chat as primary interface
- broad startup/company databases
- grant-tracking products
- patent landscape products
- live collaborative workspaces
- paid SaaS packaging
- custom model training
- large-scale data crawling
- production data warehouse design
- general-purpose biotech search engine

These may be valuable later, but they are not required to win the job-positioning objective.

### 3A.4 MVP Scope Boundary

The MVP should remain limited to:

- four static target-indication case packets
- one polished static frontend
- connector abstractions with fixture mode
- one optional live retrieval path
- build-time AI synthesis
- source-linked evidence table
- report, risk map, trial table, knowledge graph, source manifest, and eval panel
- deterministic tests and schema validation
- launch kit for Cursor-style repo generation

### 3A.5 Portfolio Narrative Requirement

The final repo should communicate this narrative:

```
I built a static-first scientific workflow system that uses AI to synthesize biomedical evidence into auditable artifacts, with tool abstractions, provenance, evals, and a polished frontend. It is designed as applied AI infrastructure for life-science workflows, not as a generic chatbot or biotech dashboard.
```

## 4. Parallel Workstreams and File Ownership

Agents must obey the file ownership rules below. Agents may read any file but may only modify files explicitly listed under their workstream unless the PRD is updated.

### Workstream A: Backend Pipeline

Owner agent: backend-pipeline-agent

May modify:

- pipeline/
- generated/
- tests/pipeline/

Must not modify:

- web/
- connectors/ except through documented interfaces
- schemas/ except via schema-agent approval

Responsibilities:

- Parse YAML run configs.
- Execute connector retrieval.
- Save raw connector outputs.
- Normalize connector results into case artifacts.
- Generate case packet folders.
- Copy validated artifacts into frontend public directory.
- Provide CLI commands for local execution.

Primary files:

- pipeline/run_workflow.py
- pipeline/config_loader.py
- pipeline/artifact_writer.py
- pipeline/run_registry.py
- pipeline/normalize_entities.py
- pipeline/build_graph.py
- pipeline/`types.py`

Acceptance criteria:

- `python -m pipeline.run_workflow --config configs/cases/sting_pdac.yaml --mode fixture` produces a complete artifact folder.
- Pipeline runs without frontend.
- Pipeline can run with mocked connector responses.
- Pipeline exits nonzero if any required artifact is missing.

### Workstream B: Connector Layer

Owner agent: connectors-agent

May modify:

- connectors/
- tests/connectors/
- tests/fixtures/connectors/

Must not modify:

- pipeline/ except after interface review
- web/
- evals/

Responsibilities:

- Implement public data source adapters.
- Return standardized connector outputs.
- Provide mocked fixtures for offline development.
- Preserve raw API responses.
- Normalize obvious source metadata such as PMIDs, NCT IDs, ChEMBL IDs, and source URLs.

Primary files:

- connectors/`base.py`
- connectors/`pubmed.py`
- connectors/`clinicaltrials.py`
- connectors/`opentargets.py`
- connectors/`chembl.py`
- connectors/`biothings.py`
- connectors/local_docs.py
- tests/connectors/

Acceptance criteria:

- Each connector implements `fetch(config: dict) -> ConnectorResult`.
- Each connector has fixture tests.
- Each connector can run in fixture mode without external API keys.
- Each connector returns errors and warnings in the ConnectorResult envelope rather than throwing unhandled exceptions for recoverable source failures.

### Workstream C: AI Synthesis and Skill Layer

Owner agent: synthesis-agent

May modify:

- skills/
- pipeline/generate_report.py
- pipeline/generate_claims.py
- pipeline/generate_risk_map.py
- pipeline/generate_questions.py
- tests/synthesis/

Must not modify:

- connectors/
- web/
- schemas/ except via schema-agent approval

Responsibilities:

- Define the translational diligence skill.
- Generate structured report JSON and Markdown.
- Generate evidence table, risks, maturity scores, diligence questions, and executive summary.
- Preserve provenance for all generated claims.
- Use build-time OpenAI calls only in MVP.

Primary files:

- skills/translational_diligence/`SKILL.md`
- skills/translational_diligence/output_schema.json
- skills/translational_diligence/prompts/claim_extraction.md
- skills/translational_diligence/prompts/report_generation.md
- skills/translational_diligence/prompts/risk_mapping.md
- pipeline/generate_report.py
- pipeline/generate_claims.py
- pipeline/generate_risk_map.py
- pipeline/generate_questions.py

Acceptance criteria:

- Synthesis can run against static fixture artifacts.
- Output validates against JSON schemas.
- Each generated claim includes at least one evidence reference or is marked `unsupported`.
- Unsupported claims are flagged by eval layer.

### Workstream D: Evaluation and Audit Layer

Owner agent: evals-agent

May modify:

- evals/
- tests/evals/

Must not modify:

- connectors/
- web/
- skills/ except by request

Responsibilities:

- Evaluate citation fidelity.
- Detect unsupported claims.
- Detect hallucinated trial IDs.
- Score evidence coverage.
- Generate `eval_results.json`.

Primary files:

- evals/citation_fidelity.py
- evals/unsupported_claims.py
- evals/trial_hallucination.py
- evals/evidence_coverage.py
- evals/run_evals.py

Acceptance criteria:

- Every case has `eval_results.json`.
- Any NCT ID in report must exist in `clinical_trials.json`.
- Any PMID cited in report must exist in `literature_records.json`.
- Any claim marked `supported` must cite at least one source record or retrieved snippet.
- Eval tests run without OpenAI calls.

### Workstream E: Frontend Application

Owner agent: frontend-agent

May modify:

- web/
- tests/frontend/ if created

Must not modify:

- pipeline/
- connectors/
- evals/
- schemas/ except generated TypeScript types after schema-agent approval

Responsibilities:

- Build static Next.js app.
- Load case packets from generated JSON/Markdown.
- Render case library, dashboard, evidence table, trials, graph, sources, and eval panels.
- Use polished scientific cockpit UX, not chatbot-first UX.

Primary files:

- web/app/page.tsx
- web/app/cases/[caseId]/page.tsx
- web/components/CaseCard.tsx
- web/components/ExecutiveSnapshot.tsx
- web/components/EvidenceTable.tsx
- web/components/TrialsTable.tsx
- web/components/RiskMap.tsx
- web/components/KnowledgeGraph.tsx
- web/components/SourceManifest.tsx
- web/components/EvalPanel.tsx
- web/types/artifacts.ts

Acceptance criteria:

- Frontend works using only static files from `web/public/data/cases/`.
- Frontend has no runtime dependency on OpenAI or biomedical APIs.
- Four demo case cards render from fixture data.
- Case dashboard renders all seven tabs.
- Missing optional fields produce graceful empty states, not crashes.

### Workstream F: Shared Types and Schemas

Owner agent: schema-agent

May modify:

- schemas/
- web/types/artifacts.ts
- pipeline/`types.py`
- tests/schemas/

Must not modify:

- connector implementations
- frontend components beyond generated type files
- synthesis prompts

Responsibilities:

- Define canonical JSON schemas.
- Define matching Python dataclasses or Pydantic models.
- Define matching TypeScript types.
- Ensure frontend and backend agree on artifact shapes.

Primary files:

- schemas/case_metadata.schema.json
- schemas/source_manifest.schema.json
- schemas/normalized_entities.schema.json
- schemas/literature_records.schema.json
- schemas/clinical_trials.schema.json
- schemas/target_biology.schema.json
- schemas/evidence_table.schema.json
- schemas/diligence_report.schema.json
- schemas/risk_map.schema.json
- schemas/knowledge_graph.schema.json
- schemas/eval_results.schema.json
- web/types/artifacts.ts
- pipeline/`types.py`

Acceptance criteria:

- All generated JSON validates against schemas.
- TypeScript types match JSON schemas.
- Python types can serialize and deserialize each artifact.
- Fixture data passes validation.

## 5. Build Dependency DAG

Agents should build according to this dependency graph:

1. Schema definitions
2. Fixture data
3. Connector interface and mock connector outputs
4. Pipeline artifact writer
5. Normalization and graph builder
6. Synthesis modules
7. Evaluation modules
8. Frontend static renderer
9. End-to-end workflow command
10. CI validation

Hard dependency rules:

- Frontend depends on schemas and fixture artifacts, not live pipeline completion.
- Evaluation depends on generated artifacts, not frontend.
- Synthesis depends on normalized source artifacts, not frontend.
- Connectors depend only on config and connector base types.
- Pipeline orchestrates modules but must not contain source-specific business logic.

## 6. Static-First Architecture

Build-time flow:

1. Load YAML config.
2. Resolve target and indication aliases.
3. Fetch source records through connectors.
4. Save immutable raw data.
5. Normalize entities.
6. Run AI synthesis modules.
7. Run audit and evaluation modules.
8. Write static artifacts.
9. Copy artifacts into frontend public data directory.
10. Build static frontend.

Runtime flow:

1. User opens static frontend.
2. User selects a case.
3. Frontend loads JSON/Markdown from static files.
4. UI renders report, evidence, trials, graph, risks, sources, and evals.

No runtime LLM calls in MVP.

## 7. Repository Layout

```
translational-diligence-workbench/
  README.md
  MASTER_PRD.md
  pyproject.toml
  package.json
  .env.example

  configs/
    cases/
      sting_pdac.yaml
      parp_breast.yaml
      tau_alzheimers.yaml
      iaip_sepsis.yaml

  connectors/
    base.py
    pubmed.py
    clinicaltrials.py
    opentargets.py
    chembl.py
    biothings.py
    local_docs.py

  pipeline/
    run_workflow.py
    config_loader.py
    normalize_entities.py
    generate_report.py
    generate_claims.py
    generate_risk_map.py
    generate_questions.py
    build_graph.py
    artifact_writer.py
    run_registry.py
    provenance.py
    types.py

  skills/
    translational_diligence/
      SKILL.md
      output_schema.json
      prompts/
        claim_extraction.md
        report_generation.md
        risk_mapping.md
        diligence_questions.md
      templates/
        diligence_report.md
        evidence_table.md
        risk_map.md

  schemas/
    case_metadata.schema.json
    source_manifest.schema.json
    normalized_entities.schema.json
    literature_records.schema.json
    clinical_trials.schema.json
    target_biology.schema.json
    evidence_table.schema.json
    diligence_report.schema.json
    risk_map.schema.json
    knowledge_graph.schema.json
    eval_results.schema.json

  evals/
    run_evals.py
    citation_fidelity.py
    unsupported_claims.py
    trial_hallucination.py
    evidence_coverage.py

  generated/
    cases/

  tests/
    fixtures/
      cases/
        sting_pdac/
        parp_breast/
        tau_alzheimers/
        iaip_sepsis/
      connectors/
    connectors/
    pipeline/
    schemas/
    evals/
    synthesis/

  web/
    app/
      page.tsx
      cases/[caseId]/page.tsx
    components/
      CaseCard.tsx
      ExecutiveSnapshot.tsx
      EvidenceTable.tsx
      TrialsTable.tsx
      RiskMap.tsx
      KnowledgeGraph.tsx
      SourceManifest.tsx
      EvalPanel.tsx
    public/
      data/
        cases/
    types/
      artifacts.ts
```

## 8. Case Packet Contract

Each target-indication case must generate a folder:

`generated/cases/{case_id}/`

Required artifacts:

1. `metadata.yaml` — run configuration and target/indication metadata.
2. `source_manifest.json` — source queries, timestamps, counts, provenance.
3. `normalized_entities.json` — target, disease, drug, gene, trial, paper, and institution entities.
4. `literature_records.json` — PubMed, bioRxiv, medRxiv, and local-document records.
5. `clinical_trials.json` — ClinicalTrials.gov records.
6. `target_biology.json` — Open Targets, ChEMBL, BioThings outputs.
7. `evidence_table.json` — claim-level evidence rows with citations.
8. `diligence_report.md` — human-readable memo.
9. `diligence_report.json` — structured memo representation.
10. `risk_map.json` — translational, clinical, biomarker, safety, competition, and evidence risks.
11. `knowledge_graph.json` — nodes and edges for frontend graph visualization.
12. `eval_results.json` — citation audit, unsupported claims, hallucinated trial checks, coverage metrics.

Minimum demo: 4 case packets, 12 artifacts each, 48 generated files total.

Initial demo cases:

- STING / pancreatic cancer
- PARP / breast cancer
- tau / Alzheimer’s disease
- IAIP / sepsis

## 9. Shared Interface: ConnectorResult

Every connector returns this normalized envelope:

```json
{
  "connector_name": "pubmed",
  "case_id": "sting_pdac",
  "query": {
    "target": "STING",
    "indication": "pancreatic cancer",
    "raw_query": "STING OR TMEM173 AND pancreatic cancer"
  },
  "retrieved_at": "2026-05-15T00:00:00Z",
  "records": [],
  "errors": [],
  "warnings": []
}
```

ConnectorResult requirements:

- `connector_name` must be stable and lowercase.
- `case_id` must match metadata case ID.
- `retrieved_at` must be ISO 8601 UTC.
- `records` may be empty only if a warning explains why.
- `errors` are fatal connector failures.
- `warnings` are recoverable data gaps.

## 10. Provenance Contract

Every generated artifact except raw source snapshots must include or reference provenance metadata.

Required provenance fields:

```json
{
  "generated_by": "pipeline/generate_risk_map.py",
  "generated_at": "2026-05-15T00:00:00Z",
  "input_artifacts": ["evidence_table.json", "clinical_trials.json"],
  "model_provider": "openai",
  "model_name": "gpt-4.1-mini",
  "prompt_template": "skills/translational_diligence/prompts/risk_mapping.md",
  "prompt_hash": "sha256:placeholder",
  "schema_version": "v0.3"
}
```

If an artifact is not AI-generated, `model_provider`, `model_name`, and `prompt_hash` must be null.

## 11. Frontend UX Contract

Frontend pages:

- `/` — Case Library
- `/cases/[caseId]` — Case Dashboard

Case Dashboard tabs:

1. Summary
2. Evidence
3. Trials
4. Risk Map
5. Graph
6. Sources
7. Eval

The UI should feel like a scientific diligence cockpit, not a chatbot.

Minimum visual requirements:

- Case cards with target, indication, maturity, confidence, evidence density, and top risk.
- Executive snapshot with generated conclusion and confidence labels.
- Evidence table with claim, source, evidence type, confidence, citation link.
- Trials table with NCT ID, phase, status, sponsor, intervention, condition.
- Risk map chart using Recharts.
- Knowledge graph using Cytoscape.js or React Flow.
- Eval panel with citation fidelity score, unsupported claim count, hallucinated trial count.

Frontend component props must use typed artifact objects, not untyped `any`.

## 12. Frontend Component API Requirements

`CaseCard` props:

- `caseId: string`
- `targetName: string`
- `indicationName: string`
- `maturityStage: string`
- `confidenceScore: number`
- `evidenceDensity: "low" | "medium" | "high"`
- `topRisk: string`

`ExecutiveSnapshot` props:

- `report: DiligenceReport`
- `riskMap: RiskMap`
- `evalResults: EvalResults`

`EvidenceTable` props:

- `evidenceRows: EvidenceRow[]`

`TrialsTable` props:

- `trials: ClinicalTrial[]`

`KnowledgeGraph` props:

- `graph: KnowledgeGraph`

`SourceManifest` props:

- `manifest: SourceManifest`

`EvalPanel` props:

- `evalResults: EvalResults`

## 13. AI Usage Contract

MVP uses OpenAI API at build time only.

Permitted model tasks:

- Claim extraction
- Evidence synthesis
- Report generation
- Risk mapping
- Diligence question generation
- Structured JSON cleanup

Forbidden MVP behavior:

- Runtime chat as primary interface
- Unsupported biological claims
- Claims without source references
- Monolithic prompt producing all artifacts in one pass
- Treating model output as factual without evidence links

Recommended model split:

- High-level report synthesis: GPT-4.1 or equivalent high-quality model.
- Extraction, JSON cleanup, and risk categorization: GPT-4.1-mini or equivalent cheaper model.
- Evals should be deterministic first; model-assisted evals are Phase 2.

## 14. Prompt Contract Requirements

Each prompt template must declare:

- Purpose
- Input artifacts
- Required output artifact
- Required schema
- Citation rules
- Failure behavior
- Maximum output size

Example prompt contract:

```
Prompt: risk_mapping.md
Inputs:
- evidence_table.json
- clinical_trials.json
- target_biology.json
Output:
- risk_map.json
Rules:
- Produce maximum 10 risks.
- Every risk must cite at least one evidence row or be marked inferred.
- Use categories: translational, clinical, biomarker, safety, competition, evidence_gap, manufacturing, regulatory.
- If evidence is insufficient, output low-confidence risk rather than inventing support.
```

## 15. Evaluation Gates

A case packet is not valid unless:

- All 12 required artifacts exist.
- All JSON artifacts validate against schemas.
- Every report claim appears in `evidence_table.json`.
- Every supported claim has at least one citation.
- Every NCT ID mentioned in report exists in `clinical_trials.json`.
- Every PMID cited in report exists in `literature_records.json`.
- Eval results render in frontend.
- Frontend build succeeds using copied static artifacts.

## 16. Fixture Strategy

Fixture data is mandatory.

Required fixture cases:

- `tests/fixtures/cases/sting_pdac/`
- `tests/fixtures/cases/parp_breast/`
- `tests/fixtures/cases/tau_alzheimers/`
- `tests/fixtures/cases/iaip_sepsis/`

Each fixture case must include:

- raw connector samples
- normalized connector output
- all 12 required final artifacts
- expected eval results

Fixture mode must allow the entire app to run without:

- OpenAI API key
- PubMed access
- ClinicalTrials.gov access
- Open Targets access
- ChEMBL access
- BioThings access

## 17. CLI Requirements

Required commands:

```bash
python -m pipeline.run_workflow --config configs/cases/sting_pdac.yaml --mode fixture
python -m pipeline.run_workflow --config configs/cases/sting_pdac.yaml --mode live
python -m evals.run_evals --case generated/cases/sting_pdac
python -m pipeline.artifact_writer --copy-to-web generated/cases/sting_pdac
npm run dev --prefix web
npm run build --prefix web
```

Acceptance criteria:

- Commands must be documented in README.
- Fixture commands must succeed without external API keys.
- Live commands may require `.env`.

## 18. CI Requirements

Minimum CI checks:

- Python lint/type check.
- Connector unit tests.
- Schema validation tests.
- Eval tests.
- Fixture pipeline generation test.
- Frontend TypeScript check.
- Frontend build.

CI must not require paid API calls.

## 19. Repo Foundation Requirements

Use custom orchestration as the core. Do not fork a giant agent repo as the main foundation.

Direct dependencies / foundations:

- Next.js for frontend.
- Tailwind and shadcn/ui for UI primitives.
- Recharts for charts.
- Cytoscape.js or React Flow for graph visualization.
- OpenAI API for build-time synthesis.
- Pydantic or equivalent for Python validation.
- JSON Schema for cross-language artifact validation.

Borrow or integrate selectively:

- PaperQA2 for scientific document QA and citation-aware RAG patterns.
- BioThings Explorer concepts for federated biomedical relationships.
- LangGraph as architectural inspiration for stateful workflows, but avoid over-abstracting MVP.

Do not use as MVP foundation:

- AutoGPT-style agent frameworks.
- Generic chatbot templates.
- No-code AI workflow builders.
- Heavy Neo4j/GraphRAG infrastructure unless Phase 2.

## 20. MVP Completion Definition

MVP is complete when:

1. Four target-indication cases generate successfully.
2. Each case produces all 12 artifacts.
3. Frontend renders all four cases from static files.
4. Eval panel displays audit results for every case.
5. README includes setup, generation, validation, and deployment instructions.
6. The entire system can be cloned and run locally with fixture data without external API keys.
7. The system can optionally run live connector/API mode with environment variables.
8. CI passes without paid API calls.
9. At least one live-generated case has been manually reviewed for scientific plausibility.

## 21. Open Decisions

- Whether to include Rhode Island regional overlay in MVP or Phase 2.
- Whether to use Cytoscape.js or React Flow as the first graph library.
- Whether PaperQA2 is integrated in MVP or Phase 2.
- Whether BioThings Explorer is used directly or via custom BioThings connector.
- Whether frontend should support user-created target-indication forms in MVP or only static demo cases.
- Whether to use Pydantic v2 as canonical Python schema layer.

## 22. Parallel-Agent Convergence Model

The system must be buildable by multiple Cursor agents working independently and then converging through contract-first integration.

### 22.1 Core Rule

Agents do not coordinate through assumptions. Agents coordinate through schemas, fixtures, file ownership boundaries, CLI contracts, and acceptance tests.

### 22.2 Parallel Development Pattern

Each workstream must support independent implementation using fixtures before live integration.

Required pattern:

1. Schema-agent defines artifact contracts.
2. Fixture-agent or schema-agent creates representative fixture artifacts.
3. Frontend-agent builds against fixture artifacts only.
4. Connector-agent builds against mocked and live source responses.
5. Pipeline-agent builds orchestration against connector interface, not source internals.
6. Synthesis-agent builds against normalized fixture artifacts.
7. Evals-agent builds against generated fixture artifacts.
8. Integration-agent runs full pipeline and resolves contract mismatches.

### 22.3 Agent Interface Boundaries

Each agent must publish or maintain a local `AGENT_HANDOFF.md` in its owned directory describing:

- files modified
- interfaces consumed
- interfaces produced
- commands to test its module
- assumptions made
- unresolved blockers
- expected downstream consumers

Required handoff files:

- `schemas/AGENT_HANDOFF.md`
- `connectors/AGENT_HANDOFF.md`
- `pipeline/AGENT_HANDOFF.md`
- `skills/AGENT_HANDOFF.md`
- `evals/AGENT_HANDOFF.md`
- `web/AGENT_HANDOFF.md`

### 22.4 Integration Gates

A module cannot be considered complete merely because it runs locally. It must pass its integration gate.

Integration gates:

- Schemas: all fixture artifacts validate.
- Connectors: all connectors return `ConnectorResult` in fixture mode.
- Pipeline: fixture case generates all 12 required artifacts.
- Synthesis: generated report JSON, evidence table, and risk map validate against schemas.
- Evals: invalid claims and hallucinated trial IDs are detected in test fixtures.
- Frontend: static build succeeds using only `web/public/data/cases/`.
- End-to-end: one fixture case runs from config to rendered frontend without external API keys.

### 22.5 Contract-First Development

When a downstream agent needs data that does not exist, it must not invent a private shape. It must request or define a schema update first.

Allowed temporary workaround:

- add a clearly marked fixture field under `experimental` only if the schema permits it.

Forbidden workaround:

- adding undocumented fields directly to frontend or pipeline code.

### 22.6 Holistic Assembly Requirement

Final assembly is complete only when the following command chain succeeds from a clean clone:

```bash
python -m pipeline.run_workflow --config configs/cases/sting_pdac.yaml --mode fixture
python -m evals.run_evals --case generated/cases/sting_pdac
python -m pipeline.artifact_writer --copy-to-web generated/cases/sting_pdac
npm run build --prefix web
```

The same architecture must then support the other fixture cases without code changes:

```bash
python -m pipeline.run_workflow --config configs/cases/parp_breast.yaml --mode fixture
python -m pipeline.run_workflow --config configs/cases/tau_alzheimers.yaml --mode fixture
python -m pipeline.run_workflow --config configs/cases/iaip_sepsis.yaml --mode fixture
```

### 22.7 Merge Conflict Policy

If two agents need to modify the same file, the PRD must identify which agent owns the file. Non-owner agents should propose changes through handoff notes or schema updates rather than editing directly.

High-risk shared files:

- `pipeline/types.py`
- `web/types/artifacts.ts`
- `schemas/*.schema.json`
- `README.md`
- `MASTER_PRD.md`

These files should be modified only by the designated owner or integration-agent.

### 22.8 Integration-Agent Role

A dedicated integration-agent should be responsible for final holistic assembly.

Integration-agent may modify:

- `README.md`
- package scripts
- CI configuration
- cross-module import paths
- fixture copy scripts
- non-domain glue code

Integration-agent must not silently change:

- schema semantics
- prompt behavior
- connector normalization logic
- evaluation scoring rules

Those require PRD revision.

## 23. Change Tracking Protocol

Every future PRD revision must include:

- version number
- date
- sections changed
- summary of changes
- rationale
- superseded assumptions
- new open questions

The canonical PRD is revised in place, but major versions should also be snapshotted as child pages or exported to Git once the repo exists.

## 24. Formal Interface Contracts

This section defines the implementation contracts that all agents must obey. These contracts are intentionally explicit so backend, frontend, connector, synthesis, eval, and integration agents can build independently and converge.

### 24.1 Contract Categories

The system has eight required contract categories:

1. Case config contract
2. Connector contract
3. Source record contract
4. Entity normalization contract
5. Artifact contract
6. LLM provider contract
7. Prompt contract
8. Evaluation contract

A change to any contract is a PRD-level change and must increment the version number.

### 24.2 Case Config Contract

Every case config must live at:

`configs/cases/{case_id}.yaml`

Required fields:

```yaml
case_id: sting_pdac
display_name: STING / Pancreatic Cancer
workflow: translational_diligence
version: v0.5

target:
  name: STING
  canonical_id: null
  aliases:
    - TMEM173
    - Stimulator of Interferon Genes

indication:
  name: pancreatic cancer
  aliases:
    - pancreatic ductal adenocarcinoma
    - PDAC

sources:
  pubmed: true
  clinicaltrials: true
  opentargets: true
  chembl: true
  biothings: true
  local_docs: false

limits:
  max_literature_records: 50
  max_trials: 100
  max_evidence_rows: 100

run_mode_defaults:
  fixture_allowed: true
  live_allowed: true
```

Validation rules:

- `case_id` must be lowercase snake_case.
- `workflow` must equal `translational_diligence` for MVP.
- `target.name` and `indication.name` are required.
- Source booleans must be explicit.
- Limits must be positive integers.

### 24.3 Connector Contract

Every connector must implement:

```python
class BaseConnector(Protocol):
    name: str

    def fetch(self, config: CaseConfig, mode: Literal["fixture", "live"]) -> ConnectorResult:
        ...
```

Every connector returns `ConnectorResult`:

```json
{
  "connector_name": "pubmed",
  "case_id": "sting_pdac",
  "mode": "fixture",
  "query": {
    "target": "STING",
    "indication": "pancreatic cancer",
    "raw_query": "(STING OR TMEM173) AND pancreatic cancer"
  },
  "retrieved_at": "2026-05-15T00:00:00Z",
  "records": [],
  "errors": [],
  "warnings": [],
  "provenance": {
    "source_name": "PubMed",
    "source_url": "https://pubmed.ncbi.nlm.nih.gov/",
    "api_endpoint": null,
    "api_version": null
  }
}
```

Connector rules:

- Do not throw unhandled exceptions for recoverable source failures.
- Return fatal failures in `errors`.
- Return partial data with `warnings` if possible.
- Preserve raw source payloads under `generated/cases/{case_id}/raw/{connector_name}_raw.json`.
- Do not perform AI synthesis inside connectors.

### 24.4 External API Endpoint Contracts

MVP connector endpoint specs must be documented in each connector file and in `connectors/AGENT_HANDOFF.md`.

Required sources:

PubMed:

- Base: NCBI E-utilities
- Search: `esearch.fcgi`
- Fetch: `efetch.fcgi`
- Required normalized IDs: PMID, DOI when available

ClinicalTrials.gov:

- Base: ClinicalTrials.gov API v2
- Required normalized IDs: NCT ID
- Required fields: status, phase, sponsor, interventions, conditions, start date, completion date if available

Open Targets:

- Base: Open Targets Platform API
- Required normalized fields: target ID, disease ID, association score if available

ChEMBL:

- Base: ChEMBL web resource client or REST API
- Required normalized fields: molecule ID, mechanism, target ID, activity summary if available

BioThings:

- Base: BioThings APIs or BioThings Explorer adapter
- Required normalized fields: subject, predicate, object, source, confidence when available

Endpoint implementations must include:

- base URL
- auth requirements
- pagination strategy
- rate-limit assumption
- retry policy
- timeout policy
- fixture file path

### 24.5 Source Record Contract

All source records must normalize into one of these source record types:

- `LiteratureRecord`
- `ClinicalTrialRecord`
- `TargetBiologyRecord`
- `CompoundRecord`
- `RelationshipRecord`
- `LocalDocumentRecord`

Minimum shared fields:

```json
{
  "source_record_id": "pubmed:12345678",
  "source_type": "literature",
  "source_name": "PubMed",
  "title": "string",
  "url": "string_or_null",
  "publication_date": "string_or_null",
  "retrieved_at": "2026-05-15T00:00:00Z",
  "raw_record_ref": "raw/pubmed_raw.json#records/0"
}
```

Rules:

- IDs must be globally namespaced: `pubmed:PMID`, `clinicaltrials:NCT_ID`, `chembl:CHEMBL_ID`.
- Records must retain a pointer to raw source data.
- Records may not contain model-generated conclusions.

### 24.6 Entity Normalization Contract

All normalized entities must follow this shape:

```json
{
  "entity_id": "gene:TMEM173",
  "entity_type": "gene",
  "canonical_name": "TMEM173",
  "display_name": "STING",
  "aliases": ["STING", "Stimulator of Interferon Genes"],
  "external_ids": {
    "entrez": null,
    "ensembl": null,
    "uniprot": null,
    "wikidata": null,
    "chembl": null,
    "mondo": null,
    "mesh": null
  },
  "source_record_ids": ["pubmed:12345678"],
  "confidence": 0.9
}
```

Allowed `entity_type` values for MVP:

- gene
- protein
- disease
- pathway
- compound
- modality
- biomarker
- clinical_trial
- publication
- organization
- investigator

Rules:

- Entity IDs must be stable within a case.
- The same biological entity should not appear under multiple canonical IDs if aliases can resolve it.
- Ambiguous entities must include lower confidence and warning metadata.

### 24.7 Artifact Contract

All generated case artifacts must follow this wrapper pattern unless the artifact is Markdown:

```json
{
  "artifact_type": "evidence_table",
  "case_id": "sting_pdac",
  "schema_version": "v0.5",
  "generated_at": "2026-05-15T00:00:00Z",
  "provenance": {},
  "data": {}
}
```

Rules:

- Frontend reads only validated artifact JSON from `web/public/data/cases/{case_id}/`.
- Pipeline writes canonical artifacts to `generated/cases/{case_id}/`.
- Artifact copy to frontend must happen only after schema validation.
- Markdown artifacts must have a paired JSON artifact when used by frontend.

### 24.8 Evidence Row Contract

`evidence_table.json` data rows must follow:

```json
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
      "text": "short extracted support passage",
      "location": "abstract"
    }
  ],
  "limitations": ["preclinical evidence only"]
}
```

Allowed `claim_type` values:

- mechanistic
- translational
- clinical
- safety
- biomarker
- competitive
- regulatory
- commercial
- evidence_gap

Allowed `support_status` values:

- supported
- partially_supported
- unsupported
- contradicted
- insufficient_evidence

### 24.9 LLM Provider Contract

All model calls must go through a provider abstraction. Synthesis code must not call OpenAI directly.

Required interface:

```python
class LLMProvider(Protocol):
    provider_name: str

    def generate_json(
        self,
        prompt: str,
        schema: dict,
        temperature: float,
        max_output_tokens: int,
        metadata: dict
    ) -> LLMResponse:
        ...
```

`LLMResponse` contract:

```json
{
  "provider_name": "openai",
  "model_name": "gpt-4.1-mini",
  "output_json": {},
  "raw_text": null,
  "usage": {
    "input_tokens": 0,
    "output_tokens": 0,
    "estimated_cost_usd": 0.0
  },
  "finish_reason": "stop",
  "errors": [],
  "warnings": []
}
```

Required providers:

- `MockProvider` for fixture and CI mode.
- `OpenAIProvider` for live build-time synthesis.

Phase 2 providers:

- `AnthropicProvider`
- local model provider

Rules:

- CI must use `MockProvider` only.
- All live model calls must write provenance metadata.
- All generated JSON must validate against schema before being accepted.

### 24.10 Prompt Contract

Each prompt file must begin with a contract header:

```
Prompt Name: risk_mapping
Purpose: Generate translational risk map.
Input Artifacts: evidence_table.json, clinical_trials.json, target_biology.json
Output Artifact: risk_map.json
Output Schema: schemas/risk_map.schema.json
Allowed Claim Sources: evidence_table.source_record_ids only
Failure Behavior: Return insufficient_evidence risk if support is weak.
Max Output Tokens: 4000
```

Prompt rules:

- Prompts must forbid unsupported claims.
- Prompts must ask the model to emit structured JSON only.
- Prompts must distinguish evidence-supported claims from inferred risks.
- Prompts must instruct the model to preserve uncertainty.
- Prompts must not ask the model to browse the web.

### 24.11 Evaluation Contract

Every evaluator must expose:

```python
def evaluate(case_dir: Path) -> EvaluationResult:
    ...
```

`EvaluationResult` minimum fields:

```json
{
  "evaluator_name": "trial_hallucination",
  "case_id": "sting_pdac",
  "passed": true,
  "score": 1.0,
  "errors": [],
  "warnings": [],
  "checked_artifacts": ["diligence_report.json", "clinical_trials.json"]
}
```

Required evaluators:

- citation_fidelity
- unsupported_claims
- trial_hallucination
- evidence_coverage
- schema_validation
- provenance_completeness

Hard fail conditions:

- invalid JSON schema
- hallucinated NCT ID
- hallucinated PMID
- missing provenance on generated artifacts
- frontend build failure

### 24.12 Frontend Data Loading Contract

Frontend may load data only from:

`/data/cases/{case_id}/{artifact_name}.json`

Required frontend data loader:

```tsx
async function loadCaseArtifact<T>(caseId: string, artifactName: string): Promise<T>
```

Rules:

- Components must not fetch external APIs.
- Components must not call LLM providers.
- Components must use typed artifact objects.
- Missing optional data must render empty states.
- Missing required artifacts must render a visible error state.

### 24.13 MCP-Style Tool Contract

Connectors should be designed so they can later become MCP tools.

Each connector must document:

- tool name
- input schema
- output schema
- side effects
- authentication requirements
- rate limits
- example call
- example response

MVP does not require a fully running MCP server, but connector interfaces must be compatible with future MCP wrapping.

### 24.14 Contract Change Process

Any change to a contract must include:

- affected contract name
- reason for change
- downstream modules affected
- migration required
- fixture updates required
- schema version bump if artifact shape changes

Contract changes cannot be made silently inside implementation code.

## 25. Efficient Development Guidelines

This section exists to prevent overbuilding, agent drift, dependency sprawl, and broken end-to-end assembly. The project should be built efficiently by prioritizing interfaces, fixtures, vertical slices, and deterministic tests before live integrations or advanced features.

### 25.1 Development Philosophy

Build the thinnest complete system first, then deepen modules behind stable contracts.

Efficient development means:

- one working vertical slice before broad feature expansion
- fixture mode before live API mode
- schemas before implementation details
- static frontend before dynamic interaction
- deterministic evals before model-assisted evals
- simple orchestration before agent frameworks
- visible end-to-end demo before infrastructure hardening

The goal is not to maximize architecture. The goal is to reach a credible, testable, Anthropic-relevant demo quickly without sacrificing future extensibility.

### 25.2 MVP Vertical Slice Rule

The first implementation target is one full fixture case from config to frontend:

`configs/cases/sting_pdac.yaml -> generated/cases/sting_pdac/* -> web/public/data/cases/sting_pdac/* -> rendered case dashboard`

No additional live connector, model provider, graph enhancement, or dynamic UI feature should be prioritized until this vertical slice works.

### 25.3 Build Order for Efficient Development

Recommended build order:

1. Repo scaffold and placeholder files
2. JSON schemas and TypeScript/Python types
3. Fixture case packets for four cases
4. Static frontend rendering fixture data
5. Pipeline artifact validation and copy-to-web flow
6. Mock connector mode
7. Deterministic evaluation suite
8. Mock LLM provider and synthesis stubs
9. One live connector at a time
10. OpenAI live synthesis mode
11. End-to-end live case generation

This order minimizes unknowns and lets frontend, backend, schemas, and evals proceed in parallel.

### 25.4 Anti-Overbuilding Rules

Do not add the following in MVP unless explicitly promoted by PRD revision:

- user authentication
- database-backed user accounts
- realtime collaboration
- runtime chat as primary UI
- Neo4j or managed graph database
- hosted vector database
- autonomous multi-agent planning loops
- Kubernetes
- background job queues
- payment systems
- editable dashboards
- large-scale crawling
- custom model training
- fine-tuning

Acceptable MVP substitutes:

- static JSON instead of database
- fixture mode instead of live API mode
- simple Python orchestration instead of LangGraph runtime
- static graph payload instead of graph database
- mock provider instead of paid model call in CI
- local file cache instead of Redis

### 25.5 Dependency Budget

Every dependency must justify itself. Agents should prefer standard library and simple libraries unless a dependency directly improves the demo.

Required or preferred dependencies:

- Python: pydantic, requests/httpx, pytest, jsonschema or pydantic validation, pyyaml
- Frontend: Next.js, TypeScript, Tailwind, shadcn/ui, Recharts, Cytoscape.js or React Flow
- AI: OpenAI SDK behind provider abstraction

Avoid in MVP:

- heavy workflow engines
- unnecessary ORMs
- vector databases
- distributed task queues
- multi-provider abstraction frameworks unless simple
- UI template libraries that fight shadcn/ui

### 25.6 Agent Efficiency Rules

Each Cursor agent should:

- read MASTER_PRD.md first
- read only its owned AGENT_HANDOFF.md next
- modify only owned files
- implement smallest passing version first
- use fixture data before live services
- add tests with every implementation change
- update its AGENT_HANDOFF.md after meaningful changes
- avoid broad refactors outside its scope
- stop and record blocker if a contract is missing

Agents should not:

- invent new artifact shapes
- add undocumented fields
- change schemas without updating fixtures and types
- call paid APIs in tests
- replace working simple code with complex abstractions
- introduce a new framework to solve a small local problem

### 25.7 Efficient Prompting for Repo Development

The launch prompt to a repo-building agent should be short and command-like, then reference the PRD.

Recommended root prompt:

```
Build this repository according to MASTER_PRD.md. Start by creating the scaffold, schemas, fixture data, agent handoff files, and the minimal static frontend. Obey file ownership rules. Use fixture mode only. Do not call paid APIs. Do not invent undocumented interfaces. Stop after the first end-to-end fixture case renders and all tests pass.
```

Agent-specific prompts should point to one workstream only.

Bad prompt:

```
Build the whole biotech AI platform.
```

Good prompt:

```
You are the schema-agent. Implement the JSON schemas, Python types, TypeScript artifact types, fixture validation tests, and schemas/AGENT_HANDOFF.md according to MASTER_PRD.md. Do not modify connectors, pipeline, evals, or frontend components.
```

### 25.8 Cursor Launch Kit

The repo must include a launch kit that turns the PRD into executable multi-agent work.

Required launch kit files:

```
AGENT_ORCHESTRATION.md
LAUNCH_PROMPT.md
tasks/
  00_repo_scaffold.md
  01_schema_agent.md
  02_fixture_agent.md
  03_frontend_agent.md
  04_connector_agent.md
  05_pipeline_agent.md
  06_synthesis_agent.md
  07_evals_agent.md
  08_integration_agent.md
```

### 25.9 LAUNCH_PROMPT.md Contract

`LAUNCH_PROMPT.md` must contain:

- one master build prompt
- one fixture-only build prompt
- one live-integration build prompt
- one integration-agent prompt
- explicit instruction to obey MASTER_PRD.md
- explicit instruction to avoid paid API calls unless live mode is requested

Minimum master prompt:

```
You are building the Translational Diligence Workbench. Read MASTER_PRD.md completely. Implement the repo in the required build order. First create the scaffold, schemas, fixture data, static frontend, pipeline stubs, eval stubs, and integration tests. Use fixture mode only. Do not call paid APIs. Do not add features outside the PRD. Every module must include an AGENT_HANDOFF.md. Stop when the STING/PDAC fixture case renders in the frontend and the documented test commands pass.
```

### 25.10 Task File Contract

Each file in `tasks/` must include:

- agent name
- objective
- files allowed to modify
- files forbidden to modify
- input contracts consumed
- output contracts produced
- implementation steps
- tests to run
- acceptance criteria
- handoff notes required

Example task file header:

```markdown
# 01 Schema Agent

Agent: schema-agent
Objective: Implement canonical artifact schemas and shared types.
May modify:
- schemas/**
- pipeline/types.py
- web/types/artifacts.ts
- tests/schemas/**
Must not modify:
- connectors/**
- pipeline/run_workflow.py
- web/components/**
```

### 25.11 Token and Context Efficiency

Agents should avoid loading the entire repository context when unnecessary.

Context loading order:

1. MASTER_PRD.md
2. relevant task file
3. relevant AGENT_HANDOFF.md
4. relevant schemas
5. local files owned by the agent

Agents should not load unrelated frontend files while implementing connectors, or connector files while implementing frontend components, unless debugging integration.

### 25.12 Definition of Efficient MVP Done

Efficient MVP is done when:

1. Clean clone installs successfully.
2. Fixture mode runs without API keys.
3. One full case renders end-to-end.
4. Four fixture case cards render.
5. All 12 artifacts exist for the primary fixture case.
6. Schema validation passes.
7. Eval stubs or deterministic evals run.
8. Frontend build succeeds.
9. README explains the single-command fixture demo.
10. Launch kit files exist and match PRD workstreams.

## 26. Version History

- v0.1: Initial canonical PRD draft.
- v0.2: Reframed as implementation contract for parallel Cursor-agent development.
- v0.3: Added file ownership rules, build DAG, provenance contract, frontend component APIs, prompt contracts, fixture strategy, CLI requirements, CI requirements, and repo foundation requirements.
- v0.4: Added formal parallel-agent convergence model, agent handoff files, contract-first development rules, integration gates, holistic assembly command chain, merge conflict policy, integration-agent role, and change tracking protocol.
- v0.5: Added formal interface contracts for case configs, connectors, source records, entity normalization, artifacts, evidence rows, LLM providers, prompts, evaluators, frontend data loading, MCP-style tools, and contract change process.
- v0.6: Added efficient development guidelines, MVP vertical slice rule, build order, anti-overbuilding rules, dependency budget, agent efficiency rules, repo-development prompt guidance, Cursor launch kit, launch prompt contract, task file contract, token/context efficiency rules, and efficient MVP definition.
- v0.6: Added efficient development guidelines, MVP vertical slice rule, build order, anti-overbuilding rules, dependency budget, agent efficiency rules, repo-development prompt guidance, Cursor launch kit, launch prompt contract, task file contract, token/context efficiency rules, and efficient MVP definition.
- v0.7: Deduplicated section 3A and erroneous section 26 duplicate; fixed broken export links.
