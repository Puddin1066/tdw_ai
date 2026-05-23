from __future__ import annotations

from dataclasses import replace

from connectors.biomcp_adapter import should_use_biomcp_backend
from connectors.biothings import BioThingsConnector
from connectors.chembl import ChEMBLConnector
from connectors.clinicaltrials import ClinicalTrialsConnector
from connectors.gwas import GwasConnector
from connectors.opentargets import OpenTargetsConnector
from connectors.openfda import OpenFdaConnector
from connectors.pharmgkb import PharmGkbConnector
from connectors.pubmed import PubMedConnector
from connectors.reactome import ReactomeConnector
from connectors.uniprot import UniProtConnector
from connectors.base import build_raw_query
from pipeline.types import IndicationConfig, TargetConfig
from tests.connectors.test_connectors_fixture import sting_pdac_config


def test_should_use_biomcp_backend_prefers_connector_specific(monkeypatch) -> None:
    monkeypatch.setenv("CONNECTOR_BACKEND", "legacy")
    monkeypatch.setenv("OPENTARGETS_BACKEND", "biomcp")
    assert should_use_biomcp_backend("opentargets") is True


def test_should_use_biomcp_backend_uses_global(monkeypatch) -> None:
    monkeypatch.delenv("CHEMBL_BACKEND", raising=False)
    monkeypatch.setenv("CONNECTOR_BACKEND", "biomcp")
    assert should_use_biomcp_backend("chembl") is True


def test_should_use_biomcp_backend_defaults_core_connectors(monkeypatch) -> None:
    monkeypatch.delenv("CONNECTOR_BACKEND", raising=False)
    monkeypatch.delenv("PUBMED_BACKEND", raising=False)
    monkeypatch.delenv("OPENTARGETS_BACKEND", raising=False)
    monkeypatch.delenv("UNIPROT_BACKEND", raising=False)
    assert should_use_biomcp_backend("pubmed") is True
    assert should_use_biomcp_backend("opentargets") is True
    assert should_use_biomcp_backend("uniprot") is True


def test_should_use_biomcp_backend_allows_native_override(monkeypatch) -> None:
    monkeypatch.setenv("CONNECTOR_BACKEND", "biomcp")
    monkeypatch.setenv("PUBMED_BACKEND", "native")
    assert should_use_biomcp_backend("pubmed") is False


def test_opentargets_biomcp_backend_path(monkeypatch) -> None:
    config = sting_pdac_config()
    monkeypatch.setenv("OPENTARGETS_BACKEND", "biomcp")

    def _fake_search(entity: str, term: str | None, *, limit: int = 25, offset: int = 0, options=None):
        del entity, term, limit, offset, options
        return {"results": [{"id": "ENSG000001", "name": "TMEM173", "entity": "target"}]}, None

    def _fake_gene_get(identifier: str, *, enrich: str | None = None):
        del identifier, enrich
        return {"results": [{"id": "ENSG000001", "summary": "STING pathway biology"}]}, None

    monkeypatch.setattr("connectors.opentargets.run_biomcp_search", _fake_search)
    monkeypatch.setattr("connectors.opentargets.run_biomcp_gene_get", _fake_gene_get)
    monkeypatch.setattr("connectors.opentargets.run_biomcp_drug_get", lambda token: (None, f"missing {token}"))
    monkeypatch.setattr("connectors.opentargets.run_biomcp_disease_get", lambda token: (None, f"missing {token}"))
    result = OpenTargetsConnector().fetch(config, "live")
    assert result.records
    assert result.records[0]["source_record_id"].startswith("opentargets:")
    assert result.raw_payload and result.raw_payload.get("backend") == "biomcp"


def test_chembl_biomcp_backend_path(monkeypatch) -> None:
    config = sting_pdac_config()
    monkeypatch.setenv("CHEMBL_BACKEND", "biomcp")

    def _fake_search(entity: str, term: str | None, *, limit: int = 25, offset: int = 0, options=None):
        del entity, term, limit, offset, options
        return {"results": [{"id": "CHEMBL123", "name": "Example Compound", "entity": "drug"}]}, None

    def _fake_drug_get(identifier: str):
        del identifier
        return {"results": [{"chembl_id": "CHEMBL123", "description": "Kinase inhibitor"}]}, None

    monkeypatch.setattr("connectors.chembl.run_biomcp_search", _fake_search)
    monkeypatch.setattr("connectors.chembl.run_biomcp_drug_get", _fake_drug_get)
    result = ChEMBLConnector().fetch(config, "live")
    assert result.records
    assert result.records[0]["source_record_id"].startswith("chembl:")
    assert result.raw_payload and result.raw_payload.get("backend") == "biomcp"


