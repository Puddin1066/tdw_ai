"""ClinicalTrials.gov API v2 connector (fixture + live)."""

from __future__ import annotations

import os
from typing import Any

import httpx

from connectors._shared import FixtureCapableConnector
from connectors.biomcp_adapter import extract_records, run_biomcp_search
from connectors.base import (
    CaseConfig,
    ConnectorProvenance,
    ConnectorResult,
    build_query,
    empty_result,
    utc_now_iso,
)

# Live endpoints (not implemented for MVP):
# - Base: https://clinicaltrials.gov/api/v2/
# - Search: GET /studies?query.term={query}&pageSize={n}
# Auth: none
# Pagination: pageToken
# Rate limit: conservative 1 req/s
# Retry: backoff on 5xx; timeout 30s


class ClinicalTrialsConnector(FixtureCapableConnector):
    name = "clinicaltrials"
    source_name = "ClinicalTrials.gov"
    source_url = "https://clinicaltrials.gov/"
    api_endpoint = "https://clinicaltrials.gov/api/v2/"
    api_version = "v2"

    def _fetch_live(self, config: CaseConfig, provenance: ConnectorProvenance) -> ConnectorResult:
        result = empty_result(self.name, config, "live", provenance)
        query = build_query(config)
        if not query.raw_query.strip():
            return result.model_copy(
                update={
                    "query": query,
                    "retrieved_at": utc_now_iso(),
                    "warnings": [
                        *result.warnings,
                        "ClinicalTrials skipped: no target/indication anchor provided; add either field for retrieval.",
                    ],
                }
            )
        if _use_biomcp_backend():
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
        page_size = max(10, min(config.limits.max_trials, 100))
        search_terms = _build_search_terms(config, query.raw_query)
        max_trials = max(1, min(config.limits.max_trials, 150))
        combined_studies: list[dict[str, Any]] = []
        raw_queries: list[dict[str, Any]] = []
        try:
            with httpx.Client(timeout=30.0) as client:
                for term in search_terms:
                    payload = _fetch_studies_for_term(client, self.api_endpoint, term, page_size)
                    studies = payload.get("studies", [])
                    if isinstance(studies, list):
                        combined_studies.extend(studies)
                    raw_queries.append(
                        {
                            "term": term,
                            "returned_studies": len(studies) if isinstance(studies, list) else 0,
                            "payload": payload,
                        }
                    )
        except Exception as exc:  # noqa: BLE001
            return result.model_copy(
                update={"errors": [*result.errors, f"ClinicalTrials.gov live fetch failed: {exc}"]}
            )

        unique_trials = _dedupe_trials(combined_studies)
        scored_records: list[dict[str, Any]] = []
        for idx, study in enumerate(unique_trials):
            if not isinstance(study, dict):
                continue
            normalized = _normalize_study(study, idx)
            if not normalized:
                continue
            normalized["match_score"] = _relevance_score(config, normalized)
            scored_records.append(normalized)
        scored_records.sort(
            key=lambda r: (
                float(r.get("match_score") or 0.0),
                float(r.get("enrollment_count") or 0),
            ),
            reverse=True,
        )
        records = scored_records[:max_trials]

        warnings: list[str] = list(result.warnings)
        if not records:
            warnings.append("ClinicalTrials.gov live fetch returned zero studies.")
        elif len(records) < 8:
            warnings.append(
                f"Sparse clinical trial coverage ({len(records)} records). "
                "Consider broadening connector search terms."
            )
        return result.model_copy(
            update={
                "query": query,
                "retrieved_at": utc_now_iso(),
                "records": records,
                "warnings": warnings,
                "raw_payload": {
                    "query_terms": search_terms,
                    "returned_total_studies": len(combined_studies),
                    "deduped_trials": len(unique_trials),
                    "query_payloads": raw_queries,
                },
            }
        )


connector = ClinicalTrialsConnector()


