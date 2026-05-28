/** Monolithic case enrichment row (mirrors data/ri/ri_cases_enriched.csv). */

export type ReviewStatus = "pending" | "approved";

export interface RiCasesEnrichedFile {
  schema_version: number;
  fieldnames: string[];
  generated_at: string;
  source_csv: string;
  row_count: number;
  rows: RiCaseRow[];
}

export type RiCaseRow = Record<string, string> & {
  case_id: string;
  catalog_tier: string;
  catalog_include: string;
  review_status: ReviewStatus | string;
  title_clean: string;
};

export interface ParallelListItem {
  index: number;
  lines: string[];
}

export interface PublicationEntry {
  title: string;
  leadAuthor: string;
  riAffiliation: string;
  url: string;
  pmid: string;
  note?: string;
  isSuggestion?: boolean;
}

export interface ComparableEntry {
  rank: 1 | 2 | 3;
  name: string;
  type: string;
  url: string;
  valueAnchorUsd: string;
  valueAnchorType: string;
  valueSourceUrl: string;
  totalRaisedUsd: string;
  lastRoundUsd: string;
  financingLadder: string;
  developmentPath: string;
  validationStatus: string;
  suggestValueSourceUrl?: string;
  suggestFinancingLadder?: string;
  suggestNotes?: string;
}

export interface PhysicianSupporter {
  npi: string;
  name: string;
  specialty: string;
  institution: string;
  role: string;
  profileUrl?: string;
}

export interface TrialEntry {
  nctId: string;
  title: string;
  piNames: string;
  url: string;
  phase: string;
}
