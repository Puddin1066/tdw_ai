# Schema Agent Handoff

Workstream **F** (MASTER_PRD §4): canonical JSON Schema definitions, matching Python (Pydantic v2) and TypeScript types.

## Artifact inventory (11 JSON schemas)

Maps to PRD §8 case packet artifacts (JSON counterparts of generated files):

| Schema file | Generated artifact | `artifact_type` |
|-------------|-------------------|-----------------|
| `case_metadata.schema.json` | `metadata.yaml` / case card fields | `case_metadata` |
| `source_manifest.schema.json` | `source_manifest.json` | `source_manifest` |
| `normalized_entities.schema.json` | `normalized_entities.json` | `normalized_entities` |
| `literature_records.schema.json` | `literature_records.json` | `literature_records` |
| `clinical_trials.schema.json` | `clinical_trials.json` | `clinical_trials` |
| `target_biology.schema.json` | `target_biology.json` | `target_biology` |
| `evidence_table.schema.json` | `evidence_table.json` | `evidence_table` |
| `diligence_report.schema.json` | `diligence_report.json` | `diligence_report` |
| `risk_map.schema.json` | `risk_map.json` | `risk_map` |
| `knowledge_graph.schema.json` | `knowledge_graph.json` | `knowledge_graph` |
| `eval_results.schema.json` | `eval_results.json` | `eval_results` |

Shared definitions: `schemas/_common.definitions.json` (envelope §24.7, provenance §10, entity §24.6, evidence row §24.8).

**Schema version:** `v0.5` (const on all artifacts).

## Contract summary

- **Envelope (§24.7):** `artifact_type`, `case_id`, `schema_version`, `generated_at`, `provenance`, `data`.
- **Provenance (§10):** `generated_by`, `generated_at`, `input_artifacts`, optional model fields (null when not AI-generated).
- **Source records (§24.5):** base fields on literature / trial / biology records; namespaced IDs (`pubmed:`, `clinicaltrials:`, etc.).
- **Entities (§24.6):** `normalized_entities.data.entities[]`.
- **Evidence (§24.8):** `evidence_table.data.rows[]` with `claim_type` and `support_status` enums.
- **Eval (§24.11):** `eval_results.data.evaluations[]` plus aggregate `metrics`.

## Type mirrors

| Language | Path | Notes |
|----------|------|-------|
| Python | `pipeline/types.py` | Pydantic v2; `ARTIFACT_MODEL_BY_TYPE` registry |
| TypeScript | `web/types/artifacts.ts` | Interfaces for frontend components |

## Consumers (do not break without schema bump)

| Consumer | Usage |
|----------|--------|
| `pipeline/artifact_writer.py` | Validate before write / copy-to-web |
| `pipeline/run_workflow.py` | Orchestrates artifact generation |
| `evals/run_evals.py` | Reads case dir; `schema_validation` evaluator |
| `web/components/*` | Props: `DiligenceReport`, `RiskMap`, `EvidenceRow[]`, etc. |
| `web/public/data/cases/{case_id}/` | Static JSON loaded by dashboard |
| `tests/fixtures/cases/*` | Fixture packets must validate |

## Test commands

```bash
# Install (from repo root)
python -m pip install -e ".[dev]"

# Schema + Pydantic validation
pytest tests/schemas/test_schema_validation.py -v

# All tests (when present)
pytest tests/ -v
```

## Validation in code

```python
from pathlib import Path
import json
from jsonschema import Draft202012Validator
from pipeline.types import EvidenceTableArtifact

schema = json.loads(Path("schemas/evidence_table.schema.json").read_text())
registry = json.loads(Path("schemas/_common.definitions.json").read_text())
Draft202012Validator(schema, registry=registry).validate(payload)
artifact = EvidenceTableArtifact.model_validate(payload)
```

## Out of scope for schema-agent

Per workstream boundaries: `connectors/`, `pipeline/run_workflow.py`, `web/components/`, `web/app/`.

## Next agents

1. **Fixture-agent:** populate `tests/fixtures/cases/{case_id}/` using minimal examples in `tests/schemas/test_schema_validation.py`.
2. **Pipeline-agent:** `artifact_writer` should load schemas from `schemas/` and reject invalid JSON before `copy-to-web`.
3. **Frontend-agent:** import types from `web/types/artifacts.ts`; use `loadCaseArtifact<T>()`.
