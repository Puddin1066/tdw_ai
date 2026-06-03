"""Web-informed remediation pass for data/ri/ri_cases_enriched.csv.

Fixes systematic bootstrap errors: stale thesis text, npi_ prefixes in supporters,
irrelevant suggest_publication_* blobs (remediation no longer clears BioMCP suggest columns),
indications, auto-matched trial placeholders, ri_operating comp types, and selected
comparable evidence updates verified via public sources.
"""

from __future__ import annotations

import argparse
import re
from datetime import date
from pathlib import Path

from pipeline.brown_vivo_profiles import fill_brown_profile_url
from pipeline.ri_cases_enriched_io import (
    CASES_CSV,
    apply_finance_defaults,
    build_thesis,
    load_cases,
    write_cases,
)
from pipeline.ri_cases_enriched_schema import COMP_PREFIXES

GENERIC_INDICATION = "RI technology opportunity from patent corpus"

# Tier-A registry placeholders — not patent inventors; replaced via PHYSICIAN_FIXES or inventors.
PLACEHOLDER_LEADS = frozenset(
    {
        "EUGENIE ATALLAH",
        "TODD ROBERTS",
        "SHANTHI MOGALI",
        "HEINRICH ELINZANO",
        "BLAISE BAXTER",
        "BENJAMIN POLLOCK",
        "SETH CLARK",
        "GERARDO CARINO",
        "MAHER EL KHATIB",
        "LAERT RUSHA",
    }
)

# Curated physician / inventor alignment (sources: Brown VIVO, USPTO inventors, NPI registry).
PHYSICIAN_FIXES: dict[str, dict[str, str]] = {
    "auto_brown_university_drug_overdose": {
        "physician_lead_name": "CAROLINA HAASS-KOFFLER",
        "physician_lead_npi": "",
        "physician_lead_specialty": "Addiction medicine / translational pharmacology",
        "physician_lead_institution": "Brown University",
        "physician_lead_profile_url": "https://vivo.brown.edu/display/chaassko",
    },
    "auto_brown_university_anti_antibody_bispecific_chi3l1_reagents_relatin": {
        "physician_lead_name": "JACK A ELIAS",
        "physician_lead_npi": "",
        "physician_lead_specialty": "Pulmonary / critical care medicine",
        "physician_lead_institution": "Brown University",
        "physician_lead_profile_url": "https://vivo.brown.edu/display/jaelias",
    },
    "auto_brown_university_brain_chemotherapeutic_drug_enhancing_tumors_upt": {
        "physician_lead_name": "SEAN LAWLER",
        "physician_lead_npi": "",
        "physician_lead_specialty": "Neuro-oncology",
        "physician_lead_institution": "Brown University",
        "physician_lead_profile_url": "https://vivo.brown.edu/display/slawler",
    },
    "auto_brown_university_implantable_neural_wireless": {
        "physician_lead_name": "ARTO V NURMIKKO",
        "physician_lead_npi": "1003392689",
        "physician_lead_specialty": "Neuroengineering / neural interfaces",
        "physician_lead_institution": "Brown University School of Engineering",
        "physician_lead_profile_url": "https://vivo.brown.edu/display/anurmikk",
    },
    "auto_brown_university_cardiac_cell_collagen_engineered_tissue": {
        "physician_lead_name": "FRANK SELLKE",
        "physician_lead_npi": "1457304859",
        "physician_lead_specialty": "Thoracic and cardiac surgery",
        "physician_lead_institution": "Rhode Island Hospital / Brown University",
    },
    "auto_rhode_island_cardiotoxicity_human_model_vitro": {
        "physician_lead_name": "RUPA BALA",
        "physician_lead_npi": "1417983123",
        "physician_lead_specialty": "Cardiac electrophysiology",
        "physician_lead_institution": "Rhode Island Hospital",
    },
    "auto_brown_university_decellularized_extracellular_making_mammalian_ma": {
        "physician_lead_name": "FRANK SELLKE",
        "physician_lead_npi": "1457304859",
        "physician_lead_specialty": "Thoracic and cardiac surgery",
        "physician_lead_institution": "Rhode Island Hospital / Brown University",
    },
    "mindimmune_therapeutics_ri": {
        "physician_lead_name": "HEINRICH ELINZANO",
        "physician_lead_npi": "1063477032",
        "physician_lead_specialty": "Neurology / cognitive disorders",
        "physician_lead_institution": "Rhode Island Hospital",
        "physician_lead_profile_url": "https://vivo.brown.edu/display/helinzano",
        "primary_patent_url": "https://patents.google.com/patent/US20210181185A1/en",
    },
    "theromics_ri": {
        "physician_lead_name": "DAMIAN E DUPUY",
        "physician_lead_npi": "1861480733",
        "physician_lead_specialty": "Interventional radiology / tumor ablation",
        "physician_lead_institution": "Rhode Island Hospital (Theromics co-founder)",
        "physician_lead_profile_url": "https://www.theromicsinc.com/",
    },
    "nanode_ri": {
        "physician_lead_name": "QIAN CHEN",
        "physician_lead_npi": "",
        "physician_lead_specialty": "Biomedical engineering / nucleic acid delivery",
        "physician_lead_institution": "Rhode Island Hospital / NanoDe Therapeutics",
        "physician_lead_profile_url": "https://nanodetherapeutics.com/",
    },
    "cbt_pain_digital_platform_ri": {
        "physician_lead_name": "FREDERIKE PETZSCHNER",
        "physician_lead_npi": "",
        "physician_lead_specialty": "Psychiatry / digital pain therapeutics",
        "physician_lead_institution": "Brown University",
        "physician_lead_profile_url": "https://vivo.brown.edu/display/fpetzsch",
    },
    "monaghan_sepsis_diagnostic_ri": {
        "physician_lead_name": "SEAN MONAGHAN",
        "physician_lead_npi": "1871795906",
        "physician_lead_specialty": "Critical care / sepsis diagnostics",
        "physician_lead_institution": "Rhode Island Hospital",
        "physician_lead_profile_url": "",
    },
    "phlip_therapeutics_ri": {
        "physician_lead_name": "YANA K RESHETNYAK",
        "physician_lead_npi": "",
        "physician_lead_specialty": "Biophysics / pH-targeted imaging",
        "physician_lead_institution": "University of Rhode Island",
        "physician_lead_profile_url": "https://web.uri.edu/pharmacy/meet/yana-reshetnyak/",
    },
    "auto_rhode_island_biomedical_detecting_electrical_electrode_locali": {
        "physician_lead_name": "WALTER G BESIO",
        "physician_lead_npi": "",
        "physician_lead_specialty": "Biomedical engineering / neural interfaces",
        "physician_lead_institution": "University of Rhode Island",
        "physician_lead_profile_url": "https://www.ele.uri.edu/faculty/besio/",
    },
    "prothera_iaip_ri": {
        "physician_lead_name": "CHESTON CUNHA",
        "physician_lead_npi": "1023246287",
        "physician_lead_specialty": "Infectious disease / antimicrobial stewardship",
        "physician_lead_institution": "Rhode Island Hospital / Brown Medicine",
        "physician_lead_profile_url": "https://vivo.brown.edu/display/ccunha",
    },
}

