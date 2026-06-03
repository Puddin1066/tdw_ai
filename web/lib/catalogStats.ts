import type { CatalogCard } from "@/types/combined";

export interface CatalogPortfolioStats {
  total: number;
  compGrounded: number;
  packageReady: number;
  withPhysicianRoster: number;
  verifiedComps: number;
}

export function computeCatalogStats(cards: CatalogCard[]): CatalogPortfolioStats {
  return {
    total: cards.length,
    compGrounded: cards.filter((c) => c.comparator_grounded).length,
    packageReady: cards.filter(
      (c) =>
        c.comparator_grounded &&
        c.physician_count > 0 &&
        !c.has_data_caveat &&
        c.capital_gap_usd <= 400_000,
    ).length,
    withPhysicianRoster: cards.filter((c) => c.physician_count >= 5).length,
    verifiedComps: cards.filter((c) => c.verified_comp_count > 0).length,
  };
}

export function selectFeaturedCards(cards: CatalogCard[], limit = 3): CatalogCard[] {
  return [...cards]
    .filter((c) => c.catalog_tier === "A" && c.comparator_grounded && !c.has_data_caveat)
    .sort((a, b) => {
      const score = (c: CatalogCard) =>
        (c.verified_comp_count > 0 ? 4 : 0) +
        (c.review_status?.toLowerCase() === "approved" ? 2 : 0) +
        c.physician_count +
        c.publication_count * 0.1;
      return score(b) - score(a);
    })
    .slice(0, limit);
}
