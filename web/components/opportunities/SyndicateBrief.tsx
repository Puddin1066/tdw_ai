"use client";

import Link from "next/link";
import { useMemo, useState } from "react";
import type { CasePacket } from "@/types/artifacts";
import type { OpportunityIndexRow, OpportunityProfile } from "@/types/opportunities";
import { ReadinessBadge } from "@/components/opportunities/ReadinessBadge";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card";
import { formatUsd, opportunityTypeLabel } from "@/lib/format";

interface SyndicateBriefProps {
  indexRow: OpportunityIndexRow;
  profile: OpportunityProfile | null;
  packet: CasePacket;
}

export function SyndicateBrief({ indexRow, profile, packet }: SyndicateBriefProps) {
  const readiness = packet.riFinancingReadiness;
  const physicians = packet.riPhysicianMatch;
  const inflection = packet.riClinicalInflection;
  const capital = packet.riCapitalMatch;

  const events = inflection?.candidate_validation_events ?? [];
  const bestId = inflection?.best_validation_event?.template_id ?? events[0]?.template_id ?? null;
  const [selectedTemplateId, setSelectedTemplateId] = useState<string | null>(bestId);

  const selectedEvent = useMemo(() => {
    if (!inflection) return null;
    if (selectedTemplateId) {
      const match = events.find((e) => e.template_id === selectedTemplateId);
      if (match) return match;
    }
    return inflection.best_validation_event ?? events[0] ?? null;
  }, [inflection, events, selectedTemplateId]);

  const lead =
    profile?.ri_physician_lead && profile.ri_physician_lead !== "TBD"
      ? profile.ri_physician_lead
      : physicians?.candidate_physicians?.[0]?.name ?? "TBD (top match)";

  return (
    <div className="space-y-8">
      <section className="space-y-4">
        <div className="flex flex-wrap items-start justify-between gap-4">
          <div>
            <p className="font-mono text-xs uppercase tracking-wider text-cockpit-teal">
              {indexRow.case_id}
            </p>
            <h1 className="text-3xl font-semibold tracking-tight">
              {profile?.llm_inferred_label || indexRow.display_name}
            </h1>
            <p className="mt-2 max-w-3xl text-sm text-muted-foreground">
              {indexRow.target} · {indexRow.indication} · {opportunityTypeLabel(indexRow.opportunity_type)}{" "}
              · {indexRow.development_stage} · {indexRow.geography}
            </p>
          </div>
          {readiness ? (
            <ReadinessBadge
              state={readiness.financing_readiness_state}
              score={readiness.financing_readiness_score_0_100}
            />
          ) : null}
        </div>

        {readiness ? (
          <div className="grid gap-3 sm:grid-cols-2 lg:grid-cols-4">
            {[
              { label: "Clinical inflection", value: readiness.clinical_inflection_score_0_100 },
              { label: "Staffing feasibility", value: readiness.staffing_feasibility_score_0_100 },
              { label: "Capital path", value: readiness.capital_path_score_0_100 },
              { label: "RI anchor", value: readiness.ri_anchor_score_0_100 },
            ].map((item) => (
              <div
                key={item.label}
                className="rounded-md border border-border/60 bg-card/50 px-3 py-2"
              >
                <p className="text-xs text-muted-foreground">{item.label}</p>
                <p className="text-lg font-semibold">{item.value.toFixed(1)}</p>
              </div>
            ))}
          </div>
        ) : null}

        {readiness?.next_actions?.length ? (
          <Card className="border-border/70 bg-card/70">
            <CardHeader className="pb-2">
              <CardTitle className="text-base">Next actions</CardTitle>
            </CardHeader>
            <CardContent>
              <ul className="list-inside list-disc space-y-1 text-sm text-muted-foreground">
                {readiness.next_actions.map((action) => (
                  <li key={action}>{action}</li>
                ))}
              </ul>
            </CardContent>
          </Card>
        ) : null}

        <div className="flex flex-wrap gap-2">
          {readiness?.mocked ? <Badge variant="warning">Mocked / static CSV inputs</Badge> : null}
          <Badge variant="outline">Lead: {lead}</Badge>
          <Badge variant="outline">Capital gap {formatUsd(indexRow.capital_gap_usd)}</Badge>
        </div>
      </section>

      <section id="technology" className="space-y-3">
        <h2 className="text-xl font-semibold">Technology & IP</h2>
        {profile?.ip_assets?.length ? (
          <div className="grid gap-3 md:grid-cols-2">
            {profile.ip_assets.map((asset) => (
              <Card key={asset.asset_id ?? asset.lens_id} className="border-border/70 bg-card/70">
                <CardHeader className="pb-2">
                  <CardTitle className="text-sm leading-snug">{asset.title}</CardTitle>
                  <CardDescription>{asset.owners}</CardDescription>
                </CardHeader>
                <CardContent className="text-xs text-muted-foreground">
                  <p>Status: {asset.legal_status}</p>
                  {asset.url ? (
                    <a
                      href={asset.url}
                      target="_blank"
                      rel="noreferrer"
                      className="text-cockpit-teal hover:underline"
                    >
                      Lens record
                    </a>
                  ) : null}
                </CardContent>
              </Card>
            ))}
          </div>
        ) : (
          <p className="text-sm text-muted-foreground">No IP assets linked in profile.</p>
        )}
        {profile?.ri_notes ? (
          <p className="text-sm text-muted-foreground">{profile.ri_notes}</p>
        ) : null}
      </section>

      <section id="physicians" className="space-y-3">
        <h2 className="text-xl font-semibold">Physician syndicate</h2>
        {physicians ? (
          <>
            {physicians.required_clinical_tags?.length ? (
              <p className="text-sm text-muted-foreground">
                Required clinical tags: {physicians.required_clinical_tags.join(", ")}
              </p>
            ) : null}
            <div className="flex flex-wrap gap-2">
              {physicians.required_roles.map((role) => (
                <Badge
                  key={role}
                  variant={physicians.role_coverage[role] ? "success" : "danger"}
                >
                  {role} {physicians.role_coverage[role] ? "✓" : "gap"}
                </Badge>
              ))}
            </div>
            <p className="text-sm text-muted-foreground">
              Specialties: {physicians.required_specialties.join(", ")} · Feasibility{" "}
              {physicians.staffing_feasibility_score_0_100.toFixed(0)}/100
            </p>
            <div className="overflow-x-auto rounded-md border border-border/60">
              <table className="w-full min-w-[640px] text-left text-sm">
                <thead className="border-b border-border/60 bg-muted/30 text-xs uppercase text-muted-foreground">
                  <tr>
                    <th className="px-3 py-2">Name</th>
                    <th className="px-3 py-2">Specialty</th>
                    <th className="px-3 py-2">Institution</th>
                    <th className="px-3 py-2">Roles</th>
                    <th className="px-3 py-2">Clinical fit</th>
                    <th className="px-3 py-2">Match</th>
                    <th className="px-3 py-2">Interest</th>
                  </tr>
                </thead>
                <tbody>
                  {physicians.candidate_physicians.map((p, index) => (
                    <tr
                      key={`${p.physician_id ?? p.name}-${index}`}
                      className="border-b border-border/40"
                    >
                      <td className="px-3 py-2 font-medium">{p.name}</td>
                      <td className="px-3 py-2 text-muted-foreground">{p.specialty}</td>
                      <td className="px-3 py-2 text-muted-foreground">{p.institution}</td>
                      <td className="px-3 py-2">{(p.roles_matched ?? []).join(", ")}</td>
                      <td className="px-3 py-2 text-xs text-muted-foreground">
                        {(p.clinical_tags_matched ?? []).join(", ") || "—"}
                        {p.relevance_rationale ? (
                          <span className="mt-0.5 block text-[10px]">{p.relevance_rationale}</span>
                        ) : null}
                      </td>
                      <td className="px-3 py-2">{p.match_score_0_100?.toFixed(0)}</td>
                      <td className="px-3 py-2 capitalize">{p.investor_interest_level}</td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          </>
        ) : (
          <p className="text-sm text-muted-foreground">No physician match artifact.</p>
        )}
      </section>

      <section id="clinical" className="space-y-3">
        <h2 className="text-xl font-semibold">Clinical enablement</h2>
        {inflection ? (
          <>
            <p className="text-sm font-medium text-foreground">{inflection.financing_milestone}</p>
            {events.length > 1 ? (
              <div className="flex flex-wrap gap-2">
                {events.map((event) => (
                  <button
                    key={event.template_id}
                    type="button"
                    onClick={() => setSelectedTemplateId(event.template_id ?? null)}
                    className={`rounded border px-2 py-1 text-xs ${
                      selectedEvent?.template_id === event.template_id
                        ? "border-cockpit-teal/60 bg-cockpit-teal/10 text-cockpit-teal"
                        : "border-border/60 text-muted-foreground"
                    }`}
                  >
                    {event.template_id}
                  </button>
                ))}
              </div>
            ) : null}
            {selectedEvent ? (
              <Card className="border-border/70 bg-card/70">
                <CardContent className="grid gap-2 pt-4 text-sm sm:grid-cols-2">
                  <p>
                    <span className="text-muted-foreground">Study:</span> {selectedEvent.study_type}
                  </p>
                  <p>
                    <span className="text-muted-foreground">Endpoint:</span>{" "}
                    {selectedEvent.primary_endpoint_type}
                  </p>
                  <p>
                    <span className="text-muted-foreground">Duration:</span>{" "}
                    {selectedEvent.duration_weeks} weeks
                  </p>
                  <p>
                    <span className="text-muted-foreground">Est. cost:</span>{" "}
                    {formatUsd(selectedEvent.cost_usd)}
                  </p>
                  <p className="sm:col-span-2">
                    <span className="text-muted-foreground">Roles:</span>{" "}
                    {(selectedEvent.required_roles ?? []).join(", ")}
                  </p>
                </CardContent>
              </Card>
            ) : null}
          </>
        ) : (
          <p className="text-sm text-muted-foreground">No clinical inflection artifact.</p>
        )}
      </section>

      <section id="capital" className="space-y-3">
        <h2 className="text-xl font-semibold">Financing structure (50 / 50)</h2>
        {capital ? (
          <>
            <div className="space-y-2">
              {(capital.potential_sources ?? []).map((source) => {
                const total = capital.private_match_needed_usd || indexRow.capital_gap_usd || 1;
                const pct = Math.min(
                  100,
                  Math.round(((source.projected_commitment_usd ?? 0) / total) * 100),
                );
                return (
                  <div key={source.source_id} className="space-y-1">
                    <div className="flex justify-between text-sm">
                      <span>{source.source_name}</span>
                      <span className="text-muted-foreground">
                        {formatUsd(source.projected_commitment_usd ?? 0)} · {source.decision_cycle_weeks}{" "}
                        wk cycle
                      </span>
                    </div>
                    <div className="h-2 overflow-hidden rounded-full bg-muted">
                      <div
                        className="h-full bg-cockpit-teal/80"
                        style={{ width: `${pct}%` }}
                      />
                    </div>
                  </div>
                );
              })}
            </div>
            <p className="text-sm text-muted-foreground">
              Committed {formatUsd(capital.capital_committed_usd)} · Gap remaining{" "}
              {formatUsd(capital.capital_gap_remaining_usd)} · Path score{" "}
              {capital.capital_path_score_0_100.toFixed(0)}/100
            </p>
          </>
        ) : (
          <p className="text-sm text-muted-foreground">No capital match artifact.</p>
        )}
      </section>

      <section className="flex flex-wrap gap-2 border-t border-border/60 pt-6">
        <Button asChild variant="outline">
          <Link href="/opportunities">Back to catalog</Link>
        </Button>
        <Button asChild variant="outline">
          <Link href={`/cases/${indexRow.case_id}`}>Deep diligence cockpit</Link>
        </Button>
        <Button asChild>
          <Link href="/evaluate">Portfolio evaluate</Link>
        </Button>
      </section>
    </div>
  );
}
