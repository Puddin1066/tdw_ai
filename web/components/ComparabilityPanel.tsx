import type { EvalResultsData, SourceManifestData } from "@/types/artifacts";
import { Badge } from "@/components/ui/badge";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { EmptyState } from "@/components/EmptyState";
import { formatConfidence } from "@/lib/utils";

interface ComparabilityPanelProps {
  evalResults: EvalResultsData | null;
  sourceManifest: SourceManifestData | null;
}

interface GateStatus {
  label: string;
  passed: boolean;
  detail: string;
}

const THRESHOLDS = {
  minConnectorsWithRecords: 3,
  minTotalRecords: 10,
  maxFallbackEntries: 0,
  maxGenericRiskTitles: 0,
};

export function ComparabilityPanel({ evalResults, sourceManifest }: ComparabilityPanelProps) {
  if (!evalResults) {
    return (
      <EmptyState
        title="No comparability data"
        description="eval_results.json is required to validate benchmark and case comparability."
      />
    );
  }

  const metrics = evalResults.metrics ?? {};
  const contractScore = metrics.benchmark_contract_score;
  const contractPassed = metrics.benchmark_contract_passed === true;
  const connectorsWithRecords = metrics.contract_connectors_with_records ?? 0;
  const totalRecords = metrics.contract_total_records ?? 0;
  const fallbackEntries = metrics.contract_fallback_entries ?? 0;
  const genericRiskTitles = metrics.contract_generic_risk_titles ?? 0;
  const brokenEvidenceLinks = metrics.contract_broken_evidence_links ?? 0;
  const duplicateRiskTitles = metrics.contract_duplicate_risk_titles ?? 0;

  const entries = sourceManifest?.entries ?? [];
  const mockWarningCount = entries.filter((entry) =>
    (entry.warnings ?? []).some((warning) => warning.includes("MOCK/SYNTHETIC fallback")),
  ).length;

  const gates: GateStatus[] = [
    {
      label: "Benchmark contract evaluator",
      passed: contractPassed,
      detail: contractPassed ? "Passed" : "Failed or missing",
    },
    {
      label: "Connectors with records",
      passed: connectorsWithRecords >= THRESHOLDS.minConnectorsWithRecords,
      detail: `${connectorsWithRecords} / minimum ${THRESHOLDS.minConnectorsWithRecords}`,
    },
    {
      label: "Total records fetched",
      passed: totalRecords >= THRESHOLDS.minTotalRecords,
      detail: `${totalRecords} / minimum ${THRESHOLDS.minTotalRecords}`,
    },
    {
      label: "Fallback connectors",
      passed: fallbackEntries <= THRESHOLDS.maxFallbackEntries,
      detail: `${fallbackEntries} / maximum ${THRESHOLDS.maxFallbackEntries}`,
    },
    {
      label: "Generic risk titles",
      passed: genericRiskTitles <= THRESHOLDS.maxGenericRiskTitles,
      detail: `${genericRiskTitles} / maximum ${THRESHOLDS.maxGenericRiskTitles}`,
    },
    {
      label: "Broken evidence links",
      passed: brokenEvidenceLinks === 0,
      detail: `${brokenEvidenceLinks} / required 0`,
    },
    {
      label: "Duplicate risk titles",
      passed: duplicateRiskTitles === 0,
      detail: `${duplicateRiskTitles} / required 0`,
    },
  ];

  const failedCount = gates.filter((gate) => !gate.passed).length;

  return (
    <div className="space-y-4">
      <Card>
        <CardHeader>
          <CardTitle>Comparability contract</CardTitle>
        </CardHeader>
        <CardContent className="space-y-3">
          <div className="flex flex-wrap gap-2">
            <Badge variant={contractPassed ? "success" : "danger"}>
              {contractPassed ? "Contract pass" : "Contract fail"}
            </Badge>
            {typeof contractScore === "number" ? (
              <Badge variant="outline">Score: {formatConfidence(contractScore)}</Badge>
            ) : (
              <Badge variant="outline">Score: n/a</Badge>
            )}
            <Badge variant={failedCount === 0 ? "success" : "warning"}>
              {failedCount} failed gate{failedCount === 1 ? "" : "s"}
            </Badge>
            <Badge variant={mockWarningCount === 0 ? "success" : "warning"}>
              {mockWarningCount} Mock/Synthetic Fallback warning{mockWarningCount === 1 ? "" : "s"}
            </Badge>
          </div>
          <p className="text-sm text-muted-foreground">
            This panel enforces a single evaluation standard across benchmarks and future live cases so outputs are
            comparable and auditable.
          </p>
          <p className="text-xs text-muted-foreground">
            How to read: all gates should pass for decision-grade comparison. Gate thresholds are
            policy values enforced during publish in live mode, not ad hoc UI-only checks.
          </p>
        </CardContent>
      </Card>

      <div className="grid gap-3 md:grid-cols-2">
        {gates.map((gate) => (
          <Card key={gate.label} className={gate.passed ? undefined : "border-cockpit-rose/40"}>
            <CardHeader className="pb-2">
              <CardTitle className="text-sm">{gate.label}</CardTitle>
            </CardHeader>
            <CardContent className="space-y-2 text-sm">
              <Badge variant={gate.passed ? "success" : "danger"}>
                {gate.passed ? "pass" : "fail"}
              </Badge>
              <p className="font-mono text-xs text-muted-foreground">{gate.detail}</p>
            </CardContent>
          </Card>
        ))}
      </div>

      <Card>
        <CardHeader>
          <CardTitle className="text-sm">Interpretation</CardTitle>
        </CardHeader>
        <CardContent className="text-sm text-muted-foreground">
          {failedCount === 0
            ? "This case meets the comparability contract. Data fetch depth, risk framing specificity, and evidence linkage are within policy."
            : "This case does not meet the comparability contract. Review failed gates before comparing this case to benchmark outputs."}
        </CardContent>
      </Card>
    </div>
  );
}
