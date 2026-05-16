# Evals Agent Handoff

**Status:** pending

**Owner agent:** evals-agent

**Task file:** `tasks/07_evals_agent.md`

## Interfaces consumed

- Generated case artifacts (`literature_records.json`, `clinical_trials.json`, `diligence_report.json`, etc.)
- `schemas/eval_results.schema.json`

## Interfaces produced

- `eval_results.json` per case
- `evals/run_evals.py` CLI

## Commands to test

```bash
python -m evals.run_evals --case generated/cases/sting_pdac
python -m pytest tests/evals -q
```

## Assumptions

- Evals are deterministic; no OpenAI in eval path.

## Blockers

- Eval modules not implemented.
- Depends on pipeline producing valid artifacts.

## Downstream consumers

- frontend-agent (EvalPanel), integration-agent
