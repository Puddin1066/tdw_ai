import { type ClassValue, clsx } from "clsx";
import { twMerge } from "tailwind-merge";

export function cn(...inputs: ClassValue[]) {
  return twMerge(clsx(inputs));
}

export function formatConfidence(score: number): string {
  return `${Math.round(score * 100)}%`;
}

export function pmidUrl(sourceId: string): string | null {
  const match = sourceId.match(/^pubmed:(\d+)$/i);
  if (!match) return null;
  return `https://pubmed.ncbi.nlm.nih.gov/${match[1]}/`;
}

export function nctUrl(nctId: string): string {
  return `https://clinicaltrials.gov/study/${nctId}`;
}
