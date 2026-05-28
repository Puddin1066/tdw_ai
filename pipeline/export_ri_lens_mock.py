"""Export mocked RI lens CSV signals into static JSON for web use."""

from __future__ import annotations

import argparse
import csv
import json
from datetime import datetime, timezone
from pathlib import Path


DEFAULT_INPUT = Path("data/ri/ri_lens_mock_signals.csv")
DEFAULT_OUTPUT = Path("web/public/data/ri/ri_lens_mock_signals.json")


def parse_bool(value: str) -> bool:
    return value.strip().lower() in {"1", "true", "t", "yes", "y"}


def parse_int(value: str) -> int:
    return int(value.strip() or "0")


def load_rows(path: Path) -> list[dict[str, object]]:
    rows: list[dict[str, object]] = []
    with path.open(newline="", encoding="utf-8") as handle:
        reader = csv.DictReader(handle)
        for row in reader:
            case_id = (row.get("case_id") or "").strip()
            if not case_id:
                continue
            rows.append(
                {
                    "case_id": case_id,
                    "mocked": parse_bool(row.get("data_is_mocked", "true")),
                    "metrics": {
                        "ri_anchor_score_0_100": parse_int(row.get("ri_anchor_score_0_100", "0")),
                        "physician_champion_score_0_100": parse_int(
                            row.get("physician_champion_score_0_100", "0")
                        ),
                        "ip_provenance_score_0_100": parse_int(row.get("ip_provenance_score_0_100", "0")),
                        "slater_stage_fit_score_0_100": parse_int(row.get("slater_stage_fit_score_0_100", "0")),
                        "ssbci_match_readiness_score_0_100": parse_int(
                            row.get("ssbci_match_readiness_score_0_100", "0")
                        ),
                        "regulatory_path_clarity_score_0_100": parse_int(
                            row.get("regulatory_path_clarity_score_0_100", "0")
                        ),
                        "pilotability_score_0_100": parse_int(row.get("pilotability_score_0_100", "0")),
                        "buyer_path_clarity_score_0_100": parse_int(
                            row.get("buyer_path_clarity_score_0_100", "0")
                        ),
                        "time_to_inflection_months": parse_int(row.get("time_to_inflection_months", "0")),
                    },
                    "qualitative": {
                        "ri_anchor_rationale": (row.get("ri_anchor_rationale") or "").strip(),
                        "physician_rationale": (row.get("physician_rationale") or "").strip(),
                        "ip_rationale": (row.get("ip_rationale") or "").strip(),
                        "slater_ssbci_rationale": (row.get("slater_ssbci_rationale") or "").strip(),
                        "commercialization_rationale": (row.get("commercialization_rationale") or "").strip(),
                    },
                    "mock_notes": (row.get("mock_notes") or "").strip(),
                }
            )
    return rows


def export_json(input_csv: Path, output_json: Path) -> Path:
    records = load_rows(input_csv)
    output_json.parent.mkdir(parents=True, exist_ok=True)
    payload = {
        "artifact_type": "ri_lens_mock_signals",
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "record_count": len(records),
        "records": records,
    }
    output_json.write_text(json.dumps(payload, indent=2) + "\n", encoding="utf-8")
    return output_json


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Export RI mock lens CSV into static JSON.")
    parser.add_argument("--input", type=Path, default=DEFAULT_INPUT, help="Input CSV path")
    parser.add_argument("--output", type=Path, default=DEFAULT_OUTPUT, help="Output JSON path")
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    out = export_json(args.input.resolve(), args.output.resolve())
    print(f"Wrote {out}")


if __name__ == "__main__":
    main()
