"use client";

import { useMemo, useState } from "react";
import { Badge } from "@/components/ui/badge";
import { TextInput } from "@/components/curate/FieldEditor";
import { extractUrls } from "@/lib/riCasesCsv";
import type { RiCaseRow } from "@/types/riCasesEnriched";

interface CaseTableViewProps {
  rows: RiCaseRow[];
  fieldnames: string[];
  selectedId: string;
  onSelect: (caseId: string) => void;
}

function cellPreview(value: string, max = 48): string {
  const oneLine = value.replace(/\s+/g, " ").trim();
  if (!oneLine) return "—";
  return oneLine.length > max ? `${oneLine.slice(0, max)}…` : oneLine;
}

export function CaseTableView({ rows, fieldnames, selectedId, onSelect }: CaseTableViewProps) {
  const [search, setSearch] = useState("");
  const [columnFilter, setColumnFilter] = useState("");

  const visibleColumns = useMemo(() => {
    const q = columnFilter.trim().toLowerCase();
    if (!q) return fieldnames;
    return fieldnames.filter((f) => f.toLowerCase().includes(q));
  }, [fieldnames, columnFilter]);

  const filteredRows = useMemo(() => {
    const q = search.trim().toLowerCase();
    if (!q) return rows;
    return rows.filter((r) =>
      [r.case_id, r.display_name, r.title_clean, r.company, r.indication]
        .join(" ")
        .toLowerCase()
        .includes(q),
    );
  }, [rows, search]);

  return (
    <div className="flex h-full min-h-0 flex-col gap-3">
      <div className="flex flex-wrap gap-2">
        <div className="min-w-[200px] flex-1">
          <TextInput value={search} onChange={setSearch} placeholder="Filter cases…" />
        </div>
        <div className="min-w-[200px] flex-1">
          <TextInput
            value={columnFilter}
            onChange={setColumnFilter}
            placeholder="Filter columns…"
          />
        </div>
      </div>

      <p className="text-xs text-muted-foreground">
        {filteredRows.length} cases × {visibleColumns.length} columns — click a row to edit. Scroll
        horizontally for all CSV fields.
      </p>

      <div className="min-h-0 flex-1 overflow-auto rounded-lg border border-border/60">
        <table className="w-max min-w-full border-collapse text-xs">
          <thead className="sticky top-0 z-10 bg-background/95 backdrop-blur">
            <tr>
              {visibleColumns.map((col) => (
                <th
                  key={col}
                  className="border-b border-border/60 px-2 py-2 text-left font-mono font-medium text-muted-foreground whitespace-nowrap"
                >
                  {col}
                </th>
              ))}
            </tr>
          </thead>
          <tbody>
            {filteredRows.map((row) => {
              const selected = row.case_id === selectedId;
              return (
                <tr
                  key={row.case_id}
                  onClick={() => onSelect(row.case_id)}
                  className={`cursor-pointer border-b border-border/30 ${
                    selected ? "bg-cockpit-teal/15" : "hover:bg-muted/40"
                  }`}
                >
                  {visibleColumns.map((col) => {
                    const value = row[col] ?? "";
                    const urls = extractUrls(col, value);
                    return (
                      <td
                        key={`${row.case_id}-${col}`}
                        className="max-w-[220px] px-2 py-1.5 align-top"
                        title={value || undefined}
                      >
                        {col === "review_status" ? (
                          <Badge
                            variant={value === "approved" ? "success" : "outline"}
                            className="text-[10px]"
                          >
                            {value || "pending"}
                          </Badge>
                        ) : urls.length === 1 ? (
                          <a
                            href={urls[0]}
                            target="_blank"
                            rel="noopener noreferrer"
                            className="text-cockpit-teal underline-offset-2 hover:underline"
                            onClick={(e) => e.stopPropagation()}
                          >
                            {cellPreview(value, 32)}
                          </a>
                        ) : (
                          <span className={value.trim() ? "text-foreground" : "text-muted-foreground/50"}>
                            {cellPreview(value)}
                          </span>
                        )}
                      </td>
                    );
                  })}
                </tr>
              );
            })}
          </tbody>
        </table>
      </div>
    </div>
  );
}
