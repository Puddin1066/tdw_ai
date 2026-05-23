"""Generate, evaluate, and publish static case packets for the web client."""

from __future__ import annotations

import argparse
import json
import subprocess
import sys
from dataclasses import dataclass
from pathlib import Path
from typing import Any

import yaml
from evals.run_evals import run_evaluations, write_eval_results
from pipeline.artifact_writer import copy_to_web
from pipeline.config_loader import load_case_config
from pipeline.run_workflow import run_case_workflow
from pipeline.types import RunMode, repo_root


@dataclass(frozen=True)
class PublishResult:
    case_id: str
    case_dir: Path
    web_dir: Path
    eval_passed: bool | None
    eval_score: float | None
    comparability_passed: bool | None


COMPARABILITY_THRESHOLDS = {
    "min_connectors_with_records": 3,
    "min_total_records": 10,
    "max_fallback_entries": 0,
    "max_generic_risk_titles": 0,
}


def discover_case_configs(config_dir: Path) -> list[Path]:
    """Return available case config files from configs/cases/."""
    if not config_dir.exists():
        return []
    return sorted(path for path in config_dir.glob("*.yaml") if path.is_file())


def resolve_case_configs(config_dir: Path, requested_cases: list[str], all_cases: bool) -> list[Path]:
    """Resolve requested case IDs/paths into config file paths."""
    if all_cases:
        configs = discover_case_configs(config_dir)
        if not configs:
            raise FileNotFoundError(f"No case configs found in {config_dir}")
        return configs

    resolved: list[Path] = []
    seen: set[Path] = set()
    for raw in requested_cases:
        token = raw.strip()
        if not token:
            continue
        candidate = Path(token)
        if candidate.suffix == ".yaml":
            path = candidate if candidate.is_absolute() else (repo_root() / candidate)
        else:
            path = config_dir / f"{token}.yaml"
        path = path.resolve()
        if not path.exists():
            raise FileNotFoundError(f"Case config not found: {path}")
        if path in seen:
            continue
        seen.add(path)
        resolved.append(path)

    if not resolved:
        raise ValueError("Provide --all-cases or at least one --case")
    return resolved


def publish_cases(
    config_paths: list[Path],
    *,
    mode: RunMode,
    run_evals: bool,
    allow_failed_evals: bool,
    allow_comparability_fail: bool,
    validate_schemas: bool,
    require_biomcp: bool,
) -> list[PublishResult]:
    """Run workflow + eval + publish-to-web for each requested case."""
    results: list[PublishResult] = []
    for config_path in config_paths:
        config = load_case_config(config_path)
        case_dir = run_case_workflow(config, mode)
        if require_biomcp and mode == "live":
            _assert_biomcp_integrity(case_dir, _required_biomcp_connectors(config))

        eval_passed: bool | None = None
        eval_score: float | None = None
        comparability_passed: bool | None = None
        if _comparability_required(mode) and not run_evals:
            raise RuntimeError(
                f"Comparability policy requires evals for {config.case_id}; remove --skip-evals or run in fixture mode."
            )
        if run_evals:
            payload = run_evaluations(case_dir)
            write_eval_results(case_dir, payload)
            eval_data = payload.get("data", {})
            eval_passed = bool(eval_data.get("overall_passed"))
            raw_score = eval_data.get("aggregate_score")
            eval_score = float(raw_score) if isinstance(raw_score, (int, float)) else None
            comparability_issues = _comparability_issues(payload, mode=mode)
            comparability_passed = len(comparability_issues) == 0
            _write_comparability_context(case_dir, payload, comparability_issues, mode=mode)
            if comparability_issues and not allow_comparability_fail:
                raise RuntimeError(
                    f"Comparability policy failed for {config.case_id}; "
                    "re-run with --allow-comparability-fail to publish anyway."
                )
            if not eval_passed and not allow_failed_evals:
                raise RuntimeError(
                    f"Eval failed for {config.case_id}; re-run with --allow-failed-evals "
                    "to publish anyway."
                )

        web_dir = copy_to_web(case_dir, validate_schemas=validate_schemas)
        results.append(
            PublishResult(
                case_id=config.case_id,
                case_dir=case_dir,
                web_dir=web_dir,
                eval_passed=eval_passed,
                eval_score=eval_score,
                comparability_passed=comparability_passed,
            )
        )
    return results


def _comparability_required(mode: RunMode) -> bool:
    return mode == "live"


