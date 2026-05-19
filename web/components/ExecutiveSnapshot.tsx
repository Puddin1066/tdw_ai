import type {
  ClinicalTrialRecord,
  DiligenceReportData,
  EvalResultsData,
  EvidenceRow,
  RiskMapData,
  SourceManifestData,
} from "@/types/artifacts";
import { Badge } from "@/components/ui/badge";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { EmptyState } from "@/components/EmptyState";
import { formatConfidence } from "@/lib/utils";

export interface ExecutiveSnapshotProps {
  report: DiligenceReportData | null;
  riskMap: RiskMapData | null;
  evalResults: EvalResultsData | null;
  evidenceRows: EvidenceRow[];
  sourceManifest: SourceManifestData | null;
  clinicalTrials: ClinicalTrialRecord[];
}

export function ExecutiveSnapshot({
  report,
  riskMap,
  evalResults,
  evidenceRows,
  sourceManifest,
  clinicalTrials,
}: ExecutiveSnapshotProps) {
  if (!report) {
    return (
      <EmptyState
        title="No diligence report"
        description="diligence_report.json is missing or could not be loaded for this case."
      />
    );
  }

  const topRisks = riskMap?.risks?.slice(0, 3) ?? [];
  const topClaims = [...evidenceRows]
    .sort((a, b) => b.confidence - a.confidence)
    .slice(0, 3);
  const decision = deriveRecommendation(report, evalResults, topRisks.length);
  const trialReality = summarizeTrialReality(sourceManifest, clinicalTrials.length, evalResults);
  const nextActions = buildNextActions({
    evalResults,
    topRisksCount: topRisks.length,
    trialCount: clinicalTrials.length,
    liveFallbackCount: trialReality.fallbackConnectors,
  });

  return (
    <div className="space-y-4">
      <Card>
        <CardHeader>
          <CardTitle>Decision layer</CardTitle>
        </CardHeader>
        <CardContent className="space-y-4">
          <div className="flex flex-wrap items-center gap-2">
            <Badge
              variant={decision.recommendation === "advance" ? "default" : "outline"}
              className="capitalize"
            >
              Recommendation: {decision.recommendation}
            </Badge>
            <Badge variant="secondary">Confidence band: {decision.band}</Badge>
            <Badge variant="outline">
              Eval status: {evalResults?.overall_passed ? "pass" : "needs review"}
            </Badge>
          </div>
          <p className="text-sm text-muted-foreground">{decision.reason}</p>
          {topClaims.length > 0 ? (
            <div className="space-y-2">
              <p className="text-sm font-medium">Top evidence-backed claims</p>
              <ul className="space-y-2 text-sm">
                {topClaims.map((row) => (
                  <li key={row.evidence_id} className="rounded-md border border-border/60 p-2">
                    <p className="font-medium text-foreground">{row.claim_text}</p>
                    <p className="mt-1 text-xs text-muted-foreground">
                      {row.claim_type} · {row.support_status} · {formatConfidence(row.confidence)} ·{" "}
                      {row.source_record_ids.length} source link
                      {row.source_record_ids.length === 1 ? "" : "s"}
                    </p>
                  </li>
                ))}
              </ul>
            </div>
          ) : null}
        </CardContent>
      </Card>

      <div className="grid gap-4 lg:grid-cols-3">
      <Card className="lg:col-span-2">
        <CardHeader>
          <CardTitle>Executive conclusion</CardTitle>
        </CardHeader>
        <CardContent className="space-y-4">
          <p className="text-sm leading-relaxed text-foreground/90">
            {report.conclusion ??
              report.executive_summary ??
              (report as { summary?: string }).summary ??
              report.title}
          </p>
          {report.executive_summary ? (
            <p className="text-sm text-muted-foreground">{report.executive_summary}</p>
          ) : null}
          <div className="flex flex-wrap gap-2">
            <Badge variant="outline">
              Confidence:{" "}
              {typeof report.overall_confidence === "number"
                ? `${Math.round(report.overall_confidence * 100)}%`
                : String((report as { confidence?: string }).confidence ?? "—")}
            </Badge>
            {report.maturity_stage ? (
              <Badge variant="secondary">Maturity: {report.maturity_stage}</Badge>
            ) : null}
          </div>
          {report.sections && report.sections.length > 0 ? (
            <ul className="list-inside list-disc space-y-1 text-sm text-muted-foreground">
              {report.sections.slice(0, 4).map((section) => (
                <li key={section.title ?? (section as { heading?: string }).heading}>
                  {section.title ?? (section as { heading?: string }).heading}
                </li>
              ))}
            </ul>
          ) : null}
        </CardContent>
      </Card>

      <div className="space-y-4">
        <Card>
          <CardHeader>
            <CardTitle className="text-base">Eval snapshot</CardTitle>
          </CardHeader>
          <CardContent className="space-y-2 text-sm">
            {evalResults ? (
              <>
                <MetricRow
                  label="Overall"
                  value={evalResults.overall_passed ? "Pass" : "Fail"}
                />
                <MetricRow
                  label="Aggregate score"
                  value={formatConfidence(evalResults.aggregate_score)}
                />
                <MetricRow
                  label="Citation fidelity"
                  value={formatConfidence(evalResults.metrics?.citation_fidelity_score ?? 0)}
                />
                <MetricRow
                  label="Unsupported claims"
                  value={String(evalResults.metrics?.unsupported_claim_count ?? 0)}
                />
              </>
            ) : (
              <p className="text-muted-foreground">Eval results not available.</p>
            )}
          </CardContent>
        </Card>

        <Card>
          <CardHeader>
            <CardTitle className="text-base">Trial reality check</CardTitle>
          </CardHeader>
          <CardContent className="space-y-2 text-sm">
            <MetricRow label="Trials in packet" value={String(trialReality.trialCount)} />
            <MetricRow label="Live connectors" value={String(trialReality.liveConnectors)} />
            <MetricRow
              label="Fixture fallback connectors"
              value={String(trialReality.fallbackConnectors)}
            />
            <MetricRow
              label="Hallucinated trial refs"
              value={String(trialReality.hallucinatedTrialCount)}
            />
            <p className="text-xs text-muted-foreground">{trialReality.note}</p>
          </CardContent>
        </Card>

        <Card>
          <CardHeader>
            <CardTitle className="text-base">Top risks</CardTitle>
          </CardHeader>
          <CardContent>
            {topRisks.length > 0 ? (
              <ul className="space-y-2 text-sm">
                {topRisks.map((risk) => (
                  <li key={risk.risk_id} className="border-l-2 border-cockpit-amber/60 pl-3">
                    <span className="font-medium">{risk.title}</span>
                    <span className="ml-2 text-xs capitalize text-muted-foreground">
                      {risk.category}
                    </span>
                  </li>
                ))}
              </ul>
            ) : (
              <p className="text-sm text-muted-foreground">No risk map data.</p>
            )}
          </CardContent>
        </Card>
      </div>
      </div>

      <Card>
        <CardHeader>
          <CardTitle className="text-base">Next diligence actions</CardTitle>
        </CardHeader>
        <CardContent>
          <ul className="list-inside list-disc space-y-1 text-sm text-foreground/90">
            {nextActions.map((action) => (
              <li key={action}>{action}</li>
            ))}
          </ul>
        </CardContent>
      </Card>
    </div>
  );
}

