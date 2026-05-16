# 06 Synthesis Agent

**Agent:** synthesis-agent

**Objective:** Define translational diligence skill and generate structured report, evidence table, risk map, claims, and diligence questions with full provenance.

## May modify

- `skills/**`
- `pipeline/generate_report.py`
- `pipeline/generate_claims.py`
- `pipeline/generate_risk_map.py`
- `pipeline/generate_questions.py`
- `tests/synthesis/**`

## Must not modify

- `connectors/**`
- `web/**`
- `schemas/**` except via schema-agent approval
- `evals/**`

## Input contracts consumed

- PRD §13 AI Usage Contract
- PRD §14 Prompt Contract Requirements
- PRD §24.9 LLM Provider Contract
- PRD §24.10 Prompt Contract
- Normalized fixture artifacts from pipeline/fixture-agent
- `skills/translational_diligence/output_schema.json` aligned with schemas

## Output contracts produced

- `skills/translational_diligence/SKILL.md`
- `skills/translational_diligence/output_schema.json`
- `skills/translational_diligence/prompts/*.md`
- `skills/translational_diligence/templates/*.md`
- Pipeline modules: `generate_report.py`, `generate_claims.py`, `generate_risk_map.py`, `generate_questions.py`
- Mock LLM provider for fixture mode; OpenAI for live build-time synthesis

## Implementation steps

1. Author skill definition and prompt templates per PRD §14.
2. Implement mock provider returning deterministic JSON from fixtures.
3. Wire synthesis steps into pipeline after normalization.
4. Ensure every claim has ≥1 evidence reference or `unsupported` flag.
5. Validate outputs against JSON schemas.
6. Update `skills/AGENT_HANDOFF.md`.

## Tests to run

```bash
python -m pytest tests/synthesis -q
python -m pipeline.run_workflow --config configs/cases/sting_pdac.yaml --mode fixture
# Verify diligence_report.json, evidence_table.json, risk_map.json validate
```

## Acceptance criteria

- [ ] Synthesis runs against static fixture artifacts without OpenAI in fixture mode
- [ ] Output validates against JSON schemas
- [ ] Each generated claim includes ≥1 evidence reference or is marked `unsupported`
- [ ] Unsupported claims detectable by eval layer
- [ ] Live mode uses OpenAI only when explicitly requested with `.env`
- [ ] `skills/AGENT_HANDOFF.md` complete

## Handoff notes required

- Mock vs live provider switch mechanism
- Prompt versioning and output schema paths
- Provenance fields written per claim
- Blockers for eval-agent unsupported-claim tests
