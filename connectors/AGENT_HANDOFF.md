# Connectors Agent Handoff

**Status:** pending

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

- `ConnectorResult` schema/types pending schema-agent.
- No connector implementations yet.

## Downstream consumers

- backend-pipeline-agent
