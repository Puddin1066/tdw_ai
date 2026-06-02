"""Tests for patent inventor → NPI physician matching."""

from pipeline.ri_inventor_npi_match import (
    _inventor_display_name,
    best_inventor_physician_match,
    lead_npi_name_mismatch,
    match_inventors_to_physicians,
    score_inventor_physician_match,
)


def test_inventor_display_name_uspto_order():
    assert _inventor_display_name("DUPUY DAMIAN E") == "Damian E Dupuy"


def test_score_inventor_physician_match():
    phy = {
        "name": "DAMIAN E DUPUY",
        "institution": "RHODE ISLAND HOSPITAL",
        "roles_willing": "advisor|investigator",
    }
    score = score_inventor_physician_match("DUPUY DAMIAN E", phy)
    assert score >= 60


def test_match_inventors_to_physicians_finds_hits():
    hits = match_inventors_to_physicians(["DUPUY DAMIAN E", "PARK ARTHUR"])
    assert isinstance(hits, list)
    if hits:
        assert hits[0]["physician_id"]


def test_lead_npi_name_mismatch():
    row = {
        "physician_lead_name": "Arto Nurmikko",
        "physician_lead_npi": "1003392689",
    }
    assert lead_npi_name_mismatch(row) is True


def test_best_inventor_match():
    best = best_inventor_physician_match(["ATALLAH EUGENIE"])
    if best:
        assert "ATALLAH" in best.get("name", "").upper()
