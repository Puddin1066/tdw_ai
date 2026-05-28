"use client";

import Link from "next/link";
import { useMemo, useState } from "react";
import { ArrowLeft, FlaskConical, Search, ShieldAlert, Target } from "lucide-react";
import type {
  CaseMetadata,
  EvaluationCaseData,
  GeneratedQualitativeAssessment,
  QualitativeDimensionKey,
} from "@/types/artifacts";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card";

interface DealEvaluationWorkflowProps {
  cases: EvaluationCaseData[];
}

const DIMENSION_ORDER: QualitativeDimensionKey[] = [
  "science",
  "differentiation",
  "regulatory",
  "execution",
  "strategicFit",
];

const DIMENSION_LABELS: Record<QualitativeDimensionKey, string> = {
  science: "Science quality",
  differentiation: "Differentiation and moat",
  regulatory: "Regulatory clarity",
  execution: "Execution readiness",
  strategicFit: "Strategic fit",
};

export function DealEvaluationWorkflow({ cases }: DealEvaluationWorkflowProps) {
  const candidateCases = useMemo(
    () => cases.filter((item) => !item.metadata.is_benchmark),
    [cases],
  );
  const benchmarkCases = useMemo(
    () => cases.filter((item) => item.metadata.is_benchmark),
    [cases],
  );
  const benchmarkCohorts = useMemo(
    () =>
      Array.from(
        new Set(
          benchmarkCases
            .map((item) => item.metadata.benchmark_cohort)
            .filter((item): item is string => !!item),
        ),
      ).sort(),
    [benchmarkCases],
  );

  const [query, setQuery] = useState("");
  const [stageFilter, setStageFilter] = useState("all");
  const [cohortFilter, setCohortFilter] = useState("all");
  const [selectedCaseId, setSelectedCaseId] = useState(candidateCases[0]?.metadata.case_id ?? "");

  const stageOptions = useMemo(
    () =>
      Array.from(
        new Set(
          candidateCases
            .map((item) => item.metadata.maturity_stage)
            .filter((item): item is string => !!item),
        ),
      ).sort(),
    [candidateCases],
  );

  const filteredCandidates = useMemo(() => {
    const normalizedQuery = query.trim().toLowerCase();
    return candidateCases.filter((item) => {
      if (stageFilter !== "all" && item.metadata.maturity_stage !== stageFilter) return false;
      if (!normalizedQuery) return true;
      const fields = [
        item.metadata.display_name,
        item.metadata.case_id,
        item.metadata.target_name,
        item.metadata.indication_name,
        item.metadata.input_profile?.biology?.modality,
      ]
        .filter((value): value is string => !!value)
        .map((value) => value.toLowerCase());
      return fields.some((value) => value.includes(normalizedQuery));
    });
  }, [candidateCases, query, stageFilter]);

  const selectedCaseEntry = useMemo(
    () =>
      filteredCandidates.find((item) => item.metadata.case_id === selectedCaseId) ??
      candidateCases.find((item) => item.metadata.case_id === selectedCaseId) ??
      filteredCandidates[0] ??
      candidateCases[0] ??
      null,
    [candidateCases, filteredCandidates, selectedCaseId],
  );

  const selectedCase = selectedCaseEntry?.metadata ?? null;
  const selectedQualitative = selectedCaseEntry?.qualitative_assessment ?? null;
  const selectedRiReadiness = selectedCaseEntry?.ri_financing_readiness ?? null;

  const activeBenchmarks = useMemo(() => {
    if (cohortFilter === "all") return benchmarkCases;
    return benchmarkCases.filter((item) => item.metadata.benchmark_cohort === cohortFilter);
  }, [benchmarkCases, cohortFilter]);

  const nearestBenchmarks = useMemo(() => {
    if (!selectedCaseEntry) return [];
    return [...activeBenchmarks]
      .sort(
        (a, b) =>
          similarityScore(b.metadata, selectedCaseEntry.metadata) -
          similarityScore(a.metadata, selectedCaseEntry.metadata),
      )
      .slice(0, 5);
  }, [activeBenchmarks, selectedCaseEntry]);

  const quantScore = useMemo(() => {
    if (!selectedCase || activeBenchmarks.length === 0) return 0;
    const confidencePercentile = percentileRank(selectedCase.confidence_score ?? 0, activeBenchmarks, (item) =>
      safeNumber(item.metadata.confidence_score),
    );
    const comparabilityPercentile = percentileRank(
      selectedCase.comparability_score ?? 0,
      activeBenchmarks,
      (item) => safeNumber(item.metadata.comparability_score),
    );
    const recordsPercentile = percentileRank(selectedCase.total_records ?? 0, activeBenchmarks, (item) =>
      safeNumber(item.metadata.total_records),
    );
    const connectorsPercentile = percentileRank(
      selectedCase.connectors_with_records ?? 0,
      activeBenchmarks,
      (item) => safeNumber(item.metadata.connectors_with_records),
    );
    return (
      confidencePercentile * 0.35 +
      comparabilityPercentile * 0.25 +
      recordsPercentile * 0.2 +
      connectorsPercentile * 0.2
    );
  }, [activeBenchmarks, selectedCase]);

  const qualitativeScore = useMemo(() => {
    if (!selectedQualitative) return 0;
    const scores = DIMENSION_ORDER.map(
      (dimension) => selectedQualitative.dimensions[dimension].score_1_5,
    );
    const average = avg(scores);
    return ((average - 1) / 4) * 100;
  }, [selectedQualitative]);

  const riskPenalty = useMemo(() => {
    if (!selectedCase) return 100;
    let penalty = 0;
    if (selectedCase.evidence_density === "low") penalty += 20;
    if (selectedCase.evidence_density === "medium") penalty += 10;
    if (selectedCase.comparability_passed === false) penalty += 25;
    penalty += Math.min(30, safeNumber(selectedCase.fallback_connector_count) * 10);
    const records = safeNumber(selectedCase.total_records);
    if (records > 0 && records < 100) penalty += 15;
    if (records >= 100 && records < 250) penalty += 8;
    return Math.min(penalty, 100);
  }, [selectedCase]);

  const diligenceScore = Math.max(
    0,
    Math.min(100, quantScore * 0.45 + qualitativeScore * 0.35 + (100 - riskPenalty) * 0.2),
  );
  const riReadinessScore = safeNumber(selectedRiReadiness?.financing_readiness_score_0_100);
  const finalScore = selectedRiReadiness
    ? Math.max(0, Math.min(100, diligenceScore * 0.7 + riReadinessScore * 0.3))
    : diligenceScore;
  const recommendation = finalScore >= 75 ? "Prioritize" : finalScore >= 60 ? "Watchlist" : "Deprioritize";

  const mockedCandidate =
    Boolean(selectedCase?.mocked_api_calls) ||
    safeNumber(selectedCase?.fallback_connector_count) > 0 ||
    Boolean(selectedQualitative?.mocked_data_present);
  const mockedBenchmarks = activeBenchmarks.some(
    (item) =>
      Boolean(item.metadata.mocked_api_calls) ||
      safeNumber(item.metadata.fallback_connector_count) > 0 ||
      Boolean(item.qualitative_assessment.mocked_data_present),
  );

  const confidenceSignals = [
    selectedCase ? 1 : 0,
    safeNumber(selectedCase?.connectors_with_records) > 0 ? 1 : 0,
    safeNumber(selectedCase?.total_records) > 0 ? 1 : 0,
    activeBenchmarks.length >= 3 ? 1 : 0,
  ];
  const confidenceScore = (confidenceSignals.reduce((sum, item) => sum + item, 0) / confidenceSignals.length) * 100;

  return (
    <main className="mx-auto max-w-7xl space-y-6 px-4 py-8 sm:px-6 lg:px-8">
      <header className="space-y-3">
        <Link href="/" className="inline-flex items-center gap-1 text-sm text-muted-foreground hover:text-foreground">
          <ArrowLeft className="h-4 w-4" />
          Back to case library
        </Link>
        <p className="font-mono text-xs uppercase tracking-widest text-cockpit-teal">Deal evaluation workflow</p>
        <h1 className="text-3xl font-semibold tracking-tight">Search, benchmark, and prioritize</h1>
        <p className="max-w-3xl text-sm text-muted-foreground">
          Evaluate a target case against benchmark peers with percentile-based quantitative metrics and
          qualitative judgments generated only from cached artifacts.
        </p>
      </header>

      <div className="grid gap-6 lg:grid-cols-2">
        <Card className="border-border/80 bg-card/80">
          <CardHeader>
            <CardTitle className="flex items-center gap-2">
              <Search className="h-5 w-5 text-cockpit-teal" />
              Step 1: Search and pick a case
            </CardTitle>
            <CardDescription>Filter candidate cases before scoring.</CardDescription>
          </CardHeader>
          <CardContent className="space-y-4">
            <div className="grid gap-3 md:grid-cols-2">
              <InputRow label="Search query" value={query} onChange={setQuery} placeholder="Target, indication, modality" />
              <SelectRow
                label="Maturity stage"
                value={stageFilter}
                onChange={setStageFilter}
                options={[{ value: "all", label: "All stages" }, ...stageOptions.map((value) => ({ value, label: value }))]}
              />
            </div>
            <SelectRow
              label="Candidate case"
              value={selectedCase?.case_id ?? ""}
              onChange={setSelectedCaseId}
              options={filteredCandidates.map((item) => ({
                value: item.metadata.case_id,
                label: `${item.metadata.target_name} · ${item.metadata.indication_name}`,
              }))}
            />
            <p className="text-xs text-muted-foreground">
              Showing {filteredCandidates.length} candidate cases from {candidateCases.length} non-benchmark cases.
            </p>
          </CardContent>
        </Card>

        <Card className="border-border/80 bg-card/80">
          <CardHeader>
            <CardTitle className="flex items-center gap-2">
              <Target className="h-5 w-5 text-cockpit-teal" />
              Step 2: Benchmark cohort
            </CardTitle>
            <CardDescription>Scope comparison to all benchmarks or a specific benchmark cohort.</CardDescription>
          </CardHeader>
          <CardContent className="space-y-4">
            <SelectRow
              label="Benchmark cohort"
              value={cohortFilter}
              onChange={setCohortFilter}
              options={[
                { value: "all", label: "All benchmark cases" },
                ...benchmarkCohorts.map((cohort) => ({ value: cohort, label: cohort })),
              ]}
            />
            <div className="flex flex-wrap gap-2">
              <Badge variant={activeBenchmarks.length >= 5 ? "success" : "warning"}>
                {activeBenchmarks.length} benchmarks in scope
              </Badge>
              <Badge variant={mockedBenchmarks ? "warning" : "success"}>
                {mockedBenchmarks ? "Benchmark set includes mocked/fallback pulls" : "Benchmark set is live-only"}
              </Badge>
            </div>
            <p className="text-xs text-muted-foreground">
              Mock visibility is explicit. Any fallback connector in case artifacts is surfaced as mocked/fallback data.
            </p>
          </CardContent>
        </Card>
      </div>

      <div className="grid gap-6 lg:grid-cols-2">
        <Card className="border-border/80 bg-card/80">
          <CardHeader>
            <CardTitle className="flex items-center gap-2">
              <FlaskConical className="h-5 w-5 text-cockpit-teal" />
              Step 3: Quantitative score
            </CardTitle>
            <CardDescription>Percentile ranking of the selected case versus the active benchmark set.</CardDescription>
          </CardHeader>
          <CardContent className="space-y-3 text-sm">
            <ScoreRow label="Confidence percentile" value={metricPercentile(selectedCase, activeBenchmarks, "confidence_score")} />
            <ScoreRow
              label="Comparability percentile"
              value={metricPercentile(selectedCase, activeBenchmarks, "comparability_score")}
            />
            <ScoreRow label="Evidence volume percentile" value={metricPercentile(selectedCase, activeBenchmarks, "total_records")} />
            <ScoreRow
              label="Connector coverage percentile"
              value={metricPercentile(selectedCase, activeBenchmarks, "connectors_with_records")}
            />
            <div className="rounded-md border border-border/60 bg-background/40 px-3 py-2">
              <p className="font-medium text-foreground">Quant composite: {quantScore.toFixed(1)} / 100</p>
              <p className="text-xs text-muted-foreground">
                Weights: confidence 35%, comparability 25%, evidence volume 20%, connector coverage 20%.
              </p>
            </div>
          </CardContent>
        </Card>

        <Card className="border-border/80 bg-card/80">
          <CardHeader>
            <CardTitle className="flex items-center gap-2">
              <ShieldAlert className="h-5 w-5 text-cockpit-teal" />
              Step 4: Qualitative rubric
            </CardTitle>
            <CardDescription>
              Auto-generated from cached artifacts with source-record citations per dimension.
            </CardDescription>
          </CardHeader>
          <CardContent className="space-y-3 text-sm">
            {selectedQualitative ? (
              DIMENSION_ORDER.map((dimension) => (
                <GeneratedDimensionCard
                  key={dimension}
                  label={DIMENSION_LABELS[dimension]}
                  result={selectedQualitative.dimensions[dimension]}
                />
              ))
            ) : (
              <p className="text-muted-foreground">
                No qualitative artifact-derived assessment available for selected case.
              </p>
            )}
            <div className="rounded-md border border-border/60 bg-background/40 px-3 py-2">
              <p className="font-medium text-foreground">Qual composite: {qualitativeScore.toFixed(1)} / 100</p>
              <p className="text-xs text-muted-foreground">
                Source: {selectedQualitative?.generated_from ?? "n/a"}
              </p>
            </div>
          </CardContent>
        </Card>
      </div>

      <Card className="border-border/80 bg-card/80">
        <CardHeader>
          <CardTitle>Step 4b: RI clinical inflection readiness</CardTitle>
          <CardDescription>
            Static RI lens overlays clinical-inflection, physician staffing, and capital-path readiness.
          </CardDescription>
        </CardHeader>
        <CardContent className="space-y-4">
          {selectedRiReadiness ? (
            <>
              <div className="grid gap-3 md:grid-cols-4">
                <DecisionStat
                  label="Inflection score"
                  value={safeNumber(selectedRiReadiness.clinical_inflection_score_0_100).toFixed(1)}
                />
                <DecisionStat
                  label="Staffing feasibility"
                  value={safeNumber(selectedRiReadiness.staffing_feasibility_score_0_100).toFixed(1)}
                />
                <DecisionStat
                  label="Capital path score"
                  value={safeNumber(selectedRiReadiness.capital_path_score_0_100).toFixed(1)}
                />
                <DecisionStat
                  label="RI readiness score"
                  value={safeNumber(selectedRiReadiness.financing_readiness_score_0_100).toFixed(1)}
                />
              </div>
              <div className="flex flex-wrap items-center gap-2">
                <Badge variant={selectedRiReadiness.mocked ? "warning" : "success"}>
                  {selectedRiReadiness.mocked
                    ? "RI lens uses mocked static CSV inputs"
                    : "RI lens derived from validated non-mock inputs"}
                </Badge>
                <Badge
                  variant={
                    selectedRiReadiness.financing_readiness_state === "financeable_now"
                      ? "success"
                      : selectedRiReadiness.financing_readiness_state === "financeable_post_inflection"
                        ? "warning"
                        : "danger"
                  }
                >
                  {selectedRiReadiness.financing_readiness_state.replace(/_/g, " ")}
                </Badge>
              </div>
              <div className="rounded-md border border-border/60 bg-background/40 p-3">
                <p className="font-medium text-foreground">Next actions</p>
                {selectedRiReadiness.next_actions.length > 0 ? (
                  <ul className="mt-2 list-inside list-disc space-y-1 text-sm text-muted-foreground">
                    {selectedRiReadiness.next_actions.map((action) => (
                      <li key={action}>{action}</li>
                    ))}
                  </ul>
                ) : (
                  <p className="mt-2 text-sm text-muted-foreground">No RI next actions generated for this case.</p>
                )}
              </div>
            </>
          ) : (
            <p className="text-sm text-muted-foreground">
              No RI readiness artifact found for selected case. Run static RI artifact generation in workflow.
            </p>
          )}
        </CardContent>
      </Card>

      <Card className="border-border/80 bg-card/80">
        <CardHeader>
          <CardTitle>Step 5: Prioritization decision</CardTitle>
          <CardDescription>Final recommendation blends quant score, qual rubric, and explicit risk penalties.</CardDescription>
        </CardHeader>
        <CardContent className="space-y-4">
          <div className="grid gap-3 md:grid-cols-4">
            <DecisionStat label="Diligence score" value={diligenceScore.toFixed(1)} />
            <DecisionStat label="RI readiness score" value={riReadinessScore.toFixed(1)} />
            <DecisionStat
              label={selectedRiReadiness ? "Composite (70/30 blend)" : "Composite score"}
              value={finalScore.toFixed(1)}
            />
            <DecisionStat label="Confidence context" value={`${confidenceScore.toFixed(0)}%`} />
          </div>
          <div className="flex flex-wrap items-center gap-2">
            <Badge variant={recommendation === "Prioritize" ? "success" : recommendation === "Watchlist" ? "warning" : "danger"}>
              {recommendation}: {finalScore.toFixed(1)} / 100
            </Badge>
            <Badge variant={mockedCandidate ? "warning" : "success"}>
              {mockedCandidate ? "Selected case includes mocked/fallback API data" : "Selected case appears live-only"}
            </Badge>
          </div>
          <p className="text-sm text-muted-foreground">
            Rule bands: Prioritize ≥ 75, Watchlist 60-74, Deprioritize &lt; 60. The mocked/fallback badge should always be
            shown during investment review.
          </p>

          <div className="rounded-md border border-border/60 bg-background/40 p-3">
            <p className="font-medium text-foreground">Nearest benchmark context</p>
            {nearestBenchmarks.length === 0 ? (
              <p className="mt-1 text-sm text-muted-foreground">No benchmark peers available in the current cohort.</p>
            ) : (
              <ul className="mt-2 space-y-1 text-sm text-muted-foreground">
                {nearestBenchmarks.map((item) => (
                  <li key={item.metadata.case_id}>
                    {item.metadata.target_name} / {item.metadata.indication_name} (
                    {item.metadata.maturity_stage})
                  </li>
                ))}
              </ul>
            )}
          </div>

          {selectedCase ? (
            <>
              <Button asChild variant="outline">
                <Link href={`/opportunities/${selectedCase.case_id}`}>Open syndicate brief</Link>
              </Button>
              <Button asChild variant="outline">
                <Link href={`/cases/${selectedCase.case_id}`}>Open diligence cockpit</Link>
              </Button>
            </>
          ) : null}
        </CardContent>
      </Card>
    </main>
  );
}

