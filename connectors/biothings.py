"""BioThings Explorer / APIs connector (fixture + live stub)."""

from __future__ import annotations

from connectors._shared import FixtureCapableConnector
from connectors.base import CaseConfig, ConnectorProvenance, ConnectorResult

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
        raise NotImplementedError("BioThings live fetch is not implemented; use mode='fixture'.")


connector = BioThingsConnector()
