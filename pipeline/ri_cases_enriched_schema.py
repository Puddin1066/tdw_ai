"""Column schema for data/ri/ri_cases_enriched.csv (monolithic case enrichment)."""

from __future__ import annotations

# Policy defaults (locked decisions)
MAX_TOTAL_PACKAGE_USD = 400_000
MAX_SLATER_SHARE_USD = 200_000
DEFAULT_TOTAL_PACKAGE_USD = 400_000

MAX_COMP_SLOTS = 6

# Per-slot comparable columns (wide CSV; Excel-friendly).
COMP_SUFFIXES: tuple[str, ...] = (
    "name",
    "type",
    "role",
    "stage",
    "url",
    "notes",
    "value_anchor_usd",
    "value_anchor_type",
    "value_source_url",
    "total_raised_usd",
    "last_round_usd",
    "financing_ladder",
    "development_path",
    "validation_status",
    "supporting_citations",
)

COMP_PREFIXES: tuple[str, ...] = tuple(f"comp{i}_" for i in range(1, MAX_COMP_SLOTS + 1))


def comp_fieldnames() -> list[str]:
    """All compN_* columns for slots 1..MAX_COMP_SLOTS."""
    return [f"comp{i}_{suffix}" for i in range(1, MAX_COMP_SLOTS + 1) for suffix in COMP_SUFFIXES]


FIELDNAMES: list[str] = [
    # Identity
    "case_id",
    "catalog_tier",
    "catalog_include",
    "review_status",
    "title_clean",
    "display_name",
    "company",
    "indication",
    "opportunity_type",
    "development_stage",
    "ri_institution",
    "data_caveat",
    "ri_notes",
    "last_refreshed_at",
    "reviewer",
    # Web enrichment audit (scripts only)
    "web_search_queries",
    "web_search_notes",
    # Patents
    "primary_lens_id",
    "primary_display_key",
    "primary_patent_title",
    "primary_patent_url",
    "assignee_company",
    "inventors",
    "ip_lens_ids",
    "ip_titles",
    "ip_urls",
    # Publications (approved columns)
    "publication_count",
    "publication_titles",
    "publication_lead_authors",
    "publication_ri_affiliations",
    "publication_urls",
    "publication_pmids",
    "literature_narrative",
    "literature_source_urls",
    # Publication suggestions (scripts only)
    "suggest_publication_titles",
    "suggest_publication_urls",
    "suggest_publication_notes",
    # Physicians
    "physician_lead_npi",
    "physician_lead_name",
    "physician_lead_specialty",
    "physician_lead_institution",
    "physician_lead_profile_url",
    "physician_supporters",
    "physician_supporter_profile_urls",
    # Physician suggestions (NPI match assist; curate promotes to lead/supporters)
    "suggest_physician_lead_npi",
    "suggest_physician_lead_name",
    "suggest_physician_lead_specialty",
    "suggest_physician_lead_institution",
    "suggest_physician_lead_match_score",
    "suggest_physician_supporters",
    "suggest_physician_notes",
    "staffing_feasibility_score",
    *comp_fieldnames(),
    # Comp suggestions
    "suggest_comp1_value_source_url",
    "suggest_comp1_financing_ladder",
    "suggest_comp1_notes",
    # Finance (display truth)
    "financing_stage",
    "total_package_usd",
    "physician_share_usd",
    "slater_share_usd",
    "clinical_allocation_usd",
    "rd_allocation_usd",
    "financing_rationale",
    # Trials
    "trial_count",
    "trial_nct_ids",
    "trial_titles",
    "trial_pi_names",
    "trial_urls",
    "trial_phases",
    # Trial suggestions (low-confidence path analogs; scripts / curate only)
    "suggest_trial_nct_ids",
    "suggest_trial_titles",
    "suggest_trial_urls",
    "suggest_trial_notes",
    # R&D plan
    "rd_plan_summary",
    "rd_milestones",
    "rd_milestone_types",
    "rd_milestone_source_urls",
    "rd_plan_source_url",
    # Clinical template (from catalog)
    "clinical_study_type",
    "clinical_primary_endpoint",
    "clinical_duration_weeks",
    "clinical_cost_usd",
    "clinical_path_notes",
    "target_timeline_weeks",
    # Build / framing
    "comparable_market_narrative",
    "investment_thesis",
    "mcq_lead_pillar",
    "mcq_financing_structure",
    "mcq_audience",
    "required_specialties",
    "clinical_tags",
    "program_family",
    "enrichment_status",
]
