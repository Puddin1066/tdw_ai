"""Sync curated seed program fields from apply_seed_resolution into tier_a/registry.csv."""

from __future__ import annotations

import argparse

from pipeline.apply_seed_resolution import SEED_ENRICHMENT
from pipeline.tier_a.io import load_registry, write_registry

SEED_CASE_IDS = tuple(SEED_ENRICHMENT.keys())


def sync_seeds() -> int:
    rows = load_registry()
    by_id = {r["case_id"]: r for r in rows}
    updated = 0
    for case_id, patch in SEED_ENRICHMENT.items():
        if case_id not in by_id:
            continue
        row = by_id[case_id]
        mapping = {
            "title_clean": patch.get("title_clean", ""),
            "company": patch.get("company", ""),
            "opportunity_type": patch.get("opportunity_type", row.get("opportunity_type", "")),
            "indication": patch.get("indication", ""),
            "primary_lens_id": patch.get("primary_lens_id", ""),
            "physician_lead_name": patch.get("physician_lead_name", ""),
            "physician_lead_npi": patch.get("physician_lead_npi", ""),
            "data_caveat": patch.get("data_caveat", ""),
            "ri_notes": patch.get("ri_notes", ""),
            "promotion_source": "seed",
            "reviewed_by": "sync_seeds",
        }
        for key, value in mapping.items():
            if value and row.get(key) != value:
                row[key] = value
                updated += 1
    write_registry(list(by_id.values()))
    return updated


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.parse_args()
    n = sync_seeds()
    print(f"Synced seed fields into tier_a/registry.csv ({len(SEED_CASE_IDS)} programs, {n} cell updates).")


if __name__ == "__main__":
    main()
