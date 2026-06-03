import { readFileSync } from "fs";
import path from "path";
import type {
  CatalogCard,
  CombinedOpportunity,
  CombinedOpportunityBundle,
  OpportunityExhibit,
} from "@/types/combined";

const BUNDLE_PATH = path.join(
  process.cwd(),
  "public",
  "data",
  "ri",
  "opportunities_combined.json",
);

let cached: CombinedOpportunityBundle | null = null;

function loadBundle(): CombinedOpportunityBundle {
  if (process.env.NODE_ENV === "production" && cached) {
    return cached;
  }
  const raw = readFileSync(BUNDLE_PATH, "utf-8");
  cached = JSON.parse(raw) as CombinedOpportunityBundle;
  return cached;
}

export function loadCatalogCards(): CatalogCard[] {
  const bundle = loadBundle();
  if (bundle.catalog_cards?.length) {
    return bundle.catalog_cards;
  }
  return bundle.opportunities.map((o) => ({
    case_id: o.case_id,
    catalog_tier: o.exhibit.headline.catalog_tier,
    ri_institution: o.exhibit.headline.ri_institution,
    title: o.exhibit.headline.title,
    opportunity_type_label: o.exhibit.headline.opportunity_type_label,
    development_stage: o.exhibit.headline.development_stage,
    thesis_teaser: o.exhibit.headline.thesis.slice(0, 220),
    value_band_label: o.exhibit.snapshot.value_band.label,
    capital_gap_usd: o.exhibit.snapshot.capital_gap_usd,
    patent_count: o.exhibit.technology.patent_count,
    physician_count: o.exhibit.syndicate.roster_size,
    verified_comp_count: o.exhibit.snapshot.value_band.verified_anchor_count,
    has_data_caveat: Boolean(o.exhibit.headline.data_caveat),
    comparator_grounded: o.exhibit.snapshot.comparator_grounded,
    lead_comparable_name: o.exhibit.snapshot.lead_comparable?.name ?? "",
    publication_count: o.exhibit.evidence?.publication_count ?? 0,
    evidence_status: o.exhibit.evidence?.status ?? "pending",
    review_status: o.exhibit.meta.review_status,
  }));
}

export function loadCombinedOpportunities(): CombinedOpportunity[] {
  return loadBundle().opportunities;
}

export function getCombinedOpportunity(caseId: string): CombinedOpportunity | undefined {
  return loadCombinedOpportunities().find((row) => row.case_id === caseId);
}

export function getExhibit(caseId: string): OpportunityExhibit | undefined {
  return getCombinedOpportunity(caseId)?.exhibit;
}

export function listCombinedCaseIds(): string[] {
  return loadCombinedOpportunities().map((row) => row.case_id);
}
