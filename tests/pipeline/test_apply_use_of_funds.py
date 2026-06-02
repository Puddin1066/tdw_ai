"""Tests for use-of-funds allocation on enriched rows."""

from pipeline.ri_cases_enriched_io import apply_use_of_funds


def test_apply_use_of_funds_splits_package():
    row = {
        "total_package_usd": "400000",
        "opportunity_type": "medical_device",
        "clinical_cost_usd": "120000",
    }
    assert apply_use_of_funds(row) is True
    assert int(row["clinical_allocation_usd"]) > 0
    assert int(row["rd_allocation_usd"]) > 0
    assert int(row["clinical_allocation_usd"]) + int(row["rd_allocation_usd"]) == 400000
    assert "physician syndicate" in row["financing_rationale"].lower()