def test_biothings_biomcp_backend_path(monkeypatch) -> None:
    config = sting_pdac_config()
    monkeypatch.setenv("BIOTHINGS_BACKEND", "biomcp")

    def _fake_search(entity: str, term: str | None, *, limit: int = 25, offset: int = 0, options=None):
        del entity, term, limit, offset, options
        return {"results": [{"id": "6737", "symbol": "TMEM173", "summary": "STING gene"}]}, None

    def _fake_gene_get(identifier: str, *, enrich: str | None = None):
        del identifier, enrich
        return {"results": [{"gene_id": "6737", "summary": "STING biology details"}]}, None

    monkeypatch.setattr("connectors.biothings.run_biomcp_search", _fake_search)
    monkeypatch.setattr("connectors.biothings.run_biomcp_gene_get", _fake_gene_get)
    result = BioThingsConnector().fetch(config, "live")
    assert result.records
    assert result.records[0]["source_record_id"].startswith("biothings:")
    assert result.raw_payload and result.raw_payload.get("backend") == "biomcp"


def test_pubmed_biomcp_backend_path(monkeypatch) -> None:
    config = sting_pdac_config()
    monkeypatch.setenv("PUBMED_BACKEND", "biomcp")

    def _fake_search(entity: str, term: str | None, *, limit: int = 25, offset: int = 0, options=None):
        del entity, term, limit, offset, options
        return {"results": [{"id": "35600001", "title": "STING in PDAC"}]}, None

    monkeypatch.setattr("connectors.pubmed.run_biomcp_search", _fake_search)
    result = PubMedConnector().fetch(config, "live")
    assert result.records
    assert result.records[0]["source_record_id"].startswith("pubmed:")
    assert result.raw_payload and result.raw_payload.get("backend") == "biomcp"


def test_clinicaltrials_biomcp_backend_path(monkeypatch) -> None:
    config = sting_pdac_config()
    monkeypatch.setenv("CLINICALTRIALS_BACKEND", "biomcp")

    def _fake_search(entity: str, term: str | None, *, limit: int = 25, offset: int = 0, options=None):
        del entity, term, limit, offset, options
        return {
            "results": [
                {
                    "nct_id": "NCT01234567",
                    "title": "STING agonist in PDAC",
                    "status": "RECRUITING",
                    "conditions": ["pancreatic cancer"],
                }
            ]
        }, None

    monkeypatch.setattr("connectors.clinicaltrials.run_biomcp_search", _fake_search)
    result = ClinicalTrialsConnector().fetch(config, "live")
    assert result.records
    assert result.records[0]["source_record_id"].startswith("clinicaltrials:")
    assert result.raw_payload and result.raw_payload.get("backend") == "biomcp"


def test_uniprot_biomcp_backend_path(monkeypatch) -> None:
    config = sting_pdac_config()
    monkeypatch.setenv("UNIPROT_BACKEND", "biomcp")

    def _fake_search(entity: str, term: str | None, *, limit: int = 25, offset: int = 0, options=None):
        del term, limit, offset, options
        assert entity == "protein"
        return {"results": [{"id": "P27544", "name": "TMEM173 protein"}]}, None

    monkeypatch.setattr("connectors.uniprot.run_biomcp_search", _fake_search, raising=False)
    monkeypatch.setattr("connectors.biomcp_generic.run_biomcp_search", _fake_search)
    monkeypatch.setattr(
        "connectors.biomcp_generic.run_biomcp_gene_get",
        lambda identifier, enrich=None: (
            {"results": [{"id": identifier, "summary": "Reactome gene detail"}]},
            None,
        ),
    )
    monkeypatch.setattr(
        "connectors.biomcp_generic.run_biomcp_variant_get",
        lambda identifier, extensive=True: (None, f"not a variant: {identifier}"),
    )
    result = UniProtConnector().fetch(config, "live")
    assert result.records
    assert result.records[0]["source_record_id"].startswith("uniprot:protein:")
    assert result.raw_payload and result.raw_payload.get("backend") == "biomcp"


