import type { DiligenceReportData, EvalResultsData, RiskMapData } from "@/types/artifacts";
import { Badge } from "@/components/ui/badge";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { EmptyState } from "@/components/EmptyState";
import { formatConfidence } from "@/lib/utils";

export interface ExecutiveSnapshotProps {
  report: DiligenceReportData | null;
  riskMap: RiskMapData | null;
  evalResults: EvalResultsData | null;
}

export function ExecutiveSnapshot({ report, riskMap, evalResults }: ExecutiveSnapshotProps) {
  if (!report) {
    return (
      <EmptyState
        title="No diligence report"
        description="diligence_report.json is missing or could not be loaded for this case."
      />
    );
  }

  const topRisks = riskMap?.risks?.slice(0, 3) ?? [];

  return (
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
  );
}

function MetricRow({ label, value }: { label: string; value: string }) {
  return (
    <div className="flex justify-between gap-4">
      <span className="text-muted-foreground">{label}</span>
      <span className="font-mono font-medium">{value}</span>
    </div>
  );
}
