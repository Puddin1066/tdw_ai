# 05 Pipeline Agent

**Agent:** backend-pipeline-agent

**Objective:** Orchestrate case workflow — load config, run connectors, normalize entities, write artifacts, copy to web public dir — with fixture and live modes.

## May modify

- `pipeline/**`
- `generated/**` (runtime output; gitignored)
- `tests/pipeline/**`

## Must not modify

- `web/app/**`, `web/components/**`
- `connectors/**` except via documented `ConnectorResult` interface
- `schemas/**` except via schema-agent approval
- `skills/**` (synthesis-agent owns generation modules)

## Input contracts consumed

- PRD §8 Case Packet Contract
- PRD §24.2 Case Config Contract
- `configs/cases/*.yaml`
- `connectors/*` — `fetch()` interface
- `pipeline/types.py` from schema-agent
- Fixture cases from fixture-agent (for fixture mode shortcut)

## Output contracts produced

- `pipeline/run_workflow.py` — CLI entrypoint
- `pipeline/config_loader.py`
- `pipeline/normalize_entities.py`
- `pipeline/build_graph.py`
- `pipeline/artifact_writer.py`
- `pipeline/run_registry.py`
- `pipeline/provenance.py`
- Complete `generated/cases/{case_id}/` with 12 artifacts

## Implementation steps

1. Implement YAML config loader with validation against §24.2.
2. Wire connector dispatch from case `sources` flags.
3. Save raw connector outputs; normalize to artifact shapes.
4. Implement `--mode fixture` using `tests/fixtures/cases/` or connector fixtures.
5. Implement `--mode live` delegating to connector live paths.
6. Write all 12 artifacts; exit nonzero if any required artifact missing.
7. Implement `artifact_writer --copy-to-web` to `web/public/data/cases/`.
8. Update `pipeline/AGENT_HANDOFF.md`.

## Tests to run

```bash
python -m pipeline.run_workflow --config configs/cases/sting_pdac.yaml --mode fixture
python -m pipeline.artifact_writer --copy-to-web generated/cases/sting_pdac
python -m pytest tests/pipeline -q
```

## Acceptance criteria

- [ ] `python -m pipeline.run_workflow --config configs/cases/sting_pdac.yaml --mode fixture` produces complete artifact folder
- [ ] Pipeline runs without frontend
- [ ] Pipeline runs with mocked connector responses
- [ ] Pipeline exits nonzero if any required artifact is missing
- [ ] `artifact_writer --copy-to-web` populates `web/public/data/cases/sting_pdac/`
- [ ] Same command works for all four case configs without code changes
- [ ] `pipeline/AGENT_HANDOFF.md` complete

## Handoff notes required

- CLI flags and artifact directory layout
- Fixture vs live code paths
- Dependencies on synthesis-agent for report generation stubs
- Blockers for integration-agent E2E
