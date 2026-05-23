import type { EvalResultsData } from "@/types/artifacts";
import { Badge } from "@/components/ui/badge";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { EmptyState } from "@/components/EmptyState";
import { formatConfidence } from "@/lib/utils";

export interface EvalPanelProps {
  evalResults: EvalResultsData | null;
}

export function EvalPanel({ evalResults }: EvalPanelProps) {
  if (!evalResults) {
    return (
      <EmptyState
        title="No evaluation results"
        description="eval_results.json has not been generated for this case packet."
      />
    );
  }

  const metrics = evalResults.metrics;
  const evaluations = evalResults.evaluations ?? [];

  return (
    <div className="space-y-4">
      <div className="flex flex-wrap gap-2">
        <Badge variant={evalResults.overall_passed ? "success" : "danger"}>
          {evalResults.overall_passed ? "Overall pass" : "Overall fail"}
        </Badge>
        <Badge variant="outline">
          Aggregate: {formatConfidence(evalResults.aggregate_score)}
        </Badge>
      </div>

      <div className="grid gap-4 sm:grid-cols-3">
        <MetricCard
          label="Citation fidelity"
          value={formatConfidence(metrics.citation_fidelity_score)}
        />
        <MetricCard
          label="Unsupported claims"
          value={String(metrics.unsupported_claim_count)}
          alert={metrics.unsupported_claim_count > 0}
        />
        <MetricCard
          label="Hallucinated trials"
          value={String(metrics.hallucinated_trial_count)}
          alert={metrics.hallucinated_trial_count > 0}
        />
      </div>
      {typeof metrics.benchmark_contract_score === "number" ? (
        <div className="grid gap-4 sm:grid-cols-3">
          <MetricCard
            label="Benchmark contract"
            value={formatConfidence(metrics.benchmark_contract_score)}
            alert={metrics.benchmark_contract_passed === false}
          />
          <MetricCard
            label="Contract issues"
            value={String(metrics.benchmark_contract_issue_count ?? 0)}
            alert={(metrics.benchmark_contract_issue_count ?? 0) > 0}
          />
          <MetricCard
            label="Fallback connectors"
            value={String(metrics.contract_fallback_entries ?? 0)}
            alert={(metrics.contract_fallback_entries ?? 0) > 0}
          />
        </div>
      ) : null}

      {evaluations.length > 0 ? (
        <div className="overflow-x-auto rounded-lg border border-border">
          <table className="w-full text-left text-sm">
            <thead className="border-b border-border bg-muted/30 text-xs uppercase text-muted-foreground">
              <tr>
                <th className="px-4 py-3">Evaluator</th>
                <th className="px-4 py-3">Score</th>
                <th className="px-4 py-3">Status</th>
                <th className="px-4 py-3">Checked artifacts</th>
              </tr>
            </thead>
            <tbody>
              {evaluations.map((ev) => (
                <tr key={ev.evaluator_name} className="border-b border-border/60">
                  <td className="px-4 py-3 font-mono text-xs">{ev.evaluator_name}</td>
                  <td className="px-4 py-3 font-mono">{ev.score.toFixed(2)}</td>
                  <td className="px-4 py-3">
                    <Badge variant={ev.passed ? "success" : "danger"}>
                      {ev.passed ? "pass" : "fail"}
                    </Badge>
                  </td>
                  <td className="px-4 py-3 text-xs text-muted-foreground">
                    {ev.checked_artifacts.join(", ")}
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      ) : (
        <p className="text-sm text-muted-foreground">No per-evaluator breakdown available.</p>
      )}
    </div>
  );
}

function MetricCard({
  label,
  value,
  alert = false,
}: {
  label: string;
  value: string;
  alert?: boolean;
}) {
  return (
    <Card className={alert ? "border-cockpit-rose/40" : undefined}>
      <CardHeader className="pb-1">
        <CardTitle className="text-xs font-normal text-muted-foreground">{label}</CardTitle>
      </CardHeader>
      <CardContent>
        <p className={`font-mono text-2xl font-semibold ${alert ? "text-cockpit-rose" : ""}`}>
          {value}
        </p>
      </CardContent>
    </Card>
  );
}
