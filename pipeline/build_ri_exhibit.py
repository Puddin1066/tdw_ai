"""Build structured exhibit artifacts for RI opportunity UI (schema v2)."""

from __future__ import annotations

from typing import Any

MCQ_LABELS = {
    "ip": "Technology & IP",
    "physicians": "Physician expertise",
    "clinical": "Clinical path",
    "physician_50_slater_ssbci_50": "50% physician syndicate / 50% Slater SSBCI",
    "mixed_slater_physician_hospital_bd": "Slater · physicians · hospital BD",
}

TYPE_LABELS = {
    "medical_device": "Medical device",
    "diagnostic": "Diagnostic",
    "therapeutic": "Therapeutic",
    "digital_therapeutic": "Digital health",
    "pharma_manufacturing": "Pharma / manufacturing",
    "software": "Software",
}


def _num(value: str | None) -> int:
    try:
        return int(float((value or "").strip()))
    except ValueError:
        return 0


def _pipe_list(value: str | None) -> list[str]:
    return [x.strip() for x in (value or "").replace(",", "|").split("|") if x.strip()]


def _order_ip_assets(row: dict[str, str], ip_assets: list[dict[str, str]]) -> list[dict[str, str]]:
    """Put catalog primary_lens_id first so exhibit primary_patent matches enrichment."""
    primary = (row.get("primary_lens_id") or "").strip()
    if not primary:
        return ip_assets
    prim = [a for a in ip_assets if a.get("lens_id") == primary]
    rest = [a for a in ip_assets if a.get("lens_id") != primary]
    return prim + rest


def _format_anchor_short(usd: int, anchor_type: str) -> str:
    if usd >= 1_000_000_000:
        amt = f"${usd / 1_000_000_000:.1f}B"
    elif usd >= 1_000_000:
        amt = f"${usd / 1_000_000:.1f}M"
    elif usd >= 1_000:
        amt = f"${usd / 1_000:.0f}K"
    else:
        amt = f"${usd:,}"
    kind = (anchor_type or "value").replace("_", " ")
    return f"{amt} ({kind})"


def _enrich_precedent(
    p: dict[str, Any],
    dossier_entry: dict[str, Any] | None = None,
) -> dict[str, Any]:
    from pipeline.comp_site_dossier import merge_dossier_into_precedent

    anchor = _num(str(p.get("value_anchor_usd", "")))
    status = (p.get("validation_status") or "suggested").lower()
    headline = p.get("name", "")
    if anchor:
        headline = f"{headline} — {_format_anchor_short(anchor, p.get('value_anchor_type', ''))}"
    base = {
        **p,
        "display_headline": headline,
        "has_value_anchor": anchor > 0,
        "is_verified": status == "verified",
    }
    return merge_dossier_into_precedent(base, dossier_entry)


def _pick_lead_precedent(precedents: list[dict[str, Any]]) -> dict[str, Any] | None:
    for status in ("verified", "estimated", "suggested"):
        for p in precedents:
            if (p.get("validation_status") or "").lower() == status and _num(
                str(p.get("value_anchor_usd", ""))
            ):
                return p
    return precedents[0] if precedents else None


def _value_band_label(row: dict[str, str]) -> str:
    lo, hi = _num(row.get("value_band_min_usd")), _num(row.get("value_band_max_usd"))
    if not lo and not hi:
        return ""
    if lo == hi:
        return _format_anchor_short(lo, "comparable")
    return f"{_format_anchor_short(lo, 'comparable')} – {_format_anchor_short(hi, 'comparable')}"


def _build_evidence_section(
    row: dict[str, str],
    evidence: dict[str, Any] | None,
) -> dict[str, Any]:
    if evidence:
        return {
            "status": evidence.get("status", "pending"),
            "search_terms": evidence.get("search_terms") or [],
            "publications": evidence.get("publications") or [],
            "trials": evidence.get("trials") or [],
            "narrative": evidence.get("literature_narrative")
            or row.get("biomcp_literature_narrative", ""),
            "publication_count": evidence.get("publication_count", 0),
            "trial_count": evidence.get("trial_count", 0),
            "fetched_at": evidence.get("fetched_at", ""),
            "warnings": evidence.get("warnings") or [],
            "related_case_ids": evidence.get("related_case_ids") or [],
            "inventor_surnames": evidence.get("inventor_surnames") or [],
            "primary_lens_id": evidence.get("primary_lens_id", ""),
        }
    return {
        "status": row.get("biomcp_evidence_status", "pending"),
        "search_terms": _pipe_list(row.get("biomcp_search_terms")),
        "publications": [],
        "trials": [],
        "narrative": row.get("biomcp_literature_narrative", ""),
        "publication_count": _num(row.get("biomcp_publication_count")),
        "trial_count": _num(row.get("biomcp_trial_count")),
        "fetched_at": row.get("biomcp_fetched_at", ""),
        "warnings": [],
    }


