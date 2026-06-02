interface SupportingCitation {
  label: string;
  url: string;
}

interface ComparableCitationLinksProps {
  companyUrl?: string;
  valueSourceUrl?: string;
  supportingCitations?: SupportingCitation[];
  className?: string;
}

function trimUrl(url?: string): string {
  return (url ?? "").trim();
}

function urlsEqual(a: string, b: string): boolean {
  if (!a || !b) return false;
  const norm = (u: string) => u.replace(/\/+$/, "").toLowerCase();
  return norm(a) === norm(b);
}

const linkClass =
  "inline-block text-sm text-cockpit-teal hover:underline";

/** Company site + financing / deal citation + optional supporting sources for comparables. */
export function ComparableCitationLinks({
  companyUrl,
  valueSourceUrl,
  supportingCitations = [],
  className = "",
}: ComparableCitationLinksProps) {
  const company = trimUrl(companyUrl);
  const financing = trimUrl(valueSourceUrl);
  const showFinancing = Boolean(financing && !urlsEqual(financing, company));

  const seen = new Set<string>();
  const extras = supportingCitations.filter((c) => {
    const url = trimUrl(c.url);
    if (!url || seen.has(url.toLowerCase())) return false;
    if (urlsEqual(url, company) || urlsEqual(url, financing)) return false;
    seen.add(url.toLowerCase());
    return true;
  });

  if (!company && !showFinancing && !extras.length) return null;

  return (
    <div className={`flex flex-wrap gap-x-4 gap-y-1 ${className}`.trim()}>
      {company ? (
        <a href={company} target="_blank" rel="noreferrer" className={linkClass}>
          Company website
        </a>
      ) : null}
      {showFinancing ? (
        <a href={financing} target="_blank" rel="noreferrer" className={linkClass}>
          Round / financing source
        </a>
      ) : null}
      {extras.map((c) => (
        <a
          key={c.url}
          href={c.url}
          target="_blank"
          rel="noreferrer"
          className={linkClass}
        >
          {c.label || "Supporting source"}
        </a>
      ))}
    </div>
  );
}
