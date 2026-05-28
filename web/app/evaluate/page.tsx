import { DealEvaluationWorkflow } from "@/components/DealEvaluationWorkflow";
import { SiteNav } from "@/components/SiteNav";
import { loadEvaluationCases } from "@/lib/loadCase";

export default async function DealEvaluationPage() {
  const cases = await loadEvaluationCases();
  return (
    <>
      <SiteNav />
      <DealEvaluationWorkflow cases={cases} />
    </>
  );
}
