"""Shared connector implementation helpers."""

from __future__ import annotations

from connectors.base import (
    CaseConfig,
    ConnectorMode,
    ConnectorProvenance,
    ConnectorResult,
    empty_result,
    load_fixture_payload,
    merge_fixture_into_result,
    result_from_exception,
)


class FixtureCapableConnector:
    """Base class for connectors with fixture and live modes."""

    name: str
    source_name: str
    source_url: str
    api_endpoint: str | None = None
    api_version: str | None = None

    def provenance(self) -> ConnectorProvenance:
        return ConnectorProvenance(
            source_name=self.source_name,
            source_url=self.source_url,
            api_endpoint=self.api_endpoint,
            api_version=self.api_version,
        )

    def fetch(self, config: CaseConfig, mode: ConnectorMode) -> ConnectorResult:
        provenance = self.provenance()
        try:
            if mode == "fixture":
                return self._fetch_fixture(config, provenance)
            return self._fetch_live(config, provenance)
        except NotImplementedError as exc:
            return result_from_exception(self.name, config, mode, provenance, exc)
        except Exception as exc:  # noqa: BLE001 — recoverable source failures stay in envelope
            return result_from_exception(self.name, config, mode, provenance, exc)

    def _fetch_fixture(self, config: CaseConfig, provenance: ConnectorProvenance) -> ConnectorResult:
        result = empty_result(self.name, config, "fixture", provenance)
        payload, warning = load_fixture_payload(self.name, config.case_id)
        if payload is None:
            warnings = [warning] if warning else ["Fixture payload missing"]
            return result.model_copy(update={"warnings": warnings})
        merged = merge_fixture_into_result(result, payload)
        if not merged.records and not merged.warnings:
            merged = merged.model_copy(
                update={"warnings": ["Fixture loaded but records list is empty"]}
            )
        return merged

    def _fetch_live(self, config: CaseConfig, provenance: ConnectorProvenance) -> ConnectorResult:
        raise NotImplementedError(
            f"Live mode for {self.name} is not implemented; use fixture mode or extend _fetch_live."
        )
