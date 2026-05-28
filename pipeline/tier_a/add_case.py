"""Interactive Tier A onboarding: registry, comparables, finance, evidence QC."""

from __future__ import annotations

import argparse
import re
import sys
from datetime import date
from typing import Any

from pipeline.tier_a.build_from_sources import apply_tier_a_to_catalog_row
from pipeline.tier_a.io import (
    comparables_by_case,
    ensure_tier_a_dir,
    evidence_by_case,
    load_comparables,
    load_evidence_overrides,
    load_registry,
    read_csv,
    registry_by_case,
    write_comparables,
    write_evidence_overrides,
    write_registry,
)
from pipeline.tier_a.paths import CATALOG_PATH, IP_ASSETS_PATH, OPPORTUNITIES_PATH
from pipeline.tier_a.validate_sources import validate_sources


def _prompt(label: str, default: str = "", *, required: bool = False) -> str:
    suffix = f" [{default}]" if default else ""
    while True:
        raw = input(f"{label}{suffix}: ").strip()
        if not raw:
            if default:
                return default
            if not required:
                return ""
            print("  (required)")
            continue
        return raw


def _prompt_yes_no(label: str, default: bool = False) -> bool:
    default_s = "Y/n" if default else "y/N"
    raw = input(f"{label} ({default_s}): ").strip().lower()
    if not raw:
        return default
    return raw in {"y", "yes", "1", "true"}


def _prompt_choice(label: str, choices: list[str], default: str = "") -> str:
    print(f"{label}")
    for index, choice in enumerate(choices, start=1):
        mark = " *" if choice == default else ""
        print(f"  {index}. {choice}{mark}")
    while True:
        raw = input("Choose number or type value: ").strip()
        if not raw and default:
            return default
        if raw.isdigit():
            idx = int(raw) - 1
            if 0 <= idx < len(choices):
                return choices[idx]
        if raw in choices:
            return raw
        print("  Invalid choice")


def _load_suggestions(case_id: str) -> dict[str, Any]:
    catalog = {r["case_id"]: r for r in read_csv(CATALOG_PATH)} if CATALOG_PATH.exists() else {}
    opps = {r["case_id"]: r for r in read_csv(OPPORTUNITIES_PATH)} if OPPORTUNITIES_PATH.exists() else {}
    ip_rows = [r for r in read_csv(IP_ASSETS_PATH) if r.get("case_id") == case_id] if IP_ASSETS_PATH.exists() else []
    catalog_row = catalog.get(case_id, {})
    opp_row = opps.get(case_id, catalog_row)
    existing_prec = comparables_by_case().get(case_id, [])
    return {
        "catalog": catalog_row,
        "opportunity": opp_row,
        "ip_assets": ip_rows,
        "precedents": existing_prec,
    }


def _suggest_registry(case_id: str, hints: dict[str, Any]) -> dict[str, str]:
    cat = hints.get("catalog") or {}
    opp = hints.get("opportunity") or {}
    ip_assets = hints.get("ip_assets") or []
    primary_lens = cat.get("primary_lens_id") or ""
    if not primary_lens and ip_assets:
        primary_lens = ip_assets[0].get("lens_id", "")

    print("\n--- Program identity (registry.csv) ---")
    title = _prompt("title_clean", cat.get("title_clean") or opp.get("display_name", case_id))
    company = _prompt("company", cat.get("company") or opp.get("company", "TBD"))
    opportunity_type = _prompt_choice(
        "opportunity_type",
        ["platform", "therapeutic", "diagnostic", "medical_device", "digital_therapeutic"],
        (cat.get("opportunity_type") or opp.get("opportunity_type") or "platform").lower(),
    )
    indication = _prompt("indication", cat.get("indication") or opp.get("indication", ""))
    program_family = _prompt("program_family (precedent group hint)", cat.get("program_family", ""))
    physician_lead = _prompt(
        "physician_lead_name",
        cat.get("physician_lead_name") or opp.get("ri_physician_lead", ""),
    )
    physician_npi = _prompt("physician_lead_npi", cat.get("physician_lead_npi", ""))
    primary_lens_id = _prompt("primary_lens_id", primary_lens)
    ri_notes = _prompt("ri_notes", cat.get("ri_notes") or opp.get("ri_notes", ""))
    data_caveat = _prompt("data_caveat", cat.get("data_caveat", ""))

    status = _prompt_choice("status", ["draft", "active"], "draft")
    promotion = _prompt_choice(
        "promotion_source",
        ["manual", "seed", "auto_promoted"],
        "manual" if case_id.startswith("auto_") else "seed",
    )

    print("\n--- Finance (registry overrides; blank = policy inference at build) ---")
    capital_gap = _prompt("capital_gap_usd override", cat.get("capital_gap_usd", ""))
    budget = _prompt("budget_ceiling_usd override", cat.get("budget_ceiling_usd", ""))
    clinical_weeks = _prompt("clinical_duration_weeks override", cat.get("clinical_duration_weeks", ""))
    dev_stage = _prompt(
        "development_stage override",
        cat.get("development_stage") or opp.get("development_stage", ""),
    )

    reviewer = _prompt("reviewed_by", "interactive")
    reviewed_at = date.today().isoformat()

    return {
        "case_id": case_id,
        "title_clean": title,
        "program_family": program_family,
        "company": company,
        "opportunity_type": opportunity_type,
        "indication": indication,
        "primary_lens_id": primary_lens_id,
        "physician_lead_name": physician_lead,
        "physician_lead_npi": physician_npi,
        "status": status,
        "promotion_source": promotion,
        "capital_gap_usd": capital_gap,
        "budget_ceiling_usd": budget,
        "clinical_duration_weeks": clinical_weeks,
        "development_stage": dev_stage,
        "data_caveat": data_caveat,
        "ri_notes": ri_notes,
        "reviewed_by": reviewer,
        "reviewed_at": reviewed_at,
    }


