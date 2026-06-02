"""Tests for agentic RI cases enrichment."""

from pipeline.enrich_ri_cases_agent import (
    apply_agent_payload,
    call_agent,
    verify_agent_urls,
)
from pipeline.ri_cases_enriched_io import empty_row


def test_call_agent_uses_fixture():
    row = empty_row("test_agent_case")
    row["catalog_include"] = "true"
    row["title_clean"] = "Test Program"
    row["indication"] = "oncology"
    payload, warnings = call_agent(row, prefer_live=False)
    assert payload["comps"][0]["name"] == "Fixture Therapeutics"
    assert any("MOCK/SYNTHETIC" in w for w in warnings)


def test_call_agent_fallback_without_fixture():
    row = empty_row("no_fixture_case_xyz")
    row["catalog_include"] = "true"
    row["comp1_name"] = "Acme Bio"
    row["comp1_type"] = "startup"
    payload, warnings = call_agent(row, prefer_live=False)
    assert payload["comps"]
    assert payload["comps"][0]["name"] == "Acme Bio"
    assert any("fallback" in w.lower() or "MOCK" in w for w in warnings)


def test_apply_agent_payload_writes_audit_notes():
    row = empty_row("test_agent_case")
    row["catalog_include"] = "true"
    payload = {
        "comps": [
            {
                "slot": 2,
                "name": "New Comp Inc",
                "type": "startup",
                "role": "diagnostic",
                "notes": "Septic diagnostic path",
                "development_path": "510k",
                "financing_search_queries": ["New Comp Inc funding"],
                "supporting_citation_queries": [],
            }
        ],
        "comp_gaps": "Need verified URL on comp1",
        "rd_milestones_draft": "Complete analytical validation",
        "rd_plan_summary_draft": "",
        "literature_narrative_draft": "",
        "physician_profile_queries": [],
    }
    changes = apply_agent_payload(row, payload, verified={}, agent_warnings=["MOCK/SYNTHETIC test"])
    assert "comp2_suggested" in changes
    assert row["comp2_name"] == "New Comp Inc"
    assert row["comp2_validation_status"] == "suggested"
    assert "agent_comp2" in row["web_search_notes"]
    assert row["rd_milestones"] == "Complete analytical validation"
    assert row["enrichment_status"] == "agent_enriched"


def test_apply_agent_skips_approved():
    row = empty_row("test_agent_case")
    row["catalog_include"] = "true"
    row["review_status"] = "approved"
    changes = apply_agent_payload(
        row,
        {"comps": [], "rd_milestones_draft": "x"},
        verified={},
    )
    assert changes == []


def test_verify_agent_urls_no_fetch():
    payload = {
        "comps": [
            {
                "slot": 1,
                "financing_search_queries": ["Acme Bio funding"],
            }
        ]
    }
    assert verify_agent_urls(payload, fetch=False) == {}
