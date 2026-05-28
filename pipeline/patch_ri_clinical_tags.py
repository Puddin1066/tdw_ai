"""Patch clinical_tags onto existing ri_physicians.csv and ri_opportunities.csv without full re-normalize."""

from __future__ import annotations

import csv
from collections import defaultdict
from pathlib import Path

from pipeline.physician_assignment import enrich_opportunity_row, enrich_physician_row
from pipeline.types import repo_root

DATA_ROOT = repo_root() / "data" / "ri"


def _read(path: Path) -> list[dict[str, str]]:
    with path.open(newline="", encoding="utf-8") as handle:
        return list(csv.DictReader(handle))


def _write(path: Path, fieldnames: list[str], rows: list[dict[str, str]]) -> None:
    with path.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=fieldnames, extrasaction="ignore")
        writer.writeheader()
        writer.writerows(rows)


def main() -> int:
    physicians_path = DATA_ROOT / "ri_physicians.csv"
    opportunities_path = DATA_ROOT / "ri_opportunities.csv"
    ip_path = DATA_ROOT / "ri_ip_assets.csv"

    physicians = [enrich_physician_row(row) for row in _read(physicians_path)]
    ip_by_case: dict[str, list[dict[str, str]]] = defaultdict(list)
    for row in _read(ip_path):
        case_id = (row.get("case_id") or "").strip()
        if case_id:
            ip_by_case[case_id].append(row)

    opportunities = [
        enrich_opportunity_row(row, patent_rows=ip_by_case.get((row.get("case_id") or "").strip()))
        for row in _read(opportunities_path)
    ]

    if physicians:
        fields = list(physicians[0].keys())
        if "clinical_tags" not in fields:
            fields.insert(3, "clinical_tags")
        _write(physicians_path, fields, physicians)
    if opportunities:
        fields = list(opportunities[0].keys())
        if "clinical_tags" not in fields:
            idx = fields.index("required_specialties") + 1 if "required_specialties" in fields else len(fields)
            fields.insert(idx, "clinical_tags")
        _write(opportunities_path, fields, opportunities)

    print(f"Patched {len(physicians)} physicians and {len(opportunities)} opportunities")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
