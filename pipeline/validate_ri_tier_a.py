"""Validate Tier A catalog consistency across RI data and web publish artifacts."""

from __future__ import annotations

import argparse
import csv
import json
from dataclasses import dataclass, field
from pathlib import Path

from pipeline.apply_seed_resolution import DEDUPE_CASE, SEED_ENRICHMENT
from pipeline.types import repo_root

ROOT = repo_root()
DATA = ROOT / "data" / "ri"
ENRICH = DATA / "ri_opportunities_catalog_enrichment.csv"
OPPS = DATA / "ri_opportunities.csv"
IP_ASSETS = DATA / "ri_ip_assets.csv"
COMBINED = DATA / "ri_opportunities_combined.json"
PROFILES = ROOT / "web" / "public" / "data" / "opportunities" / "profiles"
INDEX = ROOT / "web" / "public" / "data" / "opportunities" / "index.json"

def _expected_tier_a_count() -> int:
    from pipeline.tier_a.build_from_sources import tier_a_registry_count
    from pipeline.tier_a.io import load_registry

    count = tier_a_registry_count()
    if count:
        return count
    active = load_registry(active_only=True)
    return len(active) if active else 25

# Seed-specific invariants from curated resolution.
SEED_PRIMARY_LENS = {
    cid: patch["primary_lens_id"]
    for cid, patch in SEED_ENRICHMENT.items()
    if patch.get("primary_lens_id")
}
SEED_PROGRAM_ONLY = {"cbt_pain_digital_platform_ri"}
SEED_SECONDARY_LENS = {
    "nanode_ri": "104-876-606-446-902",
    "phlip_therapeutics_ri": "129-685-709-438-265",
}
FORBIDDEN_BY_CASE = {
    "monaghan_sepsis_diagnostic_ri": {"063-586-913-488-802"},
}


@dataclass
class ValidationReport:
    errors: list[str] = field(default_factory=list)
    warnings: list[str] = field(default_factory=list)

    @property
    def ok(self) -> bool:
        return not self.errors


def _read_csv(path: Path) -> list[dict[str, str]]:
    with path.open(newline="", encoding="utf-8") as handle:
        return list(csv.DictReader(handle))


def _bool(value: str | None) -> bool:
    return (value or "").strip().lower() in {"1", "true", "t", "yes", "y"}