# Comparable patches from primary sources (PR/grant URLs).
COMP_FIXES: dict[str, dict[str, dict[str, str]]] = {
    "nanode_ri": {
        "comp1_": {
            "comp1_value_source_url": (
                "https://www.globenewswire.com/news-release/2025/05/19/"
                "3083947/0/en/Eascra-Biotech-Awarded-100-000-MassVentures-START-Grant.html"
            ),
            "comp1_last_round_usd": "100000",
            "comp1_total_raised_usd": "4500000",
            "comp1_financing_ladder": (
                "NSF SBIR + AFWERX SBIR + >$4.5M grants/awards; "
                "MassVentures START $100K (May 2025)"
            ),
            "comp1_validation_status": "verified",
        },
    },
    "auto_rhode_island_antibacterial_antibiofilm_auranofin_catheter_coa": {
        "comp1_": {
            "comp1_name": "CorMedix DefenCath",
            "comp1_type": "incumbent",
            "comp1_role": "platform",
            "comp1_stage": "FDA_approved",
            "comp1_url": "https://www.cormedix.com/",
            "comp1_notes": (
                "FDA-approved antimicrobial catheter lock (DefenCath) — commercial "
                "infection-prevention precedent for intravascular devices"
            ),
            "comp1_value_anchor_usd": "570000000",
            "comp1_value_anchor_type": "market_cap",
            "comp1_value_source_url": (
                "https://www.macrotrends.net/stocks/charts/CRMD/cormedix-inc/market-cap"
            ),
            "comp1_financing_ladder": "Public (NASDAQ CRMD); DefenCath commercial; hospital GPO channel",
            "comp1_development_path": "Regulatory clearance → commercial infection prevention",
            "comp1_validation_status": "verified",
            "comp1_supporting_citations": (
                "CorMedix DefenCath pivotal lock study NCT02651428 | "
                "https://clinicaltrials.gov/study/NCT02651428"
            ),
        },
        "comp2_": {
            "comp2_name": "Brown/RI Hospital auranofin catheter (published)",
            "comp2_type": "research",
            "comp2_role": "platform",
            "comp2_stage": "published",
            "comp2_url": (
                "https://engineering.brown.edu/news/2019-03-07/"
                "germ-fighting-catheter-coating-may-help-prevent-infections"
            ),
            "comp2_notes": "Same invention family — Brown Engineering news + peer-reviewed coating science",
            "comp2_development_path": "GLP → 510(k) catheter coating evidence package",
            "comp2_validation_status": "suggested",
        },
        "comp3_": {
            "comp3_name": "Frontiers publication (auranofin PU coating)",
            "comp3_type": "research",
            "comp3_role": "platform",
            "comp3_stage": "published",
            "comp3_url": (
                "https://www.frontiersin.org/journals/cellular-and-infection-microbiology/"
                "articles/10.3389/fcimb.2019.00037/full"
            ),
            "comp3_notes": "Scientific precedent for auranofin polyurethane catheter coating claims",
            "comp3_development_path": "Grant-funded science → translational device spinout",
            "comp3_validation_status": "suggested",
        },
    },
    "auto_brown_university_brain_chemotherapeutic_drug_enhancing_tumors_upt": {
        "comp1_": {
            "comp1_name": "Carthera (Sonocloud BBB)",
            "comp1_type": "startup",
            "comp1_role": "platform",
            "comp1_stage": "clinical",
            "comp1_url": "https://www.carthera.eu/",
            "comp1_notes": (
                "Device-based BBB opening for brain drug delivery — clinical neuro-onc path"
            ),
            "comp1_value_anchor_usd": "55100000",
            "comp1_value_anchor_type": "total_raised",
            "comp1_value_source_url": "https://carthera.eu/",
            "comp1_total_raised_usd": "55100000",
            "comp1_last_round_usd": "45000000",
            "comp1_financing_ladder": (
                "~$55M total; Series B €42M (~$45M, Dec 2023)"
            ),
            "comp1_development_path": "Clinical trials in neuro-onc — BBB opening",
            "comp1_validation_status": "verified",
            "comp1_supporting_citations": (
                "Carthera company | https://www.carthera.eu/\n"
                "Sonocloud-9 GBM trial NCT05902169 | "
                "https://clinicaltrials.gov/study/NCT05902169"
            ),
        },
        "comp2_": {
            "comp2_name": "Insightec (Exablate / tFUS BBB)",
            "comp2_type": "startup",
            "comp2_url": "https://insightec.com/",
            "comp2_value_anchor_usd": "150000000",
            "comp2_value_anchor_type": "last_round",
            "comp2_value_source_url": (
                "https://insightec.com/news/insightec-announces-150m-financing-to-fund-continued-growth/"
            ),
            "comp2_total_raised_usd": "810000000",
            "comp2_last_round_usd": "150000000",
            "comp2_financing_ladder": "$150M equity round (Jun 2024); BBB-opening tFUS platform",
            "comp2_development_path": "Non-invasive FUS BBB modulation → neuro-onc trials",
            "comp2_validation_status": "verified",
        },
    },
    "auto_brown_university_anti_antibody_bispecific_chi3l1_reagents_relatin": {
        "comp3_": {
            "comp3_validation_status": "suggested",
            "comp3_development_path": (
                "Pharma acquisition analog — review therapeutic fit (NASH ≠ CHI3L1); "
                "prefer Ocean Biomedical / bispecific oncology exits"
            ),
        },
    },
    "prothera_iaip_ri": {
        "comp1_": {
            "comp1_name": "Takeda (ProThera IAIP license)",
            "comp1_type": "pharma_deal",
            "comp1_role": "therapeutic",
            "comp1_stage": "licensed_2020",
            "comp1_url": "https://www.takeda.com/",
            "comp1_notes": (
                "Direct IAIP development path — global plasma-derived IAIP license; "
                "Takeda funds IND-enabling and all commercialization"
            ),
            "comp1_value_source_url": (
                "https://www.takeda.com/en-us/newsroom/news-releases/2020/"
                "prothera-biologics-and-takeda-enter-global-licensing-agreement/"
            ),
            "comp1_development_path": (
                "IND-enabling → Takeda-led plasma-derived IAIP trials + companion Dx"
            ),
            "comp1_financing_ladder": (
                "Global licensing deal (Apr 2020); Takeda assumes all development "
                "funding (terms undisclosed)"
            ),
            "comp1_validation_status": "verified",
            "comp1_supporting_citations": (
                "ProThera press release | https://www.protherabiologics.com/"
                "prothera-biologics-and-takeda-enter-global-licensing-agreement-to-develop-"
                "novel-plasma-derived-therapy-based-on-inter-alpha-inhibitor-proteins-iaip/\n"
                "FierceBiotech deal summary | https://www.fiercebiotech.com/biotech/"
                "takeda-licenses-prothera-plasma-drug-for-use-inflammatory-conditions"
            ),
        },
        "comp2_": {
            "comp2_name": "Kamada",
            "comp2_type": "public",
            "comp2_role": "therapeutic",
            "comp2_stage": "commercial",
            "comp2_url": "https://www.kamada.com/",
            "comp2_notes": (
                "Plasma-derived specialty biologics commercial model — manufacturing, "
                "FDA-approved hyperimmune portfolio, and hospital formulary path "
                "(analog for IAIP CMC/commercialization)"
            ),
            "comp2_value_source_url": (
                "https://www.nasdaq.com/press-release/kamada-announces-strategic-"
                "transformational-transaction-positioning-the-company-as-a-global-leader-"
                "in-the-plasma-derived-hyperimmune-market-through-the-acquisition-of-a-"
                "portfolio-of-four-fda-approved-commercial-products"
            ),
            "comp2_value_anchor_usd": "95000000",
            "comp2_value_anchor_type": "acquisition",
            "comp2_total_raised_usd": "",
            "comp2_last_round_usd": "",
            "comp2_financing_ladder": (
                "$95M upfront Saol hyperimmune portfolio (Nov 2021); "
                "~$178–182M revenue guidance (2025); 6 FDA-approved plasma products"
            ),
            "comp2_development_path": (
                "Plasma fractionation → FDA-approved specialty biologics → "
                "hospital/transplant channel"
            ),
            "comp2_validation_status": "verified",
            "comp2_supporting_citations": (
                "Kamada investor deck (SEC) | https://www.sec.gov/Archives/edgar/data/"
                "1567529/000121390025001809/ea022709001ex99-2_kamada.htm\n"
                "IAIP sepsis science review | https://pmc.ncbi.nlm.nih.gov/articles/PMC3016999/\n"
                "IAIP plasma fractionation patent | https://patents.google.com/patent/WO2013126904A1/en"
            ),
        },
        "comp3_": {
            "comp3_name": "Lev Pharmaceuticals (Cinryze)",
            "comp3_type": "startup",
            "comp3_role": "therapeutic",
            "comp3_stage": "acquired_2008",
            "comp3_url": "https://www.fiercebiotech.com/biotech/lev-pharmaceuticals-s-cinryze-receives-fda-approval-for-prophylaxis-against-hereditary",
            "comp3_notes": (
                "Plasma-derived inflammatory biologic BLA path — C1 inhibitor (Cinryze) "
                "for orphan inflammatory disease; acquired by ViroPharma (2008)"
            ),
            "comp3_value_source_url": (
                "https://www.sec.gov/Archives/edgar/data/1144062/000114420408040150/dex991.htm"
            ),
            "comp3_value_anchor_usd": "442900000",
            "comp3_value_anchor_type": "acquisition",
            "comp3_total_raised_usd": "",
            "comp3_last_round_usd": "",
            "comp3_financing_ladder": (
                "Cinryze FDA approval (2008); ViroPharma acquired Lev for ~$442M (Oct 2008); "
                "plasma C1 inhibitor orphan BLA precedent"
            ),
            "comp3_development_path": (
                "Plasma-derived replacement therapy → orphan BLA → pharma acquisition"
            ),
            "comp3_validation_status": "verified",
            "comp3_supporting_citations": (
                "ViroPharma merger PR (SEC) | https://www.sec.gov/Archives/edgar/data/"
                "1144062/000114420408040150/dex991.htm\n"
                "Lev plasma intermediate supply (SEC) | https://www.sec.gov/Archives/edgar/"
                "data/1144062/000114420408022518/v110691_ex99-1.htm\n"
                "Acquisition completed (BioSpace) | https://www.biospace.com/"
                "viropharma-incorporated-completes-acquisition-of-lev-pharmaceuticals-inc"
            ),
        },
        "comp4_": {
            "comp4_name": "Immunexpress (SeptiCyte RAPID)",
            "comp4_type": "startup",
            "comp4_role": "diagnostic",
            "comp4_stage": "FDA_cleared",
            "comp4_url": "https://immunexpress.com/",
            "comp4_notes": (
                "Complementary sepsis host-response diagnostic — FDA-cleared SeptiCyte "
                "RAPID on Biocartis Idylla (~1 hr); pairs with IAIP therapeutic staging"
            ),
            "comp4_value_source_url": (
                "https://www.prnewswire.com/news-releases/immunexpress-secures-barda-"
                "contract-for-the-continued-development-of-septicyte-for-the-rapid-and-"
                "accurate-diagnosis-of-sepsis-300790510.html"
            ),
            "comp4_value_anchor_usd": "3200000",
            "comp4_value_anchor_type": "grant",
            "comp4_total_raised_usd": "3200000",
            "comp4_financing_ladder": (
                "BARDA DRIVe $744K of $3.2M SeptiCyte/Idylla project (Feb 2019); "
                "FDA-cleared host-response panel"
            ),
            "comp4_development_path": (
                "Host-response gene panel → FDA clearance → hospital lab adoption"
            ),
            "comp4_validation_status": "verified",
            "comp4_supporting_citations": (
                "SeptiCyte product site | https://septicyte.com/\n"
                "Immunexpress company overview | https://immunexpress.com/company-overview/\n"
                "Pediatric sepsis TGA clearance (2026) | https://immunexpress.com/"
                "immunexpress-sepsis-test-receives-regulatory-clearance-from-australian-"
                "therapeutic-goods-administration-tga-for-paediatric-patients-suspected-of-sepsis/"
            ),
        },
        "comp5_": {
            "comp5_name": "Inflammatix (TriVerity)",
            "comp5_type": "startup",
            "comp5_role": "diagnostic",
            "comp5_stage": "FDA_cleared_2025",
            "comp5_url": "https://www.inflammatix.com/",
            "comp5_notes": (
                "Sepsis host-response Dx — FDA-cleared Jan 2025; ICU adoption and "
                "$200M+ VC ladder (Monaghan-adjacent RNA panel)"
            ),
            "comp5_value_source_url": (
                "https://inflammatix.com/inflammatix-secures-57-million-to-advance-novel-"
                "diagnostic-for-patients-with-suspected-infections-or-sepsis/"
            ),
            "comp5_value_anchor_usd": "200000000",
            "comp5_value_anchor_type": "total_raised",
            "comp5_total_raised_usd": "200000000",
            "comp5_last_round_usd": "57000000",
            "comp5_financing_ladder": (
                ">$200M private + >$50M grants; $57M Series E (Sep 2024); FDA clearance Jan 2025"
            ),
            "comp5_development_path": "FDA clearance → ICU sepsis host-response adoption",
            "comp5_validation_status": "verified",
            "comp5_supporting_citations": (
                "FDA TriVerity clearance (BioSpace) | https://www.biospace.com/press-releases/"
                "inflammatix-receives-fda-clearance-for-first-in-class-triverity-test\n"
                "FDA decision summary (K241676) | https://www.accessdata.fda.gov/cdrh_docs/pdf24/K241676.pdf"
            ),
        },
        "comp6_": {
            "comp6_name": "",
            "comp6_type": "",
            "comp6_role": "",
            "comp6_stage": "",
            "comp6_url": "",
            "comp6_notes": "",
            "comp6_value_anchor_usd": "",
            "comp6_value_anchor_type": "",
            "comp6_value_source_url": "",
            "comp6_total_raised_usd": "",
            "comp6_last_round_usd": "",
            "comp6_financing_ladder": "",
            "comp6_development_path": "",
            "comp6_validation_status": "",
            "comp6_supporting_citations": "",
        },
    },
    "auto_brown_university_cardiac_cell_collagen_engineered_tissue": {
        "comp1_": {
            "comp1_name": "Heartseed (HS-001)",
            "comp1_type": "startup",
            "comp1_role": "platform",
            "comp1_stage": "clinical",
            "comp1_url": "https://heartseed.jp/en/",
            "comp1_notes": (
                "iPSC-derived cardiomyocyte spheroids for heart failure remuscularization; "
                "Phase 1/2 LAPiS study in Japan"
            ),
            "comp1_value_anchor_usd": "74000000",
            "comp1_value_anchor_type": "total_raised",
            "comp1_value_source_url": (
                "https://bioinformant.com/novo-withdraws-from-heartseed-partnership/"
            ),
            "comp1_total_raised_usd": "74000000",
            "comp1_financing_ladder": ">10.2B JPY (~$74M) lifetime; Novo Nordisk partnership ended 2025",
            "comp1_development_path": "Preclinical NHP → clinical remuscularization",
            "comp1_validation_status": "verified",
            "comp1_supporting_citations": (
                "Heartseed funding overview | "
                "https://bioinformant.com/novo-withdraws-from-heartseed-partnership/\n"
                "LAPiS Study NCT04945018 | https://clinicaltrials.gov/study/NCT04945018"
            ),
        },
        "comp2_": {
            "comp2_name": "StemCardia",
            "comp2_type": "startup",
            "comp2_role": "platform",
            "comp2_stage": "preclinical",
            "comp2_url": "https://stemcardia.com/",
            "comp2_notes": (
                "iPSC-CM remuscularization; BioCardia Helix intramyocardial delivery "
                "partnership (Mar 2024)"
            ),
            "comp2_development_path": "Preclinical NHP → IND-enabling → delivery partnership",
            "comp2_validation_status": "suggested",
            "comp2_supporting_citations": (
                "BioCardia–StemCardia partnership | "
                "https://www.globenewswire.com/news-release/2024/03/13/"
                "2845293/0/en/BioCardia-and-StemCardia-Announce-Biotherapeutic-Delivery-Partnership.html"
            ),
        },
        "comp3_": {
            "comp3_name": "BioCardia",
            "comp3_type": "public",
            "comp3_role": "platform",
            "comp3_stage": "public",
            "comp3_url": "https://www.biocardia.com/",
            "comp3_notes": "Helix intramyocardial delivery system for cell/gene therapies",
            "comp3_development_path": "IDE → clinical delivery platform → partnerships",
            "comp3_validation_status": "suggested",
        },
    },
    "auto_rhode_island_cardiotoxicity_human_model_vitro": {
        "comp1_": {
            "comp1_name": "Ncardia",
            "comp1_type": "startup",
            "comp1_role": "platform",
            "comp1_stage": "commercial",
            "comp1_url": "https://www.ncardia.com/",
            "comp1_notes": (
                "iPSC cardiac models and automated 3D microtissue CRO platform "
                "(LUMC partnership Jan 2026)"
            ),
            "comp1_development_path": (
                "Automated microtissue production → pharma safety contracts"
            ),
            "comp1_validation_status": "suggested",
        },
        "comp2_": {
            "comp2_name": "ScitoVation (IVIVE collab)",
            "comp2_type": "research",
            "comp2_role": "platform",
            "comp2_stage": "published",
            "comp2_url": (
                "https://scitovation.com/cardiac-toxicity-evaluation-with-a-"
                "human-tissue-engineered-model/"
            ),
            "comp2_notes": (
                "Published IVIVE collaboration with Coulombe/Choi microtissue platform"
            ),
            "comp2_development_path": "Grant-funded IVIVE → regulatory science adoption",
            "comp2_validation_status": "suggested",
        },
        "comp3_": {
            "comp3_name": "Brown atrial microtissue (tech transfer)",
            "comp3_type": "research",
            "comp3_role": "platform",
            "comp3_stage": "published",
            "comp3_url": "http://brown.technologypublisher.com/technology/51279",
            "comp3_notes": (
                "Chamber-specific atrial microtissues; TEEM Therapeutics spinout path"
            ),
            "comp3_development_path": "Academic platform → TEEM Therapeutics seed",
            "comp3_validation_status": "suggested",
            "comp3_supporting_citations": (
                "Brown Technology Innovations | "
                "http://brown.technologypublisher.com/technology/51279"
            ),
        },
    },
    "auto_brown_university_decellularized_extracellular_making_mammalian_ma": {
        "comp1_": {
            "comp1_name": "Slater / XM Therapeutics seed",
            "comp1_type": "ri_operating",
            "comp1_role": "platform",
            "comp1_stage": "seed_2023",
            "comp1_url": "https://slaterfund.com/slater-invests-in-xm-therapeutics/",
            "comp1_notes": (
                "Slater Technology Fund $375K seed into XM Therapeutics (Brown Morgan "
                "spinout, Oct 2023)"
            ),
            "comp1_value_anchor_usd": "375000",
            "comp1_value_anchor_type": "total_raised",
            "comp1_value_source_url": (
                "https://slaterfund.com/slater-invests-in-xm-therapeutics/"
            ),
            "comp1_total_raised_usd": "375000",
            "comp1_last_round_usd": "375000",
            "comp1_financing_ladder": "Slater $375K seed (Oct 2023); additional seed ongoing",
            "comp1_development_path": (
                "Preclinical ECM particles → pharma partnerships → IND"
            ),
            "comp1_validation_status": "verified",
            "comp1_supporting_citations": (
                "Slater invests in XM | "
                "https://slaterfund.com/slater-invests-in-xm-therapeutics/\n"
                "PBN Slater funding | https://pbn.com/brown-launched-biotech-secures-375000-in-slater-funding/"
            ),
        },
        "comp2_": {
            "comp2_name": "Ventrix VentriGel (Karen Christman)",
            "comp2_type": "startup",
            "comp2_role": "platform",
            "comp2_stage": "phase_1_complete",
            "comp2_url": "https://clinicaltrials.gov/study/NCT02305602",
            "comp2_notes": (
                "VentriGel — decellularized porcine myocardial ECM hydrogel; first-in-human "
                "Phase 1 (NCT02305602) transendocardial injection in post-MI patients with "
                "LV dysfunction; Christman/Ventrix (UCSD spinout)"
            ),
            "comp2_value_source_url": "https://pmc.ncbi.nlm.nih.gov/articles/PMC6834965/",
            "comp2_financing_ladder": (
                "Ventrix venture; FDA Phase 1 completed (15 pts); first decellularized ECM "
                "hydrogel in humans"
            ),
            "comp2_development_path": (
                "Preclinical porcine ECM hydrogel → Phase 1 safety/feasibility (Christman) "
                "→ Phase 2/3 heart failure"
            ),
            "comp2_validation_status": "verified",
            "comp2_supporting_citations": (
                "Christman Phase 1 VentriGel (JACC Basic Transl Sci) | "
                "https://pmc.ncbi.nlm.nih.gov/articles/PMC6834965/\n"
                "ClinicalTrials.gov NCT02305602 | "
                "https://clinicaltrials.gov/study/NCT02305602"
            ),
        },
        "comp3_": {
            "comp3_name": "Pliant Therapeutics (fibrosis)",
            "comp3_type": "startup",
            "comp3_role": "platform",
            "comp3_stage": "acquired_2024",
            "comp3_url": "https://www.roche.com/investors/updates/inv-update-2024-10-31",
            "comp3_notes": "Pulmonary fibrosis biotech; Roche acquisition exit analog for pulmonary focus",
            "comp3_value_anchor_usd": "1700000000",
            "comp3_value_anchor_type": "acquisition",
            "comp3_value_source_url": (
                "https://www.roche.com/investors/updates/inv-update-2024-10-31"
            ),
            "comp3_development_path": "Clinical fibrosis biotech → pharma acquisition",
            "comp3_validation_status": "suggested",
        },
        "comp4_": {
            "comp4_name": "Capricor Therapeutics (cardiac)",
            "comp4_type": "startup",
            "comp4_role": "platform",
            "comp4_stage": "clinical",
            "comp4_url": "https://www.capricor.com/",
            "comp4_notes": "Cardiac exosome/cell programs for heart failure — alternate cardiac biologics path",
            "comp4_development_path": "Preclinical → clinical cardiac biologics",
            "comp4_validation_status": "suggested",
        },
    },
    "auto_rhode_island_detection_large_occlusion_prediction_vessel": {
        "comp1_": {
            "comp1_supporting_citations": (
                "Viz.ai Series D | "
                "https://www.viz.ai/news/viz-ai-raises-100-million-in-series-d-funding\n"
                "SYNCHRONISE LVO triage study NCT04608617 | "
                "https://clinicaltrials.gov/study/NCT04608617"
            ),
        },
    },
    "phlip_therapeutics_ri": {
        "comp2_": {
            "comp2_supporting_citations": (
                "On Target Cytalux FDA approval | "
                "https://www.prnewswire.com/news-releases/on-target-laboratories-announces-fda-approval-of-cytalux-pafolacianine-for-intraoperative-identification-of-ovarian-cancer-301412789.html\n"
                "OTL38 lung imaging trial NCT02872701 | "
                "https://clinicaltrials.gov/study/NCT02872701"
            ),
        },
    },
    "theromics_ri": {
        "comp2_": {
            "comp2_supporting_citations": (
                "Profound Medical TULSA-PRO | https://profoundmedical.com/\n"
                "TULSA vs prostatectomy NCT05027477 | "
                "https://clinicaltrials.gov/study/NCT05027477"
            ),
        },
    },
    "auto_rhode_island_biomedical_detecting_electrical_electrode_locali": {
        "comp3_": {
            "comp3_supporting_citations": (
                "Precisis EASEE platform | https://www.precisis.com/\n"
                "EASEE US pivotal NCT07301346 | "
                "https://clinicaltrials.gov/study/NCT07301346"
            ),
        },
    },
    "auto_brown_university_biomedical_biosensor_diagnostics_large_networks": {
        "comp2_": {
            "comp2_supporting_citations": (
                "Synchron Series D | "
                "https://www.businesswire.com/news/home/20251106150841/en/"
                "Synchron-Raises-200-Million-Series-D-to-Advance-Brain-Computer-Interface-Technology\n"
                "SWITCH Stentrode FIH NCT03834857 | "
                "https://clinicaltrials.gov/study/NCT03834857"
            ),
        },
    },
    "monaghan_sepsis_diagnostic_ri": {
        "comp1_": {
            "comp1_supporting_citations": (
                "Inflammatix Series E | "
                "https://inflammatix.com/inflammatix-secures-57-million-to-advance-novel-diagnostic-for-patients-with-suspected-infections-or-sepsis/\n"
                "TriVerity ED sepsis study NCT06637904 | "
                "https://clinicaltrials.gov/study/NCT06637904"
            ),
        },
    },
}

