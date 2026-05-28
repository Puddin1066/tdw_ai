"use client";

import Link from "next/link";
import { useCallback, useEffect, useMemo, useState } from "react";
import { AllColumnsEditor } from "@/components/curate/AllColumnsEditor";
import { CaseTableView } from "@/components/curate/CaseTableView";
import { ComparableEditor } from "@/components/curate/ComparableEditor";
import { ExternalLink } from "@/components/curate/ExternalLink";
import { FactCheckPanel } from "@/components/curate/FactCheckPanel";
import { Field, TextArea, TextInput, UrlField } from "@/components/curate/FieldEditor";
import { PublicationEditor } from "@/components/curate/PublicationEditor";
import { SiteNav } from "@/components/SiteNav";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Tabs, TabsContent, TabsList, TabsTrigger } from "@/components/ui/tabs";
import {
  countFilledFields,
  ENRICHED_JSON_PATH,
  normalizePayload,
  STORAGE_KEY,
  applyFinanceSplit,
  downloadText,
  parseCsv,
  parseComparable,
  parsePublications,
  parseTrials,
  promoteCompFinancingUrl,
  promotePublication,
  rowsToCsv,
  rowsToJsonPayload,
  splitLines,
  validationHints,
  writeComparable,
  writePublications,
  writeTrials,
} from "@/lib/riCasesCsv";
import type { RiCaseRow, RiCasesEnrichedFile } from "@/types/riCasesEnriched";

function statusBadge(status: string): "success" | "outline" {
  return status.toLowerCase() === "approved" ? "success" : "outline";
}

