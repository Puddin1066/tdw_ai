"""Build ri_program_precedents.csv and link all comparables into catalog enrichment CSV."""

from __future__ import annotations

import csv
import statistics
from pathlib import Path

from pipeline.infer_ri_opportunity_package import apply_to_catalog_row
from pipeline.ri_precedent_catalog import CASE_PRECEDENT_GROUP, PRECEDENT_GROUPS, PHARMA_PREFIXES
from pipeline.ri_precedent_common import PRECEDENT_FIELDS, apply_value_anchor
from pipeline.ri_precedent_verified import VERIFIED_PATCHES

DATA = Path(__file__).resolve().parents[1] / "data" / "ri"
CATALOG_PATH = DATA / "ri_opportunities_catalog_enrichment.csv"
PRECEDENTS_PATH = DATA / "ri_program_precedents.csv"


def resolve_group(case_id: str, program_family: str) -> str:
    if case_id in CASE_PRECEDENT_GROUP:
        return CASE_PRECEDENT_GROUP[case_id]
    if any(case_id.startswith(p) for p in PHARMA_PREFIXES):
        return "ri_pharma_chemistry"
    pf = (program_family or "").strip()
    if pf in PRECEDENT_GROUPS:
        return pf
    if "theromics" in case_id or "ablat" in case_id:
        return "theromics_ablation"
    if "chi3l1" in case_id:
        return "chi3l1"
    if "besio" in case_id or "electrode" in case_id:
        return "besio_epilepsy"
    return "general_ri_spinout"


def _parse_usd(value: str | None) -> int | None:
    try:
        n = int(float((value or "").strip()))
        return n if n > 0 else None
    except ValueError:
        return None


def _merge_precedent(group_key: str, prec: dict[str, str]) -> dict[str, str]:
    row = {
        "validation_status": "suggested",
        "confidence": "medium",
        "source": "web_search_2026_03",
        "value_anchor_usd": "",
        "value_anchor_type": "",
        "value_source_url": "",
        **prec,
    }
    patch = VERIFIED_PATCHES.get((group_key, prec["precedent_name"]))
    if patch:
        row.update(patch)
    apply_value_anchor(row)
    return row


def build_precedent_rows(catalog_rows: list[dict[str, str]]) -> list[dict[str, str]]:
    out: list[dict[str, str]] = []
    for row in catalog_rows:
        if row.get("catalog_include", "true").lower() != "true":
            continue
        case_id = row["case_id"]
        group_key = resolve_group(case_id, row.get("program_family", ""))
        precedents = PRECEDENT_GROUPS.get(group_key, PRECEDENT_GROUPS["general_ri_spinout"])
        for rank, prec in enumerate(precedents, start=1):
            merged = _merge_precedent(group_key, prec)
            out.append(
                {
                    "case_id": case_id,
                    "title_clean": row.get("title_clean", ""),
                    "program_family": group_key,
                    "precedent_rank": str(rank),
                    **merged,
                }
            )
    return out


def _value_band_for_case(rows: list[dict[str, str]], case_id: str) -> dict[str, str]:
    items = [r for r in rows if r["case_id"] == case_id]
    anchors: list[int] = []
    verified = 0
    estimated = 0
    for r in items:
        status = (r.get("validation_status") or "").lower()
        if status == "verified":
            verified += 1
        elif status == "estimated":
            estimated += 1
        anchor = _parse_usd(r.get("value_anchor_usd"))
        if anchor and status in {"verified", "estimated"}:
            anchors.append(anchor)
    if not anchors:
        return {
            "value_band_min_usd": "",
            "value_band_max_usd": "",
            "value_band_median_usd": "",
            "value_anchor_verified_count": str(verified),
            "value_anchor_estimated_count": str(estimated),
            "value_verification_status": "no_verified_anchors",
        }
    return {
        "value_band_min_usd": str(min(anchors)),
        "value_band_max_usd": str(max(anchors)),
        "value_band_median_usd": str(int(statistics.median(anchors))),
        "value_anchor_verified_count": str(verified),
        "value_anchor_estimated_count": str(estimated),
        "value_verification_status": "verified" if verified else "estimated",
    }


