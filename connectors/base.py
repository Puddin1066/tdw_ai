"""Shared connector protocol, result envelope, and fixture loading."""

from __future__ import annotations

import json
from dataclasses import dataclass, field
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Literal, Protocol, runtime_checkable

from pydantic import BaseModel, Field

try:
    from pipeline.types import (  # type: ignore[attr-defined]
        CaseConfig,
        IndicationConfig,
        LimitsConfig,
        SourcesConfig,
        TargetConfig,
    )
except ImportError:

    @dataclass
    class TargetConfig:
        name: str
        canonical_id: str | None = None
        aliases: list[str] = field(default_factory=list)

    @dataclass
    class IndicationConfig:
        name: str
        aliases: list[str] = field(default_factory=list)

    @dataclass
    class SourcesConfig:
        pubmed: bool = True
        clinicaltrials: bool = True
        opentargets: bool = True
        chembl: bool = True
        biothings: bool = True
        local_docs: bool = False

    @dataclass
    class LimitsConfig:
        max_literature_records: int = 50
        max_trials: int = 100
        max_evidence_rows: int = 100

    @dataclass
    class CaseConfig:
        case_id: str
        display_name: str
        workflow: str
        version: str
        target: TargetConfig
        indication: IndicationConfig
        sources: SourcesConfig
        limits: LimitsConfig


ConnectorMode = Literal["fixture", "live"]
REPO_ROOT = Path(__file__).resolve().parents[1]
FIXTURE_CONNECTORS_DIR = REPO_ROOT / "tests" / "fixtures" / "connectors"
FIXTURE_CASES_DIR = REPO_ROOT / "tests" / "fixtures" / "cases"


class ConnectorQuery(BaseModel):
    target: str
    indication: str
    raw_query: str


class ConnectorProvenance(BaseModel):
    source_name: str
    source_url: str
    api_endpoint: str | None = None
    api_version: str | None = None


class ConnectorResult(BaseModel):
    connector_name: str
    case_id: str
    mode: ConnectorMode
    query: ConnectorQuery
    retrieved_at: str
    records: list[dict[str, Any]] = Field(default_factory=list)
    errors: list[str] = Field(default_factory=list)
    warnings: list[str] = Field(default_factory=list)
    provenance: ConnectorProvenance
    raw_payload: dict[str, Any] | None = None


def utc_now_iso() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat().replace("+00:00", "Z")


def build_raw_query(target: Any, indication: Any) -> str:
    target_terms = [target.name, *target.aliases]
    indication_terms = [indication.name, *indication.aliases]
    target_clause = " OR ".join(dict.fromkeys(target_terms))
    indication_clause = " OR ".join(dict.fromkeys(indication_terms))
    return f"({target_clause}) AND ({indication_clause})"


def build_query(config: CaseConfig) -> ConnectorQuery:
    raw_query = build_raw_query(config.target, config.indication)
    return ConnectorQuery(
        target=config.target.name,
        indication=config.indication.name,
        raw_query=raw_query,
    )


def fixture_paths(connector_name: str, case_id: str) -> list[Path]:
    case_raw = FIXTURE_CASES_DIR / case_id / "raw"
    return [
        FIXTURE_CONNECTORS_DIR / f"{connector_name}_{case_id}.json",
        case_raw / f"{connector_name}.json",
        case_raw / f"{connector_name}_raw.json",
    ]


def load_fixture_payload(connector_name: str, case_id: str) -> tuple[dict[str, Any] | None, str | None]:
    """Load fixture JSON; returns (payload, warning_if_missing)."""
    for path in fixture_paths(connector_name, case_id):
        if path.is_file():
            try:
                with path.open(encoding="utf-8") as handle:
                    return json.load(handle), None
            except (json.JSONDecodeError, OSError) as exc:
                return None, f"Failed to read fixture {path}: {exc}"
    searched = ", ".join(str(p) for p in fixture_paths(connector_name, case_id))
    return None, f"No fixture found for {connector_name}/{case_id} (searched: {searched})"


def merge_fixture_into_result(
    base: ConnectorResult,
    payload: dict[str, Any],
) -> ConnectorResult:
    """Apply fixture file contents onto a ConnectorResult skeleton."""
    records = payload.get("records", base.records)
    errors = list(payload.get("errors", base.errors))
    warnings = list(payload.get("warnings", base.warnings))
    provenance = base.provenance
    if "provenance" in payload and isinstance(payload["provenance"], dict):
        provenance = ConnectorProvenance(**{**base.provenance.model_dump(), **payload["provenance"]})
    query = base.query
    if "query" in payload and isinstance(payload["query"], dict):
        query = ConnectorQuery(**{**base.query.model_dump(), **payload["query"]})
    retrieved_at = payload.get("retrieved_at", base.retrieved_at)
    raw_payload = payload.get("raw_payload", payload if "records" not in payload else payload.get("raw_payload"))
    return base.model_copy(
        update={
            "query": query,
            "retrieved_at": retrieved_at,
            "records": records,
            "errors": errors,
            "warnings": warnings,
            "provenance": provenance,
            "raw_payload": raw_payload,
        }
    )


def empty_result(
    connector_name: str,
    config: CaseConfig,
    mode: ConnectorMode,
    provenance: ConnectorProvenance,
) -> ConnectorResult:
    return ConnectorResult(
        connector_name=connector_name,
        case_id=config.case_id,
        mode=mode,
        query=build_query(config),
        retrieved_at=utc_now_iso(),
        provenance=provenance,
    )


def result_from_exception(
    connector_name: str,
    config: CaseConfig,
    mode: ConnectorMode,
    provenance: ConnectorProvenance,
    exc: BaseException,
    *,
    warning: bool = False,
) -> ConnectorResult:
    message = f"{type(exc).__name__}: {exc}"
    result = empty_result(connector_name, config, mode, provenance)
    if warning:
        return result.model_copy(update={"warnings": [message]})
    return result.model_copy(update={"errors": [message]})


@runtime_checkable
class BaseConnector(Protocol):
    name: str

    def fetch(self, config: CaseConfig, mode: ConnectorMode) -> ConnectorResult: ...
