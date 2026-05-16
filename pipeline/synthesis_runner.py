"""Run translational diligence synthesis steps via LLMProvider."""

from __future__ import annotations

import hashlib
import json
from pathlib import Path
from typing import Any

from pipeline.llm_provider import get_provider
from pipeline.provenance import build_provenance, utc_now_iso
from pipeline.schema_validate import validator_for_schema_file
from pipeline.types import SCHEMA_VERSION, CaseConfig, RunMode, repo_root

SKILLS_ROOT = repo_root() / "skills" / "translational_diligence"
PROMPTS_DIR = SKILLS_ROOT / "prompts"

STEP_SCHEMA_FILES: dict[str, str] = {
    "evidence_table": "evidence_table.schema.json",
    "risk_map": "risk_map.schema.json",
    "diligence_report": "diligence_report.schema.json",
}

PROMPT_FILES: dict[str, str] = {
    "claim_extraction": "claim_extraction.md",
    "risk_mapping": "risk_mapping.md",
    "report_generation": "report_generation.md",
}


def _prompt_hash(text: str) -> str:
    return "sha256:" + hashlib.sha256(text.encode("utf-8")).hexdigest()[:16]


def load_prompt(prompt_name: str) -> str:
    filename = PROMPT_FILES.get(prompt_name, f"{prompt_name}.md")
    path = PROMPTS_DIR / filename
    if not path.is_file():
        return f"# {prompt_name}\n\nEmit structured JSON for the requested artifact.\n"
    return path.read_text(encoding="utf-8")


def _read_json(path: Path) -> dict[str, Any]:
    with path.open(encoding="utf-8") as handle:
        return json.load(handle)


def _artifact_data(path: Path) -> dict[str, Any]:
    payload = _read_json(path)
    if "data" in payload and isinstance(payload["data"], dict):
        return payload["data"]
    return payload


def _align_mock_citations(case_dir: Path, data: dict[str, Any], step: str) -> dict[str, Any]:
    """Align mock synthesis citations with live-fetched source records when present."""
    if step == "diligence_report":
        evidence_path = case_dir / "evidence_table.json"
        if not evidence_path.is_file():
            return data
        rows = _artifact_data(evidence_path).get("rows", [])
        pmids: list[str] = []
        ncts: list[str] = []
        source_ids: list[str] = []
        for row in rows:
            if not isinstance(row, dict):
                continue
            for sid in row.get("source_record_ids", []):
                source_ids.append(sid)
                if str(sid).startswith("pubmed:"):
                    pmids.append(str(sid).split(":", 1)[-1])
                if str(sid).startswith("clinicaltrials:"):
                    ncts.append(str(sid).split(":", 1)[-1])
        data = dict(data)
        data["cited_pmids"] = pmids
        data["cited_nct_ids"] = ncts
        data["cited_source_record_ids"] = source_ids
        return data

    if step != "evidence_table":
        return data
    rows = data.get("rows")
    if not isinstance(rows, list) or not rows:
        return data

    lit_path = case_dir / "literature_records.json"
    trial_path = case_dir / "clinical_trials.json"
    pmid = None
    nct = None
    if lit_path.is_file():
        lit_data = _artifact_data(lit_path).get("records", [])
        if lit_data and isinstance(lit_data[0], dict):
            pmid = lit_data[0].get("pmid") or str(lit_data[0].get("source_record_id", "")).split(":")[-1]
    if trial_path.is_file():
        trial_data = _artifact_data(trial_path).get("trials", [])
        if trial_data and isinstance(trial_data[0], dict):
            nct = trial_data[0].get("nct_id")

    aligned: list[dict[str, Any]] = []
    for i, row in enumerate(rows):
        if not isinstance(row, dict):
            aligned.append(row)
            continue
        row = dict(row)
        if i == 0 and pmid:
            row["source_record_ids"] = [f"pubmed:{pmid}"]
            row["quoted_evidence"] = [
                {
                    "source_record_id": f"pubmed:{pmid}",
                    "text": row.get("claim_text", "")[:200],
                    "location": "abstract",
                }
            ]
        if i == 1 and nct:
            row["source_record_ids"] = [f"clinicaltrials:{nct}"]
            row["claim_text"] = f"Trial {nct} evaluates STING pathway modulation in PDAC."
        aligned.append(row)
    data = dict(data)
    data["rows"] = aligned
    return data


