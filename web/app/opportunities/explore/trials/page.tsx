import { TrialExplore } from "@/components/opportunities/TrialExplore";
import { SiteNav } from "@/components/SiteNav";
import { loadTrialTemplateUsage } from "@/lib/loadOpportunities";

export default function ExploreTrialsPage() {
  const templates = loadTrialTemplateUsage();

  return (
    <>
      <SiteNav />
      <main className="mx-auto max-w-7xl space-y-6 px-4 py-8 sm:px-6 lg:px-8">
        <header className="space-y-2">
          <h1 className="text-2xl font-semibold">Trial playbooks</h1>
          <p className="text-sm text-muted-foreground">
            Historical RI trial templates reused as validation paths across the opportunity portfolio.
          </p>
        </header>
        <TrialExplore templates={templates} />
      </main>
    </>
  );
}
