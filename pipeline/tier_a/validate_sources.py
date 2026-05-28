"""Validate Tier A canonical source files before build."""

from __future__ import annotations

import argparse
from dataclasses import dataclass, field
from urllib.parse import urlparse

from pipeline.tier_a.io import (
    comparables_by_case,
    evidence_by_case,
    load_comparables,
    load_evidence_overrides,
    load_finance_policy,
    load_registry,
    registry_by_case,
)
from pipeline.tier_a.paths import IP_ASSETS_PATH, OPPORTUNITIES_PATH
from pipeline.tier_a.io import read_csv

VALID_STATUSES = {"draft", "active", "archived"}
VALID_VALIDATION = {"suggested", "estimated", "verified"}
VALID_EVIDENCE_GRADES = {"A", "B", "C", "draft", ""}
VALID_REVIEW = {"pending", "approved", "needs_work", ""}


@dataclass
class SourceValidationReport:
    errors: list[str] = field(default_factory=list)
    warnings: list[str] = field(default_factory=list)

    @property
    def ok(self) -> bool:
        return not self.errors


def _is_url(value: str) -> bool:
    try:
        parsed = urlparse(value)
        return parsed.scheme in {"http", "https"} and bool(parsed.netloc)
    except ValueError:
        return False


def validate_sources(*, strict_evidence: bool = False) -> SourceValidationReport:
    report = SourceValidationReport()
    registry = load_registry()
    if not registry:
        report.errors.append("tier_a/registry.csv is empty or missing")
        return report

    policy = load_finance_policy()
    if not policy:
        report.warnings.append("tier_a/finance_policy.yaml missing or empty; build uses code defaults")

    reg_by = registry_by_case(registry)
    comps_by = comparables_by_case()
    evidence_by = evidence_by_case()
    opps = {r["case_id"]: r for r in read_csv(OPPORTUNITIES_PATH)} if OPPORTUNITIES_PATH.exists() else {}
    ip_by: dict[str, list[str]] = {}
    for row in read_csv(IP_ASSETS_PATH) if IP_ASSETS_PATH.exists() else []:
        ip_by.setdefault(row["case_id"], []).append(row.get("lens_id", ""))

    seen_ids: set[str] = set()
    active_ids: list[str] = []
    for row in registry:
        case_id = (row.get("case_id") or "").strip()
        if not case_id:
            report.errors.append("registry row missing case_id")
            continue
        if case_id in seen_ids:
            report.errors.append(f"duplicate registry case_id: {case_id}")
        seen_ids.add(case_id)

        status = (row.get("status") or "active").lower()
        if status not in VALID_STATUSES:
            report.errors.append(f"{case_id}: invalid status={status!r}")
        if status in {"active", "draft"}:
            active_ids.append(case_id)

        if status == "active" and case_id not in opps:
            report.errors.append(f"{case_id}: active in registry but missing from ri_opportunities.csv")

        primary = (row.get("primary_lens_id") or "").strip()
        if primary and status == "active":
            assets = ip_by.get(case_id, [])
            if assets and primary not in assets:
                report.warnings.append(
                    f"{case_id}: primary_lens_id {primary} not in ri_ip_assets ({len(assets)} assets)"
                )

    for case_id in active_ids:
        comps = comps_by.get(case_id, [])
        if not comps:
            report.errors.append(f"{case_id}: active Tier A has no rows in comparables.csv")
            continue
        ranks = []
        for comp in comps:
            name = (comp.get("precedent_name") or "").strip()
            if not name:
                report.errors.append(f"{case_id}: comparable missing precedent_name")
            try:
                ranks.append(int(comp.get("precedent_rank") or 0))
            except ValueError:
                report.errors.append(f"{case_id}: invalid precedent_rank")
            vstatus = (comp.get("validation_status") or "suggested").lower()
            if vstatus not in VALID_VALIDATION:
                report.errors.append(f"{case_id}: invalid validation_status on {name!r}")
            if vstatus == "verified":
                url = (comp.get("value_source_url") or "").strip()
                if not url:
                    report.errors.append(f"{case_id}: verified comp {name!r} missing value_source_url")
                elif not _is_url(url):
                    report.errors.append(f"{case_id}: verified comp {name!r} has invalid value_source_url")
                anchor = (comp.get("value_anchor_usd") or "").strip()
                if not anchor:
                    report.errors.append(f"{case_id}: verified comp {name!r} missing value_anchor_usd")
        if ranks and ranks != list(range(1, len(ranks) + 1)):
            report.warnings.append(f"{case_id}: precedent_rank not contiguous from 1 ({ranks})")

        if case_id not in evidence_by:
            report.warnings.append(f"{case_id}: no evidence_overrides.csv row (add before investor-facing)")
        else:
            ev = evidence_by[case_id]
            grade = (ev.get("evidence_grade") or "").strip()
            if grade not in VALID_EVIDENCE_GRADES:
                report.errors.append(f"{case_id}: invalid evidence_grade={grade!r}")
            review = (ev.get("review_status") or "").strip()
            if review not in VALID_REVIEW:
                report.errors.append(f"{case_id}: invalid review_status={review!r}")
            if strict_evidence and review != "approved":
                report.errors.append(f"{case_id}: strict mode requires review_status=approved")

    for case_id in comps_by:
        if case_id not in reg_by:
            report.errors.append(f"comparables.csv case_id not in registry: {case_id}")

    for case_id in evidence_by:
        if case_id not in reg_by:
            report.errors.append(f"evidence_overrides.csv case_id not in registry: {case_id}")

    return report


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--strict-evidence", action="store_true")
    args = parser.parse_args()
    report = validate_sources(strict_evidence=args.strict_evidence)
    for warning in report.warnings:
        print(f"WARN: {warning}")
    for error in report.errors:
        print(f"ERROR: {error}")
    if report.ok:
        print(f"Tier A source validation passed ({len(load_registry(active_only=True))} active programs).")
    else:
        raise SystemExit(1)


if __name__ == "__main__":
    main()
