"use client";

import { useMemo, useState } from "react";
import Link from "next/link";
import { ArrowLeft, CheckCircle2, Database, FileText, FlaskConical, PlayCircle } from "lucide-react";
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card";
import { Button } from "@/components/ui/button";
import { Badge } from "@/components/ui/badge";

type ConnectorKey =
  | "pubmed"
  | "clinicaltrials"
  | "opentargets"
  | "chembl"
  | "biothings"
  | "uniprot"
  | "reactome"
  | "gwas"
  | "pharmgkb"
  | "openfda";

const CONNECTOR_LABELS: Record<ConnectorKey, string> = {
  pubmed: "PubMed",
  clinicaltrials: "ClinicalTrials.gov",
  opentargets: "Open Targets",
  chembl: "ChEMBL",
  biothings: "BioThings",
  uniprot: "UniProt",
  reactome: "Reactome",
  gwas: "GWAS Catalog",
  pharmgkb: "PharmGKB",
  openfda: "OpenFDA",
};

const CONNECTOR_KEYS = Object.keys(CONNECTOR_LABELS) as ConnectorKey[];

interface IntakeDraft {
  caseId: string;
  displayName: string;
  target: string;
  indication: string;
  mechanismDirection: string;
  modality: string;
  developmentStage: string;
  strategicQuestion: string;
}

const DEFAULT_DRAFT: IntakeDraft = {
  caseId: "new_case_slug",
  displayName: "New Case / Target-Indication",
  target: "Target Name",
  indication: "Indication Name",
  mechanismDirection: "inhibit",
  modality: "small molecule",
  developmentStage: "preclinical",
  strategicQuestion: "What makes this case commercially differentiated?",
};

