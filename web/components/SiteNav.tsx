"use client";

import Link from "next/link";
import { usePathname } from "next/navigation";
import { cn } from "@/lib/utils";

interface SiteNavProps {
  className?: string;
}

const NAV_LINKS = [
  { href: "/opportunities", label: "Opportunities" },
  { href: "/program", label: "Program" },
] as const;

export function SiteNav({ className }: SiteNavProps) {
  const pathname = usePathname();

  return (
    <nav
      className={cn(
        "border-b border-border/60 bg-background/80 backdrop-blur supports-[backdrop-filter]:bg-background/60",
        className,
      )}
    >
      <div className="mx-auto flex max-w-7xl items-center justify-between gap-4 px-4 py-3 sm:px-6 lg:px-8">
        <div className="flex flex-wrap items-center gap-4">
          <Link
            href="/opportunities"
            className="font-mono text-xs uppercase tracking-widest text-cockpit-teal"
          >
            RI Physician-Led Syndicates
          </Link>
          <div className="flex items-center gap-1">
            {NAV_LINKS.map((link) => {
              const active =
                link.href === "/opportunities"
                  ? pathname === "/opportunities" || pathname.startsWith("/opportunities/")
                  : pathname.startsWith(link.href);
              return (
                <Link
                  key={link.href}
                  href={link.href}
                  className={cn(
                    "rounded-md px-2 py-1 text-xs transition-colors",
                    active
                      ? "bg-cockpit-teal/10 font-medium text-cockpit-teal"
                      : "text-muted-foreground hover:text-foreground",
                  )}
                >
                  {link.label}
                </Link>
              );
            })}
          </div>
        </div>
        <div className="flex items-center gap-3">
          <p className="hidden text-xs text-muted-foreground md:block">
            Patent → Physician syndicate → Slater match
          </p>
          <Link
            href="/opportunities/curate"
            className="text-xs text-muted-foreground hover:text-foreground"
          >
            Curator
          </Link>
        </div>
      </div>
    </nav>
  );
}
