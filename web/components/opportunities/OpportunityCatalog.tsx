"use client";

import Link from "next/link";
import { useMemo, useState } from "react";
import type { CatalogCard } from "@/types/combined";
import { Badge } from "@/components/ui/badge";
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card";
import { formatUsd } from "@/lib/format";

type CatalogFilter = "all" | "comp_grounded" | "tier_a" | "package_ready";

interface OpportunityCatalogProps {
  cards: CatalogCard[];
}

const FILTER_OPTIONS: { id: CatalogFilter; label: string }[] = [
  { id: "all", label: "All" },
  { id: "package_ready", label: "Package-ready" },
  { id: "comp_grounded", label: "Comp-grounded" },
  { id: "tier_a", label: "Tier A" },
];

function matchesFilter(card: CatalogCard, filter: CatalogFilter): boolean {
  switch (filter) {
    case "comp_grounded":
      return card.comparator_grounded;
    case "tier_a":
      return card.catalog_tier === "A";
    case "package_ready":
      return (
        card.comparator_grounded &&
        card.physician_count > 0 &&
        !card.has_data_caveat &&
        card.capital_gap_usd <= 400_000
      );
    default:
      return true;
  }
}

export function OpportunityCatalog({ cards }: OpportunityCatalogProps) {
  const [query, setQuery] = useState("");
  const [filter, setFilter] = useState<CatalogFilter>("all");

  const filtered = useMemo(() => {
    const q = query.trim().toLowerCase();
    return cards.filter((card) => {
      if (!matchesFilter(card, filter)) return false;
      if (!q) return true;
      const hay =
        `${card.title} ${card.thesis_teaser} ${card.lead_comparable_name} ${card.opportunity_type_label} ${card.ri_institution ?? ""}`.toLowerCase();
      return hay.includes(q);
    });
  }, [cards, query, filter]);

  return (
    <div id="catalog" className="scroll-mt-8 space-y-6">
      <div className="space-y-3">
        <h2 className="text-xl font-semibold tracking-tight">Opportunity catalog</h2>
        <p className="max-w-3xl text-sm leading-relaxed text-muted-foreground">
          {cards.length} RI technologies in the pipeline. Each card links to a diligence memo with
          cited comparables, physician matches, and use-of-funds. Draft memos are labeled; approved
          memos are ready for syndicate review.
        </p>
        <div className="flex flex-wrap gap-2 text-xs text-muted-foreground">
          <span className="font-medium text-foreground">Legend:</span>
          <span>
            <Badge variant="secondary" className="mr-1 text-[10px] font-normal">
              Comp-grounded
            </Badge>
            financing sized to a verified market comparable
          </span>
          <span className="hidden sm:inline">·</span>
          <span>
            <Badge variant="outline" className="mr-1 text-[10px] font-normal text-muted-foreground">
              Draft
            </Badge>
            enrichment in progress — verify citations before sharing
          </span>
          <span className="hidden sm:inline">·</span>
          <span>
            <Badge variant="outline" className="mr-1 text-[10px] font-normal">
              Tier A
            </Badge>
            highest-priority cases for physician and investor review
          </span>
        </div>
      </div>

      <div className="flex flex-col gap-3 sm:flex-row sm:items-center sm:justify-between">
        <div className="flex flex-wrap gap-2">
          {FILTER_OPTIONS.map((option) => (
            <button
              key={option.id}
              type="button"
              onClick={() => setFilter(option.id)}
              className={`rounded-md border px-3 py-1.5 text-xs transition-colors ${
                filter === option.id
                  ? "border-cockpit-teal/50 bg-cockpit-teal/10 font-medium text-cockpit-teal"
                  : "border-border bg-background text-muted-foreground hover:text-foreground"
              }`}
            >
              {option.label}
            </button>
          ))}
        </div>
        <input
          type="search"
          placeholder="Search programs, comparables, indications…"
          value={query}
          onChange={(e) => setQuery(e.target.value)}
          className="w-full rounded-md border border-border bg-background px-3 py-2 text-sm sm:max-w-xs"
          aria-label="Search opportunities"
        />
      </div>

      <p className="text-sm text-muted-foreground">
        Showing {filtered.length} of {cards.length} programs
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
                  {(card.review_status || "pending").toLowerCase() !== "approved" ? (
                    <Badge variant="outline" className="text-[10px] font-normal text-muted-foreground">
                      Draft
                    </Badge>
                  ) : null}
                </div>
                {card.ri_institution ? (
                  <p className="text-xs text-muted-foreground">{card.ri_institution}</p>
                ) : null}
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
                    <span className="text-muted-foreground">Financing precedent: </span>
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
