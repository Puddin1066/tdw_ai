from __future__ import annotations

from connectors.clinicaltrials import (
    ClinicalTrialsConnector,
    _build_search_terms,
    _dedupe_trials,
    _normalize_study,
    _relevance_score,
)
from tests.connectors.test_connectors_fixture import sting_pdac_config


def test_normalize_study_maps_core_fields() -> None:
    study = {
        "protocolSection": {
            "identificationModule": {
                "nctId": "NCT12345678",
                "briefTitle": "Example trial",
                "officialTitle": "Official example trial",
            },
            "statusModule": {
                "overallStatus": "RECRUITING",
                "startDateStruct": {"date": "2024-01-01"},
                "completionDateStruct": {"date": "2026-06-30"},
            },
            "designModule": {
                "studyType": "INTERVENTIONAL",
                "phases": ["PHASE1", "PHASE2"],
                "enrollmentInfo": {"count": 120},
            },
            "sponsorCollaboratorsModule": {"leadSponsor": {"name": "Example Sponsor"}},
            "conditionsModule": {"conditions": ["Pancreatic Cancer"]},
            "armsInterventionsModule": {"interventions": [{"name": "Drug A"}]},
        }
    }

    record = _normalize_study(study, 0)

    assert record is not None
    assert record["nct_id"] == "NCT12345678"
    assert record["brief_title"] == "Example trial"
    assert record["phase"] == "PHASE1, PHASE2"
    assert record["study_type"] == "INTERVENTIONAL"
    assert record["enrollment_count"] == 120
    assert record["interventions"] == ["Drug A"]
    assert record["conditions"] == ["Pancreatic Cancer"]


def test_clinicaltrials_live_fetch_uses_api_payload(monkeypatch) -> None:
    class _Resp:
        def raise_for_status(self) -> None:
            return None

        def json(self) -> dict[str, object]:
            return {
                "studies": [
                    {
                        "protocolSection": {
                            "identificationModule": {
                                "nctId": "NCT87654321",
                                "briefTitle": "Live mapped trial",
                            },
                            "statusModule": {"overallStatus": "ACTIVE_NOT_RECRUITING"},
                        }
                    }
                ]
            }

    class _Client:
        def __init__(self, *args, **kwargs) -> None:
            del args, kwargs

        def __enter__(self):
            return self

        def __exit__(self, exc_type, exc, tb) -> bool:
            del exc_type, exc, tb
            return False

        def get(self, *args, **kwargs):
            del args, kwargs
            return _Resp()

    monkeypatch.setattr("connectors.clinicaltrials.httpx.Client", _Client)
    config = sting_pdac_config()

    result = ClinicalTrialsConnector().fetch(config, "live")

    assert result.mode == "live"
    assert not result.errors
    assert result.records
    assert result.records[0]["nct_id"] == "NCT87654321"


def test_build_search_terms_returns_multiple_queries() -> None:
    config = sting_pdac_config()
    terms = _build_search_terms(config, "(STING) AND (pancreatic cancer)")
    assert len(terms) >= 3
    assert any("solid tumor" in term for term in terms)


def test_dedupe_trials_by_nct_id() -> None:
    studies = [
        {"protocolSection": {"identificationModule": {"nctId": "NCT00000001"}}},
        {"protocolSection": {"identificationModule": {"nctId": "NCT00000001"}}},
        {"protocolSection": {"identificationModule": {"nctId": "NCT00000002"}}},
    ]
    deduped = _dedupe_trials(studies)
    assert len(deduped) == 2


def test_relevance_score_rewards_target_and_indication_matches() -> None:
    config = sting_pdac_config()
    record = {
        "title": "STING agonist in pancreatic ductal adenocarcinoma",
        "official_title": "TMEM173 strategy in PDAC",
        "conditions": ["Pancreatic Cancer"],
        "interventions": ["STING agonist"],
        "overall_status": "RECRUITING",
        "phase": "PHASE2",
    }
    assert _relevance_score(config, record) > 0.5
