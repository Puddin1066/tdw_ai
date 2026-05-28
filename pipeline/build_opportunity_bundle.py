"""Build aggregated opportunity index, profiles, edges, and program JSON for the web UI."""

from __future__ import annotations

import argparse
import csv
import json
import shutil
from collections import defaultdict
from pathlib import Path
from typing import Any

import yaml

from pipeline.physician_assignment import physician_match_for_case
from pipeline.types import repo_root

DATA_RI = repo_root() / "data" / "ri"
DEFAULT_CASES_ROOT = repo_root() / "generated" / "cases"
DEFAULT_OUT = repo_root() / "web" / "public" / "data" / "opportunities"
DEFAULT_WEB_CASES = repo_root() / "web" / "public" / "data" / "cases"


def _read_csv(path: Path) -> list[dict[str, str]]:
    if not path.exists():
        return []
    with path.open(newline="", encoding="utf-8") as handle:
        return list(csv.DictReader(handle))


def _read_json(path: Path) -> dict[str, Any] | None:
    if not path.exists():
        return None
    return json.loads(path.read_text(encoding="utf-8"))


def _unwrap_data(envelope: dict[str, Any] | None) -> dict[str, Any]:
    if not envelope:
        return {}
    if "data" in envelope and isinstance(envelope["data"], dict):
        return envelope["data"]
    return envelope


def _is_ri_opportunity(case_id: str) -> bool:
    return case_id.endswith("_ri") or case_id.startswith("auto_")


def _load_metadata(case_dir: Path) -> dict[str, Any]:
    yaml_path = case_dir / "metadata.yaml"
    if yaml_path.exists():
        raw = yaml.safe_load(yaml_path.read_text(encoding="utf-8")) or {}
        return raw if isinstance(raw, dict) else {}
    return {}


def _bool_benchmark(metadata: dict[str, Any]) -> bool:
    benchmark = metadata.get("benchmark")
    if isinstance(benchmark, dict):
        return bool(benchmark.get("enabled"))
    return False


def _geography(metadata: dict[str, Any], opp_row: dict[str, str]) -> str:
    profile = metadata.get("input_profile")
    if isinstance(profile, dict):
        disease = profile.get("disease")
        if isinstance(disease, dict) and disease.get("geography"):
            return str(disease["geography"])
    return opp_row.get("geography", "Rhode Island") or "Rhode Island"


def _company(metadata: dict[str, Any], opp_row: dict[str, str]) -> str:
    profile = metadata.get("input_profile")
    if isinstance(profile, dict):
        program = profile.get("program")
        if isinstance(program, dict) and program.get("company"):
            return str(program["company"])
    target = metadata.get("target")
    if isinstance(target, dict) and target.get("name"):
        return str(target["name"])
    return opp_row.get("company", "TBD") or "TBD"


def _opportunity_type(metadata: dict[str, Any], opp_row: dict[str, str]) -> str:
    profile = metadata.get("input_profile")
    if isinstance(profile, dict):
        program = profile.get("program")
        if isinstance(program, dict) and program.get("opportunity_type"):
            return str(program["opportunity_type"])
    return opp_row.get("opportunity_type", "platform") or "platform"


