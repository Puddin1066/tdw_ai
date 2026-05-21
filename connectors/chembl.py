"""ChEMBL REST API connector (fixture + live)."""

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
# - Base: https://www.ebi.ac.uk/chembl/api/data/
# - Example: molecule/search.json?q={target}
# Auth: none
# Pagination: limit/offset
# Rate limit: conservative 1 req/s
# Retry: backoff on 5xx; timeout 30s


class ChEMBLConnector(FixtureCapableConnector):
    name = "chembl"
    source_name = "ChEMBL"
    source_url = "https://www.ebi.ac.uk/chembl/"
    api_endpoint = "https://www.ebi.ac.uk/chembl/api/data/"
    api_version = "chembl_33"

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
        target_terms = [config.target.name, *config.target.aliases]
        records: list[dict[str, Any]] = []
        raw_payloads: list[dict[str, Any]] = []
        with httpx.Client(timeout=30.0) as client:
            for term in _dedupe_terms(target_terms):
                target_payload = _get_json(
                    client,
                    f"{self.api_endpoint}target/search.json",
                    {"q": term, "limit": 8},
                )
                targets = target_payload.get("targets", [])
                if isinstance(targets, list):
                    for idx, target in enumerate(targets):
                        if isinstance(target, dict):
                            record = _target_record(target, idx)
                            if record:
                                records.append(record)
                raw_payloads.append({"target_term": term, "payload": target_payload})

            mol_query = f"{config.target.name} {config.indication.name}"
            molecule_payload = _get_json(
                client,
                f"{self.api_endpoint}molecule/search.json",
                {"q": mol_query, "limit": 16},
            )
            molecules = molecule_payload.get("molecules", [])
            if isinstance(molecules, list):
                for idx, molecule in enumerate(molecules):
                    if isinstance(molecule, dict):
                        record = _molecule_record(molecule, idx)
                        if record:
                            records.append(record)
            raw_payloads.append({"molecule_query": mol_query, "payload": molecule_payload})

        deduped = _dedupe_records(records)
        warnings: list[str] = list(result.warnings)
        if len(deduped) < 5:
            warnings.append(f"ChEMBL returned sparse signal ({len(deduped)} records).")
        return result.model_copy(
            update={
                "query": query,
                "retrieved_at": utc_now_iso(),
                "records": deduped,
                "warnings": warnings,
                "raw_payload": {"responses": raw_payloads},
            }
        )


connector = ChEMBLConnector()


def _get_json(client: httpx.Client, url: str, params: dict[str, Any]) -> dict[str, Any]:
    response = client.get(url, params=params)
    response.raise_for_status()
    payload = response.json()
    return payload if isinstance(payload, dict) else {}


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


def _target_record(target: dict[str, Any], idx: int) -> dict[str, Any] | None:
    chembl_id = str(target.get("target_chembl_id", "")).strip()
    pref_name = str(target.get("pref_name") or "").strip()
    if not chembl_id and not pref_name:
        return None
    title = pref_name or chembl_id
    return {
        "source_record_id": f"chembl:target:{chembl_id or idx}",
        "source_type": "target_biology",
        "source_name": "ChEMBL",
        "title": title,
        "url": f"https://www.ebi.ac.uk/chembl/target_report_card/{chembl_id}/" if chembl_id else None,
        "publication_date": None,
        "retrieved_at": utc_now_iso(),
        "raw_record_ref": f"raw/chembl_raw.json#targets/{idx}",
        "biology_source": "chembl",
        "target_id": chembl_id or None,
        "disease_id": None,
        "association_score": None,
        "molecule_chembl_id": None,
        "mechanism_of_action": str(target.get("target_type") or "") or None,
        "activity_summary": str(target.get("organism") or "") or None,
        "subject": pref_name or chembl_id,
        "predicate": "target_profile",
        "object": str(target.get("target_type") or "target"),
        "relationship_confidence": 0.55,
    }


def _molecule_record(molecule: dict[str, Any], idx: int) -> dict[str, Any] | None:
    chembl_id = str(molecule.get("molecule_chembl_id", "")).strip()
    pref_name = str(molecule.get("pref_name") or "").strip()
    if not chembl_id and not pref_name:
        return None
    title = pref_name or chembl_id
    max_phase = molecule.get("max_phase")
    max_phase_text = str(max_phase) if max_phase is not None else "unknown"
    return {
        "source_record_id": f"chembl:molecule:{chembl_id or idx}",
        "source_type": "compound",
        "source_name": "ChEMBL",
        "title": title,
        "url": f"https://www.ebi.ac.uk/chembl/compound_report_card/{chembl_id}/" if chembl_id else None,
        "publication_date": None,
        "retrieved_at": utc_now_iso(),
        "raw_record_ref": f"raw/chembl_raw.json#molecules/{idx}",
        "biology_source": "chembl",
        "target_id": None,
        "disease_id": None,
        "association_score": None,
        "molecule_chembl_id": chembl_id or None,
        "mechanism_of_action": str(molecule.get("molecule_type") or "") or None,
        "activity_summary": f"max_phase={max_phase_text}",
        "subject": title,
        "predicate": "candidate_for",
        "object": "oncology",
        "relationship_confidence": 0.5,
    }


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
    rows: list[dict[str, Any]] = []
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
        for offset in (0, 25):
            payload, err = run_biomcp_search("drug", term, limit=25, offset=offset)
            if err:
                warnings.append(f"BioMCP chembl search warning ({term}, offset={offset}): {err}")
                continue
            if payload is None:
                continue
            payloads[f"{term}|offset={offset}"] = payload
            rows.extend(_biomcp_rows_to_chembl(extract_records(payload), term))
    return _dedupe_records(rows), payloads, warnings


def _biomcp_rows_to_chembl(rows: list[dict[str, Any]], term: str) -> list[dict[str, Any]]:
    out: list[dict[str, Any]] = []
    for idx, row in enumerate(rows):
        name = str(row.get("name") or row.get("label") or row.get("title") or "").strip()
        raw_id = str(
            row.get("chembl_id")
            or row.get("molecule_chembl_id")
            or row.get("id")
            or row.get("_id")
            or ""
        ).strip()
        if not name and not raw_id:
            continue
        entity = str(row.get("entity") or row.get("type") or "drug").lower()
        source_type = "compound" if entity in {"drug", "compound", "molecule"} else "relationship"
        identifier = raw_id or f"row{idx}"
        out.append(
            {
                "source_record_id": f"chembl:biomcp:{identifier}",
                "source_type": source_type,
                "source_name": "ChEMBL",
                "title": name or identifier,
                "url": row.get("url"),
                "publication_date": None,
                "retrieved_at": utc_now_iso(),
                "raw_record_ref": f"raw/chembl_raw.json#biomcp/{term}/{idx}",
                "biology_source": "chembl",
                "target_id": None,
                "disease_id": None,
                "association_score": None,
                "molecule_chembl_id": identifier,
                "mechanism_of_action": str(row.get("mechanism") or row.get("description") or "") or None,
                "activity_summary": str(row.get("summary") or "") or None,
                "subject": name or identifier,
                "predicate": "candidate_for",
                "object": config_indication_hint(term),
                "relationship_confidence": 0.5,
            }
        )
    return out


def config_indication_hint(term: str) -> str:
    return term
