"""Runtime environment helpers for local CLI workflows."""

from __future__ import annotations

import os
from pathlib import Path

from pipeline.types import repo_root

_ENV_LOADED = False


def load_repo_env(*, force: bool = False) -> bool:
    """Load repo `.env` values into process env if present.

    This keeps local CLI commands deterministic: users can set `OPENAI_API_KEY` in
    `.env` without manually exporting vars in every shell session.
    """
    global _ENV_LOADED
    if _ENV_LOADED and not force:
        return False
    if os.environ.get("TDW_SKIP_REPO_ENV") == "1":
        _ENV_LOADED = True
        return False

    env_path = repo_root() / ".env"
    if not env_path.is_file():
        _ENV_LOADED = True
        return False

    loaded_any = False
    for raw_line in env_path.read_text(encoding="utf-8").splitlines():
        line = raw_line.strip()
        if not line or line.startswith("#"):
            continue
        if line.startswith("export "):
            line = line[len("export ") :].strip()
        if "=" not in line:
            continue
        key, value = line.split("=", 1)
        key = key.strip()
        if not key:
            continue
        value = value.strip()
        if len(value) >= 2 and value[0] == value[-1] and value[0] in {'"', "'"}:
            value = value[1:-1]
        os.environ.setdefault(key, value)
        loaded_any = True

    _ENV_LOADED = True
    return loaded_any

