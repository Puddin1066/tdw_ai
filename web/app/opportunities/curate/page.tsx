"use client";

import dynamic from "next/dynamic";

const CaseCuratorApp = dynamic(
  () => import("@/components/curate/CaseCuratorApp").then((mod) => mod.CaseCuratorApp),
  {
    ssr: false,
    loading: () => (
      <main className="mx-auto max-w-7xl px-4 py-16 text-muted-foreground">Loading case curator…</main>
    ),
  },
);

export default function CuratePage() {
  return <CaseCuratorApp />;
}
