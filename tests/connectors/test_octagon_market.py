from __future__ import annotations

from connectors.octagon_market import OctagonMarketConnector
from tests.connectors.test_connectors_fixture import sting_pdac_config


def test_octagon_market_live_maps_rows(monkeypatch) -> None:
    config = sting_pdac_config()

    def _fake_search(topic: str, *, limit: int = 25):
        del topic, limit
        return {
            "results": [
                {"id": "cmp-1", "company": "Acme Bio", "role": "partner", "score": 0.9},
                {"id": "cmp-2", "company": "Beta Pharma", "role": "acquirer", "score": 0.8},
            ]
        }, None

    monkeypatch.setattr("connectors.octagon_market.run_octagon_search", _fake_search)
    result = OctagonMarketConnector().fetch(config, "live")
    assert not result.errors
    assert len(result.records) == 2
    assert result.records[0]["source_record_id"].startswith("octagon:")
    assert result.records[0]["biology_source"] == "octagon"


def test_octagon_market_live_warns_when_command_missing(monkeypatch) -> None:
    config = sting_pdac_config()

    def _fake_search(topic: str, *, limit: int = 25):
        del topic, limit
        return None, "octagon executable not found in PATH"

    monkeypatch.setattr("connectors.octagon_market.run_octagon_search", _fake_search)
    result = OctagonMarketConnector().fetch(config, "live")
    assert not result.errors
    assert not result.records
    assert result.warnings
