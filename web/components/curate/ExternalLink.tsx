"use client";

import { cn } from "@/lib/utils";

interface ExternalLinkProps {
  href: string;
  label?: string;
  className?: string;
}

export function ExternalLink({ href, label, className }: ExternalLinkProps) {
  const trimmed = href.trim();
  if (!trimmed) return null;
  const display = label ?? trimmed.replace(/^https?:\/\//, "").slice(0, 72);
  return (
    <a
      href={trimmed}
      target="_blank"
      rel="noopener noreferrer"
      className={cn(
        "inline-flex items-center gap-1 text-sm text-cockpit-teal underline-offset-2 hover:underline",
        className,
      )}
    >
      {display}
      <span aria-hidden className="text-xs opacity-60">
        ↗
      </span>
    </a>
  );
}
