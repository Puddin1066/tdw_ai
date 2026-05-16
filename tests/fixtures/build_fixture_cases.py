#!/usr/bin/env python3
"""Generate complete fixture case packets and copy to web/public/data/cases/."""

from __future__ import annotations

import json
import shutil
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

REPO_ROOT = Path(__file__).resolve().parents[2]
FIXTURE_ROOT = REPO_ROOT / "tests" / "fixtures" / "cases"
WEB_ROOT = REPO_ROOT / "web" / "public" / "data" / "cases"

GENERATED_AT = "2026-05-15T12:00:00Z"
SCHEMA_VERSION = "v0.5"

REQUIRED_JSON_ARTIFACTS = [
    "source_manifest.json",
    "normalized_entities.json",
    "literature_records.json",
    "clinical_trials.json",
    "target_biology.json",
    "evidence_table.json",
    "diligence_report.json",
    "risk_map.json",
    "knowledge_graph.json",
    "eval_results.json",
]

REQUIRED_ALL_ARTIFACTS = [
    "metadata.yaml",
    *REQUIRED_JSON_ARTIFACTS,
    "diligence_report.md",
]


def utc_now_iso() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def provenance(
    generated_by: str,
    input_artifacts: list[str] | None = None,
    *,
    model_provider: str | None = None,
    model_name: str | None = None,
    prompt_template: str | None = None,
) -> dict[str, Any]:
    return {
        "generated_by": generated_by,
        "generated_at": GENERATED_AT,
        "input_artifacts": input_artifacts or [],
        "model_provider": model_provider,
        "model_name": model_name,
        "prompt_template": prompt_template,
        "prompt_hash": None,
        "schema_version": SCHEMA_VERSION,
    }


def wrap(artifact_type: str, case_id: str, data: Any, prov: dict[str, Any]) -> dict[str, Any]:
    return {
        "artifact_type": artifact_type,
        "case_id": case_id,
        "schema_version": SCHEMA_VERSION,
        "generated_at": GENERATED_AT,
        "provenance": prov,
        "data": data,
    }


def literature_record(
    pmid: str,
    title: str,
    *,
    abstract: str,
    journal: str,
    year: int,
    authors: list[str],
    doi: str | None = None,
) -> dict[str, Any]:
    return {
        "source_record_id": f"pubmed:{pmid}",
        "source_type": "literature",
        "source_name": "PubMed",
        "title": title,
        "abstract": abstract,
        "authors": authors,
        "journal": journal,
        "publication_year": year,
        "doi": doi,
        "pmid": pmid,
        "url": f"https://pubmed.ncbi.nlm.nih.gov/{pmid}/",
        "publication_date": f"{year}-06-01",
        "retrieved_at": GENERATED_AT,
        "raw_record_ref": f"raw/pubmed_raw.json#records/{pmid}",
    }


def trial_record(
    nct_id: str,
    title: str,
    *,
    phase: str,
    status: str,
    sponsor: str,
    interventions: list[str],
    conditions: list[str],
    start_date: str,
) -> dict[str, Any]:
    return {
        "source_record_id": f"clinicaltrials:{nct_id}",
        "source_type": "clinical_trial",
        "source_name": "ClinicalTrials.gov",
        "nct_id": nct_id,
        "title": title,
        "phase": phase,
        "overall_status": status,
        "sponsor": sponsor,
        "interventions": interventions,
        "conditions": conditions,
        "start_date": start_date,
        "completion_date": None,
        "url": f"https://clinicaltrials.gov/study/{nct_id}",
        "retrieved_at": GENERATED_AT,
        "raw_record_ref": f"raw/clinicaltrials_raw.json#records/{nct_id}",
    }


def entity(
    entity_id: str,
    entity_type: str,
    canonical_name: str,
    display_name: str,
    *,
    aliases: list[str] | None = None,
    source_record_ids: list[str] | None = None,
    confidence: float = 0.95,
    external_ids: dict[str, str | None] | None = None,
) -> dict[str, Any]:
    base_ids = {
        "entrez": None,
        "ensembl": None,
        "uniprot": None,
        "wikidata": None,
        "chembl": None,
        "mondo": None,
        "mesh": None,
    }
    if external_ids:
        base_ids.update(external_ids)
    return {
        "entity_id": entity_id,
        "entity_type": entity_type,
        "canonical_name": canonical_name,
        "display_name": display_name,
        "aliases": aliases or [],
        "external_ids": base_ids,
        "source_record_ids": source_record_ids or [],
        "confidence": confidence,
    }


def evidence_row(
    case_id: str,
    idx: int,
    claim_text: str,
    claim_type: str,
    source_record_ids: list[str],
    *,
    support_status: str = "supported",
    confidence: float = 0.8,
    quoted_text: str,
    limitations: list[str] | None = None,
) -> dict[str, Any]:
    return {
        "evidence_id": f"evidence:{case_id}:{idx:04d}",
        "claim_text": claim_text,
        "claim_type": claim_type,
        "support_status": support_status,
        "confidence": confidence,
        "source_record_ids": source_record_ids,
        "quoted_evidence": [
            {
                "source_record_id": source_record_ids[0],
                "text": quoted_text,
                "location": "abstract",
            }
        ],
        "limitations": limitations or [],
    }


def risk(
    risk_id: str,
    category: str,
    title: str,
    description: str,
    *,
    severity: str,
    confidence: float,
    evidence_ids: list[str],
    inferred: bool = False,
) -> dict[str, Any]:
    return {
        "risk_id": risk_id,
        "category": category,
        "title": title,
        "description": description,
        "severity": severity,
        "confidence": confidence,
        "evidence_ids": evidence_ids,
        "inferred": inferred,
    }


