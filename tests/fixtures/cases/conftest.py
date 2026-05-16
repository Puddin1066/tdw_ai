"""Pytest helpers for case fixture materialization."""

from __future__ import annotations

from pathlib import Path

import pytest

from tests.fixtures.cases._helpers import bad_nct_packet, base_packet, write_packet


@pytest.fixture
def sting_pdac_case(tmp_path: Path) -> Path:
    return write_packet(tmp_path / "sting_pdac", base_packet())


@pytest.fixture
def sting_pdac_bad_nct_case(tmp_path: Path) -> Path:
    return write_packet(tmp_path / "sting_pdac_bad_nct", bad_nct_packet())
