"use client";

import { Button } from "@/components/ui/button";
import { ExternalLink } from "@/components/curate/ExternalLink";
import { Field, TextArea, TextInput } from "@/components/curate/FieldEditor";
import type { ComparableEntry } from "@/types/riCasesEnriched";

interface ComparableEditorProps {
  comp: ComparableEntry;
  onChange: (comp: ComparableEntry) => void;
  onPromoteFinancing?: () => void;
}

export function ComparableEditor({ comp, onChange, onPromoteFinancing }: ComparableEditorProps) {
  const set = (patch: Partial<ComparableEntry>) => onChange({ ...comp, ...patch });

  if (!comp.name && !comp.url) {
    return (
      <section className="rounded-lg border border-dashed border-border/50 p-4">
        <h3 className="text-sm font-semibold text-muted-foreground">Comparable {comp.rank}</h3>
        <p className="mt-2 text-sm text-muted-foreground">Empty — add name to enable editing.</p>
        <div className="mt-3">
          <Field label="Company name">
            <TextInput value={comp.name} onChange={(v) => set({ name: v })} />
          </Field>
        </div>
      </section>
    );
  }

  return (
    <section className="rounded-lg border border-border/60 bg-card/40 p-4 space-y-3">
      <div className="flex flex-wrap items-center justify-between gap-2">
        <h3 className="text-sm font-semibold">
          Comparable {comp.rank}: {comp.name || "Unnamed"}
        </h3>
        <div className="flex flex-wrap gap-2">
          {comp.url ? <ExternalLink href={comp.url} label="Company site" /> : null}
          {comp.valueSourceUrl ? (
            <ExternalLink href={comp.valueSourceUrl} label="Financing source" />
          ) : null}
        </div>
      </div>

      <div className="grid gap-3 sm:grid-cols-2">
        <Field label="Name">
          <TextInput value={comp.name} onChange={(v) => set({ name: v })} />
        </Field>
        <Field label="Type">
          <TextInput value={comp.type} onChange={(v) => set({ type: v })} />
        </Field>
        <Field label="Company URL">
          <TextInput value={comp.url} onChange={(v) => set({ url: v })} />
        </Field>
        <Field label="Validation status">
          <select
            className="w-full rounded-md border border-border/80 bg-background/60 px-3 py-2 text-sm"
            value={comp.validationStatus}
            onChange={(e) => set({ validationStatus: e.target.value })}
          >
            <option value="suggested">suggested</option>
            <option value="verified">verified</option>
            <option value="rejected">rejected</option>
          </select>
        </Field>
      </div>

      <div className="grid gap-3 sm:grid-cols-3">
        <Field label="Value anchor ($)">
          <TextInput value={comp.valueAnchorUsd} onChange={(v) => set({ valueAnchorUsd: v })} />
        </Field>
        <Field label="Anchor type">
          <TextInput value={comp.valueAnchorType} onChange={(v) => set({ valueAnchorType: v })} />
        </Field>
        <Field label="Total raised ($)">
          <TextInput value={comp.totalRaisedUsd} onChange={(v) => set({ totalRaisedUsd: v })} />
        </Field>
      </div>

      <Field label="Financing source URL">
        <TextInput value={comp.valueSourceUrl} onChange={(v) => set({ valueSourceUrl: v })} />
      </Field>

      <Field label="Financing ladder" hint="One round per line">
        <TextArea
          rows={4}
          mono
          value={comp.financingLadder}
          onChange={(v) => set({ financingLadder: v })}
        />
      </Field>

      <Field label="Development path">
        <TextArea rows={2} value={comp.developmentPath} onChange={(v) => set({ developmentPath: v })} />
      </Field>

      {comp.rank === 1 && (comp.suggestValueSourceUrl || comp.suggestFinancingLadder) ? (
        <div className="rounded-md border border-amber-500/30 bg-amber-500/5 p-3 space-y-2">
          <p className="text-xs font-medium uppercase text-amber-200/90">Script suggestions</p>
          {comp.suggestValueSourceUrl ? (
            <div className="flex flex-wrap items-center gap-2">
              <ExternalLink href={comp.suggestValueSourceUrl} label="Suggested financing URL" />
              {onPromoteFinancing ? (
                <Button type="button" size="sm" variant="outline" onClick={onPromoteFinancing}>
                  Use suggested URL
                </Button>
              ) : null}
            </div>
          ) : null}
          {comp.suggestFinancingLadder ? (
            <pre className="whitespace-pre-wrap font-mono text-xs text-muted-foreground">
              {comp.suggestFinancingLadder}
            </pre>
          ) : null}
          {comp.suggestNotes ? (
            <p className="text-xs text-muted-foreground">{comp.suggestNotes}</p>
          ) : null}
        </div>
      ) : null}
    </section>
  );
}
