"use client";

import { useMemo, useState } from "react";
import { ExternalLink } from "@/components/curate/ExternalLink";
import { Field, TextArea, TextInput } from "@/components/curate/FieldEditor";
import { Badge } from "@/components/ui/badge";
import {
  FIELD_GROUPS,
  countFilledFields,
  extractUrls,
  fieldsNotInGroups,
  isUrlLikeField,
} from "@/lib/riCasesCsv";
import type { RiCaseRow } from "@/types/riCasesEnriched";

type ColumnFilter = "all" | "filled" | "empty" | "urls";

interface AllColumnsEditorProps {
  row: RiCaseRow;
  fieldnames: string[];
  onChange: (patch: Partial<RiCaseRow>) => void;
}

function fieldRows(value: string): number {
  const lines = value.split("\n").length;
  return Math.min(12, Math.max(2, lines + 1));
}

function humanLabel(name: string): string {
  return name.replace(/_/g, " ");
}

export function AllColumnsEditor({ row, fieldnames, onChange }: AllColumnsEditorProps) {
  const [search, setSearch] = useState("");
  const [filter, setFilter] = useState<ColumnFilter>("all");
  const [collapsed, setCollapsed] = useState<Record<string, boolean>>({});

  const filledCount = countFilledFields(row, fieldnames);
  const extraFields = fieldsNotInGroups(fieldnames);

  const groups = useMemo(() => {
    const base = FIELD_GROUPS.map((group) => ({
      ...group,
      fields: group.fields.filter((f) => fieldnames.includes(f)),
    })).filter((g) => g.fields.length > 0);

    if (extraFields.length) {
      base.push({ label: "Other", fields: extraFields });
    }
    return base;
  }, [fieldnames, extraFields]);

  const q = search.trim().toLowerCase();

  const visibleFields = (fields: string[]) =>
    fields.filter((name) => {
      if (q && !name.toLowerCase().includes(q)) return false;
      const value = (row[name] ?? "").trim();
      if (filter === "filled" && !value) return false;
      if (filter === "empty" && value) return false;
      if (filter === "urls" && !isUrlLikeField(name, value) && extractUrls(name, value).length === 0) {
        return false;
      }
      return true;
    });

  return (
    <div className="space-y-4">
      <div className="flex flex-wrap items-center justify-between gap-3">
        <p className="text-sm text-muted-foreground">
          Full CSV row — <span className="font-medium text-foreground">{filledCount}</span> /{" "}
          {fieldnames.length} columns populated
        </p>
        <div className="flex flex-wrap gap-2">
          {(["all", "filled", "empty", "urls"] as const).map((mode) => (
            <button
              key={mode}
              type="button"
              onClick={() => setFilter(mode)}
              className={`rounded-md px-2.5 py-1 text-xs capitalize ${
                filter === mode
                  ? "bg-cockpit-teal/20 text-cockpit-teal"
                  : "bg-muted/50 text-muted-foreground hover:text-foreground"
              }`}
            >
              {mode}
            </button>
          ))}
        </div>
      </div>

      <TextInput
        value={search}
        onChange={setSearch}
        placeholder="Filter columns by name…"
      />

      <div className="space-y-4">
        {groups.map((group) => {
          const fields = visibleFields(group.fields);
          if (!fields.length) return null;
          const isCollapsed = collapsed[group.label] ?? false;
          const groupFilled = group.fields.filter((f) => (row[f] ?? "").trim()).length;

          return (
            <section
              key={group.label}
              className="rounded-lg border border-border/60 bg-card/30 overflow-hidden"
            >
              <button
                type="button"
                className="flex w-full items-center justify-between gap-2 px-4 py-3 text-left hover:bg-muted/30"
                onClick={() =>
                  setCollapsed((prev) => ({ ...prev, [group.label]: !isCollapsed }))
                }
              >
                <span className="text-sm font-semibold">{group.label}</span>
                <span className="flex items-center gap-2">
                  <Badge variant="outline" className="text-[10px]">
                    {groupFilled}/{group.fields.length}
                  </Badge>
                  <span className="text-xs text-muted-foreground">{isCollapsed ? "▸" : "▾"}</span>
                </span>
              </button>

              {!isCollapsed ? (
                <div className="space-y-4 border-t border-border/40 px-4 py-4">
                  {fields.map((name) => {
                    const value = row[name] ?? "";
                    const urls = extractUrls(name, value);
                    const multiline =
                      value.includes("\n") ||
                      value.length > 120 ||
                      name.includes("ladder") ||
                      name.includes("milestones") ||
                      name.includes("titles") ||
                      name.includes("notes") ||
                      name.includes("thesis") ||
                      name.includes("narrative");

                    return (
                      <div
                        key={name}
                        className={`rounded-md border px-3 py-3 space-y-2 ${
                          value.trim()
                            ? "border-border/50 bg-background/40"
                            : "border-dashed border-border/30 bg-transparent"
                        }`}
                      >
                        <div className="flex flex-wrap items-start justify-between gap-2">
                          <div className="space-y-1">
                            <p className="text-xs font-medium uppercase tracking-wide text-muted-foreground">
                              {humanLabel(name)}
                            </p>
                            <p className="font-mono text-[10px] text-muted-foreground/80">{name}</p>
                          </div>
                          {!value.trim() ? (
                            <Badge variant="outline" className="text-[10px] text-muted-foreground">
                              empty
                            </Badge>
                          ) : null}
                        </div>

                        {multiline ? (
                          <TextArea
                            mono
                            rows={fieldRows(value)}
                            value={value}
                            onChange={(v) => onChange({ [name]: v })}
                          />
                        ) : (
                          <TextInput value={value} onChange={(v) => onChange({ [name]: v })} />
                        )}

                        {urls.length ? (
                          <div className="flex flex-wrap gap-x-3 gap-y-1 pt-1">
                            {urls.map((href, i) => (
                              <ExternalLink
                                key={`${name}-${href}`}
                                href={href}
                                label={urls.length > 1 ? `Open ${i + 1}` : "Open link"}
                                className="text-xs"
                              />
                            ))}
                          </div>
                        ) : null}
                      </div>
                    );
                  })}
                </div>
              ) : null}
            </section>
          );
        })}
      </div>
    </div>
  );
}