CASE_DEFINITIONS: dict[str, dict[str, Any]] = {
    "sting_pdac": {
        "display_name": "STING / Pancreatic Cancer",
        "target": {"name": "STING", "aliases": ["TMEM173", "Stimulator of Interferon Genes"]},
        "indication": {"name": "pancreatic cancer", "aliases": ["PDAC", "pancreatic ductal adenocarcinoma"]},
        "maturity_stage": "translational",
        "confidence_score": 0.72,
        "evidence_density": "high",
        "top_risk": "Limited clinical efficacy data for STING agonists in PDAC",
        "mock_banner": True,
        "rich": True,
    },
    "parp_breast": {
        "display_name": "PARP / Breast Cancer",
        "target": {"name": "PARP1", "aliases": ["PARP", "poly(ADP-ribose) polymerase 1"]},
        "indication": {"name": "breast cancer", "aliases": ["HR-deficient breast cancer", "BRCA-mutant breast cancer"]},
        "maturity_stage": "clinical",
        "confidence_score": 0.88,
        "evidence_density": "high",
        "top_risk": "Resistance mechanisms after PARP inhibitor exposure",
        "mock_banner": False,
        "rich": False,
    },
    "tau_alzheimers": {
        "display_name": "tau / Alzheimer's Disease",
        "target": {"name": "tau", "aliases": ["MAPT", "microtubule-associated protein tau"]},
        "indication": {"name": "Alzheimer's disease", "aliases": ["AD", "Alzheimer disease"]},
        "maturity_stage": "clinical",
        "confidence_score": 0.65,
        "evidence_density": "medium",
        "top_risk": "Mixed Phase 2/3 outcomes for anti-tau modalities",
        "mock_banner": False,
        "rich": False,
    },
    "iaip_sepsis": {
        "display_name": "IAIP / Sepsis",
        "target": {"name": "IAIP", "aliases": ["inter-alpha inhibitor proteins", "ITIH3", "ITIH4"]},
        "indication": {"name": "sepsis", "aliases": ["septic shock", "severe sepsis"]},
        "maturity_stage": "translational",
        "confidence_score": 0.58,
        "evidence_density": "medium",
        "top_risk": "Heterogeneous sepsis populations and endpoint variability",
        "mock_banner": False,
        "rich": False,
    },
}


