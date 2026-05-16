"""Minimal run registry for pipeline executions."""

from __future__ import annotations

import json
from dataclasses import asdict, dataclass, field
from pathlib import Path
from typing import Any, Literal

from pipeline.provenance import utc_now_iso
from pipeline.types import RunMode, repo_root

RunStatus = Literal["running", "completed", "failed"]


@dataclass
class RunRecord:
    run_id: str
    case_id: str
    mode: RunMode
    status: RunStatus
    started_at: str
    completed_at: str | None = None
    config_path: str | None = None
    output_dir: str | None = None
    artifacts: list[str] = field(default_factory=list)
    errors: list[str] = field(default_factory=list)
    metadata: dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


class RunRegistry:
    """Append-only JSONL registry under generated/.runs/registry.jsonl."""

    def __init__(self, registry_path: Path | None = None) -> None:
        root = repo_root()
        self.registry_path = registry_path or (root / "generated" / ".runs" / "registry.jsonl")
        self.registry_path.parent.mkdir(parents=True, exist_ok=True)

    def append(self, record: RunRecord) -> None:
        with self.registry_path.open("a", encoding="utf-8") as handle:
            handle.write(json.dumps(record.to_dict()) + "\n")

    def start_run(
        self,
        *,
        run_id: str,
        case_id: str,
        mode: RunMode,
        config_path: Path | None,
        output_dir: Path,
    ) -> RunRecord:
        record = RunRecord(
            run_id=run_id,
            case_id=case_id,
            mode=mode,
            status="running",
            started_at=utc_now_iso(),
            config_path=str(config_path) if config_path else None,
            output_dir=str(output_dir),
        )
        self.append(record)
        return record

    def complete_run(
        self,
        record: RunRecord,
        *,
        artifacts: list[str],
        errors: list[str] | None = None,
    ) -> RunRecord:
        record.status = "failed" if errors else "completed"
        record.completed_at = utc_now_iso()
        record.artifacts = artifacts
        record.errors = errors or []
        self.append(record)
        return record
