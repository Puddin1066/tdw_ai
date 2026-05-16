# 09 Synthesis Agent (Phase 2)

**Agent:** synthesis-agent

**Objective:** Implement `pipeline/llm_provider.py`, `skills/translational_diligence/`, wire `generate_*` in live mode, and `tests/synthesis/`.

## May modify

- `pipeline/llm_provider.py`
- `pipeline/synthesis_runner.py`
- `pipeline/generate_*.py`
- `skills/translational_diligence/**`
- `tests/fixtures/synthesis/**`
- `tests/synthesis/**`
- `skills/AGENT_HANDOFF.md`

## Must not modify

- `schemas/*.schema.json` (without schema-agent)
- `web/components/**`

## Verify

```bash
pytest tests/synthesis -q
python -m pipeline.run_workflow --config configs/cases/sting_pdac.yaml --mode live
```

## Acceptance

- MockProvider serves CI without API keys
- Live mode synthesis does not copy from `tests/fixtures/cases/`
- Outputs validate against JSON schemas
