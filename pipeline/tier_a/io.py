"""CSV/YAML helpers for Tier A sources."""

from __future__ import annotations

import csv
from pathlib import Path
from typing import Any

import yaml

from pipeline.tier_a import paths as tier_a_paths


def ensure_tier_a_dir() -> Path:
    tier_a_paths.TIER_A_ROOT.mkdir(parents=True, exist_ok=True)
    return tier_a_paths.TIER_A_ROOT


def read_csv(path: Path) -> list[dict[str, str]]:
    if not path.exists():
        return []
    with path.open(newline="", encoding="utf-8") as handle:
        return list(csv.DictReader(handle))


def write_csv(path: Path, fieldnames: list[str], rows: list[dict[str, str]]) -> None:
    ensure_tier_a_dir()
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=fieldnames, extrasaction="ignore")
        writer.writeheader()
        writer.writerows(rows)


def load_registry(*, active_only: bool = False) -> list[dict[str, str]]:
    rows = read_csv(tier_a_paths.REGISTRY_CSV)
    if not active_only:
        return rows
    return [r for r in rows if (r.get("status") or "active").lower() in {"active", "approved"}]


def load_comparables() -> list[dict[str, str]]:
    return read_csv(tier_a_paths.COMPARABLES_CSV)


def load_evidence_overrides() -> list[dict[str, str]]:
    return read_csv(tier_a_paths.EVIDENCE_OVERRIDES_CSV)


def load_finance_policy() -> dict[str, Any]:
    if not tier_a_paths.FINANCE_POLICY_YAML.exists():
        return {}
    with tier_a_paths.FINANCE_POLICY_YAML.open(encoding="utf-8") as handle:
        return yaml.safe_load(handle) or {}


def comparables_by_case(rows: list[dict[str, str]] | None = None) -> dict[str, list[dict[str, str]]]:
    grouped: dict[str, list[dict[str, str]]] = {}
    for row in rows or load_comparables():
        case_id = (row.get("case_id") or "").strip()
        if not case_id:
            continue
        grouped.setdefault(case_id, []).append(row)
    for case_id in grouped:
        grouped[case_id].sort(key=lambda r: int(r.get("precedent_rank") or 99))
    return grouped


def registry_by_case(rows: list[dict[str, str]] | None = None) -> dict[str, dict[str, str]]:
    return {(r.get("case_id") or "").strip(): r for r in (rows or load_registry()) if r.get("case_id")}


def evidence_by_case(rows: list[dict[str, str]] | None = None) -> dict[str, dict[str, str]]:
    return {
        (r.get("case_id") or "").strip(): r
        for r in (rows or load_evidence_overrides())
        if r.get("case_id")
    }


def write_registry(rows: list[dict[str, str]]) -> None:
    write_csv(tier_a_paths.REGISTRY_CSV, tier_a_paths.REGISTRY_FIELDS, rows)


def write_comparables(rows: list[dict[str, str]]) -> None:
    write_csv(tier_a_paths.COMPARABLES_CSV, tier_a_paths.COMPARABLE_FIELDS, rows)


def write_evidence_overrides(rows: list[dict[str, str]]) -> None:
    write_csv(
        tier_a_paths.EVIDENCE_OVERRIDES_CSV,
        tier_a_paths.EVIDENCE_OVERRIDE_FIELDS,
        rows,
    )
