import Link from "next/link";
import { FeaturedOpportunities } from "@/components/opportunities/FeaturedOpportunities";
import { OpportunityCatalog } from "@/components/opportunities/OpportunityCatalog";
import { OpportunityHowItWorks } from "@/components/opportunities/OpportunityHowItWorks";
import { PortfolioStatsBar } from "@/components/opportunities/PortfolioStatsBar";
import { SiteNav } from "@/components/SiteNav";
import { Button } from "@/components/ui/button";
import { computeCatalogStats, selectFeaturedCards } from "@/lib/catalogStats";
import { loadCatalogCards } from "@/lib/loadCombined";
import { loadProgramData } from "@/lib/loadOpportunities";

export default function OpportunitiesPage() {
  const cards = loadCatalogCards();
  const program = loadProgramData();
  const stats = computeCatalogStats(cards);
  const featured = selectFeaturedCards(cards);

  const statItems = [
    { label: "In catalog", value: String(stats.total) },
    { label: "Package-ready", value: String(stats.packageReady) },
    { label: "Comp-grounded", value: String(stats.compGrounded) },
    { label: "Verified comp anchors", value: String(stats.verifiedComps) },
    { label: "Full physician roster", value: String(stats.withPhysicianRoster) },
  ];

  return (
    <>
      <SiteNav />
      <main className="mx-auto max-w-7xl space-y-12 px-4 py-10 sm:px-6 lg:px-8">
        <header className="max-w-3xl space-y-5">
          <div className="space-y-2">
            <p className="font-mono text-xs uppercase tracking-widest text-cockpit-teal">
              Rhode Island · Physician-led venture syndicates
            </p>
            <h1 className="text-3xl font-semibold tracking-tight text-balance sm:text-4xl">
              {program?.title ?? "RI Physician-Led Venture Syndicates"}
            </h1>
            <p className="text-lg text-muted-foreground">
              {program?.subtitle ??
                "Rhode Island technologies, clinician syndicates, and Slater SSBCI match capital"}
            </p>
          </div>
          <p className="text-base leading-relaxed text-muted-foreground">
            Every program below is a Brown, URI, or RI Hospital technology packaged as a{" "}
            <strong className="font-medium text-foreground">≤$400K co-investment</strong>: half from
            a local physician syndicate, half matched by Slater Tech Fund — with{" "}
            <strong className="font-medium text-foreground">cited market comparables</strong>,{" "}
            <strong className="font-medium text-foreground">matched physician rosters</strong>, and a{" "}
            <strong className="font-medium text-foreground">defined clinical pilot path</strong> you
            can verify.
          </p>
          <div className="flex flex-wrap gap-3">
            <Button asChild>
              <Link href="#catalog">Browse packages</Link>
            </Button>
            <Button variant="outline" asChild>
              <Link href="/program">How the program works</Link>
            </Button>
          </div>
        </header>

        <OpportunityHowItWorks />

        {cards.length > 0 ? <PortfolioStatsBar items={statItems} /> : null}

        {featured.length > 0 ? <FeaturedOpportunities cards={featured} /> : null}

        {cards.length === 0 ? (
          <p className="text-sm text-muted-foreground">
            No opportunities loaded. Run <code className="font-mono">npm run build:ri:combined</code>.
          </p>
        ) : (
          <OpportunityCatalog cards={cards} />
        )}

        <footer className="max-w-3xl space-y-2 border-t border-border/60 pt-8 text-sm leading-relaxed text-muted-foreground">
          <p>
            <strong className="font-medium text-foreground">Every claim links to a source.</strong>{" "}
            Comparables, publications, trials, and physician matches trace to primary URLs or curated
            ground truth — not generated filler.
          </p>
          <p>
            Governance includes COI checks, required investigator and reviewer roles, and conflict
            tagging before syndicate assignment.{" "}
            <Link href="/program" className="text-cockpit-teal hover:underline">
              Program details &amp; governance →
            </Link>
          </p>
        </footer>
      </main>
    </>
  );
}
