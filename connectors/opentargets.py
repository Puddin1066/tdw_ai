"""Open Targets Platform API connector (fixture + live stub)."""

from __future__ import annotations

from connectors._shared import FixtureCapableConnector
from connectors.base import CaseConfig, ConnectorProvenance, ConnectorResult

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
        raise NotImplementedError(
            "Open Targets live fetch is not implemented; use mode='fixture'."
        )


connector = OpenTargetsConnector()
