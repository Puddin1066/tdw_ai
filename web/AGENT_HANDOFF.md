# Frontend Agent Handoff (Workstream E)

## Status

Static-first Next.js 15 App Router app under `web/`. All case data loads from `web/public/data/cases/{caseId}/` at build time via `lib/loadCase.ts` (Node `fs`). No runtime API or LLM calls.

## Commands

```bash
cd web
npm install
node scripts/generate-stub-cases.mjs   # regenerate 4 demo case stubs
npm run dev                          # local preview
npm run build                        # static export to web/out/
```

## Routes

| Route | Purpose |
|-------|---------|
| `/` | Case library — 4 `CaseCard` components from case metadata |
| `/cases/[caseId]` | Dashboard with tabs: Overview, Evidence, Trials, Risks, Graph, Sources, Evals |

## Components (PRD §12)

| Component | File | Props |
|-----------|------|-------|
| `CaseCard` | `components/CaseCard.tsx` | `caseId`, `targetName`, `indicationName`, `maturityStage`, `confidenceScore`, `evidenceDensity`, `topRisk` |
| `ExecutiveSnapshot` | `components/ExecutiveSnapshot.tsx` | `report`, `riskMap`, `evalResults` |
| `EvidenceTable` | `components/EvidenceTable.tsx` | `evidenceRows` |
| `TrialsTable` | `components/TrialsTable.tsx` | `trials` |
| `RiskMap` | `components/RiskMap.tsx` | `riskMap` |
| `KnowledgeGraph` | `components/KnowledgeGraph.tsx` | `graph` |
| `SourceManifest` | `components/SourceManifest.tsx` | `manifest` |
| `EvalPanel` | `components/EvalPanel.tsx` | `evalResults` |
| `CaseDashboard` | `components/CaseDashboard.tsx` | client shell for tabs |

shadcn-style primitives: `components/ui/{button,card,tabs,badge}.tsx`

## Types

`types/artifacts.ts` — TypeScript contracts aligned with MASTER_PRD / guide_v07 (artifact envelopes, evidence rows, trials, report, risks, graph, manifest, evals).

## Data contract

Per case folder (`public/data/cases/{case_id}/`):

- `metadata.yaml` or `case_metadata.json` (required for routing)
- `diligence_report.json`, `evidence_table.json`, `clinical_trials.json` (expected)
- `risk_map.json`, `knowledge_graph.json`, `source_manifest.json`, `eval_results.json` (optional — empty states if missing)

JSON artifacts use the envelope shape: `{ artifact_type, case_id, schema_version, generated_at, provenance, data }`.

Stub generator: `scripts/generate-stub-cases.mjs` creates all four demo cases (`sting_pdac`, `parp_breast`, `tau_alzheimers`, `iaip_sepsis`).

## Integration notes for downstream agents

1. **Pipeline / fixture-agent**: Copy validated artifacts from `generated/cases/{id}/` into `web/public/data/cases/{id}/` after schema validation. Re-run `npm run build`.
2. **Schema-agent**: Update `web/types/artifacts.ts` when JSON schemas change; keep field names in sync with `schemas/*.schema.json`.
3. **Static export**: `next.config.ts` sets `output: "export"`. Dynamic routes use `generateStaticParams()` from `listCaseIds()`.

## Out of scope (do not add in frontend)

- Runtime chat UI
- Live PubMed / ClinicalTrials / OpenTargets API calls
- Auth, databases, background jobs

## Known limitations

- Knowledge graph uses a simple grid layout in React Flow (no force-directed physics).
- Risk map chart is severity/likelihood bars, not a heatmap matrix.
- Stub NCT/PMID IDs are placeholders for build verification only.