def _walk_comparables(case_id: str, hints: dict[str, Any]) -> list[dict[str, str]]:
    existing = hints.get("precedents") or []
    print("\n--- Comparables (3 recommended) ---")
    count = int(_prompt("How many comparables", str(max(3, len(existing))) if existing else "3") or "3")
    rows: list[dict[str, str]] = []
    for rank in range(1, count + 1):
        print(f"\nComparable #{rank}")
        seed = existing[rank - 1] if rank - 1 < len(existing) else {}
        name = _prompt("precedent_name", seed.get("precedent_name", ""), required=True)
        url = _prompt("precedent_url", seed.get("precedent_url", ""))
        stage = _prompt("precedent_stage", seed.get("precedent_stage", "commercial"))
        vstatus = _prompt_choice(
            "validation_status",
            ["suggested", "estimated", "verified"],
            seed.get("validation_status", "suggested"),
        )
        anchor = _prompt("value_anchor_usd", seed.get("value_anchor_usd", ""))
        anchor_type = _prompt("value_anchor_type", seed.get("value_anchor_type", ""))
        source_url = _prompt("value_source_url (required if verified)", seed.get("value_source_url", ""))
        if vstatus == "verified" and not source_url:
            print("  ERROR: verified comps need value_source_url")
            source_url = _prompt("value_source_url", required=True)
        rows.append(
            {
                "case_id": case_id,
                "precedent_rank": str(rank),
                "precedent_type": _prompt("precedent_type", seed.get("precedent_type", "startup")),
                "precedent_name": name,
                "precedent_stage": stage,
                "precedent_notes": _prompt("precedent_notes", seed.get("precedent_notes", "")),
                "precedent_url": url,
                "inferred_development": _prompt(
                    "inferred_development", seed.get("inferred_development", "")
                ),
                "inferred_financing": _prompt("inferred_financing", seed.get("inferred_financing", "")),
                "inferred_team": _prompt("inferred_team", seed.get("inferred_team", "")),
                "total_raised_usd_est": _prompt("total_raised_usd_est", seed.get("total_raised_usd_est", "")),
                "last_round_usd_est": _prompt("last_round_usd_est", seed.get("last_round_usd_est", "")),
                "value_anchor_usd": anchor,
                "value_anchor_type": anchor_type,
                "value_source_url": source_url,
                "financing_strategy": _prompt("financing_strategy", seed.get("financing_strategy", "")),
                "validation_status": vstatus,
                "confidence": _prompt("confidence", seed.get("confidence", "medium")),
                "source": "tier_a_interactive",
            }
        )
    return rows


def _walk_evidence(case_id: str, hints: dict[str, Any]) -> dict[str, str]:
    cat = hints.get("catalog") or {}
    existing = evidence_by_case().get(case_id, {})
    print("\n--- Evidence depth QC (evidence_overrides.csv) ---")
    pub_suggest = cat.get("biomcp_publication_count", existing.get("min_publication_count", "0"))
    print(f"  Suggested publication count from catalog/BioMCP: {pub_suggest}")
    depth = _prompt("evidence_depth_score_0_100", existing.get("evidence_depth_score_0_100", ""))
    grade = _prompt_choice("evidence_grade", ["A", "B", "C", "draft"], existing.get("evidence_grade", "draft"))
    review = _prompt_choice(
        "review_status",
        ["pending", "needs_work", "approved"],
        existing.get("review_status", "pending"),
    )
    canonical = _prompt(
        "canonical_evidence_status",
        existing.get("canonical_evidence_status", cat.get("biomcp_evidence_status", "pending")),
    )
    note = _prompt("reviewer_note", existing.get("reviewer_note", ""))
    return {
        "case_id": case_id,
        "evidence_depth_score_0_100": depth,
        "evidence_grade": grade,
        "review_status": review,
        "reviewer_note": note,
        "canonical_evidence_status": canonical,
        "min_publication_count": _prompt("min_publication_count", pub_suggest),
    }


