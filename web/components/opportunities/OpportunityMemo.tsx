import Link from "next/link";
import type { ReactNode } from "react";
import type { OpportunityExhibit } from "@/types/combined";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { OpportunityFramingBanner } from "@/components/opportunities/OpportunityFramingBanner";
import { ComparableCitationLinks } from "@/components/opportunities/ComparableCitationLinks";
import { formatUsd, formatValueAnchorType } from "@/lib/format";
import { OpportunityEvidence } from "@/components/opportunities/OpportunityEvidence";
import { OpportunityInvestmentPackage } from "@/components/opportunities/OpportunityInvestmentPackage";
import { OpportunityPrecedents } from "@/components/opportunities/OpportunityPrecedents";
import { CompSiteHighlight } from "@/components/opportunities/CompSiteDossier";

interface OpportunityMemoProps {
  exhibit: OpportunityExhibit;
}

function FramingStrip({ exhibit }: { exhibit: OpportunityExhibit }) {
  const f = exhibit.financing;
  const items = [
    { label: "Lead pillar", value: f.lead_pillar_label },
    { label: "Financing", value: f.structure_label },
    { label: "Audience", value: f.audience_label },
    { label: "Development ask", value: f.development_ask_label },
  ].filter((item) => item.value);

  if (!items.length) return null;

  return (
    <div className="flex flex-wrap gap-2" aria-label="Framing decisions">
      {items.map((item) => (
        <Badge key={item.label} variant="outline" className="font-normal">
          <span className="text-muted-foreground">{item.label}:</span> {item.value}
        </Badge>
      ))}
    </div>
  );
}