export function CaseCuratorApp() {
  const [fieldnames, setFieldnames] = useState<string[]>([]);
  const [rows, setRows] = useState<RiCaseRow[]>([]);
  const [selectedId, setSelectedId] = useState<string>("");
  const [filter, setFilter] = useState("");
  const [tierFilter, setTierFilter] = useState<string>("all");
  const [statusFilter, setStatusFilter] = useState<string>("all");
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [draftBanner, setDraftBanner] = useState(false);
  const [savedAt, setSavedAt] = useState<string | null>(null);
  const [viewMode, setViewMode] = useState<"case" | "table">("case");

  const loadFromPayload = useCallback((payload: RiCasesEnrichedFile, preserveSelection = false) => {
    const normalized = normalizePayload(payload);
    setFieldnames(normalized.fieldnames);
    setRows(normalized.rows);
    setSelectedId((prev) => {
      if (preserveSelection && prev && normalized.rows.some((r) => r.case_id === prev)) {
        return prev;
      }
      return normalized.rows[0]?.case_id ?? "";
    });
  }, []);

  useEffect(() => {
    async function load() {
      try {
        const draft = localStorage.getItem(STORAGE_KEY);
        if (draft) {
          const parsed = JSON.parse(draft) as RiCasesEnrichedFile;
          loadFromPayload(parsed, true);
          setDraftBanner(true);
          setLoading(false);
          return;
        }
        const res = await fetch(ENRICHED_JSON_PATH);
        if (!res.ok) throw new Error(`Failed to load ${ENRICHED_JSON_PATH} (${res.status})`);
        const payload = (await res.json()) as RiCasesEnrichedFile;
        loadFromPayload(payload, false);
      } catch (e) {
        setError(e instanceof Error ? e.message : "Load failed");
      } finally {
        setLoading(false);
      }
    }
    load();
  }, [loadFromPayload]);

  const filteredRows = useMemo(() => {
    const q = filter.toLowerCase();
    return rows.filter((r) => {
      if (tierFilter !== "all" && (r.catalog_tier ?? "").toUpperCase() !== tierFilter) return false;
      if (statusFilter !== "all" && (r.review_status ?? "").toLowerCase() !== statusFilter) {
        return false;
      }
      if (!q) return true;
      const hay = [
        r.case_id,
        r.display_name,
        r.title_clean,
        r.company,
        r.indication,
      ]
        .join(" ")
        .toLowerCase();
      return hay.includes(q);
    });
  }, [rows, filter, tierFilter, statusFilter]);

  const selected = useMemo(
    () => rows.find((r) => r.case_id === selectedId) ?? null,
    [rows, selectedId],
  );

  const updateRow = useCallback((caseId: string, patch: Partial<RiCaseRow>) => {
    setRows((prev) =>
      prev.map((r) => {
        if (r.case_id !== caseId) return r;
        const next = { ...r };
        for (const [k, v] of Object.entries(patch)) {
          if (v !== undefined) next[k] = v;
        }
        return next as RiCaseRow;
      }),
    );
  }, []);

  const patchSelected = useCallback(
    (patch: Partial<RiCaseRow>) => {
      if (!selected) return;
      updateRow(selected.case_id, patch);
    },
    [selected, updateRow],
  );

  const saveDraft = useCallback(() => {
    if (!fieldnames.length) return;
    const payload = rowsToJsonPayload(fieldnames, rows);
    localStorage.setItem(STORAGE_KEY, JSON.stringify(payload));
    setSavedAt(new Date().toLocaleTimeString());
    setDraftBanner(true);
  }, [fieldnames, rows]);

  const discardDraft = useCallback(async () => {
    localStorage.removeItem(STORAGE_KEY);
    setDraftBanner(false);
    setLoading(true);
    try {
      const res = await fetch(ENRICHED_JSON_PATH);
      const payload = (await res.json()) as RiCasesEnrichedFile;
      loadFromPayload(payload);
    } finally {
      setLoading(false);
    }
  }, [loadFromPayload]);

  const exportCsv = useCallback(() => {
    if (!fieldnames.length) return;
    downloadText(
      "ri_cases_enriched.csv",
      rowsToCsv(fieldnames, rows),
      "text/csv;charset=utf-8",
    );
  }, [fieldnames, rows]);

  const exportJson = useCallback(() => {
    if (!fieldnames.length) return;
    downloadText(
      "ri_cases_enriched.json",
      JSON.stringify(rowsToJsonPayload(fieldnames, rows), null, 2),
      "application/json",
    );
  }, [fieldnames, rows]);

  const importPayload = useCallback(
    (payload: RiCasesEnrichedFile) => {
      if (!payload.rows?.length || !payload.fieldnames?.length) {
        throw new Error("Invalid file: need fieldnames and rows");
      }
      loadFromPayload(payload);
      localStorage.setItem(STORAGE_KEY, JSON.stringify(payload));
      setDraftBanner(true);
      setError(null);
    },
    [loadFromPayload],
  );

  const importJsonFile = useCallback(
    (file: File) => {
      const reader = new FileReader();
      reader.onload = () => {
        try {
          importPayload(JSON.parse(String(reader.result)) as RiCasesEnrichedFile);
        } catch (e) {
          setError(e instanceof Error ? e.message : "Import failed");
        }
      };
      reader.readAsText(file);
    },
    [importPayload],
  );

  const importCsvFile = useCallback(
    (file: File) => {
      const reader = new FileReader();
      reader.onload = () => {
        try {
          const { fieldnames: fn, rows: parsed } = parseCsv(String(reader.result));
          if (!parsed.length || !fn.length) throw new Error("CSV is empty");
          importPayload(rowsToJsonPayload(fn, parsed));
        } catch (e) {
          setError(e instanceof Error ? e.message : "CSV import failed");
        }
      };
      reader.readAsText(file);
    },
    [importPayload],
  );

  const reloadFromServer = useCallback(async () => {
    setLoading(true);
    setError(null);
    try {
      const res = await fetch(`${ENRICHED_JSON_PATH}?t=${Date.now()}`);
      if (!res.ok) throw new Error(`Failed to reload (${res.status})`);
      loadFromPayload((await res.json()) as RiCasesEnrichedFile, true);
    } catch (e) {
      setError(e instanceof Error ? e.message : "Reload failed");
    } finally {
      setLoading(false);
    }
  }, [loadFromPayload]);

  const hints = selected ? validationHints(selected) : [];

  if (loading) {
    return (
      <>
        <SiteNav />
        <main className="mx-auto max-w-7xl px-4 py-16 text-muted-foreground">Loading cases…</main>
      </>
    );
  }

  if (error && !rows.length) {
    return (
      <>
        <SiteNav />
        <main className="mx-auto max-w-7xl space-y-4 px-4 py-16">
          <p className="text-destructive">{error}</p>
          <p className="text-sm text-muted-foreground">
            Run{" "}
            <code className="font-mono">npm run ri:cases:export-json</code> from the repo root, then
            refresh.
          </p>
        </main>
      </>
    );
  }

  return (
    <>
      <SiteNav />
      <main className="mx-auto flex max-w-[1600px] flex-col gap-4 px-4 py-6 lg:h-[calc(100vh-3.5rem)] lg:flex-row lg:overflow-hidden">
        {/* Sidebar */}
        <aside className="flex w-full shrink-0 flex-col gap-3 lg:w-80 lg:border-r lg:border-border/60 lg:pr-4">
          <header className="space-y-2">
            <div className="flex items-center justify-between gap-2">
              <h1 className="text-lg font-semibold">Case curator</h1>
              <Link
                href="/opportunities"
                className="text-xs text-muted-foreground hover:text-cockpit-teal"
              >
                Catalog
              </Link>
            </div>
            <p className="text-xs text-muted-foreground leading-relaxed">
              Human-readable view of <code className="font-mono">ri_cases_enriched.csv</code> — every
              patent, publication, comp, and trial opens in a new tab for fact-checking.
            </p>
            <details className="rounded-md border border-border/50 px-3 py-2 text-xs text-muted-foreground">
              <summary className="cursor-pointer font-medium text-foreground">Save workflow</summary>
              <ol className="mt-2 list-decimal space-y-1 pl-4">
                <li>Edit fields → Save draft (browser)</li>
                <li>Download CSV</li>
                <li>
                  <code className="font-mono">npm run ri:cases:apply -- ~/Downloads/ri_cases_enriched.csv</code>
                </li>
                <li>
                  <code className="font-mono">npm run ri:cases:validate && npm run ri:cases:build</code>
                </li>
              </ol>
            </details>
          </header>

          {draftBanner ? (
            <div className="rounded-md border border-amber-500/40 bg-amber-500/10 px-3 py-2 text-xs">
              Local draft active{savedAt ? ` (saved ${savedAt})` : ""}.
              <button
                type="button"
                className="ml-2 underline"
                onClick={() => discardDraft()}
              >
                Discard
              </button>
            </div>
          ) : null}

          <div className="flex flex-wrap gap-1 rounded-md border border-border/60 p-0.5">
            <button
              type="button"
              onClick={() => setViewMode("case")}
              className={`rounded px-2.5 py-1 text-xs ${
                viewMode === "case"
                  ? "bg-cockpit-teal/20 text-foreground"
                  : "text-muted-foreground hover:text-foreground"
              }`}
            >
              Case editor
            </button>
            <button
              type="button"
              onClick={() => setViewMode("table")}
              className={`rounded px-2.5 py-1 text-xs ${
                viewMode === "table"
                  ? "bg-cockpit-teal/20 text-foreground"
                  : "text-muted-foreground hover:text-foreground"
              }`}
            >
              Full table (107 cols)
            </button>
          </div>

          <div className="flex flex-wrap gap-2">
            <Button type="button" size="sm" onClick={saveDraft}>
              Save draft
            </Button>
            <Button type="button" size="sm" variant="outline" onClick={exportCsv}>
              Download CSV
            </Button>
            <Button type="button" size="sm" variant="outline" onClick={exportJson}>
              JSON
            </Button>
            <label className="cursor-pointer">
              <span className="inline-flex h-8 items-center rounded-md border border-input px-3 text-xs hover:bg-accent">
                Import CSV
              </span>
              <input
                type="file"
                accept=".csv,text/csv"
                className="hidden"
                onChange={(e) => {
                  const f = e.target.files?.[0];
                  if (f) importCsvFile(f);
                  e.target.value = "";
                }}
              />
            </label>
            <label className="cursor-pointer">
              <span className="inline-flex h-8 items-center rounded-md border border-input px-3 text-xs hover:bg-accent">
                Import JSON
              </span>
              <input
                type="file"
                accept="application/json,.json"
                className="hidden"
                onChange={(e) => {
                  const f = e.target.files?.[0];
                  if (f) importJsonFile(f);
                  e.target.value = "";
                }}
              />
            </label>
            <Button type="button" size="sm" variant="ghost" onClick={() => reloadFromServer()}>
              Reload
            </Button>
          </div>

          <TextInput
            value={filter}
            onChange={setFilter}
            placeholder="Search case id, title, company…"
          />
          <div className="flex gap-2">
            <select
              className="flex-1 rounded-md border border-border/80 bg-background/60 px-2 py-1.5 text-xs"
              value={tierFilter}
              onChange={(e) => setTierFilter(e.target.value)}
            >
              <option value="all">All tiers</option>
              <option value="A">Tier A</option>
              <option value="B">Tier B</option>
            </select>
            <select
              className="flex-1 rounded-md border border-border/80 bg-background/60 px-2 py-1.5 text-xs"
              value={statusFilter}
              onChange={(e) => setStatusFilter(e.target.value)}
            >
              <option value="all">All status</option>
              <option value="pending">Pending</option>
              <option value="approved">Approved</option>
            </select>
          </div>

          <ul className="flex-1 space-y-1 overflow-y-auto pr-1 lg:max-h-none">
            {filteredRows.map((r) => (
              <li key={r.case_id}>
                <button
                  type="button"
                  onClick={() => setSelectedId(r.case_id)}
                  className={`w-full rounded-md px-3 py-2 text-left text-sm transition-colors ${
                    r.case_id === selectedId
                      ? "bg-cockpit-teal/15 text-foreground"
                      : "hover:bg-muted/50 text-muted-foreground hover:text-foreground"
                  }`}
                >
                  <span className="flex items-center gap-2">
                    <Badge variant={statusBadge(r.review_status)} className="text-[10px]">
                      {r.review_status || "pending"}
                    </Badge>
                    {r.catalog_tier ? (
                      <span className="font-mono text-[10px]">T{r.catalog_tier}</span>
                    ) : null}
                  </span>
                  <span className="mt-0.5 block truncate font-medium">
                    {r.display_name || r.title_clean || r.case_id}
                  </span>
                  <span className="block truncate font-mono text-[10px] opacity-70">{r.case_id}</span>
                </button>
              </li>
            ))}
          </ul>
          <p className="text-[10px] text-muted-foreground">
            {filteredRows.length} / {rows.length} cases
          </p>
        </aside>

        {/* Editor */}
        <div className="min-h-0 flex-1 overflow-y-auto lg:pl-2">
          {viewMode === "table" ? (
            <CaseTableView
              rows={filteredRows}
              fieldnames={fieldnames}
              selectedId={selectedId}
              onSelect={(id) => {
                setSelectedId(id);
                setViewMode("case");
              }}
            />
          ) : !selected ? (
            <p className="text-muted-foreground">Select a case.</p>
          ) : (
            <CaseEditor
              row={selected}
              fieldnames={fieldnames}
              onChange={patchSelected}
              hints={hints}
            />
          )}
        </div>
      </main>
    </>
  );
}

