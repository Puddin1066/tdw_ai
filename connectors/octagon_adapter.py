"""Best-effort Octagon MCP adapter for market-intelligence retrieval."""

from __future__ import annotations

import json
import os
import re
import shutil
import subprocess
from typing import Any

import httpx


def run_octagon_search(topic: str, *, limit: int = 25) -> tuple[dict[str, Any] | None, str | None]:
    """Execute Octagon retrieval via CLI first, then REST fallback."""
    cli_payload, cli_error = _run_octagon_cli_search(topic, limit=limit)
    if cli_payload is not None:
        return cli_payload, None
    rest_payload, rest_error = _run_octagon_rest_search(topic, limit=limit)
    if rest_payload is not None:
        return rest_payload, None
    return None, _merge_errors(cli_error, rest_error)


def _run_octagon_cli_search(topic: str, *, limit: int) -> tuple[dict[str, Any] | None, str | None]:
    command_names = _candidate_commands()
    if not command_names:
        return None, "Octagon CLI not found (set OCTAGON_MCP_COMMAND or install octagon CLI)"
    errors: list[str] = []
    for command_name in command_names:
        command = [command_name, "search", topic, "--limit", str(limit), "--json"]
        try:
            proc = subprocess.run(
                command,
                capture_output=True,
                text=True,
                timeout=float(os.environ.get("OCTAGON_TIMEOUT_SECONDS", "25")),
                check=False,
            )
        except Exception as exc:  # noqa: BLE001
            errors.append(f"{command_name} execution failed: {exc}")
            continue

        if proc.returncode != 0:
            stderr = (proc.stderr or "").strip()
            errors.append(
                f"{command_name} returned exit code {proc.returncode}: {stderr or 'no stderr'}"
            )
            continue

        payload = _parse_json(proc.stdout)
        if payload is not None:
            return payload, None
        errors.append(f"{command_name} output was not parseable JSON")
    return None, "; ".join(errors) if errors else None


def _candidate_commands() -> list[str]:
    explicit = (os.environ.get("OCTAGON_MCP_COMMAND") or "").strip()
    candidates = [explicit] if explicit else ["octagon", "octagon-mcp", "octagon_mcp"]
    out: list[str] = []
    for name in candidates:
        if not name:
            continue
        if shutil.which(name):
            out.append(name)
    return out


def _run_octagon_rest_search(topic: str, *, limit: int) -> tuple[dict[str, Any] | None, str | None]:
    api_key = (os.environ.get("OCTAGON_API_KEY") or "").strip()
    if not api_key:
        return None, "OCTAGON_API_KEY not set for REST fallback"

    base_url = (os.environ.get("OCTAGON_API_BASE_URL") or "https://api.octagonai.co/v1").strip()
    model = (os.environ.get("OCTAGON_MODEL") or "octagon-sec-agent").strip()
    system_prompt = (
        "Return only strict JSON with top-level key 'results'. "
        "Each result must be an object with: id, company, role, score, url, summary, program_stage."
    )
    user_prompt = (
        f"Find up to {limit} companies relevant to: {topic}. "
        "Classify each as partner, acquirer, or comparable."
    )
    payload = {
        "model": model,
        "messages": [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": user_prompt},
        ],
        "stream": False,
    }
    headers = {"Authorization": f"Bearer {api_key}", "Content-Type": "application/json"}
    try:
        with httpx.Client(timeout=float(os.environ.get("OCTAGON_TIMEOUT_SECONDS", "25"))) as client:
            response = client.post(f"{base_url}/chat/completions", headers=headers, json=payload)
            response.raise_for_status()
            raw = response.json()
    except Exception as exc:  # noqa: BLE001
        return None, f"Octagon REST fallback failed: {exc}"

    parsed = _extract_chat_json(raw)
    if parsed is None:
        return None, "Octagon REST fallback returned unparsable content"
    return parsed, None


def _extract_chat_json(payload: dict[str, Any]) -> dict[str, Any] | None:
    choices = payload.get("choices")
    if not isinstance(choices, list) or not choices:
        return None
    first = choices[0]
    if not isinstance(first, dict):
        return None
    message = first.get("message")
    if not isinstance(message, dict):
        return None
    content = message.get("content")
    if isinstance(content, str):
        parsed = _parse_json(content)
        if parsed is not None:
            return parsed
    elif isinstance(content, list):
        merged = " ".join(
            str(item.get("text"))
            for item in content
            if isinstance(item, dict) and item.get("text") is not None
        ).strip()
        if merged:
            parsed = _parse_json(merged)
            if parsed is not None:
                return parsed
    return None


def _merge_errors(cli_error: str | None, rest_error: str | None) -> str:
    parts = [part for part in (cli_error, rest_error) if part]
    return "; ".join(parts) if parts else "Octagon retrieval failed"


def extract_records(payload: dict[str, Any]) -> list[dict[str, Any]]:
    """Extract a list of mapping-like records from nested payloads."""
    rows: list[dict[str, Any]] = []

    def visit(value: Any) -> None:
        if isinstance(value, list):
            if value and all(isinstance(item, dict) for item in value):
                rows.extend(item for item in value if isinstance(item, dict))
                return
            for item in value:
                visit(item)
            return
        if isinstance(value, dict):
            for key in ("results", "items", "companies", "data", "rows"):
                child = value.get(key)
                if isinstance(child, list):
                    visit(child)
            for child in value.values():
                if isinstance(child, (list, dict)):
                    visit(child)

    visit(payload)
    deduped: list[dict[str, Any]] = []
    seen: set[str] = set()
    for row in rows:
        key = json.dumps(row, sort_keys=True, default=str)
        if key in seen:
            continue
        seen.add(key)
        deduped.append(row)
    return deduped


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
