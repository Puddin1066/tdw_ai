# 07 Evals Agent

**Agent:** evals-agent

**Objective:** Implement deterministic evaluation suite producing `eval_results.json` — citation fidelity, unsupported claims, trial hallucination, evidence coverage — without OpenAI calls.

## May modify

- `evals/**`
- `tests/evals/**`

## Must not modify

- `connectors/**`
- `web/**`
- `skills/**` except by documented request
- `pipeline/**` except consuming artifact paths

## Input contracts consumed

- PRD §15 Evaluation Gates
- PRD §24.11 Evaluation Contract
- Generated or fixture artifacts: `literature_records.json`, `clinical_trials.json`, `diligence_report.json`, `evidence_table.json`
- `schemas/eval_results.schema.json` from schema-agent

## Output contracts produced

- `evals/run_evals.py` — CLI entrypoint
- `evals/citation_fidelity.py`
- `evals/unsupported_claims.py`
- `evals/trial_hallucination.py`
- `evals/evidence_coverage.py`
- `eval_results.json` per case under case folder

## Implementation steps

1. Implement CLI: `python -m evals.run_evals --case generated/cases/sting_pdac`.
2. Verify cited PMIDs exist in `literature_records.json`.
3. Verify cited NCT IDs exist in `clinical_trials.json`.
4. Flag claims marked `supported` without source records.
5. Score evidence coverage; aggregate into `eval_results.json`.
6. Add fixture tests with intentional bad citations for regression.
7. Update `evals/AGENT_HANDOFF.md`.

## Tests to run

```bash
python -m evals.run_evals --case generated/cases/sting_pdac
python -m pytest tests/evals -q
```

## Acceptance criteria

- [ ] Every case produces `eval_results.json`
- [ ] NCT IDs in report must exist in `clinical_trials.json`
- [ ] PMIDs in report must exist in `literature_records.json`
- [ ] Claims marked `supported` must cite ≥1 source record or snippet
- [ ] Eval tests run without OpenAI calls
- [ ] Invalid claims and hallucinated trial IDs detected in test fixtures
- [ ] `evals/AGENT_HANDOFF.md` complete

## Handoff notes required

- Eval score definitions and thresholds
- CLI usage and output path
- Test fixtures with known failures
- Blockers if report schema lacks required provenance fields
