import type { ExhibitClinical, ExhibitFinancing, ExhibitSnapshot } from "@/types/combined";
import { Badge } from "@/components/ui/badge";
import { formatUsd } from "@/lib/format";

interface OpportunityInvestmentPackageProps {
  snapshot: ExhibitSnapshot;
  clinical: ExhibitClinical;
  financing: ExhibitFinancing;
}

export function OpportunityInvestmentPackage({
  snapshot,
  clinical,
  financing,
}: OpportunityInvestmentPackageProps) {
  const gap = snapshot.capital_gap_usd;

  return (
    <section className="rounded-lg border border-cockpit-teal/30 bg-cockpit-teal/5 px-5 py-5 space-y-4">
      <div className="flex flex-wrap items-center gap-2">
        <h2 className="text-lg font-semibold">RI investment package</h2>
        {snapshot.comparator_grounded ? (
          <Badge variant="outline" className="font-normal text-xs">
            Comparator-sized
          </Badge>
        ) : null}
      </div>
      <p className="text-sm leading-relaxed text-muted-foreground">
        <span className="font-medium text-foreground">{financing.structure_label}</span> — total ask{" "}
        <strong className="text-foreground">{formatUsd(gap)}</strong> for Rhode Island physicians
        and Slater Tech Fund (SSBCI match):
      </p>
      <ul className="text-sm space-y-1 list-none pl-0">
        <li>
          <strong className="text-foreground">{formatUsd(snapshot.physician_share_usd)}</strong>{" "}
          <span className="text-muted-foreground">
            — physician syndicate check (clinical oversight, pilot credibility, local KOL network)
          </span>
        </li>
        <li>
          <strong className="text-foreground">{formatUsd(snapshot.slater_share_usd)}</strong>{" "}
          <span className="text-muted-foreground">
            — Slater SSBCI equity match (≤$200K policy cap)
          </span>
        </li>
      </ul>
      {snapshot.next_milestone ? (
        <p className="text-sm">
          <span className="text-muted-foreground">Next milestone:</span> {snapshot.next_milestone}
        </p>
      ) : null}
      {snapshot.financing_rationale ? (
        <p className="text-sm text-muted-foreground">{snapshot.financing_rationale}</p>
      ) : null}
      <dl className="grid gap-3 text-sm sm:grid-cols-3">
        <div>
          <dt className="text-muted-foreground">Clinical allocation</dt>
          <dd className="font-medium">
            {formatUsd(snapshot.clinical_allocation_usd ?? clinical.cost_usd)}
          </dd>
        </div>
        <div>
          <dt className="text-muted-foreground">R&D / preclinical</dt>
          <dd className="font-medium">{formatUsd(snapshot.rd_allocation_usd ?? 0)}</dd>
        </div>
        <div>
          <dt className="text-muted-foreground">Timeline</dt>
          <dd className="font-medium">
            {clinical.timeline_weeks || clinical.duration_weeks || "—"} weeks
          </dd>
        </div>
        <div>
          <dt className="text-muted-foreground">Budget ceiling</dt>
          <dd className="font-medium">{formatUsd(snapshot.budget_ceiling_usd)}</dd>
        </div>
      </dl>
      <p className="text-xs text-muted-foreground">
        Audience: {financing.audience_label} · Ask: {financing.development_ask_label}
      </p>
    </section>
  );
}
