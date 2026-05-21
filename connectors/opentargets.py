"""Open Targets Platform API connector (fixture + live)."""

from __future__ import annotations

from typing import Any

import httpx

from connectors._shared import FixtureCapableConnector
from connectors.biomcp_adapter import extract_records, run_biomcp_search, should_use_biomcp_backend
from connectors.base import (
    CaseConfig,
    ConnectorProvenance,
    ConnectorResult,
    build_query,
    empty_result,
    utc_now_iso,
)

# Live endpoints (not implemented for MVP):
# - GraphQL: https://api.platform.opentargets.org/api/v4/graphql
# Auth: none for public GraphQL
# Pagination: cursor-based in GraphQL
# Rate limit: conservative 2 req/s
# Retry: backoff on 5xx; timeout 60s


class OpenTargetsConnector(FixtureCapableConnector):
    name = "opentargets"
    source_name = "Open Targets"
    source_url = "https://platform.opentargets.org/"
    api_endpoint = "https://api.platform.opentargets.org/api/v4/graphql"
    api_version = "v4"

    def _fetch_live(self, config: CaseConfig, provenance: ConnectorProvenance) -> ConnectorResult:
        result = empty_result(self.name, config, "live", provenance)
        query = build_query(config)
        if should_use_biomcp_backend(self.name):
            biomcp_records, biomcp_payload, biomcp_warnings = _fetch_via_biomcp(config)
            if biomcp_records:
                return result.model_copy(
                    update={
                        "query": query,
                        "retrieved_at": utc_now_iso(),
                        "records": biomcp_records,
                        "warnings": biomcp_warnings,
                        "raw_payload": {"backend": "biomcp", "payload": biomcp_payload},
                    }
                )
            # Fall through to native path to avoid hard-failing live runs.
            if biomcp_warnings:
                result = result.model_copy(update={"warnings": biomcp_warnings})
        terms = _build_terms(config)
        records: list[dict[str, Any]] = []
        raw_payloads: list[dict[str, Any]] = []
        warnings: list[str] = list(result.warnings)

        with httpx.Client(timeout=30.0) as client:
            for term in terms:
                payload = _search_graphql(client, self.api_endpoint, term)
                hits = _extract_hits(payload)
                raw_payloads.append({"term": term, "hit_count": len(hits), "payload": payload})
                records.extend(_hits_to_records(hits, term))

        deduped = _dedupe_records(records)
        if len(deduped) < 5:
            warnings.append(
                f"Open Targets returned sparse signal ({len(deduped)} records) for target/indication."
            )
        return result.model_copy(
            update={
                "query": query,
                "retrieved_at": utc_now_iso(),
                "records": deduped,
                "warnings": warnings,
                "raw_payload": {"query_terms": terms, "responses": raw_payloads},
            }
        )


connector = OpenTargetsConnector()


SEARCH_QUERY = """
query SearchOpenTargets($queryString: String!) {
  search(queryString: $queryString, page: { index: 0, size: 25 }) {
    total
    hits {
      id
      name
      description
      entity
    }
  }
}
"""


def _build_terms(config: CaseConfig) -> list[str]:
    values = [
        config.target.name,
        *config.target.aliases,
        config.indication.name,
        *config.indication.aliases,
        f"{config.target.name} {config.indication.name}",
    ]
    deduped: list[str] = []
    seen: set[str] = set()
    for value in values:
        text = value.strip()
        if not text:
            continue
        key = text.lower()
        if key in seen:
            continue
        seen.add(key)
        deduped.append(text)
    return deduped


def _search_graphql(client: httpx.Client, endpoint: str, term: str) -> dict[str, Any]:
    response = client.post(
        endpoint,
        json={"query": SEARCH_QUERY, "variables": {"queryString": term}},
    )
    response.raise_for_status()
    payload = response.json()
    return payload if isinstance(payload, dict) else {}


def _extract_hits(payload: dict[str, Any]) -> list[dict[str, Any]]:
    data = payload.get("data", {})
    if not isinstance(data, dict):
        return []
    search = data.get("search", {})
    if not isinstance(search, dict):
        return []
    hits = search.get("hits", [])
    if not isinstance(hits, list):
        return []
    return [hit for hit in hits if isinstance(hit, dict)]


