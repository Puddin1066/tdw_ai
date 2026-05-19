# Live Case Review — STING / PDAC (`sting_pdac`)

**Status:** Complete — portfolio MVP sign-off (engineering / demo plausibility; not clinical or investment advice).

## Run metadata

| Field | Value |
|-------|--------|
| Case ID | `sting_pdac` |
| Mode | `live` |
| Synthesis provider | `mock` (`mock-synthesis-v1`) — `tests/fixtures/synthesis/sting_pdac/` payloads, not copied from `tests/fixtures/cases/` |
| Packet generated | `2026-05-16T13:46:04Z` |
| Review date | 2026-05-16 |
| Reviewer | Engineering (portfolio demo) |

## Data sources

- [x] **PubMed live fetch** — 50 records; query: `(STING OR TMEM173 OR Stimulator of Interferon Genes) AND (pancreatic cancer OR pancreatic ductal adenocarcinoma OR PDAC)`
- [x] **ClinicalTrials.gov** — live attempted; `NotImplementedError`; **3 trials** from fixture fallback in `clinical_trials.json`
- [x] **Open Targets, ChEMBL, BioThings** — live attempted; not implemented; fixture/zero records documented in `source_manifest.json`

Synthesis inputs (`literature_records`, `clinical_trials`, entities) built via `pipeline/build_sources.py` from connector results plus documented fallbacks.

## Scientific plausibility

| Area | Plausible? | Notes |
|------|------------|-------|
| Mechanism claims | Yes (directional) | STING innate immune signaling in PDAC is consistent with published preclinical literature; mock synthesis uses aligned PMID `42102812` from live PubMed set. |
| Trial references | Yes (with caveat) | `NCT05234567` present in fixture trial set; report cites trial consistent with packet. CT.gov not live-fetched — trial landscape is partially synthetic. |
| Risk framing | Yes | High-severity clinical/translational risks (limited single-agent efficacy, immunosuppressive TME) match known PDAC/STING narrative. |
| Confidence scores | Acceptable for demo | Report `0.65`, evidence rows `0.82`/`0.9` — reasonable spread; not calibrated to real-world evidence strength. |

**Caveats:** Narrative depth is intentionally thin (2 evidence rows, mock LLM). Top PubMed hits were not manually curated. Portfolio purpose is workflow credibility (provenance, citations, eval gates), not therapeutic due diligence.

## Eval gates

- [x] `python -m evals.run_evals --case generated/cases/sting_pdac` — **overall_passed: true**, aggregate_score: 1.0
- Gates: citation_fidelity, unsupported_claims, trial_hallucination, evidence_coverage — all passed
- Warning (acceptable): evidence_coverage notes no structured claims in report JSON (sections-only model)

## Artifact checklist (12 files)

All present under `generated/cases/sting_pdac/` after `run_workflow --mode live`: metadata, source_manifest, normalized_entities, literature_records, clinical_trials, target_biology, evidence_table, diligence_report (.json + .md), risk_map, knowledge_graph, eval_results (after eval step).

## Known limitations

- **MockProvider** when `OPENAI_API_KEY` unset; synthesis labeled MOCK/SYNTHETIC in evidence limitations.
- **One live connector** (PubMed) per §24.4A; other sources fixture fallback.
- **Strict JSON Schema** on full packet: optional `--validate-schemas` may fail on legacy shapes (`target_biology`, `clinical_trials` field names).
- **Not for clinical decision-making** or investment decisions.

## Sign-off

Portfolio MVP (Tier B) engineering sign-off: **approved** for static demo and job-portfolio narrative, subject to caveats above.

Reviewer: Jay Round (engineering) — 2026-05-16
