"""Shared helper for BioMCP-first connector implementations."""

from __future__ import annotations

from typing import Any

from connectors.base import CaseConfig, utc_now_iso
from connectors.biomcp_adapter import extract_records, run_biomcp_search


def build_biomcp_terms(config: CaseConfig) -> list[str]:
    values = [
        config.target.name,
        *config.target.aliases,
        config.indication.name,
        *config.indication.aliases,
        config.input_profile.biology.modality,
        config.input_profile.biology.mechanism_direction,
        config.input_profile.program.asset,
        config.input_profile.program.company,
        f"{config.target.name} {config.indication.name}",
    ]
    deduped: list[str] = []
    seen: set[str] = set()
    for value in values:
        text = str(value or "").strip()
        if not text:
            continue
        key = text.lower()
        if key in seen:
            continue
        seen.add(key)
        deduped.append(text)
    return deduped


def fetch_records(
    *,
    connector_name: str,
    source_name: str,
    entity: str,
    config: CaseConfig,
    limit: int = 25,
    offsets: tuple[int, ...] = (0, 25),
    terms: list[str] | None = None,
    ignore_error_substrings: tuple[str, ...] = (),
) -> tuple[list[dict[str, Any]], dict[str, Any], list[str]]:
    warnings: list[str] = []
    payloads: dict[str, Any] = {}
    records: list[dict[str, Any]] = []
    query_terms = terms if terms is not None else build_biomcp_terms(config)
    if not query_terms:
        warnings.append(
            f"BioMCP {connector_name} skipped: no semantic anchors provided (target/indication/input profile)."
        )
        return records, payloads, warnings
    for term in query_terms:
        for offset in offsets:
            payload, err = run_biomcp_search(entity, term, limit=limit, offset=offset)
            if err:
                lowered = err.lower()
                if any(token.lower() in lowered for token in ignore_error_substrings):
                    continue
                warnings.append(
                    f"BioMCP {connector_name} search warning ({entity}:{term}, offset={offset}): {err}"
                )
                continue
            if payload is None:
                continue
            key = f"{entity}:{term}|offset={offset}"
            payloads[key] = payload
            rows = extract_records(payload)
            records.extend(_rows_to_records(rows, connector_name, source_name, entity, key))
    return _dedupe_records(records), payloads, warnings


def _rows_to_records(
    rows: list[dict[str, Any]],
    connector_name: str,
    source_name: str,
    entity: str,
    query_key: str,
) -> list[dict[str, Any]]:
    out: list[dict[str, Any]] = []
    for idx, row in enumerate(rows):
        identifier = str(
            row.get("id")
            or row.get("_id")
            or row.get("identifier")
            or row.get("accession")
            or row.get("rsid")
            or ""
        ).strip()
        label = str(
            row.get("title")
            or row.get("name")
            or row.get("symbol")
            or row.get("label")
            or row.get("drug")
            or row.get("pathway")
            or row.get("term")
            or ""
        ).strip()
        if not identifier and not label:
            continue
        record_id = identifier or f"row{idx}"
        summary = str(
            row.get("description")
            or row.get("summary")
            or row.get("mechanism")
            or row.get("evidence")
            or ""
        ).strip()
        out.append(
            {
                "source_record_id": f"{connector_name}:{entity}:{record_id}",
                "source_type": "relationship",
                "source_name": source_name,
                "title": label or record_id,
                "url": row.get("url"),
                "publication_date": row.get("date"),
                "retrieved_at": utc_now_iso(),
                "raw_record_ref": f"raw/{connector_name}_raw.json#biomcp/{query_key}/{idx}",
                "subject": label or record_id,
                "predicate": "contextual_signal_for",
                "object": query_key,
                "relationship_confidence": 0.5,
                "activity_summary": summary[:300] if summary else None,
            }
        )
    return out


def _dedupe_records(records: list[dict[str, Any]]) -> list[dict[str, Any]]:
    seen: set[str] = set()
    out: list[dict[str, Any]] = []
    for record in records:
        source_record_id = str(record.get("source_record_id") or "")
        if not source_record_id or source_record_id in seen:
            continue
        seen.add(source_record_id)
        out.append(record)
    return out
