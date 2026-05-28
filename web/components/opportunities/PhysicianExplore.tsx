"use client";

import Link from "next/link";
import { useMemo, useState } from "react";
import type { PhysicianOpportunityEdge } from "@/types/opportunities";

interface PhysicianExploreProps {
  edges: PhysicianOpportunityEdge[];
}

export function PhysicianExplore({ edges }: PhysicianExploreProps) {
  const [query, setQuery] = useState("");

  const filtered = useMemo(() => {
    const q = query.trim().toLowerCase();
    if (!q) return edges.slice(0, 100);
    return edges.filter((edge) => {
      const hay = `${edge.name} ${edge.specialty} ${edge.institution} ${edge.physician_id}`.toLowerCase();
      return hay.includes(q);
    }).slice(0, 100);
  }, [edges, query]);

  return (
    <div className="space-y-4">
      <input
        type="search"
        placeholder="Search physician name, specialty, NPI…"
        value={query}
        onChange={(e) => setQuery(e.target.value)}
        className="w-full max-w-md rounded-md border border-border bg-background px-3 py-2 text-sm"
      />
      <p className="text-sm text-muted-foreground">
        Showing {filtered.length} clinicians (max 100). Cross-opportunity matches support syndicate planning.
      </p>
      <div className="space-y-3">
        {filtered.map((edge) => (
          <div
            key={edge.physician_id}
            className="rounded-md border border-border/60 bg-card/50 px-4 py-3"
          >
            <p className="font-medium">{edge.name}</p>
            <p className="text-sm text-muted-foreground">
              {edge.specialty} · {edge.institution}
            </p>
            <p className="mt-2 text-xs text-muted-foreground">
              Matched to {edge.opportunities.length} opportunities
            </p>
            <ul className="mt-2 flex flex-wrap gap-2">
              {edge.opportunities.slice(0, 8).map((opp) => (
                <li key={opp.case_id}>
                  <Link
                    href={`/opportunities/${opp.case_id}`}
                    className="rounded border border-border/60 px-2 py-0.5 text-xs hover:border-cockpit-teal/40"
                  >
                    {opp.display_name.slice(0, 36)}
                    {opp.display_name.length > 36 ? "…" : ""} ({opp.match_score_0_100})
                  </Link>
                </li>
              ))}
              {edge.opportunities.length > 8 ? (
                <li className="text-xs text-muted-foreground">+{edge.opportunities.length - 8} more</li>
              ) : null}
            </ul>
          </div>
        ))}
      </div>
    </div>
  );
}
