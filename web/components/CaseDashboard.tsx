"use client";

import Link from "next/link";
import { ChevronLeft } from "lucide-react";
import type { CasePacket } from "@/types/artifacts";
import { ExecutiveSnapshot } from "@/components/ExecutiveSnapshot";
import { EvidenceTable } from "@/components/EvidenceTable";
import { TrialsTable } from "@/components/TrialsTable";
import { RiskMap } from "@/components/RiskMap";
import { KnowledgeGraph } from "@/components/KnowledgeGraph";
import { SourceManifest } from "@/components/SourceManifest";
import { EvalPanel } from "@/components/EvalPanel";
import { ProcessingFlow } from "@/components/ProcessingFlow";
import { Badge } from "@/components/ui/badge";
import { Tabs, TabsContent, TabsList, TabsTrigger } from "@/components/ui/tabs";

interface CaseDashboardProps {
  packet: CasePacket;
}

export function CaseDashboard({ packet }: CaseDashboardProps) {
  const { metadata } = packet;

  return (
    <div className="mx-auto max-w-7xl space-y-6 px-4 py-8 sm:px-6 lg:px-8">
      <header className="space-y-4">
        <Link
          href="/"
          className="inline-flex items-center gap-1 text-sm text-muted-foreground hover:text-foreground"
        >
          <ChevronLeft className="h-4 w-4" />
          Case library
        </Link>
        <div className="flex flex-wrap items-end justify-between gap-4">
          <div>
            <p className="font-mono text-xs uppercase tracking-wider text-cockpit-teal">
              {metadata.case_id}
            </p>
            <h1 className="text-3xl font-semibold tracking-tight">
              {metadata.target_name}
              <span className="text-muted-foreground"> · </span>
              {metadata.indication_name}
            </h1>
            {metadata.description ? (
              <p className="mt-2 max-w-2xl text-sm text-muted-foreground">{metadata.description}</p>
            ) : null}
          </div>
          <Badge variant="outline" className="capitalize">
            {metadata.maturity_stage}
          </Badge>
        </div>
        {metadata.input_profile ? (
          <div className="rounded-md border border-border/60 bg-card/40 px-4 py-3 text-xs text-muted-foreground">
            <p className="font-medium text-foreground/90">Input profile</p>
            <div className="mt-1 grid gap-1 md:grid-cols-2">
              <p>Mechanism: {metadata.input_profile.biology?.mechanism_direction ?? "—"}</p>
              <p>Modality: {metadata.input_profile.biology?.modality ?? "—"}</p>
              <p>Target alias: {metadata.input_profile.biology?.target_alias ?? "—"}</p>
              <p>Patient segment: {metadata.input_profile.disease?.patient_segment ?? "—"}</p>
              <p>Geography: {metadata.input_profile.disease?.geography ?? "—"}</p>
              <p>Asset: {metadata.input_profile.program?.asset ?? "—"}</p>
              <p>Company: {metadata.input_profile.program?.company ?? "—"}</p>
              <p>Development stage: {metadata.input_profile.program?.development_stage ?? "—"}</p>
              <p className="md:col-span-2">
                Comparators: {(metadata.input_profile.program?.comparators ?? []).join("; ") || "—"}
              </p>
              <p className="md:col-span-2">
                Strategic question: {metadata.input_profile.commercial?.strategic_question ?? "—"}
              </p>
              <p className="md:col-span-2">
                Licensing question: {metadata.input_profile.commercial?.licensing_question ?? "—"}
              </p>
              <p className="md:col-span-2">
                Investment question: {metadata.input_profile.commercial?.investment_question ?? "—"}
              </p>
            </div>
          </div>
        ) : null}
        {packet.loadErrors.length > 0 ? (
          <div className="rounded-md border border-amber-500/30 bg-amber-500/10 px-4 py-3 text-sm text-amber-200">
            <p className="font-medium">Partial data load</p>
            <ul className="mt-1 list-inside list-disc text-amber-200/80">
              {packet.loadErrors.map((err) => (
                <li key={err}>{err}</li>
              ))}
            </ul>
          </div>
        ) : null}
      </header>

      <Tabs defaultValue="overview" className="w-full">
        <TabsList className="flex h-auto w-full flex-wrap justify-start gap-1">
          <TabsTrigger value="overview">Overview</TabsTrigger>
          <TabsTrigger value="flow">Flow</TabsTrigger>
          <TabsTrigger value="evidence">Evidence</TabsTrigger>
          <TabsTrigger value="trials">Trials</TabsTrigger>
          <TabsTrigger value="risks">Risks</TabsTrigger>
          <TabsTrigger value="graph">Graph</TabsTrigger>
          <TabsTrigger value="sources">Sources</TabsTrigger>
          <TabsTrigger value="evals">Evals</TabsTrigger>
        </TabsList>

        <TabsContent value="overview">
          <ExecutiveSnapshot
            report={packet.diligenceReport}
            riskMap={packet.riskMap}
            evalResults={packet.evalResults}
            evidenceRows={packet.evidenceTable}
            sourceManifest={packet.sourceManifest}
            clinicalTrials={packet.clinicalTrials}
          />
        </TabsContent>
        <TabsContent value="flow">
          <ProcessingFlow packet={packet} />
        </TabsContent>
        <TabsContent value="evidence">
          <EvidenceTable evidenceRows={packet.evidenceTable} />
        </TabsContent>
        <TabsContent value="trials">
          <TrialsTable trials={packet.clinicalTrials} />
        </TabsContent>
        <TabsContent value="risks">
          <RiskMap riskMap={packet.riskMap} />
        </TabsContent>
        <TabsContent value="graph">
          <KnowledgeGraph graph={packet.knowledgeGraph} />
        </TabsContent>
        <TabsContent value="sources">
          <SourceManifest manifest={packet.sourceManifest} />
        </TabsContent>
        <TabsContent value="evals">
          <EvalPanel evalResults={packet.evalResults} />
        </TabsContent>
      </Tabs>
    </div>
  );
}
