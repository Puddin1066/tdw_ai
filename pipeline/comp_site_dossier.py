"""Comp site dossier bundle I/O and merge into RI precedents / exhibits."""

from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

DATA_ROOT = Path(__file__).resolve().parents[1] / "data" / "ri"
DOSSIERS_PATH = DATA_ROOT / "ri_comp_site_dossiers.json"
FIXTURE_PATH = Path(__file__).resolve().parents[1] / "tests" / "fixtures" / "ri" / "comp_site_dossiers.json"

SCHEMA_VERSION = 1


def _utc_now() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat().replace("+00:00", "Z")


def dossier_key(case_id: str, precedent_name: str) -> str:
    return f"{case_id}::{precedent_name}"


def empty_bundle() -> dict[str, Any]:
    return {
        "schema_version": SCHEMA_VERSION,
        "generated_by": "pipeline/enrich_ri_comp_sites.py",
        "dossier_count": 0,
        "by_key": {},
        "by_case_id": {},
    }


def load_dossier_bundle(path: Path | None = None) -> dict[str, Any]:
    target = path or DOSSIERS_PATH
    if not target.exists():
        return empty_bundle()
    data = json.loads(target.read_text(encoding="utf-8"))
    if not isinstance(data, dict):
        return empty_bundle()
    data.setdefault("by_key", {})
    data.setdefault("by_case_id", {})
    if data["by_key"] and not data["by_case_id"]:
        rebuild_by_case_index(data)
    return data


def save_dossier_bundle(bundle: dict[str, Any], path: Path | None = None) -> Path:
    target = path or DOSSIERS_PATH
    target.parent.mkdir(parents=True, exist_ok=True)
    by_key = bundle.get("by_key") or {}
    bundle["dossier_count"] = len(by_key)
    bundle["schema_version"] = SCHEMA_VERSION
    target.write_text(json.dumps(bundle, indent=2) + "\n", encoding="utf-8")
    return target


def _infer_comparable_fit(precedent: dict[str, str]) -> str:
    notes = (precedent.get("precedent_notes") or "").lower()
    ptype = (precedent.get("precedent_type") or "").lower()
    if "analog" in notes or "not " in notes and "mechanism" in notes:
        return "analog"
    if ptype in {"incumbent", "pharma_deal"} or "strategic" in (precedent.get("financing_strategy") or "").lower():
        return "strategic"
    return "direct"


def build_ri_parallel(
    *,
    case_title: str,
    precedent: dict[str, str],
    dossier_body: dict[str, Any],
) -> str:
    dev = (precedent.get("inferred_development") or "").strip()
    fin = (precedent.get("inferred_financing") or "").strip()
    name = precedent.get("precedent_name") or precedent.get("name") or "Comparable"
    parts = [f"For {case_title}, {name} shows a precedent path"]
    if dev:
        parts.append(f"via {dev}")
    if fin:
        parts.append(f"({fin})")
    if dossier_body.get("reimbursement_notes"):
        parts.append("with published reimbursement/access positioning on their site")
    elif dossier_body.get("clinical_milestones"):
        parts.append("with regulatory/clinical milestones documented on their site")
    return " ".join(parts).strip() + "."


def wrap_dossier_entry(
    *,
    case_id: str,
    case_title: str,
    precedent: dict[str, str],
    dossier_body: dict[str, Any],
    warnings: list[str],
    fetched: bool,
    human_reviewed: bool = False,
) -> dict[str, Any]:
    status = "reviewed" if human_reviewed else ("partial" if dossier_body.get("science_summary") else "pending")
    if fetched and (dossier_body.get("key_publications") or dossier_body.get("reimbursement_notes")):
        status = "partial" if not human_reviewed else "reviewed"
    return {
        "case_id": case_id,
        "case_title": case_title,
        "precedent_name": precedent.get("precedent_name") or precedent.get("name", ""),
        "precedent_rank": int(precedent.get("precedent_rank") or precedent.get("rank") or 0),
        "comparable_fit": _infer_comparable_fit(precedent),
        "dossier_status": status,
        "human_reviewed": human_reviewed,
        "fetched_at": _utc_now() if fetched else "",
        "warnings": warnings,
        "ri_parallel": build_ri_parallel(
            case_title=case_title,
            precedent=precedent,
            dossier_body=dossier_body,
        ),
        **dossier_body,
    }


