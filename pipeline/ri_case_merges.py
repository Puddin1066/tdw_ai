"""Curated case_id merges for RI patent normalization and catalog curation."""

from __future__ import annotations

# alias case_id -> canonical case_id (patents + opportunities collapse to canonical)
CASE_MERGE_ALIASES: dict[str, str] = {
    # ProThera IAIP — one program (US + DK + BR family members)
    "auto_prothera_biologics_alpha_inhibitor_inter_proteins_thereof": "prothera_iaip_ri",
    "auto_prothera_biologics_alpha_blod_fremstilling_inhibitorproteiner_inter": "prothera_iaip_ri",
    "auto_prothera_biologics_alfa_composi_inibidoras_inter_partir_prepara_pro": "prothera_iaip_ri",
    # Tapinos enhancer RNA — RI Hospital canonical
    "auto_univ_brown_brain_enhancer_primary_rnas_targeting_tumors": (
        "auto_rhode_island_brain_enhancer_primary_rnas_targeting_tumors"
    ),
    # Brown/Bryant diamide antibacterials — same family (Bryant US grant canonical)
    "auto_univ_brown_antibacterial_compounds_making_novel_same_using": (
        "auto_bryant_university_antibacterial_compounds_making_same_using"
    ),
    # Saab RI pain neurophysiology cluster
    "auto_rhode_island_associated_cord_detecting_diseases_disorders_ner": (
        "auto_rhode_island_activity_brain_detecting_pain_using"
    ),
    "auto_rhode_island_management_pain": "auto_rhode_island_activity_brain_detecting_pain_using",
}

MERGE_EXCLUSION_NOTE = "Merged into canonical case per ri_case_merges.CASE_MERGE_ALIASES; do not promote standalone."


def canonical_case_id(case_id: str) -> str:
    return CASE_MERGE_ALIASES.get(case_id, case_id)


def apply_case_merges(
    assets: list[dict[str, str]],
    opportunities: list[dict[str, str]],
) -> tuple[list[dict[str, str]], list[dict[str, str]]]:
    """Reassign alias case_ids; collapse duplicate opportunities and assets."""
    if not CASE_MERGE_ALIASES:
        return assets, opportunities

    merged_assets: list[dict[str, str]] = []
    seen_asset_lens: set[tuple[str, str]] = set()
    for row in assets:
        patched = dict(row)
        orig = patched.get("case_id", "")
        target = canonical_case_id(orig)
        if target != orig:
            patched["case_id"] = target
            patched["ri_relevance_reason"] = (
                f"{patched.get('ri_relevance_reason', '')};case_merge:{orig}->{target}"
            ).strip(";")
        key = (target, (patched.get("lens_id") or "").strip())
        if key in seen_asset_lens:
            continue
        seen_asset_lens.add(key)
        merged_assets.append(patched)

    by_canonical: dict[str, dict[str, str]] = {}
    absorbed: dict[str, list[str]] = {}

    def _prefer_row(current: dict[str, str], incoming: dict[str, str], canonical: str) -> dict[str, str]:
        if incoming.get("case_id") == canonical and current.get("case_id") != canonical:
            return incoming
        if current.get("case_id") == canonical and incoming.get("case_id") != canonical:
            return current
        if current.get("source_type") == "ri_physicians_ip_seed":
            return current
        if incoming.get("source_type") == "ri_physicians_ip_seed":
            return incoming
        cur_lens = (current.get("ri_ip_source") or "").replace("lens:", "")
        inc_lens = (incoming.get("ri_ip_source") or "").replace("lens:", "")
        if len(inc_lens) > len(cur_lens):
            return incoming
        return current

    for row in opportunities:
        orig = row.get("case_id", "")
        canonical = canonical_case_id(orig)
        incoming = dict(row)
        incoming["case_id"] = canonical
        if orig != canonical:
            absorbed.setdefault(canonical, []).append(orig)
        if canonical not in by_canonical:
            by_canonical[canonical] = incoming
            continue
        by_canonical[canonical] = _prefer_row(by_canonical[canonical], incoming, canonical)

    merged_opps: list[dict[str, str]] = []
    for canonical, keeper in by_canonical.items():
        aliases = absorbed.get(canonical, [])
        if aliases:
            note = f"Merged alias case_ids: {', '.join(sorted(set(aliases)))}."
            existing = (keeper.get("ri_notes") or "").strip()
            keeper["ri_notes"] = f"{existing} {note}".strip() if existing else note
        merged_opps.append(keeper)

    return merged_assets, merged_opps
