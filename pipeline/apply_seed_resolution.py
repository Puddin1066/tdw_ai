"""Apply curated seed Tier A resolution to normalized CSVs and enrichment catalog."""

from __future__ import annotations

import csv
from pathlib import Path

from pipeline.ri_case_merges import CASE_MERGE_ALIASES, MERGE_EXCLUSION_NOTE, apply_case_merges, canonical_case_id
from pipeline.types import repo_root

DATA = repo_root() / "data" / "ri"
ASSETS = DATA / "ri_ip_assets.csv"
OPPS = DATA / "ri_opportunities.csv"
ENRICH = DATA / "ri_opportunities_catalog_enrichment.csv"
MATCHES = DATA / "ri_physician_match_suggestions.csv"

# Secondary patents to attach after normalize (distinct invention families).
SECONDARY_IP: dict[str, str] = {
    "nanode_ri": "104-876-606-446-902",
    "phlip_therapeutics_ri": "129-685-709-438-265",
}

SEED_ENRICHMENT: dict[str, dict[str, str]] = {
    "theromics_ri": {
        "title_clean": "Theromics — albumin thermal accelerant (HeatSYNC)",
        "indication": "thermal tumor ablation (liver/kidney RF and microwave)",
        "company": "Theromics Inc",
        "opportunity_type": "platform",
        "primary_lens_id": "185-839-533-093-266",
        "primary_display_key": "US 11076916 B2",
        "primary_patent_title": "Thermal accelerant compositions and methods of use",
        "ip_lens_ids": "185-839-533-093-266|115-872-208-456-081",
        "ip_asset_count": "2",
        "physician_lead_npi": "npi_1487681342",
        "physician_lead_name": "BLAISE BAXTER",
        "data_caveat": "",
        "ri_notes": "Park Lab spinout; albumin-based gel for RF/microwave ablation (HeatSYNC).",
    },
    "monaghan_sepsis_diagnostic_ri": {
        "title_clean": "Monaghan — deep RNA host-response diagnostic",
        "indication": "early sepsis and critical illness host-response RNA diagnostics",
        "company": "Monaghan Lab / RI Hospital",
        "primary_lens_id": "085-655-703-999-246",
        "primary_display_key": "US 2025/0034234 A1",
        "primary_patent_title": "PREDICTING COVID-19 ANTIBODIES AMONG SURVIVORS WITH DEEP RNA SEQUENCING",
        "ip_lens_ids": "085-655-703-999-246",
        "ip_asset_count": "1",
        "physician_lead_npi": "npi_1871795906",
        "physician_lead_name": "SEAN MONAGHAN",
        "data_caveat": "Platform anchored on Monaghan deep RNA-seq patent; sepsis-specific claims may be grant/publication-led.",
        "ri_notes": "Monaghan Lab; NIH-funded deep RNA platform (Inflammatix-like). No spinout yet.",
    },
    "cbt_pain_digital_platform_ri": {
        "title_clean": "Petzchner — SOMA Pain Management (digital CBT)",
        "indication": "chronic pain — digital CBT via mobile app",
        "company": "SOMA Pain Management (Federika Petzchner / Brown)",
        "primary_lens_id": "",
        "primary_display_key": "",
        "primary_patent_title": "",
        "ip_lens_ids": "",
        "ip_asset_count": "0",
        "physician_lead_npi": "npi_1013301381",
        "physician_lead_name": "LAERT RUSHA",
        "data_caveat": "No RI patent in Lens export; proxy = SOMA Pain Management iOS app + Petzchner publications.",
        "ri_notes": "Digital therapeutic; App Store SOMA Pain Management beta.",
    },
    "nanode_ri": {
        "title_clean": "NanoDe — Nanopieces / Janus nucleotide delivery",
        "indication": "Janus nucleotide and Nanopieces nucleic acid delivery",
        "company": "NanoDe Therapeutics",
        "opportunity_type": "platform",
        "primary_lens_id": "008-231-790-422-477",
        "primary_display_key": "US 2024/0156853 A1",
        "primary_patent_title": "IN VITRO AND IN VIVO INTRACELLULAR DELIVERY OF SIRNA VIA SELF-ASSEMBLED NANOPIECES",
        "ip_lens_ids": "008-231-790-422-477|104-876-606-446-902",
        "ip_asset_count": "2",
        "physician_lead_npi": "npi_1003871336",
        "physician_lead_name": "TODD ROBERTS",
        "data_caveat": "",
        "ri_notes": "Chen Qian Nanopieces primary; nanotube carrier secondary. Dana Ono historical CEO.",
    },
    "phlip_therapeutics_ri": {
        "title_clean": "pHLIP Inc — imaging and pH-targeted delivery",
        "indication": "tumor imaging and pH-targeted therapeutic delivery",
        "company": "pHLIP Inc",
        "opportunity_type": "platform",
        "primary_lens_id": "156-876-316-327-303",
        "primary_display_key": "US 12290575 B2",
        "primary_patent_title": "Fluorescent compound comprising a fluorophore conjugated to a pH-triggered polypeptide",
        "ip_lens_ids": "156-876-316-327-303|129-685-709-438-265",
        "ip_asset_count": "2",
        "physician_lead_npi": "npi_1487681342",
        "physician_lead_name": "BLAISE BAXTER",
        "data_caveat": "Some therapeutic delivery rights may be licensed separately (e.g. Cybrexa).",
        "ri_notes": "pHLIP Inc (phlipinc.com); Reshetnyak/Engelman Yale-URI IP.",
    },
    "prothera_iaip_ri": {
        "catalog_tier": "B",
        "catalog_include": "true",
        "title_clean": "ProThera — IAIP biologics for sepsis",
        "program_family": "prothera_iaip",
        "indication": "early sepsis and critical illness — IAIP biologic therapeutic",
        "company": "ProThera Biologics Inc",
        "opportunity_type": "therapeutic",
        "primary_lens_id": "041-853-574-697-591",
        "primary_display_key": "US 2026/0130975 A1",
        "primary_patent_title": "INTER-ALPHA INHIBITOR PROTEINS AND METHODS OF USE THEREOF",
        "ip_lens_ids": "041-853-574-697-591|161-049-569-910-996|112-360-390-080-405",
        "ip_asset_count": "3",
        "physician_lead_npi": "",
        "physician_lead_name": "TBD",
        "data_caveat": "Merged ProThera US/DK/BR family from supplemental Lens export.",
        "ri_notes": (
            "Yow-Pin Lim / ProThera. Complementary to monaghan_sepsis_diagnostic_ri "
            "(host RNA dx) — distinct IAIP biologic MOA."
        ),
    },
}

