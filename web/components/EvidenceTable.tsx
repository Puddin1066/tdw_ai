import type { EvidenceRow } from "@/types/artifacts";
import { Badge } from "@/components/ui/badge";
import { EmptyState } from "@/components/EmptyState";
import { formatConfidence, pmidUrl } from "@/lib/utils";

export interface EvidenceTableProps {
  evidenceRows: EvidenceRow[];
}

const statusVariant: Record<string, "success" | "warning" | "danger" | "outline"> = {
  supported: "success",
  partially_supported: "warning",
  unsupported: "danger",
  contradicted: "danger",
  insufficient_evidence: "outline",
};

export function EvidenceTable({ evidenceRows }: EvidenceTableProps) {
  if (evidenceRows.length === 0) {
    return (
      <EmptyState
        title="No evidence rows"
        description="evidence_table.json contains no claim-level evidence for this case."
      />
    );
  }

  return (
    <div className="overflow-x-auto rounded-lg border border-border">
      <table className="w-full min-w-[720px] text-left text-sm">
        <thead className="border-b border-border bg-muted/30 text-xs uppercase tracking-wide text-muted-foreground">
          <tr>
            <th className="px-4 py-3 font-medium">Claim</th>
            <th className="px-4 py-3 font-medium">Type</th>
            <th className="px-4 py-3 font-medium">Status</th>
            <th className="px-4 py-3 font-medium">Confidence</th>
            <th className="px-4 py-3 font-medium">Sources</th>
          </tr>
        </thead>
        <tbody>
          {evidenceRows.map((row) => (
            <tr key={row.evidence_id} className="border-b border-border/60 hover:bg-muted/10">
              <td className="max-w-md px-4 py-3 align-top">{row.claim_text}</td>
              <td className="px-4 py-3 align-top capitalize text-muted-foreground">
                {row.claim_type.replace(/_/g, " ")}
              </td>
              <td className="px-4 py-3 align-top">
                <Badge variant={statusVariant[row.support_status] ?? "outline"}>
                  {row.support_status.replace(/_/g, " ")}
                </Badge>
              </td>
              <td className="px-4 py-3 align-top font-mono">{formatConfidence(row.confidence)}</td>
              <td className="px-4 py-3 align-top">
                <SourceLinks ids={row.source_record_ids} />
              </td>
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  );
}

function SourceLinks({ ids }: { ids: string[] }) {
  if (!ids || ids.length === 0) {
    return <span className="text-muted-foreground">—</span>;
  }
  return (
    <ul className="space-y-1">
      {ids.map((id) => {
        const url = pmidUrl(id);
        return (
          <li key={id}>
            {url ? (
              <a
                href={url}
                target="_blank"
                rel="noopener noreferrer"
                className="text-cockpit-teal hover:underline"
              >
                {id}
              </a>
            ) : (
              <span className="font-mono text-xs">{id}</span>
            )}
          </li>
        );
      })}
    </ul>
  );
}
