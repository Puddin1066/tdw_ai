"use client";

import { Database, FileSearch, FlaskConical, ScrollText } from "lucide-react";
import type { ReactNode } from "react";
import type { CasePacket } from "@/types/artifacts";
import { Badge } from "@/components/ui/badge";
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card";

interface ProcessingFlowProps {
  packet: CasePacket;
}

export function ProcessingFlow({ packet }: ProcessingFlowProps) {
  const entries = packet.sourceManifest?.entries ?? [];
  const sourceCount = entries.length;
  const biomcpBackedCount = entries.filter((entry) => entry.backend_used === "biomcp").length;
  const warningCount = entries.filter((entry) => (entry.warnings ?? []).length > 0).length;
  const errorCount = entries.filter((entry) => (entry.errors ?? []).length > 0).length;
  const literatureCount = packet.evidenceTable.length;
  const trialCount = packet.clinicalTrials.length;
  const riskCount = packet.riskMap?.risks.length ?? 0;
  const hasReport = !!packet.diligenceReport;

  return (
    <div className="space-y-4">
      <Card className="border-border/70 bg-card/70">
        <CardHeader>
          <CardTitle>How this case is processed</CardTitle>
          <CardDescription>
            This walkthrough maps your inputs to BioMCP retrieval, artifact generation, and final diligence outputs.
          </CardDescription>
        </CardHeader>
        <CardContent className="grid gap-4 md:grid-cols-2">
          <FlowStep
            icon={<FileSearch className="h-4 w-4 text-cockpit-teal" />}
            title="1) Input profile intake"
            copy="Target, indication, modality, mechanism, stage, and commercial questions are parsed into a structured case profile."
            badge={
              <Badge variant="outline">
                {packet.metadata.input_profile ? "Profile loaded" : "Profile partial"}
              </Badge>
            }
          />
          <FlowStep
            icon={<Database className="h-4 w-4 text-cockpit-teal" />}
            title="2) BioMCP source retrieval"
            copy="Configured connectors run searches and capture backend, connection status, record counts, warnings, and value interpretation."
            badge={
              <div className="flex flex-wrap items-center gap-2">
                <Badge
                  variant={
                    sourceCount >= 10
                      ? "success"
                      : sourceCount >= 5
                        ? "warning"
                        : "danger"
                  }
                >
                  {sourceCount} connectors in manifest
                </Badge>
                <Badge
                  variant={
                    biomcpBackedCount === sourceCount && sourceCount > 0
                      ? "success"
                      : biomcpBackedCount > 0
                        ? "warning"
                        : "danger"
                  }
                >
                  BioMCP-backed {biomcpBackedCount}/{sourceCount}
                </Badge>
                <Badge variant={warningCount === 0 ? "success" : "warning"}>
                  {warningCount} warnings
                </Badge>
                <Badge variant={errorCount === 0 ? "success" : "danger"}>
                  {errorCount} errors
                </Badge>
              </div>
            }
          />
          <FlowStep
            icon={<FlaskConical className="h-4 w-4 text-cockpit-teal" />}
            title="3) Artifact synthesis pipeline"
            copy="Pipeline writes source manifest, trials, biology records, evidence rows, risk map, report, and eval artifacts for static consumption."
            badge={
              <Badge variant={hasReport ? "success" : "warning"}>
                {hasReport ? "Report generated" : "Report missing"}
              </Badge>
            }
          />
          <FlowStep
            icon={<ScrollText className="h-4 w-4 text-cockpit-teal" />}
            title="4) Cockpit outputs"
            copy="Dashboard tabs display the cached artifacts so users can audit provenance, evidence depth, risks, and execution outcomes."
            badge={
              <Badge variant="outline">
                Evidence {literatureCount} · Trials {trialCount} · Risks {riskCount}
              </Badge>
            }
          />
        </CardContent>
      </Card>
    </div>
  );
}

function FlowStep({
  icon,
  title,
  copy,
  badge,
}: {
  icon: ReactNode;
  title: string;
  copy: string;
  badge: ReactNode;
}) {
  return (
    <div className="rounded-md border border-border/70 bg-background/30 p-4">
      <p className="flex items-center gap-2 text-sm font-medium">
        {icon}
        {title}
      </p>
      <p className="mt-2 text-sm text-muted-foreground">{copy}</p>
      <div className="mt-3">{badge}</div>
    </div>
  );
}