def build_bundle(
    *,
    cases_root: Path,
    out_dir: Path,
    opportunities_csv: Path | None = None,
) -> dict[str, int]:
    """Write opportunity bundle files under out_dir."""
    out_dir.mkdir(parents=True, exist_ok=True)
    profiles_dir = out_dir / "profiles"
    profiles_dir.mkdir(parents=True, exist_ok=True)
    edges_dir = out_dir / "edges"
    edges_dir.mkdir(parents=True, exist_ok=True)

    opp_rows = {row["case_id"]: row for row in _read_csv(opportunities_csv or DATA_RI / "ri_opportunities.csv")}
    ip_by_case: dict[str, list[dict[str, str]]] = defaultdict(list)
    for row in _read_csv(DATA_RI / "ri_ip_assets.csv"):
        case_id = row.get("case_id", "").strip()
        if case_id:
            ip_by_case[case_id].append(row)

    capital_sources = _read_csv(DATA_RI / "ri_capital_sources.csv")
    governance = _read_csv(DATA_RI / "ri_governance_rules.csv")

    index_rows: list[dict[str, Any]] = []
    physician_edges: dict[str, dict[str, Any]] = {}
    template_usage: dict[str, dict[str, Any]] = defaultdict(
        lambda: {"template_id": "", "study_type": "", "opportunity_count": 0, "case_ids": []}
    )

    case_dirs_by_id = {
        path.name: path for path in cases_root.iterdir() if path.is_dir()
    } if cases_root.exists() else {}
    ri_case_ids = sorted(case_id for case_id in opp_rows if _is_ri_opportunity(case_id))

    for case_id in ri_case_ids:
        case_dir = case_dirs_by_id.get(case_id)
        metadata = _load_metadata(case_dir) if case_dir else {}
        opp_row = opp_rows.get(case_id, {})

        if case_dir:
            readiness = _unwrap_data(_read_json(case_dir / "ri_financing_readiness.json"))
            physician = _unwrap_data(_read_json(case_dir / "ri_physician_match.json"))
            inflection = _unwrap_data(_read_json(case_dir / "ri_clinical_inflection.json"))
            capital = _unwrap_data(_read_json(case_dir / "ri_capital_match.json"))
        else:
            readiness = {}
            physician = physician_match_for_case(case_id)
            inflection = {}
            capital = {}

        target = metadata.get("target")
        indication = metadata.get("indication")
        target_name = (
            target.get("name") if isinstance(target, dict) else opp_row.get("target", case_id)
        ) or case_id
        indication_name = (
            indication.get("name")
            if isinstance(indication, dict)
            else opp_row.get("indication", "Unknown")
        ) or "Unknown"

        display_name = str(metadata.get("display_name") or opp_row.get("display_name") or case_id)
        candidates = physician.get("candidate_physicians") or []
        if not isinstance(candidates, list):
            candidates = []
        staffing_gaps = physician.get("staffing_gaps") or []
        if not isinstance(staffing_gaps, list):
            staffing_gaps = []
        required_roles = physician.get("required_roles") or []
        required_specialties = physician.get("required_specialties") or []
        best = inflection.get("best_validation_event") if isinstance(inflection.get("best_validation_event"), dict) else {}

        ip_assets = ip_by_case.get(case_id, [])[:2]
        primary_lens = ip_assets[0].get("lens_id") if ip_assets else opp_row.get("ri_ip_source", "").replace("lens:", "")

        def _num(value: Any, default: float = 0) -> float:
            try:
                return float(value)
            except (TypeError, ValueError):
                return default

        def _int(value: Any, default: int = 0) -> int:
            try:
                return int(float(value))
            except (TypeError, ValueError):
                return default

        index_row: dict[str, Any] = {
            "case_id": case_id,
            "display_name": display_name,
            "llm_inferred_label": opp_row.get("llm_inferred_label") or display_name,
            "opportunity_type": _opportunity_type(metadata, opp_row),
            "indication": indication_name,
            "target": str(target_name),
            "company": _company(metadata, opp_row),
            "development_stage": str(
                opp_row.get("development_stage")
                or (metadata.get("input_profile") or {}).get("program", {}).get("development_stage")
                or "validation"
            ),
            "geography": _geography(metadata, opp_row),
            "capital_gap_usd": _int(opp_row.get("capital_gap_usd") or capital.get("private_match_needed_usd")),
            "budget_ceiling_usd": _int(opp_row.get("budget_ceiling_usd")),
            "target_timeline_weeks": _int(opp_row.get("target_timeline_weeks"), 20),
            "slater_invested": str(opp_row.get("slater_invested", "")).lower() == "true"
            or bool(readiness.get("slater_invested")),
            "ri_institution": opp_row.get("ri_institution") or "",
            "patent_count": len(ip_assets),
            "primary_lens_id": primary_lens or None,
            "financing_readiness_state": readiness.get("financing_readiness_state", "not_financeable_yet"),
            "financing_readiness_score_0_100": _num(readiness.get("financing_readiness_score_0_100")),
            "clinical_inflection_score_0_100": _num(readiness.get("clinical_inflection_score_0_100")),
            "staffing_feasibility_score_0_100": _num(readiness.get("staffing_feasibility_score_0_100")),
            "capital_path_score_0_100": _num(readiness.get("capital_path_score_0_100")),
            "capital_gap_remaining_usd": _int(capital.get("capital_gap_remaining_usd")),
            "private_match_needed_usd": _int(capital.get("private_match_needed_usd")),
            "physician_candidate_count": len(candidates),
            "staffing_gaps": [str(g) for g in staffing_gaps],
            "required_roles": [str(r) for r in required_roles],
            "required_specialties": [str(s) for s in required_specialties],
            "best_template_id": best.get("template_id"),
            "estimated_cost_usd": _int(inflection.get("estimated_cost_usd")),
            "estimated_duration_weeks": _int(inflection.get("estimated_duration_weeks")),
            "financing_milestone": str(inflection.get("financing_milestone") or ""),
            "mocked": bool(
                readiness.get("mocked") or physician.get("mocked") or inflection.get("mocked")
            ),
            "confidence_0_1": _num(readiness.get("confidence_0_1"), 0.5),
            "is_ri_opportunity": True,
            "is_benchmark": _bool_benchmark(metadata),
        }
        index_rows.append(index_row)

        profile = {
            "case_id": case_id,
            "display_name": display_name,
            "llm_inferred_label": index_row["llm_inferred_label"],
            "ri_notes": opp_row.get("ri_notes") or "",
            "ri_physician_lead": opp_row.get("ri_physician_lead") or "TBD",
            "conflict_tags": [t for t in (opp_row.get("conflict_tags") or "").split("|") if t],
            "ri_institution": index_row["ri_institution"],
            "ri_ip_source": opp_row.get("ri_ip_source") or "",
            "ip_assets": [
                {
                    "asset_id": asset.get("asset_id"),
                    "title": asset.get("title"),
                    "lens_id": asset.get("lens_id"),
                    "url": asset.get("url"),
                    "owners": asset.get("owners"),
                    "legal_status": asset.get("legal_status"),
                    "publication_date": asset.get("publication_date"),
                }
                for asset in ip_assets
            ],
        }
        (profiles_dir / f"{case_id}.json").write_text(
            json.dumps(profile, indent=2) + "\n", encoding="utf-8"
        )

        for candidate in candidates:
            if not isinstance(candidate, dict):
                continue
            pid = str(candidate.get("physician_id") or "").strip()
            if not pid:
                continue
            entry = physician_edges.setdefault(
                pid,
                {
                    "physician_id": pid,
                    "name": candidate.get("name"),
                    "specialty": candidate.get("specialty"),
                    "institution": candidate.get("institution"),
                    "opportunities": [],
                },
            )
            entry["opportunities"].append(
                {
                    "case_id": case_id,
                    "display_name": display_name,
                    "match_score_0_100": candidate.get("match_score_0_100", 0),
                    "roles_matched": candidate.get("roles_matched") or [],
                }
            )

        template_id = best.get("template_id")
        if template_id:
            bucket = template_usage[str(template_id)]
            bucket["template_id"] = str(template_id)
            bucket["study_type"] = str(best.get("study_type") or "")
            bucket["case_ids"].append(case_id)
            bucket["opportunity_count"] = len(bucket["case_ids"])

    index_rows.sort(key=lambda row: (-row["financing_readiness_score_0_100"], row["display_name"]))
    (out_dir / "index.json").write_text(json.dumps(index_rows, indent=2) + "\n", encoding="utf-8")

    physician_list = sorted(
        physician_edges.values(),
        key=lambda item: -len(item.get("opportunities") or []),
    )
    (edges_dir / "physician_opportunities.json").write_text(
        json.dumps(physician_list, indent=2) + "\n", encoding="utf-8"
    )

    trial_list = sorted(
        template_usage.values(),
        key=lambda item: -int(item.get("opportunity_count") or 0),
    )
    (edges_dir / "trial_templates.json").write_text(
        json.dumps(trial_list, indent=2) + "\n", encoding="utf-8"
    )

    program = {
        "title": "RI Physician-Led Venture Syndicates",
        "subtitle": "Rhode Island technologies, clinician syndicates, and Slater SSBCI match capital",
        "capital_sources": [
            {
                "source_id": row.get("source_id"),
                "source_name": row.get("source_name"),
                "source_type": row.get("source_type"),
                "check_min_usd": int(float(row.get("check_min_usd") or 0)),
                "check_max_usd": int(float(row.get("check_max_usd") or 0)),
                "decision_cycle_weeks": int(float(row.get("decision_cycle_weeks") or 0)),
                "ri_focus": str(row.get("ri_focus", "")).lower() == "true",
            }
            for row in capital_sources
        ],
        "governance_rules": [
            {
                "rule_id": row.get("rule_id"),
                "category": row.get("category"),
                "rule_text": row.get("rule_text"),
            }
            for row in governance
        ],
        "stats": {
            "opportunity_count": len(index_rows),
            "financeable_now_count": sum(
                1 for row in index_rows if row["financing_readiness_state"] == "financeable_now"
            ),
            "total_capital_gap_usd": sum(row["capital_gap_usd"] for row in index_rows),
        },
    }
    (out_dir / "program.json").write_text(json.dumps(program, indent=2) + "\n", encoding="utf-8")

    return {
        "index_count": len(index_rows),
        "profile_count": len(index_rows),
        "physician_edge_count": len(physician_list),
        "trial_template_count": len(trial_list),
        "case_ids": [row["case_id"] for row in index_rows],
    }


