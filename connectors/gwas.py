"""GWAS Catalog connector (BioMCP-first)."""

from __future__ import annotations

from connectors._shared import FixtureCapableConnector
from connectors.biomcp_adapter import should_use_biomcp_backend
from connectors.biomcp_generic import fetch_records
from connectors.base import CaseConfig, ConnectorProvenance, ConnectorResult, build_query, empty_result, utc_now_iso


class GwasConnector(FixtureCapableConnector):
    name = "gwas"
    source_name = "GWAS Catalog"
    source_url = "https://www.ebi.ac.uk/gwas/"
    api_endpoint = "biomcp search gwas"
    api_version = "biomcp"

    def _fetch_live(self, config: CaseConfig, provenance: ConnectorProvenance) -> ConnectorResult:
        result = empty_result(self.name, config, "live", provenance)
        if not should_use_biomcp_backend(self.name):
            return self._live_fixture_fallback(config, provenance, reason="native backend not implemented")
        records, payload, warnings = fetch_records(
            connector_name=self.name,
            source_name=self.source_name,
            entity="gwas",
            config=config,
            limit=25,
            offsets=(0,),
            terms=_gene_symbol_terms(config),
        )
        return result.model_copy(
            update={
                "query": build_query(config),
                "retrieved_at": utc_now_iso(),
                "records": records,
                "warnings": warnings,
                "raw_payload": {"backend": "biomcp", "payload": payload},
            }
        )


connector = GwasConnector()


def _gene_symbol_terms(config: CaseConfig) -> list[str]:
    candidates = [config.target.name, *config.target.aliases]
    out: list[str] = []
    seen: set[str] = set()
    for raw in candidates:
        text = str(raw or "").strip().upper()
        if not text or " " in text:
            continue
        if not any(char.isalpha() for char in text):
            continue
        if text in seen:
            continue
        seen.add(text)
        out.append(text)
    return out[:3]
