# 10 Live Connector Agent (Phase 2)

**Agent:** connectors-agent

**Objective:** Ensure at least one live connector (PubMed) returns records for `sting_pdac` in live mode.

## May modify

- `connectors/pubmed.py`
- `pipeline/build_sources.py`
- `tests/connectors/**` (add `@pytest.mark.live` tests)

## Verify

```bash
pytest tests/connectors -q -m "not live"
# Manual with network:
pytest tests/connectors -q -m live
```

## Acceptance

- `pipeline.run_workflow --mode live` includes live PubMed records when network available
- Errors stay in ConnectorResult envelope