def _upsert_catalog_tier_a(case_id: str, registry_row: dict[str, str]) -> None:
    if not CATALOG_PATH.exists():
        print(f"WARN: {CATALOG_PATH} missing; skip catalog promotion")
        return
    rows = read_csv(CATALOG_PATH)
    by_id = {r["case_id"]: r for r in rows}
    row = by_id.get(case_id)
    if not row:
        print(f"WARN: {case_id} not in catalog enrichment; add row manually with catalog_tier=A")
        return
    row["catalog_tier"] = "A"
    row["catalog_include"] = "true"
    row.update(
        {
            k: v
            for k, v in registry_row.items()
            if k
            in {
                "title_clean",
                "company",
                "opportunity_type",
                "indication",
                "primary_lens_id",
                "physician_lead_name",
                "physician_lead_npi",
                "capital_gap_usd",
                "budget_ceiling_usd",
                "clinical_duration_weeks",
                "development_stage",
                "data_caveat",
                "ri_notes",
            }
            and v
        }
    )
    patch = apply_tier_a_to_catalog_row(row)
    row.update(patch)
    import csv

    fieldnames = list(rows[0].keys()) if rows else list(row.keys())
    for key in row:
        if key not in fieldnames:
            fieldnames.append(key)
    with CATALOG_PATH.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=fieldnames, extrasaction="ignore")
        writer.writeheader()
        writer.writerows(rows)
    print(f"Updated {CATALOG_PATH} for {case_id} (catalog_tier=A)")


def _merge_rows(
    existing: list[dict[str, str]],
    new_rows: list[dict[str, str]],
    *,
    key: str,
) -> list[dict[str, str]]:
    by_key = {r[key]: r for r in existing if r.get(key)}
    for row in new_rows:
        by_key[row[key]] = row
    return list(by_key.values())


def run_interactive(
    *,
    case_id: str,
    from_case: str | None = None,
    promote_catalog: bool = True,
    dry_run: bool = False,
) -> int:
    ensure_tier_a_dir()
    case_id = re.sub(r"[^a-z0-9_]+", "_", case_id.strip().lower()).strip("_")
    if not case_id:
        print("ERROR: case_id required")
        return 1

    source_id = from_case or case_id
    hints = _load_suggestions(source_id)
    if not hints["catalog"] and not hints["opportunity"]:
        print(f"WARN: no catalog/opportunity row for {source_id}; continuing with blanks")

    print(f"\n=== Tier A onboarding: {case_id} ===")
    if from_case and from_case != case_id:
        print(f"(suggestions from {from_case})")

    registry_row = _suggest_registry(case_id, hints)
    comp_rows = _walk_comparables(case_id, hints)
    evidence_row = _walk_evidence(case_id, hints)

    print("\n--- Quality check (in-memory) ---")
    reg_all = _merge_rows(load_registry(), [registry_row], key="case_id")
    comp_all = [r for r in load_comparables() if r.get("case_id") != case_id] + comp_rows
    ev_all = _merge_rows(load_evidence_overrides(), [evidence_row], key="case_id")

    # Temporarily validate by writing to memory - use validate on merged sets
    from pipeline.tier_a import io as tier_io

    orig_reg = tier_io.REGISTRY_CSV
    if dry_run:
        print("DRY RUN: no files written")
        for label, row in [
            ("registry", registry_row),
            ("evidence", evidence_row),
        ]:
            print(f"\n{label}:")
            for k, v in row.items():
                if v:
                    print(f"  {k}: {v}")
        print(f"\ncomparables: {len(comp_rows)} rows")
        return 0

    write_registry(reg_all)
    write_comparables(comp_all)
    write_evidence_overrides(ev_all)

    report = validate_sources()
    for warning in report.warnings:
        print(f"WARN: {warning}")
    for error in report.errors:
        print(f"ERROR: {error}")

    if promote_catalog and registry_row.get("status") == "active":
        _upsert_catalog_tier_a(case_id, registry_row)

    if not report.ok:
        print("\nFix errors above, then run: npm run tier:a:validate")
        return 1

    print("\nSaved tier_a sources. Next:")
    print("  npm run tier:a:build")
    print("  npm run build:ri:combined")
    return 0


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--case-id", required=True, help="Tier A case_id to create or update")
    parser.add_argument(
        "--from-case",
        help="Pull suggestions from another case_id (e.g. auto_* before promotion)",
    )
    parser.add_argument("--dry-run", action="store_true", help="Print prompts result without writing")
    parser.add_argument("--no-promote-catalog", action="store_true")
    args = parser.parse_args()
    raise SystemExit(
        run_interactive(
            case_id=args.case_id,
            from_case=args.from_case,
            promote_catalog=not args.no_promote_catalog,
            dry_run=args.dry_run,
        )
    )


if __name__ == "__main__":
    main()
