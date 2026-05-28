"""Tests for Brown VIVO profile URL resolution."""

from __future__ import annotations

from pipeline.brown_vivo_profiles import (
    brown_vivo_url,
    is_brown_vivo_url,
    resolve_brown_vivo_url,
    slug_candidates,
)


def test_brown_vivo_url_format():
    assert brown_vivo_url("smargoli") == "https://vivo.brown.edu/display/smargoli"
    assert is_brown_vivo_url("https://vivo.brown.edu/display/smargoli")


def test_slug_candidates_known_patterns():
    assert "smargoli" in slug_candidates("Seth Margolis")
    assert "wasaad" in slug_candidates("Wael Asaad")
    assert "anurmikk" in slug_candidates("Arto V Nurmikko")


def test_resolve_known_curated_slug():
    url = resolve_brown_vivo_url("Jack A Elias", verify=False)
    assert url == "https://vivo.brown.edu/display/jaelias"
