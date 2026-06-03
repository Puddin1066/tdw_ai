import { Card, CardDescription, CardHeader, CardTitle } from "@/components/ui/card";
import { formatUsd } from "@/lib/format";

const STEPS = [
  {
    title: "Source",
    body: "Patent-backed technologies from Brown, URI, and RI Hospital — grouped into investable venture cases.",
  },
  {
    title: "Select",
    body: "RI physicians matched by specialty and role: investigator, reviewer, and pilot designer.",
  },
  {
    title: "Package",
    body: "Each case is structured as a ≤$400K co-investment: physician syndicate check plus Slater SSBCI match, sized to cited market comparables.",
  },
] as const;

export function OpportunityHowItWorks() {
  return (
    <section className="space-y-4" aria-labelledby="how-it-works-heading">
      <div className="space-y-1">
        <h2 id="how-it-works-heading" className="text-xl font-semibold tracking-tight">
          Source · Select · Package
        </h2>
        <p className="text-sm text-muted-foreground">
          From university IP to a match-ready Slater co-investment package.
        </p>
      </div>
      <div className="grid gap-3 md:grid-cols-3">
        {STEPS.map((item) => (
          <Card key={item.title} className="border-border/70 bg-card/70">
            <CardHeader>
              <CardTitle className="text-base">{item.title}</CardTitle>
              <CardDescription className="leading-relaxed">{item.body}</CardDescription>
            </CardHeader>
          </Card>
        ))}
      </div>
      <div className="rounded-lg border border-cockpit-teal/30 bg-cockpit-teal/5 px-4 py-3 text-sm leading-relaxed">
        <span className="font-medium text-foreground">50 / 50 capital policy — </span>
        <span className="text-muted-foreground">
          up to {formatUsd(200_000)} physician syndicate + up to {formatUsd(200_000)} Slater Tech Fund
          SSBCI match per package (≤{formatUsd(400_000)} total).
        </span>
      </div>
    </section>
  );
}