export function OpportunityMemo({ exhibit }: OpportunityMemoProps) {
  const {
    headline,
    snapshot,
    technology,
    evidence,
    market,
    syndicate,
    clinical,
    financing,
    presentation,
  } = exhibit;

  const sectionContent: Record<string, ReactNode> = {
    technology: (
      <div className="space-y-4">
        <p className="text-sm text-muted-foreground">{technology.summary}</p>
        {technology.patents.length ? (
          <ul className="space-y-3">
            {technology.patents.map((asset) => (
              <li
                key={asset.lens_id || asset.title}
                className="rounded-lg border border-border/60 bg-card/50 px-4 py-3"
              >
                <p className="font-medium leading-snug">{asset.title}</p>
                {asset.display_key ? (
                  <p className="mt-1 text-xs text-cockpit-teal">{asset.display_key}</p>
                ) : null}
                {asset.owners ? (
                  <p className="mt-1 text-sm text-muted-foreground">{asset.owners}</p>
                ) : null}
                {asset.url ? (
                  <a
                    href={asset.url}
                    target="_blank"
                    rel="noreferrer"
                    className="mt-2 inline-block text-sm text-cockpit-teal hover:underline"
                  >
                    View patent record
                  </a>
                ) : null}
              </li>
            ))}
          </ul>
        ) : (
          <p className="text-sm text-muted-foreground">No linked patent assets.</p>
        )}
      </div>
    ),
    evidence: <OpportunityEvidence evidence={evidence} />,
    market: (
      <OpportunityPrecedents
        market={market}
        valueBandLabel={snapshot.value_band.label}
        verifiedCount={snapshot.value_band.verified_anchor_count}
      />
    ),
    syndicate: (
      <div className="space-y-4">
        <p className="text-sm leading-relaxed text-muted-foreground">
          {syndicate.roster.length
            ? `${syndicate.summary} Co-investors oversee clinical credibility, pilot design, and local adoption — not passive capital.`
            : `${syndicate.summary} Target: Rhode Island physician syndicate paired with Slater SSBCI for clinical oversight.`}
        </p>
        {(syndicate.staffing_feasibility_score_0_100 ?? 0) > 0 ||
        (syndicate.required_clinical_tags?.length ?? 0) > 0 ? (
          <div className="flex flex-wrap gap-2 text-xs">
            {(syndicate.staffing_feasibility_score_0_100 ?? 0) > 0 ? (
              <Badge variant="outline" className="font-normal">
                Staffing feasibility: {syndicate.staffing_feasibility_score_0_100?.toFixed(0)}/100
              </Badge>
            ) : null}
            {syndicate.required_clinical_tags?.slice(0, 6).map((tag) => (
              <Badge key={tag} variant="outline" className="font-normal text-muted-foreground">
                {tag.replace(/_/g, " ")}
              </Badge>
            ))}
          </div>
        ) : null}
        {syndicate.roster.length ? (
          <div className="overflow-x-auto rounded-lg border border-border/60">
            <table className="w-full min-w-[520px] text-left text-sm">
              <thead className="border-b border-border/60 bg-muted/20 text-xs uppercase text-muted-foreground">
                <tr>
                  <th className="px-4 py-2 font-medium">Name</th>
                  <th className="px-4 py-2 font-medium">Specialty</th>
                  <th className="px-4 py-2 font-medium">Institution</th>
                  <th className="px-4 py-2 font-medium">Role</th>
                </tr>
              </thead>
              <tbody>
                {syndicate.roster.map((p, index) => (
                  <tr
                    key={`${p.physician_id || p.name}-${p.is_lead}-${index}`}
                    className="border-b border-border/40"
                  >
                    <td className="px-4 py-2.5 font-medium">
                      {p.profile_url ? (
                        <a
                          href={p.profile_url}
                          target="_blank"
                          rel="noreferrer"
                          className="text-cockpit-teal hover:underline"
                        >
                          {p.name}
                        </a>
                      ) : (
                        p.name
                      )}
                    </td>
                    <td className="px-4 py-2.5 text-muted-foreground">{p.specialty || "—"}</td>
                    <td className="px-4 py-2.5 text-muted-foreground">{p.institution || "—"}</td>
                    <td className="px-4 py-2.5 capitalize">
                      {p.is_lead === "true"
                        ? "Lead"
                        : Array.isArray(p.roles_matched)
                          ? p.roles_matched.join(", ")
                          : String(p.roles_matched || "").replace(/\|/g, ", ")}
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        ) : (
          <p className="text-sm text-muted-foreground">No matched physicians on roster yet.</p>
        )}
        {(syndicate.candidate_physicians?.length ?? 0) > 0 ? (
          <div className="space-y-2">
            <h3 className="text-sm font-medium text-foreground">NPI-matched candidates</h3>
            <p className="text-xs text-muted-foreground">
              Ranked by clinical-tag overlap and role fit (CMS NPI registry). Promote in curate after
              conflict review.
            </p>
            <ul className="space-y-2">
              {syndicate.candidate_physicians!.slice(0, 8).map((p) => (
                <li
                  key={`${p.physician_id}-${p.name}`}
                  className="rounded-lg border border-border/60 bg-card/50 px-4 py-2.5 text-sm"
                >
                  <div className="flex flex-wrap items-baseline justify-between gap-2">
                    <span className="font-medium">{p.name}</span>
                    {p.match_score_0_100 != null ? (
                      <span className="text-xs text-cockpit-teal">
                        Match {p.match_score_0_100}/100
                      </span>
                    ) : null}
                  </div>
                  <p className="text-xs text-muted-foreground mt-1">
                    {[p.specialty, p.institution].filter(Boolean).join(" · ")}
                  </p>
                  {p.clinical_tags_matched?.length ? (
                    <p className="text-xs text-muted-foreground mt-1">
                      Tags: {p.clinical_tags_matched.join(", ")}
                    </p>
                  ) : null}
                </li>
              ))}
            </ul>
          </div>
        ) : null}
        {syndicate.staffing_gaps?.length ? (
          <p className="text-xs text-muted-foreground">
            Role gaps: {syndicate.staffing_gaps.join(", ")}
          </p>
        ) : null}
      </div>
    ),
    clinical: clinical.has_plan ? (
      <Card className="border-border/70 bg-card/60">
        <CardHeader className="pb-2">
          <CardTitle className="text-base">{clinical.study_type}</CardTitle>
        </CardHeader>
        <CardContent className="grid gap-2 text-sm sm:grid-cols-2">
          {clinical.primary_endpoint ? (
            <p>
              <span className="text-muted-foreground">Primary endpoint:</span>{" "}
              {clinical.primary_endpoint}
            </p>
          ) : null}
          <p>
            <span className="text-muted-foreground">Duration:</span> {clinical.duration_weeks}{" "}
            weeks
          </p>
          <p>
            <span className="text-muted-foreground">Estimated cost:</span>{" "}
            {formatUsd(clinical.cost_usd)}
          </p>
          {clinical.path_notes ? (
            <p className="sm:col-span-2 text-muted-foreground">{clinical.path_notes}</p>
          ) : null}
        </CardContent>
      </Card>
    ) : (
      <p className="text-sm text-muted-foreground">Clinical path to be defined in enrichment CSV.</p>
    ),
  };

  return (
    <article className="space-y-10">
      <header className="space-y-4 border-b border-border/60 pb-8">
        <p className="text-xs uppercase tracking-wider text-cockpit-teal">
          {headline.opportunity_type_label} · {headline.geography}
          {headline.catalog_tier ? ` · Tier ${headline.catalog_tier}` : ""}
        </p>
        <h1 className="text-3xl font-semibold tracking-tight text-balance">{headline.title}</h1>
        {headline.tagline && headline.tagline !== headline.title ? (
          <p className="text-sm text-muted-foreground">{headline.tagline}</p>
        ) : null}
        <OpportunityFramingBanner headline={headline} meta={exhibit.meta} />
        <p className="max-w-3xl text-base leading-relaxed text-muted-foreground">{headline.thesis}</p>
        <FramingStrip exhibit={exhibit} />
        {headline.data_caveat ? (
          <Badge variant="warning" className="font-normal">
            {headline.data_caveat}
          </Badge>
        ) : null}
        {headline.indication &&
        headline.indication.toLowerCase() !== headline.title.toLowerCase() ? (
          <p className="text-sm text-muted-foreground">
            <span className="font-medium text-foreground">Indication: </span>
            {headline.indication}
          </p>
        ) : null}
      </header>

      {/* At-a-glance snapshot */}
      <section className="grid gap-3 rounded-lg border border-border/60 bg-muted/20 p-4 sm:grid-cols-2 lg:grid-cols-4">
        <div>
          <p className="text-xs text-muted-foreground">RI co-investment package</p>
          <p className="text-lg font-semibold">{formatUsd(snapshot.capital_gap_usd)}</p>
          <p className="text-xs text-muted-foreground mt-0.5">
            {formatUsd(snapshot.physician_share_usd)} physician ·{" "}
            {formatUsd(snapshot.slater_share_usd)} Slater
          </p>
        </div>
        {snapshot.value_band.label ? (
          <div>
            <p className="text-xs text-muted-foreground">Financing precedent</p>
            <p className="text-sm font-semibold leading-snug">{snapshot.value_band.label}</p>
            {snapshot.value_band.verified_anchor_count > 0 ? (
              <p className="text-xs text-muted-foreground">
                {snapshot.value_band.verified_anchor_count} verified anchor
                {snapshot.value_band.verified_anchor_count === 1 ? "" : "s"}
              </p>
            ) : null}
          </div>
        ) : null}
        {snapshot.lead_comparable?.name ? (
          <div className="space-y-1">
            <p className="text-xs text-muted-foreground">Lead comparable</p>
            <p className="text-sm font-semibold leading-snug">{snapshot.lead_comparable.name}</p>
            {Number(snapshot.lead_comparable.value_anchor_usd) > 0 ? (
              <p className="text-xs text-muted-foreground">
                {formatUsd(Number(snapshot.lead_comparable.value_anchor_usd))}
                {snapshot.lead_comparable.value_anchor_type
                  ? ` · ${formatValueAnchorType(snapshot.lead_comparable.value_anchor_type)}`
                  : ""}
              </p>
            ) : null}
            <ComparableCitationLinks
              companyUrl={snapshot.lead_comparable.url}
              valueSourceUrl={snapshot.lead_comparable.value_source_url}
            />
          </div>
        ) : null}
        <div>
          <p className="text-xs text-muted-foreground">Stage</p>
          <p className="text-sm font-semibold capitalize">{headline.development_stage}</p>
        </div>
      </section>

      <CompSiteHighlight market={market} />

      {presentation.sections.map((section) => (
        <section key={section.id} id={section.id} className="space-y-4">
          <h2 className="text-lg font-semibold">{section.title}</h2>
          {sectionContent[section.id]}
        </section>
      ))}

      <OpportunityInvestmentPackage
        snapshot={snapshot}
        clinical={clinical}
        financing={financing}
      />

      {exhibit.meta.ri_notes ? (
        <p className="border-t border-border/40 pt-4 text-xs text-muted-foreground">
          Curator notes: {exhibit.meta.ri_notes}
        </p>
      ) : null}

      <footer className="flex flex-wrap gap-2 pt-2">
        <Button asChild variant="outline" size="sm">
          <Link href="/opportunities">All opportunities</Link>
        </Button>
      </footer>
    </article>
  );
}
