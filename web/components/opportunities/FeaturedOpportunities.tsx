import Link from "next/link";
import type { CatalogCard } from "@/types/combined";
import { Badge } from "@/components/ui/badge";
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card";
import { formatUsd } from "@/lib/format";

interface FeaturedOpportunitiesProps {
  cards: CatalogCard[];
}

export function FeaturedOpportunities({ cards }: FeaturedOpportunitiesProps) {
  if (cards.length === 0) return null;

  return (
    <section className="space-y-4" aria-labelledby="featured-heading">
      <div className="space-y-1">
        <h2 id="featured-heading" className="text-xl font-semibold tracking-tight">
          Example packages
        </h2>
        <p className="text-sm text-muted-foreground">
          Tier A opportunities with cited comparables and physician rosters — open a memo to trace
          every citation.
        </p>
      </div>
      <div className="grid gap-4 md:grid-cols-3">
        {cards.map((card) => (
          <Link key={card.case_id} href={`/opportunities/${card.case_id}`} className="group block">
            <Card className="h-full border-cockpit-teal/20 bg-card/80 transition-colors group-hover:border-cockpit-teal/50">
              <CardHeader className="space-y-2 pb-2">
                <div className="flex flex-wrap items-center gap-2">
                  <p className="text-[10px] uppercase tracking-wider text-cockpit-teal">
                    {card.opportunity_type_label}
                  </p>
                  {card.comparator_grounded ? (
                    <Badge variant="secondary" className="text-[10px] font-normal">
                      Comp-grounded
                    </Badge>
                  ) : null}
                </div>
                {card.ri_institution ? (
                  <p className="text-xs text-muted-foreground">{card.ri_institution}</p>
                ) : null}
                <CardTitle className="text-base leading-snug group-hover:text-cockpit-teal">
                  {card.title}
                </CardTitle>
                <CardDescription className="line-clamp-2 text-sm">
                  {card.lead_comparable_name
                    ? `Lead comp: ${card.lead_comparable_name}`
                    : card.thesis_teaser}
                </CardDescription>
              </CardHeader>
              <CardContent className="space-y-2 text-sm">
                {card.value_band_label ? (
                  <p className="text-xs text-muted-foreground">{card.value_band_label}</p>
                ) : null}
                <p className="font-medium">
                  {formatUsd(card.capital_gap_usd)}{" "}
                  <span className="font-normal text-muted-foreground">· 50/50 package</span>
                </p>
                <p className="text-xs text-cockpit-teal group-hover:underline">
                  View full memo →
                </p>
              </CardContent>
            </Card>
          </Link>
        ))}
      </div>
    </section>
  );
}
