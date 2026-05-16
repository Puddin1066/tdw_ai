"""Validate case artifacts and copy them into the static web data directory."""

from __future__ import annotations

import argparse
import json
import shutil
import sys
from pathlib import Path

from pipeline.schema_validate import validate_case_dir as schema_validate_case_dir
from pipeline.types import REQUIRED_ARTIFACTS, generated_case_dir, web_case_dir


class ArtifactValidationError(Exception):
    """Raised when a case packet fails validation."""


def validate_case_dir(case_dir: Path, *, validate_schemas: bool = True) -> list[str]:
    """Ensure all required artifacts exist and JSON files parse."""
    missing = [name for name in REQUIRED_ARTIFACTS if not (case_dir / name).exists()]
    if missing:
        raise ArtifactValidationError(f"Missing required artifacts: {', '.join(missing)}")

    for name in REQUIRED_ARTIFACTS:
        if not name.endswith(".json"):
            continue
        path = case_dir / name
        try:
            payload = json.loads(path.read_text(encoding="utf-8"))
        except json.JSONDecodeError as exc:
            raise ArtifactValidationError(f"Invalid JSON in {name}: {exc}") from exc
        if not isinstance(payload, dict):
            raise ArtifactValidationError(f"Expected JSON object in {name}")

    if validate_schemas:
        schema_errors = schema_validate_case_dir(case_dir)
        if schema_errors:
            raise ArtifactValidationError(
                "Schema validation failed:\n" + "\n".join(schema_errors[:10])
            )

    return list(REQUIRED_ARTIFACTS)


def copy_to_web(
    case_dir: Path,
    *,
    web_dir: Path | None = None,
    validate_schemas: bool = False,
) -> Path:
    """Validate and copy a generated case directory into web/public/data/cases/."""
    case_dir = case_dir.resolve()
    if not case_dir.exists():
        raise FileNotFoundError(f"Case directory not found: {case_dir}")

    validate_case_dir(case_dir, validate_schemas=validate_schemas)
    case_id = case_dir.name
    destination = (web_dir or web_case_dir(case_id)).resolve()
    destination.parent.mkdir(parents=True, exist_ok=True)

    if destination.exists():
        shutil.rmtree(destination)
    shutil.copytree(case_dir, destination)
    return destination


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Validate and publish case artifacts to web/")
    parser.add_argument(
        "case_path",
        nargs="?",
        help="Path to generated case directory (e.g. generated/cases/sting_pdac)",
    )
    parser.add_argument(
        "--copy-to-web",
        dest="copy_to_web",
        action="store_true",
        help="Copy validated artifacts into web/public/data/cases/{case_id}/",
    )
    parser.add_argument(
        "--validate-schemas",
        dest="validate_schemas",
        action="store_true",
        default=False,
        help="Validate JSON artifacts against schemas/ (strict publish)",
    )
    args = parser.parse_args(argv)

    if not args.case_path:
        parser.error("case_path is required")

    case_path = Path(args.case_path)
    if not case_path.is_absolute() and not case_path.exists():
        generated_guess = generated_case_dir(case_path.name)
        if generated_guess.exists():
            case_path = generated_guess

    try:
        artifacts = validate_case_dir(
            case_path.resolve(),
            validate_schemas=args.validate_schemas,
        )
    except (ArtifactValidationError, FileNotFoundError) as exc:
        print(f"Validation failed: {exc}", file=sys.stderr)
        return 1

    print(f"Validated {len(artifacts)} artifacts in {case_path.resolve()}")

    if args.copy_to_web:
        destination = copy_to_web(
            case_path.resolve(),
            validate_schemas=args.validate_schemas,
        )
        print(f"Copied artifacts to {destination}")

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