function similarityScore(candidate: CaseMetadata, reference: CaseMetadata): number {
  let score = 0;
  if (candidate.maturity_stage === reference.maturity_stage) score += 2;
  if (candidate.indication_name.toLowerCase() === reference.indication_name.toLowerCase()) score += 3;
  if ((candidate.input_profile?.biology?.modality ?? "") === (reference.input_profile?.biology?.modality ?? "")) score += 2;
  score += Math.max(0, 1 - Math.abs(safeNumber(candidate.confidence_score) - safeNumber(reference.confidence_score)));
  return score;
}

function safeNumber(value: number | undefined | null): number {
  if (typeof value !== "number" || Number.isNaN(value)) return 0;
  return value;
}

function percentileRank<T>(value: number, set: T[], accessor: (item: T) => number): number {
  if (set.length === 0) return 0;
  const sorted = [...set].map(accessor).sort((a, b) => a - b);
  let belowOrEqual = 0;
  for (const item of sorted) {
    if (item <= value) belowOrEqual += 1;
  }
  return (belowOrEqual / sorted.length) * 100;
}

function metricPercentile(
  selectedCase: EvaluationCaseData["metadata"] | null,
  benchmarks: EvaluationCaseData[],
  key: "confidence_score" | "comparability_score" | "total_records" | "connectors_with_records",
): string {
  if (!selectedCase || benchmarks.length === 0) return "0.0";
  return percentileRank(safeNumber(selectedCase[key]), benchmarks, (item) => safeNumber(item.metadata[key])).toFixed(1);
}

