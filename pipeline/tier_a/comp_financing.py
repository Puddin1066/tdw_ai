"""VC-staged financing evidence model for Tier A comparables.

Ground truth for comparables should describe how venture capital (and strategic
rounds) staged development — not only terminal valuation or public market cap.
"""

from __future__ import annotations

# Preferred anchor types when verifying startup / platform comps (in priority order).
PREFERRED_VC_ANCHOR_TYPES: tuple[str, ...] = (
    "total_raised",
    "last_round",
    "series_c",
    "series_b",
    "series_a",
    "seed_round",
    "grant",
)

# Fallback anchors for strategic / public paths (use only when no VC ladder exists).
STRATEGIC_ANCHOR_TYPES: tuple[str, ...] = (
    "acquisition",
    "market_cap",
    "post_money_valuation",
)

ANCHOR_TYPE_HINTS: dict[str, str] = {
    "total_raised": "Sum of disclosed equity rounds (Crunchbase-style lifecycle total)",
    "last_round": "Most recent VC round (amount + date)",
    "series_a": "Series A round",
    "series_b": "Series B round",
    "series_c": "Series C round",
    "seed_round": "Seed round",
    "grant": "Non-dilutive grant (SBIR/STTR, etc.) when that staged the program",
    "acquisition": "M&A exit (only when no venture ladder applies)",
    "market_cap": "Public market cap (path comp for incumbents; not a VC staging ladder)",
    "post_money_valuation": "Post-money valuation at a named round",
}


def comp_base_name(comp_name: str) -> str:
    return comp_name.split("(")[0].strip()


def default_anchor_type(comp: dict[str, str]) -> str:
    """Default value_anchor_type for interactive review."""
    existing = (comp.get("value_anchor_type") or "").strip()
    if existing:
        return existing
    ptype = (comp.get("precedent_type") or "").lower()
    if ptype in {"incumbent", "public"}:
        return "market_cap"
    if ptype == "pharma_deal":
        return "acquisition"
    return "total_raised"


def resolve_financing_queries(comp: dict[str, str]) -> list[str]:
    """Search queries biased toward VC round announcements and round totals."""
    base = comp_base_name(comp.get("precedent_name", ""))
    ptype = (comp.get("precedent_type") or "").lower()
    queries = [
        (
            f'"{base}" ("Series A" OR "Series B" OR "Series C" OR seed OR '
            f'"venture capital" OR "funding round")'
        ),
        f"{base} total funding raised venture capital investors",
        (
            f"{base} funding site:prnewswire.com OR site:businesswire.com "
            f"OR site:techcrunch.com OR site:fiercebiotech.com"
        ),
        f"{base} crunchbase funding rounds",
    ]
    if ptype in {"incumbent", "public", "ri_public", "pharma_deal"}:
        queries.append(f"{base} acquisition OR IPO OR market cap")
    return queries


def discovery_search_urls(comp_name: str, *, google_url) -> dict[str, str]:
    """Optional Google discovery URLs (CSV export); VC-first ordering."""
    base = comp_name.split("(")[0].strip()
    return {
        "search_vc_rounds": google_url(
            f'"{base}" Series seed venture funding round 2020..2026'
        ),
        "search_total_raised": google_url(f"{base} total venture funding raised investors"),
        "search_press_vc": google_url(
            f"{base} (site:prnewswire.com OR site:businesswire.com OR site:techcrunch.com) "
            f"Series OR seed OR venture"
        ),
        "search_acquisition": google_url(f"{base} acquisition price deal"),
        "search_market_cap": google_url(f"{base} market cap NASDAQ"),
    }


def inferred_financing_prompt(comp: dict[str, str]) -> str:
    return (
        "inferred_financing — VC staging ladder, e.g. "
        "'$6M seed (2017); $25M Series B (Mar 2021); $116.5M total raised'"
    )


def value_source_prompt() -> str:
    return (
        "value_source_url — PR/SEC/article that states the anchor round or total "
        "(not google.com/search; prefer round announcement over market-cap page)"
    )


def workbook_intro() -> str:
    return (
        "Financing ground truth = **how VC (and strategic) rounds staged the comp**, "
        "not just valuation. Capture `total_raised` / `last_round` / `series_*` anchors "
        "with PR links; use `market_cap` only for public/path comps without a venture ladder."
    )