# Private RI opioid/API manufacturers — excluded from Tier A syndicate scope.
TIER_C_OPIOID_API_PREFIXES: tuple[str, ...] = (
    "auto_rhodes_technologies_",
    "auto_noramco_",
)

TIER_C_OPIOID_API_PATCH: dict[str, str] = {
    "catalog_tier": "C",
    "review_status": "pending",
    "data_caveat": (
        "Catalog Tier C — private RI opioid/API manufacturer (Rhodes Technologies / "
        "Noramco). Retained for IP registry only; out of scope for Slater/physician "
        "syndicate translational packages and Tier A diligence."
    ),
    "enrichment_status": "tier_c_private_api_excluded",
}


def _is_tier_c_opioid_api(case_id: str) -> bool:
    return any(case_id.startswith(prefix) for prefix in TIER_C_OPIOID_API_PREFIXES)


def _apply_tier_c_opioid_api(row: dict[str, str]) -> list[str]:
    if not _is_tier_c_opioid_api(row.get("case_id", "")):
        return []
    changes: list[str] = []
    for key, value in TIER_C_OPIOID_API_PATCH.items():
        if row.get(key) != value:
            row[key] = value
            changes.append(key)
    return changes


# Full-row content patches (publications, clinical package, syndicate) — curated primary sources.
CASE_FIELD_PATCHES: dict[str, dict[str, str]] = {
    "cbt_pain_digital_platform_ri": {
        "catalog_tier": "A",
        "display_name": (
            "SOMA — Brown digital pain app (Petzschner / Carney Institute)"
        ),
        "title_clean": "SOMA — digital pain symptom tracking & CBT (Brown)",
        "development_stage": "validation",
        "financing_stage": "seed",
        "indication": (
            "chronic and acute pain — SOMA app for symptom tracking, digital phenotyping, "
            "and CBT-informed interventions"
        ),
        "company": "Brown University / SOMA (somatheapp.com)",
        "ri_institution": "Brown University / Carney Institute for Brain Science",
        "data_caveat": (
            "No RI patent in Lens export. Product is the SOMA Pain Manager app "
            "(somatheapp.com; iOS/Android). Research platform from Petzschner lab — "
            "distinct from employer MSK unicorns (Hinge/Sword) but follows payer/ROI analogs."
        ),
        "ri_notes": (
            "PI Frederike Petzschner (https://vivo.brown.edu/display/fpetzsch). SOMA app "
            "released 2022; >1,500 users per Carney Institute (2024). App: "
            "https://somatheapp.com/ | Apple: id6444110898. Comparables: Kaia/Sword, Hinge."
        ),
        "required_specialties": (
            "pain medicine|psychiatry|physical medicine and rehabilitation|behavioral health"
        ),
        "clinical_tags": "pain|digital_therapeutic|cbt|behavioral_health|brown",
        "physician_supporters": (
            "1194716829|MAHER EL KHATIB|PAIN MANAGEMENT|ORTHOPEDICS RHODE ISLAND INC|reviewer\n"
            "1275821738|SHIQIANG TIAN|PAIN MANAGEMENT|UNIVERSITY ORTHOPEDICS INC|reviewer\n"
            "1316966393|DO CHAN|INTERVENTIONAL PAIN MANAGEMENT|WARWICK PAIN ASSOCIATES LLC|reviewer"
        ),
        "publication_count": "3",
        "publication_titles": (
            "Practical challenges for precision medicine\n"
            "SOMAScience: A Novel Platform for Multidimensional, Longitudinal Pain Assessment\n"
            "Individual treatment expectations predict clinical outcome after lumbar "
            "injections against low back pain"
        ),
        "publication_urls": (
            "https://pubmed.ncbi.nlm.nih.gov/38207033/\n"
            "https://pubmed.ncbi.nlm.nih.gov/38214952/\n"
            "https://pubmed.ncbi.nlm.nih.gov/35543638/"
        ),
        "publication_lead_authors": (
            "Frederike H Petzschner\n"
            "Chloe Zimmerman Gunsilius; Frederike H Petzschner\n"
            "Matthias Müller-Schrader; Frederike H Petzschner"
        ),
        "publication_ri_affiliations": (
            "Brown University\nBrown University\nBrown University"
        ),
        "literature_narrative": (
            "Brown Carney Institute team led by Frederike Petzschner developed SOMA — a "
            "free pain symptom-tracking app (somatheapp.com) combining daily PRO logging, "
            "mood/activity diaries, and computational pain phenotyping for chronic pain "
            "research. SOMAScience platform publications (PubMed 38214952) support "
            "multidimensional longitudinal pain assessment; app store release documented by "
            "Brown Daily Herald (2022) and Carney Institute project page."
        ),
        "literature_source_urls": (
            "SOMA Carney project | https://carney.brown.edu/research-projects/soma-app-monitor-bodily-symptoms\n"
            "SOMA app site | https://somatheapp.com/\n"
            "SOMAScience (PubMed) | https://pubmed.ncbi.nlm.nih.gov/38214952/\n"
            "Brown Daily Herald launch | "
            "https://www.browndailyherald.com/article/2022/09/"
            "brown-researchers-collaborate-with-software-developers-to-release-pain-monitoring-app\n"
            "Apple App Store | https://apps.apple.com/us/app/soma-pain-manager/id6444110898"
        ),
        "comparable_market_narrative": (
            "Kaia Health — acquired by Sword for $285M (Jan 2026) [verified] || "
            "Hinge Health — ~$1.5B total raised; $437M IPO (May 2025) [verified] || "
            "Sword Health — ~$4B post-money; acquired Kaia 2026 [verified]"
        ),
        "investment_thesis": (
            "Brown University's Petzschner laboratory has published RI-affiliated research "
            "on digital pain assessment (SOMAScience) and clinical pain outcomes, packaged "
            "for investors as the SOMA Pain Management digital CBT platform. A $400,000 RI "
            "co-investment de-risks payer-ready outcomes studies and Rhode Island pain-clinic "
            "pilots with a statewide physician syndicate (pain medicine reviewers). Comparable "
            "financing spans Kaia/Sword consolidation and Hinge Health's venture-to-public "
            "MSK path — validating employer/payer ROI for digital pain programs. "
            "$200,000 clinical / $200,000 R&D; 50% physician syndicate / 50% Slater SSBCI match."
        ),
        "trial_count": "0",
        "trial_nct_ids": "",
        "trial_titles": "",
        "trial_pi_names": "",
        "trial_urls": "",
        "trial_phases": "",
        "clinical_study_type": (
            "RI digital pain pilot — SOMA app engagement + PRO endpoints in chronic pain cohort"
        ),
        "clinical_primary_endpoint": (
            "8-week change in pain interference (PROMIS) vs usual care; app adherence ≥70%"
        ),
        "clinical_duration_weeks": "12",
        "clinical_cost_usd": "200000",
        "clinical_allocation_usd": "200000",
        "rd_allocation_usd": "200000",
        "target_timeline_weeks": "12",
        "clinical_path_notes": (
            "RI pain-medicine reviewers oversee endpoint selection; design aligned with "
            "digital MSK precedents (Hinge/Sword) without claiming their trials."
        ),
        "rd_plan_summary": (
            "Harden SOMAScience analytics pipeline; complete health-economic model for "
            "payer pitch; prepare Series A data room referencing Kaia/Sword and Hinge "
            "financing ladders."
        ),
        "rd_milestones": (
            "Q1: SOMA app + analytics validation vs publication claims\n"
            "Q2: Payer/employer pilot LOI with RI pain clinic partners\n"
            "Q3: Physician syndicate review of clinical endpoints\n"
            "Q4: Slater/physician gate for seed syndicate or strategic MSK partner"
        ),
        "rd_milestone_types": "clinical|regulatory|financing|preclinical",
        "rd_milestone_source_urls": (
            "Q1: SOMAScience platform (PubMed) | https://pubmed.ncbi.nlm.nih.gov/38214952/\n"
            "Q2: Kaia/Sword acquisition precedent | "
            "https://swordhealth.com/newsroom/sword-acquires-kaia-health\n"
            "Q3: Hinge Health financing path | https://sacra.com/c/hinge-health/\n"
            "Q4: Sword Health scale | https://swordhealth.com/newsroom/sword-acquires-kaia-health"
        ),
        "rd_plan_source_url": "https://pubmed.ncbi.nlm.nih.gov/38214952/",
        "financing_rationale": (
            "$400K RI package: $200K funds digital pain pilot and syndicate oversight; "
            "$200K covers analytics, payer modeling, and commercialization materials. "
            "Verified digital MSK comps anchor Slater SSBCI match narrative."
        ),
        "mcq_lead_pillar": "clinical",
        "mcq_financing_structure": "physician_50_slater_ssbci_50",
        "mcq_audience": "mixed_slater_physician_hospital_bd",
        "review_status": "approved",
        "reviewer": "JJR",
        "enrichment_status": "curated_tier_a",
    },
    "auto_rhode_island_antibacterial_antibiofilm_auranofin_catheter_coa": {
        "catalog_tier": "A",
        "display_name": (
            "Auranofin antibiofilm catheter coating — Brown / RI Hospital device IP"
        ),
        "development_stage": "validation",
        "financing_stage": "seed",
        "indication": (
            "intravascular catheter coatings — sustained auranofin release against "
            "bacterial biofilm and MRSA persisters"
        ),
        "company": "Brown University / Rhode Island Hospital",
        "ri_institution": "Brown University / Rhode Island Hospital",
        "data_caveat": (
            "Active patent US 11931482 B2 (auranofin-releasing PU catheter coatings). "
            "RI package funds 510(k)-oriented evidence — not a duplicate of CorMedix "
            "DefenCath commercial lock solution."
        ),
        "ri_notes": (
            "Inventors Beth Fuchs, Anita Shukla, Eleftherios Mylonakis (Brown/RI Hospital). "
            "CorMedix DefenCath = commercial infection-prevention comp; Brown Engineering "
            "news + Frontiers paper = science precedent."
        ),
        "required_specialties": (
            "infectious disease|critical care|hospital epidemiology|interventional cardiology"
        ),
        "clinical_tags": "infectious_disease|medical_device|catheter|biofilm|brown",
        "physician_lead_name": "BETH FUCHS",
        "physician_lead_specialty": "Infectious disease / hospital epidemiology",
        "physician_lead_institution": "Rhode Island Hospital / Brown University",
        "publication_count": "5",
        "publication_titles": (
            "Strategies against methicillin-resistant Staphylococcus aureus persisters\n"
            "Antibacterial properties of 3-(phenylsulfonyl)-2-pyrazinecarbonitrile\n"
            "Molecular and nonmolecular diagnostic methods for invasive fungal infections\n"
            "Prevalence of Steatotic Liver Disease (MASLD, MetALD, and ALD) in the US\n"
            "Antimicrobial Peptides and Small Molecules Targeting the Cell Membrane"
        ),
        "publication_urls": (
            "https://pubmed.ncbi.nlm.nih.gov/29569952/\n"
            "https://pubmed.ncbi.nlm.nih.gov/26459212/\n"
            "https://pubmed.ncbi.nlm.nih.gov/24982319/\n"
            "https://pubmed.ncbi.nlm.nih.gov/37949334/\n"
            "https://pubmed.ncbi.nlm.nih.gov/37129495/"
        ),
        "publication_lead_authors": (
            "Wooseong Kim; Eleftherios Mylonakis\n"
            "Rajmohan Rajamuthiah; Eleftherios Mylonakis\n"
            "Marios Arvanitis; Eleftherios Mylonakis\n"
            "Markos Kalligeros; Eleftherios Mylonakis\n"
            "Haiyan Liu; Eleftherios Mylonakis"
        ),
        "publication_ri_affiliations": (
            "Brown University\nBrown University\nBrown University\nBrown University\nBrown University"
        ),
        "literature_narrative": (
            "Brown and Rhode Island Hospital research targets MRSA persisters and antibacterial "
            "small molecules (PubMed 29569952, 26459212) with Mylonakis-lab infectious disease "
            "depth. Patent US 11931482 B2 covers auranofin-releasing polyurethane intravascular "
            "catheter coatings. CorMedix DefenCath provides the commercial catheter "
            "infection-prevention benchmark (~$570M market cap)."
        ),
        "literature_source_urls": (
            "MRSA persister strategies (PubMed) | https://pubmed.ncbi.nlm.nih.gov/29569952/\n"
            "Antibacterial small molecules (PubMed) | https://pubmed.ncbi.nlm.nih.gov/26459212/\n"
            "Brown Engineering catheter coating news | "
            "https://engineering.brown.edu/news/2019-03-07/"
            "germ-fighting-catheter-coating-may-help-prevent-infections\n"
            "Primary patent (Lens) | https://lens.org/046-968-808-987-818"
        ),
        "comparable_market_narrative": (
            "CorMedix DefenCath — ~$570M market cap; FDA-approved catheter lock [verified] || "
            "Brown/RI Hospital auranofin catheter (published) — translational science [suggested] || "
            "Frontiers auranofin PU coating paper — 510(k) evidence [suggested]"
        ),
        "investment_thesis": (
            "Brown and Rhode Island Hospital hold active patent protection for auranofin-releasing "
            "antibiofilm polyurethane catheter coatings (US 11931482 B2), supported by "
            "Mylonakis-laboratory infectious disease publications. The RI package funds "
            "510(k)-oriented coating validation and hospital epidemiology pilots — complementary "
            "to CorMedix DefenCath's commercial lock franchise, not competing with it. "
            "Inventor-aligned oversight (Beth Fuchs) and ID syndicate framing de-risk "
            "regulatory and adoption narratives. "
            "$200,000 clinical / $200,000 R&D; 50% physician syndicate / 50% Slater SSBCI match."
        ),
        "clinical_study_type": (
            "RI catheter coating pilot — biofilm burden and MRSA persistence on coated vs "
            "control catheters (preclinical/clinical simulation)"
        ),
        "clinical_primary_endpoint": (
            "Log reduction in biofilm CFU at 72h; catheter surface biocompatibility histology"
        ),
        "clinical_duration_weeks": "32",
        "clinical_cost_usd": "200000",
        "clinical_allocation_usd": "200000",
        "rd_allocation_usd": "200000",
        "target_timeline_weeks": "32",
        "clinical_path_notes": (
            "Hospital epidemiology framing; endpoints suitable for 510(k) substantial "
            "equivalence narrative vs published coating science and DefenCath market context."
        ),
        "rd_plan_summary": (
            "Complete coating release kinetics and biofilm assay package; draft 510(k) "
            "predicate strategy; prepare strategic outreach to catheter OEM partners."
        ),
        "rd_milestones": (
            "Q1: In vitro MRSA biofilm assay vs CorMedix benchmark claims\n"
            "Q2: Coating stability and elution kinetics (GLP-style)\n"
            "Q3: ID physician syndicate review of safety monitoring plan\n"
            "Q4: Slater/physician gate for spinout or OEM partnership"
        ),
        "rd_milestone_types": "preclinical|regulatory|clinical|financing",
        "rd_milestone_source_urls": (
            "Q1: MRSA persister science (PubMed) | https://pubmed.ncbi.nlm.nih.gov/29569952/\n"
            "Q2: Frontiers coating publication | "
            "https://www.frontiersin.org/journals/cellular-and-infection-microbiology/"
            "articles/10.3389/fcimb.2019.00037/full\n"
            "Q3: CorMedix commercial benchmark | https://www.cormedix.com/\n"
            "Q4: Primary patent (Lens) | https://lens.org/046-968-808-987-818"
        ),
        "rd_plan_source_url": "https://lens.org/046-968-808-987-818",
        "financing_rationale": (
            "$400K RI package: $200K funds biofilm pilot and ID oversight; $200K covers "
            "coating analytics, regulatory drafting, and OEM partnership materials. "
            "CorMedix verified comp anchors hospital adoption narrative."
        ),
        "mcq_lead_pillar": "clinical",
        "mcq_financing_structure": "physician_50_slater_ssbci_50",
        "mcq_audience": "mixed_slater_physician_hospital_bd",
        "review_status": "approved",
        "reviewer": "JJR",
        "enrichment_status": "curated_tier_a",
    },
    "auto_rhode_island_detection_large_occlusion_prediction_vessel": {
        "catalog_tier": "A",
        "display_name": (
            "AI large-vessel occlusion detection — Brown / RI Hospital stroke triage IP"
        ),
        "development_stage": "validation",
        "financing_stage": "seed",
        "indication": (
            "acute ischemic stroke — large vessel occlusion detection and treatment "
            "prediction from neuroimaging"
        ),
        "company": "Brown University / Rhode Island Hospital",
        "ri_institution": "Brown University / Rhode Island Hospital",
        "data_caveat": (
            "Pending patent US 2023/0149088 A1 (LVO detection and treatment prediction). "
            "RI package funds clinical validation with stroke neurology — distinct from "
            "Viz.ai / RapidAI commercial triage contracts."
        ),
        "ri_notes": (
            "Inventor Harrison Bai (Brown/RI Hospital). Comparables: Viz.ai ($100M Series D), "
            "RapidAI ($75M Series C). Curated publications emphasize radiology ML methods "
            "supporting neuro-AI translation."
        ),
        "required_specialties": "neurology|neurosurgery|neuroradiology|stroke",
        "clinical_tags": "stroke|lvo|neuroradiology|ai|brown",
        "physician_lead_name": "HARRISON BAI",
        "physician_lead_specialty": "Neuroradiology / stroke imaging",
        "physician_lead_institution": "Rhode Island Hospital / Brown University",
        "physician_supporters": (
            "1043704703|SCOTT WARREN|NEUROLOGY|RHODE ISLAND HOSPITAL|reviewer\n"
            "1043730112|ANIRUDH PENUMAKA|NEUROSURGERY|LIFESPAN PHYSICIAN GROUP INC|reviewer\n"
            "1053840827|ELIAS SHAAYA|NEUROSURGERY|RHODE ISLAND HOSPITAL|reviewer"
        ),
        "publication_count": "4",
        "publication_titles": (
            "Using Machine Learning to Predict Response to Image-guided Therapies for "
            "Hepatocellular Carcinoma\n"
            "Artificial intelligence for medical image analysis in epilepsy\n"
            "Deep Learning: An Update for Radiologists\n"
            "Performance of Radiologists in Differentiating COVID-19 from Non-COVID-19 "
            "Viral Pneumonia at Chest CT"
        ),
        "publication_urls": (
            "https://pubmed.ncbi.nlm.nih.gov/37934098/\n"
            "https://pubmed.ncbi.nlm.nih.gov/35364483/\n"
            "https://pubmed.ncbi.nlm.nih.gov/34469211/\n"
            "https://pubmed.ncbi.nlm.nih.gov/32155105/"
        ),
        "publication_lead_authors": (
            "Harrison X Bai; Celina Hsieh\n"
            "Harrison X Bai; John Sollee\n"
            "Harrison X Bai\n"
            "Harrison X Bai; Phillip M Cheng"
        ),
        "publication_ri_affiliations": (
            "Brown University\nBrown University\nBrown University\nBrown University"
        ),
        "literature_narrative": (
            "Brown-affiliated radiology AI publications by Harrison Bai include machine-learning "
            "prediction for image-guided therapy (PubMed 37934098), epilepsy imaging AI "
            "(35364483), and radiologist-facing deep learning methods (34469211). Pending "
            "patent US 2023/0149088 A1 targets LVO detection and treatment prediction. "
            "Viz.ai and RapidAI provide verified stroke-triage financing precedents."
        ),
        "literature_source_urls": (
            "ML image-guided therapy (PubMed) | https://pubmed.ncbi.nlm.nih.gov/37934098/\n"
            "AI medical imaging epilepsy (PubMed) | https://pubmed.ncbi.nlm.nih.gov/35364483/\n"
            "Deep learning radiology update (PubMed) | https://pubmed.ncbi.nlm.nih.gov/34469211/\n"
            "Primary patent (Lens) | https://lens.org/074-975-118-075-847"
        ),
        "comparable_market_narrative": (
            "Viz.ai — $100M Series D (Apr 2022); $1.2B valuation; stroke triage SaaS [verified] || "
            "RapidAI — $75M Series C (Jul 2023); LVO + perfusion AI [verified]"
        ),
        "investment_thesis": (
            "Brown and Rhode Island Hospital inventors hold pending IP on large-vessel "
            "occlusion detection and treatment prediction (US 2023/0149088 A1), with "
            "Harrison Bai's RI lead-author radiology AI publications establishing technical "
            "credibility. The $400,000 RI package funds stroke-neurology validation and "
            "health-system pilot design — not a replacement for Viz.ai or RapidAI enterprise "
            "contracts, but a local proof point for Slater and physician syndicate co-investment. "
            "Comparable financing shows $100M+ venture rounds for AI stroke networks. "
            "$200,000 clinical / $200,000 R&D; 50% physician syndicate / 50% Slater SSBCI match."
        ),
        "clinical_study_type": (
            "RI stroke AI validation — LVO detection accuracy vs neuroradiology gold standard "
            "(retrospective + prospective pilot)"
        ),
        "clinical_primary_endpoint": (
            "Sensitivity/specificity for LVO on CTA; time-to-triage vs standard of care"
        ),
        "clinical_duration_weeks": "40",
        "clinical_cost_usd": "200000",
        "clinical_allocation_usd": "200000",
        "rd_allocation_usd": "200000",
        "target_timeline_weeks": "40",
        "clinical_path_notes": (
            "RI neurology/neurosurgery reviewers (Warren, Penumaka, Shaaya) frame endpoints; "
            "aligned with Viz.ai/RapidAI hospital workflow precedents."
        ),
        "rd_plan_summary": (
            "Lock ML model on RI Hospital imaging cohort; complete FDA SaMD pre-submission "
            "outline; prepare health-system pilot MOU referencing Viz.ai/RapidAI market path."
        ),
        "rd_milestones": (
            "Q1: Retrospective LVO model validation on RI Hospital CTA set\n"
            "Q2: Prospective triage time-to-decision pilot\n"
            "Q3: Stroke syndicate review of clinical safety and workflow\n"
            "Q4: Slater/physician gate for seed round or strategic channel (Viz/Rapid analog)"
        ),
        "rd_milestone_types": "clinical|regulatory|financing|preclinical",
        "rd_milestone_source_urls": (
            "Q1: ML radiology methods (PubMed) | https://pubmed.ncbi.nlm.nih.gov/37934098/\n"
            "Q2: Viz.ai Series D precedent | "
            "https://www.viz.ai/news/viz-ai-raises-100-million-in-series-d-funding\n"
            "Q3: RapidAI Series C | "
            "https://www.rapidai.com/press-release/rapid-announces-investment-led-by-vista-credit-partners\n"
            "Q4: Primary patent (Lens) | https://lens.org/074-975-118-075-847"
        ),
        "rd_plan_source_url": "https://lens.org/074-975-118-075-847",
        "financing_rationale": (
            "$400K RI package: $200K funds stroke validation pilot and syndicate oversight; "
            "$200K covers model hardening, regulatory strategy, and health-system outreach. "
            "Verified AI stroke comps (Viz.ai, RapidAI) anchor investor narrative."
        ),
        "mcq_lead_pillar": "clinical",
        "mcq_financing_structure": "physician_50_slater_ssbci_50",
        "mcq_audience": "mixed_slater_physician_hospital_bd",
        "review_status": "approved",
        "reviewer": "JJR",
        "enrichment_status": "curated_tier_a",
    },
    "auto_brown_university_brain_chemotherapeutic_drug_enhancing_tumors_upt": {
        "catalog_tier": "A",
        "display_name": (
            "Blood-tumor barrier modulation for GBM chemo uptake — Brown Lawler lab"
        ),
        "development_stage": "validation",
        "financing_stage": "seed",
        "indication": (
            "glioblastoma and primary brain tumors — enhancing chemotherapeutic drug "
            "uptake across the blood-tumor barrier"
        ),
        "ri_institution": "Brown University",
        "data_caveat": (
            "Brown University therapeutic composition/platform (US 2024/0358678 A1). "
            "Distinct from device-based BBB opening (Carthera Sonocloud) — focuses on "
            "modulating blood-tumor barrier biology to potentiate chemotherapy."
        ),
        "ri_notes": (
            "Inventor Sean Lawler (https://vivo.brown.edu/display/slawler). "
            "Comparables: Carthera BBB device path, Insightec tFUS BBB modulation. "
            "Four Brown-affiliated PubMed papers on blood-tumor barrier and GBM (2024–2025)."
        ),
        "required_specialties": "neuro-oncology|medical oncology|neurosurgery|radiation oncology",
        "clinical_tags": "neuro_oncology|glioblastoma|bbb|therapeutic|brown",
        "physician_lead_npi": "",
        "physician_supporters": (
            "1194249565|MOHAMMED JALOUDI|MEDICAL ONCOLOGY|AFFINITY PHYSICIANS LLC.|reviewer\n"
            "1336596774|KATHRYN DECARLI|MEDICAL ONCOLOGY|RHODE ISLAND HOSPITAL|reviewer\n"
            "1790977650|KHALDOUN ALMHANNA|MEDICAL ONCOLOGY|RHODE ISLAND HOSPITAL|reviewer"
        ),
        "publication_count": "4",
        "publication_titles": (
            "Modulation of blood-tumor barrier transcriptional programs improves "
            "intratumoral drug delivery and potentiates chemotherapy in GBM\n"
            "Modulation of blood-tumor barrier transcriptional programs improves "
            "intra-tumoral drug delivery and potentiates chemotherapy in GBM\n"
            "Decoding the biology of the blood-brain tumor barrier in brain cancer\n"
            "Clinical implications of cytomegalovirus in glioblastoma progression and therapy"
        ),
        "publication_urls": (
            "https://pubmed.ncbi.nlm.nih.gov/40009687/\n"
            "https://pubmed.ncbi.nlm.nih.gov/39253453/\n"
            "https://pubmed.ncbi.nlm.nih.gov/41854391/\n"
            "https://pubmed.ncbi.nlm.nih.gov/39343770/"
        ),
        "publication_lead_authors": (
            "Sean Lawler; Jorge L Jimenez-Macias\n"
            "Sean Lawler; Jorge L Jimenez-Macias\n"
            "Jorge L Jimenez-Macias; Sean Lawler\n"
            "Noe B Mercado; Sean Lawler"
        ),
        "publication_ri_affiliations": (
            "Brown University\nBrown University\nBrown University\nBrown University"
        ),
        "literature_narrative": (
            "Brown University research shows that modulating blood-tumor barrier (BTB) "
            "transcriptional programs can improve intratumoral delivery and potentiate "
            "chemotherapy in glioblastoma (PubMed 40009687, 39253453). Related work "
            "decodes BTB biology in brain cancer (PubMed 41854391). The Lawler lab patent "
            "family (US 2024/0358678 A1) targets enhanced chemotherapeutic uptake into "
            "brain tumors. Development and financing comps include Carthera Sonocloud BBB "
            "device trials and Insightec Exablate tFUS BBB-opening platform ($150M round, 2024)."
        ),
        "literature_source_urls": (
            "BTB modulation improves GBM chemotherapy (PubMed) | "
            "https://pubmed.ncbi.nlm.nih.gov/40009687/\n"
            "BTB transcriptional programs (PubMed) | "
            "https://pubmed.ncbi.nlm.nih.gov/39253453/\n"
            "Blood-brain tumor barrier biology (PubMed) | "
            "https://pubmed.ncbi.nlm.nih.gov/41854391/\n"
            "Primary patent (Lens) | https://lens.org/152-495-100-609-294"
        ),
        "comparable_market_narrative": (
            "Carthera (Sonocloud BBB) — ~$55M raised; clinical BBB opening for brain drug "
            "delivery [verified] || Insightec (Exablate / tFUS BBB) — $150M round (Jun 2024); "
            "non-invasive FUS BBB modulation [verified]"
        ),
        "investment_thesis": (
            "Brown University's Lawler laboratory has published RI lead-author work on "
            "blood-tumor barrier biology and glioblastoma chemotherapy potentiation, "
            "anchored by pending patent US 2024/0358678 A1. The RI opportunity is a "
            "$400,000 validation package to de-risk BTB-targeted compositions and "
            "in vivo chemo-uptake claims — complementary to device-based BBB opening "
            "(Carthera, Insightec) rather than competing with their Sonocloud or tFUS "
            "platforms. Neuro-oncology physician syndicate oversight (Prof. Sean Lawler, "
            "RI Hospital oncology reviewers) frames a translational path toward IND-enabling "
            "studies. Comparable financing spans Carthera venture neuro-onc rounds and "
            "Insightec's $150M BBB platform raise. "
            "$200,000 clinical / $200,000 R&D; 50% physician syndicate / 50% Slater SSBCI match."
        ),
        "clinical_study_type": (
            "RI GBM translational pilot — BTB biomarker panel and chemo uptake pharmacology "
            "(preclinical/early clinical protocol design; not claiming existing registry match)"
        ),
        "clinical_primary_endpoint": (
            "Intratumoral drug concentration vs BTB transcriptional score in GBM model; "
            "safety/tolerability of modulation regimen"
        ),
        "clinical_duration_weeks": "40",
        "clinical_cost_usd": "200000",
        "clinical_allocation_usd": "200000",
        "rd_allocation_usd": "200000",
        "target_timeline_weeks": "40",
        "clinical_path_notes": (
            "Oncology syndicate (RI Hospital medical oncology) reviews endpoint selection; "
            "aligns with Carthera/Insightec BBB precedent narratives without claiming "
            "their device trials."
        ),
        "rd_plan_summary": (
            "Validate BTB modulation composition in GBM models; quantify chemotherapeutic "
            "uptake vs controls; complete CMC/analytics package and pre-IND briefing outline "
            "referencing Carthera clinical path and Insightec BBB-opening regulatory analogs."
        ),
        "rd_milestones": (
            "Q1: BTB transcriptional biomarker panel locked to publication claims\n"
            "Q2: In vivo chemo-uptake study vs GBM controls (GLP-style report)\n"
            "Q3: Physician syndicate review of clinical translation and safety monitoring\n"
            "Q4: Slater/physician gate for spinout or strategic device-pharma partnership"
        ),
        "rd_milestone_types": "preclinical|clinical|regulatory|financing",
        "rd_milestone_source_urls": (
            "Q1: BTB biomarker panel (PubMed) | https://pubmed.ncbi.nlm.nih.gov/40009687/\n"
            "Q2: In vivo chemo-uptake study | https://pubmed.ncbi.nlm.nih.gov/39253453/\n"
            "Q3: Clinical translation review | https://carthera.eu/\n"
            "Q4: Strategic partnership gate | "
            "https://insightec.com/news/insightec-announces-150m-financing-to-fund-continued-growth/"
        ),
        "rd_plan_source_url": "https://lens.org/152-495-100-609-294",
        "financing_rationale": (
            "$400K RI package: $200K funds GBM translational pilot design and oncology "
            "syndicate oversight; $200K covers BTB modulation studies, analytics, and "
            "pre-IND documentation. Verified BBB comps (Carthera, Insightec) anchor "
            "investor narrative for Slater SSBCI match."
        ),
        "mcq_lead_pillar": "clinical",
        "mcq_financing_structure": "physician_50_slater_ssbci_50",
        "mcq_audience": "mixed_slater_physician_hospital_bd",
        "review_status": "approved",
        "reviewer": "JJR",
        "enrichment_status": "curated_tier_a",
    },
    "auto_brown_university_implantable_neural_wireless": {
        "catalog_tier": "A",
        "display_name": (
            "Wireless implantable neural interface — Brown Nurmikko lab, BCI precedent path"
        ),
        "development_stage": "validation",
        "financing_stage": "seed",
        "indication": (
            "chronic wireless neural recording and stimulation for neuroprosthetics and BCI"
        ),
        "ri_institution": "Brown University",
        "data_caveat": (
            "Academic platform (US 10433754 B2 family); no RI spinout named in Lens export. "
            "RI package funds translational de-risking and clinician validation — distinct "
            "from Astellas/Iota corporate path."
        ),
        "ri_notes": (
            "Inventor Arto Nurmikko (https://vivo.brown.edu/display/anurmikk). "
            "Comparables: Iota neural dust → Astellas acquisition, Synchron endovascular BCI, "
            "Precision thin-film cortical arrays. Related Brown wireless neural programs in "
            "biomedical_biosensor_diagnostics_large_networks row."
        ),
        "required_specialties": "neurology|neurosurgery|physical medicine and rehabilitation",
        "clinical_tags": "neurology|neurosurgery|medical_device|neuroengineering|bci",
        "physician_supporters": (
            "1023039740|DENNIS AUMENTADO|NEUROLOGY|NORTH SMITHFIELD, RI|reviewer\n"
            "1023135720|PREETI GUPTA|NEUROLOGY|EAST PROVIDENCE, RI|reviewer\n"
            "1023182383|JUAN CANTON|NEUROLOGY|WARWICK, RI|reviewer"
        ),
        "publication_count": "6",
        "publication_titles": (
            "Listening to Brain Microcircuits for Interfacing With External World-Progress "
            "in Wireless Implantable Microelectronic Neuroengineering Devices\n"
            "Developing implantable neuroprosthetics: a new model in pig\n"
            "A 100-channel hermetically sealed implantable device for chronic wireless "
            "neurosensing applications\n"
            "A 32-channel fully implantable wireless neurosensor for simultaneous recording "
            "from two cortical regions\n"
            "Wireless, high-bandwidth recordings from non-human primate motor cortex using "
            "a scalable 16-Ch implantable microsystem\n"
            "An implantable wireless neural interface for recording cortical circuit "
            "dynamics in moving primates"
        ),
        "publication_urls": (
            "https://pubmed.ncbi.nlm.nih.gov/21654935/\n"
            "https://pubmed.ncbi.nlm.nih.gov/22254977/\n"
            "https://pubmed.ncbi.nlm.nih.gov/23853294/\n"
            "https://pubmed.ncbi.nlm.nih.gov/22254801/\n"
            "https://pubmed.ncbi.nlm.nih.gov/19964128/\n"
            "https://pubmed.ncbi.nlm.nih.gov/23428937/"
        ),
        "publication_lead_authors": (
            "Arto Nurmikko; Juan Aceros\n"
            "Arto Nurmikko; David A Borton\n"
            "Arto Nurmikko; Ming Yin\n"
            "Arto Nurmikko; William R Patterson\n"
            "Arto Nurmikko; David A Borton\n"
            "Arto Nurmikko; David A Borton"
        ),
        "publication_ri_affiliations": (
            "Brown University\nBrown University\nBrown University\nBrown University\n"
            "Brown University\nBrown University"
        ),
        "literature_narrative": (
            "Brown University neuroengineering publications document scalable wireless "
            "implantable microsystems for chronic cortical recording in large animals and "
            "primates (PubMed 21654935, 23428937). The Nurmikko lab patent family "
            "(US 10433754 B2) covers hermetically sealed, high-channel-count wireless "
            "neurosensors — the technical anchor for an RI validation package. Financing "
            "and development path comps run Iota/Astellas neural dust acquisition, "
            "Synchron endovascular BCI, and Precision Neuroscience cortical surface arrays."
        ),
        "literature_source_urls": (
            "Wireless neuroengineering review (PubMed) | "
            "https://pubmed.ncbi.nlm.nih.gov/21654935/\n"
            "Implantable neuroprosthetics pig model (PubMed) | "
            "https://pubmed.ncbi.nlm.nih.gov/22254977/\n"
            "100-channel wireless neurosensor (PubMed) | "
            "https://pubmed.ncbi.nlm.nih.gov/23853294/\n"
            "Primary patent (Lens) | https://lens.org/086-564-880-656-79X"
        ),
        "comparable_market_narrative": (
            "Iota Biosciences (neural dust) — $304M Astellas acquisition path [verified] || "
            "Synchron (Stentrode) — $345M lifetime funding; pivotal BCI [verified] || "
            "Precision Neuroscience (Layer 7) — $155M; thin-film cortical array [verified] || "
            "Blackrock Neurotech — Utah array research/clinical BCI [suggested]"
        ),
        "investment_thesis": (
            "Brown University's Nurmikko lab has published a decade-long trajectory of "
            "wireless, implantable neural interfaces for chronic brain recording — anchored "
            "by US 10433754 B2 and six Brown-affiliated PubMed papers. The RI opportunity "
            "is not a duplicate of Astellas/Iota or Synchron corporate programs; a $400,000 "
            "co-investment package de-risks translational milestones (hermetic packaging, "
            "wireless link reliability, large-animal feasibility) with neurology/neurosurgery "
            "syndicate oversight led by inventor-aligned engineering faculty (Prof. Arto "
            "Nurmikko). Comparable financing runs neural-dust acquisition → endovascular BCI "
            "venture scale → cortical surface-array Series C. "
            "$200,000 clinical / $200,000 R&D; 50% physician syndicate / 50% Slater SSBCI match."
        ),
        "clinical_study_type": (
            "RI translational feasibility — wireless implant telemetry and biocompatibility "
            "in large-animal neurosensor pilot (protocol design; not claiming existing NCT)"
        ),
        "clinical_primary_endpoint": (
            "30-day wireless link uptime and signal quality in chronic implant model; "
            "adverse event profile vs bench controls"
        ),
        "clinical_duration_weeks": "36",
        "clinical_cost_usd": "200000",
        "clinical_allocation_usd": "200000",
        "rd_allocation_usd": "200000",
        "target_timeline_weeks": "36",
        "clinical_path_notes": (
            "Physician syndicate (RI neurology reviewers) advises on clinical relevance of "
            "endpoints; pilot design aligned with BCI precedent path (Synchron/Precision) "
            "without claiming IDE status."
        ),
        "rd_plan_summary": (
            "Complete hermetic packaging and wireless power/data link validation; "
            "document multi-channel cortical recording in translational model; prepare "
            "regulatory strategy memo (510(k)/IDE pathway analog) and Series A data room "
            "aligned with Iota/Synchron financing precedents."
        ),
        "rd_milestones": (
            "Q1: Bench wireless link + hermetic seal verification vs patent claims\n"
            "Q2: Large-animal chronic recording feasibility (telemetry QA)\n"
            "Q3: Physician syndicate review of clinical endpoint and safety monitoring plan\n"
            "Q4: Slater/physician gate for spinout/partner discussions (Astellas-class strategic)"
        ),
        "rd_milestone_types": "preclinical|clinical|regulatory|financing",
        "rd_milestone_source_urls": (
            "Q1: Bench wireless link + hermetic seal verification vs patent claims | "
            "https://lens.org/086-564-880-656-79X\n"
            "Q2: Large-animal chronic recording feasibility (telemetry QA) | "
            "https://pubmed.ncbi.nlm.nih.gov/22254977/\n"
            "Q3: Physician syndicate review of clinical endpoint and safety monitoring plan | "
            "https://newsroom.astellas.com/2020-10-30-Astellas-Completes-Acquisition-of-iota-Biosciences\n"
            "Q4: Slater/physician gate for spinout/partner discussions | "
            "https://www.businesswire.com/news/home/20251106150841/en/Synchron-Raises-200-Million-Series-D-to-Advance-Brain-Computer-Interface-Technology"
        ),
        "rd_plan_source_url": "https://lens.org/086-564-880-656-79X",
        "financing_rationale": (
            "$400K RI package: $200K funds translational pilot design and clinician "
            "oversight; $200K covers packaging, wireless electronics, and regulatory "
            "strategy documentation. Comps show venture → acquisition (Iota) and "
            "late-stage BCI private rounds (Synchron, Precision) — RI capital proves "
            "local credibility for Slater SSBCI match."
        ),
        "trial_count": "2",
        "trial_nct_ids": "NCT03834857 | NCT05034870",
        "trial_titles": (
            "SWITCH — Stentrode first-in-human BCI (Synchron comp precedent)\n"
            "COMMAND — Stentrode early feasibility study in severe paralysis (Synchron)"
        ),
        "trial_pi_names": "Synchron Inc",
        "trial_urls": (
            "https://clinicaltrials.gov/study/NCT03834857\n"
            "https://clinicaltrials.gov/study/NCT05034870"
        ),
        "trial_phases": "Early Phase 1 | Early Phase 1",
        "mcq_lead_pillar": "technology",
        "mcq_financing_structure": "physician_50_slater_ssbci_50",
        "mcq_audience": "mixed_slater_physician_hospital_bd",
        "review_status": "approved",
        "reviewer": "JJR",
        "enrichment_status": "curated_tier_a",
    },
    "prothera_iaip_ri": {
        "catalog_tier": "A",
        "display_name": (
            "Plasma-derived IAIP for early sepsis — Brown/RI Hospital science, Takeda global license"
        ),
        "development_stage": "validation",
        "financing_stage": "seed",
        "ri_institution": "Brown University / Rhode Island Hospital / ProThera Biologics",
        "data_caveat": (
            "Global IAIP program licensed to Takeda (Apr 2020). RI co-investment package "
            "funds local ICU biomarker-enriched pilot and physician validation — not a "
            "duplicate of Takeda IND."
        ),
        "ri_notes": (
            "Inventor/CEO Yow-Pin Lim (https://vivo.brown.edu/display/ylimmdph). "
            "Distinct IAIP replacement biologic vs monaghan_sepsis_diagnostic_ri host-RNA dx. "
            "Slater-seeded; >$12M NIH SBIR; Takeda global license."
        ),
        "required_specialties": "critical care|infectious disease|neonatology|emergency medicine",
        "clinical_tags": "sepsis|critical_care|infectious_disease|neonatology|therapeutic",
        "physician_supporters": (
            "1205814357|GERARDO CARINO|CRITICAL CARE (INTENSIVISTS)|BROWN MEDICINE|"
            "pilot_designer|reviewer\n"
            "1104189653|DONALD RICE|INFECTIOUS DISEASE|BROWN MEDICINE|investigator|reviewer"
        ),
        "publication_count": "3",
        "publication_titles": (
            "ProThera Biologics, Inc.: A Novel Immunomodulator and Biomarker for "
            "Life-Threatening Diseases\n"
            "Correlation between mortality and the levels of inter-alpha inhibitors in the "
            "plasma of patients with severe sepsis\n"
            "Longitudinal studies of inter-alpha inhibitor proteins in severely septic "
            "patients: a potential clinical marker and mediator of severe sepsis"
        ),
        "publication_urls": (
            "http://www.rimed.org/rimedicaljournal/2013/02/2013-02-16-bio-prothera.pdf\n"
            "https://pubmed.ncbi.nlm.nih.gov/12964125/\n"
            "https://pubmed.ncbi.nlm.nih.gov/17205024/"
        ),
        "publication_lead_authors": (
            "Yow-Pin Lim; Douglas C. Hixson\n"
            "Yow-Pin Lim; Douglas C. Hixson\n"
            "Yow-Pin Lim; Douglas C. Hixson"
        ),
        "publication_ri_affiliations": (
            "Rhode Island Hospital\nRhode Island Hospital\nRhode Island Hospital"
        ),
        "literature_narrative": (
            "Inter-alpha inhibitor proteins (IAIP) are endogenous serine protease inhibitors "
            "depleted in severe sepsis; failure to recover IAIP levels correlates with mortality "
            "(PubMed 17205024). RI Hospital/Brown research (Lim, Hixson) showed IAIP "
            "replacement improves survival in E. coli sepsis models (PubMed 12964125). "
            "ProThera holds RI-origin IP, NIH SBIR-funded manufacturing, and a 2020 Takeda "
            "global license — the only plasma-derived IAIP platform with pharma-backed "
            "IND-enabling path. Pairs with FDA-cleared sepsis host-response diagnostics "
            "(Inflammatix, Immunexpress) for stratified ICU pilots."
        ),
        "literature_source_urls": (
            "ProThera Biologics novel immunomodulator (RI Med J) | "
            "http://www.rimed.org/rimedicaljournal/2013/02/2013-02-16-bio-prothera.pdf\n"
            "IAIP levels and sepsis mortality (PubMed) | "
            "https://pubmed.ncbi.nlm.nih.gov/17205024/\n"
            "Longitudinal IAIP in severe sepsis (PubMed) | "
            "https://pubmed.ncbi.nlm.nih.gov/12964125/\n"
            "Primary patent (Lens) | https://lens.org/041-853-574-697-591"
        ),
        "comparable_market_narrative": (
            "Takeda (ProThera IAIP license) — global plasma IAIP license (Apr 2020); "
            "Takeda funds IND-enabling [verified] || "
            "Kamada — $95M hyperimmune portfolio acquisition; plasma commercial model [verified] || "
            "Lev Pharmaceuticals (Cinryze) — ~$443M ViroPharma acquisition; orphan plasma BLA [verified] || "
            "Immunexpress (SeptiCyte RAPID) — BARDA-funded; FDA-cleared host-response sepsis Dx [verified] || "
            "Inflammatix (TriVerity) — $57M Series E; FDA clearance Jan 2025 [verified]"
        ),
        "investment_thesis": (
            "ProThera Biologics is the Rhode Island originator of inter-alpha inhibitor protein "
            "(IAIP) replacement therapy for early sepsis and critical illness. Brown and Rhode "
            "Island Hospital research links low IAIP levels to mortality and shows replacement "
            "improves outcomes in preclinical models. The platform is de-risked by a global Takeda "
            "license (Apr 2020) funding IND-enabling work; this $400,000 RI package does not "
            "duplicate Takeda development—it funds a biomarker-enriched ICU pilot, GMP analytics, "
            "and pre-IND documentation with physician syndicate oversight (Dr. Cheston Cunha, "
            "infectious disease/critical care). Comparable path runs Takeda pharma deal → plasma "
            "commercial models (Kamada, Cinryze) and pairs with FDA-cleared sepsis host-response "
            "diagnostics (SeptiCyte, TriVerity) for stratified enrollment. "
            "$240,000 clinical / $160,000 R&D; 50% physician syndicate / 50% Slater SSBCI match."
        ),
        "rd_milestone_source_urls": (
            "Q1: IAIP assay correlation with host-response Dx in RI ICU biobank samples | "
            "https://pubmed.ncbi.nlm.nih.gov/17205024/\n"
            "Q2: GMP lot characterization + pre-IND briefing book draft | "
            "https://www.takeda.com/en-us/newsroom/news-releases/2020/"
            "prothera-biologics-and-takeda-enter-global-licensing-agreement/\n"
            "Q3: Physician syndicate–reviewed pilot protocol (N≈30–40) with Lifespan IRB path | "
            "https://immunexpress.com/\n"
            "Q4: Slater/physician milestone gate for expanded enrollment or strategic follow-on | "
            "https://inflammatix.com/inflammatix-secures-57-million-to-advance-novel-diagnostic-for-patients-with-suspected-infections-or-sepsis/"
        ),
        "rd_plan_source_url": "https://lens.org/041-853-574-697-591",
        "clinical_study_type": "RI ICU biomarker-enriched IAIP pilot (companion to host-response Dx)",
        "clinical_primary_endpoint": (
            "IAIP recovery trajectory at 72h and organ failure–free days in high-risk sepsis"
        ),
        "clinical_duration_weeks": "40",
        "clinical_cost_usd": "240000",
        "clinical_allocation_usd": "240000",
        "rd_allocation_usd": "160000",
        "target_timeline_weeks": "40",
        "clinical_path_notes": (
            "Stage with SeptiCyte/TriVerity host-response panels; physician syndicate "
            "oversees ICU enrollment, biomarker cutoffs, and antimicrobial stewardship alignment."
        ),
        "rd_plan_summary": (
            "Validate GMP IAIP lot release and point-of-care IAIP level assay against RI ICU "
            "samples; complete pre-IND briefing package aligned with Takeda license scope while "
            "preserving ProThera optionality on companion diagnostic and neonatal indications."
        ),
        "rd_milestones": (
            "Q1: IAIP assay correlation with host-response Dx in RI ICU biobank samples\n"
            "Q2: GMP lot characterization + pre-IND briefing book draft\n"
            "Q3: Physician syndicate–reviewed pilot protocol (N≈30–40) with Lifespan IRB path\n"
            "Q4: Slater/physician milestone gate for expanded enrollment or strategic follow-on"
        ),
        "rd_milestone_types": "preclinical|regulatory|clinical|financing",
        "financing_rationale": (
            "$400K RI package: $240K funds biomarker-enriched ICU pilot design and IRB-ready "
            "protocol (physician syndicate oversight); $160K covers GMP analytics, IAIP assay "
            "validation, and pre-IND documentation. Takeda license de-risks global development; "
            "RI capital proves local clinical credibility for Slater SSBCI match and Right Hill "
            "follow-on."
        ),
        "mcq_lead_pillar": "physicians",
        "mcq_financing_structure": "physician_50_slater_ssbci_50",
        "mcq_audience": "mixed_slater_physician_hospital_bd",
        "trial_count": "0",
        "trial_nct_ids": "",
        "trial_titles": "",
        "trial_pi_names": "",
        "trial_urls": "",
        "trial_phases": "",
        "review_status": "approved",
        "reviewer": "JJR",
        "enrichment_status": "curated_tier_a",
    },
    "auto_brown_university_cardiac_cell_collagen_engineered_tissue": {
        "catalog_tier": "A",
        "title_clean": "Coulombe — engineered cardiac tissue (EHM)",
        "program_family": "coulombe_cardiac_regen",
        "display_name": (
            "Engineered human myocardium — Coulombe Lab hiPSC collagen ECT, remuscularization"
        ),
        "development_stage": "validation",
        "financing_stage": "seed",
        "indication": (
            "post-MI heart failure — hiPSC engineered human myocardium remuscularization"
        ),
        "company": "Brown University / Coulombe Lab",
        "ri_institution": "Brown University / Rhode Island Hospital",
        "opportunity_type": "platform",
        "data_caveat": (
            "Patent US 2024/0165301 A1 (Coulombe, Dwyer, Kant). Distinct from TEEM "
            "Therapeutics (cardiotox/AFib platform) and XM Therapeutics (injectable ECM "
            "particles). No named RI spinout in Lens export yet."
        ),
        "ri_notes": (
            "Inventor Kareen Coulombe (https://sites.brown.edu/coulombelab/). NIH NHLBI "
            "$2.8M remuscularization grant (2024). Frank Sellke cardiac surgery collab on "
            "EHM publications. Sibling case: auto_rhode_island_cardiotoxicity_human_model_vitro."
        ),
        "required_specialties": "cardiology|thoracic surgery|heart failure",
        "clinical_tags": "heart_failure|regenerative_medicine|cardiology|brown",
        "physician_supporters": (
            "1417983123|RUPA BALA|CARDIAC ELECTROPHYSIOLOGY|RHODE ISLAND HOSPITAL|reviewer\n"
            "1043439615|PHILIP HAINES|CARDIOVASCULAR DISEASE (CARDIOLOGY)|"
            "THE MIRIAM HOSPITAL|reviewer"
        ),
        "publication_count": "3",
        "publication_titles": (
            "One Billion hiPSC-Cardiomyocytes: Upscaling Engineered Cardiac Tissues to "
            "Create High Cell Density Therapies for Clinical Translation in Heart Regeneration\n"
            "A predictive in vitro risk assessment platform for pro-arrhythmic toxicity "
            "using human 3D cardiac microtissues\n"
            "Human Atrial Cardiac Microtissues for Chamber-Specific Arrhythmic Risk Assessment"
        ),
        "publication_urls": (
            "https://pubmed.ncbi.nlm.nih.gov/37189962/\n"
            "https://pubmed.ncbi.nlm.nih.gov/34050128/\n"
            "https://pubmed.ncbi.nlm.nih.gov/34777603/"
        ),
        "publication_lead_authors": (
            "Kiera Dwyer; Kareen L K Coulombe\n"
            "Catherine M Kofron; Kareen L K Coulombe\n"
            "A H Soepriatna; Kareen L K Coulombe"
        ),
        "publication_ri_affiliations": (
            "Brown University\nBrown University\nBrown University"
        ),
        "literature_narrative": (
            "Coulombe Lab at Brown engineers hiPSC-derived cardiomyocyte tissues for heart "
            "regeneration and disease modeling. Dwyer et al. (2023) scaled engineered cardiac "
            "tissues to clinical cell doses (~1B hiPSC-CMs). Patent US 2024/0165301 A1 covers "
            "cell and collagen compositions for engineered cardiac tissue. Comparable path "
            "follows Heartseed iPSC spheroid clinical development (~$74M raised)."
        ),
        "literature_source_urls": (
            "One billion hiPSC-CMs ECT (PubMed) | https://pubmed.ncbi.nlm.nih.gov/37189962/\n"
            "Coulombe Lab research | https://sites.brown.edu/coulombelab/research/heartregeneration/\n"
            "NIH remuscularization grant | "
            "https://engineering.brown.edu/news/2024-05-30/coulombe-awarded-28m-nih\n"
            "Primary patent (Lens) | https://lens.org/026-212-779-352-796"
        ),
        "comparable_market_narrative": (
            "Heartseed (HS-001) — ~$74M raised; iPSC spheroid Phase 1/2 in Japan [verified] || "
            "StemCardia — BioCardia Helix delivery partnership; preclinical remuscularization "
            "[suggested] || BioCardia — intramyocardial delivery platform [suggested]"
        ),
        "trial_count": "1",
        "trial_nct_ids": "NCT04945018",
        "trial_titles": (
            "LAPiS Study — HS-001 iPSC-derived cardiomyocyte spheroids in ischemic heart "
            "failure (Heartseed comp precedent; not Coulombe ECT-sponsored)"
        ),
        "trial_pi_names": "Heartseed Inc",
        "trial_urls": "https://clinicaltrials.gov/study/NCT04945018",
        "trial_phases": "Phase 1/Phase 2",
        "review_status": "pending",
        "enrichment_status": "curated_tier_a",
    },
    "auto_rhode_island_cardiotoxicity_human_model_vitro": {
        "catalog_tier": "A",
        "title_clean": "TEEM Therapeutics — cardiac microtissue platform",
        "program_family": "teem_cardiac_platform",
        "display_name": (
            "TEEM Therapeutics — hiPSC cardiac microtissues for cardiotox and AFib R&D"
        ),
        "development_stage": "validation",
        "financing_stage": "seed",
        "indication": (
            "proarrhythmic cardiotoxicity screening and atrial fibrillation drug discovery"
        ),
        "company": "TEEM Therapeutics Inc",
        "ri_institution": "Brown University / Rhode Island Hospital",
        "opportunity_type": "platform",
        "data_caveat": (
            "Patent US 2022/0163511 A1 (Choi, Coulombe). Coulombe Lab states TEEM "
            "Therapeutics Inc. is the startup spinout for AFib drug-discovery R&D using "
            "tissue-engineered cardiac microtissues (TEEMs). Cardiotox screening platform "
            "collaborates with Choi/Mende (RI Hospital) and ScitoVation IVIVE — distinct "
            "from Coulombe ECT therapy case."
        ),
        "ri_notes": (
            "TEEM Therapeutics spinout per Coulombe Lab research page. Coulombe/Choi hiPSC "
            "3D cardiac microtissues for proarrhythmic cardiotoxicity (Sci Reports 2021) and "
            "AFib atrial microtissues (Cell Mol Bioeng 2021). NIEHS U01 + NSF CAREER; "
            "ScitoVation IVIVE collaboration. Sibling: Coulombe ECT remuscularization case."
        ),
        "required_specialties": (
            "cardiology|electrophysiology|medical oncology"
        ),
        "clinical_tags": "cardiology|electrophysiology|diagnostic|platform|brown",
        "physician_supporters": (
            "1457304859|FRANK SELLKE|THORACIC SURGERY|"
            "UNIVERSITY CARDIOVASCULAR SURGICAL ASSOCIATES INC|reviewer\n"
            "1043439615|PHILIP HAINES|CARDIOVASCULAR DISEASE (CARDIOLOGY)|"
            "THE MIRIAM HOSPITAL|reviewer"
        ),
        "publication_count": "3",
        "publication_titles": (
            "A predictive in vitro risk assessment platform for pro-arrhythmic toxicity "
            "using human 3D cardiac microtissues\n"
            "Human Atrial Cardiac Microtissues for Chamber-Specific Arrhythmic Risk Assessment\n"
            "Computationally informed point of departure evaluation for proarrhythmic "
            "cardiotoxicity assessment using 3D engineered cardiac microtissues"
        ),
        "publication_urls": (
            "https://pubmed.ncbi.nlm.nih.gov/34050128/\n"
            "https://pubmed.ncbi.nlm.nih.gov/34777603/\n"
            "https://pubmed.ncbi.nlm.nih.gov/39253453/"
        ),
        "publication_lead_authors": (
            "Catherine M Kofron; Kareen L K Coulombe\n"
            "A H Soepriatna; Kareen L K Coulombe\n"
            "M C Daley; Kareen L K Coulombe"
        ),
        "publication_ri_affiliations": (
            "Brown University\nBrown University\nBrown University"
        ),
        "literature_narrative": (
            "Coulombe and Choi labs at Brown/RI Hospital built 3D hiPSC cardiac microtissues "
            "(TEEMs) for proarrhythmic cardiotoxicity screening (Sci Reports 2021; CAAT "
            "Brown cardiac program) and chamber-specific atrial AFib modeling (Cell Mol "
            "Bioeng 2021). Coulombe Lab notes AFib drug R&D spun into startup TEEM "
            "Therapeutics Inc.; ScitoVation collaboration uses IVIVE for regulatory "
            "translation of microtissue cardiotox data."
        ),
        "literature_source_urls": (
            "Coulombe Lab research (TEEM spinout) | https://sites.brown.edu/coulombelab/research/\n"
            "In vitro cardiotox models | https://sites.brown.edu/coulombelab/research/invitromodels-2/\n"
            "CAAT Brown cardiac | https://caat.brown.edu/research/cardiac\n"
            "ScitoVation collab | https://scitovation.com/cardiac-toxicity-evaluation-with-a-human-tissue-engineered-model/\n"
            "Pro-arrhythmic microtissues (PubMed) | https://pubmed.ncbi.nlm.nih.gov/34050128/\n"
            "Atrial microtissues (PubMed) | https://pubmed.ncbi.nlm.nih.gov/34777603/\n"
            "Primary patent (Lens) | https://lens.org/128-033-973-760-237"
        ),
        "comparable_market_narrative": (
            "ScitoVation IVIVE collab — regulatory translation path for Coulombe cardiotox "
            "platform [verified] || Ncardia — iPSC cardiac microtissue CRO [suggested] || "
            "Brown atrial microtissue → TEEM Therapeutics spinout [verified per Coulombe Lab]"
        ),
        "rd_plan_summary": (
            "Validate TEEM cardiotox platform against FDA CiPA reference compounds; extend "
            "IVIVE modeling with ScitoVation; advance atrial AFib microtissue drug-target "
            "screening under TEEM Therapeutics spinout path with cardiology/EP syndicate "
            "oversight."
        ),
        "rd_milestones": (
            "Q1: Lock cardiotox metric panel vs Sci Reports 2021 platform claims\n"
            "Q2: ScitoVation IVIVE report for lead oncology cardiotox analogs\n"
            "Q3: Atrial AFib microtissue target triage (Brown tech transfer 51279)\n"
            "Q4: Physician syndicate review of TEEM clinical translation path"
        ),
        "rd_milestone_source_urls": (
            "Q1: Cardiotox platform (PubMed) | https://pubmed.ncbi.nlm.nih.gov/34050128/\n"
            "Q2: ScitoVation IVIVE | https://scitovation.com/cardiac-toxicity-evaluation-with-a-human-tissue-engineered-model/\n"
            "Q3: Brown atrial tech transfer | http://brown.technologypublisher.com/technology/51279\n"
            "Q4: Coulombe Lab TEEM spinout | https://sites.brown.edu/coulombelab/research/"
        ),
        "rd_plan_source_url": "https://sites.brown.edu/coulombelab/research/",
        "review_status": "pending",
        "enrichment_status": "curated_tier_a",
    },
    "monaghan_sepsis_diagnostic_ri": {
        "catalog_tier": "A",
        "display_name": (
            "Monaghan Lab — deep RNA sepsis pathogen diagnostics (RI Hospital)"
        ),
        "title_clean": "Monaghan — deep RNA sepsis diagnostics",
        "company": "Monaghan Lab / Rhode Island Hospital",
        "data_caveat": (
            "Diagnostic host-response / pathogen RNA program led by Sean Monaghan (RI "
            "Hospital surgery/critical care). Distinct from ProThera Biologics IAIP "
            "replacement therapy (Takeda-licensed therapeutic) — Monaghan develops RNA-seq "
            "→ PCR pathogen tests (QIAcuityDx), not plasma protein replacement."
        ),
        "ri_notes": (
            "PI Sean Monaghan (https://vivo.brown.edu/display/smonagha). NIH NIGMS R35 "
            "GM142638 Improving Sepsis Care with Deep RNA Sequencing. RI Hospital first "
            "North America QIAcuityDx install for sepsis pathogen PCR targets derived from "
            "RNA-seq. Patent family US20220340972A1 (sepsis RNA diagnosis). No spinout yet."
        ),
        "literature_narrative": (
            "Monaghan Lab uses deep RNA sequencing (>100M reads/blood draw) in ICU sepsis "
            "patients to detect pathogen RNA, resistance genes, and host splicing signatures — "
            "translating hits to digital PCR on QIAcuityDx (PubMed 41697057; Brown Health "
            "2024). Program is diagnostic/microbiology acceleration, not therapeutic IAIP "
            "replacement (see prothera_iaip_ri)."
        ),
        "literature_source_urls": (
            "Monaghan Lab | https://surgery.med.brown.edu/divisions/surgical-research/laboratories/monaghan-lab\n"
            "VIVO profile | https://vivo.brown.edu/display/smonagha\n"
            "Sepsis RNA PCR paper (PubMed) | https://pubmed.ncbi.nlm.nih.gov/41697057/\n"
            "Sepsis RNA patent | https://patents.google.com/patent/US20220340972A1/en\n"
            "QIAcuityDx RI Hospital | "
            "https://www.brownhealth.org/news/rhode-island-hospital-becomes-first-hospital-north-america-install-qiacuitydx\n"
            "Primary patent (Lens) | https://lens.org/085-655-703-999-246"
        ),
        "rd_plan_summary": (
            "Translate Monaghan deep RNA-seq pathogen targets to QIAcuityDx clinical "
            "microbiology workflow; validate vs blood culture in RI ICU cohort; prepare "
            "physician syndicate–reviewed pilot with critical care / ID reviewers."
        ),
        "rd_milestones": (
            "Q1: Lock PCR target panel from PubMed 41697057 cohort\n"
            "Q2: QIAcuityDx validation vs blood culture in RI ICU samples\n"
            "Q3: Critical care syndicate endpoint + IRB protocol review\n"
            "Q4: Slater/physician gate for diagnostic spinout or hospital lab partnership"
        ),
        "rd_milestone_source_urls": (
            "Q1: RNA-seq pathogen paper | https://pubmed.ncbi.nlm.nih.gov/41697057/\n"
            "Q2: QIAcuityDx install | https://www.brownhealth.org/news/rhode-island-hospital-becomes-first-hospital-north-america-install-qiacuitydx\n"
            "Q3: Monaghan Lab | https://surgery.med.brown.edu/divisions/surgical-research/laboratories/monaghan-lab\n"
            "Q4: NIH R35GM142638 | https://vivo.brown.edu/display/smonagha"
        ),
        "rd_plan_source_url": "https://vivo.brown.edu/display/smonagha",
        "comparable_market_narrative": (
            "Inflammatix TriVerity — host-response sepsis Dx; FDA cleared 2025 [verified] || "
            "Immunexpress SeptiCyte — host RNA sepsis on Idylla [verified] || "
            "Presymptom Health — early infection RNA Dx [suggested]"
        ),
        "trial_count": "1",
        "trial_nct_ids": "NCT06637904",
        "trial_titles": (
            "TriVerity for Improved Management of Emergency Department (ED) Patients "
            "With Suspected Severe Infection or Sepsis (Inflammatix comp precedent; "
            "not Monaghan Lab-sponsored)"
        ),
        "trial_pi_names": "Inflammatix Inc",
        "trial_urls": "https://clinicaltrials.gov/study/NCT06637904",
        "trial_phases": "Not Applicable",
        "review_status": "pending",
        "enrichment_status": "curated_tier_a",
    },
    "nanode_ri": {
        "catalog_tier": "A",
        "display_name": (
            "NanoDe Therapeutics — Nanopieces RNA delivery (Qian Chen, RI Hospital)"
        ),
        "title_clean": "NanoDe — Nanopieces nucleic acid delivery",
        "company": "NanoDe Therapeutics Inc",
        "ri_institution": "Brown University / Rhode Island Hospital",
        "data_caveat": (
            "Technology licensed from Brown University Health / RI Hospital (Janus-base "
            "Nanopieces). Scientific founder and CSO: Qian Chen. Lab in Providence with "
            "RI Life Science Hub Growth Catalyst Award (2024–2025)."
        ),
        "ri_notes": (
            "Qian Chen — co-founder/CSO (https://nanodetherapeutics.com/). NIH R41 "
            "TR002298 Nanopieces siRNA delivery. Founded 2015; Barrington RI HQ; Providence "
            "lab with Brown Health core access. Targets solid tumor, CNS, cartilage."
        ),
        "physician_lead_name": "QIAN CHEN",
        "physician_lead_specialty": "Nucleic acid delivery / biomedical engineering",
        "physician_lead_institution": "NanoDe Therapeutics / Rhode Island Hospital",
        "physician_lead_profile_url": "https://nanodetherapeutics.com/",
        "literature_narrative": (
            "NanoDe Therapeutics develops Nanopieces — self-assembled Janus-base nanotube "
            "carriers for siRNA/mRNA/gene therapy into dense tissues (tumor, cartilage, "
            "brain). Platform invented at Brown/RI Hospital by Qian Chen; company received "
            "Rhode Island Life Science Hub Growth Catalyst Award and NIH SBIR R41 support."
        ),
        "literature_source_urls": (
            "NanoDe Therapeutics | https://nanodetherapeutics.com/\n"
            "NIH R41 TR002298 | https://grantome.com/grant/NIH/R41-TR002298-01A1\n"
            "Primary patent (Lens) | https://lens.org/008-231-790-422-477"
        ),
        "rd_plan_summary": (
            "Advance Nanopieces siRNA delivery POC in cartilage/oncology models; leverage "
            "RI Life Science Hub Growth Catalyst Award for CMC and in vivo biodistribution; "
            "prepare Slater/physician syndicate path toward Series A."
        ),
        "rd_milestones": (
            "Q1: Nanopieces formulation QC vs patent claims\n"
            "Q2: In vivo delivery POC (cartilage or tumor model)\n"
            "Q3: Growth Catalyst / SBIR milestone report\n"
            "Q4: Physician syndicate review of first indication"
        ),
        "rd_milestone_source_urls": (
            "Q1: Primary patent (Lens) | https://lens.org/008-231-790-422-477\n"
            "Q2: NanoDe site | https://nanodetherapeutics.com/\n"
            "Q3: NIH R41 | https://grantome.com/grant/NIH/R41-TR002298-01A1\n"
            "Q4: NanoDe site | https://nanodetherapeutics.com/"
        ),
        "rd_plan_source_url": "https://nanodetherapeutics.com/",
        "comparable_market_narrative": (
            "Eascra Biotech — Janus nucleotide SBIR analog (UConn) [verified] || "
            "Ionis Pharmaceuticals — oligonucleotide platform [suggested] || "
            "Alnylam — RNAi delivery [suggested]"
        ),
        "review_status": "pending",
        "enrichment_status": "curated_tier_a",
    },
    "auto_brown_university_decellularized_extracellular_making_mammalian_ma": {
        "catalog_tier": "A",
        "title_clean": "XM Therapeutics — injectable ECM particles",
        "program_family": "xm_therapeutics_ecm",
        "display_name": (
            "XM Therapeutics — Morgan lab injectable ECM particles for heart failure "
            "and pulmonary fibrosis"
        ),
        "development_stage": "validation",
        "financing_stage": "seed",
        "indication": (
            "heart failure and pulmonary fibrosis — injectable designer ECM particles"
        ),
        "company": "XM Therapeutics Inc",
        "ri_institution": "Brown University / Rhode Island Hospital",
        "opportunity_type": "platform",
        "data_caveat": (
            "Patent US 2023/0348859 A1 (Morgan, Blanche). Slater invested $375K (Oct 2023). "
            "Clinical precedent: Christman/Ventrix VentriGel Phase 1 (NCT02305602) used "
            "decellularized porcine cardiac ECM hydrogel — separate sponsor, same modality "
            "class. XM has not yet registered its own clinical trial."
        ),
        "ri_notes": (
            "Co-founder Jeffrey Morgan (https://vivo.brown.edu/display/jmorgan). CEO Frank "
            "Ahmann; cardiac advisor Frank Sellke (RI Hospital). Slater seed $375K. "
            "Development path analog: Karen Christman VentriGel (porcine decellularized ECM, "
            "NCT02305602). Distinct from Coulombe ECT and TEEM cardiotox cases."
        ),
        "required_specialties": "cardiology|pulmonology|heart failure",
        "clinical_tags": "heart_failure|pulmonary_fibrosis|regenerative_medicine|brown|slater",
        "physician_lead_profile_url": "https://vivo.brown.edu/display/jmorgan",
        "physician_supporters": (
            "1417983123|RUPA BALA|CARDIAC ELECTROPHYSIOLOGY|RHODE ISLAND HOSPITAL|reviewer\n"
            "1043439615|PHILIP HAINES|CARDIOVASCULAR DISEASE (CARDIOLOGY)|"
            "THE MIRIAM HOSPITAL|reviewer"
        ),
        "publication_count": "3",
        "publication_titles": (
            "First-in-Man Study of a Cardiac Extracellular Matrix Hydrogel in Early and "
            "Late Myocardial Infarction Patients\n"
            "Multi-cellular spheroids as building blocks for scaffold-free tissue "
            "engineering\n"
            "Engineering of functional, pre-vascularized three-dimensional cardiac "
            "tissues in vitro"
        ),
        "publication_urls": (
            "https://pmc.ncbi.nlm.nih.gov/articles/PMC6834965/\n"
            "https://pubmed.ncbi.nlm.nih.gov/19543177/\n"
            "https://pubmed.ncbi.nlm.nih.gov/23415088/"
        ),
        "publication_lead_authors": (
            "Karen L Christman; Ventrix clinical team\n"
            "Jeffrey R Morgan; et al.\n"
            "Kareen L K Coulombe; Jeffrey R Morgan"
        ),
        "publication_ri_affiliations": (
            "UC San Diego / Ventrix (clinical precedent)\nBrown University\nBrown University"
        ),
        "literature_narrative": (
            "Jeffrey Morgan's Brown laboratory pioneered scaffold-free 3D microtissues; XM "
            "Therapeutics applies decellularized ECM particles from human 3D cultures for "
            "heart failure and pulmonary fibrosis. The leading clinical precedent in this "
            "modality is Karen Christman's VentriGel — a decellularized porcine myocardial "
            "ECM hydrogel tested in the first-in-human Phase 1 trial NCT02305602 "
            "(transendocardial injection, post-MI patients, n=15), which demonstrated safety "
            "and feasibility. Patent US 2023/0348859 A1 covers Morgan's ECM morsels; Slater "
            "led a $375K XM seed round (Oct 2023)."
        ),
        "literature_source_urls": (
            "Christman VentriGel Phase 1 (PMC) | "
            "https://pmc.ncbi.nlm.nih.gov/articles/PMC6834965/\n"
            "ClinicalTrials.gov NCT02305602 | "
            "https://clinicaltrials.gov/study/NCT02305602\n"
            "Morgan microtissue spheroids (PubMed) | https://pubmed.ncbi.nlm.nih.gov/19543177/\n"
            "Brown Impact — XM Therapeutics | "
            "https://impact-magazine.brown.edu/brown-invents/xm-therapeutics\n"
            "Slater invests in XM | "
            "https://slaterfund.com/slater-invests-in-xm-therapeutics/\n"
            "Primary patent (Lens) | https://lens.org/193-358-966-816-063"
        ),
        "comparable_market_narrative": (
            "Slater / XM Therapeutics seed — $375K Slater seed (Oct 2023) [verified] || "
            "Ventrix VentriGel (Karen Christman) — Phase 1 NCT02305602; decellularized "
            "porcine cardiac ECM hydrogel; first-in-human ECM gel [verified] || "
            "Pliant Therapeutics (fibrosis) — Roche acquisition fibrosis exit analog "
            "[suggested] || Capricor Therapeutics (cardiac) — clinical cardiac biologics "
            "[suggested]"
        ),
        "suggest_trial_nct_ids": "",
        "suggest_trial_titles": "",
        "suggest_trial_urls": "",
        "suggest_trial_notes": "",
        "trial_count": "1",
        "trial_nct_ids": "NCT02305602",
        "trial_titles": (
            "A Study of VentriGel in Post-MI Patients (decellularized porcine cardiac ECM "
            "hydrogel — Ventrix/VentriGel)"
        ),
        "trial_pi_names": "Karen L Christman",
        "trial_urls": "https://clinicaltrials.gov/study/NCT02305602",
        "trial_phases": "Phase 1",
        "clinical_study_type": (
            "RI-aligned early clinical path — injectable cardiac ECM after MI, modeled on "
            "Christman VentriGel Phase 1 (transendocardial delivery, LVEF 25–45%)"
        ),
        "clinical_primary_endpoint": (
            "Safety/feasibility of transendocardial ECM delivery; secondary LV remodeling "
            "(ESV, EDV, EF, scar mass) per Christman precedent"
        ),
        "clinical_path_notes": (
            "Christman/Ventrix NCT02305602 established first-in-human safety for "
            "decellularized porcine cardiac ECM hydrogel in post-MI heart failure. XM "
            "preclinical program targets similar indications with human 3D-culture-derived "
            "ECM particles; RI syndicate (Sellke/cardiology) validates endpoint selection "
            "for a future XM IND — not claiming VentriGel trial as XM-owned."
        ),
        "rd_plan_summary": (
            "Advance XM ECM particle CMC and large-animal cardiac repair data; align IND "
            "enabling endpoints with Christman VentriGel Phase 1 precedent "
            "(NCT02305602); prepare physician-syndicate-reviewed protocol outline for "
            "post-MI injectable ECM trial at RI/Lifespan sites."
        ),
        "rd_milestones": (
            "Q1: Map XM particle release/spec vs VentriGel hydrogel precedent (Christman PMC)\n"
            "Q2: Preclinical cardiac repair package (porcine/large animal) with Sellke input\n"
            "Q3: Draft IND briefing outline citing NCT02305602 safety/feasibility\n"
            "Q4: Slater/physician gate for XM first-in-human protocol"
        ),
        "rd_milestone_source_urls": (
            "Q1: Christman VentriGel Phase 1 | https://pmc.ncbi.nlm.nih.gov/articles/PMC6834965/\n"
            "Q2: XM preclinical (company) | https://www.xmtherapeutics.com/technology\n"
            "Q3: NCT02305602 registry | https://clinicaltrials.gov/study/NCT02305602\n"
            "Q4: Slater XM seed | https://slaterfund.com/slater-invests-in-xm-therapeutics/"
        ),
        "review_status": "pending",
        "enrichment_status": "curated_tier_a",
    },
}

