import Link from "next/link";
import { OpportunityCatalog } from "@/components/opportunities/OpportunityCatalog";
import { SiteNav } from "@/components/SiteNav";
import { loadCatalogCards } from "@/lib/loadCombined";

export default function OpportunitiesPage() {
  const cards = loadCatalogCards();

  return (
    <>
      <SiteNav />
      <main className="mx-auto max-w-7xl space-y-8 px-4 py-10 sm:px-6 lg:px-8">
        <header className="max-w-2xl space-y-3">
          <h1 className="text-3xl font-semibold tracking-tight">Rhode Island opportunities</h1>
          <p className="text-base leading-relaxed text-muted-foreground">
            Each program is a Rhode Island patent-backed venture case: verified{" "}
            <strong className="font-medium text-foreground">market comparables</strong> set financing
            and development precedent,{" "}
            <strong className="font-medium text-foreground">physician syndicates</strong> provide
            clinical credibility, and a{" "}
            <strong className="font-medium text-foreground">pilot path</strong> de-risks the technology
            — packaged for 50/50 physician and Slater SSBCI financing.
          </p>
          <Link
            href="/opportunities/curate"
            className="inline-flex items-center gap-1 text-sm text-cockpit-teal underline-offset-2 hover:underline"
          >
            Review &amp; edit source data (CSV curator)
            <span aria-hidden>→</span>
          </Link>
        </header>

        {cards.length === 0 ? (
          <p className="text-sm text-muted-foreground">
            No opportunities loaded. Run <code className="font-mono">npm run build:ri:combined</code>.
          </p>
        ) : (
          <OpportunityCatalog cards={cards} />
        )}
      </main>
    </>
  );
}