export function CaseOnboardingFlow() {
  const [draft, setDraft] = useState<IntakeDraft>(DEFAULT_DRAFT);
  const [connectors, setConnectors] = useState<Record<ConnectorKey, boolean>>(
    CONNECTOR_KEYS.reduce(
      (acc, key) => {
        acc[key] = true;
        return acc;
      },
      {} as Record<ConnectorKey, boolean>,
    ),
  );

  const selectedConnectorCount = CONNECTOR_KEYS.filter((key) => connectors[key]).length;
  const requiredFieldsComplete = [
    draft.caseId,
    draft.displayName,
    draft.target,
    draft.indication,
    draft.mechanismDirection,
    draft.modality,
    draft.developmentStage,
    draft.strategicQuestion,
  ].filter((value) => value.trim().length > 0).length;

  const yamlPreview = useMemo(() => {
    const sourceLines = CONNECTOR_KEYS.map((key) => `  ${key}: ${connectors[key] ? "true" : "false"}`).join("\n");
    return `case_id: ${draft.caseId}
display_name: ${draft.displayName}
workflow: translational_diligence
version: v0.5

target:
  name: ${draft.target}
  aliases: []

indication:
  name: ${draft.indication}
  aliases: []

biology:
  mechanism_direction: ${draft.mechanismDirection}
  modality: ${draft.modality}

program:
  development_stage: ${draft.developmentStage}

commercial:
  strategic_question: ${draft.strategicQuestion}

sources:
${sourceLines}
  octagon_market: false
  local_docs: false
`;
  }, [connectors, draft]);

  return (
    <main className="mx-auto max-w-7xl space-y-6 px-4 py-8 sm:px-6 lg:px-8">
      <header className="space-y-3">
        <Link href="/" className="inline-flex items-center gap-1 text-sm text-muted-foreground hover:text-foreground">
          <ArrowLeft className="h-4 w-4" />
          Back to case library
        </Link>
        <p className="font-mono text-xs uppercase tracking-widest text-cockpit-teal">Case onboarding</p>
        <h1 className="text-3xl font-semibold tracking-tight">New case submission and execution flow</h1>
        <p className="max-w-3xl text-sm text-muted-foreground">
          This flow is for drafting case inputs, selecting BioMCP sources, and understanding exactly how inputs become
          cached artifacts and cockpit outputs.
        </p>
      </header>

      <div className="grid gap-6 lg:grid-cols-2">
        <Card className="border-border/80 bg-card/80">
          <CardHeader>
            <CardTitle className="flex items-center gap-2">
              <FileText className="h-5 w-5 text-cockpit-teal" />
              Intake draft
            </CardTitle>
            <CardDescription>
              Enter core fields that drive query generation, benchmarking prompts, and report synthesis.
            </CardDescription>
          </CardHeader>
          <CardContent className="space-y-3">
            <InputRow
              label="Case ID"
              value={draft.caseId}
              onChange={(value) => setDraft((prev) => ({ ...prev, caseId: value }))}
            />
            <InputRow
              label="Display name"
              value={draft.displayName}
              onChange={(value) => setDraft((prev) => ({ ...prev, displayName: value }))}
            />
            <InputRow
              label="Target"
              value={draft.target}
              onChange={(value) => setDraft((prev) => ({ ...prev, target: value }))}
            />
            <InputRow
              label="Indication"
              value={draft.indication}
              onChange={(value) => setDraft((prev) => ({ ...prev, indication: value }))}
            />
            <InputRow
              label="Mechanism direction"
              value={draft.mechanismDirection}
              onChange={(value) => setDraft((prev) => ({ ...prev, mechanismDirection: value }))}
            />
            <InputRow
              label="Modality"
              value={draft.modality}
              onChange={(value) => setDraft((prev) => ({ ...prev, modality: value }))}
            />
            <InputRow
              label="Development stage"
              value={draft.developmentStage}
              onChange={(value) => setDraft((prev) => ({ ...prev, developmentStage: value }))}
            />
            <InputRow
              label="Strategic question"
              value={draft.strategicQuestion}
              onChange={(value) => setDraft((prev) => ({ ...prev, strategicQuestion: value }))}
            />
          </CardContent>
        </Card>

        <Card className="border-border/80 bg-card/80">
          <CardHeader>
            <CardTitle className="flex items-center gap-2">
              <Database className="h-5 w-5 text-cockpit-teal" />
              Source selection
            </CardTitle>
            <CardDescription>
              Choose distinct BioMCP-backed data sources. The UI source panel will display backend, status, and value.
            </CardDescription>
          </CardHeader>
          <CardContent className="space-y-4">
            <div className="grid gap-2 sm:grid-cols-2">
              {CONNECTOR_KEYS.map((key) => (
                <label key={key} className="flex items-center gap-2 rounded border border-border/60 px-3 py-2 text-sm">
                  <input
                    type="checkbox"
                    checked={connectors[key]}
                    onChange={(event) =>
                      setConnectors((prev) => ({
                        ...prev,
                        [key]: event.target.checked,
                      }))
                    }
                  />
                  {CONNECTOR_LABELS[key]}
                </label>
              ))}
            </div>
            <div className="flex flex-wrap items-center gap-2">
              <Badge variant={selectedConnectorCount >= 10 ? "success" : "warning"}>
                {selectedConnectorCount}/10 selected
              </Badge>
              <Badge variant={requiredFieldsComplete >= 8 ? "success" : "warning"}>
                {requiredFieldsComplete}/8 required fields completed
              </Badge>
            </div>
            <p className="text-xs text-muted-foreground">
              Recommendation: keep at least 10 sources selected and complete all core fields to maximize query
              relevance and output quality.
            </p>
          </CardContent>
        </Card>
      </div>

      <div className="grid gap-6 lg:grid-cols-2">
        <Card className="border-border/80 bg-card/80">
          <CardHeader>
            <CardTitle className="flex items-center gap-2">
              <PlayCircle className="h-5 w-5 text-cockpit-teal" />
              Processing flow
            </CardTitle>
            <CardDescription>Use this copy in demos to explain what happens after submission.</CardDescription>
          </CardHeader>
          <CardContent className="space-y-4 text-sm">
            <StepCopy
              title="1) Intake and validation"
              body="The case config is parsed into a structured input profile and graded for input quality so downstream queries stay specific."
            />
            <StepCopy
              title="2) Live BioMCP retrieval"
              body="Selected connectors run BioMCP calls. Raw responses are cached and each connector gets backend/status/value metadata."
            />
            <StepCopy
              title="3) Artifact generation"
              body="The pipeline builds source manifest, literature, trials, biology, evidence, risk, report, and evaluation artifacts."
            />
            <StepCopy
              title="4) Static publish for UI"
              body="Artifacts are copied into public case folders so the frontend reads fully cached data with no runtime API dependency."
            />
          </CardContent>
        </Card>

        <Card className="border-border/80 bg-card/80">
          <CardHeader>
            <CardTitle className="flex items-center gap-2">
              <FlaskConical className="h-5 w-5 text-cockpit-teal" />
              Config and run preview
            </CardTitle>
            <CardDescription>Preview the case YAML and the command used to populate the static UI cache.</CardDescription>
          </CardHeader>
          <CardContent className="space-y-3">
            <pre className="max-h-72 overflow-auto rounded-md border border-border/60 bg-background/60 p-3 text-xs">
              {yamlPreview}
            </pre>
            <div className="rounded-md border border-border/60 bg-background/60 p-3 text-xs">
              <p className="font-medium text-foreground">Run command</p>
              <code className="mt-2 block whitespace-pre-wrap text-muted-foreground">
                python -m pipeline.publish_static --case {draft.caseId} --mode live --build-web
              </code>
            </div>
            <div className="rounded-md border border-border/60 bg-background/60 p-3 text-xs">
              <p className="font-medium text-foreground">Where it appears in UI</p>
              <ul className="mt-2 list-inside list-disc space-y-1 text-muted-foreground">
                <li>Input profile in case header</li>
                <li>Source connection/value diagnostics in Sources tab</li>
                <li>Prompt runs and benchmark topics in Sources tab</li>
                <li>Evidence, Trials, Risks, and Evals tabs from cached artifacts</li>
              </ul>
            </div>
            <Button asChild className="w-full">
              <Link href="/">Review published cases</Link>
            </Button>
          </CardContent>
        </Card>
      </div>

      <Card className="border-border/80 bg-card/80">
        <CardHeader>
          <CardTitle>Execution verification checklist</CardTitle>
          <CardDescription>
            Use this checklist during demos to confirm the UI is showing real pipeline execution, not placeholder data.
          </CardDescription>
        </CardHeader>
        <CardContent className="grid gap-4 text-sm md:grid-cols-2">
          <div className="rounded-md border border-border/60 bg-background/40 p-3">
            <p className="font-medium text-foreground">Required checks in Sources tab</p>
            <ul className="mt-2 list-inside list-disc space-y-1 text-muted-foreground">
              <li>`backend_used` is biomcp for intended connectors</li>
              <li>`connection_status` is mostly ok (warnings understood)</li>
              <li>`record_count` is non-zero where biologically expected</li>
              <li>`mcp_prompt_runs` are cached with source record IDs</li>
            </ul>
          </div>
          <div className="rounded-md border border-border/60 bg-background/40 p-3">
            <p className="font-medium text-foreground">Required checks across cockpit tabs</p>
            <ul className="mt-2 list-inside list-disc space-y-1 text-muted-foreground">
              <li>Header input profile matches submission intent</li>
              <li>Evidence tab shows populated rows with source IDs</li>
              <li>Trials and Risks tabs show case-relevant records</li>
              <li>Flow tab reflects connector and artifact health</li>
            </ul>
          </div>
          <div className="rounded-md border border-border/60 bg-background/40 p-3 md:col-span-2">
            <p className="font-medium text-foreground">Viewer flow</p>
            <p className="mt-1 text-muted-foreground">
              1) Draft inputs and sources here, 2) run publish command, 3) open case dashboard, 4) walk Flow then
              Sources tabs first, 5) conclude with Evidence/Risks/Evals for decision support.
            </p>
            <div className="mt-3 flex flex-wrap gap-2">
              <Button asChild size="sm" variant="outline">
                <Link href={`/cases/${draft.caseId}`}>Open drafted case route</Link>
              </Button>
              <Button asChild size="sm" variant="outline">
                <Link href="/cases/sting_pdac">Open reference live case</Link>
              </Button>
            </div>
          </div>
        </CardContent>
      </Card>
    </main>
  );
}

function InputRow({
  label,
  value,
  onChange,
}: {
  label: string;
  value: string;
  onChange: (value: string) => void;
}) {
  return (
    <label className="grid gap-1 text-sm">
      <span className="text-muted-foreground">{label}</span>
      <input
        className="rounded-md border border-input bg-background px-3 py-2 text-sm outline-none ring-offset-background focus-visible:ring-2 focus-visible:ring-ring"
        value={value}
        onChange={(event) => onChange(event.target.value)}
      />
    </label>
  );
}

function StepCopy({ title, body }: { title: string; body: string }) {
  return (
    <div className="rounded-md border border-border/60 bg-background/40 p-3">
      <p className="flex items-center gap-2 font-medium text-foreground">
        <CheckCircle2 className="h-4 w-4 text-cockpit-teal" />
        {title}
      </p>
      <p className="mt-1 text-muted-foreground">{body}</p>
    </div>
  );
}
