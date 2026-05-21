import type { SourceManifestData } from "@/types/artifacts";
import { Badge } from "@/components/ui/badge";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { EmptyState } from "@/components/EmptyState";

export interface SourceManifestProps {
  manifest: SourceManifestData | null;
}

export function SourceManifest({ manifest }: SourceManifestProps) {
  const entries = manifest?.entries ?? [];
  const benchmarkPlan = manifest?.benchmark_plan;

  if (entries.length === 0) {
    return (
      <EmptyState
        title="No source manifest"
        description="source_manifest.json is missing or lists no connector queries for this case."
      />
    );
  }

  const totalRecords = entries.reduce((sum, e) => sum + e.record_count, 0);

  return (
    <div className="space-y-4">
      <Badge variant="outline">{totalRecords} total records</Badge>
      {benchmarkPlan ? (
        <Card>
          <CardHeader className="pb-2">
            <CardTitle className="text-sm">Comparable benchmark plan (MCP prompt set)</CardTitle>
          </CardHeader>
          <CardContent className="space-y-3 text-sm">
            {benchmarkPlan.input_summary ? (
              <div className="grid gap-2 text-xs md:grid-cols-2">
                <InputLine label="Target" value={benchmarkPlan.input_summary.target} />
                <InputLine label="Indication" value={benchmarkPlan.input_summary.indication} />
                <InputLine label="Target alias" value={benchmarkPlan.input_summary.target_alias} />
                <InputLine
                  label="Mechanism direction"
                  value={benchmarkPlan.input_summary.mechanism_direction}
                />
                <InputLine label="Modality" value={benchmarkPlan.input_summary.modality} />
                <InputLine label="Patient segment" value={benchmarkPlan.input_summary.patient_segment} />
                <InputLine label="Geography" value={benchmarkPlan.input_summary.geography} />
                <InputLine label="Asset" value={benchmarkPlan.input_summary.asset} />
                <InputLine label="Company" value={benchmarkPlan.input_summary.company} />
                <InputLine
                  label="Development stage"
                  value={benchmarkPlan.input_summary.development_stage}
                />
                <InputLine
                  label="Strategic question"
                  value={benchmarkPlan.input_summary.strategic_question}
                />
                <InputLine
                  label="Licensing question"
                  value={benchmarkPlan.input_summary.licensing_question}
                />
                <InputLine
                  label="Investment question"
                  value={benchmarkPlan.input_summary.investment_question}
                />
                <InputLine
                  label="Comparators"
                  value={(benchmarkPlan.input_summary.comparators ?? []).join("; ")}
                />
              </div>
            ) : null}
            {(benchmarkPlan.comparable_topics ?? []).length > 0 ? (
              <div>
                <p className="text-xs font-medium text-muted-foreground">Comparable topics</p>
                <ul className="mt-1 list-inside list-disc space-y-1 text-xs text-muted-foreground">
                  {(benchmarkPlan.comparable_topics ?? []).slice(0, 6).map((topic) => (
                    <li key={topic}>{topic}</li>
                  ))}
                </ul>
              </div>
            ) : null}
            {(benchmarkPlan.mcp_prompt_set ?? []).length > 0 ? (
              <div>
                <p className="text-xs font-medium text-muted-foreground">Prompt templates</p>
                <div className="mt-2 space-y-2">
                  {(benchmarkPlan.mcp_prompt_set ?? []).slice(0, 8).map((prompt, idx) => (
                    <div key={`${prompt.connector_name}-${prompt.query_text}-${idx}`} className="rounded-md border border-border/60 p-2">
                      <p className="font-mono text-xs">
                        {prompt.connector_name} · {prompt.entity}
                      </p>
                      <p className="text-xs text-muted-foreground">{prompt.query_text}</p>
                    </div>
                  ))}
                </div>
              </div>
            ) : null}
            {(benchmarkPlan.mcp_prompt_runs ?? []).length > 0 ? (
              <div>
                <p className="text-xs font-medium text-muted-foreground">
                  Cached prompt responses
                </p>
                <div className="mt-2 space-y-2">
                  {(benchmarkPlan.mcp_prompt_runs ?? []).slice(0, 12).map((run) => (
                    <div key={run.prompt_id} className="rounded-md border border-border/60 p-2">
                      <div className="flex flex-wrap gap-2 text-xs">
                        <span className="font-mono">{run.prompt_id}</span>
                        <span>{run.connector_name}</span>
                        <span className="capitalize text-muted-foreground">{run.status}</span>
                        <span className="text-muted-foreground">{run.cached_at}</span>
                      </div>
                      <p className="mt-1 text-xs text-muted-foreground">{run.query_text}</p>
                      <p className="mt-1 text-xs">{run.response_text}</p>
                      {run.source_record_ids.length > 0 ? (
                        <p className="mt-1 text-xs text-muted-foreground">
                          Source IDs: {run.source_record_ids.slice(0, 3).join(", ")}
                        </p>
                      ) : null}
                      {run.warning ? (
                        <p className="mt-1 text-xs text-amber-300">Warning: {run.warning}</p>
                      ) : null}
                      {run.error ? (
                        <p className="mt-1 text-xs text-red-300">Error: {run.error}</p>
                      ) : null}
                    </div>
                  ))}
                </div>
              </div>
            ) : null}
          </CardContent>
        </Card>
      ) : null}
      <div className="grid gap-3 md:grid-cols-2">
        {entries.map((entry) => (
          <Card key={`${entry.connector_name}-${entry.retrieved_at}`}>
            <CardHeader className="pb-2">
              <CardTitle className="text-sm font-mono">{entry.connector_name}</CardTitle>
              <p className="text-xs text-muted-foreground">{entry.source_name}</p>
            </CardHeader>
            <CardContent className="space-y-2 text-sm">
              <p>
                <span className="text-muted-foreground">Records: </span>
                <span className="font-mono">{entry.record_count}</span>
              </p>
              <p>
                <span className="text-muted-foreground">Mode: </span>
                <span className="capitalize">{entry.mode}</span>
              </p>
              <p>
                <span className="text-muted-foreground">Backend: </span>
                <span className="font-mono">{entry.backend_used ?? "unknown"}</span>
              </p>
              <p>
                <span className="text-muted-foreground">Connection: </span>
                <span className="capitalize">{entry.connection_status ?? "unknown"}</span>
              </p>
              <p>
                <span className="text-muted-foreground">Value score: </span>
                <span className="font-mono">{entry.value_score ?? 0}/5</span>
              </p>
              {entry.query?.raw_query ? (
                <p className="text-xs text-muted-foreground">{entry.query.raw_query}</p>
              ) : null}
              {entry.value_interpretation ? (
                <p className="text-xs text-muted-foreground">{entry.value_interpretation}</p>
              ) : null}
              {(entry.warnings?.length ?? 0) > 0 ? (
                <p className="text-xs text-amber-300">
                  Warning: {entry.warnings?.[0]}
                </p>
              ) : null}
              {(entry.errors?.length ?? 0) > 0 ? (
                <p className="text-xs text-red-300">
                  Error: {entry.errors?.[0]}
                </p>
              ) : null}
              <p className="text-xs text-muted-foreground">Retrieved: {entry.retrieved_at}</p>
            </CardContent>
          </Card>
        ))}
      </div>
    </div>
  );
}

function InputLine({ label, value }: { label: string; value?: string | null }) {
  return (
    <p>
      <span className="text-muted-foreground">{label}: </span>
      {value && value.trim() ? value : "—"}
    </p>
  );
}
