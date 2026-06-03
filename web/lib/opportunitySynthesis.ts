import type { CasePacket } from "@/types/artifacts";
import type { OpportunityIndexRow, OpportunityProfile } from "@/types/opportunities";
import { formatUsd } from "@/lib/format";
import { cleanOpportunityTitle } from "@/lib/format";

export function buildOpportunitySynthesis(
  indexRow: OpportunityIndexRow,
  profile: OpportunityProfile | null,
  packet: CasePacket,
): string {
  const title = cleanOpportunityTitle(
    profile?.llm_inferred_label || indexRow.llm_inferred_label || indexRow.display_name,
  );
  const ipCount = profile?.ip_assets?.length ?? indexRow.patent_count ?? 0;
  const physicians = packet.riPhysicianMatch?.candidate_physicians ?? [];
  const specialties = [
    ...new Set(physicians.map((p) => p.specialty).filter(Boolean) as string[]),
  ].slice(0, 4);
  const event =
    packet.riClinicalInflection?.best_validation_event ??
    packet.riClinicalInflection?.candidate_validation_events?.[0];
  const study = event?.study_type ?? "clinical validation study";
  const gap = formatUsd(indexRow.capital_gap_usd);

  const specialtyPhrase =
    specialties.length > 0
      ? `a Rhode Island physician syndicate spanning ${specialties.join(", ")}`
      : "matched Rhode Island physician expertise";

  const ipPhrase =
    ipCount > 1
      ? `${ipCount} related patent assets`
      : ipCount === 1
        ? "anchored patent protection"
        : "RI-linked intellectual property";

  return (
    `${title} combines ${ipPhrase}, ${specialtyPhrase}, and a ${study.toLowerCase()} ` +
    `as the near-term development path. The financing package targets ${gap} with ` +
    `50% physician syndicate capital and 50% Slater SSBCI match once the clinical path is staffed.`
  );
}

export function pillarSummary(indexRow: OpportunityIndexRow, packet: CasePacket) {
  const event =
    packet.riClinicalInflection?.best_validation_event ??
    packet.riClinicalInflection?.candidate_validation_events?.[0];
  return {
    ipCount: indexRow.patent_count ?? 0,
    physicianCount: indexRow.physician_candidate_count ?? 0,
    clinicalLabel: event?.study_type ?? indexRow.best_template_id ?? "Validation pilot",
    clinicalWeeks: event?.duration_weeks ?? indexRow.estimated_duration_weeks,
    clinicalCost: event?.cost_usd ?? indexRow.estimated_cost_usd,
  };
}
