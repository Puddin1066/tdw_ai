import { CaseCard } from "@/components/CaseCard";
import { CompareWorkbench } from "@/components/CompareWorkbench";
import { loadAllCaseMetadata } from "@/lib/loadCase";
import { Button } from "@/components/ui/button";
import Link from "next/link";

export default async function CaseLibraryPage() {
  const cases = await loadAllCaseMetadata();

  return (
    <main className="mx-auto max-w-7xl px-4 py-10 sm:px-6 lg:px-8">
      <header className="mb-10 space-y-2">
        <p className="font-mono text-xs uppercase tracking-widest text-cockpit-teal">
          Translational Diligence Workbench
        </p>
        <h1 className="text-3xl font-semibold tracking-tight sm:text-4xl">Case library</h1>
        <p className="max-w-2xl text-sm text-muted-foreground">
          Compare target-indication cases against benchmarks using one evidence standard. Each card
          is built from cached source artifacts, connector diagnostics, and contract-based quality gates.
        </p>
        <p className="max-w-3xl text-xs text-muted-foreground">
          Value proposition: transparent data sourcing + explicit framing lineage + consistent
          comparability rules, so scientific and investment decisions are made on auditable evidence.
        </p>
        <div className="pt-2">
          <Button asChild variant="outline">
            <Link href="/onboarding">New case onboarding flow</Link>
          </Button>
        </div>
      </header>

      {cases.length === 0 ? (
        <p className="text-sm text-muted-foreground">
          No cases found under <code className="font-mono">public/data/cases/</code>.
        </p>
      ) : (
        <div className="grid gap-4 sm:grid-cols-2 lg:grid-cols-2 xl:grid-cols-4">
          {cases.map((meta) => (
            <CaseCard
              key={meta.case_id}
              caseId={meta.case_id}
              targetName={meta.target_name}
              indicationName={meta.indication_name}
              maturityStage={meta.maturity_stage}
              confidenceScore={meta.confidence_score}
              evidenceDensity={meta.evidence_density}
              topRisk={meta.top_risk}
              isBenchmark={meta.is_benchmark}
              comparabilityPassed={meta.comparability_passed}
              comparabilityScore={meta.comparability_score}
              fallbackConnectorCount={meta.fallback_connector_count}
            />
          ))}
        </div>
      )}
      <section className="mt-10">
        <CompareWorkbench cases={cases} />
      </section>
    </main>
  );
}
