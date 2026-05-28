"""Apply web-verified findings for Tier A seed programs, then merge into comparables.csv."""

from __future__ import annotations

import csv
from datetime import date
from pathlib import Path

from pipeline.tier_a.comp_web_review import FINDINGS_CSV, FINDINGS_FIELDS
from pipeline.tier_a import paths as tier_a_paths

# Seed-program comps verified via web search (May 2026).
SEED_WEB_FINDINGS: list[dict[str, str]] = [
    {
        "case_id": "theromics_ri",
        "precedent_rank": "1",
        "precedent_name": "Theromics Inc",
        "action": "verify",
        "validation_status": "verified",
        "value_anchor_usd": "1000000",
        "value_anchor_type": "grant",
        "value_source_url": "https://www.prnewswire.com/news-releases/theromics-inc-receives-national-science-foundation-grant-for-innovative-ablation-therapy-technology-302086925.html",
        "inferred_financing": "NSF STTR Phase II $1M (Mar 2024); prior Phase I; MassVentures START grant",
        "search_notes": "NSF $1M STTR Phase II for HeatSYNC; Brown/RI Hospital spinout.",
    },
    {
        "case_id": "theromics_ri",
        "precedent_rank": "3",
        "precedent_name": "Neuwave (Ethicon/J&J)",
        "action": "skip",
        "validation_status": "suggested",
        "search_notes": "Strategic incumbent; no RI-relevant venture anchor — path comp only.",
    },
    {
        "case_id": "phlip_therapeutics_ri",
        "precedent_rank": "1",
        "precedent_name": "pHLIP Inc",
        "action": "note",
        "validation_status": "estimated",
        "inferred_financing": "Yale University + Pacific Partners investors; URI/Yale/MSK licenses",
        "value_source_url": "https://web.uri.edu/research-admin/university-of-rhode-island-professors-yana-reshetnyak-and-oleg-andreev-transferring-technology-to-the-market/",
        "search_notes": "No disclosed venture round anchor; RI spinout since 2015; clinical validation stage.",
    },
    {
        "case_id": "phlip_therapeutics_ri",
        "precedent_rank": "2",
        "precedent_name": "On Target Laboratories (Cytalux)",
        "action": "verify",
        "validation_status": "verified",
        "value_anchor_usd": "116500000",
        "value_anchor_type": "total_raised",
        "value_source_url": "https://www.prnewswire.com/news-releases/on-target-laboratories-secures-30-million-for-commercialization-of-cytalux-pafolacianine-injection-301989832.html",
        "total_raised_usd_est": "116500000",
        "last_round_usd_est": "30000000",
        "inferred_financing": "$116.5M total raised; $30M Series C Nov 2023 for CYTALUX commercialization",
        "search_notes": "FDA-approved pafolacianine; Series C $30M Nov 2023.",
    },
    {
        "case_id": "phlip_therapeutics_ri",
        "precedent_rank": "3",
        "precedent_name": "Cybrexa (alphalex)",
        "action": "verify",
        "validation_status": "verified",
        "value_anchor_usd": "44400000",
        "value_anchor_type": "total_raised",
        "value_source_url": "https://www.globenewswire.com/news-release/2021/03/10/2190275/0/en/Cybrexa-Therapeutics-Closes-25-Million-Series-B-Financing.html",
        "total_raised_usd_est": "44400000",
        "last_round_usd_est": "25000000",
        "inferred_financing": "$6M seed (2017) + $25M Series B (Mar 2021); alphalex PDC platform; URI-origin pHLIP",
        "search_notes": "Crunchbase-style total ~$44.4M disclosed equity.",
    },
    {
        "case_id": "phlip_therapeutics_ri",
        "precedent_rank": "4",
        "precedent_name": "Indocyanine green (ICG)",
        "action": "skip",
        "validation_status": "suggested",
        "search_notes": "Generic incumbent comparator; no venture anchor.",
    },
    {
        "case_id": "monaghan_sepsis_diagnostic_ri",
        "precedent_rank": "2",
        "precedent_name": "Immunexpress (SeptiCyte)",
        "action": "verify",
        "validation_status": "verified",
        "value_anchor_usd": "46880000",
        "value_anchor_type": "total_raised",
        "value_source_url": "https://www.prnewswire.com/news-releases/immunexpress-announces-closing-of-private-funding-round-300930242.html",
        "total_raised_usd_est": "46880000",
        "inferred_financing": "~$46.9M total raised; FDA-cleared SeptiCyte RAPID on Biocartis Idylla",
        "search_notes": "CB Insights / company profile ~$46.88M total.",
    },
    {
        "case_id": "monaghan_sepsis_diagnostic_ri",
        "precedent_rank": "3",
        "precedent_name": "Presymptom Health (InfectiClear)",
        "action": "verify",
        "validation_status": "verified",
        "value_anchor_usd": "1900000",
        "value_anchor_type": "total_raised",
        "value_source_url": "https://ploughshare.co.uk/mod-spin-out-presymptom-health-raises-1-5m-to-develop-ai-driven-sepsis-and-infection-tests-for-the-nhs/",
        "total_raised_usd_est": "3200000",
        "inferred_financing": "£1.5M follow-on seed+grants (Mar 2024); UKI2S reports ~£3.2M total capital",
        "search_notes": "£1.5M round Mar 2024; USD anchor uses ~$1.9M for £1.5M component.",
    },
    {
        "case_id": "nanode_ri",
        "precedent_rank": "2",
        "precedent_name": "Ionis Pharmaceuticals",
        "action": "verify",
        "validation_status": "verified",
        "value_anchor_usd": "12640000000",
        "value_anchor_type": "market_cap",
        "value_source_url": "https://www.macrotrends.net/stocks/charts/IONS/ionis-pharmaceuticals/market-cap",
        "inferred_financing": "Public NASDAQ IONS; ~$12.6B market cap May 2026",
        "search_notes": "Platform comp for nucleic acid therapeutics.",
    },
    {
        "case_id": "nanode_ri",
        "precedent_rank": "3",
        "precedent_name": "Alnylam Pharmaceuticals",
        "action": "verify",
        "validation_status": "verified",
        "value_anchor_usd": "38920000000",
        "value_anchor_type": "market_cap",
        "value_source_url": "https://stockanalysis.com/stocks/alny/statistics/",
        "inferred_financing": "Public NASDAQ ALNY; ~$38.9B market cap May 2026",
        "search_notes": "RNAi platform delivery comp.",
    },
]


def write_seed_findings() -> Path:
    tier_a_paths.TIER_A_ROOT.mkdir(parents=True, exist_ok=True)
    today = date.today().isoformat()
    rows: list[dict[str, str]] = []
    for partial in SEED_WEB_FINDINGS:
        row = {field: "" for field in FINDINGS_FIELDS}
        row.update(partial)
        row["reviewer"] = "run_seeds_web_review"
        row["reviewed_at"] = today
        rows.append(row)
    with FINDINGS_CSV.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=FINDINGS_FIELDS)
        writer.writeheader()
        writer.writerows(rows)
    return FINDINGS_CSV


def main() -> int:
    path = write_seed_findings()
    print(f"Wrote {len(SEED_WEB_FINDINGS)} seed findings -> {path}")
    print("Run: python3 -m pipeline.tier_a.comp_web_review apply && npm run tier:a:build")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
