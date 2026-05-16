# 01 Schema Agent

**Agent:** schema-agent

**Objective:** Implement canonical artifact JSON schemas and matching Python (Pydantic) and TypeScript types so all workstreams share one contract.

## May modify

- `schemas/**`
- `pipeline/types.py`
- `web/types/artifacts.ts`
- `tests/schemas/**`

## Must not modify

- `connectors/**`
- `pipeline/run_workflow.py` (orchestration logic)
- `web/components/**`
- `web/app/**`
- `skills/**`
- `evals/**`
- `tests/fixtures/cases/**` (fixture data — coordinate with fixture-agent)

## Input contracts consumed

- PRD §8 Case Packet Contract (12 required artifacts)
- PRD §24.1 Contract Categories
- PRD §24.5–24.8 Source, Entity, Artifact, Evidence contracts
- Existing `configs/cases/*.yaml` for `case_id` examples

## Output contracts produced

- `schemas/case_metadata.schema.json`
- `schemas/source_manifest.schema.json`
- `schemas/normalized_entities.schema.json`
- `schemas/literature_records.schema.json`
- `schemas/clinical_trials.schema.json`
- `schemas/target_biology.schema.json`
- `schemas/evidence_table.schema.json`
- `schemas/diligence_report.schema.json`
- `schemas/risk_map.schema.json`
- `schemas/knowledge_graph.schema.json`
- `schemas/eval_results.schema.json`
- `pipeline/types.py` — Pydantic models mirroring schemas
- `web/types/artifacts.ts` — TypeScript types mirroring schemas

## Implementation steps

1. Enumerate all 12 artifact filenames and required fields from PRD §8.
2. Author JSON Schema files with `$schema`, stable `$id`, and explicit required fields.
3. Implement Pydantic v2 models with `model_config` for JSON round-trip.
4. Generate or hand-write TypeScript types consistent with schemas.
5. Add `tests/schemas/test_artifact_schemas.py` validating golden minimal instances.
6. Update `schemas/AGENT_HANDOFF.md` with schema version and consumer list.

## Tests to run

```bash
python -m pytest tests/schemas -q
# Optional: jsonschema CLI validation against fixture samples once fixture-agent lands
```

## Acceptance criteria

- [ ] All 12 schema files exist under `schemas/`
- [ ] Python types serialize/deserialize each artifact shape
- [ ] TypeScript types match JSON schemas (no undocumented fields)
- [ ] Minimal valid instances pass `jsonschema` validation in tests
- [ ] `schemas/AGENT_HANDOFF.md` documents interfaces and test commands
- [ ] Fixture data from fixture-agent passes validation when integrated

## Handoff notes required

- Schema `$id` URLs and versioning strategy
- Any `experimental` extension points permitted
- List of fields downstream agents must not rename
- Blockers for fixture-agent or pipeline-agent
