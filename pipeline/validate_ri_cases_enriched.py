"""Validate data/ri/ri_cases_enriched.csv against locked enrichment rules."""

from __future__ import annotations

import argparse
from dataclasses import dataclass, field
from pathlib import Path

import yaml

from pipeline.ri_cases_enriched_io import CASES_CSV, load_cases
from pipeline.ri_cases_enriched_schema import (
    COMP_PREFIXES,
    MAX_SLATER_SHARE_USD,
    MAX_TOTAL_PACKAGE_USD,
)

ROOT = Path(__file__).resolve().parents[1]
ALLOWLIST = ROOT / "data" / "ri" / "ri_institution_allowlist.yaml"


@dataclass
class ValidationReport:
    errors: list[str] = field(default_factory=list)
    warnings: list[str] = field(default_factory=list)

    @property
    def ok(self) -> bool:
        return not self.errors


def _bool(value: str | None) -> bool:
    return (value or "").strip().lower() in {"1", "true", "t", "yes", "y"}


def _int(value: str | None) -> int:
    try:
        return int(float((value or "").strip()))
    except ValueError:
        return 0


def _split_lines(value: str) -> list[str]:
    return [x.strip() for x in (value or "").replace("\r", "").split("\n") if x.strip()]


def _is_discovery_url(url: str) -> bool:
    lower = url.lower()
    return "google.com/search" in lower or "bing.com/search" in lower


def _load_allowlist() -> list[str]:
    if not ALLOWLIST.exists():
        return []
    data = yaml.safe_load(ALLOWLIST.read_text(encoding="utf-8"))
    return list(data.get("publication_affiliations") or [])


def _affiliation_ok(affiliation: str, allowlist: list[str]) -> bool:
    aff = affiliation.lower()
    return any(term.lower() in aff for term in allowlist)


def validate_row(row: dict[str, str], allowlist: list[str]) -> ValidationReport:
    report = ValidationReport()
    case_id = row.get("case_id", "?")
    if (row.get("review_status") or "").lower() != "approved":
        return report

    url = (row.get("primary_patent_url") or "").strip()
    if url and "lens.org" not in url:
        report.errors.append(f"{case_id}: primary_patent_url must be lens.org")
    elif not url and (row.get("primary_lens_id") or "").strip():
        report.errors.append(f"{case_id}: missing primary_patent_url")

    pubs = _split_lines(row.get("publication_titles", ""))
    affs = _split_lines(row.get("publication_ri_affiliations", ""))
    pub_urls = _split_lines(row.get("publication_urls", ""))
    count = _int(row.get("publication_count")) or len(pubs)
    tier = (row.get("catalog_tier") or "").upper()
    if tier == "A":
        if count < 2 or count > 6:
            report.errors.append(f"{case_id}: publication_count must be 2–6 (got {count})")
        if len(pubs) != count:
            report.errors.append(f"{case_id}: publication_titles count mismatch")
        for i, aff in enumerate(affs):
            if not _affiliation_ok(aff, allowlist):
                report.errors.append(
                    f"{case_id}: publication {i + 1} RI affiliation not on allowlist: {aff!r}"
                )
        for i, purl in enumerate(pub_urls):
            if not purl:
                report.errors.append(f"{case_id}: publication_urls[{i}] empty")
            if _is_discovery_url(purl):
                report.errors.append(f"{case_id}: publication_urls[{i}] is a search URL")

    total = _int(row.get("total_package_usd"))
    physician = _int(row.get("physician_share_usd"))
    slater = _int(row.get("slater_share_usd"))
    if total > MAX_TOTAL_PACKAGE_USD:
        report.errors.append(f"{case_id}: total_package_usd {total} > {MAX_TOTAL_PACKAGE_USD}")
    if slater > MAX_SLATER_SHARE_USD:
        report.errors.append(f"{case_id}: slater_share_usd {slater} > {MAX_SLATER_SHARE_USD}")
    if total and physician + slater != total:
        report.errors.append(f"{case_id}: physician + slater must equal total_package_usd")

    for prefix in COMP_PREFIXES:
        name = (row.get(f"{prefix}name") or "").strip()
        if not name:
            continue
        status = (row.get(f"{prefix}validation_status") or "").lower()
        src = (row.get(f"{prefix}value_source_url") or "").strip()
        if status == "verified" and not src:
            report.errors.append(f"{case_id}: {prefix} verified but missing value_source_url")
        if src and _is_discovery_url(src):
            report.errors.append(f"{case_id}: {prefix} value_source_url is a search URL")

    ncts = [x.strip() for x in (row.get("trial_nct_ids") or "").split("|") if x.strip()]
    t_urls = _split_lines(row.get("trial_urls", ""))
    if ncts:
        if len(t_urls) < len(ncts):
            report.errors.append(f"{case_id}: trial_urls missing for nct_ids")
        for url in t_urls:
            if url and "clinicaltrials.gov" not in url:
                report.warnings.append(f"{case_id}: trial url not clinicaltrials.gov: {url}")

    if tier == "A" and not (row.get("physician_lead_name") or "").strip():
        report.warnings.append(f"{case_id}: Tier A missing physician_lead_name")

    return report


def validate(path: Path = CASES_CSV) -> ValidationReport:
    allowlist = _load_allowlist()
    report = ValidationReport()
    rows = load_cases(path)
    if not rows:
        report.errors.append(f"Missing or empty: {path}")
        return report
    included = [r for r in rows if _bool(r.get("catalog_include", "true"))]
    pending = sum(1 for r in included if (r.get("review_status") or "").lower() != "approved")
    report.warnings.append(f"{len(included)} catalog rows; {pending} pending review")
    for row in included:
        sub = validate_row(row, allowlist)
        report.errors.extend(sub.errors)
        report.warnings.extend(sub.warnings)
    return report


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--path", type=Path, default=CASES_CSV)
    args = parser.parse_args()
    report = validate(args.path)
    for w in report.warnings:
        print(f"WARN: {w}")
    for e in report.errors:
        print(f"ERROR: {e}")
    if report.ok:
        print("Validation passed (no errors on approved rows).")
    else:
        raise SystemExit(1)


if __name__ == "__main__":
    main()
