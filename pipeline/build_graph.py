"""Build knowledge_graph.json from normalized entities and source artifacts."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from pipeline.provenance import build_provenance, utc_now_iso
from pipeline.types import SCHEMA_VERSION, CaseConfig


def _entity_nodes(entities: list[dict[str, Any]]) -> list[dict[str, Any]]:
    nodes: list[dict[str, Any]] = []
    for entity in entities:
        entity_type = entity.get("entity_type", "other")
        nodes.append(
            {
                "node_id": entity["entity_id"],
                "label": entity.get("display_name") or entity.get("canonical_name"),
                "node_type": entity_type if entity_type != "clinical_trial" else "trial",
                "entity_id": entity["entity_id"],
            }
        )
    return nodes


def _entity_edges(entities: list[dict[str, Any]], case_id: str) -> list[dict[str, Any]]:
    genes = [e for e in entities if e.get("entity_type") in {"gene", "protein"}]
    diseases = [e for e in entities if e.get("entity_type") == "disease"]
    edges: list[dict[str, Any]] = []
    for gene in genes:
        for disease in diseases:
            edges.append(
                {
                    "edge_id": f"edge:{case_id}:{gene['entity_id']}->{disease['entity_id']}",
                    "source": gene["entity_id"],
                    "target": disease["entity_id"],
                    "relationship": "associated_with",
                    "confidence": min(gene.get("confidence", 0.5), disease.get("confidence", 0.5)),
                }
            )
    return edges


def build_knowledge_graph(config: CaseConfig, case_dir: Path) -> Path:
    """Generate knowledge_graph.json from normalized_entities.json."""
    entities_path = case_dir / "normalized_entities.json"
    if not entities_path.exists():
        raise FileNotFoundError(f"Missing normalized entities: {entities_path}")

    payload = json.loads(entities_path.read_text(encoding="utf-8"))
    entities = payload.get("data", {}).get("entities", [])
    if not entities and isinstance(payload.get("entities"), list):
        entities = payload["entities"]

    nodes = _entity_nodes(entities)
    edges = _entity_edges(entities, config.case_id)

    envelope = {
        "artifact_type": "knowledge_graph",
        "case_id": config.case_id,
        "schema_version": SCHEMA_VERSION,
        "generated_at": utc_now_iso(),
        "provenance": build_provenance(
            "pipeline/build_graph.py",
            ["normalized_entities.json"],
        ),
        "data": {
            "nodes": nodes,
            "edges": edges,
        },
    }

    output_path = case_dir / "knowledge_graph.json"
    output_path.write_text(json.dumps(envelope, indent=2) + "\n", encoding="utf-8")
    return output_path
