import type { ExhibitHeadline, ExhibitMeta } from "@/types/combined";
import { Badge } from "@/components/ui/badge";

interface OpportunityFramingBannerProps {
  headline: ExhibitHeadline;
  meta: ExhibitMeta;
}

export function OpportunityFramingBanner({ headline, meta }: OpportunityFramingBannerProps) {
  const pending = (meta.review_status || "pending").toLowerCase() !== "approved";

  return (
    <div className="space-y-3">
      {pending ? (
        <div
          className="rounded-lg border border-amber-500/30 bg-amber-500/5 px-4 py-3 text-sm leading-relaxed"
          role="status"
        >
          <strong className="font-medium text-foreground">Diligence in progress.</strong>{" "}
          Compiled from the enrichment catalog — curator approval required before investor
          distribution. Citations and syndicate matches may include suggested (unverified) rows.
        </div>
      ) : null}
      <div className="flex flex-wrap gap-2 text-xs text-muted-foreground">
        {headline.ri_institution ? (
          <Badge variant="outline" className="font-normal">
            {headline.ri_institution}
          </Badge>
        ) : null}
        {headline.company && headline.company !== headline.ri_institution ? (
          <Badge variant="outline" className="font-normal">
            {headline.company}
          </Badge>
        ) : null}
        {headline.inventor_lead ? (
          <span>
            Inventor: <span className="text-foreground">{headline.inventor_lead}</span>
          </span>
        ) : null}
        {headline.physician_lead_name ? (
          <span>
            Proposed syndicate lead:{" "}
            <span className="text-foreground">{headline.physician_lead_name}</span>
          </span>
        ) : null}
      </div>
    </div>
  );
}
