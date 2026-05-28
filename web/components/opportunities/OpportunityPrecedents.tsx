import type { ExhibitMarket } from "@/types/combined";
import { CompSiteDossierPanel, PrecedentCard, sortPrecedentsForDisplay } from "@/components/opportunities/CompSiteDossier";

interface OpportunityPrecedentsProps {
  market: ExhibitMarket;
  valueBandLabel: string;
  verifiedCount: number;
}

function CompRollupStrip({ rollup }: { rollup: ExhibitMarket["comp_rollup"] }) {
  if (!rollup) return null;
  const blocks = [
    { label: "Clinical precedent", value: rollup.clinical_path },
    { label: "Reimbursement precedent", value: rollup.reimbursement_path },
    { label: "KOL pattern", value: rollup.kol_pattern },
  ].filter((b) => b.value);
  if (!blocks.length) return null;
  return (
    <div className="space-y-2 rounded-md border border-cockpit-teal/20 bg-cockpit-teal/5 px-3 py-3">
      <p className="text-xs font-medium uppercase tracking-wide text-cockpit-teal">
        Comparator site rollup
      </p>
      {blocks.map((block) => (
        <p key={block.label} className="text-sm text-muted-foreground">
          <span className="font-medium text-foreground">{block.label}: </span>
          {block.value}
        </p>
      ))}
    </div>
  );
}

export function OpportunityPrecedents({ market, valueBandLabel, verifiedCount }: OpportunityPrecedentsProps) {
  if (!market.precedents.length) return null;
  const displayPrecedents = sortPrecedentsForDisplay(market.precedents);

  return (
    <div className="space-y-4">
      <p className="text-sm text-muted-foreground">
        How venture and strategic financing staged each comparable — round ladder in{" "}
        <span className="text-foreground/90">Financing</span>, dollar anchors by type (total VC
        raised, latest round, series, grant; market cap only when no venture ladder).
      </p>
      {valueBandLabel ? (
        <p className="text-sm font-medium text-foreground">
          Comparator band: {valueBandLabel}
          {verifiedCount > 0 ? (
            <span className="font-normal text-muted-foreground">
              {" "}
              · {verifiedCount} verified
            </span>
          ) : null}
        </p>
      ) : null}
      {market.highlights.length ? (
        <ul className="list-disc space-y-1 pl-5 text-sm text-muted-foreground">
          {market.highlights.map((h) => (
            <li key={h}>{h}</li>
          ))}
        </ul>
      ) : null}
      {market.development_path ? (
        <p className="text-sm rounded-md bg-muted/30 px-3 py-2">
          <span className="font-medium text-foreground">RI path: </span>
          {market.development_path}
        </p>
      ) : null}
      {market.financing_path ? (
        <p className="text-sm rounded-md bg-muted/30 px-3 py-2">
          <span className="font-medium text-foreground">Financing precedent: </span>
          {market.financing_path}
        </p>
      ) : null}
      <CompRollupStrip rollup={market.comp_rollup} />
      <ul className="space-y-3">
        {displayPrecedents.map((p) => (
          <PrecedentCard key={`${p.rank}-${p.name}`} p={p} />
        ))}
      </ul>
    </div>
  );
}
