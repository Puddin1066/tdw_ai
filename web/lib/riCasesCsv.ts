import type {
  ComparableEntry,
  PublicationEntry,
  RiCaseRow,
  RiCasesEnrichedFile,
  TrialEntry,
} from "@/types/riCasesEnriched";

export const STORAGE_KEY = "ri_cases_enriched_draft_v1";

export const ENRICHED_JSON_PATH = "/data/ri/ri_cases_enriched.json";

/** Mirrors pipeline/ri_cases_enriched_schema.py FIELDNAMES groupings. */
export const FIELD_GROUPS: { label: string; fields: string[] }[] = [
  {
    label: "Identity & review",
    fields: [
      "case_id",
      "catalog_tier",
      "catalog_include",
      "review_status",
      "title_clean",
      "display_name",
      "company",
      "indication",
      "opportunity_type",
      "development_stage",
      "ri_institution",
      "data_caveat",
      "ri_notes",
      "last_refreshed_at",
      "reviewer",
      "enrichment_status",
    ],
  },
  {
    label: "Patents",
    fields: [
      "primary_lens_id",
      "primary_display_key",
      "primary_patent_title",
      "primary_patent_url",
      "assignee_company",
      "inventors",
      "ip_lens_ids",
      "ip_titles",
      "ip_urls",
    ],
  },
  {
    label: "Publications (approved)",
    fields: [
      "publication_count",
      "publication_titles",
      "publication_lead_authors",
      "publication_ri_affiliations",
      "publication_urls",
      "publication_pmids",
      "literature_narrative",
    ],
  },
  {
    label: "Publications (suggested)",
    fields: ["suggest_publication_titles", "suggest_publication_urls", "suggest_publication_notes"],
  },
  {
    label: "Physicians",
    fields: [
      "physician_lead_npi",
      "physician_lead_name",
      "physician_lead_specialty",
      "physician_lead_institution",
      "physician_lead_profile_url",
      "physician_supporters",
      "physician_supporter_profile_urls",
    ],
  },
  {
    label: "Comparable 1",
    fields: [
      "comp1_name",
      "comp1_type",
      "comp1_url",
      "comp1_value_anchor_usd",
      "comp1_value_anchor_type",
      "comp1_value_source_url",
      "comp1_total_raised_usd",
      "comp1_last_round_usd",
      "comp1_financing_ladder",
      "comp1_development_path",
      "comp1_validation_status",
      "suggest_comp1_value_source_url",
      "suggest_comp1_financing_ladder",
      "suggest_comp1_notes",
    ],
  },
  {
    label: "Comparable 2",
    fields: [
      "comp2_name",
      "comp2_type",
      "comp2_url",
      "comp2_value_anchor_usd",
      "comp2_value_anchor_type",
      "comp2_value_source_url",
      "comp2_total_raised_usd",
      "comp2_last_round_usd",
      "comp2_financing_ladder",
      "comp2_development_path",
      "comp2_validation_status",
    ],
  },
  {
    label: "Comparable 3",
    fields: [
      "comp3_name",
      "comp3_type",
      "comp3_url",
      "comp3_value_anchor_usd",
      "comp3_value_anchor_type",
      "comp3_value_source_url",
      "comp3_total_raised_usd",
      "comp3_last_round_usd",
      "comp3_financing_ladder",
      "comp3_development_path",
      "comp3_validation_status",
    ],
  },
  {
    label: "Finance",
    fields: [
      "financing_stage",
      "total_package_usd",
      "physician_share_usd",
      "slater_share_usd",
      "clinical_allocation_usd",
      "rd_allocation_usd",
      "financing_rationale",
    ],
  },
  {
    label: "Trials",
    fields: [
      "trial_count",
      "trial_nct_ids",
      "trial_titles",
      "trial_pi_names",
      "trial_urls",
      "trial_phases",
    ],
  },
  {
    label: "R&D & clinical",
    fields: [
      "rd_plan_summary",
      "rd_milestones",
      "rd_milestone_types",
      "clinical_study_type",
      "clinical_primary_endpoint",
      "clinical_duration_weeks",
      "clinical_cost_usd",
      "clinical_path_notes",
      "target_timeline_weeks",
    ],
  },
  {
    label: "Framing & tags",
    fields: [
      "investment_thesis",
      "mcq_lead_pillar",
      "mcq_financing_structure",
      "mcq_audience",
      "required_specialties",
      "clinical_tags",
      "program_family",
    ],
  },
];