def _normalize_study(study: dict[str, Any], idx: int) -> dict[str, Any] | None:
    protocol = _dict(study.get("protocolSection"))
    ident = _dict(protocol.get("identificationModule"))
    status_mod = _dict(protocol.get("statusModule"))
    design_mod = _dict(protocol.get("designModule"))
    sponsor_mod = _dict(protocol.get("sponsorCollaboratorsModule"))
    conditions_mod = _dict(protocol.get("conditionsModule"))
    arms_mod = _dict(protocol.get("armsInterventionsModule"))

    nct_id = _str(ident.get("nctId"))
    if not nct_id:
        return None
    brief_title = _str(ident.get("briefTitle")) or f"Trial {nct_id}"
    interventions = _extract_interventions(arms_mod)
    conditions = _list_of_str(conditions_mod.get("conditions"))
    sponsor = _str(sponsor_mod.get("leadSponsor", {}).get("name")) if isinstance(
        sponsor_mod.get("leadSponsor"), dict
    ) else None

    return {
        "source_record_id": f"clinicaltrials:{nct_id}",
        "source_type": "clinical_trial",
        "source_name": "ClinicalTrials.gov",
        "title": brief_title,
        "url": f"https://clinicaltrials.gov/study/{nct_id}",
        "publication_date": _str(status_mod.get("completionDateStruct", {}).get("date"))
        if isinstance(status_mod.get("completionDateStruct"), dict)
        else None,
        "retrieved_at": utc_now_iso(),
        "raw_record_ref": f"raw/clinicaltrials_raw.json#studies/{idx}",
        "nct_id": nct_id,
        "brief_title": brief_title,
        "official_title": _str(ident.get("officialTitle")),
        "phase": _extract_phase(design_mod),
        "overall_status": _str(status_mod.get("overallStatus")) or "Unknown",
        "study_type": _str(design_mod.get("studyType")),
        "sponsor": sponsor,
        "interventions": interventions,
        "conditions": conditions,
        "start_date": _str(status_mod.get("startDateStruct", {}).get("date"))
        if isinstance(status_mod.get("startDateStruct"), dict)
        else None,
        "completion_date": _str(status_mod.get("completionDateStruct", {}).get("date"))
        if isinstance(status_mod.get("completionDateStruct"), dict)
        else None,
        "enrollment_count": _extract_enrollment(design_mod),
    }


def _dict(value: Any) -> dict[str, Any]:
    return value if isinstance(value, dict) else {}


def _str(value: Any) -> str | None:
    if value is None:
        return None
    text = str(value).strip()
    return text or None


def _list_of_str(value: Any) -> list[str]:
    if not isinstance(value, list):
        return []
    out: list[str] = []
    for item in value:
        text = _str(item)
        if text:
            out.append(text)
    return out


def _extract_interventions(arms_mod: dict[str, Any]) -> list[str]:
    entries = arms_mod.get("interventions")
    if not isinstance(entries, list):
        return []
    out: list[str] = []
    for intervention in entries:
        if not isinstance(intervention, dict):
            continue
        name = _str(intervention.get("name"))
        if name:
            out.append(name)
    return out


def _extract_phase(design_mod: dict[str, Any]) -> str | None:
    phases = design_mod.get("phases")
    if isinstance(phases, list):
        joined = ", ".join(str(p).strip() for p in phases if str(p).strip())
        return joined or None
    return _str(phases)


def _extract_enrollment(design_mod: dict[str, Any]) -> int | None:
    enrollment = design_mod.get("enrollmentInfo")
    if not isinstance(enrollment, dict):
        return None
    value = enrollment.get("count")
    if value is None:
        return None
    try:
        count = int(value)
    except (TypeError, ValueError):
        return None
    return count if count >= 0 else None


def _fetch_studies_for_term(
    client: httpx.Client,
    api_endpoint: str,
    term: str,
    page_size: int,
) -> dict[str, Any]:
    response = client.get(
        f"{api_endpoint}studies",
        params={
            "query.term": term,
            "pageSize": page_size,
            "countTotal": "true",
            "format": "json",
        },
    )
    response.raise_for_status()
    payload = response.json()
    if isinstance(payload, dict):
        return payload
    return {"studies": []}


def _build_search_terms(config: CaseConfig, raw_query: str) -> list[str]:
    target_terms = [config.target.name, *config.target.aliases]
    indication_terms = [config.indication.name, *config.indication.aliases]

    def _dedupe(values: list[str]) -> list[str]:
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

    target_terms = _dedupe(target_terms)
    indication_terms = _dedupe(indication_terms)
    target_clause = " OR ".join(target_terms)
    indication_clause = " OR ".join(indication_terms)
    short_target = target_terms[:2] if len(target_terms) > 2 else target_terms
    short_indication = indication_terms[:2] if len(indication_terms) > 2 else indication_terms
    terms: list[str] = []
    if raw_query.strip():
        terms.append(raw_query)
    if target_clause and config.indication.name.strip():
        terms.append(f"({target_clause}) AND ({config.indication.name.strip()})")
    if short_target and indication_clause:
        terms.append(f"({short_target[0]}) AND ({indication_clause})")
    if target_clause:
        terms.append(f"({target_clause}) AND (solid tumor OR cancer)")
    if short_target and short_indication:
        terms.append(f"({short_target[0]}) AND ({' OR '.join(short_indication)})")
    if not terms:
        terms.append("solid tumor")
    return _dedupe(terms)


def _dedupe_trials(studies: list[dict[str, Any]]) -> list[dict[str, Any]]:
    by_nct: dict[str, dict[str, Any]] = {}
    for study in studies:
        if not isinstance(study, dict):
            continue
        protocol = _dict(study.get("protocolSection"))
        ident = _dict(protocol.get("identificationModule"))
        nct_id = _str(ident.get("nctId"))
        if not nct_id:
            continue
        if nct_id not in by_nct:
            by_nct[nct_id] = study
    return list(by_nct.values())


