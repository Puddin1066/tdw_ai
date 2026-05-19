from __future__ import annotations

from pathlib import Path

from pipeline import runtime_env


def test_load_repo_env_reads_dotenv(monkeypatch, tmp_path: Path) -> None:
    env_path = tmp_path / ".env"
    env_path.write_text("OPENAI_API_KEY=test-key\nOPENAI_MODEL=gpt-test\n", encoding="utf-8")
    monkeypatch.setattr(runtime_env, "repo_root", lambda: tmp_path)
    monkeypatch.setattr(runtime_env, "_ENV_LOADED", False)
    monkeypatch.delenv("OPENAI_API_KEY", raising=False)
    monkeypatch.delenv("OPENAI_MODEL", raising=False)

    loaded = runtime_env.load_repo_env(force=True)

    assert loaded is True
    assert runtime_env.os.environ.get("OPENAI_API_KEY") == "test-key"
    assert runtime_env.os.environ.get("OPENAI_MODEL") == "gpt-test"


def test_load_repo_env_preserves_existing_values(monkeypatch, tmp_path: Path) -> None:
    env_path = tmp_path / ".env"
    env_path.write_text("OPENAI_MODEL=from-file\n", encoding="utf-8")
    monkeypatch.setattr(runtime_env, "repo_root", lambda: tmp_path)
    monkeypatch.setattr(runtime_env, "_ENV_LOADED", False)
    monkeypatch.setenv("OPENAI_MODEL", "from-env")

    runtime_env.load_repo_env(force=True)

    assert runtime_env.os.environ.get("OPENAI_MODEL") == "from-env"
