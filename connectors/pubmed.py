"""PubMed connector via NCBI E-utilities (fixture + live)."""

from __future__ import annotations

import os
from typing import Any
from xml.etree import ElementTree

import httpx

from connectors._shared import FixtureCapableConnector
from connectors.base import (
    CaseConfig,
    ConnectorProvenance,
    ConnectorResult,
    build_query,
    empty_result,
    utc_now_iso,
)

# Live endpoints:
# - Base: https://eutils.ncbi.nlm.nih.gov/entrez/eutils/
# - Search: esearch.fcgi?db=pubmed&term={query}&retmode=json
# - Fetch: efetch.fcgi?db=pubmed&id={pmids}&retmode=xml
# Auth: optional NCBI_API_KEY env
# Rate limit: ~3 req/s without key; use api_key when available


class PubMedConnector(FixtureCapableConnector):
    name = "pubmed"
    source_name = "PubMed"
    source_url = "https://pubmed.ncbi.nlm.nih.gov/"
    api_endpoint = "https://eutils.ncbi.nlm.nih.gov/entrez/eutils/"
    api_version = "e-utilities"

    def _fetch_live(self, config: CaseConfig, provenance: ConnectorProvenance) -> ConnectorResult:
        result = empty_result(self.name, config, "live", provenance)
        query = build_query(config)
        retmax = min(config.limits.max_literature_records, 100)
        params: dict[str, Any] = {
            "db": "pubmed",
            "term": query.raw_query,
            "retmax": retmax,
            "retmode": "json",
        }
        api_key = os.environ.get("NCBI_API_KEY")
        if api_key:
            params["api_key"] = api_key

        try:
            with httpx.Client(timeout=30.0) as client:
                search_resp = client.get(f"{self.api_endpoint}esearch.fcgi", params=params)
                search_resp.raise_for_status()
                search_data = search_resp.json()
        except Exception as exc:  # noqa: BLE001
            return result.model_copy(update={"errors": [f"PubMed esearch failed: {exc}"]})

        idlist = search_data.get("esearchresult", {}).get("idlist", [])
        if not idlist:
            return result.model_copy(
                update={
                    "warnings": ["PubMed esearch returned zero PMIDs"],
                    "retrieved_at": utc_now_iso(),
                }
            )

        records: list[dict[str, Any]] = []
        try:
            with httpx.Client(timeout=60.0) as client:
                fetch_params: dict[str, Any] = {
                    "db": "pubmed",
                    "id": ",".join(idlist),
                    "retmode": "xml",
                }
                if api_key:
                    fetch_params["api_key"] = api_key
                fetch_resp = client.get(f"{self.api_endpoint}efetch.fcgi", params=fetch_params)
                fetch_resp.raise_for_status()
                records = _parse_pubmed_xml(fetch_resp.text, query.raw_query)
        except Exception as exc:  # noqa: BLE001
            # Fallback: minimal records from IDs only
            for pmid in idlist:
                records.append(_minimal_record(pmid, query.raw_query))
            return result.model_copy(
                update={
                    "records": records,
                    "warnings": [f"efetch failed, using PMID stubs: {exc}"],
                    "retrieved_at": utc_now_iso(),
                }
            )

        return result.model_copy(
            update={
                "records": records,
                "retrieved_at": utc_now_iso(),
                "query": query,
            }
        )


def _minimal_record(pmid: str, raw_query: str) -> dict[str, Any]:
    return {
        "source_record_id": f"pubmed:{pmid}",
        "source_type": "literature",
        "source_name": "PubMed",
        "title": f"PubMed record {pmid} (live fetch)",
        "url": f"https://pubmed.ncbi.nlm.nih.gov/{pmid}/",
        "publication_date": None,
        "retrieved_at": utc_now_iso(),
        "raw_record_ref": f"raw/pubmed_raw.json#pmid/{pmid}",
        "pmid": pmid,
        "doi": None,
    }


def _parse_pubmed_xml(xml_text: str, raw_query: str) -> list[dict[str, Any]]:
    records: list[dict[str, Any]] = []
    root = ElementTree.fromstring(xml_text)
    for article in root.findall(".//PubmedArticle"):
        pmid_el = article.find(".//PMID")
        if pmid_el is None or not pmid_el.text:
            continue
        pmid = pmid_el.text.strip()
        title_el = article.find(".//ArticleTitle")
        title = title_el.text.strip() if title_el is not None and title_el.text else f"PubMed {pmid}"
        year_el = article.find(".//PubDate/Year")
        pub_date = year_el.text.strip() if year_el is not None and year_el.text else None
        doi_el = article.find(".//ArticleId[@IdType='doi']")
        doi = doi_el.text.strip() if doi_el is not None and doi_el.text else None
        records.append(
            {
                "source_record_id": f"pubmed:{pmid}",
                "source_type": "literature",
                "source_name": "PubMed",
                "title": title,
                "url": f"https://pubmed.ncbi.nlm.nih.gov/{pmid}/",
                "publication_date": pub_date,
                "retrieved_at": utc_now_iso(),
                "raw_record_ref": f"raw/pubmed_raw.json#pmid/{pmid}",
                "pmid": pmid,
                "doi": doi,
            }
        )
    if not records:
        return [_minimal_record("00000000", raw_query)]
    return records


connector = PubMedConnector()
