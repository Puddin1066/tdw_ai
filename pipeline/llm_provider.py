"""LLM provider abstraction for build-time synthesis (§24.9)."""

from __future__ import annotations

import json
import os
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Protocol, runtime_checkable

from pipeline.runtime_env import load_repo_env
from pipeline.types import repo_root

SYNTHESIS_FIXTURES = repo_root() / "tests" / "fixtures" / "synthesis"


@dataclass
class LLMUsage:
    input_tokens: int = 0
    output_tokens: int = 0
    estimated_cost_usd: float = 0.0


@dataclass
class LLMResponse:
    provider_name: str
    model_name: str
    output_json: dict[str, Any]
    raw_text: str | None = None
    usage: LLMUsage = field(default_factory=LLMUsage)
    finish_reason: str = "stop"
    errors: list[str] = field(default_factory=list)
    warnings: list[str] = field(default_factory=list)


@dataclass(frozen=True)
class ProviderSelection:
    provider: LLMProvider
    using_live_api: bool
    reason: str


@runtime_checkable
class LLMProvider(Protocol):
    provider_name: str

    def generate_json(
        self,
        prompt: str,
        schema: dict[str, Any],
        temperature: float,
        max_output_tokens: int,
        metadata: dict[str, Any],
    ) -> LLMResponse:
        ...


class MockProvider:
    """Deterministic synthesis for fixture/CI and live mode without API keys."""

    provider_name = "mock"

    def __init__(self, *, model_name: str = "mock-synthesis-v1") -> None:
        self.model_name = model_name

    def generate_json(
        self,
        prompt: str,
        schema: dict[str, Any],
        temperature: float,
        max_output_tokens: int,
        metadata: dict[str, Any],
    ) -> LLMResponse:
        del prompt, schema, temperature, max_output_tokens
        case_id = str(metadata.get("case_id", "sting_pdac"))
        step = str(metadata.get("step", "evidence_table"))
        path = SYNTHESIS_FIXTURES / f"{case_id}_{step}_data.json"
        if not path.is_file():
            return LLMResponse(
                provider_name=self.provider_name,
                model_name=self.model_name,
                output_json={},
                errors=[f"Mock synthesis fixture missing: {path}"],
            )
        try:
            data = json.loads(path.read_text(encoding="utf-8"))
        except json.JSONDecodeError as exc:
            return LLMResponse(
                provider_name=self.provider_name,
                model_name=self.model_name,
                output_json={},
                errors=[f"Invalid mock fixture JSON: {exc}"],
            )
        if not isinstance(data, dict):
            return LLMResponse(
                provider_name=self.provider_name,
                model_name=self.model_name,
                output_json={},
                errors=["Mock fixture must be a JSON object (artifact data payload)"],
            )
        return LLMResponse(
            provider_name=self.provider_name,
            model_name=self.model_name,
            output_json=data,
            raw_text=json.dumps(data),
            usage=LLMUsage(input_tokens=100, output_tokens=200),
            finish_reason="stop",
            warnings=["MOCK/SYNTHETIC — not live model output"],
        )


class OpenAIProvider:
    """Build-time OpenAI JSON synthesis when OPENAI_API_KEY is set."""

    provider_name = "openai"

    def __init__(
        self,
        *,
        model_name: str | None = None,
        api_key: str | None = None,
    ) -> None:
        self.model_name = model_name or os.environ.get("OPENAI_MODEL", "gpt-4.1-mini")
        self._api_key = api_key or os.environ.get("OPENAI_API_KEY")

    def generate_json(
        self,
        prompt: str,
        schema: dict[str, Any],
        temperature: float,
        max_output_tokens: int,
        metadata: dict[str, Any],
    ) -> LLMResponse:
        del metadata
        if not self._api_key:
            return LLMResponse(
                provider_name=self.provider_name,
                model_name=self.model_name,
                output_json={},
                errors=["OPENAI_API_KEY not set"],
            )
        try:
            from openai import OpenAI
        except ImportError:
            return LLMResponse(
                provider_name=self.provider_name,
                model_name=self.model_name,
                output_json={},
                errors=["openai package not installed; pip install -e '.[live]'"],
            )

        client = OpenAI(api_key=self._api_key)
        schema_hint = json.dumps(schema, indent=2)[:8000]
        full_prompt = (
            f"{prompt}\n\n"
            "Respond with a single JSON object matching this schema shape (data payload only):\n"
            f"{schema_hint}"
        )
        try:
            completion = client.chat.completions.create(
                model=self.model_name,
                messages=[
                    {
                        "role": "system",
                        "content": "You emit valid JSON only. No markdown fences.",
                    },
                    {"role": "user", "content": full_prompt},
                ],
                temperature=temperature,
                max_tokens=max_output_tokens,
                response_format={"type": "json_object"},
            )
        except Exception as exc:  # noqa: BLE001
            return LLMResponse(
                provider_name=self.provider_name,
                model_name=self.model_name,
                output_json={},
                errors=[f"OpenAI API error: {exc}"],
            )

        raw = completion.choices[0].message.content or "{}"
        try:
            parsed = json.loads(raw)
        except json.JSONDecodeError as exc:
            return LLMResponse(
                provider_name=self.provider_name,
                model_name=self.model_name,
                output_json={},
                raw_text=raw,
                errors=[f"Model returned non-JSON: {exc}"],
            )
        usage = completion.usage
        return LLMResponse(
            provider_name=self.provider_name,
            model_name=self.model_name,
            output_json=parsed if isinstance(parsed, dict) else {"value": parsed},
            raw_text=raw,
            usage=LLMUsage(
                input_tokens=getattr(usage, "prompt_tokens", 0) or 0,
                output_tokens=getattr(usage, "completion_tokens", 0) or 0,
            ),
            finish_reason=completion.choices[0].finish_reason or "stop",
        )


def get_provider(*, prefer_live: bool = False) -> LLMProvider:
    """Select provider: OpenAI when key present and prefer_live; else MockProvider."""
    return select_provider(prefer_live=prefer_live).provider


def select_provider(*, prefer_live: bool = False) -> ProviderSelection:
    """Return provider plus explicit selection reason for auditability."""
    load_repo_env()
    if prefer_live and os.environ.get("OPENAI_API_KEY"):
        return ProviderSelection(
            provider=OpenAIProvider(),
            using_live_api=True,
            reason="OPENAI_API_KEY detected; using OpenAIProvider",
        )
    if prefer_live:
        return ProviderSelection(
            provider=MockProvider(),
            using_live_api=False,
            reason="OPENAI_API_KEY missing; using MockProvider (MOCK/SYNTHETIC)",
        )
    return ProviderSelection(
        provider=MockProvider(),
        using_live_api=False,
        reason="Fixture mode defaults to MockProvider (MOCK/SYNTHETIC)",
    )


def get_provider_status(*, prefer_live: bool = False) -> dict[str, Any]:
    """Expose provider decision details for run metadata and debugging."""
    selection = select_provider(prefer_live=prefer_live)
    provider = selection.provider
    provider_name = getattr(provider, "provider_name", provider.__class__.__name__.lower())
    model_name = getattr(provider, "model_name", None)
    return {
        "provider_name": provider_name,
        "model_name": model_name,
        "mocked_api_calls": provider_name == "mock",
        "using_live_api": selection.using_live_api,
        "selection_reason": selection.reason,
    }
