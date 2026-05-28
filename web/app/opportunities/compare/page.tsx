import { Suspense } from "react";
import { SyndicateComparePage } from "@/components/opportunities/SyndicateComparePage";
import { SiteNav } from "@/components/SiteNav";
import { loadOpportunityIndex } from "@/lib/loadOpportunities";

function CompareFallback() {
  return <p className="text-sm text-muted-foreground">Loading comparison…</p>;
}

export default function ComparePage() {
  const index = loadOpportunityIndex();

  return (
    <>
      <SiteNav />
      <main className="mx-auto max-w-7xl px-4 py-8 sm:px-6 lg:px-8">
        <Suspense fallback={<CompareFallback />}>
          <SyndicateComparePage index={index} />
        </Suspense>
      </main>
    </>
  );
}
