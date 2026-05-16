"""ClinicalTrials.gov API v2 connector (fixture + live stub)."""

from __future__ import annotations

from connectors._shared import FixtureCapableConnector
from connectors.base import CaseConfig, ConnectorProvenance, ConnectorResult

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
        raise NotImplementedError(
            "ClinicalTrials.gov live fetch is not implemented; use mode='fixture'."
        )


connector = ClinicalTrialsConnector()
