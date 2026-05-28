"""Paths for Tier A canonical static sources."""

from __future__ import annotations

from pathlib import Path

from pipeline.types import repo_root

TIER_A_ROOT = repo_root() / "data" / "ri" / "tier_a"
REGISTRY_CSV = TIER_A_ROOT / "registry.csv"
COMPARABLES_CSV = TIER_A_ROOT / "comparables.csv"
EVIDENCE_OVERRIDES_CSV = TIER_A_ROOT / "evidence_overrides.csv"
FINANCE_POLICY_YAML = TIER_A_ROOT / "finance_policy.yaml"
README_MD = TIER_A_ROOT / "README.md"

CATALOG_PATH = repo_root() / "data" / "ri" / "ri_opportunities_catalog_enrichment.csv"
PRECEDENTS_PATH = repo_root() / "data" / "ri" / "ri_program_precedents.csv"
OPPORTUNITIES_PATH = repo_root() / "data" / "ri" / "ri_opportunities.csv"
IP_ASSETS_PATH = repo_root() / "data" / "ri" / "ri_ip_assets.csv"
EVIDENCE_PATH = repo_root() / "data" / "ri" / "ri_opportunity_evidence.json"

REGISTRY_FIELDS = [
    "case_id",
    "title_clean",
    "program_family",
    "company",
    "opportunity_type",
    "indication",
    "primary_lens_id",
    "physician_lead_name",
    "physician_lead_npi",
    "status",
    "promotion_source",
    "capital_gap_usd",
    "budget_ceiling_usd",
    "clinical_duration_weeks",
    "development_stage",
    "data_caveat",
    "ri_notes",
    "reviewed_by",
    "reviewed_at",
]

COMPARABLE_FIELDS = [
    "case_id",
    "precedent_rank",
    "precedent_type",
    "precedent_name",
    "precedent_stage",
    "precedent_notes",
    "precedent_url",
    "inferred_development",
    "inferred_financing",
    "inferred_team",
    "total_raised_usd_est",
    "last_round_usd_est",
    "value_anchor_usd",
    "value_anchor_type",
    "value_source_url",
    "financing_strategy",
    "validation_status",
    "confidence",
    "source",
]

EVIDENCE_OVERRIDE_FIELDS = [
    "case_id",
    "evidence_depth_score_0_100",
    "evidence_grade",
    "review_status",
    "reviewer_note",
    "canonical_evidence_status",
    "min_publication_count",
]
