"""PubMed connector via NCBI E-utilities (fixture + live stub)."""

from __future__ import annotations

from connectors._shared import FixtureCapableConnector
from connectors.base import CaseConfig, ConnectorProvenance, ConnectorResult

# Live endpoints (not implemented for MVP):
# - Base: https://eutils.ncbi.nlm.nih.gov/entrez/eutils/
# - Search: esearch.fcgi?db=pubmed&term={query}
# - Fetch: efetch.fcgi?db=pubmed&id={pmids}&retmode=xml
# Auth: optional NCBI API key via NCBI_API_KEY env
# Pagination: retmax/retstart on esearch
# Rate limit: ~3 req/s without key, 10/s with key
# Retry: exponential backoff on 429/5xx; timeout 30s


class PubMedConnector(FixtureCapableConnector):
    name = "pubmed"
    source_name = "PubMed"
    source_url = "https://pubmed.ncbi.nlm.nih.gov/"
    api_endpoint = "https://eutils.ncbi.nlm.nih.gov/entrez/eutils/"
    api_version = "e-utilities"

    def _fetch_live(self, config: CaseConfig, provenance: ConnectorProvenance) -> ConnectorResult:
        # Optional httpx skeleton for future live integration:
        # async with httpx.AsyncClient(timeout=30) as client:
        #     await client.get(f"{self.api_endpoint}esearch.fcgi", params={...})
        raise NotImplementedError("PubMed live fetch is not implemented; use mode='fixture'.")


connector = PubMedConnector()
