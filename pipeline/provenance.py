"""Provenance metadata helpers for generated artifacts."""

from __future__ import annotations

from datetime import datetime, timezone
from typing import Any

from pipeline.types import SCHEMA_VERSION, Provenance


def utc_now_iso() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat().replace("+00:00", "Z")


def _parse_generated_at(value: str | None) -> datetime:
    if value is None:
        return datetime.now(timezone.utc)
    normalized = value.replace("Z", "+00:00")
    return datetime.fromisoformat(normalized)


def build_provenance(
    generated_by: str,
    input_artifacts: list[str],
    *,
    model_provider: str | None = None,
    model_name: str | None = None,
    prompt_template: str | None = None,
    prompt_hash: str | None = None,
    generated_at: str | None = None,
) -> dict[str, Any]:
    record = Provenance(
        generated_by=generated_by,
        generated_at=_parse_generated_at(generated_at),
        input_artifacts=input_artifacts,
        model_provider=model_provider,
        model_name=model_name,
        prompt_template=prompt_template,
        prompt_hash=prompt_hash,
        schema_version=SCHEMA_VERSION,
    )
    payload = record.model_dump(mode="json")
    if isinstance(payload.get("generated_at"), str):
        payload["generated_at"] = generated_at or utc_now_iso()
    else:
        payload["generated_at"] = generated_at or utc_now_iso()
    return payload


def attach_provenance(
    envelope: dict[str, Any],
    provenance: dict[str, Any],
) -> dict[str, Any]:
    envelope = dict(envelope)
    envelope["provenance"] = provenance
    envelope["generated_at"] = provenance["generated_at"]
    envelope["schema_version"] = provenance.get("schema_version", SCHEMA_VERSION)
    return envelope
