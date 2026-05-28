"use client";

import { ExternalLink } from "@/components/curate/ExternalLink";
import { collectFactCheckLinks } from "@/lib/riCasesCsv";
import type { RiCaseRow } from "@/types/riCasesEnriched";

interface FactCheckPanelProps {
  row: RiCaseRow;
}

export function FactCheckPanel({ row }: FactCheckPanelProps) {
  const groups = collectFactCheckLinks(row);
  const total = groups.reduce((n, g) => n + g.links.length, 0);

  if (total === 0) {
    return (
      <section className="rounded-lg border border-dashed border-border/50 px-4 py-3 text-sm text-muted-foreground">
        No source URLs on this case yet — add patent, publication, or comparable links in the tabs
        below.
      </section>
    );
  }

  return (
    <section className="rounded-lg border border-cockpit-teal/30 bg-cockpit-teal/5 px-4 py-3 space-y-3">
      <div className="flex flex-wrap items-baseline justify-between gap-2">
        <h3 className="text-sm font-semibold text-foreground">Fact-check links</h3>
        <span className="text-xs text-muted-foreground">{total} sources</span>
      </div>
      <div className="grid gap-4 sm:grid-cols-2 lg:grid-cols-3">
        {groups.map((group) => (
          <div key={group.label} className="space-y-1.5">
            <p className="text-[10px] font-medium uppercase tracking-wide text-muted-foreground">
              {group.label}
            </p>
            <ul className="space-y-1">
              {group.links.map((link) => (
                <li key={`${group.label}-${link.href}`}>
                  <ExternalLink href={link.href} label={link.label} className="text-xs" />
                </li>
              ))}
            </ul>
          </div>
        ))}
      </div>
    </section>
  );
}
