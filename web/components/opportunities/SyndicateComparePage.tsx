"use client";

import Link from "next/link";
import { useSearchParams } from "next/navigation";
import { useMemo } from "react";
import type { OpportunityIndexRow } from "@/types/opportunities";
import { SyndicateCompare } from "@/components/opportunities/SyndicateCompare";

interface SyndicateComparePageProps {
  index: OpportunityIndexRow[];
}

export function SyndicateComparePage({ index }: SyndicateComparePageProps) {
  const searchParams = useSearchParams();
  const idsParam = searchParams.get("ids") ?? "";

  const rows = useMemo(() => {
    const requested = idsParam
      .split(",")
      .map((id) => id.trim())
      .filter(Boolean)
      .slice(0, 3);
    return requested
      .map((id) => index.find((row) => row.case_id === id))
      .filter((row): row is OpportunityIndexRow => Boolean(row));
  }, [idsParam, index]);

  return (
    <div className="space-y-6">
      <header className="space-y-2">
        <Link href="/opportunities" className="text-sm text-muted-foreground hover:text-foreground">
          ← Catalog
        </Link>
        <h1 className="text-2xl font-semibold">Compare syndicates</h1>
        <p className="text-sm text-muted-foreground">
          Side-by-side readiness, capital, staffing, and trial path (up to 3).
        </p>
      </header>
      <SyndicateCompare rows={rows} />
    </div>
  );
}
