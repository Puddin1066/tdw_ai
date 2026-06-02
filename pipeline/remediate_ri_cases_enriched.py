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
    "auto_brown_university_brain_chemotherapeutic_drug_enhancing_tumors_upt": {
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
}

# Full-row content patches (publications, clinical package, syndicate) — curated primary sources.
CASE_FIELD_PATCHES: dict[str, dict[str, str]] = {
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
        "trial_nct_ids": "",
        "trial_titles": "",
        "trial_phases": "",
        "trial_statuses": "",
        "trial_urls": "",
        "trial_count": "0",
        "suggest_trial_nct_ids": "",
        "suggest_trial_titles": "",
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
        "review_status": "approved",
        "reviewer": "JJR",
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
