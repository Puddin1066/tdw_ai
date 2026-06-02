import type { CombinedPrecedent, CompSiteDossierPayload, ExhibitMarket } from "@/types/combined";
import { ComparableCitationLinks } from "@/components/opportunities/ComparableCitationLinks";
import { Badge } from "@/components/ui/badge";
import { formatUsd, formatValueAnchorType, validationBadgeVariant } from "@/lib/format";

export function precedentsWithDossiers(precedents: CombinedPrecedent[]): CombinedPrecedent[] {
  return precedents.filter((p) => p.site_dossier && p.site_dossier.dossier_status !== "pending");
}

export function sortPrecedentsForDisplay(precedents: CombinedPrecedent[]): CombinedPrecedent[] {
  return [...precedents].sort((a, b) => {
    const aHas = Boolean(a.site_dossier?.science_summary || a.site_dossier?.ri_parallel);
    const bHas = Boolean(b.site_dossier?.science_summary || b.site_dossier?.ri_parallel);
    if (aHas !== bHas) return aHas ? -1 : 1;
    return a.rank - b.rank;
  });
}

function SiteMapLinks({ siteMap }: { siteMap: Record<string, string> }) {
  const entries = Object.entries(siteMap).filter(([role]) => role !== "corporate");
  if (!entries.length) return null;
  return (
    <div className="flex flex-wrap gap-2 pt-1">
      {entries.map(([role, url]) => (
        <a
          key={role}
          href={url}
          target="_blank"
          rel="noreferrer"
          className="text-xs text-cockpit-teal hover:underline capitalize"
        >
          {role.replace(/_/g, " ")}
        </a>
      ))}
    </div>
  );
}

function CitedList({ title, items }: { title: string; items: Array<{ text: string; source_url?: string }> }) {
  if (!items.length) return null;
  return (
    <div className="space-y-1">
      <p className="text-xs font-medium uppercase tracking-wide text-muted-foreground">{title}</p>
      <ul className="space-y-1.5 text-sm text-muted-foreground">
        {items.map((item) => (
          <li key={`${title}-${item.text.slice(0, 40)}`}>
            {item.text}
            {item.source_url ? (
              <>
                {" "}
                <a href={item.source_url} target="_blank" rel="noreferrer" className="text-cockpit-teal hover:underline">
                  [source]
                </a>
              </>
            ) : null}
          </li>
        ))}
      </ul>
    </div>
  );
}

function CompSiteDossierPanel({ dossier }: { dossier: CompSiteDossierPayload }) {
  if (dossier.dossier_status === "pending" && !dossier.science_summary) {
    return null;
  }
  return (
    <div className="mt-3 space-y-3 rounded-md border border-border/50 bg-muted/20 px-3 py-3">
      <div className="flex flex-wrap items-center gap-2">
        <p className="text-xs font-medium text-foreground">Company site dossier</p>
        <Badge variant="outline" className="text-[10px] font-normal capitalize">
          {dossier.dossier_status.replace(/_/g, " ")}
        </Badge>
        {dossier.comparable_fit ? (
          <Badge variant="secondary" className="text-[10px] font-normal capitalize">
            {dossier.comparable_fit} comp
          </Badge>
        ) : null}
      </div>
      {dossier.ri_parallel ? (
        <p className="text-sm leading-relaxed text-muted-foreground">{dossier.ri_parallel}</p>
      ) : null}
      {dossier.science_summary ? (
        <p className="text-sm text-muted-foreground">{dossier.science_summary}</p>
      ) : null}
      <SiteMapLinks siteMap={dossier.site_map} />
      {dossier.key_publications.length ? (
        <ul className="space-y-1 text-sm">
          {dossier.key_publications.map((pub) => (
            <li key={pub.url || pub.title}>
              <a href={pub.url} target="_blank" rel="noreferrer" className="text-cockpit-teal hover:underline">
                {pub.title}
              </a>
            </li>
          ))}
        </ul>
      ) : null}
      <CitedList title="Clinical / regulatory" items={dossier.clinical_milestones} />
      <CitedList title="Reimbursement / access" items={dossier.reimbursement_notes} />
      <CitedList title="KOL / adoption signals" items={dossier.kol_signals} />
    </div>
  );
}

function roleBadgeVariant(role: string): "default" | "secondary" | "outline" {
  const r = role.toLowerCase();
  if (r === "therapeutic") return "default";
  if (r === "diagnostic") return "secondary";
  return "outline";
}