def build_sting_pdac(case_id: str, meta: dict[str, Any]) -> dict[str, Any]:
    """MOCK/SYNTHETIC fixture content for demo — not live connector output."""
    pmids = ["38123456", "37234567", "36345678", "35456789", "34567890"]
    ncts = ["NCT05234567", "NCT04890123", "NCT04123456"]

    lit = [
        literature_record(
            pmids[0],
            "STING pathway activation remodels the pancreatic ductal adenocarcinoma immune microenvironment",
            abstract=(
                "Synthetic abstract (fixture): Pharmacologic STING agonism increased type I interferon "
                "signatures and CD8+ T-cell infiltration in syngeneic PDAC models, with modest tumor growth delay."
            ),
            journal="Cancer Immunology Research (fixture)",
            year=2024,
            authors=["Chen L", "Patel R", "Nguyen T"],
            doi="10.1234/fixture.2024.001",
        ),
        literature_record(
            pmids[1],
            "TMEM173 (STING) expression correlates with interferon-stimulated gene programs in PDAC cohorts",
            abstract=(
                "Synthetic abstract (fixture): Analysis of resected PDAC specimens linked higher TMEM173 "
                "expression to interferon-stimulated gene enrichment and tertiary lymphoid structure proximity."
            ),
            journal="Clinical Cancer Research (fixture)",
            year=2023,
            authors=["Williams K", "Garcia M"],
            doi="10.1234/fixture.2023.002",
        ),
        literature_record(
            pmids[2],
            "cGAS-STING innate sensing in pancreatic stellate cells modulates fibrosis and T-cell exclusion",
            abstract=(
                "Synthetic abstract (fixture): Stromal cGAS-STING signaling influenced collagen deposition "
                "and spatial T-cell exclusion in organotypic PDAC cultures."
            ),
            journal="Nature Communications (fixture)",
            year=2022,
            authors=["Kim S", "O'Brien P"],
        ),
        literature_record(
            pmids[3],
            "Intratumoral STING agonist delivery combined with anti-PD-1 in advanced pancreatic cancer: early signals",
            abstract=(
                "Synthetic abstract (fixture): A small early-phase cohort reported immune activation biomarkers "
                "but limited objective response rate as monotherapy."
            ),
            journal="Journal for ImmunoTherapy of Cancer (fixture)",
            year=2025,
            authors=["Hoffman D", "Lee A"],
        ),
        literature_record(
            pmids[4],
            "Biomarker strategies for STING pathway modulation in solid tumors including PDAC",
            abstract=(
                "Synthetic abstract (fixture): Review of pharmacodynamic readouts (IFN gene signatures, "
                "cytokines) and tumor STING expression as enrichment hypotheses."
            ),
            journal="Trends in Pharmacological Sciences (fixture)",
            year=2024,
            authors=["Rao J", "Singh N"],
        ),
    ]

    trials = [
        trial_record(
            ncts[0],
            "Phase 1/2 study of intratumoral STING agonist MK-1454 with pembrolizumab in advanced PDAC",
            phase="Phase 1/Phase 2",
            status="Recruiting",
            sponsor="Merck Sharp & Dohme LLC (fixture)",
            interventions=["MK-1454", "pembrolizumab"],
            conditions=["Pancreatic Ductal Adenocarcinoma"],
            start_date="2024-03-01",
        ),
        trial_record(
            ncts[1],
            "ADU-S100 (MIW815) with chemotherapy in metastatic pancreatic adenocarcinoma",
            phase="Phase 2",
            status="Active, not recruiting",
            sponsor="Novartis Pharmaceuticals (fixture)",
            interventions=["MIW815", "gemcitabine", "nab-paclitaxel"],
            conditions=["Pancreatic Neoplasms"],
            start_date="2021-08-15",
        ),
        trial_record(
            ncts[2],
            "Systemic STING agonist dose-escalation in solid tumors including pancreatic cancer",
            phase="Phase 1",
            status="Completed",
            sponsor="Academic Consortium (fixture)",
            interventions=["GSK3745417"],
            conditions=["Solid Tumor", "Pancreatic Neoplasms"],
            start_date="2019-01-10",
        ),
    ]

    entities = [
        entity("gene:TMEM173", "gene", "TMEM173", "STING", aliases=meta["target"]["aliases"],
               source_record_ids=[f"pubmed:{pmids[0]}"], external_ids={"entrez": "340061"}),
        entity("disease:MONDO_0007893", "disease", "pancreatic ductal adenocarcinoma", "PDAC",
               aliases=meta["indication"]["aliases"], source_record_ids=[f"pubmed:{pmids[1]}"],
               external_ids={"mondo": "MONDO:0007893"}),
        entity("pathway:CGAS_STING", "pathway", "cGAS-STING signaling", "cGAS-STING pathway",
               aliases=["innate DNA sensing"], source_record_ids=[f"pubmed:{pmids[2]}"], confidence=0.9),
        entity("compound:MK-1454", "compound", "MK-1454", "MK-1454 (STING agonist)",
               aliases=["intratumoral STING agonist"], source_record_ids=[f"clinicaltrials:{ncts[0]}"],
               external_ids={"chembl": "CHEMBL_FIXTURE_MK1454"}),
        entity("biomarker:IFN_SIGNATURE", "biomarker", "interferon-stimulated gene signature", "IFN gene signature",
               source_record_ids=[f"pubmed:{pmids[4]}"], confidence=0.85),
        entity(f"clinical_trial:{ncts[0]}", "clinical_trial", ncts[0], ncts[0],
               source_record_ids=[f"clinicaltrials:{ncts[0]}"]),
        entity(f"publication:{pmids[0]}", "publication", pmids[0], pmids[0],
               source_record_ids=[f"pubmed:{pmids[0]}"]),
    ]

    evidence = [
        evidence_row(
            case_id, 1,
            "STING (TMEM173) agonism can induce type I interferon programs in preclinical PDAC models.",
            "mechanistic", [f"pubmed:{pmids[0]}"], confidence=0.84,
            quoted_text="STING agonism increased type I interferon signatures in syngeneic PDAC models.",
            limitations=["preclinical models only", "MOCK/SYNTHETIC fixture data"],
        ),
        evidence_row(
            case_id, 2,
            "Higher TMEM173 expression in resected PDAC correlates with interferon-stimulated gene enrichment.",
            "biomarker", [f"pubmed:{pmids[1]}"], confidence=0.78,
            quoted_text="TMEM173 expression linked to ISG enrichment in PDAC cohorts.",
            limitations=["retrospective cohort", "MOCK/SYNTHETIC fixture data"],
        ),
        evidence_row(
            case_id, 3,
            "Stromal cGAS-STING activity may influence fibrosis and T-cell exclusion in PDAC.",
            "translational", [f"pubmed:{pmids[2]}"], confidence=0.71,
            quoted_text="Stromal STING signaling influenced collagen deposition and T-cell exclusion.",
            limitations=["organotypic cultures", "MOCK/SYNTHETIC fixture data"],
        ),
        evidence_row(
            case_id, 4,
            f"Early-phase trial {ncts[0]} is evaluating intratumoral STING agonist MK-1454 with pembrolizumab in advanced PDAC.",
            "clinical", [f"clinicaltrials:{ncts[0]}"], confidence=0.92,
            quoted_text="Phase 1/2 study of MK-1454 with pembrolizumab in advanced PDAC.",
        ),
        evidence_row(
            case_id, 5,
            "Objective response rates for STING monotherapy in PDAC have been limited in early clinical reports.",
            "clinical", [f"pubmed:{pmids[3]}"], confidence=0.68, support_status="partially_supported",
            quoted_text="Immune activation biomarkers reported with limited objective response rate.",
            limitations=["small cohort", "MOCK/SYNTHETIC fixture data"],
        ),
        evidence_row(
            case_id, 6,
            "IFN gene signatures and tumor STING expression are proposed pharmacodynamic and enrichment biomarkers.",
            "biomarker", [f"pubmed:{pmids[4]}"], confidence=0.75,
            quoted_text="Pharmacodynamic readouts include IFN gene signatures and tumor STING expression.",
        ),
    ]

    biology = [
        {
            "source_record_id": "opentargets:ENSG00000184584",
            "source_type": "target_biology",
            "source_name": "Open Targets",
            "target_id": "ENSG00000184584",
            "target_symbol": "TMEM173",
            "disease_id": "EFO_0002618",
            "disease_name": "pancreatic carcinoma",
            "association_score": 0.42,
            "mechanism_summary": "Innate immune DNA sensing; type I interferon induction (fixture).",
            "retrieved_at": GENERATED_AT,
            "raw_record_ref": "raw/opentargets_raw.json#records/0",
        },
        {
            "source_record_id": "chembl:CHEMBL_FIXTURE_MK1454",
            "source_type": "compound",
            "source_name": "ChEMBL",
            "molecule_id": "CHEMBL_FIXTURE_MK1454",
            "preferred_name": "MK-1454",
            "mechanism": "STING agonist",
            "target_id": "TMEM173",
            "activity_summary": "Synthetic fixture entry — preclinical STING agonist.",
            "retrieved_at": GENERATED_AT,
            "raw_record_ref": "raw/chembl_raw.json#records/0",
        },
    ]

    risks = [
        risk("risk:sting_pdac:001", "clinical", "Limited single-agent efficacy in PDAC",
             "Early clinical signals show immune activation but modest ORR; combination strategies likely required.",
             severity="high", confidence=0.8, evidence_ids=["evidence:sting_pdac:0005"]),
        risk("risk:sting_pdac:002", "translational", "Tumor microenvironment heterogeneity",
             "Fibrotic, immunosuppressive PDAC TME may blunt STING agonist activity.",
             severity="high", confidence=0.77, evidence_ids=["evidence:sting_pdac:0003"]),
        risk("risk:sting_pdac:003", "biomarker", "Uncertain patient selection biomarkers",
             "IFN signatures and STING expression lack prospective validation as enrichment markers.",
             severity="medium", confidence=0.7, evidence_ids=["evidence:sting_pdac:0006"], inferred=True),
        risk("risk:sting_pdac:004", "safety", "Systemic interferon-related toxicity",
             "Class risk of cytokine-mediated adverse events with systemic STING agonism.",
             severity="medium", confidence=0.65, evidence_ids=[], inferred=True),
        risk("risk:sting_pdac:005", "competition", "Crowded IO combination landscape in PDAC",
             "Multiple chemo-IO and innate immune approaches compete for similar patient populations.",
             severity="medium", confidence=0.6, evidence_ids=["evidence:sting_pdac:0004"], inferred=True),
    ]

    graph_nodes = [
        {"node_id": "gene:TMEM173", "label": "STING", "node_type": "gene"},
        {"node_id": "disease:MONDO_0007893", "label": "PDAC", "node_type": "disease"},
        {"node_id": "pathway:CGAS_STING", "label": "cGAS-STING", "node_type": "pathway"},
        {"node_id": "compound:MK-1454", "label": "MK-1454", "node_type": "compound"},
        {"node_id": f"clinical_trial:{ncts[0]}", "label": ncts[0], "node_type": "clinical_trial"},
        {"node_id": f"publication:{pmids[0]}", "label": f"PMID {pmids[0]}", "node_type": "publication"},
    ]
    graph_edges = [
        {"edge_id": "edge:001", "source": "gene:TMEM173", "target": "pathway:CGAS_STING", "relationship": "part_of"},
        {"edge_id": "edge:002", "source": "pathway:CGAS_STING", "target": "disease:MONDO_0007893", "relationship": "implicated_in"},
        {"edge_id": "edge:003", "source": "compound:MK-1454", "target": "gene:TMEM173", "relationship": "agonizes"},
        {"edge_id": "edge:004", "source": f"clinical_trial:{ncts[0]}", "target": "compound:MK-1454", "relationship": "tests"},
        {"edge_id": "edge:005", "source": f"publication:{pmids[0]}", "target": "gene:TMEM173", "relationship": "studies"},
    ]

    conclusion = (
        "MOCK/SYNTHETIC diligence snapshot: STING (TMEM173) pathway modulation shows credible innate immune "
        "activation in preclinical PDAC and early clinical biomarker signals, but translational risk remains high "
        "due to immunosuppressive TME, unvalidated enrichment biomarkers, and limited monotherapy efficacy. "
        "Combination and localized delivery strategies appear most plausible near term."
    )

    return {
        "literature": lit,
        "trials": trials,
        "entities": entities,
        "evidence": evidence,
        "biology": biology,
        "risks": risks,
        "graph_nodes": graph_nodes,
        "graph_edges": graph_edges,
        "conclusion": conclusion,
        "executive_summary": conclusion,
        "pmids": pmids,
        "ncts": ncts,
    }


