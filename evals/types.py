"""Shared evaluation result types."""

from __future__ import annotations

from dataclasses import asdict, dataclass, field
from typing import Any


@dataclass
class EvaluationResult:
    evaluator_name: str
    case_id: str
    passed: bool
    score: float
    errors: list[str] = field(default_factory=list)
    warnings: list[str] = field(default_factory=list)
    checked_artifacts: list[str] = field(default_factory=list)
    metrics: dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)
