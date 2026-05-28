"""Import Rhode Island physician/IP CSV rows into static case YAML configs.

This utility is intentionally static-first:
- generated cases default to fixture mode only
- no live API assumptions are introduced
"""

from __future__ import annotations

import argparse
import csv
import re
from pathlib import Path


DEFAULT_CSV_PATH = Path("data/ri/ri_physicians_ip_seed.csv")
DEFAULT_OUTPUT_DIR = Path("configs/cases")

CONNECTOR_DEFAULTS_BY_OPPORTUNITY: dict[str, dict[str, bool]] = {
    "therapeutic": {
        "pubmed": True,
        "clinicaltrials": True,
        "opentargets": True,
        "chembl": True,
        "biothings": True,
        "uniprot": True,
        "reactome": True,
        "gwas": True,
        "pharmgkb": True,
        "openfda": True,
        "octagon_market": False,
        "local_docs": True,
    },
    "platform": {
        "pubmed": True,
        "clinicaltrials": True,
        "opentargets": False,
        "chembl": False,
        "biothings": False,
        "uniprot": False,
        "reactome": False,
        "gwas": False,
        "pharmgkb": False,
        "openfda": True,
        "octagon_market": True,
        "local_docs": True,
    },
    "diagnostic": {
        "pubmed": True,
        "clinicaltrials": True,
        "opentargets": False,
        "chembl": False,
        "biothings": True,
        "uniprot": False,
        "reactome": False,
        "gwas": False,
        "pharmgkb": False,
        "openfda": True,
        "octagon_market": True,
        "local_docs": True,
    },
    "digital_therapeutic": {
        "pubmed": True,
        "clinicaltrials": True,
        "opentargets": False,
        "chembl": False,
        "biothings": False,
        "uniprot": False,
        "reactome": False,
        "gwas": False,
        "pharmgkb": False,
        "openfda": True,
        "octagon_market": True,
        "local_docs": True,
    },
    "medical_device": {
        "pubmed": True,
        "clinicaltrials": True,
        "opentargets": False,
        "chembl": False,
        "biothings": False,
        "uniprot": False,
        "reactome": False,
        "gwas": False,
        "pharmgkb": False,
        "openfda": True,
        "octagon_market": True,
        "local_docs": True,
    },
}


def normalize_case_id(value: str) -> str:
    lowered = value.strip().lower()
    lowered = re.sub(r"[^a-z0-9]+", "_", lowered)
    lowered = re.sub(r"_+", "_", lowered).strip("_")
    if not lowered:
        raise ValueError("case_id resolves to empty value")
    return lowered


def parse_bool(value: str, default: bool = False) -> bool:
    normalized = value.strip().lower()
    if not normalized:
        return default
    if normalized in {"1", "true", "t", "yes", "y"}:
        return True
    if normalized in {"0", "false", "f", "no", "n"}:
        return False
    return default


def csv_list(value: str) -> list[str]:
    return [item.strip() for item in value.split("|") if item.strip()]


def quote_yaml_string(value: str | None) -> str:
    text = (value or "").strip()
    if not text:
        return "null"
    escaped = text.replace('"', '\\"')
    return f'"{escaped}"'


def aliases_from_name(name: str) -> list[str]:
    normalized = name.strip()
    if not normalized:
        return []
    return []


def connectors_for_opportunity(opportunity_type: str) -> dict[str, bool]:
    normalized = opportunity_type.strip().lower()
    return CONNECTOR_DEFAULTS_BY_OPPORTUNITY.get(
        normalized,
        CONNECTOR_DEFAULTS_BY_OPPORTUNITY["platform"],
    )


