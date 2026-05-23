"""Shared helper for BioMCP-first connector implementations."""

from __future__ import annotations

import os
from typing import Any

from connectors.base import CaseConfig, utc_now_iso
from connectors.biomcp_adapter import (
    extract_records,
    run_biomcp_gene_get,
    run_biomcp_search,
    run_biomcp_variant_get,
)


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
    deduped = _dedupe_records(records)
    _enrich_records(connector_name, entity, deduped, payloads, warnings)
    return deduped, payloads, warnings


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


def _enrich_records(
    connector_name: str,
    entity: str,
    records: list[dict[str, Any]],
    payloads: dict[str, Any],
    warnings: list[str],
) -> None:
    detail_limit = _detail_limit(connector_name)
    if detail_limit <= 0 or not records:
        return
    tokens: list[str] = []
    seen: set[str] = set()
    for row in records:
        token = _record_token(row)
        if not token or token in seen:
            continue
        seen.add(token)
        tokens.append(token)
        if len(tokens) >= detail_limit:
            break

    details: dict[str, dict[str, Any]] = {}
    for token in tokens:
        payload, err = _run_detail(connector_name, entity, token)
        if err:
            warnings.append(f"BioMCP {connector_name} detail warning ({token}): {err}")
            continue
        if payload is None:
            continue
        payloads[f"detail:{entity}:{token}"] = payload
        rows = extract_records(payload)
        if rows:
            details[token] = rows[0]

    for row in records:
        token = _record_token(row)
        detail = details.get(token)
        if not detail:
            continue
        summary = str(
            detail.get("summary")
            or detail.get("description")
            or detail.get("mechanism")
            or detail.get("evidence")
            or ""
        ).strip()
        if summary and not row.get("activity_summary"):
            row["activity_summary"] = summary[:300]
        if not row.get("title"):
            title = str(detail.get("name") or detail.get("title") or detail.get("symbol") or "").strip()
            if title:
                row["title"] = title


def _run_detail(
    connector_name: str,
    entity: str,
    token: str,
) -> tuple[dict[str, Any] | None, str | None]:
    if connector_name in {"uniprot", "reactome"} or entity in {"protein", "pathway"}:
        return run_biomcp_gene_get(token, enrich="reactome")
    if connector_name == "gwas" or entity == "gwas":
        return run_biomcp_gene_get(token, enrich="gwas")
    if connector_name == "pharmgkb" or entity == "pgx":
        if token.lower().startswith("rs") or token.lower().startswith("chr"):
            payload, err = run_biomcp_variant_get(token, extensive=True)
            if payload is not None:
                return payload, None
            if err and "not found" not in err.lower():
                return None, err
        return run_biomcp_gene_get(token, enrich="gwas")
    return None, "no configured detail path"


def _record_token(record: dict[str, Any]) -> str:
    source_record_id = str(record.get("source_record_id") or "").strip()
    if source_record_id:
        parts = source_record_id.split(":", 2)
        if len(parts) == 3 and parts[2].strip():
            return parts[2].strip()
    for key in ("subject", "title"):
        text = str(record.get(key) or "").strip()
        if text:
            return text
    return ""


def _detail_limit(connector_name: str) -> int:
    default = 10
    env_key = f"BIOMCP_{connector_name.upper()}_DETAIL_LIMIT"
    raw = (os.environ.get(env_key) or "").strip()
    if not raw:
        return default
    try:
        return max(0, int(raw))
    except ValueError:
        return default
