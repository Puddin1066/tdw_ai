# Pipeline Agent Handoff

## Owner

`backend-pipeline-agent` (Workstream A)

## Implemented modules

| Module | Purpose |
|--------|---------|
| `config_loader.py` | Load and validate `configs/cases/{case_id}.yaml` |
| `run_workflow.py` | CLI orchestration (`fixture` and `live` modes) |
| `normalize_entities.py` | Fixture copy or light normalization stub |
| `build_graph.py` | Build `knowledge_graph.json` from `normalized_entities.json` |
| `artifact_writer.py` | Validate 12 required artifacts; copy to `web/public/data/cases/` |
| `provenance.py` | Provenance metadata helpers |
| `run_registry.py` | Append-only JSONL run log under `generated/.runs/` |
| `generate_claims.py` | Writes `evidence_table.json` |
| `generate_report.py` | Writes `diligence_report.md` + `.json` |
| `generate_risk_map.py` | Writes `risk_map.json` |
| `generate_questions.py` | Optional `diligence_questions.json` (not in required 12) |
| `types.py` | `CaseConfig`, artifact contracts, paths |

## CLI

```bash
python -m pipeline.run_workflow --config configs/cases/sting_pdac.yaml --mode fixture
python -m pipeline.run_workflow --config configs/cases/sting_pdac.yaml --mode live
python -m pipeline.artifact_writer --copy-to-web generated/cases/sting_pdac
```

## Fixture mode behavior

1. Seeds `generated/cases/{case_id}/` from `tests/fixtures/cases/{case_id}/` when present.
2. Writes `metadata.yaml` from config.
3. Runs connectors **only if** `connectors.*` modules are importable (does not modify connector internals).
4. Normalizes entities (fixture copy preferred).
5. Runs synthesis steps (fixture copy preferred).
6. Always rebuilds `knowledge_graph.json` via `build_graph.py`.
7. Validates all 12 required artifacts; exits nonzero on failure.

## Live mode behavior

Same orchestration; synthesis modules emit stubs when fixtures are absent. OpenAI integration is deferred to the synthesis-agent via `LLMProvider`.

## Required artifacts (12)

Listed in `pipeline/types.py` as `REQUIRED_ARTIFACTS`.

## Dependencies

- **Consumes:** `configs/cases/*.yaml`, `tests/fixtures/cases/{case_id}/`, optional `connectors/*`
- **Produces:** `generated/cases/{case_id}/*`, optional `web/public/data/cases/{case_id}/*`
- **Does not modify:** `connectors/` internals, `web/components/`, `evals/`

## Tests

```bash
pip install -e ".[dev]"
pytest tests/pipeline/test_run_workflow_fixture.py -v
```

## Integration notes for other agents

- **schema-agent:** JSON Schema validation can be wired into `artifact_writer.validate_case_dir` without changing orchestration order.
- **connectors-agent:** Implement `fetch(config, mode)` on connector classes; pipeline discovers them by module name.
- **synthesis-agent:** Replace stub branches in `generate_*.py` with `LLMProvider` calls; keep fixture copy path for CI.
- **frontend-agent:** Run `artifact_writer --copy-to-web` after generation to populate `web/public/data/cases/`.

## Known gaps

- Live OpenAI synthesis not implemented (stubs only).
- JSON Schema validation not yet enforced (existence + JSON parse only).
- Only `sting_pdac` fixture case is populated in this handoff.
