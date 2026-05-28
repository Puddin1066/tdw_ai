"use client";

import Link from "next/link";
import { useMemo, useState } from "react";
import type { TrialTemplateUsage } from "@/types/opportunities";

interface TrialExploreProps {
  templates: TrialTemplateUsage[];
}

export function TrialExplore({ templates }: TrialExploreProps) {
  const [query, setQuery] = useState("");

  const filtered = useMemo(() => {
    const q = query.trim().toLowerCase();
    if (!q) return templates;
    return templates.filter(
      (t) =>
        t.template_id.toLowerCase().includes(q) ||
        t.study_type.toLowerCase().includes(q),
    );
  }, [templates, query]);

  return (
    <div className="space-y-4">
      <input
        type="search"
        placeholder="Search template id or study type…"
        value={query}
        onChange={(e) => setQuery(e.target.value)}
        className="w-full max-w-md rounded-md border border-border bg-background px-3 py-2 text-sm"
      />
      <div className="space-y-3">
        {filtered.map((template) => (
          <div
            key={template.template_id}
            className="rounded-md border border-border/60 bg-card/50 px-4 py-3"
          >
            <p className="font-mono text-sm font-medium">{template.template_id}</p>
            <p className="text-sm text-muted-foreground capitalize">{template.study_type}</p>
            <p className="mt-1 text-xs text-muted-foreground">
              Used by {template.opportunity_count} opportunities
            </p>
            <ul className="mt-2 flex flex-wrap gap-2">
              {template.case_ids.slice(0, 12).map((caseId) => (
                <li key={caseId}>
                  <Link
                    href={`/opportunities/${caseId}`}
                    className="text-xs text-cockpit-teal hover:underline"
                  >
                    {caseId}
                  </Link>
                </li>
              ))}
              {template.case_ids.length > 12 ? (
                <li className="text-xs text-muted-foreground">
                  +{template.case_ids.length - 12} more
                </li>
              ) : null}
            </ul>
          </div>
        ))}
      </div>
    </div>
  );
}
