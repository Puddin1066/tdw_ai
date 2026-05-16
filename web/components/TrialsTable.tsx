import type { ClinicalTrialRecord } from "@/types/artifacts";
import { EmptyState } from "@/components/EmptyState";
import { nctUrl } from "@/lib/utils";

export interface TrialsTableProps {
  trials: ClinicalTrialRecord[];
}

export function TrialsTable({ trials }: TrialsTableProps) {
  if (trials.length === 0) {
    return (
      <EmptyState
        title="No clinical trials"
        description="clinical_trials.json has no registered trials for this target–indication case."
      />
    );
  }

  return (
    <div className="overflow-x-auto rounded-lg border border-border">
      <table className="w-full min-w-[800px] text-left text-sm">
        <thead className="border-b border-border bg-muted/30 text-xs uppercase tracking-wide text-muted-foreground">
          <tr>
            <th className="px-4 py-3 font-medium">NCT ID</th>
            <th className="px-4 py-3 font-medium">Phase</th>
            <th className="px-4 py-3 font-medium">Status</th>
            <th className="px-4 py-3 font-medium">Sponsor</th>
            <th className="px-4 py-3 font-medium">Intervention</th>
            <th className="px-4 py-3 font-medium">Condition</th>
          </tr>
        </thead>
        <tbody>
          {trials.map((trial) => (
            <tr key={trial.nct_id} className="border-b border-border/60 hover:bg-muted/10">
              <td className="px-4 py-3 font-mono">
                <a
                  href={trial.url ?? nctUrl(trial.nct_id)}
                  target="_blank"
                  rel="noopener noreferrer"
                  className="text-cockpit-teal hover:underline"
                >
                  {trial.nct_id}
                </a>
              </td>
              <td className="px-4 py-3">{trial.phase ?? "—"}</td>
              <td className="px-4 py-3 capitalize">{trial.overall_status ?? "—"}</td>
              <td className="px-4 py-3">{trial.sponsor ?? "—"}</td>
              <td className="px-4 py-3">
                {trial.interventions?.length ? trial.interventions.join("; ") : "—"}
              </td>
              <td className="px-4 py-3">
                {trial.conditions?.length ? trial.conditions.join("; ") : "—"}
              </td>
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  );
}
