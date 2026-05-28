import Link from "next/link";
import { SiteNav } from "@/components/SiteNav";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card";
import { formatUsd } from "@/lib/format";
import { loadProgramData } from "@/lib/loadOpportunities";

export default function ProgramPage() {
  const program = loadProgramData();

  if (!program) {
    return (
      <>
        <SiteNav />
        <main className="mx-auto max-w-3xl px-4 py-10">
          <p className="text-sm text-muted-foreground">
            Program data missing. Run <code className="font-mono">npm run publish:ri</code>.
          </p>
        </main>
      </>
    );
  }

  return (
    <>
      <SiteNav />
      <main className="mx-auto max-w-4xl space-y-8 px-4 py-10 sm:px-6 lg:px-8">
        <header className="space-y-3">
          <p className="font-mono text-xs uppercase tracking-widest text-cockpit-teal">Program</p>
          <h1 className="text-3xl font-semibold tracking-tight">{program.title}</h1>
          <p className="text-muted-foreground">{program.subtitle}</p>
          <Button asChild>
            <Link href="/opportunities">Browse {program.stats.opportunity_count} opportunities</Link>
          </Button>
        </header>

        <section className="grid gap-3 sm:grid-cols-3">
          <Card className="border-border/70 bg-card/70">
            <CardHeader className="pb-2">
              <CardDescription>Opportunities</CardDescription>
              <CardTitle>{program.stats.opportunity_count}</CardTitle>
            </CardHeader>
          </Card>
          <Card className="border-border/70 bg-card/70">
            <CardHeader className="pb-2">
              <CardDescription>Financeable now</CardDescription>
              <CardTitle>{program.stats.financeable_now_count}</CardTitle>
            </CardHeader>
          </Card>
          <Card className="border-border/70 bg-card/70">
            <CardHeader className="pb-2">
              <CardDescription>Aggregate capital gap</CardDescription>
              <CardTitle>{formatUsd(program.stats.total_capital_gap_usd)}</CardTitle>
            </CardHeader>
          </Card>
        </section>

        <section className="space-y-4">
          <h2 className="text-xl font-semibold">Source · Select · Support</h2>
          <div className="grid gap-3 md:grid-cols-3">
            {[
              {
                title: "Source",
                body: "RI patents and institutional IP grouped into venture-ready opportunities.",
              },
              {
                title: "Select",
                body: "Matched physician syndicate (roles, specialties) and readiness scoring.",
              },
              {
                title: "Support",
                body: "Validation trial template + 50/50 physician / Slater SSBCI capital structure.",
              },
            ].map((item) => (
              <Card key={item.title} className="border-border/70 bg-card/70">
                <CardHeader>
                  <CardTitle className="text-base">{item.title}</CardTitle>
                  <CardDescription>{item.body}</CardDescription>
                </CardHeader>
              </Card>
            ))}
          </div>
        </section>

        <section className="space-y-3">
          <h2 className="text-xl font-semibold">50 / 50 capital policy</h2>
          <div className="space-y-3">
            {program.capital_sources.map((source) => (
              <Card key={source.source_id} className="border-border/70 bg-card/70">
                <CardContent className="flex flex-wrap items-center justify-between gap-2 pt-4 text-sm">
                  <div>
                    <p className="font-medium">{source.source_name}</p>
                    <p className="text-muted-foreground capitalize">{source.source_type}</p>
                  </div>
                  <div className="text-right text-muted-foreground">
                    <p>
                      {formatUsd(source.check_min_usd)} – {formatUsd(source.check_max_usd)}
                    </p>
                    <p>{source.decision_cycle_weeks} week decision cycle</p>
                  </div>
                  {source.ri_focus ? <Badge variant="success">RI focus</Badge> : null}
                </CardContent>
              </Card>
            ))}
          </div>
        </section>

        <section className="space-y-3">
          <h2 className="text-xl font-semibold">Governance</h2>
          <ul className="space-y-2 text-sm text-muted-foreground">
            {program.governance_rules.map((rule) => (
              <li key={rule.rule_id} className="rounded-md border border-border/60 px-3 py-2">
                <span className="font-medium capitalize text-foreground">{rule.category}</span>
                {": "}
                {rule.rule_text}
              </li>
            ))}
          </ul>
        </section>
      </main>
    </>
  );
}
