import { DealEvaluationWorkflow } from "@/components/DealEvaluationWorkflow";
import { loadAllCaseMetadata } from "@/lib/loadCase";

export default async function DealEvaluationPage() {
  const cases = await loadAllCaseMetadata();
  return <DealEvaluationWorkflow cases={cases} />;
}
