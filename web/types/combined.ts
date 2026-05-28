/** UI types for data/ri/ri_opportunities_combined.json (schema v2) */

export interface CombinedIpAsset {
  lens_id: string;
  display_key: string;
  title: string;
  owners: string;
  url: string;
}

export interface CombinedPrecedent {
  rank: number;
  type: string;
  name: string;
  stage: string;
  notes: string;
  url: string;
  inferred_development: string;
  inferred_financing: string;
  inferred_team: string;
  total_raised_usd_est: string;
  last_round_usd_est: string;
  value_anchor_usd: string;
  value_anchor_type: string;
  value_source_url: string;
  financing_strategy: string;
  validation_status: string;
  confidence: string;
  source: string;
  display_headline?: string;
  has_value_anchor?: boolean;
  is_verified?: boolean;
  comparable_fit?: "direct" | "analog" | "strategic" | string;
  site_dossier?: CompSiteDossierPayload;
}

export interface CompSiteCitedText {
  text: string;
  source_url: string;
  source: string;
}

export interface CompSitePublicationLink {
  title: string;
  url: string;
  source_page: string;
  source: string;
}

export interface CompSiteDossierPayload {
  dossier_status: "pending" | "partial" | "reviewed" | string;
  human_reviewed: boolean;
  fetched_at?: string;
  comparable_fit: "direct" | "analog" | "strategic" | string;
  ri_parallel: string;
  site_map: Record<string, string>;
  science_summary: string;
  key_publications: CompSitePublicationLink[];
  clinical_milestones: CompSiteCitedText[];
  kol_signals: CompSiteCitedText[];
  reimbursement_notes: CompSiteCitedText[];
  warnings: string[];
}

export interface CompSiteRollup {
  clinical_path: string;
  reimbursement_path: string;
  kol_pattern: string;
}

export interface CombinedPhysician {
  physician_id: string;
  name: string;
  specialty: string;
  institution: string;
  roles_matched: string;
  is_lead?: string;
}

export interface ExhibitHeadline {
  title: string;
  tagline: string;
  thesis: string;
  indication: string;
  opportunity_type: string;
  opportunity_type_label: string;
  development_stage: string;
  catalog_tier: string;
  geography: string;
  company: string;
  data_caveat: string;
}

export interface ExhibitValueBand {
  min_usd: number;
  max_usd: number;
  median_usd: number;
  label: string;
  verification_status: string;
  verified_anchor_count: number;
}

export interface ExhibitLeadComparable {
  name: string;
  url: string;
  value_anchor_usd: string;
  value_anchor_type: string;
  value_source_url: string;
  validation_status: string;
  inferred_development: string;
  inferred_financing: string;
}

export interface ExhibitSnapshot {
  capital_gap_usd: number;
  physician_share_usd: number;
  slater_share_usd: number;
  budget_ceiling_usd: number;
  value_band: ExhibitValueBand;
  lead_comparable: ExhibitLeadComparable | null;
  next_milestone: string;
  enrichment_source: string;
  comparator_grounded: boolean;
}

export interface ExhibitTechnology {
  patents: CombinedIpAsset[];
  primary_patent: CombinedIpAsset | null;
  patent_count: number;
  summary: string;
}

export interface ExhibitMarket {
  precedents: CombinedPrecedent[];
  precedent_count: number;
  development_path: string;
  financing_path: string;
  comparable_narrative: string;
  comp_rollup?: CompSiteRollup;
  highlights: string[];
}

export interface ExhibitSyndicate {
  lead: CombinedPhysician | null;
  supporters: CombinedPhysician[];
  roster: CombinedPhysician[];
  roster_size: number;
  required_specialties: string[];
  summary: string;
}

export interface ExhibitPatentLink {
  primary_lens_id?: string;
  primary_display_key?: string;
  matched_inventor_surnames?: string[];
  science_overlap_score?: number;
  link_basis?: string[];
}

export interface ExhibitPublication {
  pmid?: string | null;
  doi?: string | null;
  title: string;
  url: string;
  journal: string;
  publication_date: string;
  authors: string[];
  abstract_snippet: string;
  search_term?: string;
  source?: string;
  patent_link?: ExhibitPatentLink;
}

export interface ExhibitTrial {
  nct_id: string;
  title: string;
  status: string;
  phase: string;
  url: string;
  search_term?: string;
  source?: string;
}

export interface ExhibitEvidence {
  status: string;
  search_terms: string[];
  publications: ExhibitPublication[];
  trials: ExhibitTrial[];
  narrative: string;
  publication_count: number;
  trial_count: number;
  fetched_at: string;
  warnings: string[];
  related_case_ids?: string[];
  inventor_surnames?: string[];
  primary_lens_id?: string;
}

export interface ExhibitClinical {
  study_type: string;
  primary_endpoint: string;
  duration_weeks: number;
  timeline_weeks: number;
  cost_usd: number;
  path_notes: string;
  milestone: string;
  trial_template_id: string;
  has_plan: boolean;
}

export interface ExhibitFinancing {
  structure: string;
  structure_label: string;
  audience: string;
  audience_label: string;
  development_ask_label: string;
  lead_pillar: string;
  lead_pillar_label: string;
}

export interface ExhibitPresentation {
  pillar_order: string[];
  sections: { id: string; title: string }[];
}

export interface ExhibitMeta {
  case_id: string;
  program_family: string;
  enrichment_status: string;
  clinical_tags: string[];
  ri_notes: string;
  mocked: boolean;
  source: string;
}

export interface OpportunityExhibit {
  headline: ExhibitHeadline;
  snapshot: ExhibitSnapshot;
  technology: ExhibitTechnology;
  evidence: ExhibitEvidence;
  market: ExhibitMarket;
  syndicate: ExhibitSyndicate;
  clinical: ExhibitClinical;
  financing: ExhibitFinancing;
  presentation: ExhibitPresentation;
  meta: ExhibitMeta;
}

export interface CatalogCard {
  case_id: string;
  catalog_tier: string;
  title: string;
  opportunity_type_label: string;
  development_stage: string;
  thesis_teaser: string;
  value_band_label: string;
  capital_gap_usd: number;
  patent_count: number;
  physician_count: number;
  verified_comp_count: number;
  has_data_caveat: boolean;
  comparator_grounded: boolean;
  lead_comparable_name: string;
  publication_count: number;
  evidence_status: string;
}

export interface CombinedOpportunity {
  case_id: string;
  exhibit: OpportunityExhibit;
}

export interface CombinedOpportunityBundle {
  schema_version: number;
  generated_from: string[];
  opportunity_count: number;
  catalog_cards: CatalogCard[];
  opportunities: CombinedOpportunity[];
}
