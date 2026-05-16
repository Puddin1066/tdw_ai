"""ChEMBL REST API connector (fixture + live stub)."""

from __future__ import annotations

from connectors._shared import FixtureCapableConnector
from connectors.base import CaseConfig, ConnectorProvenance, ConnectorResult

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
        raise NotImplementedError("ChEMBL live fetch is not implemented; use mode='fixture'.")


connector = ChEMBLConnector()