def _hits_to_records(hits: list[dict[str, Any]], term: str) -> list[dict[str, Any]]:
    records: list[dict[str, Any]] = []
    for idx, hit in enumerate(hits):
        hit_id = str(hit.get("id", "")).strip()
        if not hit_id:
            continue
        entity = str(hit.get("entity", "other")).lower()
        name = str(hit.get("name") or hit_id).strip()
        desc = str(hit.get("description") or "").strip()
        source_type = "target_biology"
        title = f"{name} ({entity})"
        if entity == "drug":
            source_type = "compound"
        elif entity not in {"target", "disease"}:
            source_type = "relationship"

        records.append(
            {
                "source_record_id": f"opentargets:{entity}:{hit_id}",
                "source_type": source_type,
                "source_name": "Open Targets",
                "title": title,
                "url": f"https://platform.opentargets.org/{entity}/{hit_id}",
                "publication_date": None,
                "retrieved_at": utc_now_iso(),
                "raw_record_ref": f"raw/opentargets_raw.json#hits/{term}/{idx}",
                "biology_source": "opentargets",
                "target_id": hit_id if entity == "target" else None,
                "disease_id": hit_id if entity == "disease" else None,
                "association_score": 0.6 if entity in {"target", "disease"} else None,
                "molecule_chembl_id": None,
                "mechanism_of_action": desc or None,
                "activity_summary": desc or None,
                "subject": term,
                "predicate": "related_to",
                "object": name,
                "relationship_confidence": 0.6,
            }
        )
    return records


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


def _fetch_via_biomcp(config: CaseConfig) -> tuple[list[dict[str, Any]], dict[str, Any], list[str]]:
    warnings: list[str] = []
    payloads: dict[str, Any] = {}
    records: list[dict[str, Any]] = []
    entities = ("disease", "gene", "drug")
    for term in _build_terms(config):
        for entity in entities:
            for offset in (0, 25):
                payload, err = run_biomcp_search(entity, term, limit=25, offset=offset)
                if err:
                    warnings.append(
                        f"BioMCP opentargets search warning ({entity}:{term}, offset={offset}): {err}"
                    )
                    continue
                if payload is None:
                    continue
                key = f"{entity}:{term}|offset={offset}"
                payloads[key] = payload
                records.extend(_biomcp_records_to_ot(extract_records(payload), key))
    return _dedupe_records(records), payloads, warnings


def _biomcp_records_to_ot(rows: list[dict[str, Any]], term: str) -> list[dict[str, Any]]:
    out: list[dict[str, Any]] = []
    for idx, row in enumerate(rows):
        name = str(row.get("name") or row.get("label") or row.get("title") or "").strip()
        raw_id = str(row.get("id") or row.get("_id") or row.get("identifier") or "").strip()
        if not name and not raw_id:
            continue
        entity = str(row.get("entity") or row.get("type") or "other").lower()
        source_type = "target_biology"
        if entity in {"drug", "compound"}:
            source_type = "compound"
        elif entity not in {"target", "disease"}:
            source_type = "relationship"
        identifier = raw_id or f"row{idx}"
        out.append(
            {
                "source_record_id": f"opentargets:{entity}:{identifier}",
                "source_type": source_type,
                "source_name": "Open Targets",
                "title": name or identifier,
                "url": row.get("url"),
                "publication_date": None,
                "retrieved_at": utc_now_iso(),
                "raw_record_ref": f"raw/opentargets_raw.json#biomcp/{term}/{idx}",
                "biology_source": "opentargets",
                "target_id": identifier if entity == "target" else None,
                "disease_id": identifier if entity == "disease" else None,
                "association_score": 0.55 if entity in {"target", "disease"} else None,
                "molecule_chembl_id": row.get("molecule_chembl_id"),
                "mechanism_of_action": str(row.get("description") or "") or None,
                "activity_summary": str(row.get("summary") or "") or None,
                "subject": term,
                "predicate": "related_to",
                "object": name or identifier,
                "relationship_confidence": 0.55,
            }
        )
    return out