function deriveRecommendation(
  report: DiligenceReportData,
  evalResults: EvalResultsData | null,
  topRiskCount: number,
): { recommendation: "advance" | "watchlist" | "deprioritize"; band: string; reason: string } {
  const confidence = typeof report.overall_confidence === "number" ? report.overall_confidence : 0;
  const evalPassed = evalResults?.overall_passed ?? false;
  const hallucinatedTrials = evalResults?.metrics?.hallucinated_trial_count ?? 0;
  if (!evalPassed || hallucinatedTrials > 0) {
    return {
      recommendation: "watchlist",
      band: "low-to-medium",
      reason:
        "Evaluation flags exist (for example trial/citation consistency). Resolve data integrity issues before recommending advancement.",
    };
  }
  if (confidence >= 0.7 && topRiskCount <= 2) {
    return {
      recommendation: "advance",
      band: "medium-to-high",
      reason:
        "Evidence confidence is above baseline and no major evaluation blockers were detected in this packet.",
    };
  }
  if (confidence < 0.45) {
    return {
      recommendation: "deprioritize",
      band: "low",
      reason:
        "Current evidence support and confidence are weak; resources are likely better allocated to higher-conviction programs.",
    };
  }
  return {
    recommendation: "watchlist",
    band: "medium",
    reason:
      "Signal exists but requires additional validation on trial relevance and translational risk before a stronger decision.",
  };
}

function summarizeTrialReality(
  sourceManifest: SourceManifestData | null,
  trialCount: number,
  evalResults: EvalResultsData | null,
): {
  trialCount: number;
  liveConnectors: number;
  fallbackConnectors: number;
  hallucinatedTrialCount: number;
  note: string;
} {
  const entries = sourceManifest?.entries ?? [];
  const liveConnectors = entries.filter((entry) =>
    (entry.warnings ?? []).every((warning) => !warning.includes("MOCK/SYNTHETIC fallback")),
  ).length;
  const fallbackConnectors = entries.length - liveConnectors;
  const hallucinatedTrialCount = evalResults?.metrics?.hallucinated_trial_count ?? 0;
  const note =
    fallbackConnectors > 0
      ? "Some connectors used fixture fallback; treat trial coverage as partial."
      : "All loaded connector paths reported live mode without fixture fallback warnings.";
  return {
    trialCount,
    liveConnectors,
    fallbackConnectors,
    hallucinatedTrialCount,
    note,
  };
}

function buildNextActions(params: {
  evalResults: EvalResultsData | null;
  topRisksCount: number;
  trialCount: number;
  liveFallbackCount: number;
}): string[] {
  const actions: string[] = [];
  if ((params.evalResults?.metrics?.hallucinated_trial_count ?? 0) > 0) {
    actions.push("Resolve NCT citation mismatches between diligence_report and clinical_trials artifacts.");
  }
  if (params.liveFallbackCount > 0) {
    actions.push(
      "Replace fixture connector fallbacks with live endpoints for highest-impact sources (ClinicalTrials.gov first).",
    );
  }
  if (params.trialCount < 3) {
    actions.push("Expand clinical trial retrieval query breadth to improve coverage of active programs.");
  }
  if (params.topRisksCount > 0) {
    actions.push("Map each top risk to one mitigation experiment and expected confidence impact.");
  }
  if ((params.evalResults?.metrics?.unsupported_claim_count ?? 0) > 0) {
    actions.push("Trim unsupported claims and regenerate report with stricter evidence-only assertions.");
  }
  if (actions.length < 3) {
    actions.push("Run one more live packet and compare recommendation stability across runs.");
    actions.push("Add a reviewer sign-off note explaining what evidence could flip the recommendation.");
  }
  return actions.slice(0, 5);
}

function MetricRow({ label, value }: { label: string; value: string }) {
  return (
    <div className="flex justify-between gap-4">
      <span className="text-muted-foreground">{label}</span>
      <span className="font-mono font-medium">{value}</span>
    </div>
  );
}
