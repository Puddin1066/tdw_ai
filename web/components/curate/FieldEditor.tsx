"use client";

import { cn } from "@/lib/utils";

interface FieldProps {
  label: string;
  hint?: string;
  children: React.ReactNode;
  className?: string;
}

export function Field({ label, hint, children, className }: FieldProps) {
  return (
    <label className={cn("block space-y-1.5", className)}>
      <span className="text-xs font-medium uppercase tracking-wide text-muted-foreground">
        {label}
      </span>
      {hint ? <p className="text-xs text-muted-foreground/80">{hint}</p> : null}
      {children}
    </label>
  );
}

const inputClass =
  "w-full rounded-md border border-border/80 bg-background/60 px-3 py-2 text-sm text-foreground placeholder:text-muted-foreground focus:border-cockpit-teal/60 focus:outline-none focus:ring-1 focus:ring-cockpit-teal/40";

export function TextInput({
  value,
  onChange,
  placeholder,
  type = "text",
}: {
  value: string;
  onChange: (v: string) => void;
  placeholder?: string;
  type?: string;
}) {
  return (
    <input
      type={type}
      className={inputClass}
      value={value}
      placeholder={placeholder}
      onChange={(e) => onChange(e.target.value)}
    />
  );
}

export function TextArea({
  value,
  onChange,
  rows = 3,
  placeholder,
  mono,
}: {
  value: string;
  onChange: (v: string) => void;
  rows?: number;
  placeholder?: string;
  mono?: boolean;
}) {
  return (
    <textarea
      className={cn(inputClass, mono && "font-mono text-xs")}
      rows={rows}
      value={value}
      placeholder={placeholder}
      onChange={(e) => onChange(e.target.value)}
    />
  );
}

export function UrlField({
  value,
  onChange,
  label,
  hint,
}: {
  value: string;
  onChange: (v: string) => void;
  label: string;
  hint?: string;
}) {
  return (
    <Field label={label} hint={hint}>
      <TextInput value={value} onChange={onChange} placeholder="https://..." />
    </Field>
  );
}
