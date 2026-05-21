"""BioThings Explorer / APIs connector (fixture + live)."""

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
# - BioThings: https://mygene.info/v3/query?q=...
# - Explorer: https://biothings.io/explorer/
# Auth: none for public endpoints
# Pagination: from/size
# Rate limit: conservative 2 req/s
# Retry: backoff on 5xx; timeout 30s


class BioThingsConnector(FixtureCapableConnector):
    name = "biothings"
    source_name = "BioThings"
    source_url = "https://biothings.io/"
    api_endpoint = "https://mygene.info/v3/"
    api_version = "v3"

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
            if biomcp_warnings:
                result = result.model_copy(update={"warnings": biomcp_warnings})
        terms = _dedupe_terms([config.target.name, *config.target.aliases, config.indication.name])
        records: list[dict[str, Any]] = []
        raw_payloads: list[dict[str, Any]] = []
        with httpx.Client(timeout=30.0) as client:
            for term in terms:
                payload = _query_mygene(client, self.api_endpoint, term)
                hits = payload.get("hits", [])
                if isinstance(hits, list):
                    records.extend(_hits_to_records(hits, term))
                raw_payloads.append({"term": term, "payload": payload, "hit_count": len(hits) if isinstance(hits, list) else 0})

        deduped = _dedupe_records(records)
        warnings: list[str] = list(result.warnings)
        if len(deduped) < 5:
            warnings.append(f"BioThings returned sparse signal ({len(deduped)} records).")
        return result.model_copy(
            update={
                "query": query,
                "retrieved_at": utc_now_iso(),
                "records": deduped,
                "warnings": warnings,
                "raw_payload": {"responses": raw_payloads},
            }
        )


connector = BioThingsConnector()


def _query_mygene(client: httpx.Client, endpoint: str, term: str) -> dict[str, Any]:
    response = client.get(
        f"{endpoint}query",
        params={
            "q": term,
            "species": "human",
            "size": 25,
            "fields": "symbol,name,taxid,entrezgene,summary,pathway",
        },
    )
    response.raise_for_status()
    payload = response.json()
    return payload if isinstance(payload, dict) else {}


def _hits_to_records(hits: list[dict[str, Any]], term: str) -> list[dict[str, Any]]:
    records: list[dict[str, Any]] = []
    for idx, hit in enumerate(hits):
        if not isinstance(hit, dict):
            continue
        gene_id = str(hit.get("_id", "")).strip() or str(hit.get("entrezgene", "")).strip()
        symbol = str(hit.get("symbol", "")).strip()
        name = str(hit.get("name", "")).strip()
        if not gene_id and not symbol and not name:
            continue
        pathway = hit.get("pathway")
        pathway_text = ""
        if isinstance(pathway, dict):
            keys = sorted(pathway.keys())
            pathway_text = ", ".join(keys[:3])
        summary = str(hit.get("summary", "")).strip()
        records.append(
            {
                "source_record_id": f"biothings:gene:{gene_id or idx}",
                "source_type": "relationship",
                "source_name": "BioThings",
                "title": symbol or name or f"Gene {gene_id}",
                "url": f"https://www.ncbi.nlm.nih.gov/gene/{gene_id}" if gene_id else None,
                "publication_date": None,
                "retrieved_at": utc_now_iso(),
                "raw_record_ref": f"raw/biothings_raw.json#hits/{term}/{idx}",
                "biology_source": "biothings",
                "target_id": gene_id or None,
                "disease_id": None,
                "association_score": 0.5,
                "molecule_chembl_id": None,
                "mechanism_of_action": summary[:240] if summary else None,
                "activity_summary": pathway_text or None,
                "subject": symbol or name or gene_id,
                "predicate": "contextual_signal_for",
                "object": term,
                "relationship_confidence": 0.5,
            }
        )
    return records


def _dedupe_terms(values: list[str]) -> list[str]:
    seen: set[str] = set()
    out: list[str] = []
    for value in values:
        text = value.strip()
        if not text:
            continue
        key = text.lower()
        if key in seen:
            continue
        seen.add(key)
        out.append(text)
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


def _fetch_via_biomcp(config: CaseConfig) -> tuple[list[dict[str, Any]], dict[str, Any], list[str]]:
    warnings: list[str] = []
    payloads: dict[str, Any] = {}
    records: list[dict[str, Any]] = []
    terms = _dedupe_terms(
        [
            config.target.name,
            *config.target.aliases,
            config.indication.name,
            *config.indication.aliases,
            f"{config.target.name} {config.indication.name}",
        ]
    )
    for term in terms:
        for entity in ("gene", "disease"):
            for offset in (0, 25):
                payload, err = run_biomcp_search(entity, term, limit=25, offset=offset)
                if err:
                    warnings.append(
                        f"BioMCP biothings search warning ({entity}:{term}, offset={offset}): {err}"
                    )
                    continue
                if payload is None:
                    continue
                key = f"{entity}:{term}|offset={offset}"
                payloads[key] = payload
                records.extend(_biomcp_rows_to_biothings(extract_records(payload), key))
    return _dedupe_records(records), payloads, warnings


def _biomcp_rows_to_biothings(rows: list[dict[str, Any]], term: str) -> list[dict[str, Any]]:
    out: list[dict[str, Any]] = []
    for idx, row in enumerate(rows):
        symbol = str(row.get("symbol") or row.get("name") or row.get("label") or "").strip()
        gene_id = str(row.get("id") or row.get("_id") or row.get("entrezgene") or "").strip()
        if not symbol and not gene_id:
            continue
        identifier = gene_id or f"row{idx}"
        summary = str(row.get("summary") or row.get("description") or "").strip()
        out.append(
            {
                "source_record_id": f"biothings:biomcp:{identifier}",
                "source_type": "relationship",
                "source_name": "BioThings",
                "title": symbol or identifier,
                "url": row.get("url"),
                "publication_date": None,
                "retrieved_at": utc_now_iso(),
                "raw_record_ref": f"raw/biothings_raw.json#biomcp/{term}/{idx}",
                "biology_source": "biothings",
                "target_id": identifier,
                "disease_id": None,
                "association_score": 0.5,
                "molecule_chembl_id": None,
                "mechanism_of_action": summary[:240] if summary else None,
                "activity_summary": str(row.get("pathways") or row.get("pathway") or "") or None,
                "subject": symbol or identifier,
                "predicate": "contextual_signal_for",
                "object": term,
                "relationship_confidence": 0.5,
            }
        )
    return out