def test_other_new_connectors_biomcp_backend_path(monkeypatch) -> None:
    config = sting_pdac_config()
    monkeypatch.setenv("REACTOME_BACKEND", "biomcp")
    monkeypatch.setenv("GWAS_BACKEND", "biomcp")
    monkeypatch.setenv("PHARMGKB_BACKEND", "biomcp")
    monkeypatch.setenv("OPENFDA_BACKEND", "biomcp")

    def _fake_search(entity: str, term: str | None, *, limit: int = 25, offset: int = 0, options=None):
        del term, limit, offset, options
        if entity == "fda-label":
            return {"results": [{"label_id": "label-1", "title": "Imatinib label"}]}, None
        return {"results": [{"id": f"{entity}-1", "name": f"{entity} signal"}]}, None

    monkeypatch.setattr("connectors.biomcp_generic.run_biomcp_search", _fake_search)
    monkeypatch.setattr(
        "connectors.biomcp_generic.run_biomcp_gene_get",
        lambda identifier, enrich=None: (
            {"results": [{"id": identifier, "summary": f"gene detail {enrich or 'none'}"}]},
            None,
        ),
    )
    monkeypatch.setattr(
        "connectors.biomcp_generic.run_biomcp_variant_get",
        lambda identifier, extensive=True: (
            {"results": [{"id": identifier, "summary": "variant detail"}]},
            None,
        ),
    )
    monkeypatch.setattr("connectors.openfda.run_biomcp_search", _fake_search)
    monkeypatch.setattr(
        "connectors.openfda.run_biomcp_openfda_label_get",
        lambda label_id, sections=None: ({"results": [{"id": label_id, "summary": "label details"}]}, None),
    )

    for connector, prefix in [
        (ReactomeConnector(), "reactome:pathway:"),
        (GwasConnector(), "gwas:gwas:"),
        (PharmGkbConnector(), "pharmgkb:pgx:"),
        (OpenFdaConnector(), "openfda:"),
    ]:
        result = connector.fetch(config, "live")
        assert result.records
        assert result.records[0]["source_record_id"].startswith(prefix)
        assert result.raw_payload and result.raw_payload.get("backend") == "biomcp"


def test_build_raw_query_handles_missing_anchor_fields() -> None:
    class _Target:
        name = ""
        aliases: list[str] = []

    class _Indication:
        name = "pancreatic cancer"
        aliases: list[str] = []

    assert build_raw_query(_Target(), _Indication()) == "(pancreatic cancer)"
    _Indication.name = ""
    assert build_raw_query(_Target(), _Indication()) == ""


def _empty_anchor_config():
    config = sting_pdac_config()
    return replace(
        config,
        target=TargetConfig(name="", canonical_id=None, aliases=[]),
        indication=IndicationConfig(name="", aliases=[]),
    )


def test_pubmed_skips_with_warning_when_no_anchors() -> None:
    config = _empty_anchor_config()
    result = PubMedConnector().fetch(config, "live")
    assert result.records == []
    assert any("PubMed skipped" in warning for warning in result.warnings)


def test_clinicaltrials_skips_with_warning_when_no_anchors() -> None:
    config = _empty_anchor_config()
    result = ClinicalTrialsConnector().fetch(config, "live")
    assert result.records == []
    assert any("ClinicalTrials skipped" in warning for warning in result.warnings)


def test_biothings_skips_with_warning_when_no_anchors() -> None:
    config = _empty_anchor_config()
    result = BioThingsConnector().fetch(config, "live")
    assert result.records == []
    assert any("BioThings skipped" in warning for warning in result.warnings)


def test_chembl_skips_with_warning_when_no_anchors() -> None:
    config = _empty_anchor_config()
    result = ChEMBLConnector().fetch(config, "live")
    assert result.records == []
    assert any("ChEMBL skipped" in warning for warning in result.warnings)


def test_opentargets_skips_with_warning_when_no_anchors() -> None:
    config = _empty_anchor_config()
    result = OpenTargetsConnector().fetch(config, "live")
    assert result.records == []
    assert any("Open Targets skipped" in warning for warning in result.warnings)


def test_gwas_and_pharmgkb_skip_without_gene_symbol_anchor() -> None:
    config = _empty_anchor_config()
    gwas_result = GwasConnector().fetch(config, "live")
    pharm_result = PharmGkbConnector().fetch(config, "live")
    assert gwas_result.records == []
    assert pharm_result.records == []
    assert any("GWAS skipped" in warning for warning in gwas_result.warnings)
    assert any("PharmGKB skipped" in warning for warning in pharm_result.warnings)