def build_exhibit(
    row: dict[str, str],
    precedents: list[dict[str, Any]],
    ip_assets: list[dict[str, str]],
    physicians: list[dict[str, str]],
    evidence: dict[str, Any] | None = None,
    comp_dossiers: dict[str, dict[str, Any]] | None = None,
    comp_rollup: dict[str, str] | None = None,
) -> dict[str, Any]:
    from_canonical = (row.get("enrichment_status") or "") == "canonical_csv" or (
        row.get("opportunity_enrichment_source") == "ri_cases_enriched.csv"
    )
    gap = _num(row.get("capital_gap_usd"))
    if from_canonical:
        gap = _num(row.get("total_package_usd")) or gap
    dossiers = comp_dossiers or {}
    enriched_precedents = [
        _enrich_precedent(p, dossiers.get(str(p.get("name", ""))))
        for p in precedents
    ]
    lead_prec = _pick_lead_precedent(enriched_precedents)
    lead_phys = next((p for p in physicians if p.get("is_lead") == "true"), None)
    supporters = [p for p in physicians if p.get("is_lead") != "true"]
    opp_type = row.get("opportunity_type", "medical_device")
    mcq_lead = row.get("mcq_lead_pillar", "ip")

    lead_comparable = None
    if lead_prec:
        lead_comparable = {
            "name": lead_prec.get("name", ""),
            "url": lead_prec.get("url", ""),
            "value_anchor_usd": lead_prec.get("value_anchor_usd", ""),
            "value_anchor_type": lead_prec.get("value_anchor_type", ""),
            "value_source_url": lead_prec.get("value_source_url", ""),
            "validation_status": lead_prec.get("validation_status", ""),
            "inferred_development": lead_prec.get("inferred_development", ""),
            "inferred_financing": lead_prec.get("inferred_financing", ""),
        }

    pillar_order = ["technology", "evidence", "market", "syndicate", "clinical"]
    if mcq_lead == "physicians":
        pillar_order = ["syndicate", "technology", "evidence", "market", "clinical"]
    elif mcq_lead == "clinical":
        pillar_order = ["clinical", "technology", "evidence", "market", "syndicate"]

    thesis = (row.get("investment_thesis") or row.get("synthesis_memo") or "").strip()
    ordered_ip = _order_ip_assets(row, ip_assets)

    return {
        "headline": {
            "title": row.get("title_clean", ""),
            "tagline": row.get("display_name", ""),
            "thesis": thesis,
            "indication": row.get("indication", ""),
            "opportunity_type": opp_type,
            "opportunity_type_label": TYPE_LABELS.get(opp_type, opp_type.replace("_", " ")),
            "development_stage": row.get("development_stage", ""),
            "catalog_tier": row.get("catalog_tier", ""),
            "geography": "Rhode Island",
            "company": row.get("company", ""),
            "data_caveat": row.get("data_caveat", ""),
        },
        "snapshot": {
            "capital_gap_usd": gap,
            "physician_share_usd": gap // 2 if gap else 0,
            "slater_share_usd": gap // 2 if gap else 0,
            "budget_ceiling_usd": _num(row.get("budget_ceiling_usd")),
            "value_band": {
                "min_usd": 0 if from_canonical else _num(row.get("value_band_min_usd")),
                "max_usd": 0 if from_canonical else _num(row.get("value_band_max_usd")),
                "median_usd": 0 if from_canonical else _num(row.get("value_band_median_usd")),
                "label": "" if from_canonical else _value_band_label(row),
                "verification_status": row.get("value_verification_status", ""),
                "verified_anchor_count": _num(row.get("value_anchor_verified_count")),
            },
            "lead_comparable": lead_comparable,
            "next_milestone": row.get("inferred_next_milestone", ""),
            "enrichment_source": row.get("opportunity_enrichment_source", ""),
            "comparator_grounded": row.get("opportunity_enrichment_source") == "comparator_inferred",
        },
        "technology": {
            "patents": ordered_ip,
            "primary_patent": ordered_ip[0] if ordered_ip else None,
            "patent_count": len(ordered_ip),
            "summary": (
                f"{len(ordered_ip)} Rhode Island-linked patent"
                f"{'' if len(ordered_ip) == 1 else 's'} anchor the core technology asset."
                if ordered_ip
                else "Patent linkage pending — verify Lens IDs in enrichment CSV."
            ),
        },
        "evidence": _build_evidence_section(row, evidence),
        "market": {
            "precedents": enriched_precedents,
            "precedent_count": len(enriched_precedents),
            "development_path": row.get("inferred_development_path", ""),
            "financing_path": row.get("inferred_financing_path", ""),
            "comparable_narrative": row.get("comparable_market_narrative", ""),
            "comp_rollup": comp_rollup
            or {
                "clinical_path": "",
                "reimbursement_path": "",
                "kol_pattern": "",
            },
            "highlights": [
                p["display_headline"]
                for p in enriched_precedents
                if p.get("has_value_anchor") or p.get("is_verified")
            ][:3]
            or [p.get("display_headline", p.get("name", "")) for p in enriched_precedents[:3]],
        },
        "syndicate": {
            "lead": lead_phys,
            "supporters": supporters,
            "roster": physicians,
            "roster_size": len(physicians),
            "required_specialties": _pipe_list(row.get("required_specialties")),
            "summary": (
                f"{len(physicians)} Rhode Island clinicians identified "
                f"({1 if lead_phys else 0} lead, {len(supporters)} supporters)."
                if physicians
                else "Physician syndicate roster to be confirmed."
            ),
        },
        "clinical": {
            "study_type": row.get("clinical_study_type", ""),
            "primary_endpoint": row.get("clinical_primary_endpoint", ""),
            "duration_weeks": _num(row.get("clinical_duration_weeks")),
            "timeline_weeks": _num(row.get("target_timeline_weeks")),
            "cost_usd": _num(row.get("clinical_cost_usd")),
            "path_notes": row.get("clinical_path_notes", ""),
            "milestone": row.get("inferred_next_milestone", "") or row.get("clinical_path_notes", ""),
            "trial_template_id": row.get("trial_template_id", ""),
            "has_plan": bool((row.get("clinical_study_type") or "").strip()),
        },
        "financing": {
            "structure": row.get("mcq_financing_structure", ""),
            "structure_label": MCQ_LABELS.get(
                row.get("mcq_financing_structure", ""), row.get("mcq_financing_structure", "")
            ),
            "audience": row.get("mcq_audience", ""),
            "audience_label": MCQ_LABELS.get(row.get("mcq_audience", ""), row.get("mcq_audience", "")),
            "development_ask_label": row.get("clinical_study_type", "") or "Pilot / validation",
            "lead_pillar": mcq_lead,
            "lead_pillar_label": MCQ_LABELS.get(mcq_lead, mcq_lead),
        },
        "presentation": {
            "pillar_order": pillar_order,
            "sections": [
                {"id": pid, "title": _section_title(pid)} for pid in pillar_order
            ],
        },
        "meta": {
            "case_id": row.get("case_id", ""),
            "program_family": row.get("program_family", ""),
            "enrichment_status": row.get("enrichment_status", ""),
            "clinical_tags": _pipe_list(row.get("clinical_tags")),
            "ri_notes": row.get("ri_notes", ""),
            "mocked": False,
            "source": row.get("opportunity_enrichment_source")
            or "ri_opportunities_catalog_enrichment.csv",
            "review_status": row.get("review_status", ""),
        },
    }


