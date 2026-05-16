"""Fixture-mode integration tests for all connectors (sting_pdac case)."""

from __future__ import annotations

import re

import pytest

from connectors import CONNECTORS
from connectors.base import (
    CaseConfig,
    ConnectorResult,
    IndicationConfig,
    LimitsConfig,
    SourcesConfig,
    TargetConfig,
)
from pipeline.types import RunModeDefaults

ISO_8601_Z = re.compile(r"^\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}Z$")


def sting_pdac_config() -> CaseConfig:
    return CaseConfig(
        case_id="sting_pdac",
        display_name="STING / Pancreatic Cancer",
        workflow="translational_diligence",
        version="v0.5",
        target=TargetConfig(
            name="STING",
            canonical_id=None,
            aliases=["TMEM173", "Stimulator of Interferon Genes"],
        ),
        indication=IndicationConfig(
            name="pancreatic cancer",
            aliases=["pancreatic ductal adenocarcinoma", "PDAC"],
        ),
        sources=SourcesConfig(
            pubmed=True,
            clinicaltrials=True,
            opentargets=True,
            chembl=True,
            biothings=True,
            local_docs=False,
        ),
        limits=LimitsConfig(
            max_literature_records=50,
            max_trials=100,
            max_evidence_rows=100,
        ),
        run_mode_defaults=RunModeDefaults(fixture_allowed=True, live_allowed=True),
    )


@pytest.fixture
def config() -> CaseConfig:
    return sting_pdac_config()


@pytest.mark.parametrize("connector_name", list(CONNECTORS.keys()))
def test_connector_returns_result_in_fixture_mode(connector_name: str, config: CaseConfig) -> None:
    connector = CONNECTORS[connector_name]
    result = connector.fetch(config, "fixture")

    assert isinstance(result, ConnectorResult)
    assert result.connector_name == connector_name
    assert result.case_id == "sting_pdac"
    assert result.mode == "fixture"
    assert result.query.target == "STING"
    assert result.query.indication == "pancreatic cancer"
    assert "STING" in result.query.raw_query
    assert "pancreatic cancer" in result.query.raw_query
    assert ISO_8601_Z.match(result.retrieved_at)
    assert isinstance(result.records, list)
    assert isinstance(result.errors, list)
    assert isinstance(result.warnings, list)
    assert result.provenance.source_name
    assert result.provenance.source_url


@pytest.mark.parametrize("connector_name", list(CONNECTORS.keys()))
def test_connector_live_mode_returns_result_not_raise(connector_name: str, config: CaseConfig) -> None:
    connector = CONNECTORS[connector_name]
    result = connector.fetch(config, "live")

    assert isinstance(result, ConnectorResult)
    assert result.mode == "live"
    assert result.errors, f"{connector_name} live mode should report NotImplemented in errors"


def test_pubmed_fixture_has_literature_records(config: CaseConfig) -> None:
    result = CONNECTORS["pubmed"].fetch(config, "fixture")
    assert len(result.records) >= 1
    assert result.records[0]["source_record_id"].startswith("pubmed:")
    assert "pmid" in result.records[0]


def test_clinicaltrials_fixture_has_nct_ids(config: CaseConfig) -> None:
    result = CONNECTORS["clinicaltrials"].fetch(config, "fixture")
    assert any("nct_id" in r for r in result.records)


def test_local_docs_disabled_adds_warning(config: CaseConfig) -> None:
    result = CONNECTORS["local_docs"].fetch(config, "fixture")
    assert any("local_docs disabled" in w for w in result.warnings)
