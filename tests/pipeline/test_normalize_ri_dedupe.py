from __future__ import annotations

from pipeline.normalize_ri_sources import (
    SEED_PATENT_EXTRA_TERMS,
    _cluster_patents_by_invention,
    _inventions_similar,
    _invention_token_set,
    normalize_patents,
)


def test_invention_cluster_collapses_title_variants() -> None:
    a = "Biomaterial for Articular Cartilage Maintenance and Treatment of Arthritis"
    b = "BIOMATERIAL FOR ARTICULAR CARTILAGE MAINTENANCE AND TREATMENT OF ARTHRITIS"
    assert _inventions_similar(_invention_token_set(a), _invention_token_set(b))
    patents = [
        {"Title": a, "Lens ID": "1"},
        {"Title": b, "Lens ID": "2"},
        {"Title": "Unrelated lumbar guide", "Lens ID": "3"},
    ]
    clusters = _cluster_patents_by_invention(patents)
    assert len(clusters) == 2
    assert len(clusters[0]) == 2


def test_normalize_patents_dedupes_same_invention_family() -> None:
    patents = [
        {
            "Lens ID": "111-111-111-111-111",
            "Title": "Vaccine for falciparum malaria",
            "Owners": "University of Rhode Island",
            "Applicants": "University of Rhode Island",
            "Inventors": "A Inventor",
            "Abstract": "malaria vaccine",
            "Publication Date": "2020-01-01",
            "Display Key": "US-1",
            "CPC Classifications": "",
            "IPCR Classifications": "",
        },
        {
            "Lens ID": "222-222-222-222-222",
            "Title": "VACCINE FOR FALCIPARUM MALARIA",
            "Owners": "University of Rhode Island",
            "Applicants": "University of Rhode Island",
            "Inventors": "B Inventor",
            "Abstract": "malaria vaccine variant",
            "Publication Date": "2019-01-01",
            "Display Key": "US-2",
            "CPC Classifications": "",
            "IPCR Classifications": "",
        },
        {
            "Lens ID": "333-333-333-333-333",
            "Title": "Lumbar facetectomy guide device",
            "Owners": "University of Rhode Island",
            "Applicants": "University of Rhode Island",
            "Inventors": "C Inventor",
            "Abstract": "spine guide",
            "Publication Date": "2021-01-01",
            "Display Key": "US-3",
            "CPC Classifications": "",
            "IPCR Classifications": "",
        },
    ]
    _, opportunities = normalize_patents(patents, seed_opportunities=[], max_assets_per_opportunity=2, max_generated_opportunities=0)
    auto = [row for row in opportunities if row["case_id"].startswith("auto_")]
    assert len(auto) == 2
    malaria = [row for row in auto if "malaria" in row["target"].lower()]
    assert len(malaria) == 1
    assert "2 of 2" in malaria[0]["ri_notes"]


def test_theromics_seed_absorbs_thermal_accelerant_patents() -> None:
    patents = [
        {
            "Lens ID": "115-872-208-456-081",
            "Title": "Thermal accelerant compositions and methods of use",
            "Owners": "Theromics Inc",
            "Applicants": "Theromics Inc",
            "Inventors": "Inventor One",
            "Abstract": "thermal ablation A61B18",
            "Publication Date": "2022-01-01",
            "Display Key": "US-T1",
            "CPC Classifications": "A61B18",
            "IPCR Classifications": "",
        },
        {
            "Lens ID": "185-839-533-093-266",
            "Title": "Thermal accelerant compositions and methods of use",
            "Owners": "Rhode Island Hospital",
            "Applicants": "Rhode Island Hospital",
            "Inventors": "Inventor Two",
            "Abstract": "thermal tumor ablation",
            "Publication Date": "2021-01-01",
            "Display Key": "US-T2",
            "CPC Classifications": "A61B18",
            "IPCR Classifications": "",
        },
    ]
    seeds = [
        {
            "case_id": "theromics_ri",
            "display_name": "Theromics",
            "target": "Theromics platform",
            "indication": "thermal tumor ablation",
            "opportunity_type": "platform",
            "company": "Theromics",
            "required_roles": "reviewer|advisor",
            "required_specialties": "oncology",
            "ri_notes": "seed",
        }
    ]
    assets, opportunities = normalize_patents(
        patents, seed_opportunities=seeds, max_assets_per_opportunity=2, max_generated_opportunities=0
    )
    assert len(opportunities) == 1
    assert opportunities[0]["case_id"] == "theromics_ri"
    assert len(assets) == 2
    assert "thermal" in SEED_PATENT_EXTRA_TERMS["theromics_ri"]
    auto = [row for row in opportunities if row["case_id"].startswith("auto_")]
    assert auto == []


def test_explicit_lens_id_pins_seed_opportunity() -> None:
    patents = [
        {
            "Lens ID": "156-876-316-327-303",
            "Title": "Fluorescent compound comprising a fluorophore conjugated to a pH-triggered polypeptide",
            "Owners": "University of Rhode Island",
            "Applicants": "University of Rhode Island",
            "Inventors": "Reshetnyak Yana K",
            "Abstract": "pHLIP fluorophore imaging",
            "Publication Date": "2025-05-06",
            "Display Key": "US 12290575 B2",
            "CPC Classifications": "A61K49",
            "IPCR Classifications": "",
        },
        {
            "Lens ID": "129-685-709-438-265",
            "Title": "Method of detecting diseased or damaged tissue with a pH-triggered polypeptide fluorophore composition",
            "Owners": "University of Rhode Island",
            "Applicants": "University of Rhode Island",
            "Inventors": "Reshetnyak Yana K",
            "Abstract": "pHLIP tissue detection",
            "Publication Date": "2023-08-29",
            "Display Key": "US 11738096 B2",
            "CPC Classifications": "A61K49",
            "IPCR Classifications": "",
        },
        {
            "Lens ID": "008-231-790-422-477",
            "Title": "IN VITRO AND IN VIVO INTRACELLULAR DELIVERY OF SIRNA VIA SELF-ASSEMBLED NANOPIECES",
            "Owners": "Brown University",
            "Applicants": "Brown University",
            "Inventors": "Chen Qian",
            "Abstract": "nanopieces nucleic acid delivery",
            "Publication Date": "2018-01-01",
            "Display Key": "US-1",
            "CPC Classifications": "",
            "IPCR Classifications": "",
        },
    ]
    seeds = [
        {
            "case_id": "phlip_therapeutics_ri",
            "display_name": "pHLIP Therapeutics",
            "target": "pHLIP fluorescent imaging platform",
            "indication": "tumor imaging",
            "opportunity_type": "diagnostic",
            "company": "PHLIP Therapeutics",
            "ri_ip_source": "lens:156-876-316-327-303",
            "required_roles": "reviewer|advisor",
            "required_specialties": "oncology",
            "ri_notes": "seed",
        }
    ]
    assets, opportunities = normalize_patents(
        patents, seed_opportunities=seeds, max_assets_per_opportunity=2, max_generated_opportunities=0
    )
    phlip = next(row for row in opportunities if row["case_id"] == "phlip_therapeutics_ri")
    assert phlip["ri_ip_source"] == "lens:156-876-316-327-303"
    phlip_assets = [asset for asset in assets if asset["case_id"] == "phlip_therapeutics_ri"]
    assert phlip_assets[0]["lens_id"] == "156-876-316-327-303"