def _section_title(pillar_id: str) -> str:
    titles = {
        "technology": "Technology & IP",
        "evidence": "Scientific & clinical evidence",
        "market": "Market comparables",
        "syndicate": "Physician syndicate",
        "clinical": "Clinical development",
    }
    return titles.get(pillar_id, pillar_id)


def build_catalog_card(case_id: str, exhibit: dict[str, Any]) -> dict[str, Any]:
    h = exhibit["headline"]
    s = exhibit["snapshot"]
    t = exhibit["technology"]
    syn = exhibit["syndicate"]
    vb = s["value_band"]
    return {
        "case_id": case_id,
        "catalog_tier": h.get("catalog_tier", ""),
        "title": h.get("title", ""),
        "opportunity_type_label": h.get("opportunity_type_label", ""),
        "development_stage": h.get("development_stage", ""),
        "thesis_teaser": (h.get("thesis") or "")[:220],
        "value_band_label": vb.get("label", ""),
        "capital_gap_usd": s.get("capital_gap_usd", 0),
        "patent_count": t.get("patent_count", 0),
        "physician_count": syn.get("roster_size", 0),
        "verified_comp_count": vb.get("verified_anchor_count", 0),
        "has_data_caveat": bool(h.get("data_caveat")),
        "comparator_grounded": s.get("comparator_grounded", False),
        "lead_comparable_name": (s.get("lead_comparable") or {}).get("name", ""),
        "publication_count": exhibit.get("evidence", {}).get("publication_count", 0),
        "evidence_status": exhibit.get("evidence", {}).get("status", "pending"),
        "review_status": exhibit.get("meta", {}).get("review_status", ""),
    }
