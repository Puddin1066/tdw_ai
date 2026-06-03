"""Normalize RI clinician, patent, and trial CSVs into static pipeline inputs.

This module is deterministic and static-first:
- reads user-provided CSV exports from local disk
- writes normalized CSV tables under data/ri/
- does not call network services or external APIs
"""

from __future__ import annotations

import argparse
import csv
import hashlib
import re
from dataclasses import dataclass
from datetime import date
from pathlib import Path
from typing import Iterable

from pipeline.physician_assignment import enrich_opportunity_row, enrich_physician_row
from pipeline.ri_case_merges import apply_case_merges

DATA_ROOT = Path(__file__).resolve().parents[1] / "data" / "ri"

RAW_CLINICIANS_DEFAULT = Path("/Users/JJR/Downloads/data.csv")
RAW_PATENTS_DEFAULT = Path("/Users/JJR/Downloads/Other/Data/CSV/ri-database-patents.csv")
RAW_TRIALS_DEFAULT = Path("/Users/JJR/Downloads/ctg-studies (21).csv")
SUPPLEMENTAL_PATENTS_DEFAULT = DATA_ROOT / "source" / "ri-patents-2.csv"

SEED_OPPORTUNITIES_CSV = DATA_ROOT / "ri_physicians_ip_seed.csv"

PHYSICIANS_OUT = DATA_ROOT / "ri_physicians.csv"
ASSETS_OUT = DATA_ROOT / "ri_ip_assets.csv"
OPPORTUNITIES_OUT = DATA_ROOT / "ri_opportunities.csv"
TRIAL_TEMPLATES_OUT = DATA_ROOT / "ri_trial_templates.csv"
CAPITAL_SOURCES_OUT = DATA_ROOT / "ri_capital_sources.csv"
GOVERNANCE_OUT = DATA_ROOT / "ri_governance_rules.csv"


def _slugify(value: str) -> str:
    value = re.sub(r"[^a-z0-9]+", "_", value.strip().lower())
    return re.sub(r"_+", "_", value).strip("_")


def _norm_text(value: str | None) -> str:
    return re.sub(r"\s+", " ", (value or "").strip().lower())


def _pipe_join(items: Iterable[str]) -> str:
    unique: list[str] = []
    seen: set[str] = set()
    for item in items:
        token = item.strip().lower()
        if not token or token in seen:
            continue
        seen.add(token)
        unique.append(token)
    return "|".join(unique)


def _to_int(value: str | None, default: int = 0) -> int:
    try:
        parsed = int(float((value or "").strip()))
        return parsed
    except (TypeError, ValueError):
        return default


def _to_bool_text(flag: bool) -> str:
    return "true" if flag else "false"


def _read_rows(path: Path) -> list[dict[str, str]]:
    if not path.exists():
        return []
    csv.field_size_limit(10_000_000)
    with path.open(newline="", encoding="utf-8") as handle:
        return list(csv.DictReader(handle))


def _merge_patent_exports(*paths: Path) -> list[dict[str, str]]:
    """Union Lens patent rows by Lens ID; later paths override earlier on duplicate IDs."""
    by_lens: dict[str, dict[str, str]] = {}
    for path in paths:
        if not path.exists():
            continue
        for row in _read_rows(path):
            lens_id = (row.get("Lens ID") or "").strip()
            if not lens_id:
                continue
            by_lens[lens_id] = row
    return list(by_lens.values())


