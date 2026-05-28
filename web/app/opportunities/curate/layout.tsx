import type { ReactNode } from "react";

export const metadata = {
  title: "Case curator · RI opportunities",
  description: "Review and edit ri_cases_enriched.csv with linked sources",
};

export default function CurateLayout({ children }: { children: ReactNode }) {
  return children;
}
