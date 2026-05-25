"use client";

import Link from "next/link";
import { useMemo, useState } from "react";
import { ArrowLeft, FlaskConical, Search, ShieldAlert, Target } from "lucide-react";
import type { CaseMetadata } from "@/types/artifacts";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card";

interface DealEvaluationWorkflowProps {
  cases: CaseMetadata[];
}

interface QualitativeRubric {
  science: number;
  differentiation: number;
  regulatory: number;
  execution: number;
  strategicFit: number;
}

const DEFAULT_RUBRIC: QualitativeRubric = {
  science: 3,
  differentiation: 3,
  regulatory: 3,
  execution: 3,
  strategicFit: 3,
};

export function DealEvaluationWorkflow({ cases }: DealEvaluationWorkflowProps) {
  const candidateCases = useMemo(() => cases.filter((item) => !item.is_benchmark), [cases]);
  const benchmarkCases = useMemo(() => cases.filter((item) => item.is_benchmark), [cases]);
  const benchmarkCohorts = useMemo(
    () =>
      Array.from(
        new Set(benchmarkCases.map((item) => item.benchmark_cohort).filter((item): item is string => !!item)),
      ).sort(),
    [benchmarkCases],
  );

  const [query, setQuery] = useState("");
  const [stageFilter, setStageFilter] = useState("all");
  const [cohortFilter, setCohortFilter] = useState("all");
  const [selectedCaseId, setSelectedCaseId] = useState(candidateCases[0]?.case_id ?? "");
  const [rubric, setRubric] = useState<QualitativeRubric>(DEFAULT_RUBRIC);

  const stageOptions = useMemo(
    () =>
      Array.from(
        new Set(candidateCases.map((item) => item.maturity_stage).filter((item): item is string => !!item)),
      ).sort(),
    [candidateCases],
  );

  const filteredCandidates = useMemo(() => {
    const normalizedQuery = query.trim().toLowerCase();
    return candidateCases.filter((item) => {
      if (stageFilter !== "all" && item.maturity_stage !== stageFilter) return false;
      if (!normalizedQuery) return true;
      const fields = [
        item.display_name,
        item.case_id,
        item.target_name,
        item.indication_name,
        item.input_profile?.biology?.modality,
      ]
        .filter((value): value is string => !!value)
        .map((value) => value.toLowerCase());
      return fields.some((value) => value.includes(normalizedQuery));
    });
  }, [candidateCases, query, stageFilter]);

  const selectedCase = useMemo(
    () =>
      filteredCandidates.find((item) => item.case_id === selectedCaseId) ??
      candidateCases.find((item) => item.case_id === selectedCaseId) ??
      filteredCandidates[0] ??
      candidateCases[0] ??
      null,
    [candidateCases, filteredCandidates, selectedCaseId],
  );

  const activeBenchmarks = useMemo(() => {
    if (cohortFilter === "all") return benchmarkCases;
    return benchmarkCases.filter((item) => item.benchmark_cohort === cohortFilter);
  }, [benchmarkCases, cohortFilter]);

  const nearestBenchmarks = useMemo(() => {
    if (!selectedCase) return [];
    return [...activeBenchmarks]
      .sort((a, b) => similarityScore(b, selectedCase) - similarityScore(a, selectedCase))
      .slice(0, 5);
  }, [activeBenchmarks, selectedCase]);

  const quantScore = useMemo(() => {
    if (!selectedCase || activeBenchmarks.length === 0) return 0;
    const confidencePercentile = percentileRank(selectedCase.confidence_score ?? 0, activeBenchmarks, (item) =>
      safeNumber(item.confidence_score),
    );
    const comparabilityPercentile = percentileRank(
      selectedCase.comparability_score ?? 0,
      activeBenchmarks,
      (item) => safeNumber(item.comparability_score),
    );
    const recordsPercentile = percentileRank(selectedCase.total_records ?? 0, activeBenchmarks, (item) =>
      safeNumber(item.total_records),
    );
    const connectorsPercentile = percentileRank(
      selectedCase.connectors_with_records ?? 0,
      activeBenchmarks,
      (item) => safeNumber(item.connectors_with_records),
    );
    return (
      confidencePercentile * 0.35 +
      comparabilityPercentile * 0.25 +
      recordsPercentile * 0.2 +
      connectorsPercentile * 0.2
    );
  }, [activeBenchmarks, selectedCase]);

  const qualitativeScore = useMemo(() => {
    const values = Object.values(rubric);
    const average = values.reduce((sum, value) => sum + value, 0) / values.length;
    return ((average - 1) / 4) * 100;
  }, [rubric]);

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

  const finalScore = Math.max(0, Math.min(100, quantScore * 0.45 + qualitativeScore * 0.35 + (100 - riskPenalty) * 0.2));
  const recommendation = finalScore >= 75 ? "Prioritize" : finalScore >= 60 ? "Watchlist" : "Deprioritize";

  const mockedCandidate = Boolean(selectedCase?.mocked_api_calls) || safeNumber(selectedCase?.fallback_connector_count) > 0;
  const mockedBenchmarks = activeBenchmarks.some(
    (item) => Boolean(item.mocked_api_calls) || safeNumber(item.fallback_connector_count) > 0,
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
          Evaluate a target case against benchmark peers with both percentile-based quantitative metrics and an explicit
          qualitative rubric.
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
                value: item.case_id,
                label: `${item.target_name} · ${item.indication_name}`,
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
            <CardDescription>Score each dimension from 1 to 5 with your diligence context.</CardDescription>
          </CardHeader>
          <CardContent className="space-y-3 text-sm">
            <RubricSlider label="Science quality" value={rubric.science} onChange={(value) => setRubric((prev) => ({ ...prev, science: value }))} />
            <RubricSlider
              label="Differentiation and moat"
              value={rubric.differentiation}
              onChange={(value) => setRubric((prev) => ({ ...prev, differentiation: value }))}
            />
            <RubricSlider
              label="Regulatory clarity"
              value={rubric.regulatory}
              onChange={(value) => setRubric((prev) => ({ ...prev, regulatory: value }))}
            />
            <RubricSlider
              label="Execution readiness"
              value={rubric.execution}
              onChange={(value) => setRubric((prev) => ({ ...prev, execution: value }))}
            />
            <RubricSlider
              label="Strategic fit"
              value={rubric.strategicFit}
              onChange={(value) => setRubric((prev) => ({ ...prev, strategicFit: value }))}
            />
            <div className="rounded-md border border-border/60 bg-background/40 px-3 py-2">
              <p className="font-medium text-foreground">Qual composite: {qualitativeScore.toFixed(1)} / 100</p>
            </div>
          </CardContent>
        </Card>
      </div>

      <Card className="border-border/80 bg-card/80">
        <CardHeader>
          <CardTitle>Step 5: Prioritization decision</CardTitle>
          <CardDescription>Final recommendation blends quant score, qual rubric, and explicit risk penalties.</CardDescription>
        </CardHeader>
        <CardContent className="space-y-4">
          <div className="grid gap-3 md:grid-cols-4">
            <DecisionStat label="Quant score (45%)" value={quantScore.toFixed(1)} />
            <DecisionStat label="Qual score (35%)" value={qualitativeScore.toFixed(1)} />
            <DecisionStat label="Risk adjustment (20%)" value={`${(100 - riskPenalty).toFixed(1)}`} />
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
                  <li key={item.case_id}>
                    {item.target_name} / {item.indication_name} ({item.maturity_stage})
                  </li>
                ))}
              </ul>
            )}
          </div>

          {selectedCase ? (
            <Button asChild variant="outline">
              <Link href={`/cases/${selectedCase.case_id}`}>Open selected case dashboard</Link>
            </Button>
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
  selectedCase: CaseMetadata | null,
  benchmarks: CaseMetadata[],
  key: "confidence_score" | "comparability_score" | "total_records" | "connectors_with_records",
): string {
  if (!selectedCase || benchmarks.length === 0) return "0.0";
  return percentileRank(safeNumber(selectedCase[key]), benchmarks, (item) => safeNumber(item[key])).toFixed(1);
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

function RubricSlider({
  label,
  value,
  onChange,
}: {
  label: string;
  value: number;
  onChange: (value: number) => void;
}) {
  return (
    <label className="grid gap-1 text-sm">
      <span className="flex items-center justify-between text-muted-foreground">
        {label}
        <span className="font-medium text-foreground">{value}</span>
      </span>
      <input
        type="range"
        min={1}
        max={5}
        step={1}
        value={value}
        className="accent-teal-500"
        onChange={(event) => onChange(Number(event.target.value))}
      />
    </label>
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
