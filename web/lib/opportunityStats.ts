import type { OpportunityIndexRow } from "@/types/opportunities";

export function portfolioStats(rows: OpportunityIndexRow[]) {
  return {
    total: rows.length,
    financeableNow: rows.filter((r) => r.financing_readiness_state === "financeable_now").length,
    totalCapitalGap: rows.reduce((sum, r) => sum + r.capital_gap_usd, 0),
    avgReadiness:
      rows.length > 0
        ? rows.reduce((sum, r) => sum + r.financing_readiness_score_0_100, 0) / rows.length
        : 0,
    fullPhysicianRoster: rows.filter((r) => r.physician_candidate_count >= 10).length,
  };
}