def _comparability_issues(payload: dict[str, Any], *, mode: RunMode) -> list[str]:
    if not _comparability_required(mode):
        return []
    data = payload.get("data", {})
    if not isinstance(data, dict):
        return ["eval payload missing data block"]
    metrics = data.get("metrics", {})
    if not isinstance(metrics, dict):
        return ["eval payload missing metrics block"]
    issues: list[str] = []
    if metrics.get("benchmark_contract_passed") is not True:
        issues.append("benchmark_contract_passed=false")
    if int(metrics.get("contract_connectors_with_records", 0)) < COMPARABILITY_THRESHOLDS["min_connectors_with_records"]:
        issues.append("insufficient connectors_with_records")
    if int(metrics.get("contract_total_records", 0)) < COMPARABILITY_THRESHOLDS["min_total_records"]:
        issues.append("insufficient total_records")
    if int(metrics.get("contract_fallback_entries", 0)) > COMPARABILITY_THRESHOLDS["max_fallback_entries"]:
        issues.append("fallback connector entries present")
    if int(metrics.get("contract_generic_risk_titles", 0)) > COMPARABILITY_THRESHOLDS["max_generic_risk_titles"]:
        issues.append("generic risk titles present")
    return issues


def _write_comparability_context(
    case_dir: Path,
    payload: dict[str, Any],
    issues: list[str],
    *,
    mode: RunMode,
) -> None:
    data = payload.get("data", {})
    metrics = data.get("metrics", {}) if isinstance(data, dict) else {}
    report = {
        "policy_version": "v1",
        "mode": mode,
        "required": _comparability_required(mode),
        "passed": len(issues) == 0,
        "issues": issues,
        "thresholds": COMPARABILITY_THRESHOLDS,
        "metrics": metrics if isinstance(metrics, dict) else {},
    }
    report_path = case_dir / "comparability_contract.json"
    report_path.write_text(json.dumps(report, indent=2) + "\n", encoding="utf-8")

    metadata_path = case_dir / "metadata.yaml"
    if not metadata_path.exists():
        return
    metadata = yaml.safe_load(metadata_path.read_text(encoding="utf-8")) or {}
    if not isinstance(metadata, dict):
        metadata = {}
    metadata["comparability_contract"] = {
        "policy_version": report["policy_version"],
        "required": report["required"],
        "passed": report["passed"],
        "issues": report["issues"],
        "benchmark_contract_score": (metrics.get("benchmark_contract_score") if isinstance(metrics, dict) else None),
        "connectors_with_records": (metrics.get("contract_connectors_with_records") if isinstance(metrics, dict) else None),
        "total_records": (metrics.get("contract_total_records") if isinstance(metrics, dict) else None),
    }
    metadata_path.write_text(yaml.safe_dump(metadata, sort_keys=False), encoding="utf-8")


def _required_biomcp_connectors(config: object) -> list[str]:
    sources = getattr(config, "sources", None)
    if sources is None:
        return []
    mapping = {
        "pubmed": bool(getattr(sources, "pubmed", False)),
        "clinicaltrials": bool(getattr(sources, "clinicaltrials", False)),
        "opentargets": bool(getattr(sources, "opentargets", False)),
        "chembl": bool(getattr(sources, "chembl", False)),
        "biothings": bool(getattr(sources, "biothings", False)),
        "uniprot": bool(getattr(sources, "uniprot", False)),
        "reactome": bool(getattr(sources, "reactome", False)),
        "gwas": bool(getattr(sources, "gwas", False)),
        "pharmgkb": bool(getattr(sources, "pharmgkb", False)),
        "openfda": bool(getattr(sources, "openfda", False)),
    }
    return [name for name, enabled in mapping.items() if enabled]


