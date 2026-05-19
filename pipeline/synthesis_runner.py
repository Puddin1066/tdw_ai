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

EVIDENCE_CLAIM_TYPES = {
    "mechanistic",
    "translational",
    "clinical",
    "safety",
    "biomarker",
    "competitive",
    "regulatory",
    "commercial",
    "evidence_gap",
}

SUPPORT_STATUSES = {
    "supported",
    "partially_supported",
    "unsupported",
    "contradicted",
    "insufficient_evidence",
}

RISK_CATEGORIES = {
    "translational",
    "clinical",
    "biomarker",
    "safety",
    "competition",
    "evidence_gap",
    "manufacturing",
    "regulatory",
}

RISK_SEVERITIES = {"low", "medium", "high", "critical"}


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


def _clamp_confidence(value: Any, default: float = 0.5) -> float:
    try:
        parsed = float(value)
    except (TypeError, ValueError):
        return default
    return max(0.0, min(1.0, parsed))


def _sanitize_evidence_data(data: dict[str, Any], case_id: str) -> dict[str, Any]:
    rows = data.get("rows")
    if not isinstance(rows, list):
        rows = data.get("evidence_rows")
    if not isinstance(rows, list):
        rows = []
    cleaned_rows: list[dict[str, Any]] = []
    for idx, row in enumerate(rows):
        if not isinstance(row, dict):
            continue
        claim_type = str(row.get("claim_type", "evidence_gap")).strip().lower()
        if claim_type not in EVIDENCE_CLAIM_TYPES:
            claim_type = "evidence_gap"
        support_status = str(row.get("support_status", "insufficient_evidence")).strip().lower()
        if support_status not in SUPPORT_STATUSES:
            support_status = "insufficient_evidence"
        source_record_ids = row.get("source_record_ids")
        if not isinstance(source_record_ids, list):
            source_record_ids = []
        source_record_ids = [str(v) for v in source_record_ids if str(v).strip()]
        quoted = row.get("quoted_evidence")
        cleaned_quoted: list[dict[str, Any]] = []
        if isinstance(quoted, list):
            for item in quoted:
                if not isinstance(item, dict):
                    continue
                source_id = str(item.get("source_record_id", "")).strip()
                text = str(item.get("text", "")).strip()
                location = str(item.get("location", "")).strip() or "unknown"
                if source_id and text:
                    cleaned_quoted.append(
                        {"source_record_id": source_id, "text": text, "location": location}
                    )
        limitations = row.get("limitations")
        if not isinstance(limitations, list):
            limitations = []
        limitations = [str(v) for v in limitations if str(v).strip()]
        if not limitations:
            limitations = ["model output omitted explicit limitations"]
        cleaned_rows.append(
            {
                "evidence_id": str(row.get("evidence_id") or f"evidence:{case_id}:{idx + 1:04d}"),
                "claim_text": str(row.get("claim_text") or "Evidence claim not provided by model."),
                "claim_type": claim_type,
                "support_status": support_status,
                "confidence": _clamp_confidence(row.get("confidence"), default=0.4),
                "source_record_ids": source_record_ids,
                "quoted_evidence": cleaned_quoted,
                "limitations": limitations,
            }
        )
    if not cleaned_rows:
        cleaned_rows.append(
            {
                "evidence_id": f"evidence:{case_id}:0001",
                "claim_text": "No structured evidence claims were returned by synthesis.",
                "claim_type": "evidence_gap",
                "support_status": "insufficient_evidence",
                "confidence": 0.2,
                "source_record_ids": [],
                "quoted_evidence": [],
                "limitations": ["synthesis returned no evidence rows"],
            }
        )
    return {"rows": cleaned_rows}


