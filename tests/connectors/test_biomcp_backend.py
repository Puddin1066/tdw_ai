from __future__ import annotations

from connectors.biomcp_adapter import should_use_biomcp_backend
from connectors.biothings import BioThingsConnector
from connectors.chembl import ChEMBLConnector
from connectors.opentargets import OpenTargetsConnector
from tests.connectors.test_connectors_fixture import sting_pdac_config


def test_should_use_biomcp_backend_prefers_connector_specific(monkeypatch) -> None:
    monkeypatch.setenv("CONNECTOR_BACKEND", "legacy")
    monkeypatch.setenv("OPENTARGETS_BACKEND", "biomcp")
    assert should_use_biomcp_backend("opentargets") is True


def test_should_use_biomcp_backend_uses_global(monkeypatch) -> None:
    monkeypatch.delenv("CHEMBL_BACKEND", raising=False)
    monkeypatch.setenv("CONNECTOR_BACKEND", "biomcp")
    assert should_use_biomcp_backend("chembl") is True


def test_opentargets_biomcp_backend_path(monkeypatch) -> None:
    config = sting_pdac_config()
    monkeypatch.setenv("OPENTARGETS_BACKEND", "biomcp")

    def _fake_search(entity: str, term: str, *, limit: int = 25):
        del entity, term, limit
        return {"results": [{"id": "ENSG000001", "name": "TMEM173", "entity": "target"}]}, None

    monkeypatch.setattr("connectors.opentargets.run_biomcp_search", _fake_search)
    result = OpenTargetsConnector().fetch(config, "live")
    assert result.records
    assert result.records[0]["source_record_id"].startswith("opentargets:")
    assert result.raw_payload and result.raw_payload.get("backend") == "biomcp"


def test_chembl_biomcp_backend_path(monkeypatch) -> None:
    config = sting_pdac_config()
    monkeypatch.setenv("CHEMBL_BACKEND", "biomcp")

    def _fake_search(entity: str, term: str, *, limit: int = 25):
        del entity, term, limit
        return {"results": [{"id": "CHEMBL123", "name": "Example Compound", "entity": "drug"}]}, None

    monkeypatch.setattr("connectors.chembl.run_biomcp_search", _fake_search)
    result = ChEMBLConnector().fetch(config, "live")
    assert result.records
    assert result.records[0]["source_record_id"].startswith("chembl:")
    assert result.raw_payload and result.raw_payload.get("backend") == "biomcp"


def test_biothings_biomcp_backend_path(monkeypatch) -> None:
    config = sting_pdac_config()
    monkeypatch.setenv("BIOTHINGS_BACKEND", "biomcp")

    def _fake_search(entity: str, term: str, *, limit: int = 25):
        del entity, term, limit
        return {"results": [{"id": "6737", "symbol": "TMEM173", "summary": "STING gene"}]}, None

    monkeypatch.setattr("connectors.biothings.run_biomcp_search", _fake_search)
    result = BioThingsConnector().fetch(config, "live")
    assert result.records
    assert result.records[0]["source_record_id"].startswith("biothings:")
    assert result.raw_payload and result.raw_payload.get("backend") == "biomcp"