function PrecedentCard({ p }: { p: CombinedPrecedent }) {
  const anchor = Number(p.value_anchor_usd) || 0;
  const status = (p.validation_status || "suggested").toLowerCase();
  const role = (p.role || "").trim();

  return (
    <li className="rounded-lg border border-border/60 bg-card/50 px-4 py-3 space-y-2">
      <div className="flex flex-wrap items-start justify-between gap-2">
        <div>
          <p className="font-medium leading-snug">{p.name}</p>
          <p className="text-xs text-muted-foreground capitalize">
            {p.type.replace(/_/g, " ")}
            {p.stage ? ` · ${p.stage.replace(/_/g, " ")}` : ""}
          </p>
        </div>
        <div className="flex flex-wrap gap-1 shrink-0">
          {role ? (
            <Badge variant={roleBadgeVariant(role)} className="text-[10px] uppercase">
              {role}
            </Badge>
          ) : null}
          <Badge variant={validationBadgeVariant(status)} className="text-[10px] uppercase">
            {status}
          </Badge>
        </div>
      </div>
      {p.notes && p.notes !== p.inferred_financing ? (
        <p className="text-sm text-muted-foreground">{p.notes}</p>
      ) : null}
      {anchor > 0 ? (
        <p className="text-sm">
          <span className="font-semibold text-foreground">{formatUsd(anchor)}</span>
          <span className="text-muted-foreground"> · {formatValueAnchorType(p.value_anchor_type)}</span>
        </p>
      ) : null}
      {p.inferred_development ? (
        <p className="text-sm text-muted-foreground">
          <span className="text-foreground/80">Development:</span> {p.inferred_development}
        </p>
      ) : null}
      {p.inferred_financing ? (
        <p className="text-sm text-muted-foreground">
          <span className="text-foreground/80">Financing:</span> {p.inferred_financing}
        </p>
      ) : null}
      <ComparableCitationLinks
        companyUrl={p.url}
        valueSourceUrl={p.value_source_url}
        supportingCitations={p.supporting_citations}
      />
      {p.site_dossier ? <CompSiteDossierPanel dossier={p.site_dossier} /> : null}
    </li>
  );
}

export { PrecedentCard, CompSiteDossierPanel };

function CompRollupBlock({ rollup }: { rollup: ExhibitMarket["comp_rollup"] }) {
  if (!rollup) return null;
  const blocks = [
    { label: "Clinical precedent", value: rollup.clinical_path },
    { label: "Reimbursement precedent", value: rollup.reimbursement_path },
    { label: "KOL pattern", value: rollup.kol_pattern },
  ].filter((b) => b.value);
  if (!blocks.length) return null;
  return (
    <div className="space-y-2">
      {blocks.map((block) => (
        <p key={block.label} className="text-sm text-muted-foreground">
          <span className="font-medium text-foreground">{block.label}: </span>
          {block.value}
        </p>
      ))}
    </div>
  );
}

export function CompSiteHighlight({ market }: { market: ExhibitMarket }) {
  const withDossier = precedentsWithDossiers(market.precedents);
  const lead = withDossier[0];
  const dossier = lead?.site_dossier;
  const rollup = market.comp_rollup;
  const hasRollup = Boolean(
    rollup?.clinical_path || rollup?.reimbursement_path || rollup?.kol_pattern,
  );

  if (!dossier && !hasRollup) return null;

  return (
    <section
      id="comp-site-highlight"
      className="space-y-4 rounded-lg border border-cockpit-teal/35 bg-cockpit-teal/5 px-5 py-5"
    >
      <div className="flex flex-wrap items-center gap-2">
        <h2 className="text-lg font-semibold">Comparator company dossier</h2>
        {dossier ? (
          <Badge variant="outline" className="text-[10px] font-normal capitalize">
            {dossier.dossier_status.replace(/_/g, " ")}
          </Badge>
        ) : null}
        <a href="#market" className="ml-auto text-xs text-cockpit-teal hover:underline">
          Full comparables ↓
        </a>
      </div>
      {lead ? (
        <div className="space-y-1">
          <p className="text-sm font-medium text-foreground">Lead site comp: {lead.name}</p>
          <ComparableCitationLinks companyUrl={lead.url} valueSourceUrl={lead.value_source_url} />
        </div>
      ) : null}
      {hasRollup ? <CompRollupBlock rollup={rollup} /> : null}
      {dossier ? <CompSiteDossierPanel dossier={dossier} /> : null}
    </section>
  );
}
