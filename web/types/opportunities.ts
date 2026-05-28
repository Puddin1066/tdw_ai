export type FinancingReadinessState =
  | "financeable_now"
  | "financeable_post_inflection"
  | "not_financeable_yet";

export interface OpportunityIndexRow {
  case_id: string;
  display_name: string;
  llm_inferred_label: string;
  opportunity_type: string;
  indication: string;
  target: string;
  company: string;
  development_stage: string;
  geography: string;
  capital_gap_usd: number;
  budget_ceiling_usd: number;
  target_timeline_weeks: number;
  slater_invested: boolean;
  ri_institution?: string;
  patent_count: number;
  primary_lens_id?: string | null;
  financing_readiness_state: FinancingReadinessState | string;
  financing_readiness_score_0_100: number;
  clinical_inflection_score_0_100: number;
  staffing_feasibility_score_0_100: number;
  capital_path_score_0_100: number;
  capital_gap_remaining_usd: number;
  private_match_needed_usd: number;
  physician_candidate_count: number;
  staffing_gaps: string[];
  required_roles: string[];
  required_specialties: string[];
  best_template_id?: string | null;
  estimated_cost_usd: number;
  estimated_duration_weeks: number;
  financing_milestone: string;
  mocked: boolean;
  confidence_0_1: number;
  is_ri_opportunity: boolean;
  is_benchmark: boolean;
}

export interface OpportunityIpAsset {
  asset_id?: string | null;
  title?: string | null;
  lens_id?: string | null;
  url?: string | null;
  owners?: string | null;
  legal_status?: string | null;
  publication_date?: string | null;
}

export interface OpportunityProfile {
  case_id: string;
  display_name: string;
  llm_inferred_label: string;
  ri_notes?: string;
  ri_physician_lead?: string;
  conflict_tags: string[];
  ri_institution?: string;
  ri_ip_source?: string;
  ip_assets: OpportunityIpAsset[];
}

export interface PhysicianOpportunityEdge {
  physician_id: string;
  name?: string | null;
  specialty?: string | null;
  institution?: string | null;
  opportunities: Array<{
    case_id: string;
    display_name: string;
    match_score_0_100: number;
    roles_matched: string[];
  }>;
}

export interface TrialTemplateUsage {
  template_id: string;
  study_type: string;
  opportunity_count: number;
  case_ids: string[];
}

export interface ProgramCapitalSource {
  source_id?: string;
  source_name?: string;
  source_type?: string;
  check_min_usd: number;
  check_max_usd: number;
  decision_cycle_weeks: number;
  ri_focus: boolean;
}

export interface ProgramGovernanceRule {
  rule_id?: string;
  category?: string;
  rule_text?: string;
}

export interface ProgramData {
  title: string;
  subtitle: string;
  capital_sources: ProgramCapitalSource[];
  governance_rules: ProgramGovernanceRule[];
  stats: {
    opportunity_count: number;
    financeable_now_count: number;
    total_capital_gap_usd: number;
  };
}
