# Target–Indication Benchmark Implementation Spec

## Purpose

This document specifies how TDW_AI should implement a benchmark layer for target–indication diligence.

The benchmark layer is not a keyword search feature and not a chatbot layer. It is an evidence-to-comparison system that converts the existing TDW_AI case workflow into structured, auditable benchmark records.

The benchmark answers:

> Does this target–indication pair resemble historical programs that translated efficiently into approval, financing, partnership, or commercial value — or does it resemble slow, expensive, or failure-prone development paths?

## Core concept

A benchmark is a structured reference set of historical target–indication programs with known outcomes.

TDW_AI should use the benchmark as a yardstick for new or emerging opportunities.

The canonical unit of analysis is:

```text
target + indication + development context
```

Examples:

| Target | Indication | Outcome archetype |
|---|---|---|
| SMN2 | Spinal muscular atrophy | Efficient rare-disease approval |
| TTR | ATTR amyloidosis | Efficient causal protein suppression |
| BCR-ABL | Chronic myeloid leukemia | Genetically defined oncology success |
| RPE65 | Inherited retinal dystrophy | Monogenic local-delivery success |
| Tau | Alzheimer’s disease | Slow/noisy translational path |
| BACE | Alzheimer’s disease | High-plausibility clinical failure |
| CETP | Cardiovascular disease | Biomarker-improving failure pattern |

The benchmark must include both successes and failures. If it only includes successful cases, TDW_AI will over-score plausible but risky biology.

## Strategic role in TDW_AI

Current TDW_AI workflow:

```text
target–indication pair → evidence artifacts
```

Benchmark-extended workflow:

```text
target–indication pair → evidence artifacts → benchmark features → TEI score → venture score → archetype match
```

The benchmark layer should sit after the existing evidence-generation workflow and before final artifact writing/evaluation.

## Required outputs

For each generated case, TDW_AI should add a benchmark folder:

```text
generated/cases/{case_id}/benchmark/
  benchmark_result.json
  benchmark_summary.md
  feature_trace.json
  archetype_matches.json
```

### `benchmark_result.json`

Canonical machine-readable benchmark output.

Example:

```json
{
  "case_id": "ttr_attr",
  "target": "TTR",
  "indication": "ATTR amyloidosis",
  "features": {
    "human_genetic_causality": 0.95,
    "biomarker_clarity": 0.90,
    "endpoint_compressibility": 0.82,
    "trial_feasibility": 0.80,
    "regulatory_precedent": 0.88,
    "modality_tractability": 0.90,
    "clinical_precedent": 0.88,
    "commercial_validation": 0.85,
    "partnerability": 0.80,
    "competitive_crowding": 0.62,
    "kol_network_strength": 0.78
  },
  "tei_score": 89,
  "venture_score": 84,
  "nearest_archetypes": [
    "orphan_causal_protein_suppression",
    "rna_therapeutic_validation",
    "biomarker_readable_systemic_disease"
  ],
  "interpretation": "High-confidence translational efficiency archetype with strong commercial validation and moderate crowding risk."
}
```

### `benchmark_summary.md`

Human-readable diligence summary.

It should explain:

1. Why the target–indication pair scored well or poorly.
2. Which evidence supports each major feature.
3. Which historical archetypes are most similar.
4. Which negative archetypes or failure modes are partially matched.
5. What should be manually reviewed before relying on the score.

### `feature_trace.json`

Auditable source-to-feature trace.

Each feature must include:

- feature name
- score
- confidence
- evidence snippets or artifact pointers
- source category
- extraction method
- warnings

Example:

```json
{
  "feature": "human_genetic_causality",
  "score": 0.95,
  "confidence": "high",
  "source_category": "biomedical",
  "evidence_artifacts": [
    "generated/cases/ttr_attr/evidence_tables/genetics.json"
  ],
  "rationale": "Multiple human genetic links support causal disease biology.",
  "warnings": []
}
```

### `archetype_matches.json`

Structured similarity output against historical benchmark archetypes.

Example:

```json
[
  {
    "archetype_id": "orphan_causal_protein_suppression",
    "similarity": 0.94,
    "positive_matches": [
      "human genetic causality",
      "biomarker-readable disease",
      "small definable population",
      "validated RNA modality precedent"
    ],
    "negative_matches": [
      "increasing competitive crowding"
    ]
  }
]
```

## Recommended module structure

Add the following modules:

```text
pipeline/
  benchmark/
    __init__.py
    run_benchmark.py
    feature_extractor.py
    tei_scorer.py
    venture_scorer.py
    archetype_matcher.py
    benchmark_writer.py

connectors/
  commercial/
    __init__.py
    fixture_commercial.py
    octagon_client.py
    schemas.py

data/
  benchmark_archetypes/
    efficient_approval_archetypes.json
    failure_archetypes.json

schemas/
  benchmark_feature.schema.json
  benchmark_result.schema.json
  archetype.schema.json
```

This should extend the existing contract-first architecture rather than replace it.