# Tier B / promotion drafts (supplemental patents-2 curation).
PROMOTION_ENRICHMENT: dict[str, dict[str, str]] = {
    "auto_rhode_island_activity_brain_detecting_pain_using": {
        "catalog_tier": "B",
        "catalog_include": "true",
        "title_clean": "Saab — brain/spinal pain neurophysiology",
        "program_family": "saab_pain_neuro",
        "indication": "brain- and spinal-cord–guided pain detection and neuromodulation",
        "company": "Rhode Island Hospital",
        "opportunity_type": "platform",
        "primary_lens_id": "066-078-851-468-459",
        "primary_display_key": "US 11064940 B2",
        "primary_patent_title": "Methods for detecting and treating pain using brain activity",
        "development_stage": "validation",
        "required_specialties": "pain medicine|neurology|physical medicine and rehabilitation",
        "clinical_tags": "chronic_pain|pain_medicine|neurology|medical_device",
        "target_timeline_weeks": "20",
        "budget_ceiling_usd": "400000",
        "capital_gap_usd": "1200000",
        "enrichment_status": "promotion_draft",
        "ri_notes": (
            "Merged Saab spinal oscillation + pain management families. "
            "Pair with Tier A seed cbt_pain_digital_platform_ri (DTx) for full pain stack."
        ),
    },
    "auto_rhode_island_biomarker_brugada_circulating_syndrome": {
        "catalog_tier": "B",
        "catalog_include": "true",
        "title_clean": "Brugada syndrome circulating biomarker (MESPl)",
        "program_family": "brugada_dx",
        "indication": "Brugada syndrome risk stratification from blood MESPl",
        "company": "Rhode Island Hospital",
        "opportunity_type": "diagnostic",
        "primary_lens_id": "153-735-440-075-184",
        "primary_display_key": "WO 2017/031342 A1",
        "primary_patent_title": "CIRCULATING BIOMARKER FOR BRUGADA SYNDROME",
        "development_stage": "validation",
        "required_specialties": "cardiology|electrophysiology|emergency medicine",
        "clinical_tags": "cardiology|diagnostic|electrophysiology",
        "enrichment_status": "promotion_draft",
        "ri_notes": "Dudley lab; MESPl protein/transcript biomarker. Confirm cardiology PI.",
    },
    "auto_rhode_island_conductivity_dose_fields_hydrogel_impacts_skin_t": {
        "catalog_tier": "B",
        "catalog_include": "true",
        "title_clean": "TTF hydrogel — skin dose from tumor treating fields",
        "program_family": "ttf_neuro_onc",
        "indication": "optimize Optune/TTF delivery via hydrogel conductivity",
        "company": "Rhode Island Hospital",
        "opportunity_type": "medical_device",
        "primary_lens_id": "166-122-517-000-683",
        "primary_display_key": "US 2025/0170395 A1",
        "primary_patent_title": "HYDROGEL CONDUCTIVITY IMPACTS SKIN DOSE FROM TUMOR TREATING FIELDS",
        "development_stage": "validation",
        "required_specialties": "neurology|medical oncology|radiation oncology",
        "clinical_tags": "neuro_oncology|medical_device|brain_tumor",
        "enrichment_status": "promotion_draft",
        "ri_notes": "Wong/Lok; accessory to commercial TTF (Optune). IL 315287 + US family.",
    },
    "auto_neurotech_analyte_apparatuses_diffusive_implantable_packag": {
        "catalog_tier": "B",
        "catalog_include": "true",
        "title_clean": "Neurotech — BAO implant packaging",
        "program_family": "neurotech_ect",
        "indication": "packaging and logistics for encapsulated-cell implants",
        "company": "Neurotech USA Inc",
        "opportunity_type": "medical_device",
        "primary_lens_id": "195-972-829-878-535",
        "primary_display_key": "US 12629242 B2",
        "primary_patent_title": "System, apparatuses, devices, and methods for packaging an analyte diffusive implantable device",
        "enrichment_status": "promotion_draft",
        "ri_notes": "2026 grant; pairs with ophthalmic ECT program (same assignee).",
    },
    "auto_neurotech_cell_disorders_encapsulated_ophthalmic_therapy": {
        "catalog_tier": "B",
        "catalog_include": "true",
        "title_clean": "Neurotech — encapsulated cell therapy for ophthalmic disease",
        "program_family": "neurotech_ect",
        "indication": "RP, dry AMD/GA, glaucoma via encapsulated cell therapy",
        "company": "Neurotech USA Inc",
        "opportunity_type": "platform",
        "primary_lens_id": "132-021-956-305-052",
        "primary_display_key": "WO 2016/191645 A1",
        "primary_patent_title": "USE OF ENCAPSULATED CELL THERAPY FOR TREATMENT OF OPHTHALMIC DISORDERS",
        "enrichment_status": "promotion_draft",
        "ri_notes": "Warwick RI assignee; link to auto_neurotech packaging case for manufacturing story.",
    },
    "auto_univ_brown_chiplet_intranet_large_recordiing_scale_stimulat": {
        "catalog_tier": "B",
        "catalog_include": "true",
        "title_clean": "Brown — chiplet wireless neural intranet",
        "program_family": "brown_neurotech",
        "indication": "scalable wireless neural recording/stimulation (1000+ sites)",
        "company": "Brown University",
        "opportunity_type": "medical_device",
        "primary_lens_id": "062-471-784-728-462",
        "primary_display_key": "WO 2016/187254 A1",
        "primary_patent_title": "CHIPLET BASED WIRELESS INTRANET FOR VERY LARGE SCALE RECORDIING AND STIMULATION",
        "enrichment_status": "promotion_draft",
        "ri_notes": (
            "Nurmikko ecosystem; extension of Tier A auto_brown_university_implantable_neural_wireless "
            "(distinct scalable architecture)."
        ),
    },
    "auto_rhode_island_brain_enhancer_primary_rnas_targeting_tumors": {
        "catalog_tier": "B",
        "catalog_include": "true",
        "title_clean": "Enhancer RNA targeting for primary brain tumors",
        "program_family": "brain_tumor_rna",
        "indication": "primary brain tumors — enhancer RNA therapeutics",
        "company": "Brown / Rhode Island Hospital",
        "opportunity_type": "platform",
        "primary_lens_id": "007-072-329-032-532",
        "primary_display_key": "US 12060557 B2",
        "primary_patent_title": "Targeting enhancer RNAs for the treatment of primary brain tumors",
        "enrichment_status": "promotion_draft",
        "ri_notes": "Tapinos/Akobundu; merged auto_univ_brown duplicate case.",
    },
    "auto_contech_medical_medical_securing": {
        "catalog_tier": "B",
        "catalog_include": "true",
        "title_clean": "Contech — medical device securing clip",
        "program_family": "med_device_accessory",
        "indication": "secure medical devices and tubing in clinical workflows",
        "company": "Contech Medical, Inc.",
        "opportunity_type": "medical_device",
        "primary_lens_id": "007-074-526-025-963",
        "primary_display_key": "US 2026/0137476 A1",
        "primary_patent_title": "SYSTEMS AND METHODS FOR SECURING MEDICAL DEVICES",
        "enrichment_status": "promotion_draft",
        "ri_notes": "2026 US filing; RI-area med-device manufacturer — no overlap with clinical Tier A programs.",
    },
    "auto_bryant_university_antibacterial_compounds_making_same_using": {
        "catalog_tier": "B",
        "catalog_include": "true",
        "title_clean": "Brown–Bryant antibacterial diamides",
        "program_family": "brown_antibacterial",
        "indication": "antibacterial small molecules (diamides)",
        "company": "Brown University / Bryant University",
        "opportunity_type": "therapeutic",
        "primary_lens_id": "059-233-465-923-592",
        "primary_display_key": "US 10829440 B2",
        "primary_patent_title": "Antibacterial compounds and methods of making and using same",
        "enrichment_status": "promotion_draft",
        "ri_notes": "Basu lab; merged WO auto_univ_brown duplicate. Thematic neighbor: Tier A auranofin catheter.",
    },
}

