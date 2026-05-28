import { notFound } from "next/navigation";
import { CaseDashboard } from "@/components/CaseDashboard";
import { SiteNav } from "@/components/SiteNav";
import { listCaseIds, loadCaseMetadata, loadCasePacket } from "@/lib/loadCase";

export function generateStaticParams() {
  return listCaseIds().map((caseId) => ({ caseId }));
}

interface CasePageProps {
  params: Promise<{ caseId: string }>;
}

export default async function CasePage({ params }: CasePageProps) {
  const { caseId } = await params;
  const metadata = loadCaseMetadata(caseId);

  if (!metadata) {
    notFound();
  }

  const packet = await loadCasePacket(caseId);

  return (
    <>
      <SiteNav />
      <CaseDashboard packet={packet} />
    </>
  );
}