ASSIGNEE_TO_RI_INSTITUTION: dict[str, str] = {
    "BROWN UNIVERSITY": "Brown University",
    "RHODE ISLAND HOSPITAL": "Rhode Island Hospital",
    "RHODE ISLAND BOARD OF EDUCATION STATE OF RHODE ISLAND AND PROVIDENCE PLANTATIONS": (
        "University of Rhode Island"
    ),
    "UNIVERSITY OF RHODE ISLAND BOARD OF GOVERNORS": "University of Rhode Island",
    "RHODE ISLAND COUNCIL ON POSTSECONDARY EDUCATION": "University of Rhode Island",
    "NORAMCO LLC": "Noramco LLC",
    "RHODES TECHNOLOGIES": "Rhodes Technologies",
    "PURDUE PHARMA L.P": "Purdue Pharma",
    "PURDUE PHARMACEUTICALS L.P": "Purdue Pharmaceuticals",
    "THE REGENTS OF THE UNIVERSITY OF CALIFORNIA": "University of California",
}

SUGGEST_PUB_COLUMNS = ()  # preserved for BioMCP apply (pipeline.ri_biomcp_publications)


def _inventor_display_name(patent_name: str) -> str:
    """USPTO order LAST FIRST [MIDDLE] → readable lead name."""
    parts = patent_name.strip().split()
    if len(parts) < 2:
        return patent_name.title()
    last = parts[0].replace("-", " ").title()
    rest = " ".join(p.title() for p in parts[1:])
    return f"{rest} {last}".strip()


