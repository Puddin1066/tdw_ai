"""Scan uncatalogued RI patent opportunities for Tier A promotion candidates.

Writes:
  data/ri/ri_uncat_patent_scan.csv — one row per patent asset not in catalog
  data/ri/ri_uncat_promotion_shortlist.csv — scored programs (one row per case_id)
  data/ri/ri_uncat_physician_match_suggestions.csv — top physician matches for shortlist
  data/ri/RI_UNCAT_TIER_A_RECOMMENDATIONS.md — human review packet
"""

from __future__ import annotations

import argparse
import csv
import re
from collections import defaultdict
from dataclasses import dataclass, field
from pathlib import Path

from pipeline.physician_assignment import (
    clear_assignment_cache,
    physician_match_for_case,
)
from pipeline.ri_case_merges import CASE_MERGE_ALIASES, MERGE_EXCLUSION_NOTE
from pipeline.ri_precedent_catalog import CASE_PRECEDENT_GROUP, PHARMA_PREFIXES
from pipeline.types import repo_root

DATA = repo_root() / "data" / "ri"
ENRICH = DATA / "ri_opportunities_catalog_enrichment.csv"
OPPS = DATA / "ri_opportunities.csv"
IP = DATA / "ri_ip_assets.csv"

SCAN_CSV = DATA / "ri_uncat_patent_scan.csv"
SHORTLIST_CSV = DATA / "ri_uncat_promotion_shortlist.csv"
MATCH_CSV = DATA / "ri_uncat_physician_match_suggestions.csv"
REPORT_MD = DATA / "RI_UNCAT_TIER_A_RECOMMENDATIONS.md"

# Explicitly flagged in seed curation notes (boost score).
SEED_NOTED_CASES = frozenset(
    {
        "auto_rhode_island_activity_brain_detecting_pain_using",
        "auto_rhode_island_management_pain",
        "auto_rhode_island_cells_delivery_diseased_environmentally_marking",
    }
)

# Likely merge into existing catalog program — do not promote as standalone Tier A.
MERGE_INTO: dict[str, str] = {
    **CASE_MERGE_ALIASES,
    "auto_rhode_island_acceleration_delivery_drug_thermal": "theromics_ri",
    "auto_rhode_island_ablation_enhanced_enhancement_heat_image_substra": "theromics_ri",
    "auto_rhode_island_antibodies_covid_deep_predicting_sequencing_surv": "monaghan_sepsis_diagnostic_ri",
    "auto_rhode_island_biomedical_contact_prepared_sensors_surfaces_usa": "auto_rhode_island_biomedical_detecting_electrical_electrode_locali",
    "auto_rhode_island_biomedical_electrode": "auto_rhode_island_biomedical_detecting_electrical_electrode_locali",
    "auto_brown_university_against_antibodies_bispecific_cells_chi3l1_ctla4": "auto_brown_university_anti_antibody_bispecific_chi3l1_reagents_relatin",
    "auto_brown_university_anti_antibody_chi3l1_disease_fatty_liver_metabol": "auto_brown_university_anti_antibody_bispecific_chi3l1_reagents_relatin",
    "auto_brown_university_anti_antibody_chi3l1_fibrosis_reagents_relating": "auto_brown_university_anti_antibody_bispecific_chi3l1_reagents_relatin",
    "auto_rhode_island_anti_antibodies_chi3l1_complications_detection_d": "auto_brown_university_anti_antibody_bispecific_chi3l1_reagents_relatin",
}

THEME_PATTERNS: dict[str, str] = {
    "neuro_device": r"brain|neural|eeg|dbs|catheter|electrode|bci|implant|neuro|stimulat",
    "diagnostic_dx": r"diagnostic|biomarker|assay|sequencing|rna|sepsis|infect|detect",
    "oncology_ther": r"cancer|tumor|chemo|immuno|pd-1|car-t|microrna",
    "pain_digital": r"pain|analgesic|neurofeedback|cbt",
    "ablation_thermal": r"ablat|thermal|rf |microwave|hypertherm",
    "drug_delivery": r"delivery|nanopiece|sirna|mrna|lipid|nanoparticle",
    "pharma_chem": r"opioid|morphine|cod|buprenorphine|synthesis|catalyst|hydrochloride",
    "wound_surgical": r"wound|surgical|graft|ligament|orthopedic|acl",
    "medical_device_kw": r"device|prosthetic|catheter|sensor|implantable",
}


