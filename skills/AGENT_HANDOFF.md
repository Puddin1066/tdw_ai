# Synthesis Agent Handoff

**Status:** pending

**Owner agent:** synthesis-agent

**Task file:** `tasks/06_synthesis_agent.md`

## Files modified

_None yet — scaffold placeholder._

## Interfaces consumed

- Normalized artifacts from pipeline
- PRD §13–14 AI and prompt contracts
- `schemas/diligence_report.schema.json` and related schemas

## Interfaces produced

- `skills/translational_diligence/**`
- `pipeline/generate_*.py` synthesis steps
- Report, evidence table, risk map, claims JSON

## Commands to test

```bash
python -m pytest tests/synthesis -q
```

## Assumptions

- Build-time OpenAI only in live mode for MVP.
- Fixture mode uses mock LLM provider.

## Blockers

- Skill and pipeline generation modules not implemented.
- Depends on schema-agent and normalized fixture artifacts.

## Downstream consumers

- evals-agent, integration-agent
