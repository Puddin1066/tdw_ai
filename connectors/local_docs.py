"""Local document connector for user-supplied case files (fixture + live stub)."""

from __future__ import annotations

import os
from pathlib import Path

from connectors._shared import FixtureCapableConnector
from connectors.base import (
    CaseConfig,
    ConnectorProvenance,
    ConnectorResult,
    empty_result,
    utc_now_iso,
)

# Live mode would read from configs/cases/{case_id}/local_docs/ or similar.
# Fixture mode loads tests/fixtures/cases/{case_id}/raw/local_docs*.json


class LocalDocsConnector(FixtureCapableConnector):
    name = "local_docs"
    source_name = "Local Documents"
    source_url = "file://local"
    api_endpoint = None
    api_version = None
    _ALLOWED_EXTENSIONS = {
        ".txt",
        ".md",
        ".json",
        ".jsonl",
        ".csv",
        ".tsv",
        ".pdf",
    }
    _MAX_RECORDS = 50

    def _fetch_fixture(self, config: CaseConfig, provenance: ConnectorProvenance) -> ConnectorResult:
        if not config.sources.local_docs:
            result = super()._fetch_fixture(config, provenance)
            return result.model_copy(
                update={
                    "warnings": [*result.warnings, "local_docs disabled in case config; skipping fetch"]
                }
            )
        return super()._fetch_fixture(config, provenance)

    def _fetch_live(self, config: CaseConfig, provenance: ConnectorProvenance) -> ConnectorResult:
        if not config.sources.local_docs:
            return empty_result(self.name, config, "live", provenance).model_copy(
                update={"warnings": ["local_docs disabled in case config; skipping fetch"]}
            )

        local_docs_dir = os.environ.get("LOCAL_DOCS_DIR") or os.environ.get("RHVC_DIR")
        if not local_docs_dir:
            raise ValueError("Set LOCAL_DOCS_DIR (or RHVC_DIR) for local_docs live fetch.")
        root = Path(local_docs_dir).expanduser().resolve()
        if not root.is_dir():
            raise FileNotFoundError(f"Local docs directory does not exist: {root}")

        all_files = [p for p in root.rglob("*") if p.is_file() and p.suffix.lower() in self._ALLOWED_EXTENSIONS]
        all_files.sort()
        records = [self._to_record(path, root) for path in all_files[: self._MAX_RECORDS]]
        warnings: list[str] = []
        if len(all_files) > self._MAX_RECORDS:
            warnings.append(
                f"local_docs capped at {self._MAX_RECORDS} files; skipped {len(all_files) - self._MAX_RECORDS}."
            )
        if not records:
            warnings.append("No local docs found with supported extensions.")
        return empty_result(self.name, config, "live", provenance).model_copy(
            update={"records": records, "warnings": warnings}
        )

    def _to_record(self, path: Path, root: Path) -> dict[str, object]:
        rel = str(path.relative_to(root))
        source_id = "local_docs:" + rel.replace("/", "::")
        return {
            "source_record_id": source_id,
            "source_type": "local_document",
            "source_name": "Local Documents",
            "title": path.stem,
            "url": None,
            "publication_date": None,
            "retrieved_at": utc_now_iso(),
            "raw_record_ref": f"raw/local_docs_raw.json#file/{rel}",
            "path": str(path),
            "relative_path": rel,
            "extension": path.suffix.lower(),
            "size_bytes": path.stat().st_size,
        }


connector = LocalDocsConnector()