def build_parp_breast(case_id: str, meta: dict[str, Any]) -> dict[str, Any]:
    pmids = ["30111222", "29222333", "28333444"]
    ncts = ["NCT02000622", "NCT01945775"]

    lit = [
        literature_record(
            pmids[0],
            "PARP inhibition and synthetic lethality in BRCA-mutant breast cancer",
            abstract="Fixture: PARP trapping in HR-deficient cells leads to synthetic lethality; olaparib approved in gBRCA-mutant HER2-negative breast cancer.",
            journal="Nature Reviews Cancer (fixture)",
            year=2020,
            authors=["Lord CJ", "Ashworth A"],
        ),
        literature_record(
            pmids[1],
            "Resistance to PARP inhibitors in breast cancer: mechanisms and combinations",
            abstract="Fixture: Restoration of HR repair, drug efflux, and replication fork protection contribute to acquired resistance.",
            journal="Cancer Discovery (fixture)",
            year=2019,
            authors=["Murai J", "Das BB"],
        ),
        literature_record(
            pmids[2],
            "Talazoparib versus chemotherapy in advanced BRCA-mutant breast cancer (EMBRACA)",
            abstract="Fixture: Talazoparib improved PFS versus physician's choice chemotherapy in gBRCA-mutant advanced breast cancer.",
            journal="New England Journal of Medicine (fixture)",
            year=2018,
            authors=["Litton JK", "Rugo HS"],
            doi="10.1056/fixture.embraca",
        ),
    ]
    trials = [
        trial_record(
            ncts[0],
            "Olaparib as adjuvant treatment in patients with germline BRCA-mutated breast cancer (OlympiA)",
            phase="Phase 3",
            status="Completed",
            sponsor="AstraZeneca (fixture)",
            interventions=["olaparib"],
            conditions=["Breast Cancer", "BRCA Mutation"],
            start_date="2014-06-01",
        ),
        trial_record(
            ncts[1],
            "Talazoparib in patients with advanced breast cancer and germline BRCA mutation (EMBRACA)",
            phase="Phase 3",
            status="Completed",
            sponsor="Pfizer (fixture)",
            interventions=["talazoparib"],
            conditions=["Breast Neoplasms"],
            start_date="2013-09-01",
        ),
    ]
    entities = [
        entity("gene:PARP1", "gene", "PARP1", "PARP1", aliases=meta["target"]["aliases"],
               source_record_ids=[f"pubmed:{pmids[0]}"], external_ids={"entrez": "142"}),
        entity("disease:breast_cancer", "disease", "breast cancer", "breast cancer",
               aliases=meta["indication"]["aliases"], source_record_ids=[f"pubmed:{pmids[2]}"]),
        entity("compound:olaparib", "compound", "olaparib", "olaparib",
               source_record_ids=[f"clinicaltrials:{ncts[0]}"], external_ids={"chembl": "CHEMBL1237025"}),
        entity("compound:talazoparib", "compound", "talazoparib", "talazoparib",
               source_record_ids=[f"clinicaltrials:{ncts[1]}"]),
        entity(f"clinical_trial:{ncts[0]}", "clinical_trial", ncts[0], ncts[0],
               source_record_ids=[f"clinicaltrials:{ncts[0]}"]),
    ]
    evidence = [
        evidence_row(case_id, 1, "PARP inhibitors exploit synthetic lethality in HR-deficient breast cancer.",
                     "mechanistic", [f"pubmed:{pmids[0]}"], confidence=0.9,
                     quoted_text="PARP trapping leads to synthetic lethality in HR-deficient cells."),
        evidence_row(case_id, 2, "Olaparib demonstrated adjuvant benefit in gBRCA-mutant breast cancer (OlympiA).",
                     "clinical", [f"clinicaltrials:{ncts[0]}"], confidence=0.88,
                     quoted_text="Phase 3 olaparib adjuvant study in germline BRCA-mutated breast cancer."),
        evidence_row(case_id, 3, "Acquired resistance to PARP inhibition involves HR restoration pathways.",
                     "translational", [f"pubmed:{pmids[1]}"], confidence=0.8,
                     quoted_text="Restoration of HR repair contributes to acquired resistance."),
    ]
    biology = [{
        "source_record_id": "opentargets:PARP1_BREAST",
        "source_type": "target_biology",
        "source_name": "Open Targets",
        "target_id": "ENSG00000143799",
        "target_symbol": "PARP1",
        "disease_id": "EFO_0000305",
        "disease_name": "breast carcinoma",
        "association_score": 0.71,
        "mechanism_summary": "DNA damage response; synthetic lethality with BRCA loss (fixture).",
        "retrieved_at": GENERATED_AT,
        "raw_record_ref": "raw/opentargets_raw.json#records/0",
    }]
    risks = [
        risk("risk:parp_breast:001", "clinical", "Acquired PARP inhibitor resistance",
             "HR restoration and fork protection limit durability of benefit.", severity="high", confidence=0.85,
             evidence_ids=["evidence:parp_breast:0003"]),
        risk("risk:parp_breast:002", "competition", "Established PARP inhibitor standards of care",
             "Olaparib and talazoparib set high efficacy bar in gBRCA populations.", severity="medium",
             confidence=0.8, evidence_ids=["evidence:parp_breast:0002"]),
    ]
    return {
        "literature": lit, "trials": trials, "entities": entities, "evidence": evidence,
        "biology": biology, "risks": risks,
        "graph_nodes": [
            {"node_id": "gene:PARP1", "label": "PARP1", "node_type": "gene"},
            {"node_id": "disease:breast_cancer", "label": "breast cancer", "node_type": "disease"},
            {"node_id": "compound:olaparib", "label": "olaparib", "node_type": "compound"},
        ],
        "graph_edges": [
            {"edge_id": "edge:001", "source": "compound:olaparib", "target": "gene:PARP1", "relationship": "inhibits"},
            {"edge_id": "edge:002", "source": "gene:PARP1", "target": "disease:breast_cancer", "relationship": "target_in"},
        ],
        "conclusion": "PARP inhibition is clinically validated in gBRCA-mutant breast cancer; diligence focus shifts to resistance, sequencing, and combination strategies.",
        "executive_summary": "Strong clinical validation with clear resistance and competitive risks.",
        "pmids": pmids, "ncts": ncts,
    }