def _relevance_score(config: CaseConfig, record: dict[str, Any]) -> float:
    text_parts = [
        str(record.get("title") or ""),
        str(record.get("official_title") or ""),
        " ".join(str(v) for v in record.get("conditions", [])),
        " ".join(str(v) for v in record.get("interventions", [])),
    ]
    haystack = " ".join(text_parts).lower()
    score = 0.0
    for term in [config.target.name, *config.target.aliases]:
        if term and term.lower() in haystack:
            score += 0.22
    for term in [config.indication.name, *config.indication.aliases]:
        if term and term.lower() in haystack:
            score += 0.18
    status = str(record.get("overall_status") or "").upper()
    if status in {"RECRUITING", "ACTIVE_NOT_RECRUITING", "NOT_YET_RECRUITING"}:
        score += 0.2
    phase = str(record.get("phase") or "").upper()
    if "PHASE2" in phase or "PHASE3" in phase:
        score += 0.1
    return round(min(score, 1.0), 4)


def _use_biomcp_backend() -> bool:
    backend = (
        os.environ.get("CLINICALTRIALS_BACKEND")
        or os.environ.get("CONNECTOR_BACKEND")
        or "biomcp"
    ).strip().lower()
    return backend == "biomcp"


def _fetch_via_biomcp(config: CaseConfig) -> tuple[list[dict[str, Any]], dict[str, Any], list[str]]:
    warnings: list[str] = []
    payloads: dict[str, Any] = {}
    rows: list[dict[str, Any]] = []
    terms = _build_search_terms(config, build_query(config).raw_query)
    per_page = max(10, min(config.limits.max_trials, 50))
    offsets = (0, per_page)
    for term in terms:
        for offset in offsets:
            payload, err = run_biomcp_search("trial", term, limit=per_page, offset=offset)
            if err:
                warnings.append(
                    f"BioMCP clinicaltrials search warning ({term}, offset={offset}): {err}"
                )
                continue
            if payload is None:
                continue
            payloads[f"{term}|offset={offset}"] = payload
            rows.extend(_biomcp_rows_to_trials(extract_records(payload), term))

    indication = config.indication.name.strip()
    if indication:
        for target_term in [config.target.name, *config.target.aliases]:
            text = target_term.strip()
            if not text:
                continue
            for offset in offsets:
                payload, err = run_biomcp_search(
                    "trial",
                    None,
                    limit=per_page,
                    offset=offset,
                    options=["-c", indication, "-i", text],
                )
                if err:
                    warnings.append(
                        f"BioMCP clinicaltrials intervention warning ({text}, offset={offset}): {err}"
                    )
                    continue
                if payload is None:
                    continue
                key = f"condition={indication}|intervention={text}|offset={offset}"
                payloads[key] = payload
                rows.extend(_biomcp_rows_to_trials(extract_records(payload), key))
    deduped: list[dict[str, Any]] = []
    seen: set[str] = set()
    for row in rows:
        sid = str(row.get("source_record_id", ""))
        if not sid or sid in seen:
            continue
        seen.add(sid)
        deduped.append(row)
    return deduped[: config.limits.max_trials], payloads, warnings


def _biomcp_rows_to_trials(rows: list[dict[str, Any]], term: str) -> list[dict[str, Any]]:
    out: list[dict[str, Any]] = []
    for idx, row in enumerate(rows):
        nct = str(row.get("nct_id") or row.get("id") or row.get("identifier") or "").strip().upper()
        if not nct.startswith("NCT") or len(nct) != 11:
            # keep deterministic id for schema; this preserves nonstandard rows as low-confidence.
            continue
        title = str(row.get("title") or row.get("brief_title") or f"Trial {nct}").strip()
        status = str(row.get("overall_status") or row.get("status") or "Unknown").strip() or "Unknown"
        interventions = row.get("interventions")
        conditions = row.get("conditions")
        out.append(
            {
                "source_record_id": f"clinicaltrials:{nct}",
                "source_type": "clinical_trial",
                "source_name": "ClinicalTrials.gov",
                "title": title,
                "url": row.get("url") or f"https://clinicaltrials.gov/study/{nct}",
                "publication_date": row.get("publication_date"),
                "retrieved_at": utc_now_iso(),
                "raw_record_ref": f"raw/clinicaltrials_raw.json#biomcp/{term}/{idx}",
                "nct_id": nct,
                "brief_title": title,
                "official_title": row.get("official_title"),
                "phase": row.get("phase"),
                "overall_status": status,
                "study_type": row.get("study_type"),
                "sponsor": row.get("sponsor"),
                "interventions": interventions if isinstance(interventions, list) else [],
                "conditions": conditions if isinstance(conditions, list) else [],
                "start_date": row.get("start_date"),
                "completion_date": row.get("completion_date"),
                "enrollment_count": row.get("enrollment_count"),
            }
        )
    return out
