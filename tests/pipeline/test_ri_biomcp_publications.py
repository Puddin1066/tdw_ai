"""Tests for BioMCP publication apply helpers."""

from __future__ import annotations

from pipeline.ri_biomcp_publications import classify_ri_lead_pub, match_ri_affiliation


def test_match_ri_affiliation_brown_rih():
    allowlist = ["Brown University", "Rhode Island Hospital"]
    aff = (
        "Department of Diagnostic Imaging, Rhode Island Hospital, "
        "Warren Alpert Medical School of Brown University, Providence, RI"
    )
    assert match_ri_affiliation(aff, allowlist) == "Brown University"


def test_classify_ri_lead_pub_accepts_first_author_ri_affiliation():
    allowlist = ["Brown University", "Rhode Island Hospital"]
    pub = {"pmid": "123", "title": "Thermal ablation outcomes"}
    details = {
        "123": {
            "authors": [
                {
                    "last": "Dupuy",
                    "first": "Damian E",
                    "affiliation": "Rhode Island Hospital, Brown University, Providence, RI",
                }
            ]
        }
    }
    ok, lead, aff, matched = classify_ri_lead_pub(
        pub,
        allowlist=allowlist,
        inventor_surnames={"DUPUY"},
        details=details,
    )
    assert ok
    assert "Dupuy" in lead
    assert aff in allowlist
    assert "DUPUY" in matched


def test_classify_ri_lead_pub_rejects_non_ri_lead():
    allowlist = ["Brown University"]
    pub = {"pmid": "999", "title": "Review citing Dupuy et al."}
    details = {
        "999": {
            "authors": [
                {"last": "Han", "first": "Xiaoying", "affiliation": "Shandong Provincial Hospital"},
            ]
        }
    }
    ok, _, _, _ = classify_ri_lead_pub(
        pub,
        allowlist=allowlist,
        inventor_surnames={"DUPUY"},
        details=details,
    )
    assert not ok
