import type { ExhibitEvidence, ExhibitPublication } from "@/types/combined";
import { Badge } from "@/components/ui/badge";

interface OpportunityEvidenceProps {
  evidence: ExhibitEvidence;
}

function publicationHref(pub: ExhibitPublication): string {
  const url = (pub.url ?? "").trim();
  if (url) return url;
  const pmid = String(pub.pmid ?? "").trim();
  if (pmid) return `https://pubmed.ncbi.nlm.nih.gov/${pmid}/`;
  return "";
}

export function OpportunityEvidence({ evidence }: OpportunityEvidenceProps) {
  const pubs = evidence.publications ?? [];
  const trials = evidence.trials ?? [];

  if (evidence.status === "unavailable") {
    return (
      <p className="text-sm text-muted-foreground">
        {evidence.narrative ||
          "BioMCP is not installed. Run `pip install biomcp` then `npm run enrich:ri:biomcp` to fetch publications and trials."}
      </p>
    );
  }

  if (!pubs.length && !trials.length) {
    return (
      <p className="text-sm text-muted-foreground">
        {evidence.narrative || "No publications or trials fetched yet for this program."}
        {evidence.search_terms?.length ? (
          <span className="mt-2 block text-xs">
            Search terms: {evidence.search_terms.join(" · ")}
          </span>
        ) : null}
      </p>
    );
  }

  return (
    <div className="space-y-4">
      {evidence.narrative ? (
        <p className="text-sm leading-relaxed text-muted-foreground">{evidence.narrative}</p>
      ) : null}
      {evidence.search_terms?.length ? (
        <p className="text-xs text-muted-foreground">
          BioMCP queries: {evidence.search_terms.join(" · ")}
        </p>
      ) : null}
      {evidence.related_case_ids && evidence.related_case_ids.length > 0 ? (
        <p className="text-xs text-muted-foreground">
          Related RI programs (shared patent inventors):{" "}
          {evidence.related_case_ids.slice(0, 8).join(", ")}
          {evidence.related_case_ids.length > 8 ? "…" : ""}
        </p>
      ) : null}
      {pubs.length > 0 ? (
        <div className="space-y-3">
          <h3 className="text-sm font-medium text-foreground">Publications</h3>
          <ul className="space-y-3">
            {pubs.map((pub, index) => {
              const href = publicationHref(pub);
              return (
              <li
                key={`${pub.pmid || pub.title}-${index}`}
                className="rounded-lg border border-border/60 bg-card/50 px-4 py-3 space-y-1"
              >
                <p className="font-medium leading-snug text-sm">{pub.title}</p>
                <p className="text-xs text-muted-foreground">
                  {[pub.journal, pub.publication_date].filter(Boolean).join(" · ")}
                  {pub.pmid ? ` · PMID ${pub.pmid}` : ""}
                </p>
                {pub.patent_link?.matched_inventor_surnames?.length ? (
                  <p className="text-xs text-cockpit-teal">
                    Patent-linked via {pub.patent_link.matched_inventor_surnames.join(", ")}
                    {pub.patent_link.primary_display_key
                      ? ` · ${pub.patent_link.primary_display_key}`
                      : ""}
                  </p>
                ) : null}
                {pub.abstract_snippet ? (
                  <p className="text-sm text-muted-foreground line-clamp-3">{pub.abstract_snippet}</p>
                ) : null}
                {href ? (
                  <a
                    href={href}
                    target="_blank"
                    rel="noreferrer"
                    className="inline-block text-sm text-cockpit-teal hover:underline"
                  >
                    PubMed / source
                  </a>
                ) : null}
              </li>
            );
            })}
          </ul>
        </div>
      ) : null}
      {trials.length > 0 ? (
        <div className="space-y-3">
          <h3 className="text-sm font-medium text-foreground">Related trials</h3>
          <ul className="space-y-2">
            {trials.map((trial) => (
              <li
                key={trial.nct_id || trial.title}
                className="rounded-lg border border-border/60 bg-card/50 px-4 py-2.5 text-sm"
              >
                <p className="font-medium">{trial.title}</p>
                <p className="text-xs text-muted-foreground mt-1">
                  {[trial.nct_id, trial.phase, trial.status].filter(Boolean).join(" · ")}
                </p>
                {trial.url ? (
                  <a
                    href={trial.url}
                    target="_blank"
                    rel="noreferrer"
                    className="text-cockpit-teal hover:underline text-xs"
                  >
                    ClinicalTrials.gov
                  </a>
                ) : null}
              </li>
            ))}
          </ul>
        </div>
      ) : null}
      {evidence.warnings?.length ? (
        <div className="space-y-1">
          {evidence.warnings.map((w) => (
            <Badge key={w} variant="outline" className="font-normal text-xs">
              {w}
            </Badge>
          ))}
        </div>
      ) : null}
    </div>
  );
}
