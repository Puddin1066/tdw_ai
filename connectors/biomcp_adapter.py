"""Best-effort BioMCP adapter for connector backends.

This module is intentionally conservative: if BioMCP is unavailable or returns
unexpected payloads, callers should fall back to native connector logic.
"""

from __future__ import annotations

import json
import os
import re
import hashlib
import importlib.util
import shutil
import subprocess
import sys
from typing import Any

DEFAULT_BIOMCP_CONNECTORS = {
    "pubmed",
    "clinicaltrials",
    "opentargets",
    "chembl",
    "biothings",
    "uniprot",
    "reactome",
    "gwas",
    "pharmgkb",
    "openfda",
}


def _normalize_backend(value: str | None) -> str:
    return (value or "").strip().lower()


def should_use_biomcp_backend(connector_name: str) -> bool:
    """Return True when connector backend should use BioMCP.

    Behavior:
    - connector-specific `*_BACKEND` overrides global backend
    - global `CONNECTOR_BACKEND` applies when specific backend is unset
    - when neither is set, core biomedical connectors default to BioMCP
    """
    specific = _normalize_backend(os.environ.get(f"{connector_name.upper()}_BACKEND"))
    global_backend = _normalize_backend(os.environ.get("CONNECTOR_BACKEND"))

    if specific in {"biomcp", "native"}:
        return specific == "biomcp"
    if global_backend in {"biomcp", "native"}:
        return global_backend == "biomcp"
    return connector_name.strip().lower() in DEFAULT_BIOMCP_CONNECTORS


def _biomcp_prefix() -> list[str] | None:
    executable = shutil.which("biomcp")
    if executable:
        return ["biomcp"]
    if importlib.util.find_spec("biomcp") is not None:
        return [sys.executable, "-m", "biomcp"]
    return None


def _command_core(command: list[str]) -> list[str]:
    if not command:
        return command
    if command[0] == "biomcp":
        return command
    if len(command) >= 4 and command[1] == "-m" and command[2] == "biomcp":
        return ["biomcp", *command[3:]]
    return command


