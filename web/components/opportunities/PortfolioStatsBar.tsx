import { formatUsd } from "@/lib/format";

interface PortfolioStatsBarProps {
  total: number;
  financeableNow: number;
  totalCapitalGap: number;
  avgReadiness: number;
  fullPhysicianRoster: number;
}

export function PortfolioStatsBar({
  total,
  financeableNow,
  totalCapitalGap,
  avgReadiness,
  fullPhysicianRoster,
}: PortfolioStatsBarProps) {
  const items = [
    { label: "Opportunities", value: String(total) },
    { label: "Financeable now", value: String(financeableNow) },
    { label: "Aggregate capital gap", value: formatUsd(totalCapitalGap) },
    { label: "Avg readiness", value: `${avgReadiness.toFixed(0)}` },
    { label: "Full physician roster (10)", value: String(fullPhysicianRoster) },
  ];

  return (
    <div className="grid gap-3 sm:grid-cols-2 lg:grid-cols-5">
      {items.map((item) => (
        <div
          key={item.label}
          className="rounded-md border border-border/60 bg-card/50 px-3 py-2 text-sm"
        >
          <p className="text-xs text-muted-foreground">{item.label}</p>
          <p className="font-semibold text-foreground">{item.value}</p>
        </div>
      ))}
    </div>
  );
}
