"""Synthesis sanitization should avoid flattened confidence and severity."""

from __future__ import annotations

from pipeline.synthesis_runner import _sanitize_evidence_data, _sanitize_risk_data


def test_sanitize_evidence_data_calibrates_flat_confidence() -> None:
    payload = {
        "rows": [
            {
                "evidence_id": "e1",
                "claim_text": "Strong clinical response signal reported.",
                "claim_type": "clinical",
                "support_status": "supported",
                "confidence": 0.4,
                "source_record_ids": ["clinicaltrials:NCT00000001", "pubmed:12345678"],
                "quoted_evidence": [
                    {
                        "source_record_id": "pubmed:12345678",
                        "text": "Patients achieved durable remission with statistically significant outcomes.",
                        "location": "abstract",
                    }
                ],
                "limitations": ["Limited sample size."],
            },
            {
                "evidence_id": "e2",
                "claim_text": "Signal is weak and mostly hypothesis-generating.",
                "claim_type": "evidence_gap",
                "support_status": "insufficient_evidence",
                "confidence": 0.4,
                "source_record_ids": [],
                "quoted_evidence": [
                    {
                        "source_record_id": "pubmed:99999999",
                        "text": "Exploratory signal only; no definitive endpoint met.",
                        "location": "abstract",
                    }
                ],
                "limitations": ["model output omitted explicit limitations"],
            },
        ]
    }

    sanitized = _sanitize_evidence_data(payload, "test_case")
    rows = sanitized["rows"]
    assert rows[0]["confidence"] > rows[1]["confidence"]
    assert rows[0]["confidence"] != 0.4
    assert rows[1]["confidence"] != 0.4


def test_sanitize_evidence_data_drops_ungrounded_rows() -> None:
    payload = {
        "rows": [
            {
                "evidence_id": "e1",
                "claim_text": "Ungrounded claim should be removed.",
                "claim_type": "clinical",
                "support_status": "supported",
                "confidence": 0.7,
                "source_record_ids": [],
                "quoted_evidence": [],
                "limitations": ["No citation provided."],
            }
        ]
    }

    sanitized = _sanitize_evidence_data(payload, "test_case")
    assert sanitized["rows"][0]["source_record_ids"] == []
    assert sanitized["rows"][0]["claim_type"] == "evidence_gap"


def test_sanitize_risk_data_derives_non_flat_severity_and_confidence() -> None:
    payload = {
        "risks": [
            {
                "risk_id": "r1",
                "title": "Unspecified risk",
                "description": "Potential cardiovascular toxicity requires close monitoring.",
                "category": "safety",
                "severity": "medium",
                "confidence": 0.5,
                "inferred": False,
                "evidence_ids": ["e1", "e2"],
                "source_record_ids": ["clinicaltrials:NCT00000001", "pubmed:12345678"],
            },
            {
                "risk_id": "r2",
                "title": "Unspecified risk",
                "description": "Data remains sparse for this mechanism in the target segment.",
                "category": "evidence_gap",
                "severity": "medium",
                "confidence": 0.5,
                "inferred": True,
                "evidence_ids": [],
                "source_record_ids": [],
            },
        ]
    }

    sanitized = _sanitize_risk_data(payload, "test_case")
    risks = sanitized["risks"]
    assert risks[0]["title"] != "Unspecified risk"
    assert risks[1]["title"] != "Unspecified risk"
    assert risks[0]["confidence"] != 0.5
    assert risks[1]["confidence"] != 0.5
    assert risks[0]["severity"] in {"high", "critical"}
    assert risks[1]["severity"] == "low"