## CLI design

Add a benchmark runner:

```bash
python -m pipeline.benchmark.run_benchmark \
  --case generated/cases/sting_pdac \
  --commercial-backend fixture
```

Optional live commercial mode:

```bash
python -m pipeline.benchmark.run_benchmark \
  --case generated/cases/sting_pdac \
  --commercial-backend octagon
```

Full workflow:

```bash
python -m pipeline.run_workflow --config configs/cases/sting_pdac.yaml --mode live
python -m pipeline.benchmark.run_benchmark --case generated/cases/sting_pdac --commercial-backend fixture
python -m evals.run_evals --case generated/cases/sting_pdac
python -m pipeline.artifact_writer generated/cases/sting_pdac --copy-to-web
```

## Environment variables

Add to `.env.example`:

```bash
# Biomedical backend already supported in repo
CONNECTOR_BACKEND=biomcp
OPENTARGETS_BACKEND=biomcp
CHEMBL_BACKEND=biomcp
BIOTHINGS_BACKEND=biomcp

# Commercial benchmark backend
COMMERCIAL_BACKEND=fixture
# Options: fixture, octagon
OCTAGON_API_KEY=
```

Fixture mode must remain the default for deterministic testing.

## Feature model

### Translational Efficiency Index features

| Feature | Weight | Description |
|---|---:|---|
| Human genetic causality | 0.20 | Strength of human causal evidence linking target to indication |
| Biomarker clarity | 0.15 | Existence of measurable biomarkers or objective disease markers |
| Endpoint compressibility | 0.15 | Likelihood that clinical effect can be measured quickly and objectively |
| Trial feasibility | 0.15 | Enrollment practicality, trial size, duration, and design tractability |
| Regulatory precedent | 0.10 | Similar accepted endpoints, orphan/accelerated pathways, prior approvals |
| Modality tractability | 0.10 | Fit between target biology and feasible therapeutic modalities |
| Clinical precedent | 0.10 | Evidence from prior human trials or analogous programs |
| KOL network strength | 0.05 | Concentration and quality of translational investigators/institutions |

Formula:

```text
TEI =
0.20 * human_genetic_causality
+ 0.15 * biomarker_clarity
+ 0.15 * endpoint_compressibility
+ 0.15 * trial_feasibility
+ 0.10 * regulatory_precedent
+ 0.10 * modality_tractability
+ 0.10 * clinical_precedent
+ 0.05 * kol_network_strength
```

### Venture Score features

| Feature | Weight | Description |
|---|---:|---|
| TEI | 0.30 | Translational efficiency score |
| Capital efficiency proxy | 0.20 | Historical cost/time profile of similar programs |
| Partnerability | 0.15 | Evidence of pharma licensing, M&A, strategic partnerships |
| Market validation | 0.15 | Revenue, pricing, commercial adoption, strategic market interest |
| Competitive/IP whitespace | 0.10 | Differentiation versus crowded or patent-dense spaces |
| Operator/company signal | 0.10 | Quality of companies, sponsors, management, investors, or execution track record |

Formula:

```text
Venture Score =
0.30 * TEI
+ 0.20 * capital_efficiency_proxy
+ 0.15 * partnerability
+ 0.15 * market_validation
+ 0.10 * competitive_ip_whitespace
+ 0.10 * operator_company_signal
```

Keep TEI and Venture Score separate. Biological attractiveness and venture attractiveness are not the same thing.

## Data-source roles

### BioMCP role

BioMCP is the preferred biomedical retrieval layer.

It should support features such as:

| Feature | BioMCP-derived evidence |
|---|---|
| Human genetic causality | gene–disease evidence, variants, OpenTargets-like evidence, literature |
| Biomarker clarity | publications, trial endpoints, disease markers |
| Endpoint compressibility | ClinicalTrials.gov endpoints and trial designs |
| Trial feasibility | enrollment, phase, duration, trial count, sponsor count |
| Clinical precedent | prior trials, drugs, indications, labels where available |
| KOL network strength | publication authors, trial investigators, institutions |

### Octagon MCP role

Octagon MCP is an optional commercial/company intelligence backend.

It should support features such as:

| Feature | Octagon-derived evidence |
|---|---|
| Capital efficiency proxy | financing rounds, public filings, R&D spend proxies |
| Partnerability | licensing, partnership, M&A, strategic deal signals |
| Market validation | revenue, market cap, stock reaction, product/company performance |
| Competitive/IP whitespace | company density, funding density, investor/deal crowding |
| Operator/company signal | management, investors, company trajectory, financing quality |

Octagon must be optional. If unavailable, TDW_AI should use fixture commercial evidence and emit warnings.

## Benchmark archetypes

Create positive and negative archetypes.

### Positive archetypes

Examples:

```json
[
  {
    "id": "orphan_causal_protein_suppression",
    "label": "Orphan causal protein suppression",
    "examples": ["TTR / ATTR", "C5 / PNH"],
    "feature_profile": {
      "human_genetic_causality": 0.90,
      "biomarker_clarity": 0.85,
      "trial_feasibility": 0.80,
      "regulatory_precedent": 0.80,
      "commercial_validation": 0.80
    }
  },
  {
    "id": "mutation_defined_oncology",
    "label": "Mutation-defined oncology",
    "examples": ["BCR-ABL / CML", "ALK / NSCLC", "KRAS G12C / NSCLC"],
    "feature_profile": {
      "patient_stratifiability": 0.95,
      "endpoint_compressibility": 0.80,
      "clinical_precedent": 0.85,
      "partnerability": 0.85
    }
  }
]
```

### Negative archetypes

Examples:

```json
[
  {
    "id": "biomarker_rich_clinically_weak",
    "label": "Biomarker-rich but clinically weak",
    "examples": ["CETP / cardiovascular disease"],
    "risk_profile": {
      "biomarker_clarity": 0.85,
      "clinical_precedent": 0.30,
      "endpoint_compressibility": 0.40
    }
  },
  {
    "id": "broad_inflammatory_noisy_population",
    "label": "Broad inflammatory target with noisy population",
    "examples": ["anti-inflammatory sepsis programs"],
    "risk_profile": {
      "patient_stratifiability": 0.25,
      "trial_feasibility": 0.35,
      "endpoint_compressibility": 0.30
    }
  }
]
```

## Scoring requirements

All scores must be:

- normalized between 0 and 1 at feature level
- converted to 0–100 for summary reporting
- paired with confidence values
- linked to source artifacts through `feature_trace.json`
- deterministic in fixture mode

No benchmark score should be presented as a truth claim. It is a structured diligence aid.

## Query architecture requirement

TDW_AI must not be implemented as keyword search alone.

Required progression:

```text
keyword/entity retrieval → evidence graph → feature extraction → benchmark comparison → synthesis
```

Supported query types:

| Query type | Purpose |
|---|---|
| Keyword query | retrieve raw biomedical/commercial documents |
| Entity query | resolve target, disease, drug, company, KOL, sponsor |
| Graph query | connect target, indication, trials, papers, sponsors, investigators, drugs |
| Feature query | calculate benchmark variables |
| Archetype query | compare against historical success/failure patterns |
| Venture query | overlay company, financing, market, and partnership context |
| Opportunity query | rank target–indication pairs by benchmark similarity |

## Evaluation requirements

Add deterministic tests for:

1. Schema validation of benchmark output.
2. TEI score calculation.
3. Venture Score calculation.
4. Archetype matching.
5. Fixture commercial fallback.
6. Warning emission when Octagon is unavailable.
7. Artifact writer compatibility.

Suggested test files:

```text
tests/benchmark/test_tei_scorer.py
tests/benchmark/test_venture_scorer.py
tests/benchmark/test_archetype_matcher.py
tests/benchmark/test_benchmark_writer.py
tests/connectors/test_commercial_fixture.py
```

## Frontend display

Add benchmark display cards to the static frontend case page:

- TEI score
- Venture Score
- top positive archetype matches
- top negative/failure-mode matches
- feature heatmap/table
- evidence trace links
- warning banner for fixture or incomplete commercial data

The UI must make clear when commercial evidence is fixture-derived versus live Octagon-derived.

## Implementation phases

### Phase 1 — fixture benchmark MVP

- Add benchmark schemas.
- Add scoring modules.
- Add fixture archetypes.
- Add fixture commercial connector.
- Generate benchmark outputs for existing four demo cases.
- Add deterministic tests.

### Phase 2 — BioMCP-enriched feature extraction

- Use existing BioMCP backend flags.
- Map BioMCP outputs to benchmark features.
- Add feature traces with artifact references.
- Keep fixture fallback.

### Phase 3 — Octagon commercial overlay

- Add optional Octagon client.
- Extract commercial signals.
- Generate commercial feature traces.
- Add warnings and confidence levels.

### Phase 4 — benchmark portfolio view

- Rank all generated cases by TEI and Venture Score.
- Add comparison table across cases.
- Add archetype similarity clustering.

## Acceptance criteria

A successful implementation must allow:

```bash
python -m pipeline.run_workflow --config configs/cases/sting_pdac.yaml --mode fixture
python -m pipeline.benchmark.run_benchmark --case generated/cases/sting_pdac --commercial-backend fixture
pytest tests/ -q
npm run build --prefix web
```

Expected generated files:

```text
generated/cases/sting_pdac/benchmark/benchmark_result.json
generated/cases/sting_pdac/benchmark/benchmark_summary.md
generated/cases/sting_pdac/benchmark/feature_trace.json
generated/cases/sting_pdac/benchmark/archetype_matches.json
```

## Product interpretation

This benchmark layer turns TDW_AI from a report generator into a comparative diligence platform.

The core value proposition becomes:

> TDW_AI ranks target–indication opportunities by translational efficiency, historical archetype similarity, and venture attractiveness using auditable biomedical and commercial evidence.

That is the thing worth building.