def build_tau_alzheimers(case_id: str, meta: dict[str, Any]) -> dict[str, Any]:
    pmids = ["40111222", "39222333"]
    ncts = ["NCT04549847", "NCT03446001"]

    lit = [
        literature_record(
            pmids[0],
            "Tau-targeting immunotherapies in Alzheimer's disease: biomarker and clinical update",
            abstract="Fixture: Anti-tau antibodies aim to reduce spread of pathological tau; mixed clinical outcomes across programs.",
            journal="Lancet Neurology (fixture)",
            year=2024,
            authors=["Blennow K", "Zetterberg H"],
        ),
        literature_record(
            pmids[1],
            "MAPT genetics and tau strain diversity in neurodegeneration",
            abstract="Fixture: MAPT haplotypes and post-translational modifications influence tau pathology propagation.",
            journal="Neuron (fixture)",
            year=2023,
            authors=["Goedert M", "Spillantini MG"],
        ),
    ]
    trials = [
        trial_record(
            ncts[0],
            "Study of anti-tau antibody in early Alzheimer's disease",
            phase="Phase 2",
            status="Terminated",
            sponsor="Biogen (fixture)",
            interventions=["gosuranemab"],
            conditions=["Alzheimer Disease"],
            start_date="2020-10-01",
        ),
        trial_record(
            ncts[1],
            "Semorinemab in mild-to-moderate Alzheimer's disease",
            phase="Phase 2",
            status="Completed",
            sponsor="Roche (fixture)",
            interventions=["semorinemab"],
            conditions=["Alzheimer Disease"],
            start_date="2018-02-01",
        ),
    ]
    entities = [
        entity("gene:MAPT", "gene", "MAPT", "tau", aliases=meta["target"]["aliases"],
               source_record_ids=[f"pubmed:{pmids[1]}"], external_ids={"entrez": "4137"}),
        entity("disease:alzheimers", "disease", "Alzheimer's disease", "Alzheimer's disease",
               aliases=meta["indication"]["aliases"], source_record_ids=[f"pubmed:{pmids[0]}"]),
        entity("modality:anti_tau_mab", "modality", "anti-tau monoclonal antibody", "anti-tau mAb",
               source_record_ids=[f"clinicaltrials:{ncts[0]}"]),
    ]
    evidence = [
        evidence_row(case_id, 1, "Pathological tau propagation is a central hypothesis in Alzheimer's progression.",
                     "mechanistic", [f"pubmed:{pmids[1]}"], confidence=0.86,
                     quoted_text="MAPT genetics and tau strain diversity influence pathology propagation."),
        evidence_row(case_id, 2, "Anti-tau antibody programs show heterogeneous Phase 2 outcomes.",
                     "clinical", [f"pubmed:{pmids[0]}"], confidence=0.62, support_status="partially_supported",
                     quoted_text="Mixed clinical outcomes across anti-tau programs."),
        evidence_row(case_id, 3, f"Trial {ncts[0]} (gosuranemab) was terminated in early Alzheimer's disease.",
                     "clinical", [f"clinicaltrials:{ncts[0]}"], confidence=0.9,
                     quoted_text="Phase 2 anti-tau antibody study terminated."),
    ]
    biology = [{
        "source_record_id": "opentargets:MAPT_AD",
        "source_type": "target_biology",
        "source_name": "Open Targets",
        "target_id": "ENSG00000186868",
        "target_symbol": "MAPT",
        "disease_id": "EFO_0000249",
        "disease_name": "Alzheimer disease",
        "association_score": 0.88,
        "mechanism_summary": "Microtubule binding protein; aggregates in neurofibrillary tangles (fixture).",
        "retrieved_at": GENERATED_AT,
        "raw_record_ref": "raw/opentargets_raw.json#records/0",
    }]
    risks = [
        risk("risk:tau_alzheimers:001", "clinical", "Negative or terminated Phase 2 programs",
             "Several anti-tau mAbs failed to show consistent clinical benefit.", severity="high", confidence=0.82,
             evidence_ids=["evidence:tau_alzheimers:0003"]),
        risk("risk:tau_alzheimers:002", "biomarker", "Uncertain tau PET/phospho-tau enrichment",
             "Patient selection by tau biomarkers remains evolving.", severity="medium", confidence=0.65,
             evidence_ids=["evidence:tau_alzheimers:0001"], inferred=True),
    ]
    return {
        "literature": lit, "trials": trials, "entities": entities, "evidence": evidence,
        "biology": biology, "risks": risks,
        "graph_nodes": [
            {"node_id": "gene:MAPT", "label": "tau", "node_type": "gene"},
            {"node_id": "disease:alzheimers", "label": "Alzheimer's", "node_type": "disease"},
            {"node_id": "modality:anti_tau_mab", "label": "anti-tau mAb", "node_type": "modality"},
        ],
        "graph_edges": [
            {"edge_id": "edge:001", "source": "modality:anti_tau_mab", "target": "gene:MAPT", "relationship": "targets"},
            {"edge_id": "edge:002", "source": "gene:MAPT", "target": "disease:alzheimers", "relationship": "implicated_in"},
        ],
        "conclusion": "Tau remains biologically central in AD, but clinical validation for anti-tau modalities is unproven with notable program failures.",
        "executive_summary": "High biological rationale with significant clinical translation risk.",
        "pmids": pmids, "ncts": ncts,
    }