def _first_specialty(row: dict[str, str]) -> str:
    specs = [s.strip() for s in (row.get("required_specialties") or "").split("|") if s.strip()]
    return specs[0].title() if specs else ""


def _align_lead_from_inventors(row: dict[str, str]) -> bool:
    """Replace placeholder physician leads with first patent inventor."""
    case_id = row.get("case_id", "")
    if case_id in PHYSICIAN_FIXES:
        return False
    lead = (row.get("physician_lead_name") or "").upper()
    if lead and lead not in PLACEHOLDER_LEADS:
        return False
    inventors = [x.strip() for x in (row.get("inventors") or "").split("|") if x.strip()]
    if not inventors:
        return False
    row["physician_lead_name"] = _inventor_display_name(inventors[0])
    if not (row.get("physician_lead_institution") or "").strip():
        row["physician_lead_institution"] = (
            row.get("ri_institution") or row.get("company") or ""
        )
    if not (row.get("physician_lead_specialty") or "").strip():
        row["physician_lead_specialty"] = _first_specialty(row)
    return True


def _fill_lead_metadata(row: dict[str, str]) -> bool:
    changed = False
    if (row.get("physician_lead_name") or "").strip():
        if not (row.get("physician_lead_institution") or "").strip():
            row["physician_lead_institution"] = (
                row.get("ri_institution") or row.get("company") or ""
            )
            changed = True
        if not (row.get("physician_lead_specialty") or "").strip():
            spec = _first_specialty(row)
            if spec:
                row["physician_lead_specialty"] = spec
                changed = True
    return changed


