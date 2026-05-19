# Synthesis Agent Handoff

**Status:** Tier B complete (v0.8.3)

**Owner agent:** synthesis-agent

**Task file:** `tasks/09_synthesis_agent.md`

## Implemented

- `pipeline/llm_provider.py` — `MockProvider`, `OpenAIProvider`, `get_provider()`
- `pipeline/synthesis_runner.py` — prompt load, envelope write, schema validation
- `skills/translational_diligence/SKILL.md` and `prompts/*.md`
- `tests/fixtures/synthesis/sting_pdac_*_data.json` — mock live synthesis payloads
- `tests/synthesis/test_mock_provider.py`
- Live mode wired in `pipeline/_artifacts.py` → `run_synthesis_json_step`

## Remaining (optional)

- OpenAI live synthesis run with `OPENAI_API_KEY` (not required for Tier B)
- Strict JSON Schema on all 12 artifacts (`artifact_writer --validate-schemas`)
- Golden refresh when schemas tighten fixture case packets

## Commands

```bash
pytest tests/synthesis -q
python -m pipeline.run_workflow --config configs/cases/sting_pdac.yaml --mode live
```

## Consumers

- pipeline-agent, evals-agent, integration-agent