function ScoreRow({ label, value }: { label: string; value: string }) {
  return (
    <div className="flex items-center justify-between rounded-md border border-border/60 bg-background/40 px-3 py-2">
      <span>{label}</span>
      <span className="font-medium text-foreground">{value}</span>
    </div>
  );
}

function DecisionStat({ label, value }: { label: string; value: string }) {
  return (
    <div className="rounded-md border border-border/60 bg-background/40 px-3 py-2">
      <p className="text-xs text-muted-foreground">{label}</p>
      <p className="text-lg font-semibold text-foreground">{value}</p>
    </div>
  );
}

function avg(values: number[]): number {
  if (values.length === 0) return 0;
  return values.reduce((sum, value) => sum + value, 0) / values.length;
}

function GeneratedDimensionCard({
  label,
  result,
}: {
  label: string;
  result: GeneratedQualitativeAssessment["dimensions"][QualitativeDimensionKey];
}) {
  return (
    <div className="rounded-md border border-border/60 bg-background/40 p-3">
      <div className="flex flex-wrap items-center justify-between gap-2">
        <p className="font-medium text-foreground">{label}</p>
        <div className="flex items-center gap-2">
          <Badge variant="outline">Score {result.score_1_5}/5</Badge>
          <Badge variant={result.confidence_0_1 >= 0.7 ? "success" : "warning"}>
            Confidence {(result.confidence_0_1 * 100).toFixed(0)}%
          </Badge>
        </div>
      </div>
      <p className="mt-2 text-sm text-muted-foreground">{result.rationale}</p>
      <div className="mt-2 flex flex-wrap gap-1">
        {result.source_record_ids.length > 0 ? (
          result.source_record_ids.map((sourceId) => (
            <Badge key={sourceId} variant="outline" className="font-mono">
              {sourceId}
            </Badge>
          ))
        ) : (
          <span className="text-xs text-amber-300">No source_record_ids linked</span>
        )}
      </div>
    </div>
  );
}

