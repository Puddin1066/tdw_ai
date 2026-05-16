# 04 Connector Agent

**Agent:** connectors-agent

**Objective:** Implement public biomedical source adapters returning standardized `ConnectorResult` envelopes, with fixture mode for offline development.

## May modify

- `connectors/**`
- `tests/connectors/**`
- `tests/fixtures/connectors/**`

## Must not modify

- `pipeline/**` (except after interface review documented in handoff)
- `web/**`
- `evals/**`
- `schemas/**` (request schema-agent for envelope changes)

## Input contracts consumed

- PRD §9 Shared Interface: ConnectorResult
- PRD §24.3 Connector Contract
- PRD §24.4 External API Endpoint Contracts
- `configs/cases/*.yaml` — `sources` and `limits` blocks

## Output contracts produced

- `connectors/base.py` — `BaseConnector` protocol
- `connectors/pubmed.py`
- `connectors/clinicaltrials.py`
- `connectors/opentargets.py`
- `connectors/chembl.py`
- `connectors/biothings.py`
- `connectors/local_docs.py`
- Fixture responses under `tests/fixtures/connectors/`
- Updated `connectors/AGENT_HANDOFF.md`

## Implementation steps

1. Define `ConnectorResult` pydantic model aligned with PRD §9.
2. Implement `fetch(config: dict) -> ConnectorResult` per connector.
3. Add fixture mode branch reading `tests/fixtures/connectors/`.
4. Preserve raw API payloads in `raw_response` fields.
5. Normalize obvious IDs (PMID, NCT, ChEMBL) in metadata.
6. Return errors/warnings in envelope; no unhandled exceptions for recoverable failures.
7. Unit test each connector in fixture mode.

## Tests to run

```bash
python -m pytest tests/connectors -q
# Per-connector smoke:
python -c "from connectors.pubmed import PubMedConnector; ..."  # fixture mode
```

## Acceptance criteria

- [ ] Each connector implements `fetch(config: dict) -> ConnectorResult`
- [ ] Each connector has fixture tests passing without API keys
- [ ] Fixture mode works for all enabled sources in case configs
- [ ] Recoverable source failures appear in `errors`/`warnings`, not uncaught exceptions
- [ ] `connectors/AGENT_HANDOFF.md` documents interface and fixture paths
- [ ] Live mode documented with required env vars (not used in CI)

## Handoff notes required

- `ConnectorResult` field definitions and example JSON
- Fixture file naming convention
- Rate limits and env vars for live mode
- Blockers for pipeline-agent integration