const URL_FIELD_RE = /(?:^|_)(url|urls|pmids?)$/i;

export function isUrlLikeField(name: string, value: string): boolean {
  if (URL_FIELD_RE.test(name)) return true;
  const v = value.trim();
  return /^https?:\/\//i.test(v);
}

export function extractUrls(name: string, value: string): string[] {
  const v = (value ?? "").trim();
  if (!v) return [];
  if (name.includes("pmid") && !v.includes("\n") && !v.includes("http")) {
    return v.split("|").map((p) => p.trim()).filter(Boolean).map(
      (pmid) => `https://pubmed.ncbi.nlm.nih.gov/${pmid}/`,
    );
  }
  if (name.includes("nct") && v.includes("|")) {
    return v.split("|").map((id) => id.trim()).filter(Boolean).map(
      (id) => `https://clinicaltrials.gov/study/${id}`,
    );
  }
  return splitLines(v.replace(/\|/g, "\n")).filter((line) => /^https?:\/\//i.test(line));
}

export function countFilledFields(row: RiCaseRow, fieldnames: string[]): number {
  return fieldnames.filter((f) => (row[f] ?? "").trim()).length;
}

export function fieldsNotInGroups(fieldnames: string[]): string[] {
  const grouped = new Set(FIELD_GROUPS.flatMap((g) => g.fields));
  return fieldnames.filter((f) => !grouped.has(f));
}

export const CANONICAL_FIELDNAMES = FIELD_GROUPS.flatMap((g) => g.fields);

/** Ensure every schema column exists on each row (fixes stale localStorage drafts). */
export function normalizePayload(payload: RiCasesEnrichedFile): RiCasesEnrichedFile {
  const fieldnames = [
    ...new Set([
      ...CANONICAL_FIELDNAMES,
      ...(payload.fieldnames?.length ? payload.fieldnames : []),
    ]),
  ];
  const rows = (payload.rows ?? []).map((row) => {
    const out: RiCaseRow = { case_id: row.case_id ?? "" } as RiCaseRow;
    for (const f of fieldnames) {
      out[f] = row[f] ?? "";
    }
    return out;
  });
  return {
    ...payload,
    fieldnames,
    rows,
    row_count: rows.length,
  };
}

export function splitLines(value: string | undefined): string[] {
  return (value ?? "")
    .replace(/\r/g, "")
    .split("\n")
    .map((s) => s.trim())
    .filter(Boolean);
}

export function joinLines(lines: string[]): string {
  return lines.filter(Boolean).join("\n");
}

export function splitPipe(value: string | undefined): string[] {
  return (value ?? "")
    .split("|")
    .map((s) => s.trim())
    .filter(Boolean);
}

export function joinPipe(lines: string[]): string {
  return lines.filter(Boolean).join("|");
}

export function escapeCsvField(value: string): string {
  const v = value ?? "";
  if (/[",\n\r]/.test(v)) {
    return `"${v.replace(/"/g, '""')}"`;
  }
  return v;
}

export function rowsToCsv(fieldnames: string[], rows: RiCaseRow[]): string {
  const header = fieldnames.join(",");
  const body = rows.map((row) =>
    fieldnames.map((f) => escapeCsvField(row[f] ?? "")).join(","),
  );
  return [header, ...body].join("\n");
}

export function rowsToJsonPayload(
  fieldnames: string[],
  rows: RiCaseRow[],
  meta: Partial<RiCasesEnrichedFile> = {},
): RiCasesEnrichedFile {
  return {
    schema_version: 1,
    fieldnames,
    generated_at: new Date().toISOString().slice(0, 10),
    source_csv: "data/ri/ri_cases_enriched.csv",
    row_count: rows.length,
    rows: rows.map((row) => {
      const out: RiCaseRow = { case_id: row.case_id ?? "" } as RiCaseRow;
      for (const f of fieldnames) {
        out[f] = row[f] ?? "";
      }
      return out;
    }),
    ...meta,
  };
}

export function downloadText(filename: string, content: string, mime: string) {
  const blob = new Blob([content], { type: mime });
  const url = URL.createObjectURL(blob);
  const a = document.createElement("a");
  a.href = url;
  a.download = filename;
  a.click();
  URL.revokeObjectURL(url);
}

export function applyFinanceSplit(row: RiCaseRow): RiCaseRow {
  const total = Math.min(400_000, Math.max(0, Number(row.total_package_usd) || 0));
  const half = Math.floor(total / 2);
  const slater = Math.min(200_000, half);
  const physician = total - slater;
  return {
    ...row,
    total_package_usd: total ? String(total) : row.total_package_usd,
    physician_share_usd: String(physician),
    slater_share_usd: String(slater),
  };
}

export function parsePublications(row: RiCaseRow, suggest = false): PublicationEntry[] {
  const prefix = suggest ? "suggest_" : "";
  const titles = splitLines(row[`${prefix}publication_titles`]);
  const urls = splitLines(row[`${prefix}publication_urls`]);
  const authors = suggest ? [] : splitLines(row.publication_lead_authors);
  const affs = suggest ? [] : splitLines(row.publication_ri_affiliations);
  const pmids = suggest ? [] : splitLines(row.publication_pmids);
  const notes = suggest ? splitLines(row.suggest_publication_notes) : [];
  const n = Math.max(titles.length, urls.length);
  const out: PublicationEntry[] = [];
  for (let i = 0; i < n; i++) {
    out.push({
      title: titles[i] ?? "",
      leadAuthor: authors[i] ?? "",
      riAffiliation: affs[i] ?? "",
      url: urls[i] ?? "",
      pmid: pmids[i] ?? "",
      note: notes[i],
      isSuggestion: suggest,
    });
  }
  return out;
}

export function writePublications(
  row: RiCaseRow,
  entries: PublicationEntry[],
  suggest = false,
): RiCaseRow {
  const next = { ...row };
  if (suggest) {
    next.suggest_publication_titles = joinLines(entries.map((e) => e.title));
    next.suggest_publication_urls = joinLines(entries.map((e) => e.url));
    next.suggest_publication_notes = joinLines(
      entries.map((e) => e.note ?? "").filter(Boolean),
    );
    return next;
  }
  next.publication_titles = joinLines(entries.map((e) => e.title));
  next.publication_lead_authors = joinLines(entries.map((e) => e.leadAuthor));
  next.publication_ri_affiliations = joinLines(entries.map((e) => e.riAffiliation));
  next.publication_urls = joinLines(entries.map((e) => e.url));
  next.publication_pmids = joinLines(entries.map((e) => e.pmid));
  next.publication_count = entries.length ? String(entries.length) : "";
  return next;
}

export function parseComparable(row: RiCaseRow, rank: 1 | 2 | 3): ComparableEntry {
  const p = `comp${rank}_`;
  return {
    rank,
    name: row[`${p}name`] ?? "",
    type: row[`${p}type`] ?? "",
    url: row[`${p}url`] ?? "",
    valueAnchorUsd: row[`${p}value_anchor_usd`] ?? "",
    valueAnchorType: row[`${p}value_anchor_type`] ?? "",
    valueSourceUrl: row[`${p}value_source_url`] ?? "",
    totalRaisedUsd: row[`${p}total_raised_usd`] ?? "",
    lastRoundUsd: row[`${p}last_round_usd`] ?? "",
    financingLadder: row[`${p}financing_ladder`] ?? "",
    developmentPath: row[`${p}development_path`] ?? "",
    validationStatus: row[`${p}validation_status`] ?? "suggested",
    suggestValueSourceUrl: rank === 1 ? row.suggest_comp1_value_source_url : undefined,
    suggestFinancingLadder: rank === 1 ? row.suggest_comp1_financing_ladder : undefined,
    suggestNotes: rank === 1 ? row.suggest_comp1_notes : undefined,
  };
}

export function writeComparable(row: RiCaseRow, comp: ComparableEntry): RiCaseRow {
  const p = `comp${comp.rank}_`;
  const next = {
    ...row,
    [`${p}name`]: comp.name,
    [`${p}type`]: comp.type,
    [`${p}url`]: comp.url,
    [`${p}value_anchor_usd`]: comp.valueAnchorUsd,
    [`${p}value_anchor_type`]: comp.valueAnchorType,
    [`${p}value_source_url`]: comp.valueSourceUrl,
    [`${p}total_raised_usd`]: comp.totalRaisedUsd,
    [`${p}last_round_usd`]: comp.lastRoundUsd,
    [`${p}financing_ladder`]: comp.financingLadder,
    [`${p}development_path`]: comp.developmentPath,
    [`${p}validation_status`]: comp.validationStatus,
  };
  if (comp.rank === 1) {
    next.suggest_comp1_value_source_url = comp.suggestValueSourceUrl ?? row.suggest_comp1_value_source_url;
    next.suggest_comp1_financing_ladder = comp.suggestFinancingLadder ?? row.suggest_comp1_financing_ladder;
    next.suggest_comp1_notes = comp.suggestNotes ?? row.suggest_comp1_notes;
  }
  return next;
}

export function parseTrials(row: RiCaseRow): TrialEntry[] {
  const ncts = splitPipe(row.trial_nct_ids);
  const titles = splitLines(row.trial_titles);
  const pis = splitLines(row.trial_pi_names);
  const urls = splitLines(row.trial_urls);
  const phases = splitPipe(row.trial_phases);
  return ncts.map((nctId, i) => ({
    nctId,
    title: titles[i] ?? "",
    piNames: pis[i] ?? "",
    url: urls[i] ?? (nctId ? `https://clinicaltrials.gov/study/${nctId}` : ""),
    phase: phases[i] ?? "",
  }));
}

export function writeTrials(row: RiCaseRow, trials: TrialEntry[]): RiCaseRow {
  return {
    ...row,
    trial_nct_ids: joinPipe(trials.map((t) => t.nctId)),
    trial_titles: joinLines(trials.map((t) => t.title)),
    trial_pi_names: joinLines(trials.map((t) => t.piNames)),
    trial_urls: joinLines(trials.map((t) => t.url)),
    trial_phases: joinPipe(trials.map((t) => t.phase)),
    trial_count: trials.length ? String(trials.length) : "",
  };
}

export function promotePublication(row: RiCaseRow, index: number): RiCaseRow {
  const suggested = parsePublications(row, true);
  const approved = parsePublications(row, false);
  const item = suggested[index];
  if (!item) return row;
  approved.push({
    ...item,
    isSuggestion: false,
    leadAuthor: item.leadAuthor || "",
    riAffiliation: item.riAffiliation || "",
  });
  return writePublications(row, approved, false);
}

export function promoteCompFinancingUrl(row: RiCaseRow, rank: 1 | 2 | 3): RiCaseRow {
  const comp = parseComparable(row, rank);
  if (!comp.suggestValueSourceUrl) return row;
  comp.valueSourceUrl = comp.suggestValueSourceUrl;
  if (comp.suggestFinancingLadder && !comp.financingLadder) {
    comp.financingLadder = comp.suggestFinancingLadder;
  }
  return writeComparable(row, comp);
}

export interface FactCheckLink {
  label: string;
  href: string;
}

export interface FactCheckGroup {
  label: string;
  links: FactCheckLink[];
}

function addLink(links: FactCheckLink[], href: string | undefined, label: string) {
  const trimmed = (href ?? "").trim();
  if (!trimmed || links.some((l) => l.href === trimmed)) return;
  links.push({ label, href: trimmed });
}

export function collectFactCheckLinks(row: RiCaseRow): FactCheckGroup[] {
  const groups: FactCheckGroup[] = [];

  const patents: FactCheckLink[] = [];
  addLink(patents, row.primary_patent_url, row.primary_display_key || "Primary patent");
  splitLines(row.ip_urls).forEach((url, i) => addLink(patents, url, `Patent ${i + 2}`));
  if (patents.length) groups.push({ label: "Patents", links: patents });

  const pubs: FactCheckLink[] = [];
  for (const entry of parsePublications(row, false)) {
    const label = entry.title.slice(0, 56) + (entry.title.length > 56 ? "…" : "") || "Publication";
    addLink(pubs, entry.url, label);
    if (entry.pmid) {
      addLink(pubs, `https://pubmed.ncbi.nlm.nih.gov/${entry.pmid}/`, `PubMed ${entry.pmid}`);
    }
  }
  for (const entry of parsePublications(row, true)) {
    const short = entry.title.slice(0, 48);
    const label = entry.title.length > 48 ? `(suggest) ${short}…` : `(suggest) ${short || "Publication"}`;
    addLink(pubs, entry.url, label);
  }
  if (pubs.length) groups.push({ label: "Publications", links: pubs });

  const comps: FactCheckLink[] = [];
  for (const rank of [1, 2, 3] as const) {
    const c = parseComparable(row, rank);
    if (!c.name && !c.url) continue;
    const prefix = c.name || `Comp ${rank}`;
    addLink(comps, c.url, `${prefix} · site`);
    addLink(comps, c.valueSourceUrl, `${prefix} · financing`);
    if (rank === 1) addLink(comps, c.suggestValueSourceUrl, `${prefix} · suggested financing`);
  }
  if (comps.length) groups.push({ label: "Comparables", links: comps });

  const people: FactCheckLink[] = [];
  addLink(people, row.physician_lead_profile_url, row.physician_lead_name || "Lead physician");
  splitLines(row.physician_supporter_profile_urls).forEach((url, i) =>
    addLink(people, url, `Supporter ${i + 1}`),
  );
  if (people.length) groups.push({ label: "Physicians", links: people });

  const clinical: FactCheckLink[] = [];
  for (const trial of parseTrials(row)) {
    if (trial.nctId) {
      addLink(
        clinical,
        trial.url || `https://clinicaltrials.gov/study/${trial.nctId}`,
        trial.nctId,
      );
    }
  }
  if (clinical.length) groups.push({ label: "Clinical trials", links: clinical });

  return groups;
}

/** Parse RFC 4180 CSV (quoted fields may contain newlines). */
export function parseCsv(text: string): { fieldnames: string[]; rows: RiCaseRow[] } {
  const records: string[][] = [];
  let row: string[] = [];
  let field = "";
  let inQuotes = false;

  for (let i = 0; i < text.length; i++) {
    const ch = text[i];
    const next = text[i + 1];

    if (inQuotes) {
      if (ch === '"' && next === '"') {
        field += '"';
        i++;
      } else if (ch === '"') {
        inQuotes = false;
      } else {
        field += ch;
      }
      continue;
    }

    if (ch === '"') {
      inQuotes = true;
    } else if (ch === ",") {
      row.push(field);
      field = "";
    } else if (ch === "\r" && next === "\n") {
      row.push(field);
      field = "";
      records.push(row);
      row = [];
      i++;
    } else if (ch === "\n") {
      row.push(field);
      field = "";
      records.push(row);
      row = [];
    } else {
      field += ch;
    }
  }

  if (field.length || row.length) {
    row.push(field);
    records.push(row);
  }

  const nonEmpty = records.filter((r) => r.some((c) => c.trim()));
  if (!nonEmpty.length) {
    return { fieldnames: [], rows: [] };
  }

  const fieldnames = nonEmpty[0];
  const rows: RiCaseRow[] = nonEmpty.slice(1).map((cells) => {
    const out: RiCaseRow = { case_id: cells[0] ?? "" } as RiCaseRow;
    fieldnames.forEach((name, idx) => {
      out[name] = cells[idx] ?? "";
    });
    return out;
  });

  return { fieldnames, rows };
}

export function validationHints(row: RiCaseRow): string[] {
  const hints: string[] = [];
  const tier = (row.catalog_tier ?? "").toUpperCase();
  const approved = (row.review_status ?? "").toLowerCase() === "approved";
  const pubCount = Number(row.publication_count) || parsePublications(row).length;
  if (tier === "A" && approved && (pubCount < 2 || pubCount > 6)) {
    hints.push("Tier A approved rows need 2–6 publications with RI lead author.");
  }
  if (approved && !(row.primary_patent_url ?? "").includes("lens.org")) {
    hints.push("Approved rows need a Lens patent URL.");
  }
  const total = Number(row.total_package_usd) || 0;
  if (total > 400_000) hints.push("total_package_usd must be ≤ $400,000.");
  const slater = Number(row.slater_share_usd) || 0;
  if (slater > 200_000) hints.push("slater_share_usd must be ≤ $200,000.");
  for (const rank of [1, 2, 3] as const) {
    const c = parseComparable(row, rank);
    if (!c.name) continue;
    if (c.validationStatus === "verified" && !c.valueSourceUrl) {
      hints.push(`Comp ${rank} verified requires financing source URL.`);
    }
  }
  return hints;
}
