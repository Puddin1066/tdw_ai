"use client";

import Link from "next/link";
import { cn } from "@/lib/utils";

interface SiteNavProps {
  className?: string;
}

export function SiteNav({ className }: SiteNavProps) {
  return (
    <nav
      className={cn(
        "border-b border-border/60 bg-background/80 backdrop-blur supports-[backdrop-filter]:bg-background/60",
        className,
      )}
    >
      <div className="mx-auto flex max-w-7xl items-center justify-between gap-4 px-4 py-3 sm:px-6 lg:px-8">
        <div className="flex items-center gap-4">
          <Link href="/opportunities" className="font-mono text-xs uppercase tracking-widest text-cockpit-teal">
            RI Development Opportunities
          </Link>
          <Link
            href="/opportunities/curate"
            className="rounded-md border border-cockpit-teal/40 px-2 py-0.5 text-xs text-cockpit-teal hover:bg-cockpit-teal/10"
          >
            Review &amp; edit CSV
          </Link>
        </div>
        <p className="hidden text-xs text-muted-foreground sm:block">
          IP · Physicians · Clinical path → financing
        </p>
      </div>
    </nav>
  );
}
