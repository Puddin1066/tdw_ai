"use client";

import { Button } from "@/components/ui/button";
import { ExternalLink } from "@/components/curate/ExternalLink";
import { Field, TextArea, TextInput } from "@/components/curate/FieldEditor";
import type { PublicationEntry } from "@/types/riCasesEnriched";

interface PublicationEditorProps {
  title: string;
  entries: PublicationEntry[];
  onChange: (entries: PublicationEntry[]) => void;
  onPromote?: (index: number) => void;
  readOnly?: boolean;
}

export function PublicationEditor({
  title,
  entries,
  onChange,
  onPromote,
  readOnly,
}: PublicationEditorProps) {
  const update = (index: number, patch: Partial<PublicationEntry>) => {
    const next = entries.map((e, i) => (i === index ? { ...e, ...patch } : e));
    onChange(next);
  };

  const add = () => {
    onChange([
      ...entries,
      { title: "", leadAuthor: "", riAffiliation: "", url: "", pmid: "" },
    ]);
  };

  const remove = (index: number) => {
    onChange(entries.filter((_, i) => i !== index));
  };

  return (
    <section className="space-y-3">
      <div className="flex items-center justify-between gap-2">
        <h3 className="text-sm font-semibold text-foreground">{title}</h3>
        {!readOnly ? (
          <Button type="button" variant="outline" size="sm" onClick={add}>
            Add row
          </Button>
        ) : null}
      </div>
      {entries.length === 0 ? (
        <p className="text-sm text-muted-foreground">No entries.</p>
      ) : null}
      <div className="space-y-4">
        {entries.map((entry, i) => (
          <div
            key={`${entry.title}-${i}`}
            className="rounded-lg border border-border/60 bg-card/40 p-4 space-y-3"
          >
            <div className="flex flex-wrap items-start justify-between gap-2">
              <span className="font-mono text-xs text-muted-foreground">#{i + 1}</span>
              <div className="flex flex-wrap gap-2">
                {entry.url ? <ExternalLink href={entry.url} label="Open source" /> : null}
                {entry.pmid ? (
                  <ExternalLink
                    href={`https://pubmed.ncbi.nlm.nih.gov/${entry.pmid}/`}
                    label={`PubMed ${entry.pmid}`}
                  />
                ) : null}
                {onPromote ? (
                  <Button type="button" size="sm" onClick={() => onPromote(i)}>
                    Promote to approved
                  </Button>
                ) : null}
                {!readOnly ? (
                  <Button type="button" variant="outline" size="sm" onClick={() => remove(i)}>
                    Remove
                  </Button>
                ) : null}
              </div>
            </div>
            {readOnly ? (
              <div className="space-y-1 text-sm">
                <p className="font-medium">{entry.title || "—"}</p>
                {entry.leadAuthor ? (
                  <p className="text-muted-foreground">Lead: {entry.leadAuthor}</p>
                ) : null}
                {entry.riAffiliation ? (
                  <p className="text-muted-foreground">RI: {entry.riAffiliation}</p>
                ) : null}
                {entry.note ? <p className="text-xs text-muted-foreground">{entry.note}</p> : null}
              </div>
            ) : (
              <>
                <Field label="Title">
                  <TextInput value={entry.title} onChange={(v) => update(i, { title: v })} />
                </Field>
                <div className="grid gap-3 sm:grid-cols-2">
                  <Field label="Lead author">
                    <TextInput
                      value={entry.leadAuthor}
                      onChange={(v) => update(i, { leadAuthor: v })}
                    />
                  </Field>
                  <Field label="RI affiliation">
                    <TextInput
                      value={entry.riAffiliation}
                      onChange={(v) => update(i, { riAffiliation: v })}
                    />
                  </Field>
                </div>
                <div className="grid gap-3 sm:grid-cols-2">
                  <Field label="URL">
                    <TextInput value={entry.url} onChange={(v) => update(i, { url: v })} />
                  </Field>
                  <Field label="PMID">
                    <TextInput value={entry.pmid} onChange={(v) => update(i, { pmid: v })} />
                  </Field>
                </div>
                {entry.note !== undefined ? (
                  <Field label="Note">
                    <TextInput value={entry.note ?? ""} onChange={(v) => update(i, { note: v })} />
                  </Field>
                ) : null}
              </>
            )}
          </div>
        ))}
      </div>
    </section>
  );
}
