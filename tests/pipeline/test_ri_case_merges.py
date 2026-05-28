from __future__ import annotations

from pipeline.ri_case_merges import CASE_MERGE_ALIASES, apply_case_merges


def test_apply_case_merges_collapses_prothera_aliases() -> None:
    assets = [
        {"case_id": "auto_prothera_biologics_alpha_inhibitor_inter_proteins_thereof", "lens_id": "041-853-574-697-591"},
        {"case_id": "auto_prothera_biologics_alpha_blod_fremstilling_inhibitorproteiner_inter", "lens_id": "161-049-569-910-996"},
    ]
    opportunities = [
        {"case_id": "auto_prothera_biologics_alpha_inhibitor_inter_proteins_thereof", "ri_notes": "us", "source_type": "lens_patent_csv", "ri_ip_source": "lens:041"},
        {
            "case_id": "prothera_iaip_ri",
            "ri_notes": "seed",
            "source_type": "ri_physicians_ip_seed",
            "ri_ip_source": "lens:041-853-574-697-591",
        },
        {"case_id": "auto_prothera_biologics_alfa_composi_inibidoras_inter_partir_prepara_pro", "ri_notes": "br", "source_type": "lens_patent_csv", "ri_ip_source": "lens:112"},
    ]
    merged_assets, merged_opps = apply_case_merges(assets, opportunities)
    assert all(row["case_id"] == "prothera_iaip_ri" for row in merged_assets)
    assert len(merged_assets) == 2
    assert len(merged_opps) == 1
    assert merged_opps[0]["case_id"] == "prothera_iaip_ri"
    assert "Merged alias" in merged_opps[0]["ri_notes"]
    assert len(CASE_MERGE_ALIASES) >= 6