DEDUPE_CASE = "auto_rhode_island_antibodies_covid_deep_predicting_sequencing_surv"

PROTHERA_SECONDARY_LENS = ("161-049-569-910-996", "112-360-390-080-405")

NANODE_LEAD = ("npi_1003871336", "TODD ROBERTS", "MEDICAL ONCOLOGY", "PROSPECT CHARTERCARE RWMC, LLC")


def _read_csv(path: Path) -> tuple[list[str], list[dict[str, str]]]:
    with path.open(newline="", encoding="utf-8") as f:
        reader = csv.DictReader(f)
        rows = list(reader)
        return list(reader.fieldnames or []), rows


def _write_csv(path: Path, fieldnames: list[str], rows: list[dict[str, str]]) -> None:
    with path.open("w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames, extrasaction="ignore")
        writer.writeheader()
        writer.writerows(rows)


def _load_patent_by_lens(lens_id: str) -> dict[str, str] | None:
    for row in csv.DictReader(ASSETS.open(encoding="utf-8")):
        if row.get("lens_id") == lens_id:
            return row
    # Search all assets in file (may be on another case_id before reassign)
    for row in csv.DictReader(open(DATA / "ri_ip_assets.csv", encoding="utf-8")):
        if row.get("lens_id") == lens_id:
            return dict(row)
    return None


def _lens_ids_from_assets(case_id: str) -> list[str]:
    lens_ids: list[str] = []
    for row in csv.DictReader(ASSETS.open(encoding="utf-8")):
        if row.get("case_id") == case_id:
            lid = (row.get("lens_id") or "").strip()
            if lid and lid not in lens_ids:
                lens_ids.append(lid)
    return lens_ids


def _enrichment_fields_for(case_id: str) -> dict[str, str]:
    merged: dict[str, str] = {}
    merged.update(PROMOTION_ENRICHMENT.get(case_id, {}))
    merged.update(SEED_ENRICHMENT.get(case_id, {}))
    lens_ids = _lens_ids_from_assets(case_id)
    if lens_ids:
        merged.setdefault("ip_lens_ids", "|".join(lens_ids))
        merged["ip_asset_count"] = str(len(lens_ids))
        merged.setdefault("primary_lens_id", lens_ids[0])
    return merged


def patch_normalized_case_merges() -> None:
    """Collapse alias case_ids in opportunities + IP assets (idempotent)."""
    opp_fields, opps = _read_csv(OPPS)
    asset_fields, assets = _read_csv(ASSETS)
    assets, opps = apply_case_merges(assets, opps)
    _write_csv(ASSETS, asset_fields, assets)
    _write_csv(OPPS, opp_fields, opps)


def patch_ip_assets() -> None:
    fieldnames, rows = _read_csv(ASSETS)
    by_case: dict[str, list[dict[str, str]]] = {}
    for row in rows:
        by_case.setdefault(row["case_id"], []).append(row)

    # Drop CBT opioid assets
    by_case["cbt_pain_digital_platform_ri"] = []

    for case_id in ("prothera_iaip_ri",):
        rows_for_case = by_case.get(case_id, [])
        existing_lens = {r["lens_id"] for r in rows_for_case}
        for secondary_lens in PROTHERA_SECONDARY_LENS:
            if secondary_lens in existing_lens:
                continue
            template = _load_patent_by_lens(secondary_lens)
            if not template:
                continue
            template = dict(template)
            template["case_id"] = case_id
            template["ri_relevance_reason"] = "seed_resolution_secondary_patent"
            rows_for_case.append(template)
        by_case[case_id] = rows_for_case[:6]

    for case_id, secondary_lens in SECONDARY_IP.items():
        primary_rows = by_case.get(case_id, [])
        existing_lens = {r["lens_id"] for r in primary_rows}
        if secondary_lens in existing_lens:
            continue
        template = _load_patent_by_lens(secondary_lens)
        if not template:
            continue
        template = dict(template)
        template["case_id"] = case_id
        template["ri_relevance_reason"] = "seed_resolution_secondary_patent"
        primary_rows.append(template)
        by_case[case_id] = primary_rows[:2]

    out: list[dict[str, str]] = []
    for case_id in sorted(by_case.keys()):
        out.extend(by_case[case_id])

    _write_csv(ASSETS, fieldnames, out)


def patch_opportunities() -> None:
    fieldnames, rows = _read_csv(OPPS)
    for row in rows:
        cid = row["case_id"]
        patch = _enrichment_fields_for(cid)
        if not patch:
            continue
        if patch.get("indication"):
            row["indication"] = patch["indication"]
        if patch.get("company"):
            row["company"] = patch["company"]
        if patch.get("opportunity_type"):
            row["opportunity_type"] = patch["opportunity_type"]
        if patch.get("primary_lens_id"):
            row["ri_ip_source"] = f"lens:{patch['primary_lens_id']}"
        elif cid == "cbt_pain_digital_platform_ri":
            row["ri_ip_source"] = ""
        if patch.get("ri_notes"):
            row["ri_notes"] = patch["ri_notes"]
        if patch.get("physician_lead_name"):
            row["ri_physician_lead"] = patch["physician_lead_name"]
        if cid == "cbt_pain_digital_platform_ri":
            row["llm_label_method"] = "curated_program_without_patent_anchor"
    _write_csv(OPPS, fieldnames, rows)


def _opp_row(case_id: str) -> dict[str, str] | None:
    for row in csv.DictReader(OPPS.open(encoding="utf-8")):
        if row.get("case_id") == case_id:
            return dict(row)
    return None


def patch_enrichment() -> None:
    fieldnames, rows = _read_csv(ENRICH)
    by_id = {row["case_id"]: row for row in rows}

    promote_ids = set(PROMOTION_ENRICHMENT) | set(SEED_ENRICHMENT)
    for case_id in sorted(promote_ids):
        if case_id in by_id:
            row = by_id[case_id]
        else:
            row = {f: "" for f in fieldnames}
            row["case_id"] = case_id
            opp = _opp_row(case_id)
            if opp:
                row["display_name"] = opp.get("display_name", case_id)
                row["opportunity_type"] = opp.get("opportunity_type", "platform")
                row["indication"] = opp.get("indication", "")
            by_id[case_id] = row
            rows.append(row)

    for row in rows:
        cid = row["case_id"]
        if cid == DEDUPE_CASE:
            row["catalog_tier"] = "B"
            row["catalog_include"] = "false"
            row["enrichment_status"] = "excluded_duplicate_of_monaghan_seed"
            row["ri_notes"] = (
                "Merged into monaghan_sepsis_diagnostic_ri (same Monaghan deep RNA platform)."
            )
        if cid in CASE_MERGE_ALIASES:
            target = canonical_case_id(cid)
            row["catalog_tier"] = "B"
            row["catalog_include"] = "false"
            row["enrichment_status"] = "excluded_case_merge_alias"
            row["ri_notes"] = f"{MERGE_EXCLUSION_NOTE} Canonical: `{target}`."
        patch = _enrichment_fields_for(cid)
        if patch:
            if cid == "prothera_iaip_ri" and "catalog_tier" not in patch:
                row.setdefault("catalog_tier", "B")
                row.setdefault("catalog_include", "true")
            row.update({k: v for k, v in patch.items() if k in fieldnames})
            if patch.get("physician_lead_name") and "ri_physician_lead" in fieldnames:
                row["ri_physician_lead"] = patch["physician_lead_name"]

    _write_csv(ENRICH, fieldnames, rows)


def patch_physician_matches() -> None:
    if not MATCHES.exists():
        return
    fieldnames, rows = _read_csv(MATCHES)
    out = [r for r in rows if r.get("case_id") != "nanode_ri"]
    npi, name, spec, inst = NANODE_LEAD
    out.append(
        {
            "case_id": "nanode_ri",
            "title_clean": "NanoDe — Nanopieces / Janus nucleotide delivery",
            "catalog_include": "true",
            "rank": "1",
            "physician_id": npi,
            "name": name,
            "specialty": spec,
            "institution": inst,
            "match_score": "53",
            "overlap_tags": "nucleic_acid_delivery|medical_oncology",
        }
    )
    for rank, (snpi, sname, sspec, sinst) in enumerate(
        [
            ("npi_1336596774", "KATHRYN DECARLI", "MEDICAL ONCOLOGY", "RHODE ISLAND HOSPITAL"),
            ("npi_1194249565", "MOHAMMED JALOUDI", "MEDICAL ONCOLOGY", "AFFINITY PHYSICIANS LLC."),
            ("npi_1790977650", "KHALDOUN ALMHANNA", "MEDICAL ONCOLOGY", "RHODE ISLAND HOSPITAL"),
        ],
        start=2,
    ):
        out.append(
            {
                "case_id": "nanode_ri",
                "title_clean": "NanoDe — Nanopieces / Janus nucleotide delivery",
                "catalog_include": "true",
                "rank": str(rank),
                "physician_id": snpi,
                "name": sname,
                "specialty": sspec,
                "institution": sinst,
                "match_score": "53",
                "overlap_tags": "medical_oncology|nucleic_acid_delivery",
            }
        )
    _write_csv(MATCHES, fieldnames, out)


def main() -> None:
    patch_normalized_case_merges()
    patch_ip_assets()
    patch_opportunities()
    patch_enrichment()
    patch_physician_matches()
    print("Applied case merges, seed resolution, and promotion enrichment patches.")


if __name__ == "__main__":
    main()