def validate(
    *,
    enrich_path: Path = ENRICH,
    opps_path: Path = OPPS,
    ip_path: Path = IP_ASSETS,
    combined_path: Path = COMBINED,
    profiles_dir: Path = PROFILES,
    index_path: Path = INDEX,
    expect_web: bool = True,
) -> ValidationReport:
    report = ValidationReport()
    if not enrich_path.exists():
        report.errors.append(f"Missing enrichment catalog: {enrich_path}")
        return report

    enrich_rows = _read_csv(enrich_path)
    tier_a = [
        r
        for r in enrich_rows
        if (r.get("catalog_tier") or "").upper() == "A" and _bool(r.get("catalog_include", "true"))
    ]
    expected = _expected_tier_a_count()
    if len(tier_a) != expected:
        report.errors.append(f"Expected {expected} Tier A included rows, found {len(tier_a)}")

    opps_by = {r["case_id"]: r for r in _read_csv(opps_path)} if opps_path.exists() else {}
    ip_by: dict[str, list[str]] = {}
    for row in _read_csv(ip_path) if ip_path.exists() else []:
        ip_by.setdefault(row["case_id"], []).append(row.get("lens_id", ""))

    combined_ids: set[str] = set()
    if combined_path.exists():
        payload = json.loads(combined_path.read_text(encoding="utf-8"))
        combined_ids = {o["case_id"] for o in payload.get("opportunities", [])}

    index_ids: set[str] = set()
    if index_path.exists():
        index_payload = json.loads(index_path.read_text(encoding="utf-8"))
        if isinstance(index_payload, list):
            items = index_payload
        else:
            items = index_payload.get("opportunities") or index_payload.get("items") or []
        index_ids = {item.get("case_id") or item.get("id") for item in items}
        index_ids.discard(None)

    dedupe = next((r for r in enrich_rows if r["case_id"] == DEDUPE_CASE), None)
    if dedupe:
        if _bool(dedupe.get("catalog_include", "true")):
            report.errors.append(f"{DEDUPE_CASE} must have catalog_include=false")
        if (dedupe.get("catalog_tier") or "").upper() != "B":
            report.errors.append(f"{DEDUPE_CASE} must be catalog_tier=B")

    for row in tier_a:
        case_id = row["case_id"]
        if case_id not in opps_by:
            report.errors.append(f"Tier A missing from ri_opportunities.csv: {case_id}")
        if combined_ids and case_id not in combined_ids:
            report.errors.append(f"Tier A missing from ri_opportunities_combined.json: {case_id}")
        if expect_web and profiles_dir.exists():
            if not (profiles_dir / f"{case_id}.json").exists():
                report.errors.append(f"Tier A missing web profile: {case_id}")
        if index_ids and case_id not in index_ids:
            report.warnings.append(f"Tier A not in web index: {case_id}")

        primary = (row.get("primary_lens_id") or "").strip()
        lens_ids = [x for x in (row.get("ip_lens_ids") or "").split("|") if x]
        try:
            asset_count = int(row.get("ip_asset_count") or 0)
        except ValueError:
            asset_count = -1
        actual_assets = ip_by.get(case_id, [])

        if asset_count != len(actual_assets):
            report.errors.append(
                f"{case_id}: ip_asset_count={asset_count} but ri_ip_assets has {len(actual_assets)}"
            )
        if primary and primary not in lens_ids and asset_count > 0:
            report.errors.append(f"{case_id}: primary_lens_id not listed in ip_lens_ids")

        opp = opps_by.get(case_id, {})
        src = (opp.get("ri_ip_source") or "").strip()
        if primary and asset_count > 0 and src != f"lens:{primary}":
            report.errors.append(f"{case_id}: ri_ip_source={src!r} expected lens:{primary}")

        lead = (row.get("physician_lead_name") or "").strip()
        ri_lead = (row.get("ri_physician_lead") or opp.get("ri_physician_lead") or "").strip()
        if lead and ri_lead and lead.upper() not in ri_lead.upper():
            report.warnings.append(
                f"{case_id}: physician_lead_name={lead!r} vs ri_physician_lead={ri_lead!r}"
            )

    for case_id, expected_primary in SEED_PRIMARY_LENS.items():
        row = next((r for r in enrich_rows if r["case_id"] == case_id), None)
        if not row:
            report.errors.append(f"Seed case missing from enrichment: {case_id}")
            continue
        if (row.get("primary_lens_id") or "").strip() != expected_primary:
            report.errors.append(
                f"{case_id}: primary_lens_id={row.get('primary_lens_id')!r} "
                f"expected {expected_primary!r}"
            )
        for forbidden in FORBIDDEN_BY_CASE.get(case_id, set()):
            if forbidden in ip_by.get(case_id, []):
                report.errors.append(f"{case_id}: forbidden patent lens {forbidden}")

    for case_id in SEED_PROGRAM_ONLY:
        if ip_by.get(case_id):
            report.errors.append(f"{case_id}: expected program_only (no ri_ip_assets)")

    for case_id, secondary in SEED_SECONDARY_LENS.items():
        if secondary not in ip_by.get(case_id, []):
            report.errors.append(f"{case_id}: missing secondary patent {secondary}")

    return report


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--no-web", action="store_true", help="Skip web profile/index checks")
    args = parser.parse_args()
    report = validate(expect_web=not args.no_web)
    for warning in report.warnings:
        print(f"WARN: {warning}")
    for error in report.errors:
        print(f"ERROR: {error}")
    if report.ok:
        print(f"Tier A validation passed ({_expected_tier_a_count()} programs).")
    else:
        raise SystemExit(1)


if __name__ == "__main__":
    main()
