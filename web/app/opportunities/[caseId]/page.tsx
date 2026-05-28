import Link from "next/link";
import { notFound } from "next/navigation";
import { OpportunityMemo } from "@/components/opportunities/OpportunityMemo";
import { SiteNav } from "@/components/SiteNav";
import { getCombinedOpportunity, listCombinedCaseIds } from "@/lib/loadCombined";

export function generateStaticParams() {
  return listCombinedCaseIds().map((caseId) => ({ caseId }));
}

interface OpportunityDetailPageProps {
  params: Promise<{ caseId: string }>;
}

export default async function OpportunityDetailPage({ params }: OpportunityDetailPageProps) {
  const { caseId } = await params;
  const opportunity = getCombinedOpportunity(caseId);
  if (!opportunity?.exhibit) {
    notFound();
  }

  return (
    <>
      <SiteNav />
      <main className="mx-auto max-w-3xl px-4 py-8 sm:px-6 lg:px-8">
        <Link
          href="/opportunities"
          className="mb-8 inline-block text-sm text-muted-foreground hover:text-foreground"
        >
          ← All opportunities
        </Link>
        <OpportunityMemo exhibit={opportunity.exhibit} />
      </main>
    </>
  );
}
