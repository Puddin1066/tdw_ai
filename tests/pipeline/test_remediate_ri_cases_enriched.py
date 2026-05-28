"""Tests for remediate_ri_cases_enriched."""

from pipeline.remediate_ri_cases_enriched import (
    _normalize_supporters,
    remediate_row,
)
from pipeline.ri_cases_enriched_io import empty_row


def test_normalize_supporters_strips_npi_prefix():
    raw = "npi_1023039740|DENNIS AUMENTADO|NEUROLOGY|RI|reviewer"
    assert _normalize_supporters(raw).startswith("1023039740|")


def test_remediate_clears_suggest_pubs_and_rebuilds_thesis():
    row = empty_row("auto_brown_university_drug_overdose")
    row.update(
        {
            "catalog_include": "true",
            "company": "Brown University",
            "title_clean": "Drug overdose",
            "indication": "overdose reversal",
            "comp1_name": "Indivior",
            "comp1_financing_ladder": "Public NASDAQ",
            "total_package_usd": "400000",
            "suggest_publication_titles": "BioMCP candidate paper",
            "investment_thesis": "Near-term RI package: 2,400,000 USD total",
            "physician_lead_name": "SYLVESTER SVIOKLA",
            "physician_lead_npi": "npi_1205850989",
        }
    )
    changes = remediate_row(row)
    assert "cleared:suggest_publication_titles" not in changes
    assert row["suggest_publication_titles"] == "BioMCP candidate paper"
    assert "CAROLINA HAASS-KOFFLER" == row["physician_lead_name"]
    assert "2,400,000" not in row["investment_thesis"]
    assert "400,000" in row["investment_thesis"]


def test_remediate_replaces_placeholder_lead_with_inventor():
    row = empty_row("auto_brown_university_neurogenesis")
    row.update(
        {
            "catalog_include": "true",
            "company": "Brown University",
            "ri_institution": "Brown University",
            "inventors": "NURMIKKO ARTO V|SMITH JOHN",
            "physician_lead_name": "EUGENIE ATALLAH",
            "required_specialties": "neurology|psychiatry",
            "indication": "RI technology opportunity from patent corpus",
            "title_clean": "Neurogenesis modulation",
            "clinical_path_notes": "Trial template auto-matched to NCT123.",
            "comp1_name": "Comp",
            "comp1_financing_ladder": "Series A",
        }
    )
    changes = remediate_row(row)
    assert "physician_lead_from_inventor" in changes
    assert row["physician_lead_name"] == "Arto V Nurmikko"
    assert row["indication"] == "Neurogenesis modulation"
    assert "auto-matched" not in row["clinical_path_notes"].lower()
