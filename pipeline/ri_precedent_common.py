"""Shared precedent row helpers (avoids circular imports with tier_a)."""

from __future__ import annotations

PRECEDENT_FIELDS = [
    "case_id",
    "title_clean",
    "program_family",
    "precedent_rank",
    "precedent_type",
    "precedent_name",
    "precedent_stage",
    "precedent_notes",
    "precedent_url",
    "inferred_development",
    "inferred_financing",
    "inferred_team",
    "total_raised_usd_est",
    "last_round_usd_est",
    "value_anchor_usd",
    "value_anchor_type",
    "value_source_url",
    "financing_strategy",
    "validation_status",
    "confidence",
    "source",
]


def _parse_usd(value: str | None) -> int | None:
    try:
        n = int(float((value or "").strip()))
        return n if n > 0 else None
    except ValueError:
        return None


def apply_value_anchor(row: dict[str, str]) -> None:
    """Fill value_anchor_* from dollars when not explicitly set."""
    if row.get("value_anchor_usd"):
        return
    total = _parse_usd(row.get("total_raised_usd_est"))
    last = _parse_usd(row.get("last_round_usd_est"))
    if total:
        row["value_anchor_usd"] = str(total)
        row["value_anchor_type"] = row.get("value_anchor_type") or "total_raised"
    elif last:
        row["value_anchor_usd"] = str(last)
        row["value_anchor_type"] = row.get("value_anchor_type") or "last_round"