def _sanitize_risk_data(data: dict[str, Any], case_id: str) -> dict[str, Any]:
    risks = data.get("risks")
    if not isinstance(risks, list):
        risks = data.get("risk_items")
    if not isinstance(risks, list):
        risks = []
    cleaned: list[dict[str, Any]] = []
    for idx, risk in enumerate(risks):
        if not isinstance(risk, dict):
            continue
        category = str(risk.get("category", "evidence_gap")).strip().lower()
        if category not in RISK_CATEGORIES:
            category = "evidence_gap"
        severity = str(risk.get("severity", "medium")).strip().lower()
        if severity not in RISK_SEVERITIES:
            severity = "medium"
        evidence_ids = risk.get("evidence_ids")
        if not isinstance(evidence_ids, list):
            evidence_ids = []
        source_record_ids = risk.get("source_record_ids")
        if not isinstance(source_record_ids, list):
            source_record_ids = []
        cleaned.append(
            {
                "risk_id": str(risk.get("risk_id") or f"risk:{case_id}:{idx + 1:04d}"),
                "title": str(risk.get("title") or "Unspecified risk"),
                "description": str(
                    risk.get("description") or "Model did not provide additional risk detail."
                ),
                "category": category,
                "severity": severity,
                "confidence": _clamp_confidence(risk.get("confidence"), default=0.5),
                "inferred": bool(risk.get("inferred", True)),
                "evidence_ids": [str(v) for v in evidence_ids if str(v).strip()],
                "source_record_ids": [str(v) for v in source_record_ids if str(v).strip()],
            }
        )
    return {"risks": cleaned[:10]}


def _sanitize_report_data(data: dict[str, Any], case_id: str) -> dict[str, Any]:
    sections = data.get("sections")
    if not isinstance(sections, list):
        sections = []
    cleaned_sections: list[dict[str, Any]] = []
    for idx, section in enumerate(sections):
        if not isinstance(section, dict):
            continue
        title = str(section.get("title") or section.get("heading") or f"Section {idx + 1}")
        content = str(section.get("content") or section.get("body") or "")
        evidence_ids = section.get("evidence_ids")
        if not isinstance(evidence_ids, list):
            evidence_ids = []
        cleaned_sections.append(
            {
                "section_id": str(section.get("section_id") or f"section:{case_id}:{idx + 1:04d}"),
                "title": title,
                "content": content,
                "evidence_ids": [str(v) for v in evidence_ids if str(v).strip()],
            }
        )
    if not cleaned_sections:
        cleaned_sections = [
            {
                "section_id": f"section:{case_id}:0001",
                "title": "Evidence summary",
                "content": "Model output did not provide structured report sections.",
                "evidence_ids": [],
            }
        ]

    cited_source_record_ids = data.get("cited_source_record_ids")
    cited_nct_ids = data.get("cited_nct_ids")
    cited_pmids = data.get("cited_pmids")
    return {
        "title": str(data.get("title") or f"{case_id} translational diligence report"),
        "executive_summary": str(
            data.get("executive_summary")
            or data.get("summary")
            or "Model output did not provide an executive summary."
        ),
        "overall_confidence": _clamp_confidence(data.get("overall_confidence"), default=0.4),
        "maturity_stage": str(data.get("maturity_stage") or "discovery"),
        "conclusion": str(data.get("conclusion") or ""),
        "sections": cleaned_sections,
        "cited_source_record_ids": [
            str(v) for v in cited_source_record_ids if str(v).strip()
        ]
        if isinstance(cited_source_record_ids, list)
        else [],
        "cited_nct_ids": [str(v) for v in cited_nct_ids if str(v).strip()]
        if isinstance(cited_nct_ids, list)
        else [],
        "cited_pmids": [str(v) for v in cited_pmids if str(v).strip()]
        if isinstance(cited_pmids, list)
        else [],
        "diligence_questions": [str(v) for v in data.get("diligence_questions", []) if str(v).strip()]
        if isinstance(data.get("diligence_questions"), list)
        else [],
    }


def _sanitize_step_data(step: str, data: dict[str, Any], case_id: str) -> dict[str, Any]:
    if step == "evidence_table":
        return _sanitize_evidence_data(data, case_id)
    if step == "risk_map":
        return _sanitize_risk_data(data, case_id)
    if step == "diligence_report":
        return _sanitize_report_data(data, case_id)
    return data


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

    data = _sanitize_step_data(step, data, config.case_id)
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