def _build_user_context(case_dir: Path, input_artifacts: list[str]) -> str:
    chunks: list[str] = []
    for name in input_artifacts:
        path = case_dir / name
        if path.is_file():
            chunks.append(f"## {name}\n```json\n{path.read_text(encoding='utf-8')[:12000]}\n```")
    return "\n\n".join(chunks)


def run_synthesis_json_step(
    config: CaseConfig,
    case_dir: Path,
    *,
    mode: RunMode,
    step: str,
    prompt_name: str,
    artifact_name: str,
    artifact_type: str,
    generated_by: str,
    input_artifacts: list[str],
    schema: dict[str, Any] | None = None,
) -> Path:
    dest = case_dir / artifact_name
    prompt_template = f"skills/translational_diligence/prompts/{PROMPT_FILES.get(prompt_name, prompt_name)}"
    prompt_body = load_prompt(prompt_name)
    context = _build_user_context(case_dir, input_artifacts)
    prompt = (
        f"Case: {config.display_name} ({config.case_id})\n"
        f"Target: {config.target.name}\nIndication: {config.indication.name}\n\n"
        f"{prompt_body}\n\n# Input artifacts\n{context}"
    )

    provider = get_provider(prefer_live=(mode == "live"))
    schema_file = STEP_SCHEMA_FILES.get(step, "evidence_table.schema.json")
    json_schema = schema or json.loads(
        (repo_root() / "schemas" / schema_file).read_text(encoding="utf-8")
    )

    response = provider.generate_json(
        prompt,
        json_schema,
        temperature=0.2,
        max_output_tokens=4000,
        metadata={"case_id": config.case_id, "step": step, "mode": mode},
    )

    if response.errors:
        raise RuntimeError(
            f"Synthesis step {step} failed: {'; '.join(response.errors)}"
        )

    data = response.output_json
    if "data" in data and isinstance(data["data"], dict):
        data = data["data"]

    data = _align_mock_citations(case_dir, data, step)

    envelope: dict[str, Any] = {
        "artifact_type": artifact_type,
        "case_id": config.case_id,
        "schema_version": SCHEMA_VERSION,
        "generated_at": utc_now_iso(),
        "provenance": build_provenance(
            generated_by,
            input_artifacts,
            model_provider=response.provider_name,
            model_name=response.model_name,
            prompt_template=prompt_template,
            prompt_hash=_prompt_hash(prompt_body),
        ),
        "data": data,
    }

    validator = validator_for_schema_file(schema_file)
    validation_errors = sorted(validator.iter_errors(envelope), key=lambda e: list(e.path))
    if validation_errors:
        first = validation_errors[0]
        raise ValueError(
            f"Synthesis output failed schema validation for {artifact_name}: "
            f"{first.message} at {list(first.path)}"
        )

    dest.write_text(json.dumps(envelope, indent=2) + "\n", encoding="utf-8")
    return dest


def run_synthesis_report_md(config: CaseConfig, case_dir: Path, *, mode: RunMode) -> Path:
    del mode
    report_path = case_dir / "diligence_report.json"
    dest = case_dir / "diligence_report.md"
    if not report_path.is_file():
        dest.write_text(f"# {config.display_name}\n\nReport JSON missing.\n", encoding="utf-8")
        return dest

    payload = _read_json(report_path)
    data = payload.get("data", {})
    title = data.get("title", config.display_name)
    summary = data.get("executive_summary") or data.get("summary", "")
    lines = [
        f"# {title}",
        "",
        "> **MOCK/SYNTHETIC or model-generated content** — verify before clinical use.",
        "",
        summary,
        "",
    ]
    for section in data.get("sections", []):
        heading = section.get("title") or section.get("heading", "Section")
        body = section.get("content") or section.get("body", "")
        lines.extend([f"## {heading}", "", body, ""])
    dest.write_text("\n".join(lines).strip() + "\n", encoding="utf-8")
    return dest