@dataclass
class ProgramScore:
    case_id: str
    rubric_score: int = 0
    themes: list[str] = field(default_factory=list)
    merge_target: str = ""
    seed_noted: bool = False
    ri_owner: bool = False
    opportunity_type: str = ""
    primary_lens_id: str = ""
    primary_title: str = ""
    owners: str = ""
    top_physician_score: int = 0
    top_physician_name: str = ""
    top_physician_specialty: str = ""
    staffing_score: float = 0.0
    recommendation: str = ""
    rationale: str = ""


def _read_csv(path: Path) -> list[dict[str, str]]:
    with path.open(newline="", encoding="utf-8") as handle:
        return list(csv.DictReader(handle))


def _write_csv(path: Path, fieldnames: list[str], rows: list[dict[str, str]]) -> None:
    with path.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=fieldnames, extrasaction="ignore")
        writer.writeheader()
        writer.writerows(rows)


def _catalog_lens_ids(enrich_rows: list[dict[str, str]]) -> set[str]:
    lens: set[str] = set()
    for row in enrich_rows:
        if (row.get("primary_lens_id") or "").strip():
            lens.add(row["primary_lens_id"].strip())
        for part in (row.get("ip_lens_ids") or "").split("|"):
            if part.strip():
                lens.add(part.strip())
    return lens


def _theme_hits(text: str) -> list[str]:
    t = text.lower()
    return [name for name, pat in THEME_PATTERNS.items() if re.search(pat, t)]


def _ri_owner(owners: str) -> bool:
    u = owners.upper()
    return any(
        x in u
        for x in (
            "RHODE ISLAND",
            "BROWN UNIVERSITY",
            "UNIVERSITY OF RHODE",
            "LIFESPAN",
            "URI",
        )
    )


def _is_pharma_prefix(case_id: str) -> bool:
    return any(case_id.startswith(p) for p in PHARMA_PREFIXES)


def _score_program(
    case_id: str,
    patents: list[dict[str, str]],
    opp: dict[str, str],
    *,
    in_catalog_lens: set[str],
) -> ProgramScore | None:
    if not patents:
        return None
    primary = patents[0]
    title_blob = " ".join(
        p.get("title", "") + " " + p.get("cpc_classifications", "") for p in patents
    )
    themes = _theme_hits(title_blob)
    owners = primary.get("owners", "") or primary.get("applicants", "")
    ri = _ri_owner(owners)
    otype = (opp.get("opportunity_type") or "platform").strip().lower()

    if all((p.get("lens_id") or "") in in_catalog_lens for p in patents):
        return None

    ps = ProgramScore(
        case_id=case_id,
        themes=themes,
        seed_noted=case_id in SEED_NOTED_CASES,
        ri_owner=ri,
        opportunity_type=otype,
        primary_lens_id=(primary.get("lens_id") or "").strip(),
        primary_title=(primary.get("title") or "").strip(),
        owners=(owners or "")[:120],
    )
    ps.merge_target = MERGE_INTO.get(case_id, "")

    score = 0
    if ri:
        score += 2
    if otype in {"medical_device", "diagnostic", "digital_therapeutic"}:
        score += 3
    elif otype == "therapeutic":
        score += 2
    elif otype == "platform" and (
        "medical_device_kw" in themes or "diagnostic_dx" in themes or "neuro_device" in themes
    ):
        score += 2
    if "neuro_device" in themes or "diagnostic_dx" in themes:
        score += 2
    if "wound_surgical" in themes or "drug_delivery" in themes:
        score += 1
    if len(patents) > 1:
        score += 1
    if ps.seed_noted:
        score += 3
    if case_id in CASE_PRECEDENT_GROUP:
        score += 1
    if _is_pharma_prefix(case_id):
        score -= 3
    if "pharma_chem" in themes and len(themes) <= 2:
        score -= 2
    if ps.merge_target:
        score -= 4
    if "ablation_thermal" in themes and "theromics" not in case_id:
        score -= 1

    ps.rubric_score = max(0, score)
    return ps


