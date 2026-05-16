import { CaseCard } from "@/components/CaseCard";
import { loadAllCaseMetadata } from "@/lib/loadCase";

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
          Static case packets loaded from audited artifacts. Select a target–indication dossier to
          open the diligence cockpit.
        </p>
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
            />
          ))}
        </div>
      )}
    </main>
  );
}
