"""Local document connector for user-supplied case files (fixture + live stub)."""

from __future__ import annotations

from connectors._shared import FixtureCapableConnector
from connectors.base import CaseConfig, ConnectorProvenance, ConnectorResult

# Live mode would read from configs/cases/{case_id}/local_docs/ or similar.
# Fixture mode loads tests/fixtures/cases/{case_id}/raw/local_docs*.json


class LocalDocsConnector(FixtureCapableConnector):
    name = "local_docs"
    source_name = "Local Documents"
    source_url = "file://local"
    api_endpoint = None
    api_version = None

    def _fetch_fixture(self, config: CaseConfig, provenance: ConnectorProvenance) -> ConnectorResult:
        if not config.sources.local_docs:
            result = super()._fetch_fixture(config, provenance)
            return result.model_copy(
                update={
                    "warnings": [*result.warnings, "local_docs disabled in case config; skipping fetch"]
                }
            )
        return super()._fetch_fixture(config, provenance)

    def _fetch_live(self, config: CaseConfig, provenance: ConnectorProvenance) -> ConnectorResult:
        raise NotImplementedError(
            "Local docs live fetch is not implemented; use mode='fixture'."
        )


connector = LocalDocsConnector()
