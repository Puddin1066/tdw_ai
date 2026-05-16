"""Internal helpers for reading and writing case artifacts."""

from __future__ import annotations

import json
import shutil
from pathlib import Path
from typing import Any

from pipeline.provenance import build_provenance, utc_now_iso
from pipeline.types import SCHEMA_VERSION, CaseConfig, RunMode, fixture_case_dir


def copy_fixture_artifact(case_id: str, artifact_name: str, dest: Path) -> bool:
    source = fixture_case_dir(case_id) / artifact_name
    if not source.exists():
        return False
    dest.parent.mkdir(parents=True, exist_ok=True)
    shutil.copy2(source, dest)
    return True


def write_stub_envelope(
    config: CaseConfig,
    artifact_type: str,
    data: dict[str, Any],
    *,
    generated_by: str,
    input_artifacts: list[str],
    dest: Path,
) -> Path:
    envelope = {
        "artifact_type": artifact_type,
        "case_id": config.case_id,
        "schema_version": SCHEMA_VERSION,
        "generated_at": utc_now_iso(),
        "provenance": build_provenance(generated_by, input_artifacts),
        "data": data,
    }
    dest.write_text(json.dumps(envelope, indent=2) + "\n", encoding="utf-8")
    return dest


def run_synthesis_step(
    config: CaseConfig,
    case_dir: Path,
    *,
    mode: RunMode,
    artifact_name: str,
    artifact_type: str,
    generated_by: str,
    input_artifacts: list[str],
    stub_data: dict[str, Any],
) -> Path:
    dest = case_dir / artifact_name
    if mode == "fixture" and copy_fixture_artifact(config.case_id, artifact_name, dest):
        return dest
    if artifact_name.endswith(".md"):
        dest.write_text(
            f"# {config.display_name}\n\n"
            f"Live synthesis stub for `{artifact_name}`. "
            "Wire OpenAI provider in live mode.\n",
            encoding="utf-8",
        )
        return dest
    return write_stub_envelope(
        config,
        artifact_type,
        stub_data,
        generated_by=generated_by,
        input_artifacts=input_artifacts,
        dest=dest,
    )
