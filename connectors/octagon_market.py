"""Octagon MCP market-intelligence connector (fixture + live)."""

from __future__ import annotations

from typing import Any

from connectors._shared import FixtureCapableConnector
from connectors.base import (
    CaseConfig,
    ConnectorProvenance,
    ConnectorResult,
    build_query,
    empty_result,
    utc_now_iso,
)
from connectors.octagon_adapter import extract_records, run_octagon_search


class OctagonMarketConnector(FixtureCapableConnector):
    name = "octagon_market"
    source_name = "Octagon MCP"
    source_url = "https://octagon.ai/"
    api_endpoint = "octagon mcp search"
    api_version = "mcp"

    def _fetch_live(self, config: CaseConfig, provenance: ConnectorProvenance) -> ConnectorResult:
        result = empty_result(self.name, config, "live", provenance)
        query = build_query(config)
        topics = _build_topics(config, query.raw_query)
        rows: list[dict[str, Any]] = []
        payloads: dict[str, Any] = {}
        warnings: list[str] = []
        for topic in topics:
            payload, err = run_octagon_search(topic, limit=25)
            if err:
                warnings.append(f"Octagon warning ({topic}): {err}")
                continue
            if payload is None:
                continue
            payloads[topic] = payload
            rows.extend(_to_records(extract_records(payload), topic))

        records = _dedupe_records(rows)
        if len(records) < 5:
            warnings.append(
                f"Octagon market signal sparse ({len(records)} records) for {config.case_id}."
            )
        return result.model_copy(
            update={
                "query": query,
                "retrieved_at": utc_now_iso(),
                "records": records,
                "warnings": warnings,
                "raw_payload": {"topics": topics, "responses": payloads},
            }
        )


connector = OctagonMarketConnector()


def _build_topics(config: CaseConfig, raw_query: str) -> list[str]:
    topics = [
        raw_query,
        f"{config.target.name} {config.indication.name} company programs",
        f"{config.target.name} {config.indication.name} partnership candidates",
        f"{config.target.name} {config.indication.name} acquirer comparables",
    ]
    out: list[str] = []
    seen: set[str] = set()
    for topic in topics:
        text = topic.strip()
        if not text:
            continue
        key = text.lower()
        if key in seen:
            continue
        seen.add(key)
        out.append(text)
    return out


def _to_records(rows: list[dict[str, Any]], topic: str) -> list[dict[str, Any]]:
    out: list[dict[str, Any]] = []
    for idx, row in enumerate(rows):
        name = str(
            row.get("company")
            or row.get("name")
            or row.get("organization")
            or row.get("title")
            or ""
        ).strip()
        if not name:
            continue
        rid = str(row.get("id") or row.get("ticker") or f"row{idx}").strip()
        role = str(row.get("role") or row.get("type") or "comparable").strip().lower()
        predicate = "comparable_for"
        if "partner" in role:
            predicate = "partner_candidate_for"
        elif "acquirer" in role:
            predicate = "acquirer_candidate_for"
        score_raw = row.get("score") or row.get("confidence")
        try:
            score = float(score_raw) if score_raw is not None else 0.5
        except (TypeError, ValueError):
            score = 0.5
        score = max(0.0, min(1.0, score))
        out.append(
            {
                "source_record_id": f"octagon:{rid}",
                "source_type": "relationship",
                "source_name": "Octagon MCP",
                "title": name,
                "url": row.get("url"),
                "publication_date": None,
                "retrieved_at": utc_now_iso(),
                "raw_record_ref": f"raw/octagon_market_raw.json#topic/{topic}/{idx}",
                "biology_source": "octagon",
                "target_id": None,
                "disease_id": None,
                "association_score": None,
                "molecule_chembl_id": None,
                "mechanism_of_action": str(row.get("summary") or row.get("rationale") or "") or None,
                "activity_summary": str(row.get("budget") or row.get("program_stage") or "") or None,
                "subject": name,
                "predicate": predicate,
                "object": topic,
                "relationship_confidence": score,
            }
        )
    return out


def _dedupe_records(records: list[dict[str, Any]]) -> list[dict[str, Any]]:
    seen: set[str] = set()
    out: list[dict[str, Any]] = []
    for record in records:
        sid = str(record.get("source_record_id", ""))
        if not sid or sid in seen:
            continue
        seen.add(sid)
        out.append(record)
    return out
