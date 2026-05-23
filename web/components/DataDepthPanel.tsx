import type { CasePacket } from "@/types/artifacts";
import { Badge } from "@/components/ui/badge";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { EmptyState } from "@/components/EmptyState";
import { formatConfidence } from "@/lib/utils";

interface DataDepthPanelProps {
  packet: CasePacket;
}

export function DataDepthPanel({ packet }: DataDepthPanelProps) {
  const audit = packet.depthAudit;
  if (!audit || audit.byConnector.length === 0) {
    return (
      <EmptyState
        title="No depth audit available"
        description="Depth metrics require source manifest entries and connector payloads."
      />
    );
  }

  const overall = audit.overall;
  const connectorsWithoutRaw = overall.connectorsAudited - overall.connectorsWithRawPayload;

  return (
    <div className="space-y-4">
      <Card>
        <CardHeader>
          <CardTitle>Data depth audit</CardTitle>
        </CardHeader>
        <CardContent className="space-y-3">
          <div className="flex flex-wrap gap-2">
            <Badge
              variant={overall.deepCoverage >= 0.6 ? "success" : overall.deepCoverage >= 0.3 ? "warning" : "danger"}
            >
              Deep coverage: {formatConfidence(overall.deepCoverage)}
            </Badge>
            <Badge variant="outline">
              Deep records: {overall.deepRecords}/{overall.totalRecords}
            </Badge>
            <Badge variant={connectorsWithoutRaw === 0 ? "success" : "warning"}>
              Raw payload coverage: {overall.connectorsWithRawPayload}/{overall.connectorsAudited}
            </Badge>
          </div>
          <p className="text-sm text-muted-foreground">
            Deep coverage counts records that include connector-specific rich fields (for example abstracts, protocol
            details, mechanism annotations, or label sections), not just shallow IDs/titles.
          </p>
          <p className="text-xs text-muted-foreground">
            How to read: high deep coverage means the platform retrieved substantive content, not
            only index metadata. Missing raw payload means depth could not be fully audited for that connector.
          </p>
        </CardContent>
      </Card>

      <div className="overflow-x-auto rounded-lg border border-border">
        <table className="w-full text-left text-sm">
          <thead className="border-b border-border bg-muted/30 text-xs uppercase text-muted-foreground">
            <tr>
              <th className="px-4 py-3">Connector</th>
              <th className="px-4 py-3">Records sourced</th>
              <th className="px-4 py-3">Deep records</th>
              <th className="px-4 py-3">Deep coverage</th>
              <th className="px-4 py-3">Attributed Source IDs</th>
              <th className="px-4 py-3">Raw payload</th>
              <th className="px-4 py-3">Depth fields sampled</th>
            </tr>
          </thead>
          <tbody>
            {audit.byConnector.map((row) => (
              <tr key={row.connectorName} className="border-b border-border/60">
                <td className="px-4 py-3 font-mono text-xs">{row.connectorName}</td>
                <td className="px-4 py-3 font-mono text-xs">{row.recordsSourced}</td>
                <td className="px-4 py-3 font-mono text-xs">{row.recordsWithDeepFields}</td>
                <td className="px-4 py-3 font-mono text-xs">{formatConfidence(row.deepCoverage)}</td>
                <td className="px-4 py-3 font-mono text-xs">{row.attributedRecordCount}</td>
                <td className="px-4 py-3">
                  <Badge variant={row.rawPayloadPresent ? "success" : "warning"}>
                    {row.rawPayloadPresent ? "present" : "missing"}
                  </Badge>
                </td>
                <td className="px-4 py-3 text-xs text-muted-foreground">
                  {row.sampledDeepFields.join(", ")}
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
    </div>
  );
}
