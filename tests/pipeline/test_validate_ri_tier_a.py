from __future__ import annotations

import csv
import json
from pathlib import Path

from pipeline.validate_ri_tier_a import EXPECTED_TIER_A_COUNT, validate


def _write_csv(path: Path, fieldnames: list[str], rows: list[dict[str, str]]) -> None:
    with path.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=fieldnames, extrasaction="ignore")
        writer.writeheader()
        writer.writerows(rows)


def test_validate_passes_on_repo_tier_a(tmp_path: Path) -> None:
    root = Path(__file__).resolve().parents[2]
    report = validate(
        enrich_path=root / "data" / "ri" / "ri_opportunities_catalog_enrichment.csv",
        opps_path=root / "data" / "ri" / "ri_opportunities.csv",
        ip_path=root / "data" / "ri" / "ri_ip_assets.csv",
        combined_path=root / "data" / "ri" / "ri_opportunities_combined.json",
        profiles_dir=root / "web" / "public" / "data" / "opportunities" / "profiles",
        index_path=root / "web" / "public" / "data" / "opportunities" / "index.json",
        expect_web=True,
    )
    assert report.ok, report.errors


def test_validate_catches_seed_ip_drift(tmp_path: Path) -> None:
    enrich_fields = [
        "catalog_tier",
        "catalog_include",
        "case_id",
        "primary_lens_id",
        "ip_lens_ids",
        "ip_asset_count",
        "physician_lead_name",
        "ri_physician_lead",
    ]
    tier_a_rows = [
        {
            "catalog_tier": "A",
            "catalog_include": "true",
            "case_id": f"case_{i}",
            "primary_lens_id": f"lens-{i}",
            "ip_lens_ids": f"lens-{i}",
            "ip_asset_count": "1",
            "physician_lead_name": "",
            "ri_physician_lead": "",
        }
        for i in range(EXPECTED_TIER_A_COUNT)
    ]
    tier_a_rows[0] = {
        "catalog_tier": "A",
        "catalog_include": "true",
        "case_id": "monaghan_sepsis_diagnostic_ri",
        "primary_lens_id": "085-655-703-999-246",
        "ip_lens_ids": "063-586-913-488-802",
        "ip_asset_count": "1",
        "physician_lead_name": "SEAN MONAGHAN",
        "ri_physician_lead": "SEAN MONAGHAN",
    }
    enrich = tmp_path / "enrich.csv"
    _write_csv(enrich, enrich_fields, tier_a_rows)

    ip = tmp_path / "ip.csv"
    _write_csv(
        ip,
        ["case_id", "lens_id"],
        [
            {"case_id": "monaghan_sepsis_diagnostic_ri", "lens_id": "063-586-913-488-802"},
            *[
                {"case_id": f"case_{i}", "lens_id": f"lens-{i}"}
                for i in range(1, EXPECTED_TIER_A_COUNT)
            ],
        ],
    )

    opps = tmp_path / "opps.csv"
    _write_csv(
        opps,
        ["case_id", "ri_ip_source", "ri_physician_lead"],
        [
            {
                "case_id": "monaghan_sepsis_diagnostic_ri",
                "ri_ip_source": "lens:085-655-703-999-246",
                "ri_physician_lead": "SEAN MONAGHAN",
            },
            *[
                {"case_id": f"case_{i}", "ri_ip_source": f"lens:{i}", "ri_physician_lead": ""}
                for i in range(1, EXPECTED_TIER_A_COUNT)
            ],
        ],
    )

    combined = tmp_path / "combined.json"
    combined.write_text(
        json.dumps({"opportunities": [{"case_id": r["case_id"]} for r in tier_a_rows]}),
        encoding="utf-8",
    )

    report = validate(
        enrich_path=enrich,
        opps_path=opps,
        ip_path=ip,
        combined_path=combined,
        profiles_dir=tmp_path / "profiles",
        expect_web=False,
    )
    assert not report.ok
    assert any("forbidden patent" in e for e in report.errors)