def build_iaip_sepsis(case_id: str, meta: dict[str, Any]) -> dict[str, Any]:
    pmids = ["35111222", "34222333"]
    ncts = ["NCT03034567"]

    lit = [
        literature_record(
            pmids[0],
            "Inter-alpha inhibitor proteins in sepsis: preclinical and early clinical observations",
            abstract="Fixture: IAIP family members modulate protease activity and inflammatory cascades in sepsis models.",
            journal="Critical Care Medicine (fixture)",
            year=2022,
            authors=["Stephens J", "Carroll M"],
        ),
        literature_record(
            pmids[1],
            "Plasma ITIH3/ITIH4 as prognostic markers in septic shock cohorts",
            abstract="Fixture: Lower IAIP levels correlated with organ dysfunction scores in retrospective ICU cohorts.",
            journal="Shock (fixture)",
            year=2021,
            authors=["Zhang Y", "Brown A"],
        ),
    ]
    trials = [
        trial_record(
            ncts[0],
            "IAIP supplementation in patients with septic shock",
            phase="Phase 2",
            status="Unknown status",
            sponsor="Academic Medical Center (fixture)",
            interventions=["inter-alpha inhibitor proteins"],
            conditions=["Sepsis", "Septic Shock"],
            start_date="2019-05-01",
        ),
    ]
    entities = [
        entity("protein:IAIP", "protein", "inter-alpha inhibitor proteins", "IAIP",
               aliases=meta["target"]["aliases"], source_record_ids=[f"pubmed:{pmids[0]}"]),
        entity("gene:ITIH3", "gene", "ITIH3", "ITIH3", source_record_ids=[f"pubmed:{pmids[1]}"]),
        entity("gene:ITIH4", "gene", "ITIH4", "ITIH4", source_record_ids=[f"pubmed:{pmids[1]}"]),
        entity("disease:sepsis", "disease", "sepsis", "sepsis",
               aliases=meta["indication"]["aliases"], source_record_ids=[f"pubmed:{pmids[0]}"]),
    ]
    evidence = [
        evidence_row(case_id, 1, "IAIP modulates protease activity and inflammatory signaling in sepsis models.",
                     "mechanistic", [f"pubmed:{pmids[0]}"], confidence=0.74,
                     quoted_text="IAIP family members modulate protease activity in sepsis models."),
        evidence_row(case_id, 2, "Lower plasma IAIP levels associate with organ dysfunction in septic shock cohorts.",
                     "biomarker", [f"pubmed:{pmids[1]}"], confidence=0.7,
                     quoted_text="Lower IAIP levels correlated with organ dysfunction scores."),
        evidence_row(case_id, 3, f"Phase 2 trial {ncts[0]} evaluates IAIP supplementation in septic shock.",
                     "clinical", [f"clinicaltrials:{ncts[0]}"], confidence=0.75,
                     quoted_text="IAIP supplementation in patients with septic shock."),
    ]
    biology = [{
        "source_record_id": "biothings:IAIP_SEPSIS",
        "source_type": "relationship",
        "source_name": "BioThings",
        "subject": "IAIP",
        "predicate": "associated_with",
        "object": "sepsis",
        "confidence": 0.55,
        "retrieved_at": GENERATED_AT,
        "raw_record_ref": "raw/biothings_raw.json#records/0",
    }]
    risks = [
        risk("risk:iaip_sepsis:001", "clinical", "Endpoint heterogeneity in sepsis trials",
             "Variable mortality and organ failure endpoints complicate trial interpretation.", severity="high",
             confidence=0.78, evidence_ids=["evidence:iaip_sepsis:0003"], inferred=True),
        risk("risk:iaip_sepsis:002", "evidence_gap", "Limited prospective interventional evidence",
             "Most support derives from preclinical and retrospective biomarker studies.", severity="high",
             confidence=0.8, evidence_ids=["evidence:iaip_sepsis:0001"]),
    ]
    return {
        "literature": lit, "trials": trials, "entities": entities, "evidence": evidence,
        "biology": biology, "risks": risks,
        "graph_nodes": [
            {"node_id": "protein:IAIP", "label": "IAIP", "node_type": "protein"},
            {"node_id": "disease:sepsis", "label": "sepsis", "node_type": "disease"},
            {"node_id": "gene:ITIH3", "label": "ITIH3", "node_type": "gene"},
        ],
        "graph_edges": [
            {"edge_id": "edge:001", "source": "protein:IAIP", "target": "disease:sepsis", "relationship": "associated_with"},
            {"edge_id": "edge:002", "source": "gene:ITIH3", "target": "protein:IAIP", "relationship": "encodes_component"},
        ],
        "conclusion": "IAIP biology is plausible in sepsis pathophysiology, but interventional evidence remains early and trial design risk is high.",
        "executive_summary": "Translational hypothesis with biomarker support and limited late-stage clinical validation.",
        "pmids": pmids, "ncts": ncts,
    }


BUILDERS = {
    "sting_pdac": build_sting_pdac,
    "parp_breast": build_parp_breast,
    "tau_alzheimers": build_tau_alzheimers,
    "iaip_sepsis": build_iaip_sepsis,
}


