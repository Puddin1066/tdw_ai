from __future__ import annotations

from pathlib import Path

import pytest

from pipeline.config_loader import load_case_config, summarize_input_quality
from pipeline.types import repo_root


ROOT = repo_root()


def test_input_quality_band_for_rich_case() -> None:
    config = load_case_config(ROOT / "configs" / "cases" / "sting_pdac.yaml")
    quality = summarize_input_quality(config)
    assert quality["input_primary_complete"] is True
    assert quality["input_breadth_count"] >= 6
    assert quality["input_quality_band"] == "RICH"
    assert quality["input_preferred_minimum_met"] is True


def test_input_quality_band_for_minimal_case(tmp_path: Path) -> None:
    config_path = tmp_path / "minimal_case.yaml"
    config_path.write_text(
        "\n".join(
            [
                "case_id: minimal_case",
                "display_name: Minimal Case",
                "workflow: translational_diligence",
                "version: v0.5",
                "target:",
                "  name: EGFR",
                "  canonical_id: null",
                "  aliases: []",
                "indication:",
                "  name: lung cancer",
                "  aliases: []",
                "sources:",
                "  pubmed: true",
                "  clinicaltrials: true",
                "  opentargets: true",
                "  chembl: true",
                "  biothings: true",
                "  octagon_market: false",
                "  local_docs: false",
                "limits:",
                "  max_literature_records: 50",
                "  max_trials: 100",
                "  max_evidence_rows: 100",
                "run_mode_defaults:",
                "  fixture_allowed: true",
                "  live_allowed: true",
            ]
        )
        + "\n",
        encoding="utf-8",
    )
    config = load_case_config(config_path)
    quality = summarize_input_quality(config)
    assert quality["input_primary_complete"] is True
    assert quality["input_breadth_count"] == 0
    assert quality["input_quality_band"] == "MINIMAL"
    assert quality["input_preferred_minimum_met"] is False
    warnings = quality["input_quality_warnings"]
    assert isinstance(warnings, list) and warnings
    assert any("Low input specificity" in warning for warning in warnings)


def test_input_quality_allows_optional_target_and_indication(tmp_path: Path) -> None:
    config_path = tmp_path / "optional_anchor_case.yaml"
    config_path.write_text(
        "\n".join(
            [
                "case_id: optional_anchor_case",
                "display_name: Optional Anchor Case",
                "workflow: translational_diligence",
                "version: v0.5",
                "target:",
                "  name: ''",
                "  canonical_id: null",
                "  aliases: []",
                "indication:",
                "  name: ''",
                "  aliases: []",
                "sources:",
                "  pubmed: true",
                "  clinicaltrials: true",
                "  opentargets: true",
                "  chembl: true",
                "  biothings: true",
                "  uniprot: true",
                "  reactome: true",
                "  gwas: true",
                "  pharmgkb: true",
                "  openfda: true",
                "  octagon_market: false",
                "  local_docs: false",
                "limits:",
                "  max_literature_records: 50",
                "  max_trials: 100",
                "  max_evidence_rows: 100",
                "run_mode_defaults:",
                "  fixture_allowed: true",
                "  live_allowed: true",
            ]
        )
        + "\n",
        encoding="utf-8",
    )
    config = load_case_config(config_path)
    assert config.target.name == ""
    assert config.indication.name == ""
    quality = summarize_input_quality(config)
    assert quality["input_primary_complete"] is False


@pytest.mark.parametrize(
    ("case_id", "expected_band"),
    [
        ("iaip_sepsis", "RICH"),
        ("parp_breast", "RICH"),
        ("tau_alzheimers", "RICH"),
    ],
)
def test_input_quality_band_for_all_seed_cases(case_id: str, expected_band: str) -> None:
    config = load_case_config(ROOT / "configs" / "cases" / f"{case_id}.yaml")
    quality = summarize_input_quality(config)
    assert quality["input_quality_band"] == expected_band
