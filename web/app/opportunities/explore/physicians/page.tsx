import { PhysicianExplore } from "@/components/opportunities/PhysicianExplore";
import { SiteNav } from "@/components/SiteNav";
import { loadPhysicianEdges } from "@/lib/loadOpportunities";

export default function ExplorePhysiciansPage() {
  const edges = loadPhysicianEdges();

  return (
    <>
      <SiteNav />
      <main className="mx-auto max-w-7xl space-y-6 px-4 py-8 sm:px-6 lg:px-8">
        <header className="space-y-2">
          <h1 className="text-2xl font-semibold">Physician network</h1>
          <p className="text-sm text-muted-foreground">
            Clinicians matched across multiple RI opportunities — capacity and reuse for syndicate
            planning.
          </p>
        </header>
        <PhysicianExplore edges={edges} />
      </main>
    </>
  );
}
