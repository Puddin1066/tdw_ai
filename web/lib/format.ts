import type { FinancingReadinessState } from "@/types/opportunities";

export function formatUsd(value: number): string {
  if (!Number.isFinite(value) || value === 0) return "$0";
  if (value >= 1_000_000) {
    return `$${(value / 1_000_000).toFixed(1)}M`;
  }
  if (value >= 1_000) {
    return `$${Math.round(value / 1_000)}K`;
  }
  return `$${value.toLocaleString()}`;
}

export function formatReadinessState(state: string): string {
  return state.replace(/_/g, " ");
}

export function readinessBadgeVariant(
  state: string,
): "success" | "warning" | "danger" | "secondary" {
  switch (state as FinancingReadinessState) {
    case "financeable_now":
      return "success";
    case "financeable_post_inflection":
      return "warning";
    case "not_financeable_yet":
      return "danger";
    default:
      return "secondary";
  }
}

export function opportunityTypeLabel(type: string): string {
  return type.replace(/_/g, " ");
}

/** Strip auto-generated patent label suffixes for human-readable titles. */
export function formatValueAnchorType(type: string): string {
  if (!type) return "Value";
  const labels: Record<string, string> = {
    total_raised: "Total VC raised",
    last_round: "Latest VC round",
    seed_round: "Seed round",
    series_a: "Series A",
    series_b: "Series B",
    series_c: "Series C",
    grant: "Grant / non-dilutive",
    market_cap: "Market cap (public)",
    acquisition: "Acquisition",
    post_money_valuation: "Post-money valuation",
  };
  return labels[type] || type.replace(/_/g, " ");
}

export function formatValueBand(minUsd: string | number, maxUsd: string | number): string {
  const min = Number(minUsd) || 0;
  const max = Number(maxUsd) || 0;
  if (!min && !max) return "";
  if (min === max) return formatUsd(min);
  return `${formatUsd(min)} – ${formatUsd(max)}`;
}

export function validationBadgeVariant(
  status: string,
): "success" | "warning" | "secondary" {
  switch ((status || "").toLowerCase()) {
    case "verified":
      return "success";
    case "estimated":
      return "warning";
    default:
      return "secondary";
  }
}

export function cleanOpportunityTitle(label: string): string {
  return label
    .replace(
      /\s+(Technology Platform|Therapeutic|Diagnostic|Medical Device|Digital Therapeutic)\s+Opportunity$/i,
      "",
    )
    .trim();
}
