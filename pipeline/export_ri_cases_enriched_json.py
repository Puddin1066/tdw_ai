"""Export ri_cases_enriched.csv to web/public JSON for curator UI."""

from __future__ import annotations

import json
from datetime import date
from pathlib import Path

from pipeline.ri_cases_enriched_io import CASES_CSV, load_cases
from pipeline.ri_cases_enriched_schema import FIELDNAMES

ROOT = Path(__file__).resolve().parents[1]
WEB_JSON = ROOT / "web" / "public" / "data" / "ri" / "ri_cases_enriched.json"


def export_json(path: Path = WEB_JSON) -> int:
    rows = load_cases(CASES_CSV)
    payload = {
        "schema_version": 1,
        "fieldnames": FIELDNAMES,
        "generated_at": date.today().isoformat(),
        "source_csv": "data/ri/ri_cases_enriched.csv",
        "row_count": len(rows),
        "rows": [{f: (r.get(f) or "") for f in FIELDNAMES} for r in rows],
    }
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, indent=2), encoding="utf-8")
    return len(rows)


def main() -> None:
    n = export_json()
    print(f"Exported {n} rows -> {WEB_JSON}")


if __name__ == "__main__":
    main()
