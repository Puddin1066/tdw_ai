"""Tests for comp site dossier merge and extraction helpers."""

from __future__ import annotations

from pipeline.comp_site_dossier import (
    build_case_rollup,
    merge_dossier_into_precedent,
    rebuild_by_case_index,
    select_precedents_for_enrichment,
    wrap_dossier_entry,
)
from pipeline.comp_site_extract import discover_site_map, html_to_text


SAMPLE_HTML = """
<html><body>
<a href="/clinical-evidence/">Clinical Evidence</a>
<a href="/reimbursement/">Reimbursement Support</a>
<a href="/investors/">Investors</a>
<p>FDA-cleared platform for hospital adoption and Medicare coverage pathways.</p>
</body></html>
"""


def test_discover_site_map_from_homepage_links() -> None:
    site_map = discover_site_map("https://example.com/", SAMPLE_HTML)
    assert site_map["corporate"].rstrip("/") == "https://example.com"
    assert "clinical" in site_map
    assert "reimbursement" in site_map
    assert "investors" in site_map


def test_select_precedents_prefers_verified_anchor() -> None:
    rows = [
        {"precedent_rank": "1", "precedent_name": "Incumbent", "precedent_url": "https://a.com", "validation_status": "suggested", "value_anchor_usd": ""},
        {"precedent_rank": "2", "precedent_name": "Startup", "precedent_url": "https://b.com", "validation_status": "verified", "value_anchor_usd": "1000000"},
    ]
    selected = select_precedents_for_enrichment(rows, max_comps=2)
    assert [r["precedent_name"] for r in selected] == ["Startup", "Incumbent"]


def test_merge_dossier_into_precedent() -> None:
    precedent = {"name": "ClearPoint Neuro", "validation_status": "verified"}
    dossier = wrap_dossier_entry(
        case_id="case_a",
        case_title="Test case",
        precedent={"precedent_name": "ClearPoint Neuro", "precedent_rank": "1", "precedent_type": "startup", "precedent_notes": "", "inferred_development": "Commercial", "inferred_financing": "Public"},
        dossier_body={
            "precedent_name": "ClearPoint Neuro",
            "corporate_url": "https://clearpointneuro.com",
            "site_map": {"corporate": "https://clearpointneuro.com"},
            "science_summary": "MRI-guided neuro navigation.",
            "key_publications": [],
            "clinical_milestones": [],
            "kol_signals": [],
            "reimbursement_notes": [{"text": "Coverage support.", "source_url": "https://clearpointneuro.com/reimbursement", "source": "comp_site_extract"}],
        },
        warnings=[],
        fetched=True,
    )
    merged = merge_dossier_into_precedent(precedent, dossier)
    assert merged["site_dossier"]["science_summary"].startswith("MRI-guided")
    assert merged["comparable_fit"] == "direct"


def test_rebuild_by_case_index_rollup() -> None:
    bundle = {
        "by_key": {
            "case_a::ClearPoint Neuro": wrap_dossier_entry(
                case_id="case_a",
                case_title="Brain device",
                precedent={"precedent_name": "ClearPoint Neuro", "precedent_rank": "1", "precedent_type": "startup", "precedent_notes": "", "inferred_development": "", "inferred_financing": ""},
                dossier_body={
                    "precedent_name": "ClearPoint Neuro",
                    "corporate_url": "https://clearpointneuro.com",
                    "site_map": {"corporate": "https://clearpointneuro.com"},
                    "science_summary": "",
                    "key_publications": [],
                    "clinical_milestones": [{"text": "FDA-cleared navigation.", "source_url": "https://x", "source": "comp_site_extract"}],
                    "kol_signals": [],
                    "reimbursement_notes": [{"text": "Reimbursement page.", "source_url": "https://y", "source": "comp_site_extract"}],
                },
                warnings=[],
                fetched=True,
            )
        }
    }
    rebuild_by_case_index(bundle)
    rollup = bundle["by_case_id"]["case_a"]["rollup"]
    assert "ClearPoint Neuro" in rollup["clinical_path"]
    assert "Reimbursement" in rollup["reimbursement_path"]


def test_html_to_text_strips_tags() -> None:
    text = html_to_text("<p>Hello <strong>world</strong></p>")
    assert "Hello world" in text