def select_precedents_for_enrichment(
    precedents: list[dict[str, str]],
    *,
    max_comps: int = 2,
) -> list[dict[str, str]]:
    """Pick lead verified comp + secondary for site dossier fetch."""
    if not precedents:
        return []
    ranked = sorted(precedents, key=lambda r: int(r.get("precedent_rank") or r.get("rank") or 99))
    selected: list[dict[str, str]] = []
    seen: set[str] = set()

    def add(row: dict[str, str]) -> None:
        name = (row.get("precedent_name") or row.get("name") or "").strip()
        if not name or name in seen:
            return
        if not (row.get("precedent_url") or row.get("url") or "").strip():
            return
        seen.add(name)
        selected.append(row)

    for row in ranked:
        status = (row.get("validation_status") or "").lower()
        anchor = (row.get("value_anchor_usd") or "").strip()
        if status in {"verified", "estimated"} and anchor:
            add(row)
            break

    for row in ranked:
        add(row)
        if len(selected) >= max_comps:
            break

    return selected[:max_comps]


def rebuild_by_case_index(bundle: dict[str, Any]) -> None:
    by_case: dict[str, Any] = {}
    for entry in (bundle.get("by_key") or {}).values():
        if not isinstance(entry, dict):
            continue
        cid = entry.get("case_id", "")
        if not cid:
            continue
        bucket = by_case.setdefault(
            cid,
            {
                "case_id": cid,
                "case_title": entry.get("case_title", ""),
                "dossier_count": 0,
                "precedents": {},
                "rollup": {
                    "clinical_path": "",
                    "reimbursement_path": "",
                    "kol_pattern": "",
                },
            },
        )
        name = entry.get("precedent_name", "")
        if name:
            bucket["precedents"][name] = entry
        bucket["dossier_count"] = len(bucket["precedents"])
        bucket["rollup"] = build_case_rollup(list(bucket["precedents"].values()))
    bundle["by_case_id"] = by_case


def build_case_rollup(entries: list[dict[str, Any]]) -> dict[str, str]:
    clinical_bits: list[str] = []
    reimb_bits: list[str] = []
    kol_bits: list[str] = []

    for entry in sorted(entries, key=lambda e: int(e.get("precedent_rank") or 99)):
        name = entry.get("precedent_name") or "Comparable"
        for item in entry.get("clinical_milestones") or []:
            if isinstance(item, dict) and item.get("text"):
                clinical_bits.append(f"{name}: {item['text'][:160]}")
        for item in entry.get("reimbursement_notes") or []:
            if isinstance(item, dict) and item.get("text"):
                reimb_bits.append(f"{name}: {item['text'][:160]}")
        for item in entry.get("kol_signals") or []:
            if isinstance(item, dict) and item.get("text"):
                kol_bits.append(f"{name}: {item['text'][:120]}")

    return {
        "clinical_path": " | ".join(clinical_bits[:3]),
        "reimbursement_path": " | ".join(reimb_bits[:3]),
        "kol_pattern": " | ".join(kol_bits[:3]),
    }


def merge_dossier_into_precedent(
    precedent: dict[str, Any],
    dossier_entry: dict[str, Any] | None,
) -> dict[str, Any]:
    enriched = dict(precedent)
    if not dossier_entry:
        return enriched
    enriched["comparable_fit"] = dossier_entry.get("comparable_fit", "direct")
    enriched["site_dossier"] = {
        "dossier_status": dossier_entry.get("dossier_status", "pending"),
        "human_reviewed": bool(dossier_entry.get("human_reviewed")),
        "fetched_at": dossier_entry.get("fetched_at", ""),
        "comparable_fit": dossier_entry.get("comparable_fit", "direct"),
        "ri_parallel": dossier_entry.get("ri_parallel", ""),
        "site_map": dossier_entry.get("site_map") or {},
        "science_summary": dossier_entry.get("science_summary", ""),
        "key_publications": dossier_entry.get("key_publications") or [],
        "clinical_milestones": dossier_entry.get("clinical_milestones") or [],
        "kol_signals": dossier_entry.get("kol_signals") or [],
        "reimbursement_notes": dossier_entry.get("reimbursement_notes") or [],
        "warnings": dossier_entry.get("warnings") or [],
    }
    return enriched


def dossiers_for_case(bundle: dict[str, Any], case_id: str) -> dict[str, dict[str, Any]]:
    case_bucket = (bundle.get("by_case_id") or {}).get(case_id) or {}
    precedents = case_bucket.get("precedents") or {}
    if isinstance(precedents, dict):
        return precedents
    return {}


def case_rollup(bundle: dict[str, Any], case_id: str) -> dict[str, str]:
    case_bucket = (bundle.get("by_case_id") or {}).get(case_id) or {}
    rollup = case_bucket.get("rollup") or {}
    return {
        "clinical_path": str(rollup.get("clinical_path") or ""),
        "reimbursement_path": str(rollup.get("reimbursement_path") or ""),
        "kol_pattern": str(rollup.get("kol_pattern") or ""),
    }
