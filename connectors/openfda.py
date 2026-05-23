"""OpenFDA connector (BioMCP-first)."""

from __future__ import annotations

import os
from typing import Any

from connectors._shared import FixtureCapableConnector
from connectors.biomcp_adapter import (
    extract_records,
    run_biomcp_openfda_label_get,
    run_biomcp_search,
    should_use_biomcp_backend,
)
from connectors.base import CaseConfig, ConnectorProvenance, ConnectorResult, build_query, empty_result, utc_now_iso


class OpenFdaConnector(FixtureCapableConnector):
    name = "openfda"
    source_name = "OpenFDA"
    source_url = "https://open.fda.gov/"
    api_endpoint = "biomcp search adverse-event"
    api_version = "biomcp"

    def _fetch_live(self, config: CaseConfig, provenance: ConnectorProvenance) -> ConnectorResult:
        result = empty_result(self.name, config, "live", provenance)
        if not should_use_biomcp_backend(self.name):
            return self._live_fixture_fallback(config, provenance, reason="native backend not implemented")
        records, payload, warnings = _fetch_via_biomcp(config)
        return result.model_copy(
            update={
                "query": build_query(config),
                "retrieved_at": utc_now_iso(),
                "records": records,
                "warnings": warnings,
                "raw_payload": {"backend": "biomcp", "payload": payload},
            }
        )


connector = OpenFdaConnector()


def _fetch_via_biomcp(config: CaseConfig) -> tuple[list[dict[str, Any]], dict[str, Any], list[str]]:
    warnings: list[str] = []
    payloads: dict[str, Any] = {}
    rows: list[dict[str, Any]] = []
    terms = _terms(config)
    for term in terms:
        adverse_payload, adverse_err = run_biomcp_search("adverse-event", term, limit=10, offset=0)
        if adverse_err:
            warnings.append(f"BioMCP openfda adverse warning ({term}): {adverse_err}")
        elif adverse_payload is not None:
            payloads[f"adverse:{term}"] = adverse_payload
            rows.extend(_rows_to_openfda(extract_records(adverse_payload), "adverse", term))

        label_payload, label_err = run_biomcp_search("fda-label", term, limit=8, offset=0)
        if label_err:
            warnings.append(f"BioMCP openfda label warning ({term}): {label_err}")
        elif label_payload is not None:
            payloads[f"label:{term}"] = label_payload
            rows.extend(_rows_to_openfda(extract_records(label_payload), "label", term))

    deduped = _dedupe(rows)
    _enrich_label_records(deduped, payloads, warnings)
    return deduped, payloads, warnings


def _rows_to_openfda(rows: list[dict[str, Any]], mode: str, term: str) -> list[dict[str, Any]]:
    out: list[dict[str, Any]] = []
    for idx, row in enumerate(rows):
        token = str(row.get("label_id") or row.get("id") or row.get("_id") or "").strip()
        title = str(row.get("title") or row.get("name") or f"{mode}:{term}").strip()
        if not title and not token:
            continue
        record_id = token or f"{mode}:{idx}"
        summary = str(row.get("summary") or row.get("description") or "").strip()
        out.append(
            {
                "source_record_id": f"openfda:{mode}:{record_id}",
                "source_type": "relationship",
                "source_name": "OpenFDA",
                "title": title or record_id,
                "url": "https://open.fda.gov/",
                "publication_date": None,
                "retrieved_at": utc_now_iso(),
                "raw_record_ref": f"raw/openfda_raw.json#biomcp/{mode}/{term}/{idx}",
                "subject": title or record_id,
                "predicate": "safety_or_label_signal_for",
                "object": term,
                "relationship_confidence": 0.5,
                "activity_summary": summary[:300] if summary else None,
                "fda_mode": mode,
                "fda_label_id": token if mode == "label" else None,
            }
        )
    return out


def _enrich_label_records(
    records: list[dict[str, Any]],
    payloads: dict[str, Any],
    warnings: list[str],
) -> None:
    detail_limit = _detail_limit()
    if detail_limit <= 0:
        return
    label_ids: list[str] = []
    seen: set[str] = set()
    for row in records:
        if row.get("fda_mode") != "label":
            continue
        label_id = str(row.get("fda_label_id") or "").strip()
        if not label_id or label_id in seen:
            continue
        seen.add(label_id)
        label_ids.append(label_id)
        if len(label_ids) >= detail_limit:
            break

    details: dict[str, dict[str, Any]] = {}
    for label_id in label_ids:
        detail_payload, err = run_biomcp_openfda_label_get(label_id)
        if err:
            warnings.append(f"BioMCP openfda label detail warning ({label_id}): {err}")
            continue
        if detail_payload is None:
            continue
        payloads[f"label-detail:{label_id}"] = detail_payload
        detail_rows = extract_records(detail_payload)
        if detail_rows:
            details[label_id] = detail_rows[0]

    for row in records:
        if row.get("fda_mode") != "label":
            continue
        label_id = str(row.get("fda_label_id") or "").strip()
        detail = details.get(label_id)
        if not detail:
            continue
        summary = str(detail.get("summary") or "").strip()
        if summary and not row.get("activity_summary"):
            row["activity_summary"] = summary[:500]


def _terms(config: CaseConfig) -> list[str]:
    values = [
        config.target.name,
        *config.target.aliases,
        config.indication.name,
        *config.indication.aliases,
    ]
    out: list[str] = []
    seen: set[str] = set()
    for value in values:
        text = str(value or "").strip()
        if not text:
            continue
        key = text.lower()
        if key in seen:
            continue
        seen.add(key)
        out.append(text)
    return out[:4]


def _dedupe(records: list[dict[str, Any]]) -> list[dict[str, Any]]:
    seen: set[str] = set()
    out: list[dict[str, Any]] = []
    for row in records:
        sid = str(row.get("source_record_id") or "")
        if not sid or sid in seen:
            continue
        seen.add(sid)
        out.append(row)
    return out


def _detail_limit() -> int:
    raw = (os.environ.get("BIOMCP_OPENFDA_LABEL_DETAIL_LIMIT") or "").strip()
    if not raw:
        return 8
    try:
        return max(0, int(raw))
    except ValueError:
        return 8