def _assert_biomcp_integrity(case_dir: Path, required_connectors: list[str]) -> None:
    manifest_path = case_dir / "source_manifest.json"
    if not manifest_path.exists():
        raise RuntimeError(f"BioMCP strict mode requires source_manifest.json in {case_dir}")
    payload = json.loads(manifest_path.read_text(encoding="utf-8"))
    data = payload.get("data", {})
    entries = data.get("entries", [])
    if not isinstance(entries, list):
        raise RuntimeError("BioMCP strict mode: source_manifest entries missing or invalid")

    entry_by_name: dict[str, dict] = {}
    for entry in entries:
        if isinstance(entry, dict):
            name = entry.get("connector_name")
            if isinstance(name, str) and name:
                entry_by_name[name] = entry

    failures: list[str] = []
    for connector_name in required_connectors:
        entry = entry_by_name.get(connector_name)
        if not entry:
            failures.append(f"{connector_name}: missing source_manifest entry")
            continue

        warnings = entry.get("warnings", [])
        if not isinstance(warnings, list):
            warnings = []
        errors = entry.get("errors", [])
        if not isinstance(errors, list):
            errors = []

        if errors:
            failures.append(f"{connector_name}: connector errors present ({errors[0]})")
            continue

        biomcp_warning = next(
            (
                warning
                for warning in warnings
                if isinstance(warning, str) and ("BioMCP" in warning or "biomcp" in warning)
            ),
            None,
        )
        if biomcp_warning:
            failures.append(f"{connector_name}: BioMCP warning ({biomcp_warning})")

        raw_path = case_dir / "raw" / f"{connector_name}_raw.json"
        if not raw_path.exists():
            failures.append(f"{connector_name}: missing raw payload file ({raw_path.name})")
            continue
        raw_payload = json.loads(raw_path.read_text(encoding="utf-8"))
        backend = ((raw_payload.get("raw_payload") or {}).get("backend") if isinstance(raw_payload, dict) else None)
        if backend != "biomcp":
            failures.append(f"{connector_name}: raw payload backend is not biomcp")

    if failures:
        raise RuntimeError(
            "BioMCP strict mode failed:\n- " + "\n- ".join(failures)
        )


def _run_web_build() -> None:
    completed = subprocess.run(
        ["npm", "run", "build", "--prefix", "web"],
        cwd=repo_root(),
        capture_output=True,
        text=True,
        check=False,
    )
    if completed.returncode != 0:
        stderr = completed.stderr.strip()
        stdout = completed.stdout.strip()
        raise RuntimeError(stderr or stdout or "web build failed")


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        description="Generate and cache case packets for static web deployment."
    )
    parser.add_argument(
        "--mode",
        choices=["fixture", "live"],
        default="fixture",
        help="Workflow mode used to generate case packets (default: fixture).",
    )
    parser.add_argument(
        "--case",
        dest="cases",
        action="append",
        default=[],
        help="Case ID (e.g. sting_pdac) or config path. Repeat for multiple cases.",
    )
    parser.add_argument(
        "--all-cases",
        action="store_true",
        help="Publish all configs under configs/cases/*.yaml.",
    )
    parser.add_argument(
        "--config-dir",
        default="configs/cases",
        help="Directory containing case YAML configs (default: configs/cases).",
    )
    parser.add_argument(
        "--skip-evals",
        action="store_true",
        help="Skip eval generation/check before publishing to web cache.",
    )
    parser.add_argument(
        "--allow-failed-evals",
        action="store_true",
        help="Publish even when evals report overall_passed=false.",
    )
    parser.add_argument(
        "--allow-comparability-fail",
        action="store_true",
        help="Publish even when comparability policy fails (live mode only).",
    )
    parser.add_argument(
        "--validate-schemas",
        action="store_true",
        help="Enable strict schema validation before copy-to-web.",
    )
    parser.add_argument(
        "--build-web",
        action="store_true",
        help="Run `npm run build --prefix web` after publishing case data.",
    )
    parser.add_argument(
        "--allow-biomcp-fallback",
        action="store_true",
        help="Allow connector fallback when BioMCP is unavailable (live mode).",
    )
    args = parser.parse_args(argv)

    config_dir = (repo_root() / args.config_dir).resolve()
    try:
        config_paths = resolve_case_configs(config_dir, args.cases, args.all_cases)
        results = publish_cases(
            config_paths,
            mode=args.mode,
            run_evals=not args.skip_evals,
            allow_failed_evals=args.allow_failed_evals,
            allow_comparability_fail=args.allow_comparability_fail,
            validate_schemas=args.validate_schemas,
            require_biomcp=(args.mode == "live" and not args.allow_biomcp_fallback),
        )
        if args.build_web:
            _run_web_build()
    except (FileNotFoundError, ValueError, RuntimeError) as exc:
        print(f"Publish failed: {exc}", file=sys.stderr)
        return 1

    print("Published static case cache:")
    for result in results:
        if result.eval_passed is None:
            eval_text = "evals=skipped"
        else:
            status = "pass" if result.eval_passed else "failed"
            score = f"{result.eval_score:.3f}" if result.eval_score is not None else "n/a"
            contract = (
                "contract=skipped"
                if result.comparability_passed is None
                else ("contract=pass" if result.comparability_passed else "contract=fail")
            )
            eval_text = f"evals={status} (score={score}; {contract})"
        print(f"- {result.case_id}: {result.web_dir} [{eval_text}]")
    if args.build_web:
        print("Web build completed: web/out")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
