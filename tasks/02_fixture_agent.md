# 02 Fixture Agent

**Agent:** fixture-agent

**Objective:** Create offline fixture case packets for all four MVP cases so frontend, pipeline, evals, and synthesis agents can develop without live APIs.

## May modify

- `tests/fixtures/cases/**`
- `tests/fixtures/connectors/**` (raw connector samples if needed)
- `tests/fixtures/README.md` (optional)

## Must not modify

- `schemas/*.schema.json` (request schema-agent for shape changes)
- `web/components/**`
- `connectors/*.py` (implementations)
- `pipeline/*.py`
- `generated/**` (runtime output, not source fixtures)

## Input contracts consumed

- PRD §16 Fixture Strategy
- PRD §24.2 Case configs in `configs/cases/`
- JSON schemas from schema-agent (`schemas/*.schema.json`)
- PRD §8 — 12 artifacts per case folder

## Output contracts produced

Per case (`sting_pdac`, `parp_breast`, `tau_alzheimers`, `iaip_sepsis`):

- `tests/fixtures/cases/{case_id}/` containing:
  - Raw connector samples (per enabled source)
  - Normalized connector output
  - All 12 final artifacts
  - Expected `eval_results.json`

## Implementation steps

1. Wait for schema-agent to publish schemas (or use draft schemas from PRD).
2. Build `sting_pdac` fixture first (primary vertical slice).
3. Include realistic PMIDs, NCT IDs, and evidence IDs consistent across artifacts.
4. Replicate pattern for `parp_breast`, `tau_alzheimers`, `iaip_sepsis`.
5. Add `tests/schemas/` or `tests/fixtures/` test that all fixtures validate against schemas.
6. Document fixture layout in handoff notes for pipeline copy-to-web flow.

## Tests to run

```bash
python -m pytest tests/schemas -q -k fixture
python -m pytest tests/fixtures -q  # if dedicated tests added
```

## Acceptance criteria

- [ ] Four fixture directories exist under `tests/fixtures/cases/`
- [ ] Each fixture case includes all 12 required artifacts
- [ ] Each fixture validates against canonical JSON schemas
- [ ] PMIDs in report exist in `literature_records.json`; NCT IDs in report exist in `clinical_trials.json`
- [ ] Fixtures loadable with no API keys
- [ ] Handoff notes describe how pipeline should copy fixtures to `generated/cases/` in fixture mode

## Handoff notes required

- Fixture file manifest per case
- Known synthetic IDs vs real public IDs used
- Commands to validate fixtures
- Blockers if schemas are incomplete
