"""Apply a downloaded or edited CSV back to data/ri/ri_cases_enriched.csv."""

from __future__ import annotations

import argparse
import shutil
from datetime import datetime
from pathlib import Path

from pipeline.ri_cases_enriched_io import CASES_CSV, load_cases, write_cases
from pipeline.ri_cases_enriched_schema import FIELDNAMES


ROOT = Path(__file__).resolve().parents[1]


def apply_csv(source: Path, dest: Path = CASES_CSV, backup: bool = True) -> int:
    if not source.is_file():
        raise FileNotFoundError(source)
    rows = load_cases(source)
    if not rows:
        raise ValueError(f"No rows in {source}")
    missing = [f for f in ("case_id", "review_status") if f not in rows[0]]
    if missing:
        raise ValueError(f"CSV missing required columns: {missing}")
    extra = set(rows[0].keys()) - set(FIELDNAMES)
    if extra:
        unknown = ", ".join(sorted(extra)[:8])
        raise ValueError(f"Unknown columns (not in schema): {unknown}")
    if backup and dest.is_file():
        stamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        backup_path = dest.with_suffix(f".csv.bak.{stamp}")
        shutil.copy2(dest, backup_path)
        print(f"Backup -> {backup_path}")
    write_cases(rows, dest)
    return len(rows)


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("source", type=Path, help="Edited CSV (e.g. from curator download)")
    parser.add_argument(
        "--dest",
        type=Path,
        default=CASES_CSV,
        help=f"Destination CSV (default: {CASES_CSV.relative_to(ROOT)})",
    )
    parser.add_argument("--no-backup", action="store_true", help="Skip timestamped backup")
    args = parser.parse_args()
    n = apply_csv(args.source, dest=args.dest, backup=not args.no_backup)
    print(f"Applied {n} rows -> {args.dest}")


if __name__ == "__main__":
    main()