def metadata_yaml(case_id: str, meta: dict[str, Any]) -> str:
    target = meta["target"]
    indication = meta["indication"]
    mock_note = ""
    if meta.get("mock_banner"):
        mock_note = (
            "# MOCK/SYNTHETIC FIXTURE DATA — for demo and CI only; not live connector output.\n"
        )
    return f"""{mock_note}case_id: {case_id}
display_name: {meta['display_name']}
workflow: translational_diligence
version: {SCHEMA_VERSION}
fixture: true
mock_synthetic: {str(meta.get('mock_banner', False)).lower()}

target:
  name: {target['name']}
  canonical_id: null
  aliases:
{chr(10).join('    - ' + a for a in target['aliases'])}

indication:
  name: {indication['name']}
  aliases:
{chr(10).join('    - ' + a for a in indication['aliases'])}

sources:
  pubmed: true
  clinicaltrials: true
  opentargets: true
  chembl: true
  biothings: true
  local_docs: false

limits:
  max_literature_records: 50
  max_trials: 100
  max_evidence_rows: 100

run_mode_defaults:
  fixture_allowed: true
  live_allowed: true

dashboard:
  maturity_stage: {meta['maturity_stage']}
  confidence_score: {meta['confidence_score']}
  evidence_density: {meta['evidence_density']}
  top_risk: "{meta['top_risk']}"

generated_at: {GENERATED_AT}
"""


def diligence_md(case_id: str, meta: dict[str, Any], payload: dict[str, Any]) -> str:
    mock_header = ""
    if meta.get("mock_banner"):
        mock_header = (
            "> **MOCK/SYNTHETIC FIXTURE** — This diligence memo is synthetic demo content "
            "for the translational diligence workbench. Do not cite clinically.\n\n"
        )
    ncts = ", ".join(payload["ncts"])
    pmids = ", ".join(payload["pmids"])
    return f"""{mock_header}# Translational Diligence Memo: {meta['display_name']}

**Case ID:** `{case_id}`  
**Generated:** {GENERATED_AT}  
**Maturity:** {meta['maturity_stage']} | **Confidence:** {meta['confidence_score']:.2f}

## Executive Summary

{payload['executive_summary']}

## Target & Indication

- **Target:** {meta['target']['name']} ({', '.join(meta['target']['aliases'][:2])})
- **Indication:** {meta['indication']['name']}

## Key Evidence Themes

{chr(10).join('- ' + row['claim_text'] for row in payload['evidence'][:4])}

## Clinical Trials Referenced

{ncts}

## Literature Cited

{pmids}

## Top Risks

{chr(10).join('- **' + r['title'] + '** (' + r['category'] + '): ' + r['description'] for r in payload['risks'][:3])}

## Conclusion

{payload['conclusion']}
"""


def raw_connector_samples(case_id: str, meta: dict[str, Any], payload: dict[str, Any]) -> dict[str, str]:
    target = meta["target"]["name"]
    indication = meta["indication"]["name"]
    raw_query = f"({target}) AND ({indication})"
    base = {
        "connector_name": "pubmed",
        "case_id": case_id,
        "mode": "fixture",
        "query": {"target": target, "indication": indication, "raw_query": raw_query},
        "retrieved_at": GENERATED_AT,
        "records": [],
        "errors": [],
        "warnings": ["fixture mode — synthetic raw payload"],
        "provenance": {
            "source_name": "PubMed",
            "source_url": "https://pubmed.ncbi.nlm.nih.gov/",
            "api_endpoint": None,
            "api_version": None,
        },
    }
    pubmed = {**base, "connector_name": "pubmed", "records": payload["literature"]}
    trials = {
        **base,
        "connector_name": "clinicaltrials",
        "records": payload["trials"],
        "provenance": {
            "source_name": "ClinicalTrials.gov",
            "source_url": "https://clinicaltrials.gov/",
            "api_endpoint": "https://clinicaltrials.gov/api/v2/studies",
            "api_version": "2",
        },
    }
    return {
        "pubmed_raw.json": json.dumps(pubmed, indent=2),
        "clinicaltrials_raw.json": json.dumps(trials, indent=2),
        "opentargets_raw.json": json.dumps(
            {**base, "connector_name": "opentargets", "records": [r for r in payload["biology"] if r.get("source_name") == "Open Targets"]},
            indent=2,
        ),
        "chembl_raw.json": json.dumps(
            {**base, "connector_name": "chembl", "records": [r for r in payload["biology"] if r.get("source_name") == "ChEMBL"]},
            indent=2,
        ),
        "biothings_raw.json": json.dumps(
            {**base, "connector_name": "biothings", "records": [r for r in payload["biology"] if r.get("source_name") == "BioThings"]},
            indent=2,
        ),
    }


