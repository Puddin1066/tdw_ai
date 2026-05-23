"use client";

import { useMemo, useState } from "react";
import type { CaseMetadata } from "@/types/artifacts";
import { Badge } from "@/components/ui/badge";
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card";
import { formatConfidence } from "@/lib/utils";

interface CompareWorkbenchProps {
  cases: CaseMetadata[];
}

function initialSelection(cases: CaseMetadata[]): string[] {
  const benchmarks = cases.filter((item) => item.is_benchmark).map((item) => item.case_id);
  const nonBenchmarks = cases.filter((item) => !item.is_benchmark).map((item) => item.case_id);
  const selected: string[] = [];
  if (benchmarks.length > 0) selected.push(benchmarks[0]);
  if (nonBenchmarks.length > 0) selected.push(nonBenchmarks[0]);
  if (selected.length < 2 && cases.length > 1) selected.push(cases[1].case_id);
  if (selected.length === 0 && cases.length > 0) selected.push(cases[0].case_id);
  return selected.slice(0, 3);
}

export function CompareWorkbench({ cases }: CompareWorkbenchProps) {
  const [selectedCaseIds, setSelectedCaseIds] = useState<string[]>(() => initialSelection(cases));

  const selected = useMemo(
    () => cases.filter((item) => selectedCaseIds.includes(item.case_id)).slice(0, 3),
    [cases, selectedCaseIds],
  );

  const toggleSelection = (caseId: string) => {
    setSelectedCaseIds((current) => {
      if (current.includes(caseId)) {
        return current.filter((id) => id !== caseId);
      }
      if (current.length >= 3) {
        return [...current.slice(1), caseId];
      }
      return [...current, caseId];
    });
  };

  return (
    <div className="space-y-4">
      <Card className="border-border/70 bg-card/70">
        <CardHeader>
          <CardTitle>Compare workspace</CardTitle>
          <CardDescription>
            Compare up to 3 cases using the same standard for what data was sourced, how deeply it
            was fetched, how it was framed, and whether it is reliable enough for benchmark decisions.
          </CardDescription>
        </CardHeader>
        <CardContent className="space-y-3">
          <div className="flex flex-wrap gap-2">
            {cases.map((item) => {
              const active = selectedCaseIds.includes(item.case_id);
              return (
                <button
                  key={item.case_id}
                  type="button"
                  onClick={() => toggleSelection(item.case_id)}
                  className={`rounded border px-3 py-1 text-xs transition-colors ${
                    active
                      ? "border-cockpit-teal/60 bg-cockpit-teal/10 text-cockpit-teal"
                      : "border-border/60 bg-background/40 text-muted-foreground hover:text-foreground"
                  }`}
                >
                  {item.case_id}
                </button>
              );
            })}
          </div>
          <p className="text-xs text-muted-foreground">
            How to read: sourced records and connectors show evidence volume, contract metrics show
            comparability quality, and fallback warnings indicate reduced trust.
          </p>
        </CardContent>
      </Card>

      <div className="grid gap-4 lg:grid-cols-3">
        {selected.map((item) => (
          <Card key={item.case_id} className="border-border/80 bg-card/80">
            <CardHeader className="pb-2">
              <div className="flex items-center justify-between gap-2">
                <CardTitle className="text-base">{item.case_id}</CardTitle>
                {item.is_benchmark ? <Badge variant="outline">Benchmark</Badge> : null}
              </div>
              <CardDescription>
                {item.target_name} · {item.indication_name}
              </CardDescription>
            </CardHeader>
            <CardContent className="space-y-2 text-sm">
              <MetricLine
                label="Comparability status"
                value={
                  typeof item.comparability_passed === "boolean"
                    ? item.comparability_passed
                      ? "pass"
                      : "fail"
                    : "n/a"
                }
              />
              <MetricLine
                label="Contract score"
                value={
                  typeof item.comparability_score === "number"
                    ? formatConfidence(item.comparability_score)
                    : "n/a"
                }
              />
              <MetricLine
                label="Total sourced records"
                value={typeof item.total_records === "number" ? String(item.total_records) : "n/a"}
              />
              <MetricLine
                label="Connectors with records"
                value={
                  typeof item.connectors_with_records === "number"
                    ? String(item.connectors_with_records)
                    : "n/a"
                }
              />
              <MetricLine label="Depth proxy" value={`evidence ${item.evidence_density}`} />
              <MetricLine
                label="Fallback connectors"
                value={
                  typeof item.fallback_connector_count === "number"
                    ? String(item.fallback_connector_count)
                    : "n/a"
                }
              />
              <MetricLine
                label="Mock/Synthetic Fallback warnings"
                value={
                  typeof item.mock_fallback_warning_count === "number"
                    ? String(item.mock_fallback_warning_count)
                    : "n/a"
                }
              />
              <MetricLine label="Top risk framing" value={item.top_risk || "—"} />
            </CardContent>
          </Card>
        ))}
      </div>
    </div>
  );
}

function MetricLine({ label, value }: { label: string; value: string }) {
  return (
    <p className="flex items-start justify-between gap-3">
      <span className="text-xs text-muted-foreground">{label}</span>
      <span className="max-w-[60%] text-right font-mono text-xs">{value}</span>
    </p>
  );
}
