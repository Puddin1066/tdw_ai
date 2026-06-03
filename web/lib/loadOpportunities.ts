import fs from "fs";
import path from "path";
import type {
  OpportunityIndexRow,
  OpportunityProfile,
  PhysicianOpportunityEdge,
  ProgramData,
  TrialTemplateUsage,
} from "@/types/opportunities";

const OPPORTUNITIES_ROOT = path.join(process.cwd(), "public", "data", "opportunities");

function readJson<T>(filePath: string): T | null {
  if (!fs.existsSync(filePath)) return null;
  return JSON.parse(fs.readFileSync(filePath, "utf-8")) as T;
}

export function loadOpportunityIndex(): OpportunityIndexRow[] {
  const rows = readJson<OpportunityIndexRow[]>(path.join(OPPORTUNITIES_ROOT, "index.json"));
  return rows ?? [];
}

export function loadOpportunityProfile(caseId: string): OpportunityProfile | null {
  return readJson<OpportunityProfile>(path.join(OPPORTUNITIES_ROOT, "profiles", `${caseId}.json`));
}

export function loadProgramData(): ProgramData | null {
  return readJson<ProgramData>(path.join(OPPORTUNITIES_ROOT, "program.json"));
}

export function loadPhysicianEdges(): PhysicianOpportunityEdge[] {
  const rows = readJson<PhysicianOpportunityEdge[]>(
    path.join(OPPORTUNITIES_ROOT, "edges", "physician_opportunities.json"),
  );
  return rows ?? [];
}

export function loadTrialTemplateUsage(): TrialTemplateUsage[] {
  const rows = readJson<TrialTemplateUsage[]>(
    path.join(OPPORTUNITIES_ROOT, "edges", "trial_templates.json"),
  );
  return rows ?? [];
}

export function listOpportunityCaseIds(): string[] {
  return loadOpportunityIndex().map((row) => row.case_id);
}

export function getIndexRow(caseId: string): OpportunityIndexRow | null {
  return loadOpportunityIndex().find((row) => row.case_id === caseId) ?? null;
}