def sync_ri_cases_to_web(
    *,
    cases_root: Path,
    web_cases_root: Path,
    case_ids: list[str],
) -> int:
    """Copy RI case artifact folders into web/public/data/cases/."""
    web_cases_root.mkdir(parents=True, exist_ok=True)
    copied = 0
    for case_id in case_ids:
        source = cases_root / case_id
        if not source.is_dir():
            continue
        destination = web_cases_root / case_id
        if destination.exists():
            shutil.rmtree(destination)
        shutil.copytree(source, destination)
        copied += 1
    return copied


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Build web opportunity bundle JSON")
    parser.add_argument(
        "--cases-root",
        type=Path,
        default=DEFAULT_CASES_ROOT,
        help="Directory containing per-case artifact folders",
    )
    parser.add_argument(
        "--out-dir",
        type=Path,
        default=DEFAULT_OUT,
        help="Output directory (web/public/data/opportunities)",
    )
    parser.add_argument(
        "--sync-cases",
        action="store_true",
        help="Copy RI case folders into web/public/data/cases/",
    )
    parser.add_argument(
        "--web-cases-root",
        type=Path,
        default=DEFAULT_WEB_CASES,
        help="Web public cases directory for --sync-cases",
    )
    args = parser.parse_args(argv)
    counts = build_bundle(cases_root=args.cases_root.resolve(), out_dir=args.out_dir.resolve())
    print(f"Wrote opportunity bundle to {args.out_dir.resolve()}")
    for key, value in counts.items():
        if key == "case_ids":
            continue
        print(f"  {key}: {value}")
    if args.sync_cases:
        case_ids = counts.get("case_ids", [])
        if isinstance(case_ids, list):
            copied = sync_ri_cases_to_web(
                cases_root=args.cases_root.resolve(),
                web_cases_root=args.web_cases_root.resolve(),
                case_ids=case_ids,
            )
            print(f"  synced_cases: {copied}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
