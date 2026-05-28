"""Column schema for data/ri/ri_cases_enriched.csv (monolithic case enrichment)."""

from __future__ import annotations

# Policy defaults (locked decisions)
MAX_TOTAL_PACKAGE_USD = 400_000
MAX_SLATER_SHARE_USD = 200_000
DEFAULT_TOTAL_PACKAGE_USD = 400_000

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
    # Comparable 1
    "comp1_name",
    "comp1_type",
    "comp1_url",
    "comp1_value_anchor_usd",
    "comp1_value_anchor_type",
    "comp1_value_source_url",
    "comp1_total_raised_usd",
    "comp1_last_round_usd",
    "comp1_financing_ladder",
    "comp1_development_path",
    "comp1_validation_status",
    # Comparable 2
    "comp2_name",
    "comp2_type",
    "comp2_url",
    "comp2_value_anchor_usd",
    "comp2_value_anchor_type",
    "comp2_value_source_url",
    "comp2_total_raised_usd",
    "comp2_last_round_usd",
    "comp2_financing_ladder",
    "comp2_development_path",
    "comp2_validation_status",
    # Comparable 3
    "comp3_name",
    "comp3_type",
    "comp3_url",
    "comp3_value_anchor_usd",
    "comp3_value_anchor_type",
    "comp3_value_source_url",
    "comp3_total_raised_usd",
    "comp3_last_round_usd",
    "comp3_financing_ladder",
    "comp3_development_path",
    "comp3_validation_status",
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
    # R&D plan
    "rd_plan_summary",
    "rd_milestones",
    "rd_milestone_types",
    # Clinical template (from catalog)
    "clinical_study_type",
    "clinical_primary_endpoint",
    "clinical_duration_weeks",
    "clinical_cost_usd",
    "clinical_path_notes",
    "target_timeline_weeks",
    # Build / framing
    "investment_thesis",
    "mcq_lead_pillar",
    "mcq_financing_structure",
    "mcq_audience",
    "required_specialties",
    "clinical_tags",
    "program_family",
    "enrichment_status",
]

COMP_PREFIXES = ("comp1_", "comp2_", "comp3_")