function CaseEditor({
  row,
  fieldnames,
  onChange,
  hints,
}: {
  row: RiCaseRow;
  fieldnames: string[];
  onChange: (patch: Partial<RiCaseRow>) => void;
  hints: string[];
}) {
  const pubs = parsePublications(row, false);
  const suggestPubs = parsePublications(row, true);
  const trials = parseTrials(row);
  const filledCount = countFilledFields(row, fieldnames);

  return (
    <div className="space-y-6 pb-12">
      <header className="sticky top-0 z-10 space-y-3 border-b border-border/60 bg-background/95 py-4 backdrop-blur">
        <div className="flex flex-wrap items-start justify-between gap-3">
          <div>
            <p className="font-mono text-xs text-cockpit-teal">{row.case_id}</p>
            <h2 className="text-xl font-semibold">{row.display_name || row.title_clean}</h2>
            <p className="text-sm text-muted-foreground">
              {row.company} · {row.indication}
              <span className="ml-2 text-xs text-muted-foreground/80">
                ({filledCount}/{fieldnames.length} columns)
              </span>
            </p>
          </div>
          <div className="flex flex-wrap gap-2">
            <Link href={`/opportunities/${row.case_id}`}>
              <Button type="button" variant="outline" size="sm">
                Preview exhibit
              </Button>
            </Link>
            {row.primary_patent_url ? (
              <ExternalLink href={row.primary_patent_url} label="Primary patent" />
            ) : null}
          </div>
        </div>

        {hints.length ? (
          <ul className="space-y-1 rounded-md border border-amber-500/30 bg-amber-500/5 px-3 py-2 text-xs text-amber-100/90">
            {hints.map((h) => (
              <li key={h}>• {h}</li>
            ))}
          </ul>
        ) : null}

        <FactCheckPanel row={row} />

        <div className="grid gap-3 sm:grid-cols-3">
          <Field label="Review status">
            <select
              className="w-full rounded-md border border-border/80 bg-background/60 px-3 py-2 text-sm"
              value={row.review_status || "pending"}
              onChange={(e) => onChange({ review_status: e.target.value })}
            >
              <option value="pending">pending</option>
              <option value="approved">approved</option>
            </select>
          </Field>
          <Field label="Reviewer">
            <TextInput value={row.reviewer ?? ""} onChange={(v) => onChange({ reviewer: v })} />
          </Field>
          <Field label="Last refreshed">
            <TextInput
              value={row.last_refreshed_at ?? ""}
              onChange={(v) => onChange({ last_refreshed_at: v })}
            />
          </Field>
        </div>
      </header>

      <Tabs defaultValue="all">
        <TabsList className="flex flex-wrap h-auto gap-1">
          <TabsTrigger value="all">All columns ({fieldnames.length})</TabsTrigger>
          <TabsTrigger value="identity">Identity</TabsTrigger>
          <TabsTrigger value="patents">Patents</TabsTrigger>
          <TabsTrigger value="publications">Publications</TabsTrigger>
          <TabsTrigger value="physicians">Physicians</TabsTrigger>
          <TabsTrigger value="comps">Comparables</TabsTrigger>
          <TabsTrigger value="finance">Finance</TabsTrigger>
          <TabsTrigger value="clinical">Clinical</TabsTrigger>
          <TabsTrigger value="narrative">Narrative</TabsTrigger>
        </TabsList>

        <TabsContent value="all" className="mt-4">
          <AllColumnsEditor row={row} fieldnames={fieldnames} onChange={onChange} />
        </TabsContent>

        <TabsContent value="identity" className="mt-4 space-y-4">
          <div className="grid gap-3 sm:grid-cols-2">
            <Field label="Catalog include">
              <TextInput
                value={row.catalog_include ?? ""}
                onChange={(v) => onChange({ catalog_include: v })}
              />
            </Field>
            <Field label="Enrichment status">
              <TextInput
                value={row.enrichment_status ?? ""}
                onChange={(v) => onChange({ enrichment_status: v })}
              />
            </Field>
            <Field label="Display name">
              <TextInput value={row.display_name ?? ""} onChange={(v) => onChange({ display_name: v })} />
            </Field>
            <Field label="Title (clean)">
              <TextInput value={row.title_clean ?? ""} onChange={(v) => onChange({ title_clean: v })} />
            </Field>
            <Field label="Company">
              <TextInput value={row.company ?? ""} onChange={(v) => onChange({ company: v })} />
            </Field>
            <Field label="RI institution">
              <TextInput
                value={row.ri_institution ?? ""}
                onChange={(v) => onChange({ ri_institution: v })}
              />
            </Field>
            <Field label="Indication">
              <TextInput value={row.indication ?? ""} onChange={(v) => onChange({ indication: v })} />
            </Field>
            <Field label="Opportunity type">
              <TextInput
                value={row.opportunity_type ?? ""}
                onChange={(v) => onChange({ opportunity_type: v })}
              />
            </Field>
            <Field label="Development stage">
              <TextInput
                value={row.development_stage ?? ""}
                onChange={(v) => onChange({ development_stage: v })}
              />
            </Field>
            <Field label="Catalog tier">
              <TextInput value={row.catalog_tier ?? ""} onChange={(v) => onChange({ catalog_tier: v })} />
            </Field>
          </div>
          <Field label="Data caveat">
            <TextArea value={row.data_caveat ?? ""} onChange={(v) => onChange({ data_caveat: v })} />
          </Field>
          <Field label="RI notes">
            <TextArea value={row.ri_notes ?? ""} onChange={(v) => onChange({ ri_notes: v })} />
          </Field>
        </TabsContent>

        <TabsContent value="patents" className="mt-4 space-y-4">
          <div className="grid gap-3 sm:grid-cols-2">
            <Field label="Primary Lens ID">
              <TextInput
                value={row.primary_lens_id ?? ""}
                onChange={(v) => onChange({ primary_lens_id: v })}
              />
            </Field>
            <Field label="Display key">
              <TextInput
                value={row.primary_display_key ?? ""}
                onChange={(v) => onChange({ primary_display_key: v })}
              />
            </Field>
          </div>
          <Field label="Primary patent title">
            <TextInput
              value={row.primary_patent_title ?? ""}
              onChange={(v) => onChange({ primary_patent_title: v })}
            />
          </Field>
          <UrlField
            label="Primary patent URL"
            value={row.primary_patent_url ?? ""}
            onChange={(v) => onChange({ primary_patent_url: v })}
          />
          {row.primary_patent_url ? (
            <ExternalLink href={row.primary_patent_url} label="Open in Lens" />
          ) : null}
          <Field label="Assignee">
            <TextInput value={row.assignee_company ?? ""} onChange={(v) => onChange({ assignee_company: v })} />
          </Field>
          <Field label="Inventors">
            <TextArea value={row.inventors ?? ""} onChange={(v) => onChange({ inventors: v })} />
          </Field>
          <Field label="IP Lens IDs">
            <TextArea
              mono
              rows={2}
              value={row.ip_lens_ids ?? ""}
              onChange={(v) => onChange({ ip_lens_ids: v })}
            />
          </Field>
          <Field label="IP titles">
            <TextArea
              mono
              rows={3}
              value={row.ip_titles ?? ""}
              onChange={(v) => onChange({ ip_titles: v })}
            />
          </Field>
          <Field label="Additional patent URLs (one per line)">
            <TextArea
              mono
              rows={4}
              value={row.ip_urls ?? ""}
              onChange={(v) => onChange({ ip_urls: v })}
            />
          </Field>
          {splitLines(row.ip_urls).map((url, i) => (
            <ExternalLink key={url} href={url} label={`Patent ${i + 1}`} />
          ))}
        </TabsContent>

        <TabsContent value="publications" className="mt-4 space-y-8">
          <PublicationEditor
            title="Approved publications"
            entries={pubs}
            onChange={(entries) => onChange(writePublications(row, entries, false))}
          />
          <PublicationEditor
            title="Suggested publications (scripts)"
            entries={suggestPubs}
            readOnly
            onChange={() => {}}
            onPromote={(i) => onChange(promotePublication(row, i))}
          />
          <Field label="Literature narrative">
            <TextArea
              rows={4}
              value={row.literature_narrative ?? ""}
              onChange={(v) => onChange({ literature_narrative: v })}
            />
          </Field>
        </TabsContent>

        <TabsContent value="physicians" className="mt-4 space-y-4">
          <div className="rounded-lg border border-border/60 p-4 space-y-3">
            <h3 className="text-sm font-semibold">Lead physician</h3>
            <div className="grid gap-3 sm:grid-cols-2">
              <Field label="Name">
                <TextInput
                  value={row.physician_lead_name ?? ""}
                  onChange={(v) => onChange({ physician_lead_name: v })}
                />
              </Field>
              <Field label="NPI">
                <TextInput
                  value={row.physician_lead_npi ?? ""}
                  onChange={(v) => onChange({ physician_lead_npi: v })}
                />
              </Field>
              <Field label="Specialty">
                <TextInput
                  value={row.physician_lead_specialty ?? ""}
                  onChange={(v) => onChange({ physician_lead_specialty: v })}
                />
              </Field>
              <Field label="Institution">
                <TextInput
                  value={row.physician_lead_institution ?? ""}
                  onChange={(v) => onChange({ physician_lead_institution: v })}
                />
              </Field>
            </div>
            <UrlField
              label="Profile URL"
              value={row.physician_lead_profile_url ?? ""}
              onChange={(v) => onChange({ physician_lead_profile_url: v })}
            />
            {row.physician_lead_profile_url ? (
              <ExternalLink href={row.physician_lead_profile_url} label="Open profile" />
            ) : null}
          </div>
          <Field label="Supporters (pipe-separated names)">
            <TextArea
              value={row.physician_supporters ?? ""}
              onChange={(v) => onChange({ physician_supporters: v })}
            />
          </Field>
          <Field label="Supporter profile URLs (one per line)">
            <TextArea
              mono
              rows={3}
              value={row.physician_supporter_profile_urls ?? ""}
              onChange={(v) => onChange({ physician_supporter_profile_urls: v })}
            />
          </Field>
        </TabsContent>

        <TabsContent value="comps" className="mt-4 space-y-4">
          {([1, 2, 3] as const).map((rank) => (
            <ComparableEditor
              key={rank}
              comp={parseComparable(row, rank)}
              onChange={(comp) => onChange(writeComparable(row, comp))}
              onPromoteFinancing={
                rank === 1
                  ? () => onChange(promoteCompFinancingUrl(row, rank))
                  : undefined
              }
            />
          ))}
        </TabsContent>

        <TabsContent value="finance" className="mt-4 space-y-4">
          <p className="text-sm text-muted-foreground">
            Policy cap: $400K total package, Slater ≤ $200K (50/50 split).
          </p>
          <div className="grid gap-3 sm:grid-cols-2 lg:grid-cols-4">
            <Field label="Total package ($)">
              <TextInput
                type="number"
                value={row.total_package_usd ?? ""}
                onChange={(v) => onChange(applyFinanceSplit({ ...row, total_package_usd: v }))}
              />
            </Field>
            <Field label="Physician share ($)">
              <TextInput
                value={row.physician_share_usd ?? ""}
                onChange={(v) => onChange({ physician_share_usd: v })}
              />
            </Field>
            <Field label="Slater share ($)">
              <TextInput
                value={row.slater_share_usd ?? ""}
                onChange={(v) => onChange({ slater_share_usd: v })}
              />
            </Field>
            <Field label="Financing stage">
              <TextInput
                value={row.financing_stage ?? ""}
                onChange={(v) => onChange({ financing_stage: v })}
              />
            </Field>
          </div>
          <Button
            type="button"
            variant="outline"
            size="sm"
            onClick={() => onChange(applyFinanceSplit(row))}
          >
            Recalculate 50/50 split
          </Button>
          <div className="grid gap-3 sm:grid-cols-2">
            <Field label="Clinical allocation ($)">
              <TextInput
                value={row.clinical_allocation_usd ?? ""}
                onChange={(v) => onChange({ clinical_allocation_usd: v })}
              />
            </Field>
            <Field label="R&D allocation ($)">
              <TextInput
                value={row.rd_allocation_usd ?? ""}
                onChange={(v) => onChange({ rd_allocation_usd: v })}
              />
            </Field>
          </div>
          <Field label="Financing rationale">
            <TextArea
              rows={3}
              value={row.financing_rationale ?? ""}
              onChange={(v) => onChange({ financing_rationale: v })}
            />
          </Field>
        </TabsContent>

        <TabsContent value="clinical" className="mt-4 space-y-4">
          <div className="space-y-3">
            {trials.map((t, i) => (
              <div key={t.nctId || i} className="rounded-lg border border-border/60 p-3 space-y-2">
                <div className="flex flex-wrap gap-2">
                  {t.nctId ? (
                    <ExternalLink
                      href={t.url || `https://clinicaltrials.gov/study/${t.nctId}`}
                      label={t.nctId}
                    />
                  ) : null}
                </div>
                <p className="text-sm">{t.title}</p>
                {t.piNames ? <p className="text-xs text-muted-foreground">PI: {t.piNames}</p> : null}
              </div>
            ))}
          </div>
          <Field label="Trial NCT IDs (pipe-separated)">
            <TextInput
              value={row.trial_nct_ids ?? ""}
              onChange={(v) =>
                onChange(writeTrials(row, parseTrials({ ...row, trial_nct_ids: v })))
              }
            />
          </Field>
          <Field label="Trial titles (one per line)">
            <TextArea
              mono
              rows={3}
              value={row.trial_titles ?? ""}
              onChange={(v) =>
                onChange(writeTrials(row, parseTrials({ ...row, trial_titles: v })))
              }
            />
          </Field>
          <Field label="Trial PI names (one per line)">
            <TextArea
              mono
              rows={2}
              value={row.trial_pi_names ?? ""}
              onChange={(v) => onChange({ trial_pi_names: v })}
            />
          </Field>
          <Field label="Trial URLs (one per line)">
            <TextArea
              mono
              rows={2}
              value={row.trial_urls ?? ""}
              onChange={(v) => onChange({ trial_urls: v })}
            />
          </Field>
          <Field label="Trial phases (pipe-separated)">
            <TextInput
              value={row.trial_phases ?? ""}
              onChange={(v) => onChange({ trial_phases: v })}
            />
          </Field>
          <div className="grid gap-3 sm:grid-cols-2">
            <Field label="Study type">
              <TextInput
                value={row.clinical_study_type ?? ""}
                onChange={(v) => onChange({ clinical_study_type: v })}
              />
            </Field>
            <Field label="Duration (weeks)">
              <TextInput
                value={row.clinical_duration_weeks ?? ""}
                onChange={(v) => onChange({ clinical_duration_weeks: v })}
              />
            </Field>
            <Field label="Clinical cost ($)">
              <TextInput
                value={row.clinical_cost_usd ?? ""}
                onChange={(v) => onChange({ clinical_cost_usd: v })}
              />
            </Field>
            <Field label="Target timeline (weeks)">
              <TextInput
                value={row.target_timeline_weeks ?? ""}
                onChange={(v) => onChange({ target_timeline_weeks: v })}
              />
            </Field>
          </div>
          <Field label="Primary endpoint">
            <TextArea
              value={row.clinical_primary_endpoint ?? ""}
              onChange={(v) => onChange({ clinical_primary_endpoint: v })}
            />
          </Field>
          <Field label="Clinical path notes">
            <TextArea
              rows={3}
              value={row.clinical_path_notes ?? ""}
              onChange={(v) => onChange({ clinical_path_notes: v })}
            />
          </Field>
        </TabsContent>

        <TabsContent value="narrative" className="mt-4 space-y-4">
          <Field label="Investment thesis">
            <TextArea
              rows={6}
              value={row.investment_thesis ?? ""}
              onChange={(v) => onChange({ investment_thesis: v })}
            />
          </Field>
          <Field label="R&D plan summary">
            <TextArea
              rows={4}
              value={row.rd_plan_summary ?? ""}
              onChange={(v) => onChange({ rd_plan_summary: v })}
            />
          </Field>
          <Field label="R&D milestones (one per line)">
            <TextArea
              mono
              rows={4}
              value={row.rd_milestones ?? ""}
              onChange={(v) => onChange({ rd_milestones: v })}
            />
          </Field>
          <Field label="R&D milestone types">
            <TextInput
              value={row.rd_milestone_types ?? ""}
              onChange={(v) => onChange({ rd_milestone_types: v })}
            />
          </Field>
          <div className="grid gap-3 sm:grid-cols-2">
            <Field label="MCQ lead pillar">
              <TextInput
                value={row.mcq_lead_pillar ?? ""}
                onChange={(v) => onChange({ mcq_lead_pillar: v })}
              />
            </Field>
            <Field label="MCQ financing structure">
              <TextInput
                value={row.mcq_financing_structure ?? ""}
                onChange={(v) => onChange({ mcq_financing_structure: v })}
              />
            </Field>
            <Field label="MCQ audience">
              <TextInput
                value={row.mcq_audience ?? ""}
                onChange={(v) => onChange({ mcq_audience: v })}
              />
            </Field>
            <Field label="Program family">
              <TextInput
                value={row.program_family ?? ""}
                onChange={(v) => onChange({ program_family: v })}
              />
            </Field>
          </div>
          <Field label="Required specialties">
            <TextInput
              value={row.required_specialties ?? ""}
              onChange={(v) => onChange({ required_specialties: v })}
            />
          </Field>
          <Field label="Clinical tags">
            <TextInput
              value={row.clinical_tags ?? ""}
              onChange={(v) => onChange({ clinical_tags: v })}
            />
          </Field>
        </TabsContent>
      </Tabs>
    </div>
  );
}
