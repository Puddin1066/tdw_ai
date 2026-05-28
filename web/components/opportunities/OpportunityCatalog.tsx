"use client";

import Link from "next/link";
import { useMemo, useState } from "react";
import type { CatalogCard } from "@/types/combined";
import { Badge } from "@/components/ui/badge";
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card";
import { formatUsd } from "@/lib/format";

interface OpportunityCatalogProps {
  cards: CatalogCard[];
}

export function OpportunityCatalog({ cards }: OpportunityCatalogProps) {
  const [query, setQuery] = useState("");

  const filtered = useMemo(() => {
    const q = query.trim().toLowerCase();
    if (!q) return cards;
    return cards.filter((card) => {
      const hay = `${card.title} ${card.thesis_teaser} ${card.lead_comparable_name} ${card.opportunity_type_label}`.toLowerCase();
      return hay.includes(q);
    });
  }, [cards, query]);

  return (
    <div className="space-y-6">
      <input
        type="search"
        placeholder="Search programs, comparables, indications…"
        value={query}
        onChange={(e) => setQuery(e.target.value)}
        className="w-full max-w-md rounded-md border border-border bg-background px-3 py-2 text-sm"
        aria-label="Search opportunities"
      />

      <p className="text-sm text-muted-foreground">
        {filtered.length} Rhode Island patent-backed venture programs — comparator-grounded financing
        and physician syndicates.
      </p>

      <div className="grid gap-4 md:grid-cols-2 xl:grid-cols-3">
        {filtered.map((card) => (
          <Link key={card.case_id} href={`/opportunities/${card.case_id}`} className="group block">
            <Card className="h-full border-border/80 bg-card/80 transition-colors group-hover:border-cockpit-teal/40">
              <CardHeader className="space-y-3 pb-2">
                <div className="flex flex-wrap items-center gap-2">
                  <p className="text-[10px] uppercase tracking-wider text-cockpit-teal">
                    {card.opportunity_type_label}
                  </p>
                  {card.catalog_tier ? (
                    <Badge variant="outline" className="text-[10px] font-normal">
                      Tier {card.catalog_tier}
                    </Badge>
                  ) : null}
                  {card.comparator_grounded ? (
                    <Badge variant="secondary" className="text-[10px] font-normal">
                      Comp-grounded
                    </Badge>
                  ) : null}
                </div>
                <CardTitle className="text-base leading-snug group-hover:text-cockpit-teal">
                  {card.title}
                </CardTitle>
                <CardDescription className="line-clamp-3 text-sm leading-relaxed">
                  {card.thesis_teaser}
                </CardDescription>
              </CardHeader>
              <CardContent className="space-y-4">
                {card.value_band_label ? (
                  <p className="text-xs">
                    <span className="text-muted-foreground">Market precedent: </span>
                    <span className="font-medium text-foreground">{card.value_band_label}</span>
                  </p>
                ) : null}
                {card.lead_comparable_name ? (
                  <p className="text-xs text-muted-foreground">
                    Lead comp: <span className="text-foreground">{card.lead_comparable_name}</span>
                  </p>
                ) : null}
                  <dl className="grid grid-cols-2 gap-2 text-center text-xs sm:grid-cols-4">
                    <div className="rounded-md bg-muted/30 px-2 py-2">
                      <dt className="text-muted-foreground">Patents</dt>
                      <dd className="mt-0.5 text-sm font-semibold">{card.patent_count || "—"}</dd>
                    </div>
                    <div className="rounded-md bg-muted/30 px-2 py-2">
                      <dt className="text-muted-foreground">Pubs</dt>
                      <dd className="mt-0.5 text-sm font-semibold">
                        {card.publication_count || "—"}
                      </dd>
                    </div>
                  <div className="rounded-md bg-muted/30 px-2 py-2">
                    <dt className="text-muted-foreground">Physicians</dt>
                    <dd className="mt-0.5 text-sm font-semibold">{card.physician_count}</dd>
                  </div>
                  <div className="rounded-md bg-muted/30 px-2 py-2">
                    <dt className="text-muted-foreground">Stage</dt>
                    <dd className="mt-0.5 text-sm font-semibold capitalize leading-tight">
                      {card.development_stage || "—"}
                    </dd>
                  </div>
                </dl>
                <p className="text-sm font-medium text-foreground">
                  {formatUsd(card.capital_gap_usd)}{" "}
                  <span className="font-normal text-muted-foreground">RI package · 50/50</span>
                </p>
                {card.has_data_caveat ? (
                  <Badge variant="warning" className="text-[10px] font-normal">
                    Data review needed
                  </Badge>
                ) : null}
              </CardContent>
            </Card>
          </Link>
        ))}
      </div>
    </div>
  );
}
