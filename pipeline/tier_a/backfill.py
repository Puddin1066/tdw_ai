"""Backfill tier_a/*.csv from current catalog + precedents (one-time or refresh)."""

from __future__ import annotations

import argparse
from datetime import date

from pipeline.tier_a import paths as tier_a_paths
from pipeline.tier_a.io import (
    ensure_tier_a_dir,
    read_csv,
    write_comparables,
    write_evidence_overrides,
    write_registry,
)


def _bool(value: str | None) -> bool:
    return (value or "").strip().lower() in {"1", "true", "t", "yes", "y"}


def backfill(*, overwrite: bool = False) -> dict[str, int]:
    ensure_tier_a_dir()
    if not tier_a_paths.CATALOG_PATH.exists():
        raise FileNotFoundError(tier_a_paths.CATALOG_PATH)

    catalog = read_csv(tier_a_paths.CATALOG_PATH)
    precedents = (
        read_csv(tier_a_paths.PRECEDENTS_PATH) if tier_a_paths.PRECEDENTS_PATH.exists() else []
    )
    prec_by: dict[str, list[dict[str, str]]] = {}
    for row in precedents:
        prec_by.setdefault(row["case_id"], []).append(row)

    tier_rows = [
        r
        for r in catalog
        if (r.get("catalog_tier") or "").upper() == "A" and _bool(r.get("catalog_include", "true"))
    ]

    registry_out: list[dict[str, str]] = []
    comps_out: list[dict[str, str]] = []
    evidence_out: list[dict[str, str]] = []

    today = date.today().isoformat()
    for row in tier_rows:
        case_id = row["case_id"]
        promotion = "seed" if case_id.endswith("_ri") and not case_id.startswith("auto_") else "auto_promoted"
        registry_out.append(
            {
                "case_id": case_id,
                "title_clean": row.get("title_clean", ""),
                "program_family": row.get("program_family", ""),
                "company": row.get("company", "TBD"),
                "opportunity_type": row.get("opportunity_type", "platform"),
                "indication": row.get("indication", ""),
                "primary_lens_id": row.get("primary_lens_id", ""),
                "physician_lead_name": row.get("physician_lead_name", row.get("ri_physician_lead", "")),
                "physician_lead_npi": row.get("physician_lead_npi", ""),
                "status": "active",
                "promotion_source": promotion,
                "capital_gap_usd": row.get("capital_gap_usd", ""),
                "budget_ceiling_usd": row.get("budget_ceiling_usd", ""),
                "clinical_duration_weeks": row.get("clinical_duration_weeks", ""),
                "development_stage": row.get("development_stage", ""),
                "data_caveat": row.get("data_caveat", ""),
                "ri_notes": row.get("ri_notes", ""),
                "reviewed_by": "backfill",
                "reviewed_at": today,
            }
        )

        for prec in sorted(prec_by.get(case_id, []), key=lambda r: int(r.get("precedent_rank") or 99)):
            comps_out.append(
                {
                    "case_id": case_id,
                    "precedent_rank": prec.get("precedent_rank", ""),
                    "precedent_type": prec.get("precedent_type", ""),
                    "precedent_name": prec.get("precedent_name", ""),
                    "precedent_stage": prec.get("precedent_stage", ""),
                    "precedent_notes": prec.get("precedent_notes", ""),
                    "precedent_url": prec.get("precedent_url", ""),
                    "inferred_development": prec.get("inferred_development", ""),
                    "inferred_financing": prec.get("inferred_financing", ""),
                    "inferred_team": prec.get("inferred_team", ""),
                    "total_raised_usd_est": prec.get("total_raised_usd_est", ""),
                    "last_round_usd_est": prec.get("last_round_usd_est", ""),
                    "value_anchor_usd": prec.get("value_anchor_usd", ""),
                    "value_anchor_type": prec.get("value_anchor_type", ""),
                    "value_source_url": prec.get("value_source_url", ""),
                    "financing_strategy": prec.get("financing_strategy", ""),
                    "validation_status": prec.get("validation_status", "suggested"),
                    "confidence": prec.get("confidence", "medium"),
                    "source": prec.get("source", "backfill"),
                }
            )

        pub_count = (row.get("biomcp_publication_count") or "0").strip()
        ev_status = row.get("biomcp_evidence_status", "pending")
        try:
            pubs = int(pub_count)
        except ValueError:
            pubs = 0
        depth = min(100, max(0, pubs * 15)) if pubs else 0
        grade = "B" if pubs >= 2 else "draft"
        evidence_out.append(
            {
                "case_id": case_id,
                "evidence_depth_score_0_100": str(depth),
                "evidence_grade": grade,
                "review_status": "pending",
                "reviewer_note": "Backfilled from catalog; confirm after BioMCP refresh.",
                "canonical_evidence_status": ev_status,
                "min_publication_count": pub_count,
            }
        )

    write_registry(registry_out)
    write_comparables(comps_out)
    write_evidence_overrides(evidence_out)
    return {
        "registry": len(registry_out),
        "comparables": len(comps_out),
        "evidence": len(evidence_out),
    }


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--overwrite", action="store_true", help="Ignored; backfill always rewrites tier_a CSVs")
    args = parser.parse_args()
    counts = backfill(overwrite=args.overwrite)
    print(f"Backfilled tier_a sources: {counts}")


if __name__ == "__main__":
    main()
