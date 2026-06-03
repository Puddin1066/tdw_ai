interface StatItem {
  label: string;
  value: string;
}

interface PortfolioStatsBarProps {
  items: StatItem[];
}

export function PortfolioStatsBar({ items }: PortfolioStatsBarProps) {
  return (
    <div
      className={`grid gap-3 sm:grid-cols-2 ${items.length >= 5 ? "lg:grid-cols-5" : "lg:grid-cols-4"}`}
    >
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
