"""Public data source connectors."""

from connectors.base import BaseConnector, CaseConfig, ConnectorResult
from connectors.biothings import connector as biothings_connector
from connectors.chembl import connector as chembl_connector
from connectors.clinicaltrials import connector as clinicaltrials_connector
from connectors.gwas import connector as gwas_connector
from connectors.local_docs import connector as local_docs_connector
from connectors.openfda import connector as openfda_connector
from connectors.octagon_market import connector as octagon_market_connector
from connectors.opentargets import connector as opentargets_connector
from connectors.pharmgkb import connector as pharmgkb_connector
from connectors.pubmed import connector as pubmed_connector
from connectors.reactome import connector as reactome_connector
from connectors.uniprot import connector as uniprot_connector

CONNECTORS: dict[str, BaseConnector] = {
    "pubmed": pubmed_connector,
    "clinicaltrials": clinicaltrials_connector,
    "opentargets": opentargets_connector,
    "chembl": chembl_connector,
    "biothings": biothings_connector,
    "uniprot": uniprot_connector,
    "reactome": reactome_connector,
    "gwas": gwas_connector,
    "pharmgkb": pharmgkb_connector,
    "openfda": openfda_connector,
    "octagon_market": octagon_market_connector,
    "local_docs": local_docs_connector,
}

__all__ = [
    "BaseConnector",
    "CaseConfig",
    "ConnectorResult",
    "CONNECTORS",
    "pubmed_connector",
    "clinicaltrials_connector",
    "opentargets_connector",
    "chembl_connector",
    "biothings_connector",
    "uniprot_connector",
    "reactome_connector",
    "gwas_connector",
    "pharmgkb_connector",
    "openfda_connector",
    "octagon_market_connector",
    "local_docs_connector",
]