function InputRow({
  label,
  value,
  onChange,
  placeholder,
}: {
  label: string;
  value: string;
  onChange: (value: string) => void;
  placeholder?: string;
}) {
  return (
    <label className="grid gap-1 text-sm">
      <span className="text-muted-foreground">{label}</span>
      <input
        className="rounded-md border border-input bg-background px-3 py-2 text-sm outline-none ring-offset-background focus-visible:ring-2 focus-visible:ring-ring"
        value={value}
        placeholder={placeholder}
        onChange={(event) => onChange(event.target.value)}
      />
    </label>
  );
}

function SelectRow({
  label,
  value,
  onChange,
  options,
}: {
  label: string;
  value: string;
  onChange: (value: string) => void;
  options: Array<{ value: string; label: string }>;
}) {
  return (
    <label className="grid gap-1 text-sm">
      <span className="text-muted-foreground">{label}</span>
      <select
        className="rounded-md border border-input bg-background px-3 py-2 text-sm outline-none ring-offset-background focus-visible:ring-2 focus-visible:ring-ring"
        value={value}
        onChange={(event) => onChange(event.target.value)}
      >
        {options.length === 0 ? <option value="">No options available</option> : null}
        {options.map((option) => (
          <option key={option.value} value={option.value}>
            {option.label}
          </option>
        ))}
      </select>
    </label>
  );
}