def _fix_indication(row: dict[str, str]) -> bool:
    ind = (row.get("indication") or "").strip()
    if ind != GENERIC_INDICATION:
        return False
    title = (row.get("title_clean") or row.get("display_name") or "").strip()
    if title:
        row["indication"] = title
        return True
    return False


def _fix_clinical_path_notes(row: dict[str, str]) -> bool:
    notes = row.get("clinical_path_notes") or ""
    if "trial template auto-matched" not in notes.lower():
        return False
    row["clinical_path_notes"] = (
        "Clinical path draft — confirm trial design, PI, and NCT fit before approval."
    )
    return True


def _fix_ri_operating_comps(row: dict[str, str]) -> bool:
    changed = False
    for prefix in COMP_PREFIXES:
        if (row.get(f"{prefix}type") or "") == "ri_operating":
            row[f"{prefix}type"] = "incumbent"
            changed = True
    return changed


def _title_case_company(assignee: str) -> str:
    key = assignee.strip().upper()
    if key in ASSIGNEE_TO_RI_INSTITUTION:
        return ASSIGNEE_TO_RI_INSTITUTION[key]
    # Title-case fallback
    return assignee.strip().title()


def _normalize_supporters(value: str) -> str:
    if not value.strip():
        return ""
    lines = []
    for line in value.replace("\r", "").split("\n"):
        line = line.strip()
        if not line:
            continue
        parts = line.split("|")
        if parts and parts[0].startswith("npi_"):
            parts[0] = parts[0][4:]
        lines.append("|".join(parts))
    return "\n".join(lines)