def _write_rows(path: Path, fieldnames: list[str], rows: list[dict[str, str]]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(rows)


def _specialty_roles(specialty: str) -> list[str]:
    s = specialty.lower()
    roles = {"reviewer"}
    if any(token in s for token in ("radiology", "pathology", "critical care", "infectious", "oncology", "medicine")):
        roles.add("investigator")
    if any(token in s for token in ("surgery", "medicine", "oncology", "cardio", "neurology")):
        roles.add("advisor")
    if any(token in s for token in ("engineering", "critical care", "emergency", "hospital")):
        roles.add("pilot_designer")
    return sorted(roles)


def normalize_clinicians(raw_rows: list[dict[str, str]]) -> list[dict[str, str]]:
    by_npi: dict[str, dict[str, str]] = {}
    for row in raw_rows:
        if _norm_text(row.get("State")) != "ri":
            continue
        npi = (row.get("NPI") or "").strip()
        if not npi:
            continue
        specialty = (row.get("pri_spec") or row.get("sec_spec_all") or "").strip()
        if not specialty:
            continue
        name = f"{(row.get('Provider First Name') or '').strip()} {(row.get('Provider Last Name') or '').strip()}".strip()
        institution = (row.get("Facility Name") or "").strip() or f"{(row.get('City/Town') or '').strip()}, RI"
        roles = _specialty_roles(specialty)
        grad_year = _to_int(row.get("Grd_yr"), default=2015)
        years = max(0, date.today().year - grad_year)
        availability = min(30, 8 + (years // 5))
        compensation = 350 + min(350, years * 5)
        interest = "high" if years >= 20 else ("medium" if years >= 8 else "low")
        physician_row = {
            "physician_id": f"npi_{npi}",
            "name": name or f"NPI {npi}",
            "specialty": specialty,
            "institution": institution,
            "roles_willing": _pipe_join(roles),
            "availability_hours_month": str(availability),
            "compensation_floor_usd": str(compensation),
            "conflict_tags": "none",
            "investor_interest_level": interest,
            "mocked": "false",
            "source_type": "cms_nppes_csv",
            "confidence_0_1": "0.84",
        }
        by_npi[npi] = enrich_physician_row(physician_row)
    return sorted(by_npi.values(), key=lambda row: row["physician_id"])


def _split_entities(value: str) -> list[str]:
    return [item.strip() for item in (value or "").split(";;") if item.strip()]


def _ri_patent_score(row: dict[str, str], terms: list[str]) -> int:
    text = " ".join(
        [
            row.get("Title", ""),
            row.get("Abstract", ""),
            row.get("Applicants", ""),
            row.get("Owners", ""),
            row.get("Inventors", ""),
            row.get("CPC Classifications", ""),
            row.get("IPCR Classifications", ""),
        ]
    ).lower()
    score = 0
    for term in terms:
        if term and term in text:
            score += 3 if " " in term else 1
    owners = _norm_text(row.get("Owners"))
    if "rhode island" in owners or "brown university" in owners:
        score += 2
    return score


def _infer_opportunity_label(title: str, opportunity_type: str) -> str:
    core = re.sub(r"[^A-Za-z0-9 ]+", " ", title).strip()
    if not core:
        return "RI Technology Opportunity"
    words = [w for w in core.split() if len(w) > 2][:6]
    label = " ".join(words)
    suffix = {
        "diagnostic": "Diagnostic Opportunity",
        "digital_therapeutic": "Digital Therapeutic Opportunity",
        "medical_device": "Medical Device Opportunity",
        "platform": "Technology Platform Opportunity",
        "therapeutic": "Therapeutic Opportunity",
    }.get(opportunity_type, "Technology Opportunity")
    return f"{label} {suffix}".strip()


PATENT_TITLE_STOPWORDS = {
    "method",
    "methods",
    "system",
    "systems",
    "device",
    "devices",
    "composition",
    "compositions",
    "use",
    "uses",
    "treatment",
    "treating",
    "process",
    "processes",
    "data",
    "patient",
    "patients",
    "clinical",
    "and",
    "for",
    "with",
    "from",
    "into",
    "among",
    "based",
}


def _ri_anchor_patent(row: dict[str, str]) -> bool:
    text = " ".join([row.get("Owners", ""), row.get("Applicants", ""), row.get("Title", "")]).lower()
    return any(
        anchor in text
        for anchor in (
            "rhode island",
            "brown university",
            "brown",
            "lifespan",
            "university of rhode island",
            "uri",
            "theromics",
            "nanode",
            "rhode island hospital",
        )
    )


def _title_tokens(title: str) -> list[str]:
    tokens = [token for token in re.split(r"[^a-z0-9]+", title.lower()) if len(token) >= 4]
    return [token for token in tokens if token not in PATENT_TITLE_STOPWORDS]


def _owner_anchor(row: dict[str, str]) -> str:
    owners = _split_entities(row.get("Owners", ""))
    primary = owners[0] if owners else ""
    tokens = _title_tokens(primary)
    if tokens:
        return "_".join(tokens[:2])
    applicants = _title_tokens(row.get("Applicants", ""))
    if applicants:
        return "_".join(applicants[:2])
    return "ri_owner"


def _infer_patent_opportunity_type(row: dict[str, str]) -> str:
    text = " ".join(
        [row.get("Title", ""), row.get("CPC Classifications", ""), row.get("IPCR Classifications", "")]
    ).lower()
    if any(token in text for token in ("diagnostic", "detection", "predicting", "biomarker", "sequencing")):
        return "diagnostic"
    if any(token in text for token in ("software", "digital", "app", "workflow", "platform")):
        return "digital_therapeutic"
    if any(token in text for token in ("catheter", "implant", "probe", "device", "electrode", "ultrasound")):
        return "medical_device"
    if any(token in text for token in ("drug", "antibody", "compound", "vaccine", "therapeutic")):
        return "therapeutic"
    return "platform"


def _default_specialties(opportunity_type: str) -> str:
    by_type = {
        "diagnostic": "critical care surgery|infectious disease|emergency medicine",
        "digital_therapeutic": "pain medicine|behavioral health|primary care",
        "medical_device": "critical care|hospital medicine|biomedical engineering",
        "therapeutic": "oncology|hospital medicine|clinical pharmacology",
        "platform": "oncology|pathology|biostatistics",
    }
    return by_type.get(opportunity_type, "hospital medicine|primary care")


def _sort_patents_by_recency(rows: list[dict[str, str]]) -> list[dict[str, str]]:
    def _sort_key(row: dict[str, str]) -> tuple[int, str]:
        publication = (row.get("Publication Date") or "").strip()
        year = _to_int(publication.split("-")[0] if publication else "", default=1900)
        return (year, publication)

    return sorted(rows, key=_sort_key, reverse=True)


def _chunk_rows(rows: list[dict[str, str]], chunk_size: int) -> list[list[dict[str, str]]]:
    if chunk_size <= 0:
        return [rows]
    return [rows[i : i + chunk_size] for i in range(0, len(rows), chunk_size)]


# Extra patent-matching terms for curated seed opportunities (absorbs family variants).
SEED_PATENT_EXTRA_TERMS: dict[str, list[str]] = {
    "theromics_ri": [
        "theromics",
        "thermal",
        "accelerant",
        "ablation",
        "a61b18",
        "hypertherm",
        "radiofrequency",
        "microwave",
        "tumor ablat",
    ],
    "monaghan_sepsis_diagnostic_ri": [
        "monaghan",
        "monaghan sean",
        "deep rna",
        "rna sequencing",
        "host-response",
        "host response",
        "sepsis",
        "covid-19 antibodies",
    ],
    "cbt_pain_digital_platform_ri": ["chronic pain", "cbt", "pain management", "digital therapeutic"],
    "nanode_ri": [
        "nanode",
        "chen qian",
        "nanopiece",
        "nanopieces",
        "nucleic acid",
        "nucleotide",
        "self-assembled",
        "rosette nanotube",
        "janus",
    ],
    "phlip_therapeutics_ri": [
        "phlip",
        "reshetnyak",
        "engelman",
        "fluorophore",
        "fluorescent",
        "pH-triggered",
        "pH triggered",
        "polypeptide",
    ],
    "prothera_iaip_ri": [
        "prothera",
        "inter-alpha",
        "inter alpha",
        "inhibitor protein",
        "iaip",
        "yow-pin lim",
        "lim yow",
        "sepsis",
    ],
    "mindimmune_therapeutics_ri": [
        "mindimmune",
        "miti-101",
        "dendritic cell",
        "neurodegenerative",
        "zorn",
        "menniti",
        "nelson",
        "campbell",
        "neuroinflammation",
        "alzheimer",
    ],
}


SEED_PROGRAM_ONLY_CASES: frozenset[str] = frozenset({"cbt_pain_digital_platform_ri"})


def _is_program_only_ip(ri_ip_source: str | None) -> bool:
    source = (ri_ip_source or "").strip().lower()
    return source in {"program_only", "none", "no_patent"}


def _parse_explicit_lens_id(ri_ip_source: str | None) -> str:
    source = (ri_ip_source or "").strip()
    if _is_program_only_ip(source):
        return ""
    if source.lower().startswith("lens:"):
        return source.split(":", 1)[1].strip()
    return ""


def _invention_token_set(title: str) -> set[str]:
    return set(_title_tokens(title))


def _inventions_similar(left: set[str], right: set[str]) -> bool:
    if not left or not right:
        return False
    overlap = len(left & right)
    union = len(left | right)
    return (overlap / union) >= 0.65


def _cluster_patents_by_invention(rows: list[dict[str, str]]) -> list[list[dict[str, str]]]:
    """Group patent records that share the same invention family (title token similarity)."""
    clusters: list[tuple[set[str], list[dict[str, str]]]] = []
    for row in rows:
        tokens = _invention_token_set(row.get("Title", ""))
        matched_index: int | None = None
        for index, (cluster_tokens, _) in enumerate(clusters):
            if _inventions_similar(tokens, cluster_tokens):
                matched_index = index
                break
        if matched_index is None:
            clusters.append((tokens, [row]))
            continue
        cluster_tokens, cluster_rows = clusters[matched_index]
        cluster_rows.append(row)
        clusters[matched_index] = (cluster_tokens | tokens, cluster_rows)
    return [cluster_rows for _, cluster_rows in clusters]


def _invention_fingerprint(title: str) -> str:
    """Stable slug for case_id generation from the lead patent title."""
    tokens = sorted(_invention_token_set(title))
    if not tokens:
        return "unknown_invention"
    return "_".join(tokens[:8])


def _unique_case_id(base: str, seen: set[str]) -> str:
    candidate = base
    suffix = 2
    while candidate in seen:
        candidate = f"{base}_{suffix}"
        suffix += 1
    seen.add(candidate)
    return candidate


def normalize_patents(
    raw_patent_rows: list[dict[str, str]],
    seed_opportunities: list[dict[str, str]],
    max_assets_per_opportunity: int,
    max_generated_opportunities: int,
) -> tuple[list[dict[str, str]], list[dict[str, str]]]:
    patent_rows = [row for row in raw_patent_rows if row.get("Lens ID")]
    assets_out: list[dict[str, str]] = []
    opportunities_out: list[dict[str, str]] = []
    seen_asset_keys: set[tuple[str, str]] = set()
    seen_case_ids: set[str] = set()
    assigned_lens_ids: set[str] = set()

    def _append_asset(case_id: str, patent: dict[str, str], score: int, reason: str) -> None:
        abstract = patent.get("Abstract", "")
        inventors = _split_entities(patent.get("Inventors", ""))
        owners = _split_entities(patent.get("Owners", ""))
        inventor = inventors[0] if inventors else "unknown_inventor"
        owner = owners[0] if owners else "unknown_owner"
        digest = hashlib.sha1(
            f"{_norm_text(abstract)}|{_norm_text(inventor)}|{_norm_text(owner)}".encode("utf-8")
        ).hexdigest()[:12]
        dedupe_key = (case_id, digest)
        if dedupe_key in seen_asset_keys:
            return
        seen_asset_keys.add(dedupe_key)
        assigned_lens_ids.add((patent.get("Lens ID") or "").strip())
        assets_out.append(
            {
                "case_id": case_id,
                "asset_id": f"asset_{digest}",
                "display_key": patent.get("Display Key", ""),
                "lens_id": patent.get("Lens ID", ""),
                "title": patent.get("Title", ""),
                "publication_date": patent.get("Publication Date", ""),
                "earliest_priority_date": patent.get("Earliest Priority Date", ""),
                "applicants": patent.get("Applicants", ""),
                "owners": patent.get("Owners", ""),
                "inventors": patent.get("Inventors", ""),
                "jurisdiction": patent.get("Jurisdiction", ""),
                "kind": patent.get("Kind", ""),
                "legal_status": patent.get("Legal Status", ""),
                "cpc_classifications": patent.get("CPC Classifications", ""),
                "ipcr_classifications": patent.get("IPCR Classifications", ""),
                "url": patent.get("URL", ""),
                "match_score": str(score),
                "ri_relevance_reason": reason,
                "source_type": "lens_patent_csv",
                "mocked": "false",
                "confidence_0_1": "0.8",
            }
        )

    for opportunity in seed_opportunities:
        case_id = (opportunity.get("case_id") or "").strip()
        if not case_id:
            continue
        if case_id in SEED_PROGRAM_ONLY_CASES or _is_program_only_ip(opportunity.get("ri_ip_source")):
            seen_case_ids.add(case_id)
            opportunity_type = (opportunity.get("opportunity_type") or "platform").strip().lower()
            seed_notes = (opportunity.get("ri_notes") or "").strip()
            opportunities_out.append(
                enrich_opportunity_row(
                    {
                        "case_id": case_id,
                        "display_name": opportunity.get("display_name", case_id),
                        "target": opportunity.get("target", ""),
                        "indication": opportunity.get("indication", ""),
                        "opportunity_type": opportunity_type,
                        "company": opportunity.get("company", "TBD"),
                        "slater_invested": opportunity.get("slater_invested", "false"),
                        "development_stage": opportunity.get("development_stage", "validation"),
                        "required_roles": opportunity.get("required_roles", "reviewer|advisor|investigator"),
                        "required_specialties": opportunity.get("required_specialties", "clinical"),
                        "target_timeline_weeks": opportunity.get("target_timeline_weeks", "20"),
                        "budget_ceiling_usd": opportunity.get("budget_ceiling_usd", "400000"),
                        "capital_gap_usd": opportunity.get("capital_gap_usd", "1200000"),
                        "ri_institution": opportunity.get("ri_institution", ""),
                        "ri_ip_source": "",
                        "ri_notes": seed_notes,
                        "ri_physician_lead": opportunity.get("ri_physician_lead", "TBD"),
                        "conflict_tags": opportunity.get("conflict_tags", ""),
                        "llm_inferred_label": opportunity.get("display_name", case_id),
                        "llm_label_method": "curated_program_without_patent_anchor",
                        "source_type": "ri_physicians_ip_seed",
                        "mocked": "false",
                        "confidence_0_1": "0.73",
                    },
                    patent_rows=[],
                )
            )
            continue
        terms: list[str] = []
        for key in ("target", "indication", "company", "ri_ip_source", "display_name"):
            value = _norm_text(opportunity.get(key))
            if value and value != "tbd":
                terms.append(value)
                terms.extend([token for token in re.split(r"[^a-z0-9]+", value) if len(token) >= 4])
        for extra in SEED_PATENT_EXTRA_TERMS.get(case_id, []):
            terms.append(_norm_text(extra))
            terms.extend([token for token in re.split(r"[^a-z0-9]+", _norm_text(extra)) if len(token) >= 4])
        explicit_lens_id = _parse_explicit_lens_id(opportunity.get("ri_ip_source"))
        pinned_rows = [
            row
            for row in patent_rows
            if explicit_lens_id and (row.get("Lens ID") or "").strip() == explicit_lens_id
        ]
        family_rows: list[dict[str, str]] = []
        if pinned_rows:
            seed_tokens = _invention_token_set(pinned_rows[0].get("Title", ""))
            family_rows = [
                row
                for row in patent_rows
                if _inventions_similar(_invention_token_set(row.get("Title", "")), seed_tokens)
            ]
            for row in family_rows:
                lens_id = (row.get("Lens ID") or "").strip()
                if lens_id:
                    assigned_lens_ids.add(lens_id)
            picked = _sort_patents_by_recency(family_rows)[:max_assets_per_opportunity]
        else:
            ranked = sorted(
                patent_rows,
                key=lambda row: _ri_patent_score(row, terms),
                reverse=True,
            )
            matching = [row for row in ranked if _ri_patent_score(row, terms) > 0]
            if matching:
                clusters = _cluster_patents_by_invention(matching)
                best_cluster = max(
                    clusters,
                    key=lambda cluster: sum(_ri_patent_score(row, terms) for row in cluster),
                )
                seed_tokens = _invention_token_set(best_cluster[0].get("Title", ""))
                family_rows = [
                    row
                    for row in patent_rows
                    if _inventions_similar(_invention_token_set(row.get("Title", "")), seed_tokens)
                ]
                for row in family_rows:
                    lens_id = (row.get("Lens ID") or "").strip()
                    if lens_id:
                        assigned_lens_ids.add(lens_id)
                picked = _sort_patents_by_recency(family_rows)[:max_assets_per_opportunity]
            else:
                picked = ranked[:max_assets_per_opportunity]
        if not picked:
            continue

        first = picked[0]
        seen_case_ids.add(case_id)
        opportunity_type = (opportunity.get("opportunity_type") or "platform").strip().lower()
        family_size = len(family_rows) if family_rows else len(picked)
        seed_notes = (opportunity.get("ri_notes") or "").strip()
        if family_size > len(picked):
            seed_notes = f"{seed_notes} Linked {len(picked)} of {family_size} patent records in family.".strip()
        opportunities_out.append(
            enrich_opportunity_row(
                {
                    "case_id": case_id,
                    "display_name": opportunity.get("display_name", case_id),
                    "target": opportunity.get("target", ""),
                    "indication": opportunity.get("indication", ""),
                    "opportunity_type": opportunity_type,
                    "company": opportunity.get("company", "TBD"),
                    "slater_invested": opportunity.get("slater_invested", "false"),
                    "development_stage": opportunity.get("development_stage", "validation"),
                    "required_roles": opportunity.get("required_roles", "reviewer|advisor|investigator"),
                    "required_specialties": opportunity.get("required_specialties", "clinical"),
                    "target_timeline_weeks": opportunity.get("target_timeline_weeks", "20"),
                    "budget_ceiling_usd": opportunity.get("budget_ceiling_usd", "400000"),
                    "capital_gap_usd": opportunity.get("capital_gap_usd", "1200000"),
                    "ri_institution": opportunity.get("ri_institution", ""),
                    "ri_ip_source": f"lens:{first.get('Lens ID', '')}",
                    "ri_notes": seed_notes,
                    "ri_physician_lead": opportunity.get("ri_physician_lead", "TBD"),
                    "conflict_tags": opportunity.get("conflict_tags", ""),
                    "llm_inferred_label": _infer_opportunity_label(first.get("Title", ""), opportunity_type),
                    "llm_label_method": "deterministic_proxy_from_patent_title",
                    "source_type": "lens_patent_csv",
                    "mocked": "false",
                    "confidence_0_1": "0.73",
                },
                patent_rows=picked,
            )
        )

        for patent in picked:
            _append_asset(
                case_id,
                patent,
                _ri_patent_score(patent, terms),
                "selected_top_ranked_asset_with_max_two_policy",
            )

    leftover = [
        row
        for row in patent_rows
        if (row.get("Lens ID") or "").strip() not in assigned_lens_ids
    ]
    grouped: dict[tuple[str, str], list[dict[str, str]]] = {}
    for row in leftover:
        opportunity_type = _infer_patent_opportunity_type(row)
        owner_anchor = _owner_anchor(row)
        grouped.setdefault((owner_anchor, opportunity_type), []).append(row)

    ranked_groups = sorted(
        grouped.items(),
        key=lambda item: (
            len(item[1]),
            max(_to_int((r.get("Publication Date") or "1900").split("-")[0], default=1900) for r in item[1]),
        ),
        reverse=True,
    )
    created = 0
    for (owner_anchor, opportunity_type), group_rows in ranked_groups:
        sorted_group = _sort_patents_by_recency(group_rows)
        invention_groups = sorted(
            _cluster_patents_by_invention(sorted_group),
            key=lambda cluster: (
                len(cluster),
                _to_int((cluster[0].get("Publication Date") or "1900").split("-")[0], default=1900),
            ),
            reverse=True,
        )
        for invention_rows in invention_groups:
            if not invention_rows:
                continue
            if max_generated_opportunities > 0 and created >= max_generated_opportunities:
                break
            first = invention_rows[0]
            picked = invention_rows[: max(1, max_assets_per_opportunity)]
            created += 1
            fingerprint_slug = (
                _slugify(_invention_fingerprint(first.get("Title", "")))[:48].strip("_") or f"group_{created:03d}"
            )
            base_case_id = f"auto_{_slugify(owner_anchor)}_{fingerprint_slug}".strip("_")
            case_id = _unique_case_id(base_case_id, seen_case_ids)
            family_size = len(invention_rows)
            opportunities_out.append(
                enrich_opportunity_row(
                    {
                        "case_id": case_id,
                        "display_name": _infer_opportunity_label(first.get("Title", ""), opportunity_type),
                        "target": first.get("Title", "")[:80],
                        "indication": "RI technology opportunity from patent corpus",
                        "opportunity_type": opportunity_type,
                        "company": "TBD",
                        "slater_invested": "false",
                        "development_stage": "validation",
                        "required_roles": "reviewer|advisor|investigator",
                        "required_specialties": _default_specialties(opportunity_type),
                        "target_timeline_weeks": "20",
                        "budget_ceiling_usd": "400000",
                        "capital_gap_usd": "1200000",
                        "ri_institution": "Rhode Island ecosystem",
                        "ri_ip_source": f"lens:{first.get('Lens ID', '')}",
                        "ri_notes": (
                            f"Deduped patent family ({len(picked)} of {family_size} records); "
                            "review scope and naming."
                        ),
                        "ri_physician_lead": "TBD",
                        "conflict_tags": "",
                        "llm_inferred_label": _infer_opportunity_label(first.get("Title", ""), opportunity_type),
                        "llm_label_method": "deterministic_proxy_from_deduped_patent_family",
                        "source_type": "lens_patent_csv",
                        "mocked": "false",
                        "confidence_0_1": "0.64",
                    },
                    patent_rows=picked,
                )
            )
            title_terms = _title_tokens(first.get("Title", ""))
            for patent in picked:
                _append_asset(
                    case_id,
                    patent,
                    max(1, _ri_patent_score(patent, title_terms)),
                    "deduped_family_selected_with_max_assets_policy",
                )
        if max_generated_opportunities > 0 and created >= max_generated_opportunities:
            break
    return assets_out, opportunities_out


def _is_ri_trial(locations: str) -> bool:
    text = _norm_text(locations)
    anchors = (
        "rhode island",
        "providence",
        "east greenwich",
        "brown university",
        "rhode island hospital",
        "hasbro",
        "lifespan",
    )
    return any(anchor in text for anchor in anchors)


def _primary_endpoint_type(text: str) -> str:
    value = _norm_text(text)
    if any(token in value for token in ("mortality", "survival", "response rate", "hospitalization")):
        return "clinical_outcome"
    if any(token in value for token in ("safety", "adverse", "tolerability", "toxicity")):
        return "safety"
    if any(token in value for token in ("feasibility", "adherence", "recruitment", "acceptability")):
        return "feasibility"
    if any(token in value for token in ("biomarker", "rna", "pcr", "diagnostic", "specificity", "sensitivity")):
        return "biomarker"
    return "functional_or_symptom"


def _trial_opportunity_type(conditions: str, interventions: str) -> str:
    text = f"{_norm_text(conditions)} {_norm_text(interventions)}"
    if "device:" in text:
        return "medical_device"
    if any(token in text for token in ("diagnostic", "sensitivity", "specificity", "sequencing", "screening")):
        return "diagnostic"
    if any(token in text for token in ("behavioral:", "app", "digital", "mindfulness", "coaching")):
        return "digital_therapeutic"
    if any(token in text for token in ("drug:", "biological:", "vaccine", "antibody", "therapy")):
        return "therapeutic"
    return "platform"


def _parse_ymd(value: str) -> date | None:
    text = (value or "").strip()
    for fmt in ("%Y-%m-%d", "%Y-%m", "%Y"):
        try:
            if fmt == "%Y":
                return date(int(text), 1, 1)
            if fmt == "%Y-%m":
                parts = text.split("-")
                return date(int(parts[0]), int(parts[1]), 1)
            year, month, day = text.split("-")
            return date(int(year), int(month), int(day))
        except Exception:
            continue
    return None


def _phase_weight(phase: str) -> float:
    p = _norm_text(phase)
    if "phase3" in p:
        return 0.8
    if "phase2" in p:
        return 0.65
    if "phase1" in p or "early" in p:
        return 0.5
    return 0.45


def normalize_trials(raw_rows: list[dict[str, str]]) -> list[dict[str, str]]:
    rows: list[dict[str, str]] = []
    for row in raw_rows:
        nct = (row.get("NCT Number") or "").strip()
        if not nct or not _is_ri_trial(row.get("Locations", "")):
            continue
        study_type = _norm_text(row.get("Study Type", "")) or "interventional"
        start = _parse_ymd(row.get("Start Date", ""))
        end = _parse_ymd(row.get("Completion Date", ""))
        duration_weeks = 26
        if start and end and end >= start:
            duration_weeks = max(4, (end - start).days // 7)
        enrollment = _to_int(row.get("Enrollment"), default=50)
        endpoint_type = _primary_endpoint_type(row.get("Primary Outcome Measures", ""))
        opportunity_type = _trial_opportunity_type(row.get("Conditions", ""), row.get("Interventions", ""))
        phase_w = _phase_weight(row.get("Phases", ""))
        endpoint_bump = 0.1 if endpoint_type == "clinical_outcome" else (0.05 if endpoint_type == "biomarker" else 0.0)
        weight = min(0.95, max(0.1, phase_w + endpoint_bump))

        condition_text = _norm_text(row.get("Conditions", ""))
        specialties: list[str] = []
        if "sepsis" in condition_text or "infection" in condition_text:
            specialties.extend(["critical care", "infectious disease", "emergency medicine"])
        if "pain" in condition_text or "migraine" in condition_text:
            specialties.extend(["pain medicine", "neurology"])
        if any(token in condition_text for token in ("cancer", "oncology", "tumor", "lymphoma")):
            specialties.extend(["oncology", "pathology"])
        if not specialties:
            specialties.extend(["hospital medicine", "primary care"])
        roles = ["reviewer", "investigator", "pilot_designer"] if study_type == "interventional" else ["reviewer", "advisor", "investigator"]

        phase_multiplier = 1.4 if "phase3" in _norm_text(row.get("Phases")) else (1.0 if "phase2" in _norm_text(row.get("Phases")) else 0.8)
        study_multiplier = 1.0 if study_type == "interventional" else 0.6
        duration_factor = max(0.6, min(1.8, duration_weeks / 52))
        cost_usd = int(max(50000, enrollment * 2200 * phase_multiplier * study_multiplier * duration_factor))

        rows.append(
            {
                "template_id": f"ctg_{nct.lower()}",
                "opportunity_type": opportunity_type,
                "study_type": study_type,
                "primary_endpoint_type": endpoint_type,
                "duration_weeks": str(duration_weeks),
                "cost_usd": str(cost_usd),
                "required_specialties": _pipe_join(specialties),
                "required_roles": _pipe_join(roles),
                "expected_inflection_weight_0_1": f"{weight:.2f}",
                "mocked": "false",
                "source_type": "ctgov_ri_history_csv",
            }
        )
    return rows


def build_capital_sources() -> list[dict[str, str]]:
    return [
        {
            "source_id": "cap_physician_50",
            "source_name": "RI Physician Syndicate (Policy 50%)",
            "source_type": "physician_syndicate",
            "check_min_usd": "50000",
            "check_max_usd": "3000000",
            "stage_fit": "discovery|validation|pilot launch|pilot clinical deployment|prototype to pilot",
            "ri_focus": "true",
            "match_eligible": "true",
            "decision_cycle_weeks": "6",
            "mocked": "false",
            "source_type_detail": "static_policy",
        },
        {
            "source_id": "cap_slater_ssbci_50",
            "source_name": "Slater SSBCI Match (Policy 50%)",
            "source_type": "public_program",
            "check_min_usd": "50000",
            "check_max_usd": "3000000",
            "stage_fit": "discovery|validation|pilot launch|pilot clinical deployment|prototype to pilot",
            "ri_focus": "true",
            "match_eligible": "true",
            "decision_cycle_weeks": "8",
            "mocked": "false",
            "source_type_detail": "static_policy",
        },
    ]


def build_governance_rules() -> list[dict[str, str]]:
    return [
        {"rule_id": "gov_001", "category": "coi", "rule_text": "Exclude clinicians with direct company equity conflict from reviewer role.", "applies_to": "all_opportunities", "source_type": "static_policy", "mocked": "false"},
        {"rule_id": "gov_002", "category": "coi", "rule_text": "Require conflict tag overlap check between opportunity and physician before role assignment.", "applies_to": "all_opportunities", "source_type": "static_policy", "mocked": "false"},
        {"rule_id": "gov_003", "category": "role_compatibility", "rule_text": "At least one investigator and one reviewer required for financeable readiness.", "applies_to": "all_opportunities", "source_type": "static_policy", "mocked": "false"},
    ]


@dataclass(frozen=True)
class NormalizeResult:
    normalized: bool
    files_written: int


def normalize_all(
    *,
    clinicians_csv: Path,
    patents_csv: Path,
    trials_csv: Path,
    supplemental_patents_csv: Path | None = None,
    max_assets_per_opportunity: int = 2,
    max_generated_opportunities: int = 0,
) -> NormalizeResult:
    seed_rows = _read_rows(SEED_OPPORTUNITIES_CSV)
    clinicians_raw = _read_rows(clinicians_csv)
    patent_paths = [patents_csv]
    if supplemental_patents_csv and supplemental_patents_csv.exists():
        patent_paths.append(supplemental_patents_csv)
    patents_raw = _merge_patent_exports(*patent_paths)
    trials_raw = _read_rows(trials_csv)
    if not clinicians_raw and not patents_raw and not trials_raw:
        return NormalizeResult(normalized=False, files_written=0)

    physicians_rows = normalize_clinicians(clinicians_raw)
    assets_rows, opportunities_rows = normalize_patents(
        patents_raw,
        seed_rows,
        max_assets_per_opportunity=max_assets_per_opportunity,
        max_generated_opportunities=max_generated_opportunities,
    )
    assets_rows, opportunities_rows = apply_case_merges(assets_rows, opportunities_rows)
    trial_rows = normalize_trials(trials_raw)
    capital_rows = build_capital_sources()
    governance_rows = build_governance_rules()

    if physicians_rows:
        _write_rows(
            PHYSICIANS_OUT,
            [
                "physician_id",
                "name",
                "specialty",
                "clinical_tags",
                "institution",
                "roles_willing",
                "availability_hours_month",
                "compensation_floor_usd",
                "conflict_tags",
                "investor_interest_level",
                "mocked",
                "source_type",
                "confidence_0_1",
            ],
            physicians_rows,
        )
    if assets_rows:
        _write_rows(
            ASSETS_OUT,
            [
                "case_id",
                "asset_id",
                "display_key",
                "lens_id",
                "title",
                "publication_date",
                "earliest_priority_date",
                "applicants",
                "owners",
                "inventors",
                "jurisdiction",
                "kind",
                "legal_status",
                "cpc_classifications",
                "ipcr_classifications",
                "url",
                "match_score",
                "ri_relevance_reason",
                "source_type",
                "mocked",
                "confidence_0_1",
            ],
            assets_rows,
        )
    if opportunities_rows:
        _write_rows(
            OPPORTUNITIES_OUT,
            [
                "case_id",
                "display_name",
                "target",
                "indication",
                "opportunity_type",
                "company",
                "slater_invested",
                "development_stage",
                "required_roles",
                "required_specialties",
                "clinical_tags",
                "target_timeline_weeks",
                "budget_ceiling_usd",
                "capital_gap_usd",
                "ri_institution",
                "ri_ip_source",
                "ri_notes",
                "ri_physician_lead",
                "conflict_tags",
                "llm_inferred_label",
                "llm_label_method",
                "source_type",
                "mocked",
                "confidence_0_1",
            ],
            opportunities_rows,
        )
    if trial_rows:
        _write_rows(
            TRIAL_TEMPLATES_OUT,
            [
                "template_id",
                "opportunity_type",
                "study_type",
                "primary_endpoint_type",
                "duration_weeks",
                "cost_usd",
                "required_specialties",
                "required_roles",
                "expected_inflection_weight_0_1",
                "mocked",
                "source_type",
            ],
            trial_rows,
        )
    _write_rows(
        CAPITAL_SOURCES_OUT,
        [
            "source_id",
            "source_name",
            "source_type",
            "check_min_usd",
            "check_max_usd",
            "stage_fit",
            "ri_focus",
            "match_eligible",
            "decision_cycle_weeks",
            "mocked",
            "source_type_detail",
        ],
        capital_rows,
    )
    _write_rows(
        GOVERNANCE_OUT,
        ["rule_id", "category", "rule_text", "applies_to", "source_type", "mocked"],
        governance_rows,
    )
    return NormalizeResult(normalized=True, files_written=6)


def ensure_normalized_data() -> bool:
    if not (RAW_CLINICIANS_DEFAULT.exists() and RAW_PATENTS_DEFAULT.exists() and RAW_TRIALS_DEFAULT.exists()):
        return False
    targets = [PHYSICIANS_OUT, ASSETS_OUT, OPPORTUNITIES_OUT, TRIAL_TEMPLATES_OUT, CAPITAL_SOURCES_OUT, GOVERNANCE_OUT]
    if all(path.exists() for path in targets):
        newest_source_mtime = max(
            RAW_CLINICIANS_DEFAULT.stat().st_mtime,
            RAW_PATENTS_DEFAULT.stat().st_mtime,
            RAW_TRIALS_DEFAULT.stat().st_mtime,
            SEED_OPPORTUNITIES_CSV.stat().st_mtime if SEED_OPPORTUNITIES_CSV.exists() else 0,
        )
        oldest_target_mtime = min(path.stat().st_mtime for path in targets)
        if oldest_target_mtime >= newest_source_mtime:
            return True
    result = normalize_all(
        clinicians_csv=RAW_CLINICIANS_DEFAULT,
        patents_csv=RAW_PATENTS_DEFAULT,
        trials_csv=RAW_TRIALS_DEFAULT,
    )
    return result.normalized


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Normalize RI source CSVs into data/ri static tables.")
    parser.add_argument("--clinicians-csv", type=Path, default=RAW_CLINICIANS_DEFAULT)
    parser.add_argument("--patents-csv", type=Path, default=RAW_PATENTS_DEFAULT)
    parser.add_argument(
        "--supplemental-patents-csv",
        type=Path,
        default=SUPPLEMENTAL_PATENTS_DEFAULT,
        help="Additional Lens export merged by Lens ID (default: data/ri/source/ri-patents-2.csv if present)",
    )
    parser.add_argument(
        "--no-supplemental-patents",
        action="store_true",
        help="Do not merge supplemental patent export",
    )
    parser.add_argument("--trials-csv", type=Path, default=RAW_TRIALS_DEFAULT)
    parser.add_argument("--max-assets-per-opportunity", type=int, default=2)
    parser.add_argument("--max-generated-opportunities", type=int, default=0)
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    supplemental = None if args.no_supplemental_patents else args.supplemental_patents_csv
    result = normalize_all(
        clinicians_csv=args.clinicians_csv,
        patents_csv=args.patents_csv,
        trials_csv=args.trials_csv,
        supplemental_patents_csv=supplemental,
        max_assets_per_opportunity=max(1, args.max_assets_per_opportunity),
        max_generated_opportunities=max(0, args.max_generated_opportunities),
    )
    if not result.normalized:
        print("Normalization skipped: missing seed rows or source CSVs.")
        return
    from pipeline.apply_seed_resolution import main as apply_seed_resolution

    apply_seed_resolution()
    print(f"Normalized RI CSVs successfully ({result.files_written} files).")


if __name__ == "__main__":
    main()