def _recommendation(ps: ProgramScore) -> tuple[str, str]:
    if ps.merge_target:
        return (
            "merge",
            f"Merge into `{ps.merge_target}` (duplicate / same program family).",
        )
    if _is_pharma_prefix(ps.case_id):
        if ps.rubric_score >= 8:
            return (
                "tier_b",
                "Pharma chemistry — consider Tier B only unless Slater wants manufacturing syndicate.",
            )
        return ("exclude", "Pharma process chemistry; already covered selectively in catalog.")

    if ps.seed_noted:
        if ps.rubric_score >= 6:
            return (
                "tier_a_candidate",
                "Flagged in seed curation notes — prioritize human Q&A (Seed Tier A template).",
            )

    if ps.rubric_score >= 9 and ps.top_physician_score >= 53:
        return (
            "tier_a_candidate",
            "Strong rubric + physician match — draft title_clean, PI, and comps before promotion.",
        )
    if ps.rubric_score >= 8:
        return (
            "tier_a_candidate",
            "Strong rubric — confirm PI, company, and dedupe before promotion.",
        )
    if ps.rubric_score >= 6:
        return ("tier_b", "Promising — enrich as Tier B first or hold for catalog backlog.")
    if ps.rubric_score >= 4:
        return ("watch", "Weak auto signal — review only if you recall prior diligence.")
    return ("exclude", "Low syndicate fit or generic platform cluster.")