def render_case_yaml(row: dict[str, str]) -> tuple[str, str]:
    case_id = normalize_case_id(row.get("case_id", ""))
    display_name = row.get("display_name", case_id).strip() or case_id
    target = row.get("target", "Unknown target").strip() or "Unknown target"
    indication = row.get("indication", "Unknown indication").strip() or "Unknown indication"
    opportunity_type = (row.get("opportunity_type", "platform").strip() or "platform").lower()
    company = row.get("company", "TBD").strip() or "TBD"
    stage = row.get("development_stage", "discovery").strip() or "discovery"
    mechanism = row.get("mechanism_direction", "").strip()
    modality = row.get("modality", "").strip()
    patient_segment = row.get("patient_segment", "").strip()
    geography = row.get("geography", "Rhode Island").strip() or "Rhode Island"
    asset = row.get("asset", "").strip()
    comparators = csv_list(row.get("comparators", ""))
    strategic_question = row.get("strategic_question", "").strip()
    licensing_question = row.get("licensing_question", "").strip()
    investment_question = row.get("investment_question", "").strip()
    slater_invested = parse_bool(row.get("slater_invested", ""), default=False)

    connectors = connectors_for_opportunity(opportunity_type)
    comparator_lines = (
        "\n".join([f"    - {item}" for item in comparators]) if comparators else "    - TBD comparator"
    )

    yaml_text = f"""case_id: {case_id}
display_name: {display_name}
workflow: translational_diligence
version: v0.5

target:
  name: {target}
  canonical_id: null
  aliases: []

indication:
  name: {indication}
  aliases: []

biology:
  mechanism_direction: {quote_yaml_string(mechanism)}
  modality: {quote_yaml_string(modality)}
  target_alias: null

disease:
  patient_segment: {quote_yaml_string(patient_segment)}
  geography: {quote_yaml_string(geography)}

program:
  asset: {quote_yaml_string(asset)}
  company: {quote_yaml_string(company)}
  opportunity_type: {quote_yaml_string(opportunity_type)}
  slater_invested: {"true" if slater_invested else "false"}
  development_stage: {quote_yaml_string(stage)}
  comparators:
{comparator_lines}

commercial:
  strategic_question: {quote_yaml_string(strategic_question)}
  licensing_question: {quote_yaml_string(licensing_question)}
  investment_question: {quote_yaml_string(investment_question)}

sources:
  pubmed: {"true" if connectors["pubmed"] else "false"}
  clinicaltrials: {"true" if connectors["clinicaltrials"] else "false"}
  opentargets: {"true" if connectors["opentargets"] else "false"}
  chembl: {"true" if connectors["chembl"] else "false"}
  biothings: {"true" if connectors["biothings"] else "false"}
  uniprot: {"true" if connectors["uniprot"] else "false"}
  reactome: {"true" if connectors["reactome"] else "false"}
  gwas: {"true" if connectors["gwas"] else "false"}
  pharmgkb: {"true" if connectors["pharmgkb"] else "false"}
  openfda: {"true" if connectors["openfda"] else "false"}
  octagon_market: {"true" if connectors["octagon_market"] else "false"}
  local_docs: {"true" if connectors["local_docs"] else "false"}

limits:
  max_literature_records: 60
  max_trials: 80
  max_evidence_rows: 100

run_mode_defaults:
  fixture_allowed: true
  live_allowed: false
"""
    return case_id, yaml_text


def import_csv(csv_path: Path, output_dir: Path, overwrite: bool) -> list[Path]:
    if not csv_path.exists():
        raise FileNotFoundError(f"CSV not found: {csv_path}")
    output_dir.mkdir(parents=True, exist_ok=True)

    written: list[Path] = []
    with csv_path.open(newline="", encoding="utf-8") as handle:
        reader = csv.DictReader(handle)
        for row in reader:
            if not row:
                continue
            case_id, yaml_text = render_case_yaml(row)
            out_path = output_dir / f"{case_id}.yaml"
            if out_path.exists() and not overwrite:
                continue
            out_path.write_text(yaml_text, encoding="utf-8")
            written.append(out_path)
    return written


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Import RI physician/IP CSV rows into case YAML files.")
    parser.add_argument("--csv", type=Path, default=DEFAULT_CSV_PATH, help="Path to source CSV file")
    parser.add_argument("--output-dir", type=Path, default=DEFAULT_OUTPUT_DIR, help="Directory for YAML configs")
    parser.add_argument(
        "--overwrite",
        action="store_true",
        help="Overwrite existing case YAML files when case_id matches",
    )
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    written = import_csv(args.csv.resolve(), args.output_dir.resolve(), overwrite=args.overwrite)
    print(f"Wrote {len(written)} case config(s).")
    for path in written:
        print(f"- {path}")


if __name__ == "__main__":
    main()
