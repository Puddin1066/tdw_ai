"use client";

import Link from "next/link";
import type { OpportunityIndexRow } from "@/types/opportunities";
import { ReadinessBadge } from "@/components/opportunities/ReadinessBadge";
import { formatUsd, opportunityTypeLabel } from "@/lib/format";

interface SyndicateCompareProps {
  rows: OpportunityIndexRow[];
}

export function SyndicateCompare({ rows }: SyndicateCompareProps) {
  if (rows.length === 0) {
    return (
      <p className="text-sm text-muted-foreground">
        No cases selected.{" "}
        <Link href="/opportunities" className="text-cockpit-teal hover:underline">
          Return to catalog
        </Link>
      </p>
    );
  }

  const dimensions: Array<{ label: string; render: (row: OpportunityIndexRow) => string }> = [
    { label: "Readiness", render: (r) => `${r.financing_readiness_score_0_100.toFixed(0)} (${r.financing_readiness_state.replace(/_/g, " ")})` },
    { label: "Capital gap", render: (r) => formatUsd(r.capital_gap_usd) },
    { label: "Gap remaining", render: (r) => formatUsd(r.capital_gap_remaining_usd) },
    { label: "Physicians", render: (r) => `${r.physician_candidate_count}/10` },
    { label: "Staffing gaps", render: (r) => r.staffing_gaps.join(", ") || "—" },
    { label: "Trial cost", render: (r) => formatUsd(r.estimated_cost_usd) },
    { label: "Trial weeks", render: (r) => String(r.estimated_duration_weeks) },
    { label: "Type", render: (r) => opportunityTypeLabel(r.opportunity_type) },
    { label: "Patents", render: (r) => String(r.patent_count) },
    { label: "Mocked", render: (r) => (r.mocked ? "yes" : "no") },
  ];

  return (
    <div className="overflow-x-auto rounded-md border border-border/60">
      <table className="w-full min-w-[720px] text-left text-sm">
        <thead>
          <tr className="border-b border-border/60 bg-muted/30">
            <th className="px-3 py-2 text-xs uppercase text-muted-foreground">Dimension</th>
            {rows.map((row) => (
              <th key={row.case_id} className="px-3 py-2">
                <Link href={`/opportunities/${row.case_id}`} className="font-medium hover:text-cockpit-teal">
                  {row.display_name.slice(0, 40)}
                  {row.display_name.length > 40 ? "…" : ""}
                </Link>
                <div className="mt-1">
                  <ReadinessBadge state={row.financing_readiness_state} />
                </div>
              </th>
            ))}
          </tr>
        </thead>
        <tbody>
          {dimensions.map((dim) => (
            <tr key={dim.label} className="border-b border-border/40">
              <td className="px-3 py-2 font-medium text-muted-foreground">{dim.label}</td>
              {rows.map((row) => (
                <td key={`${dim.label}-${row.case_id}`} className="px-3 py-2">
                  {dim.render(row)}
                </td>
              ))}
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  );
}
