from __future__ import annotations

from pipeline.build_ri_combined import _parse_physicians


def test_parse_physicians_dedupes_lead_from_supporters() -> None:
    row = {
        "physician_lead_npi": "npi_1063477032",
        "physician_lead_name": "HEINRICH ELINZANO",
        "physician_supporters": (
            "npi_1043704703|SCOTT WARREN|NEUROLOGY|RHODE ISLAND HOSPITAL|reviewer\n"
            "npi_1063477032|HEINRICH ELINZANO|NEUROLOGY|RHODE ISLAND HOSPITAL|reviewer\n"
            "npi_1063477032|HEINRICH ELINZANO|NEUROLOGY|RHODE ISLAND HOSPITAL|reviewer"
        ),
    }
    roster = _parse_physicians(row)
    ids = [p["physician_id"] for p in roster]
    assert ids.count("npi_1063477032") == 1
    assert roster[0]["is_lead"] == "true"
    assert len(roster) == 2