def _infer_company(row: dict[str, str]) -> str:
    existing = (row.get("company") or "").strip()
    if existing and existing.upper() not in {"TBD", "UNKNOWN"}:
        return existing
    assignee = (row.get("assignee_company") or "").strip()
    if assignee:
        return _title_case_company(assignee)
    return existing


def _infer_ri_institution(row: dict[str, str]) -> str:
    existing = (row.get("ri_institution") or "").strip()
    assignee = (row.get("assignee_company") or "").strip().upper()
    if assignee in ASSIGNEE_TO_RI_INSTITUTION:
        return ASSIGNEE_TO_RI_INSTITUTION[assignee]
    # Person name heuristic: no "University", "Hospital", etc.
    if existing and not re.search(
        r"university|hospital|noramco|rhodes|purdue|institute|college",
        existing,
        re.I,
    ):
        mapped = ASSIGNEE_TO_RI_INSTITUTION.get(assignee)
        if mapped:
            return mapped
    return existing or _title_case_company(row.get("assignee_company", ""))


def remediate_row(row: dict[str, str]) -> list[str]:
    changes: list[str] = []
    case_id = row.get("case_id", "")

    if (row.get("catalog_include") or "").lower() == "false":
        row["ri_notes"] = (row.get("ri_notes") or "").strip()
        if "excluded from catalog" not in row["ri_notes"].lower():
            row["ri_notes"] = (row["ri_notes"] + " [excluded from catalog]").strip()

    company = _infer_company(row)
    if company != (row.get("company") or ""):
        row["company"] = company
        changes.append("company")

    ri_inst = _infer_ri_institution(row)
    if ri_inst and ri_inst != (row.get("ri_institution") or ""):
        row["ri_institution"] = ri_inst
        changes.append("ri_institution")

    for col in SUGGEST_PUB_COLUMNS:
        if (row.get(col) or "").strip():
            row[col] = ""
            changes.append(f"cleared:{col}")

    supporters = _normalize_supporters(row.get("physician_supporters") or "")
    if supporters != (row.get("physician_supporters") or ""):
        row["physician_supporters"] = supporters
        changes.append("physician_supporters")

    if case_id in PHYSICIAN_FIXES:
        for k, v in PHYSICIAN_FIXES[case_id].items():
            if row.get(k) != v:
                row[k] = v
                changes.append(k)
    elif _align_lead_from_inventors(row):
        changes.append("physician_lead_from_inventor")
    elif _fill_lead_metadata(row):
        changes.append("physician_lead_metadata")

    if _fix_indication(row):
        changes.append("indication")

    if _fix_clinical_path_notes(row):
        changes.append("clinical_path_notes")

    if _fix_ri_operating_comps(row):
        changes.append("comp_type_ri_operating")

    if case_id in COMP_FIXES:
        for prefix, patch in COMP_FIXES[case_id].items():
            for k, v in patch.items():
                if row.get(k) != v:
                    row[k] = v
                    changes.append(k)

    if case_id in CASE_FIELD_PATCHES:
        for k, v in CASE_FIELD_PATCHES[case_id].items():
            if row.get(k) != v:
                row[k] = v
                changes.append(k)

    tier_c_changes = _apply_tier_c_opioid_api(row)
    changes.extend(tier_c_changes)

    # Strip npi_ prefix on lead NPI if present
    npi = (row.get("physician_lead_npi") or "").strip()
    if npi.startswith("npi_"):
        row["physician_lead_npi"] = npi[4:]
        changes.append("physician_lead_npi")

    if fill_brown_profile_url(row):
        changes.append("physician_lead_profile_url")

    apply_finance_defaults(row)
    if (row.get("review_status") or "").lower() != "approved":
        thesis = build_thesis(row)
        if thesis != (row.get("investment_thesis") or ""):
            row["investment_thesis"] = thesis
            changes.append("investment_thesis")

    row["last_refreshed_at"] = date.today().isoformat()
    row["enrichment_status"] = "remediated_web_pass_v2"
    return changes


def remediate(path: Path = CASES_CSV) -> tuple[int, int]:
    rows = load_cases(path)
    touched = 0
    for row in rows:
        if remediate_row(row):
            touched += 1
    write_cases(rows, path)
    return len(rows), touched


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--path", type=Path, default=CASES_CSV)
    args = parser.parse_args()
    total, touched = remediate(args.path)
    print(f"Remediated {touched}/{total} rows -> {args.path}")


if __name__ == "__main__":
    main()