def build_case(case_id: str) -> None:
    meta = CASE_DEFINITIONS[case_id]
    payload = BUILDERS[case_id](case_id, meta)
    case_dir = FIXTURE_ROOT / case_id
    raw_dir = case_dir / "raw"
    case_dir.mkdir(parents=True, exist_ok=True)
    raw_dir.mkdir(parents=True, exist_ok=True)

    (case_dir / "metadata.yaml").write_text(metadata_yaml(case_id, meta), encoding="utf-8")
    (case_dir / "diligence_report.md").write_text(
        diligence_md(case_id, meta, payload), encoding="utf-8"
    )

    artifacts: dict[str, dict[str, Any]] = {
        "source_manifest.json": wrap(
            "source_manifest",
            case_id,
            {
                "sources": [
                    {
                        "connector_name": "pubmed",
                        "query": payload["literature"][0]["title"][:40] + "...",
                        "retrieved_at": GENERATED_AT,
                        "record_count": len(payload["literature"]),
                        "status": "ok",
                    },
                    {
                        "connector_name": "clinicaltrials",
                        "query": meta["indication"]["name"],
                        "retrieved_at": GENERATED_AT,
                        "record_count": len(payload["trials"]),
                        "status": "ok",
                    },
                    {
                        "connector_name": "opentargets",
                        "query": meta["target"]["name"],
                        "retrieved_at": GENERATED_AT,
                        "record_count": 1,
                        "status": "ok",
                    },
                ],
                "total_records": len(payload["literature"]) + len(payload["trials"]),
            },
            provenance("connectors/aggregate", ["raw/"]),
        ),
        "normalized_entities.json": wrap(
            "normalized_entities",
            case_id,
            {"entities": payload["entities"]},
            provenance("pipeline/normalize_entities.py", ["literature_records.json", "clinical_trials.json"]),
        ),
        "literature_records.json": wrap(
            "literature_records",
            case_id,
            {"records": payload["literature"]},
            provenance("connectors/pubmed.py", ["raw/pubmed_raw.json"]),
        ),
        "clinical_trials.json": wrap(
            "clinical_trials",
            case_id,
            {"trials": payload["trials"]},
            provenance("connectors/clinicaltrials.py", ["raw/clinicaltrials_raw.json"]),
        ),
        "target_biology.json": wrap(
            "target_biology",
            case_id,
            {"records": payload["biology"]},
            provenance("connectors/opentargets.py", ["raw/opentargets_raw.json", "raw/chembl_raw.json"]),
        ),
        "evidence_table.json": wrap(
            "evidence_table",
            case_id,
            {"rows": payload["evidence"]},
            provenance(
                "pipeline/generate_claims.py",
                ["literature_records.json", "clinical_trials.json", "target_biology.json"],
                model_provider="mock",
                model_name="fixture-mock",
                prompt_template="skills/translational_diligence/prompts/claim_extraction.md",
            ),
        ),
        "diligence_report.json": wrap(
            "diligence_report",
            case_id,
            {
                "title": f"Translational Diligence: {meta['display_name']}",
                "mock_synthetic": meta.get("mock_banner", False),
                "executive_summary": payload["executive_summary"],
                "conclusion": payload["conclusion"],
                "confidence_score": meta["confidence_score"],
                "maturity_stage": meta["maturity_stage"],
                "evidence_density": meta["evidence_density"],
                "top_risk": meta["top_risk"],
                "sections": [
                    {
                        "heading": "Target biology",
                        "body": payload["executive_summary"],
                        "cited_evidence_ids": [e["evidence_id"] for e in payload["evidence"][:2]],
                        "cited_pmids": payload["pmids"][:2],
                        "cited_nct_ids": payload["ncts"][:1],
                    },
                    {
                        "heading": "Clinical landscape",
                        "body": payload["conclusion"],
                        "cited_evidence_ids": [e["evidence_id"] for e in payload["evidence"] if e["claim_type"] == "clinical"],
                        "cited_pmids": payload["pmids"],
                        "cited_nct_ids": payload["ncts"],
                    },
                ],
                "key_questions": [
                    "What biomarkers enrich for response?",
                    "What combination partners address TME resistance?",
                    "What is the competitive clinical timeline?",
                ],
            },
            provenance(
                "pipeline/generate_report.py",
                ["evidence_table.json", "clinical_trials.json", "risk_map.json"],
                model_provider="mock",
                model_name="fixture-mock",
                prompt_template="skills/translational_diligence/prompts/report_generation.md",
            ),
        ),
        "risk_map.json": wrap(
            "risk_map",
            case_id,
            {"risks": payload["risks"], "top_risk_id": payload["risks"][0]["risk_id"]},
            provenance(
                "pipeline/generate_risk_map.py",
                ["evidence_table.json", "clinical_trials.json", "target_biology.json"],
                model_provider="mock",
                model_name="fixture-mock",
                prompt_template="skills/translational_diligence/prompts/risk_mapping.md",
            ),
        ),
        "knowledge_graph.json": wrap(
            "knowledge_graph",
            case_id,
            {
                "nodes": payload["graph_nodes"],
                "edges": payload["graph_edges"],
            },
            provenance(
                "pipeline/build_graph.py",
                ["normalized_entities.json", "evidence_table.json"],
            ),
        ),
        "eval_results.json": wrap(
            "eval_results",
            case_id,
            {
                "overall_passed": True,
                "citation_fidelity_score": 0.97 if case_id == "sting_pdac" else 0.95,
                "unsupported_claim_count": 0,
                "hallucinated_trial_count": 0,
                "hallucinated_pmid_count": 0,
                "evidence_coverage_score": 0.85 if meta.get("rich") else 0.75,
                "evaluators": [
                    {
                        "evaluator_name": "citation_fidelity",
                        "case_id": case_id,
                        "passed": True,
                        "score": 0.97,
                        "errors": [],
                        "warnings": [],
                        "checked_artifacts": ["diligence_report.json", "evidence_table.json"],
                    },
                    {
                        "evaluator_name": "unsupported_claims",
                        "case_id": case_id,
                        "passed": True,
                        "score": 1.0,
                        "errors": [],
                        "warnings": [],
                        "checked_artifacts": ["diligence_report.json", "evidence_table.json"],
                    },
                    {
                        "evaluator_name": "trial_hallucination",
                        "case_id": case_id,
                        "passed": True,
                        "score": 1.0,
                        "errors": [],
                        "warnings": [],
                        "checked_artifacts": ["diligence_report.json", "clinical_trials.json"],
                    },
                    {
                        "evaluator_name": "evidence_coverage",
                        "case_id": case_id,
                        "passed": True,
                        "score": 0.85 if meta.get("rich") else 0.75,
                        "errors": [],
                        "warnings": ["fixture mode — coverage is illustrative"],
                        "checked_artifacts": ["evidence_table.json", "literature_records.json"],
                    },
                    {
                        "evaluator_name": "schema_validation",
                        "case_id": case_id,
                        "passed": True,
                        "score": 1.0,
                        "errors": [],
                        "warnings": [],
                        "checked_artifacts": REQUIRED_JSON_ARTIFACTS,
                    },
                    {
                        "evaluator_name": "provenance_completeness",
                        "case_id": case_id,
                        "passed": True,
                        "score": 1.0,
                        "errors": [],
                        "warnings": [],
                        "checked_artifacts": REQUIRED_JSON_ARTIFACTS,
                    },
                ],
            },
            provenance("evals/run_evals.py", REQUIRED_JSON_ARTIFACTS),
        ),
    }

    for name, content in artifacts.items():
        (case_dir / name).write_text(json.dumps(content, indent=2) + "\n", encoding="utf-8")

    for raw_name, raw_body in raw_connector_samples(case_id, meta, payload).items():
        (raw_dir / raw_name).write_text(raw_body + "\n", encoding="utf-8")

    web_case = WEB_ROOT / case_id
    if web_case.exists():
        shutil.rmtree(web_case)
    shutil.copytree(case_dir, web_case)


def main() -> None:
    for case_id in CASE_DEFINITIONS:
        build_case(case_id)
        print(f"Built fixture case: {case_id}")


if __name__ == "__main__":
    main()
