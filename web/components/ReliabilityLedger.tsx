import type { EvalResultsData, SourceManifestData } from "@/types/artifacts";
import { Badge } from "@/components/ui/badge";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { EmptyState } from "@/components/EmptyState";

interface ReliabilityLedgerProps {
  manifest: SourceManifestData | null;
  evalResults: EvalResultsData | null;
}

interface ConnectorReliability {
  connectorName: string;
  backend: string;
  recordCount: number;
  connectionStatus: string;
  warningCount: number;
  errorCount: number;
  fallbackDetected: boolean;
  mockFallbackDetected: boolean;
  attributedRecordCount: number;
}

export function ReliabilityLedger({ manifest, evalResults }: ReliabilityLedgerProps) {
  const entries = manifest?.entries ?? [];
  if (entries.length === 0) {
    return (
      <EmptyState
        title="No reliability ledger"
        description="source_manifest.json is missing or does not include connector entries."
      />
    );
  }

  const promptRuns = manifest?.benchmark_plan?.mcp_prompt_runs ?? [];
  const attributedByConnector = new Map<string, Set<string>>();
  for (const run of promptRuns) {
    if (!run.connector_name) continue;
    const existing = attributedByConnector.get(run.connector_name) ?? new Set<string>();
    for (const sourceId of run.source_record_ids ?? []) {
      if (sourceId?.trim()) existing.add(sourceId);
    }
    attributedByConnector.set(run.connector_name, existing);
  }

  const rows: ConnectorReliability[] = entries.map((entry) => {
    const warnings = entry.warnings ?? [];
    const errors = entry.errors ?? [];
    const backend = (entry.backend_used ?? "unknown").toLowerCase();
    const mockFallbackDetected = warnings.some((warning) => warning.includes("MOCK/SYNTHETIC fallback"));
    const fallbackDetected = mockFallbackDetected || backend.includes("fallback");
    const attributedSet = attributedByConnector.get(entry.connector_name);
    return {
      connectorName: entry.connector_name,
      backend,
      recordCount: entry.record_count,
      connectionStatus: entry.connection_status ?? "unknown",
      warningCount: warnings.length,
      errorCount: errors.length,
      fallbackDetected,
      mockFallbackDetected,
      attributedRecordCount: attributedSet?.size ?? 0,
    };
  });

  const fallbackCount = rows.filter((row) => row.fallbackDetected).length;
  const mockFallbackCount = rows.filter((row) => row.mockFallbackDetected).length;
  const connectorsWithAttribution = rows.filter((row) => row.attributedRecordCount > 0).length;
  const totalRecords = rows.reduce((sum, row) => sum + row.recordCount, 0);
  const totalAttributed = rows.reduce((sum, row) => sum + row.attributedRecordCount, 0);
  const reliabilityContractPassed = evalResults?.metrics?.benchmark_contract_passed === true;

  return (
    <div className="space-y-4">
      <Card>
        <CardHeader>
          <CardTitle>Reliability ledger</CardTitle>
        </CardHeader>
        <CardContent className="space-y-3">
          <div className="flex flex-wrap gap-2">
            <Badge variant={reliabilityContractPassed ? "success" : "warning"}>
              Contract reliability: {reliabilityContractPassed ? "pass" : "review needed"}
            </Badge>
            <Badge variant={fallbackCount === 0 ? "success" : "warning"}>
              {fallbackCount} Fallback Path connector{fallbackCount === 1 ? "" : "s"}
            </Badge>
            <Badge variant={mockFallbackCount === 0 ? "success" : "warning"}>
              {mockFallbackCount} Mock/Synthetic Fallback connector{mockFallbackCount === 1 ? "" : "s"}
            </Badge>
            <Badge variant={connectorsWithAttribution > 0 ? "success" : "warning"}>
              {connectorsWithAttribution}/{rows.length} connectors with Attributed Source IDs
            </Badge>
            <Badge variant="outline">
              Records: {totalRecords} sourced · {totalAttributed} Attributed Source IDs
            </Badge>
          </div>
          <p className="text-sm text-muted-foreground">
            This ledger explains data reality. Backend shows where each connector pulled data from,
            reliability flags show live vs fallback behavior, and attributed IDs show whether source
            records are actually referenced in framed outputs.
          </p>
          <p className="text-xs text-muted-foreground">
            Live Path = direct retrieval without fallback warnings. Fallback Path = degraded path. Mock/Synthetic
            fallback = synthetic placeholder behavior and should be treated as non-production evidence.
          </p>
        </CardContent>
      </Card>

      <div className="overflow-x-auto rounded-lg border border-border">
        <table className="w-full text-left text-sm">
          <thead className="border-b border-border bg-muted/30 text-xs uppercase text-muted-foreground">
            <tr>
              <th className="px-4 py-3">Connector</th>
              <th className="px-4 py-3">Backend</th>
              <th className="px-4 py-3">Records</th>
              <th className="px-4 py-3">Attributed IDs</th>
              <th className="px-4 py-3">Connection</th>
              <th className="px-4 py-3">Warnings</th>
              <th className="px-4 py-3">Errors</th>
              <th className="px-4 py-3">Path status</th>
            </tr>
          </thead>
          <tbody>
            {rows.map((row) => (
              <tr key={row.connectorName} className="border-b border-border/60">
                <td className="px-4 py-3 font-mono text-xs">{row.connectorName}</td>
                <td className="px-4 py-3 font-mono text-xs">{row.backend}</td>
                <td className="px-4 py-3 font-mono text-xs">{row.recordCount}</td>
                <td className="px-4 py-3 font-mono text-xs">{row.attributedRecordCount}</td>
                <td className="px-4 py-3 capitalize">{row.connectionStatus}</td>
                <td className="px-4 py-3 font-mono text-xs">{row.warningCount}</td>
                <td className="px-4 py-3 font-mono text-xs">{row.errorCount}</td>
                <td className="px-4 py-3">
                  <Badge variant={row.fallbackDetected ? "warning" : "success"}>
                    {row.fallbackDetected ? "Fallback Path" : "Live Path"}
                  </Badge>
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
    </div>
  );
}