def summarize_precedents(rows: list[dict[str, str]], case_id: str) -> dict[str, str]:
    items = [r for r in rows if r["case_id"] == case_id]
    items.sort(key=lambda r: int(r["precedent_rank"]))
    names = [r["precedent_name"] for r in items]
    urls = [r["precedent_url"] for r in items if r.get("precedent_url")]
    primary = items[0] if items else {}
    # Primary value anchor: first verified/estimated with dollars, else rank 1
    primary_anchor = primary
    for r in items:
        if (r.get("validation_status") in {"verified", "estimated"}) and _parse_usd(
            r.get("value_anchor_usd")
        ):
            primary_anchor = r
            break
    summary = {
        "precedent_count": str(len(items)),
        "precedent_names": " | ".join(names),
        "precedent_urls": " | ".join(urls),
        "primary_precedent_name": primary.get("precedent_name", ""),
        "primary_precedent_url": primary.get("precedent_url", ""),
        "precedent_inference_status": "multi_comparable_draft",
        "primary_value_anchor_usd": primary_anchor.get("value_anchor_usd", ""),
        "primary_value_anchor_type": primary_anchor.get("value_anchor_type", ""),
        "primary_value_source_url": primary_anchor.get("value_source_url", ""),
    }
    summary.update(_value_band_for_case(rows, case_id))
    return summary


def main() -> None:
    from pipeline.tier_a.build_from_sources import (
        apply_tier_a_to_catalog_row,
        apply_tier_a_to_precedents,
        tier_a_overwrite_template_gap,
    )

    catalog_rows = list(csv.DictReader(CATALOG_PATH.open(encoding="utf-8")))
    precedent_rows = build_precedent_rows(catalog_rows)
    precedent_rows = apply_tier_a_to_precedents(precedent_rows, catalog_rows)

    with PRECEDENTS_PATH.open("w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=PRECEDENT_FIELDS, extrasaction="ignore")
        writer.writeheader()
        writer.writerows(precedent_rows)

    extra_cols = [
        "precedent_count",
        "precedent_names",
        "precedent_urls",
        "primary_precedent_name",
        "primary_precedent_url",
        "precedent_inference_status",
        "primary_value_anchor_usd",
        "primary_value_anchor_type",
        "primary_value_source_url",
        "value_band_min_usd",
        "value_band_max_usd",
        "value_band_median_usd",
        "value_anchor_verified_count",
        "value_anchor_estimated_count",
        "value_verification_status",
    ]
    fieldnames = list(catalog_rows[0].keys())
    for col in extra_cols:
        if col not in fieldnames:
            fieldnames.append(col)

    inference_cols = [
        "investment_thesis",
        "comparable_market_narrative",
        "inferred_development_path",
        "inferred_financing_path",
        "inferred_next_milestone",
        "opportunity_enrichment_source",
    ]
    for col in inference_cols:
        if col not in fieldnames:
            fieldnames.append(col)

    for row in catalog_rows:
        if row.get("catalog_include", "true").lower() == "true":
            row.update(summarize_precedents(precedent_rows, row["case_id"]))
            median = _parse_usd(row.get("value_band_median_usd"))
            row.update(apply_tier_a_to_catalog_row(row, median_usd=median))
            apply_to_catalog_row(
                row,
                precedent_rows,
                overwrite_template_gap=tier_a_overwrite_template_gap(row["case_id"]),
            )
        else:
            for col in extra_cols + inference_cols:
                row[col] = ""

    with CATALOG_PATH.open("w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames, extrasaction="ignore")
        writer.writeheader()
        writer.writerows(catalog_rows)

    active = sum(1 for r in catalog_rows if r.get("catalog_include") == "true")
    with_anchors = sum(
        1
        for r in catalog_rows
        if r.get("catalog_include") == "true" and r.get("value_band_min_usd")
    )
    print(f"Wrote {len(precedent_rows)} precedent rows ({active} programs) -> {PRECEDENTS_PATH}")
    print(f"Programs with value band: {with_anchors}/{active}")
    print(f"Updated catalog summaries -> {CATALOG_PATH}")


if __name__ == "__main__":
    main()
