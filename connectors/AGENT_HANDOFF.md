# Connectors Agent Handoff

**Status:** fixture complete; live fetch Phase 2 (`tasks/10_live_connector_agent.md`)

**Owner agent:** connectors-agent

**Task file:** `tasks/04_connector_agent.md`

## Files modified

_None yet — scaffold placeholder._

## Interfaces consumed

- PRD §9 ConnectorResult
- PRD §24.3–24.4 connector contracts
- `configs/cases/*.yaml` source flags

## Interfaces produced

- `connectors/*.py` implementing `fetch(config) -> ConnectorResult`
- `tests/fixtures/connectors/` samples

## Commands to test

```bash
python -m pytest tests/connectors -q
```

## Assumptions

- Pipeline invokes connectors only through documented interface.

## Blockers

- PubMed **live** fetch via NCBI E-utilities (`httpx`). Other connectors: fixture or `NotImplemented` in live mode.
- No connector implementations yet.

## Downstream consumers

- backend-pipeline-agent