def run_biomcp_search(
    entity: str,
    term: str | None,
    *,
    limit: int = 25,
    offset: int = 0,
    options: list[str] | None = None,
) -> tuple[dict[str, Any] | None, str | None]:
    """Execute a BioMCP search command and parse JSON output when possible.

    Supports both legacy CLI (`biomcp search ...`) and newer CLI shapes
    for BioMCP python CLI domains.
    """
    prefix = _biomcp_prefix()
    if prefix is None:
        return None, "biomcp executable not found in PATH"
    safe_limit = _normalize_limit(entity, limit)
    safe_offset = max(0, int(offset))
    safe_page = (safe_offset // max(1, safe_limit)) + 1

    legacy_command = [*prefix, "search", entity]
    if term and term.strip():
        legacy_command.append(term.strip())
    if options:
        legacy_command.extend(str(opt) for opt in options if str(opt).strip())
    legacy_command.extend(["--offset", str(safe_offset), "-l", str(safe_limit), "-j"])

    commands: list[list[str]] = [legacy_command]
    normalized_entity = entity.strip().lower()
    commands.extend(
        _modern_search_commands(
            normalized_entity,
            term=term,
            limit=safe_limit,
            page=safe_page,
            options=options or [],
        )
    )

    return _run_biomcp_commands(commands)


def run_biomcp_article_get(
    identifier: str,
    *,
    full: bool = True,
) -> tuple[dict[str, Any] | None, str | None]:
    """Fetch article details by PMID/DOI using modern BioMCP article command."""
    prefix = _biomcp_prefix()
    if prefix is None:
        return None, "biomcp executable not found in PATH"
    token = str(identifier or "").strip()
    if not token:
        return None, "missing article identifier"
    command = [*prefix, "article", "get", token, "-j"]
    if full:
        command.append("--full")
    return _run_biomcp_commands([command])


def run_biomcp_trial_get(
    nct_id: str,
    *,
    module: str = "all",
) -> tuple[dict[str, Any] | None, str | None]:
    """Fetch rich trial details with module-level payloads."""
    prefix = _biomcp_prefix()
    if prefix is None:
        return None, "biomcp executable not found in PATH"
    token = str(nct_id or "").strip().upper()
    if not token:
        return None, "missing trial identifier"
    command = [*prefix, "trial", "get", token, module, "-j"]
    return _run_biomcp_commands([command])


def run_biomcp_gene_get(
    identifier: str,
    *,
    enrich: str | None = None,
) -> tuple[dict[str, Any] | None, str | None]:
    """Fetch detailed gene annotations and optional enrichment."""
    prefix = _biomcp_prefix()
    if prefix is None:
        return None, "biomcp executable not found in PATH"
    token = str(identifier or "").strip()
    if not token:
        return None, "missing gene identifier"
    command = [*prefix, "gene", "get", token, "-j"]
    if enrich:
        command.extend(["--enrich", str(enrich).strip()])
    return _run_biomcp_commands([command])


def run_biomcp_drug_get(identifier: str) -> tuple[dict[str, Any] | None, str | None]:
    """Fetch detailed drug annotations from BioMCP MyChem path."""
    prefix = _biomcp_prefix()
    if prefix is None:
        return None, "biomcp executable not found in PATH"
    token = str(identifier or "").strip()
    if not token:
        return None, "missing drug identifier"
    command = [*prefix, "drug", "get", token, "-j"]
    return _run_biomcp_commands([command])


def run_biomcp_variant_get(
    identifier: str,
    *,
    extensive: bool = True,
) -> tuple[dict[str, Any] | None, str | None]:
    """Fetch detailed variant annotations from BioMCP MyVariant path."""
    prefix = _biomcp_prefix()
    if prefix is None:
        return None, "biomcp executable not found in PATH"
    token = str(identifier or "").strip()
    if not token:
        return None, "missing variant identifier"
    command = [*prefix, "variant", "get", token, "--json"]
    if extensive:
        command.append("--extensive")
    return _run_biomcp_commands([command])


def run_biomcp_disease_get(identifier: str) -> tuple[dict[str, Any] | None, str | None]:
    """Fetch disease details from BioMCP disease domain."""
    prefix = _biomcp_prefix()
    if prefix is None:
        return None, "biomcp executable not found in PATH"
    token = str(identifier or "").strip()
    if not token:
        return None, "missing disease identifier"
    command = [*prefix, "disease", "get", token]
    return _run_biomcp_commands([command])


def run_biomcp_openfda_label_get(
    label_id: str,
    *,
    sections: str | None = None,
) -> tuple[dict[str, Any] | None, str | None]:
    """Fetch detailed OpenFDA label text for a specific label id."""
    prefix = _biomcp_prefix()
    if prefix is None:
        return None, "biomcp executable not found in PATH"
    token = str(label_id or "").strip()
    if not token:
        return None, "missing openfda label identifier"
    command = [*prefix, "openfda", "label", "get", token]
    if sections:
        command.extend(["--sections", str(sections).strip()])
    return _run_biomcp_commands([command])


def _run_biomcp_commands(commands: list[list[str]]) -> tuple[dict[str, Any] | None, str | None]:
    timeout_s = float(os.environ.get("BIOMCP_TIMEOUT_SECONDS", "90"))
    errors: list[str] = []
    for command in commands:
        try:
            proc = subprocess.run(
                command,
                capture_output=True,
                text=True,
                timeout=timeout_s,
                check=False,
            )
        except Exception as exc:  # noqa: BLE001
            errors.append(f"{' '.join(command[:3])}: BioMCP execution failed: {exc}")
            continue
        if proc.returncode != 0:
            stderr = (proc.stderr or "").strip()
            if _looks_like_command_mismatch(stderr):
                errors.append(f"{' '.join(command[:3])}: {stderr or 'command mismatch'}")
                continue
            return None, f"BioMCP returned exit code {proc.returncode}: {stderr or 'no stderr'}"
        payload = _parse_output(command, proc.stdout)
        if payload is None:
            errors.append(f"{' '.join(command[:3])}: BioMCP output was not parseable JSON")
            continue
        return payload, None
    if errors:
        return None, "; ".join(errors)
    return None, "BioMCP command execution failed"


def _looks_like_command_mismatch(stderr: str) -> bool:
    text = (stderr or "").lower()
    return "no such command" in text or "usage:" in text


def _map_trial_options(options: list[str]) -> list[str]:
    """Map legacy trial option flags to modern `biomcp trial search` flags."""
    out: list[str] = []
    idx = 0
    while idx < len(options):
        token = str(options[idx]).strip()
        nxt = str(options[idx + 1]).strip() if idx + 1 < len(options) else ""
        if token == "-c" and nxt:
            out.extend(["--condition", nxt])
            idx += 2
            continue
        if token == "-i" and nxt:
            out.extend(["--intervention", nxt])
            idx += 2
            continue
        idx += 1
    return out


def _modern_search_commands(
    entity: str,
    *,
    term: str | None,
    limit: int,
    page: int,
    options: list[str],
) -> list[list[str]]:
    prefix = _biomcp_prefix()
    if prefix is None:
        return []
    token = (term or "").strip()
    if entity == "article":
        cmd = [*prefix, "article", "search", "-l", str(limit), "-p", str(page), "-j"]
        if token:
            cmd.extend(["-k", token])
        # Ignore legacy options (e.g., --source / --ranking-mode) that are not
        # supported by biomcp article search in current CLI versions.
        return [cmd]
    if entity == "trial":
        cmd = [
            *prefix,
            "trial",
            "search",
            "--page-size",
            str(limit),
            "-j",
        ]
        if token:
            cmd.extend(["-t", token])
        cmd.extend(_map_trial_options(options))
        return [cmd]
    if entity in {"gene", "drug"} and token:
        return [[
            *prefix,
            entity,
            "search",
            token,
            "--page-size",
            str(limit),
            "--page",
            str(page),
            "-j",
        ]]
    if entity == "variant" and token:
        return [[*prefix, "variant", "search", "--gene", token, "--size", str(limit), "-j"]]
    if entity == "gwas" and token:
        return [[*prefix, "gene", "get", token, "--enrich", "gwas", "-j"]]
    if entity in {"pathway", "protein"} and token:
        return [[*prefix, "gene", "get", token, "--enrich", "reactome", "-j"]]
    if entity == "pgx" and token:
        return [[*prefix, "variant", "search", "--gene", token, "--size", str(limit), "-j"]]
    if entity == "adverse-event" and token:
        return [[
            *prefix,
            "openfda",
            "adverse",
            "search",
            "--drug",
            token,
            "--limit",
            str(limit),
            "--page",
            str(page),
        ]]
    if entity == "disease" and token:
        return [[*prefix, "disease", "search", token, "--page-size", str(limit), "--page", str(page)]]
    if entity == "fda-label" and token:
        return [[
            *prefix,
            "openfda",
            "label",
            "search",
            "--name",
            token,
            "--limit",
            str(limit),
            "--page",
            str(page),
        ]]
    return []


def _normalize_limit(entity: str, limit: int) -> int:
    bounded = max(1, int(limit))
    # trial search enforces hard max 50 in current BioMCP CLI.
    if entity.strip().lower() == "trial":
        return min(bounded, 50)
    if entity.strip().lower() in {"gene", "drug"}:
        return min(bounded, 100)
    return bounded


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


def _parse_output(command: list[str], text: str) -> dict[str, Any] | None:
    payload = _parse_json(text)
    if payload is not None:
        return payload
    if not _accepts_plain_text(command):
        return None
    body = (text or "").strip()
    if not body:
        return None
    parsed = _parse_plain_text_output(command, body)
    if parsed is not None:
        return parsed
    first_line = body.splitlines()[0][:120].strip()
    digest = hashlib.sha1((" ".join(command) + first_line).encode("utf-8")).hexdigest()[:16]
    synthetic_id = f"text:{digest}"
    return {
        "results": [
            {
                "id": synthetic_id,
                "title": first_line or "BioMCP text response",
                "summary": body[:4000],
            }
        ],
        "_raw_text": body,
    }


def _accepts_plain_text(command: list[str]) -> bool:
    core = _command_core(command)
    prefix = core[:4]
    if prefix == ["biomcp", "openfda", "adverse", "search"]:
        return True
    if prefix == ["biomcp", "openfda", "label", "search"]:
        return True
    if prefix == ["biomcp", "openfda", "label", "get"]:
        return True
    if prefix == ["biomcp", "openfda", "recall", "get"]:
        return True
    if core[:3] == ["biomcp", "disease", "search"]:
        return True
    if core[:3] == ["biomcp", "disease", "get"]:
        return True
    return False


def _parse_plain_text_output(command: list[str], body: str) -> dict[str, Any] | None:
    core = _command_core(command)
    if core[:4] == ["biomcp", "openfda", "label", "search"]:
        rows = _extract_openfda_label_rows(body)
        if rows:
            return {"results": rows, "_raw_text": body}
    if core[:4] == ["biomcp", "openfda", "label", "get"]:
        token = core[4] if len(core) > 4 else "openfda-label"
        return {
            "results": [
                {
                    "id": str(token),
                    "label_id": str(token),
                    "title": f"OpenFDA label {token}",
                    "summary": body[:4000],
                }
            ],
            "_raw_text": body,
        }
    return None


def _extract_openfda_label_rows(body: str) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    blocks = body.split("#### ")
    for idx, block in enumerate(blocks):
        text = block.strip()
        if not text:
            continue
        title_line, _, remainder = text.partition("\n")
        if not title_line[:1].isdigit():
            continue
        title = title_line.split(".", 1)[-1].strip() if "." in title_line else title_line.strip()
        label_match = re.search(r"Label ID:\s*([0-9a-fA-F-]{16,})", text, flags=re.IGNORECASE)
        label_id = label_match.group(1).strip() if label_match else ""
        if not title and not label_id:
            continue
        token = label_id or f"label-row-{idx}"
        rows.append(
            {
                "id": token,
                "label_id": token,
                "title": title or token,
                "summary": remainder.strip()[:1200] if remainder.strip() else None,
            }
        )
    return rows


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
