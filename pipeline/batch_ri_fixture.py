"""Run fixture workflow for all Rhode Island opportunity case configs."""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

from pipeline.config_loader import ConfigValidationError, load_case_config
from pipeline.run_workflow import run_case_workflow
from pipeline.types import repo_root


def discover_ri_configs(config_dir: Path) -> list[Path]:
    paths: list[Path] = []
    for path in sorted(config_dir.glob("*.yaml")):
        case_id = path.stem
        if case_id.endswith("_ri") or case_id.startswith("auto_"):
            paths.append(path)
    return paths


def batch_ri_fixture(
    config_dir: Path,
    *,
    limit: int = 0,
    skip: int = 0,
) -> tuple[int, list[tuple[str, str]]]:
    configs = discover_ri_configs(config_dir)
    if skip:
        configs = configs[skip:]
    if limit > 0:
        configs = configs[:limit]

    failures: list[tuple[str, str]] = []
    for index, config_path in enumerate(configs, start=1):
        try:
            config = load_case_config(config_path)
            run_case_workflow(config, "fixture")
            print(f"[{index}/{len(configs)}] OK {config.case_id}", flush=True)
        except (ConfigValidationError, FileNotFoundError, OSError, ValueError) as exc:
            failures.append((config_path.stem, str(exc)))
            print(f"[{index}/{len(configs)}] FAIL {config_path.stem}: {exc}", file=sys.stderr, flush=True)
    return len(configs) - len(failures), failures


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Batch fixture workflow for RI case configs.")
    parser.add_argument(
        "--config-dir",
        type=Path,
        default=repo_root() / "configs" / "cases",
        help="Directory containing case YAML files",
    )
    parser.add_argument("--limit", type=int, default=0, help="Max cases to run (0 = all)")
    parser.add_argument("--skip", type=int, default=0, help="Skip first N configs")
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    ok_count, failures = batch_ri_fixture(
        args.config_dir.resolve(),
        limit=max(0, args.limit),
        skip=max(0, args.skip),
    )
    print(f"Completed {ok_count} case(s).")
    if failures:
        print(f"Failed {len(failures)} case(s):", file=sys.stderr)
        for case_id, message in failures[:20]:
            print(f"  - {case_id}: {message}", file=sys.stderr)
        if len(failures) > 20:
            print(f"  ... and {len(failures) - 20} more", file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
