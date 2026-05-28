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
    primary_entities = [
        e for e in entities if e.get("entity_type") in {"gene", "protein", "modality", "compound", "biomarker"}
    ]
    diseases = [e for e in entities if e.get("entity_type") == "disease"]
    edges: list[dict[str, Any]] = []
    for primary in primary_entities:
        for disease in diseases:
            relationship = (
                "associated_with"
                if str(primary.get("entity_id", "")).startswith(("gene:", "protein:"))
                else "applied_in"
            )
            edges.append(
                {
                    "edge_id": f"edge:{case_id}:{primary['entity_id']}->{disease['entity_id']}",
                    "source": primary["entity_id"],
                    "target": disease["entity_id"],
                    "relationship": relationship,
                    "confidence": min(primary.get("confidence", 0.5), disease.get("confidence", 0.5)),
                }
            )
    return edges


def _resolve_source_node(
    source_record_id: str,
    node_ids: set[str],
    source_to_entity: dict[str, str],
) -> str | None:
    if source_record_id in source_to_entity:
        candidate = source_to_entity[source_record_id]
        if candidate in node_ids:
            return candidate
    if source_record_id in node_ids:
        return source_record_id
    if source_record_id.startswith("pubmed:"):
        pub_node = source_record_id.replace("pubmed:", "publication:", 1)
        return pub_node if pub_node in node_ids else None
    if source_record_id.startswith("clinicaltrials:"):
        trial_node = source_record_id.replace("clinicaltrials:", "clinical_trial:", 1)
        return trial_node if trial_node in node_ids else None
    return None


def _append_edge(
    edges: list[dict[str, Any]],
    seen_ids: set[str],
    *,
    edge_id: str,
    source: str,
    target: str,
    relationship: str,
    confidence: float | None,
    source_record_ids: list[str] | None = None,
) -> None:
    if edge_id in seen_ids:
        return
    seen_ids.add(edge_id)
    edge: dict[str, Any] = {
        "edge_id": edge_id,
        "source": source,
        "target": target,
        "relationship": relationship,
        "confidence": confidence,
    }
    if source_record_ids:
        edge["source_record_ids"] = source_record_ids
    edges.append(edge)


def _evidence_edges(
    evidence_rows: list[dict[str, Any]],
    *,
    case_id: str,
    node_ids: set[str],
    source_to_entity: dict[str, str],
    primary_ids: list[str],
    disease_ids: list[str],
) -> list[dict[str, Any]]:
    edges: list[dict[str, Any]] = []
    seen: set[str] = set()
    if not primary_ids or not disease_ids:
        return edges
    primary_id = primary_ids[0]
    supports_relationship = (
        "supports_target" if str(primary_id).startswith(("gene:", "protein:")) else "supports_opportunity"
    )
    disease_id = disease_ids[0]
    for idx, row in enumerate(evidence_rows):
        source_ids = row.get("source_record_ids", [])
        if not isinstance(source_ids, list):
            continue
        confidence = float(row.get("confidence", 0.5) or 0.5)
        for sid in source_ids:
            sid_text = str(sid)
            source_node = _resolve_source_node(sid_text, node_ids, source_to_entity)
            if not source_node:
                continue
            _append_edge(
                edges,
                seen,
                edge_id=f"edge:{case_id}:evidence:{idx}:{source_node}->{primary_id}",
                source=source_node,
                target=primary_id,
                relationship=supports_relationship,
                confidence=confidence,
                source_record_ids=[sid_text],
            )
            _append_edge(
                edges,
                seen,
                edge_id=f"edge:{case_id}:evidence:{idx}:{source_node}->{disease_id}",
                source=source_node,
                target=disease_id,
                relationship="supports_indication",
                confidence=confidence,
                source_record_ids=[sid_text],
            )
    return edges


def _trial_context_edges(
    trials: list[dict[str, Any]],
    *,
    case_id: str,
    node_ids: set[str],
    source_to_entity: dict[str, str],
    primary_ids: list[str],
    disease_ids: list[str],
) -> list[dict[str, Any]]:
    edges: list[dict[str, Any]] = []
    seen: set[str] = set()
    if not primary_ids or not disease_ids:
        return edges
    primary_id = primary_ids[0]
    disease_id = disease_ids[0]
    for trial in trials:
        sid = str(trial.get("source_record_id", ""))
        if not sid:
            continue
        trial_node = _resolve_source_node(sid, node_ids, source_to_entity)
        if not trial_node:
            continue
        _append_edge(
            edges,
            seen,
            edge_id=f"edge:{case_id}:trial:{trial_node}->{disease_id}",
            source=trial_node,
            target=disease_id,
            relationship="tested_in",
            confidence=0.65,
            source_record_ids=[sid],
        )
        _append_edge(
            edges,
            seen,
            edge_id=f"edge:{case_id}:trial:{trial_node}->{primary_id}",
            source=trial_node,
            target=primary_id,
            relationship="targets" if str(primary_id).startswith(("gene:", "protein:")) else "evaluates",
            confidence=0.65,
            source_record_ids=[sid],
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
    node_ids = {node["node_id"] for node in nodes}
    source_to_entity: dict[str, str] = {}
    for entity in entities:
        entity_id = entity.get("entity_id")
        if not isinstance(entity_id, str):
            continue
        for sid in entity.get("source_record_ids", []) if isinstance(entity.get("source_record_ids"), list) else []:
            source_to_entity[str(sid)] = entity_id

    primary_ids = [
        e["entity_id"]
        for e in entities
        if e.get("entity_type") in {"gene", "protein", "modality", "compound", "biomarker"}
    ]
    disease_ids = [e["entity_id"] for e in entities if e.get("entity_type") == "disease"]

    evidence_rows: list[dict[str, Any]] = []
    evidence_path = case_dir / "evidence_table.json"
    if evidence_path.exists():
        evidence_payload = json.loads(evidence_path.read_text(encoding="utf-8"))
        evidence_rows = evidence_payload.get("data", {}).get("rows", [])
        if not isinstance(evidence_rows, list):
            evidence_rows = []

    trials: list[dict[str, Any]] = []
    trials_path = case_dir / "clinical_trials.json"
    if trials_path.exists():
        trials_payload = json.loads(trials_path.read_text(encoding="utf-8"))
        trials = trials_payload.get("data", {}).get("trials", [])
        if not isinstance(trials, list):
            trials = []

    edges = _entity_edges(entities, config.case_id)
    edges.extend(
        _evidence_edges(
            evidence_rows,
            case_id=config.case_id,
            node_ids=node_ids,
            source_to_entity=source_to_entity,
            primary_ids=primary_ids,
            disease_ids=disease_ids,
        )
    )
    edges.extend(
        _trial_context_edges(
            trials,
            case_id=config.case_id,
            node_ids=node_ids,
            source_to_entity=source_to_entity,
            primary_ids=primary_ids,
            disease_ids=disease_ids,
        )
    )

    envelope = {
        "artifact_type": "knowledge_graph",
        "case_id": config.case_id,
        "schema_version": SCHEMA_VERSION,
        "generated_at": utc_now_iso(),
        "provenance": build_provenance(
            "pipeline/build_graph.py",
            ["normalized_entities.json", "evidence_table.json", "clinical_trials.json"],
        ),
        "data": {
            "nodes": nodes,
            "edges": edges,
        },
    }

    output_path = case_dir / "knowledge_graph.json"
    output_path.write_text(json.dumps(envelope, indent=2) + "\n", encoding="utf-8")
    return output_path
