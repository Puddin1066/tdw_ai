import type { EvidenceRow, RiskMapData } from "@/types/artifacts";
import { Badge } from "@/components/ui/badge";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { EmptyState } from "@/components/EmptyState";
import { formatConfidence } from "@/lib/utils";

interface FramingTracePanelProps {
  evidenceRows: EvidenceRow[];
  riskMap: RiskMapData | null;
}

export function FramingTracePanel({ evidenceRows, riskMap }: FramingTracePanelProps) {
  if (evidenceRows.length === 0 && (!riskMap || riskMap.risks.length === 0)) {
    return (
      <EmptyState
        title="No framing trace available"
        description="Evidence and risk artifacts are required to reconstruct framing lineage."
      />
    );
  }

  const evidenceById = new Map<string, EvidenceRow>();
  for (const row of evidenceRows) {
    evidenceById.set(row.evidence_id, row);
  }

  const uniqueSourceIds = new Set<string>();
  let evidenceWithSourceIds = 0;
  for (const row of evidenceRows) {
    if (row.source_record_ids.length > 0) evidenceWithSourceIds += 1;
    for (const sourceId of row.source_record_ids) {
      if (sourceId?.trim()) uniqueSourceIds.add(sourceId);
    }
  }

  const risks = riskMap?.risks ?? [];
  let risksWithEvidenceLinks = 0;
  let risksWithSourceLinks = 0;
  let brokenEvidenceLinks = 0;

  const tracedRisks = risks.map((risk) => {
    const evidenceIds = risk.evidence_ids ?? [];
    const linkedEvidence = evidenceIds.map((id) => evidenceById.get(id)).filter((row): row is EvidenceRow => !!row);
    const missingEvidenceCount = evidenceIds.length - linkedEvidence.length;
    brokenEvidenceLinks += Math.max(0, missingEvidenceCount);
    if (linkedEvidence.length > 0) risksWithEvidenceLinks += 1;
    if ((risk.source_record_ids ?? []).length > 0) risksWithSourceLinks += 1;

    const tracedSourceIds = new Set<string>(risk.source_record_ids ?? []);
    for (const row of linkedEvidence) {
      for (const sourceId of row.source_record_ids) {
        if (sourceId?.trim()) tracedSourceIds.add(sourceId);
      }
    }

    return {
      riskId: risk.risk_id,
      title: risk.title,
      category: risk.category,
      severity: risk.severity,
      confidence: risk.confidence,
      description: risk.description,
      linkedEvidence,
      missingEvidenceCount,
      tracedSourceIds: Array.from(tracedSourceIds),
    };
  });

  return (
    <div className="space-y-4">
      <Card>
        <CardHeader>
          <CardTitle>Framing trace</CardTitle>
        </CardHeader>
        <CardContent className="space-y-3">
          <div className="flex flex-wrap gap-2">
            <Badge variant={evidenceWithSourceIds === evidenceRows.length ? "success" : "warning"}>
              Evidence with Attributed Source IDs: {evidenceWithSourceIds}/{evidenceRows.length}
            </Badge>
            <Badge variant={risksWithEvidenceLinks === risks.length ? "success" : "warning"}>
              Risks linked to evidence: {risksWithEvidenceLinks}/{risks.length}
            </Badge>
            <Badge variant={risksWithSourceLinks === risks.length ? "success" : "warning"}>
              Risks with Attributed Source IDs: {risksWithSourceLinks}/{risks.length}
            </Badge>
            <Badge variant={brokenEvidenceLinks === 0 ? "success" : "danger"}>
              Broken evidence links: {brokenEvidenceLinks}
            </Badge>
            <Badge variant="outline">Unique source records traced: {uniqueSourceIds.size}</Badge>
          </div>
          <p className="text-sm text-muted-foreground">
            This panel shows lineage from sourced records to evidence rows and into risk conclusions, so framing logic
            can be audited end-to-end.
          </p>
          <p className="text-xs text-muted-foreground">
            How to read: if source IDs and evidence links are complete and broken links are zero,
            framing is traceable. Missing links indicate conclusions that require remediation before
            benchmark-grade comparison.
          </p>
        </CardContent>
      </Card>

      <div className="space-y-3">
        {tracedRisks.map((risk) => (
          <Card key={risk.riskId} className={risk.missingEvidenceCount > 0 ? "border-cockpit-rose/40" : undefined}>
            <CardHeader className="pb-2">
              <div className="flex flex-wrap items-center gap-2">
                <CardTitle className="text-sm">{risk.title || risk.riskId}</CardTitle>
                <Badge variant="outline" className="capitalize">
                  {risk.category}
                </Badge>
                <Badge variant="outline" className="capitalize">
                  {risk.severity}
                </Badge>
                <Badge variant="outline">Confidence {formatConfidence(risk.confidence)}</Badge>
                {risk.missingEvidenceCount > 0 ? (
                  <Badge variant="danger">Missing evidence refs: {risk.missingEvidenceCount}</Badge>
                ) : (
                  <Badge variant="success">Evidence links valid</Badge>
                )}
              </div>
            </CardHeader>
            <CardContent className="space-y-2 text-sm">
              <p className="text-muted-foreground">{risk.description}</p>
              <p className="text-xs text-muted-foreground">
                Traced Attributed Source IDs ({risk.tracedSourceIds.length}):{" "}
                {risk.tracedSourceIds.slice(0, 6).join(", ") || "none"}
              </p>
              {risk.linkedEvidence.length > 0 ? (
                <div className="space-y-2">
                  {risk.linkedEvidence.slice(0, 3).map((row) => (
                    <div key={row.evidence_id} className="rounded border border-border/60 p-2">
                      <p className="text-xs font-medium">{row.claim_text}</p>
                      <p className="mt-1 text-xs text-muted-foreground">
                        {row.evidence_id} · {row.claim_type} · {row.support_status} ·{" "}
                        {formatConfidence(row.confidence)}
                      </p>
                      <p className="mt-1 text-xs text-muted-foreground">
                        Attributed Source IDs: {row.source_record_ids.slice(0, 4).join(", ") || "none"}
                      </p>
                    </div>
                  ))}
                </div>
              ) : (
                <p className="text-xs text-cockpit-rose">No linked evidence rows.</p>
              )}
            </CardContent>
          </Card>
        ))}
      </div>
    </div>
  );
}
