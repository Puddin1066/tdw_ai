from __future__ import annotations

from types import SimpleNamespace

from connectors.biomcp_adapter import (
    run_biomcp_openfda_label_get,
    run_biomcp_search,
    run_biomcp_trial_get,
)


def _proc(returncode: int, stdout: str = "", stderr: str = "") -> SimpleNamespace:
    return SimpleNamespace(returncode=returncode, stdout=stdout, stderr=stderr)


def test_run_biomcp_search_falls_back_to_modern_article_command(monkeypatch) -> None:
    calls: list[list[str]] = []

    def _fake_run(command, **kwargs):  # noqa: ANN001
        del kwargs
        calls.append(command)
        if command[:3] == ["biomcp", "search", "article"]:
            return _proc(1, stderr="No such command 'search'")
        return _proc(0, stdout='{"results":[{"id":"35600001","title":"Paper"}]}')

    monkeypatch.setattr("connectors.biomcp_adapter.shutil.which", lambda _: "/usr/bin/biomcp")
    monkeypatch.setattr("connectors.biomcp_adapter.subprocess.run", _fake_run)

    payload, err = run_biomcp_search("article", "TMEM173", limit=25, offset=0)
    assert err is None
    assert payload and payload["results"][0]["id"] == "35600001"
    assert calls[1][:3] == ["biomcp", "article", "search"]


def test_run_biomcp_search_maps_pathway_to_gene_reactome_enrichment(monkeypatch) -> None:
    calls: list[list[str]] = []

    def _fake_run(command, **kwargs):  # noqa: ANN001
        del kwargs
        calls.append(command)
        if command[:3] == ["biomcp", "search", "pathway"]:
            return _proc(1, stderr="No such command 'search'")
        return _proc(0, stdout='{"results":[{"id":"TP53","summary":"Reactome pathways"}]}')

    monkeypatch.setattr("connectors.biomcp_adapter.shutil.which", lambda _: "/usr/bin/biomcp")
    monkeypatch.setattr("connectors.biomcp_adapter.subprocess.run", _fake_run)

    payload, err = run_biomcp_search("pathway", "TP53", limit=25, offset=0)
    assert err is None
    assert payload and payload["results"]
    assert calls[1] == ["biomcp", "gene", "get", "TP53", "--enrich", "reactome", "-j"]


def test_run_biomcp_search_maps_gwas_to_gene_gwas_enrichment(monkeypatch) -> None:
    calls: list[list[str]] = []

    def _fake_run(command, **kwargs):  # noqa: ANN001
        del kwargs
        calls.append(command)
        if command[:3] == ["biomcp", "search", "gwas"]:
            return _proc(1, stderr="No such command 'search'")
        return _proc(0, stdout='{"results":[{"id":"TP53","summary":"GWAS associations"}]}')

    monkeypatch.setattr("connectors.biomcp_adapter.shutil.which", lambda _: "/usr/bin/biomcp")
    monkeypatch.setattr("connectors.biomcp_adapter.subprocess.run", _fake_run)

    payload, err = run_biomcp_search("gwas", "TP53", limit=25, offset=0)
    assert err is None
    assert payload and payload["results"]
    assert calls[1] == ["biomcp", "gene", "get", "TP53", "--enrich", "gwas", "-j"]


def test_run_biomcp_search_accepts_plain_text_openfda_responses(monkeypatch) -> None:
    calls: list[list[str]] = []

    def _fake_run(command, **kwargs):  # noqa: ANN001
        del kwargs
        calls.append(command)
        if command[:3] == ["biomcp", "search", "adverse-event"]:
            return _proc(1, stderr="No such command 'search'")
        return _proc(0, stdout="## FDA Adverse Event Reports\nFound reports for imatinib")

    monkeypatch.setattr("connectors.biomcp_adapter.shutil.which", lambda _: "/usr/bin/biomcp")
    monkeypatch.setattr("connectors.biomcp_adapter.subprocess.run", _fake_run)

    payload, err = run_biomcp_search("adverse-event", "imatinib", limit=10, offset=0)
    assert err is None
    assert payload and payload["results"]
    assert payload["results"][0]["title"].startswith("## FDA Adverse Event Reports")
    assert calls[1][:4] == ["biomcp", "openfda", "adverse", "search"]


def test_run_biomcp_trial_get_uses_all_module_json(monkeypatch) -> None:
    calls: list[list[str]] = []

    def _fake_run(command, **kwargs):  # noqa: ANN001
        del kwargs
        calls.append(command)
        return _proc(0, stdout='{"protocolSection":{"identificationModule":{"nctId":"NCT01234567"}}}')

    monkeypatch.setattr("connectors.biomcp_adapter.shutil.which", lambda _: "/usr/bin/biomcp")
    monkeypatch.setattr("connectors.biomcp_adapter.subprocess.run", _fake_run)

    payload, err = run_biomcp_trial_get("NCT01234567", module="all")
    assert err is None
    assert payload and payload["protocolSection"]["identificationModule"]["nctId"] == "NCT01234567"
    assert calls[0] == ["biomcp", "trial", "get", "NCT01234567", "all", "-j"]


def test_run_biomcp_search_maps_openfda_label_and_extracts_label_id(monkeypatch) -> None:
    calls: list[list[str]] = []

    def _fake_run(command, **kwargs):  # noqa: ANN001
        del kwargs
        calls.append(command)
        if command[:3] == ["biomcp", "search", "fda-label"]:
            return _proc(1, stderr="No such command 'search'")
        return _proc(
            0,
            stdout=(
                "## FDA Drug Labels\n\n#### 1. IMATINIB MESYLATE\n"
                "*Label ID: 0291eca5-7a1d-4a79-30be-252224d96509*\n"
            ),
        )

    monkeypatch.setattr("connectors.biomcp_adapter.shutil.which", lambda _: "/usr/bin/biomcp")
    monkeypatch.setattr("connectors.biomcp_adapter.subprocess.run", _fake_run)

    payload, err = run_biomcp_search("fda-label", "imatinib", limit=5, offset=0)
    assert err is None
    assert payload and payload["results"]
    assert payload["results"][0]["label_id"] == "0291eca5-7a1d-4a79-30be-252224d96509"
    assert calls[1][:4] == ["biomcp", "openfda", "label", "search"]


def test_run_biomcp_openfda_label_get_uses_expected_command(monkeypatch) -> None:
    calls: list[list[str]] = []

    def _fake_run(command, **kwargs):  # noqa: ANN001
        del kwargs
        calls.append(command)
        return _proc(0, stdout="## Drug Label Details")

    monkeypatch.setattr("connectors.biomcp_adapter.shutil.which", lambda _: "/usr/bin/biomcp")
    monkeypatch.setattr("connectors.biomcp_adapter.subprocess.run", _fake_run)

    payload, err = run_biomcp_openfda_label_get("0291eca5-7a1d-4a79-30be-252224d96509")
    assert err is None
    assert payload and payload["results"]
    assert calls[0] == [
        "biomcp",
        "openfda",
        "label",
        "get",
        "0291eca5-7a1d-4a79-30be-252224d96509",
    ]