def run_scan(*, shortlist_min_score: int = 6, top_n_report: int = 25) -> dict[str, int]:
    enrich_rows = _read_csv(ENRICH)
    catalog_cases = {r["case_id"] for r in enrich_rows}
    catalog_lens = _catalog_lens_ids(enrich_rows)
    tier_a = {
        r["case_id"]
        for r in enrich_rows
        if (r.get("catalog_tier") or "").upper() == "A" and (r.get("catalog_include") or "").lower() == "true"
    }
    tier_b_inc = {
        r["case_id"]
        for r in enrich_rows
        if (r.get("catalog_tier") or "").upper() == "B" and (r.get("catalog_include") or "").lower() == "true"
    }

    opps = {r["case_id"]: r for r in _read_csv(OPPS)}
    ip_by: dict[str, list[dict[str, str]]] = defaultdict(list)
    for row in _read_csv(IP):
        ip_by[row["case_id"]].append(row)

    uncat_cases = sorted(cid for cid in opps if cid not in catalog_cases)

    # Full patent-level scan export
    scan_rows: list[dict[str, str]] = []
    for case_id in uncat_cases:
        opp = opps.get(case_id, {})
        for p in ip_by.get(case_id, []):
            lid = (p.get("lens_id") or "").strip()
            scan_rows.append(
                {
                    "case_id": case_id,
                    "lens_id": lid,
                    "display_key": p.get("display_key", ""),
                    "title": p.get("title", ""),
                    "owners": (p.get("owners") or "")[:200],
                    "inventors": (p.get("inventors") or "")[:120],
                    "legal_status": p.get("legal_status", ""),
                    "opportunity_type": opp.get("opportunity_type", ""),
                    "lens_in_catalog": "true" if lid in catalog_lens else "false",
                    "ri_notes": opp.get("ri_notes", ""),
                }
            )
    _write_csv(
        SCAN_CSV,
        [
            "case_id",
            "lens_id",
            "display_key",
            "title",
            "owners",
            "inventors",
            "legal_status",
            "opportunity_type",
            "lens_in_catalog",
            "ri_notes",
        ],
        scan_rows,
    )

    clear_assignment_cache()
    programs: list[ProgramScore] = []
    for case_id in uncat_cases:
        scored = _score_program(
            case_id, ip_by.get(case_id, []), opps.get(case_id, {}), in_catalog_lens=catalog_lens
        )
        if not scored:
            continue
        match = physician_match_for_case(case_id)
        scored.staffing_score = float(match.get("staffing_feasibility_score_0_100") or 0)
        candidates = match.get("candidate_physicians") or []
        if candidates:
            best = max(candidates, key=lambda c: int(c.get("match_score_0_100") or 0))
            scored.top_physician_score = int(best.get("match_score_0_100") or 0)
            scored.top_physician_name = str(best.get("name") or "")
            scored.top_physician_specialty = str(best.get("specialty") or "")
        scored.recommendation, scored.rationale = _recommendation(scored)
        programs.append(scored)

    programs.sort(
        key=lambda p: (
            p.recommendation != "tier_a_candidate",
            p.recommendation != "tier_b",
            -p.rubric_score,
            -p.top_physician_score,
            p.case_id,
        )
    )

    shortlist = [p for p in programs if p.rubric_score >= shortlist_min_score]
    shortlist_rows = [
        {
            "case_id": p.case_id,
            "recommendation": p.recommendation,
            "rubric_score": str(p.rubric_score),
            "themes": "|".join(p.themes),
            "seed_noted": "true" if p.seed_noted else "false",
            "merge_target": p.merge_target,
            "opportunity_type": p.opportunity_type,
            "ri_owner": "true" if p.ri_owner else "false",
            "primary_lens_id": p.primary_lens_id,
            "primary_title": p.primary_title,
            "top_physician_score": str(p.top_physician_score),
            "top_physician_name": p.top_physician_name,
            "top_physician_specialty": p.top_physician_specialty,
            "staffing_feasibility_score": str(p.staffing_score),
            "rationale": p.rationale,
        }
        for p in shortlist
    ]
    _write_csv(
        SHORTLIST_CSV,
        list(shortlist_rows[0].keys()) if shortlist_rows else ["case_id"],
        shortlist_rows,
    )

    match_rows: list[dict[str, str]] = []
    shortlist_ids = {p.case_id for p in shortlist}
    for case_id in sorted(shortlist_ids):
        match = physician_match_for_case(case_id)
        opp = opps.get(case_id, {})
        title = opp.get("display_name", case_id)
        for rank, cand in enumerate(match.get("candidate_physicians") or [], start=1):
            match_rows.append(
                {
                    "case_id": case_id,
                    "title": title[:80],
                    "rank": str(rank),
                    "physician_id": str(cand.get("physician_id") or ""),
                    "name": str(cand.get("name") or ""),
                    "specialty": str(cand.get("specialty") or ""),
                    "institution": str(cand.get("institution") or ""),
                    "match_score": str(cand.get("match_score_0_100") or ""),
                    "clinical_tags_matched": "|".join(cand.get("clinical_tags_matched") or []),
                }
            )
    _write_csv(
        MATCH_CSV,
        [
            "case_id",
            "title",
            "rank",
            "physician_id",
            "name",
            "specialty",
            "institution",
            "match_score",
            "clinical_tags_matched",
        ],
        match_rows,
    )

    tier_a_candidates = [p for p in programs if p.recommendation == "tier_a_candidate"][:top_n_report]
    high_tier_b = [
        p
        for p in programs
        if p.recommendation == "tier_b"
        and p.rubric_score >= 7
        and not p.merge_target
    ][:20]
    device_dx = [
        p
        for p in programs
        if p.recommendation in {"tier_b", "tier_a_candidate"}
        and p.opportunity_type in {"medical_device", "diagnostic"}
        and p.rubric_score >= 6
    ]

    lines: list[str] = [
        "# RI uncatalogued patent scan — Tier A promotion recommendations",
        "",
        f"Generated by `python -m pipeline.scan_ri_uncatalogued`.",
        "",
        "## Summary",
        "",
        f"| Metric | Count |",
        f"|--------|------:|",
        f"| Uncatalogued `case_id`s | {len(uncat_cases)} |",
        f"| Patent rows exported | {len(scan_rows)} |",
        f"| Programs scored | {len(programs)} |",
        f"| Shortlist (rubric ≥ {shortlist_min_score}) | {len(shortlist)} |",
        f"| Tier A candidates | {len(tier_a_candidates)} |",
        f"| Current Tier A (included) | {len(tier_a)} |",
        f"| Current Tier B (included) | {len(tier_b_inc)} |",
        "",
        "## Artifacts",
        "",
        f"- `{SCAN_CSV.relative_to(repo_root())}` — all uncatalogued patents",
        f"- `{SHORTLIST_CSV.relative_to(repo_root())}` — scored programs",
        f"- `{MATCH_CSV.relative_to(repo_root())}` — physician matches for shortlist",
        "",
        "## Tier A promotion candidates (uncatalogued)",
        "",
        "Complete the Seed Tier A Q&A (`data/ri/Seed Tier A — 5 programs.txt`) before adding rows to ",
        "`ri_opportunities_catalog_enrichment.csv`. Run `python -m pipeline.validate_ri_tier_a` after promotion.",
        "",
    ]

    if not tier_a_candidates:
        lines.append("_No automatic Tier A candidates met thresholds._\n")
    else:
        for p in tier_a_candidates:
            lines.extend(
                [
                    f"### `{p.case_id}`",
                    "",
                    f"- **Rubric:** {p.rubric_score}/12 · **Physician match:** {p.top_physician_score} "
                    f"({p.top_physician_name or 'none'} · {p.top_physician_specialty or 'n/a'})",
                    f"- **Type:** {p.opportunity_type} · **Themes:** {', '.join(p.themes) or '—'}",
                    f"- **Patent:** {p.primary_title}",
                    f"- **Lens:** `{p.primary_lens_id}`",
                    f"- **Owners:** {p.owners}",
                    f"- **Rationale:** {p.rationale}",
                    "",
                ]
            )

    lines.extend(
        [
            "## Seed-noted programs (always review)",
            "",
        ]
    )
    for p in sorted(programs, key=lambda x: x.case_id):
        if p.seed_noted:
            lines.append(
                f"- `{p.case_id}` — rubric {p.rubric_score}, rec={p.recommendation}, "
                f"physician {p.top_physician_score}"
            )
    lines.append("")

    merges = [p for p in programs if p.merge_target]
    lines.extend(["## Merge into existing catalog (do not promote standalone)", ""])
    if not merges:
        lines.append("_No uncatalogued cases flagged — duplicates are already Tier B excluded in catalog._")
    for p in sorted(merges, key=lambda x: x.case_id)[:30]:
        lines.append(f"- `{p.case_id}` → `{p.merge_target}`")
    if len(merges) > 30:
        lines.append(f"- _…and {len(merges) - 30} more (see shortlist CSV)_")
    lines.append("")

    lines.extend(
        [
            "## High-priority uncatalogued (Tier B first, then Tier A)",
            "",
            "Strong rubric (≥7) with RI ownership — likely matches technologies you reviewed:",
            "",
        ]
    )
    for p in high_tier_b:
        lines.append(
            f"- **`{p.case_id}`** (rubric {p.rubric_score}, {p.opportunity_type}, "
            f"physician {p.top_physician_score}) — {p.primary_title[:90]}"
        )
    lines.append("")

    lines.extend(["## Uncatalogued medical_device / diagnostic (≥6 rubric)", ""])
    for p in device_dx[:15]:
        lines.append(
            f"- `{p.case_id}` — {p.primary_title[:85]} "
            f"(lens `{p.primary_lens_id}`, physician {p.top_physician_score})"
        )
    lines.append("")

    lines.extend(
        [
            "## Tier B in catalog — consider promoting to Tier A",
            "",
            "These are already enriched but not Tier A; review if you remember diligencing them:",
            "",
        ]
    )
    for cid in sorted(tier_b_inc):
        row = next(r for r in enrich_rows if r["case_id"] == cid)
        lines.append(f"- `{cid}` — {row.get('title_clean', row.get('display_name', ''))[:70]}")
    lines.append("")

    lines.extend(
        [
            "## Next steps",
            "",
            "1. Review Tier A candidates above; reject merges and pharma dupes.",
            "2. For each promote: add row to `ri_opportunities_catalog_enrichment.csv` with `catalog_tier=A`.",
            "3. `python -m pipeline.apply_seed_resolution` (if seed-style patches needed).",
            "4. `python -m pipeline.validate_ri_tier_a`",
            "5. `python -m pipeline.enrich_ri_biomcp --tier A --refresh` (selected case_ids)",
            "6. `python -m pipeline.build_ri_combined` and publish web profiles.",
            "",
        ]
    )

    REPORT_MD.write_text("\n".join(lines), encoding="utf-8")

    return {
        "uncat_cases": len(uncat_cases),
        "patent_rows": len(scan_rows),
        "shortlist": len(shortlist),
        "tier_a_candidates": len(tier_a_candidates),
    }


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--shortlist-min", type=int, default=6, help="Min rubric score for shortlist CSV")
    parser.add_argument("--top", type=int, default=25, help="Max Tier A candidates in report")
    args = parser.parse_args()
    stats = run_scan(shortlist_min_score=args.shortlist_min, top_n_report=args.top)
    print(f"Wrote {SCAN_CSV.name} ({stats['patent_rows']} patent rows)")
    print(f"Wrote {SHORTLIST_CSV.name} ({stats['shortlist']} programs)")
    print(f"Wrote {MATCH_CSV.name}")
    print(f"Wrote {REPORT_MD.name} ({stats['tier_a_candidates']} Tier A candidates)")
    print(f"Uncatalogued cases: {stats['uncat_cases']}")


if __name__ == "__main__":
    main()
