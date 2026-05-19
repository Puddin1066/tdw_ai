"""Best-effort BioMCP adapter for connector backends.

This module is intentionally conservative: if BioMCP is unavailable or returns
unexpected payloads, callers should fall back to native connector logic.
"""

from __future__ import annotations

import json
import os
import re
import shutil
import subprocess
from typing import Any


def should_use_biomcp_backend(connector_name: str) -> bool:
    """Return True when connector backend is configured as `biomcp`."""
    specific = os.environ.get(f"{connector_name.upper()}_BACKEND")
    global_backend = os.environ.get("CONNECTOR_BACKEND")
    backend = (specific or global_backend or "").strip().lower()
    return backend == "biomcp"


def run_biomcp_search(entity: str, term: str, *, limit: int = 25) -> tuple[dict[str, Any] | None, str | None]:
    """Execute a BioMCP search command and parse JSON output when possible."""
    if not shutil.which("biomcp"):
        return None, "biomcp executable not found in PATH"

    command = [
        "biomcp",
        "search",
        entity,
        "-q",
        term,
        "-l",
        str(limit),
        "-j",
    ]
    try:
        proc = subprocess.run(
            command,
            capture_output=True,
            text=True,
            timeout=float(os.environ.get("BIOMCP_TIMEOUT_SECONDS", "20")),
            check=False,
        )
    except Exception as exc:  # noqa: BLE001
        return None, f"BioMCP execution failed: {exc}"

    if proc.returncode != 0:
        stderr = (proc.stderr or "").strip()
        return None, f"BioMCP returned exit code {proc.returncode}: {stderr or 'no stderr'}"

    payload = _parse_json(proc.stdout)
    if payload is None:
        return None, "BioMCP output was not parseable JSON"
    return payload, None


def _parse_json(text: str) -> dict[str, Any] | None:
    raw = (text or "").strip()
    if not raw:
        return None
    try:
        parsed = json.loads(raw)
        if isinstance(parsed, dict):
            return parsed
        if isinstance(parsed, list):
            return {"results": parsed}
    except json.JSONDecodeError:
        pass

    # Some CLIs print extra logs; salvage first JSON object/array block.
    match = re.search(r"(\{.*\}|\[.*\])", raw, flags=re.DOTALL)
    if not match:
        return None
    try:
        parsed = json.loads(match.group(1))
    except json.JSONDecodeError:
        return None
    if isinstance(parsed, dict):
        return parsed
    if isinstance(parsed, list):
        return {"results": parsed}
    return None


def extract_records(payload: dict[str, Any]) -> list[dict[str, Any]]:
    """Extract list-like records from common BioMCP JSON shapes."""
    candidates: list[dict[str, Any]] = []

    def visit(value: Any) -> None:
        if isinstance(value, list):
            if value and all(isinstance(item, dict) for item in value):
                candidates.extend(item for item in value if isinstance(item, dict))
                return
            for item in value:
                visit(item)
            return
        if isinstance(value, dict):
            # Common list containers
            for key in ("results", "items", "data", "hits", "rows"):
                child = value.get(key)
                if isinstance(child, list):
                    visit(child)
            for child in value.values():
                if isinstance(child, (dict, list)):
                    visit(child)

    visit(payload)
    # Dedupe by serialized view for stability.
    out: list[dict[str, Any]] = []
    seen: set[str] = set()
    for row in candidates:
        key = json.dumps(row, sort_keys=True, default=str)
        if key in seen:
            continue
        seen.add(key)
        out.append(row)
    return out
