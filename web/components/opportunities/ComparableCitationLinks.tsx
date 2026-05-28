interface ComparableCitationLinksProps {
  companyUrl?: string;
  valueSourceUrl?: string;
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

/** Company site + financing / deal citation for comparables (shared by precedent cards and snapshot). */
export function ComparableCitationLinks({
  companyUrl,
  valueSourceUrl,
  className = "",
}: ComparableCitationLinksProps) {
  const company = trimUrl(companyUrl);
  const financing = trimUrl(valueSourceUrl);
  const showFinancing = Boolean(financing && !urlsEqual(financing, company));

  if (!company && !showFinancing) return null;

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
    </div>
  );
}
