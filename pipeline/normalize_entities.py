"""Normalize connector outputs into case entity artifacts."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from pipeline.provenance import build_provenance, utc_now_iso
from pipeline.types import SCHEMA_VERSION, CaseConfig, RunMode, fixture_case_dir


def _read_json(path: Path) -> dict[str, Any]:
    with path.open(encoding="utf-8") as handle:
        payload = json.load(handle)
    if not isinstance(payload, dict):
        raise ValueError(f"Expected JSON object in {path}")
    return payload


def _fixture_entities(case_id: str) -> dict[str, Any] | None:
    fixture_path = fixture_case_dir(case_id) / "normalized_entities.json"
    if fixture_path.exists():
        return _read_json(fixture_path)
    return None


def _light_normalize(config: CaseConfig, connector_payloads: list[dict[str, Any]]) -> dict[str, Any]:
    entities: list[dict[str, Any]] = [
        {
            "entity_id": f"gene:{config.target.name}",
            "entity_type": "gene",
            "canonical_name": config.target.name,
            "display_name": config.target.name,
            "aliases": list(config.target.aliases),
            "external_ids": {},
            "source_record_ids": [],
            "confidence": 0.8,
        },
        {
            "entity_id": f"disease:{config.indication.name.replace(' ', '_')}",
            "entity_type": "disease",
            "canonical_name": config.indication.name,
            "display_name": config.indication.name,
            "aliases": list(config.indication.aliases),
            "external_ids": {},
            "source_record_ids": [],
            "confidence": 0.8,
        },
    ]

    for payload in connector_payloads:
        for record in payload.get("records", []):
            record_id = record.get("source_record_id")
            if not record_id:
                continue
            entity_type = record.get("entity_type") or record.get("source_type") or "publication"
            entities.append(
                {
                    "entity_id": f"{entity_type}:{record_id.split(':', 1)[-1]}",
                    "entity_type": entity_type,
                    "canonical_name": record.get("title") or record_id,
                    "display_name": record.get("title") or record_id,
                    "aliases": [],
                    "external_ids": {},
                    "source_record_ids": [record_id],
                    "confidence": 0.6,
                }
            )

    return {
        "artifact_type": "normalized_entities",
        "case_id": config.case_id,
        "schema_version": SCHEMA_VERSION,
        "generated_at": utc_now_iso(),
        "provenance": build_provenance(
            "pipeline/normalize_entities.py",
            ["source_manifest.json"],
        ),
        "data": {"entities": entities},
    }


def normalize_entities(
    config: CaseConfig,
    case_dir: Path,
    *,
    mode: RunMode,
    connector_payloads: list[dict[str, Any]] | None = None,
) -> Path:
    """Write normalized_entities.json, copying fixture data or lightly normalizing records."""
    output_path = case_dir / "normalized_entities.json"

    if mode == "fixture":
        fixture_payload = _fixture_entities(config.case_id)
        if fixture_payload is not None:
            output_path.write_text(json.dumps(fixture_payload, indent=2) + "\n", encoding="utf-8")
            return output_path

    envelope = _light_normalize(config, connector_payloads or [])
    output_path.write_text(json.dumps(envelope, indent=2) + "\n", encoding="utf-8")
    return output_path
