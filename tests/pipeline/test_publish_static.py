from __future__ import annotations

from pathlib import Path

import pytest

from pipeline import publish_static


def test_resolve_case_configs_all_cases(tmp_path: Path) -> None:
    config_dir = tmp_path / "cases"
    config_dir.mkdir(parents=True)
    for case_id in ("sting_pdac", "parp_breast"):
        (config_dir / f"{case_id}.yaml").write_text("case_id: test\n", encoding="utf-8")

    resolved = publish_static.resolve_case_configs(config_dir, requested_cases=[], all_cases=True)
    assert [path.name for path in resolved] == ["parp_breast.yaml", "sting_pdac.yaml"]


def test_publish_cases_runs_eval_and_copy(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
    config_path = tmp_path / "sting_pdac.yaml"
    config_path.write_text("case_id: sting_pdac\n", encoding="utf-8")
    case_dir = tmp_path / "generated" / "sting_pdac"
    web_dir = tmp_path / "web" / "public" / "data" / "cases" / "sting_pdac"
    case_dir.mkdir(parents=True)
    web_dir.parent.mkdir(parents=True, exist_ok=True)

    class _Config:
        case_id = "sting_pdac"
        class sources:
            pubmed = True
            clinicaltrials = True
            opentargets = True
            chembl = True
            biothings = True

    monkeypatch.setattr(publish_static, "load_case_config", lambda _: _Config())
    monkeypatch.setattr(publish_static, "run_case_workflow", lambda config, mode: case_dir)
    monkeypatch.setattr(
        publish_static,
        "run_evaluations",
        lambda _: {"data": {"overall_passed": True, "aggregate_score": 0.91}},
    )
    monkeypatch.setattr(publish_static, "write_eval_results", lambda _, __: case_dir / "eval_results.json")
    monkeypatch.setattr(publish_static, "copy_to_web", lambda *_args, **_kwargs: web_dir)

    results = publish_static.publish_cases(
        [config_path],
        mode="fixture",
        run_evals=True,
        allow_failed_evals=False,
        allow_comparability_fail=False,
        validate_schemas=False,
        require_biomcp=False,
    )
    assert len(results) == 1
    first = results[0]
    assert first.case_id == "sting_pdac"
    assert first.case_dir == case_dir
    assert first.web_dir == web_dir
    assert first.eval_passed is True
    assert first.eval_score == pytest.approx(0.91)
    assert first.comparability_passed is True


def test_publish_cases_fails_when_eval_fails(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
    config_path = tmp_path / "sting_pdac.yaml"
    config_path.write_text("case_id: sting_pdac\n", encoding="utf-8")
    case_dir = tmp_path / "generated" / "sting_pdac"
    case_dir.mkdir(parents=True)

    class _Config:
        case_id = "sting_pdac"
        class sources:
            pubmed = True
            clinicaltrials = True
            opentargets = True
            chembl = True
            biothings = True

    monkeypatch.setattr(publish_static, "load_case_config", lambda _: _Config())
    monkeypatch.setattr(publish_static, "run_case_workflow", lambda config, mode: case_dir)
    monkeypatch.setattr(
        publish_static,
        "run_evaluations",
        lambda _: {"data": {"overall_passed": False, "aggregate_score": 0.2}},
    )
    monkeypatch.setattr(publish_static, "write_eval_results", lambda _, __: case_dir / "eval_results.json")
    monkeypatch.setattr(publish_static, "copy_to_web", lambda *_args, **_kwargs: case_dir)

    with pytest.raises(RuntimeError, match="Eval failed"):
        publish_static.publish_cases(
            [config_path],
            mode="fixture",
            run_evals=True,
            allow_failed_evals=False,
            allow_comparability_fail=False,
            validate_schemas=False,
            require_biomcp=False,
        )


def test_publish_cases_fails_strict_biomcp_on_warning(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    config_path = tmp_path / "sting_pdac.yaml"
    config_path.write_text("case_id: sting_pdac\n", encoding="utf-8")
    case_dir = tmp_path / "generated" / "sting_pdac"
    case_dir.mkdir(parents=True)
    (case_dir / "raw").mkdir(parents=True, exist_ok=True)
    (case_dir / "source_manifest.json").write_text(
        """{
  "data": {
    "entries": [
      {
        "connector_name": "pubmed",
        "warnings": ["BioMCP pubmed search warning: biomcp executable not found in PATH"],
        "errors": []
      }
    ]
  }
}
""",
        encoding="utf-8",
    )
    (case_dir / "raw" / "pubmed_raw.json").write_text(
        """{"raw_payload":{"backend":"native"}}""",
        encoding="utf-8",
    )

    class _Config:
        case_id = "sting_pdac"

        class sources:
            pubmed = True
            clinicaltrials = False
            opentargets = False
            chembl = False
            biothings = False

    monkeypatch.setattr(publish_static, "load_case_config", lambda _: _Config())
    monkeypatch.setattr(publish_static, "run_case_workflow", lambda config, mode: case_dir)
    monkeypatch.setattr(
        publish_static,
        "run_evaluations",
        lambda _: {"data": {"overall_passed": True, "aggregate_score": 1.0}},
    )
    monkeypatch.setattr(publish_static, "write_eval_results", lambda _, __: case_dir / "eval_results.json")
    monkeypatch.setattr(publish_static, "copy_to_web", lambda *_args, **_kwargs: case_dir)

    with pytest.raises(RuntimeError, match="BioMCP strict mode failed"):
        publish_static.publish_cases(
            [config_path],
            mode="live",
            run_evals=True,
            allow_failed_evals=False,
            allow_comparability_fail=False,
            validate_schemas=False,
            require_biomcp=True,
        )


def test_publish_cases_live_requires_evals_for_comparability(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    config_path = tmp_path / "sting_pdac.yaml"
    config_path.write_text("case_id: sting_pdac\n", encoding="utf-8")
    case_dir = tmp_path / "generated" / "sting_pdac"
    case_dir.mkdir(parents=True)

    class _Config:
        case_id = "sting_pdac"
        class sources:
            pubmed = True
            clinicaltrials = True
            opentargets = True
            chembl = True
            biothings = True

    monkeypatch.setattr(publish_static, "load_case_config", lambda _: _Config())
    monkeypatch.setattr(publish_static, "run_case_workflow", lambda config, mode: case_dir)
    monkeypatch.setattr(publish_static, "copy_to_web", lambda *_args, **_kwargs: case_dir)

    with pytest.raises(RuntimeError, match="Comparability policy requires evals"):
        publish_static.publish_cases(
            [config_path],
            mode="live",
            run_evals=False,
            allow_failed_evals=False,
            allow_comparability_fail=False,
            validate_schemas=False,
            require_biomcp=False,
        )


def test_publish_cases_live_blocks_on_comparability_failure(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    config_path = tmp_path / "sting_pdac.yaml"
    config_path.write_text("case_id: sting_pdac\n", encoding="utf-8")
    case_dir = tmp_path / "generated" / "sting_pdac"
    case_dir.mkdir(parents=True)

    class _Config:
        case_id = "sting_pdac"
        class sources:
            pubmed = True
            clinicaltrials = True
            opentargets = True
            chembl = True
            biothings = True

    payload = {
        "data": {
            "overall_passed": True,
            "aggregate_score": 0.88,
            "metrics": {
                "benchmark_contract_passed": False,
                "contract_connectors_with_records": 2,
                "contract_total_records": 8,
                "contract_fallback_entries": 1,
                "contract_generic_risk_titles": 1,
            },
        }
    }
    monkeypatch.setattr(publish_static, "load_case_config", lambda _: _Config())
    monkeypatch.setattr(publish_static, "run_case_workflow", lambda config, mode: case_dir)
    monkeypatch.setattr(publish_static, "run_evaluations", lambda _: payload)
    monkeypatch.setattr(publish_static, "write_eval_results", lambda _, __: case_dir / "eval_results.json")
    monkeypatch.setattr(publish_static, "copy_to_web", lambda *_args, **_kwargs: case_dir)

    with pytest.raises(RuntimeError, match="Comparability policy failed"):
        publish_static.publish_cases(
            [config_path],
            mode="live",
            run_evals=True,
            allow_failed_evals=False,
            allow_comparability_fail=False,
            validate_schemas=False,
            require_biomcp=False,
        )
