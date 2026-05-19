# Translational Diligence Workbench

Static-first, AI-assisted translational diligence for arbitrary target–indication pairs. The workbench converts heterogeneous biomedical sources into auditable artifacts: reports, evidence tables, risk maps, trial landscapes, knowledge graphs, source manifests, and evaluation outputs.

**This is not a chatbot.** It is structured scientific workflow infrastructure with contract-first, multi-agent development (see `MASTER_PRD.md` v0.8.3).

## Repository status

| Layer | Status |
|-------|--------|
| Scaffold & configs | ✅ |
| JSON schemas & types | ✅ |
| Fixture case packets (4 cases, MOCK/SYNTHETIC) | ✅ |
| Connectors (fixture mode) | ✅ |
| Connectors (live) | ✅ PubMed live (`httpx`); other sources fixture fallback |
| Pipeline (fixture orchestration) | ✅ |
| Synthesis / skills / `LLMProvider` | ✅ mock live path; OpenAI optional via `.env` |
| Evals (deterministic) | ✅ |
| Frontend (static Next.js) | ✅ |
| Portfolio live case + review | ✅ `docs/LIVE_CASE_REVIEW.md` (2026-05-16) |

**Tier A (fixture MVP)** and **Tier B (portfolio MVP)** are complete per `MASTER_PRD.md` §25.12 and §20A.

## Prerequisites

- **Python 3.11+**
- **Node.js 20+**
- Optional: `.env` for live mode only (fixture mode needs no keys)

## Setup

```bash
cd tdw_ai   # or your clone path

python3.11 -m venv .venv
source .venv/bin/activate
pip install -e ".[dev]"

npm install
cd web && npm install && cd ..

cp .env.example .env   # only for live mode
```

## Demo cases

| Case ID | Display name |
|---------|----------------|
| `sting_pdac` | STING / Pancreatic Cancer |
| `parp_breast` | PARP / Breast Cancer |
| `tau_alzheimers` | Tau / Alzheimer's Disease |
| `iaip_sepsis` | IAIP / Sepsis |

Configs: `configs/cases/*.yaml`

## Fixture demo (no API keys)

```bash
source .venv/bin/activate

# Primary vertical slice
python -m pipeline.run_workflow --config configs/cases/sting_pdac.yaml --mode fixture
python -m evals.run_evals --case generated/cases/sting_pdac
python -m pipeline.artifact_writer generated/cases/sting_pdac --copy-to-web

# All four cases
python -m pipeline.run_workflow --config configs/cases/parp_breast.yaml --mode fixture
python -m pipeline.run_workflow --config configs/cases/tau_alzheimers.yaml --mode fixture
python -m pipeline.run_workflow --config configs/cases/iaip_sepsis.yaml --mode fixture

# Frontend
npm run dev --prefix web
# open http://localhost:3000
```

Shortcut: `npm run fixture:sting` (from repo root, if configured).

## Live mode (Phase 2)

**Without API keys:** uses `MockProvider` + `tests/fixtures/synthesis/sting_pdac/` (not case-fixture copy) and live PubMed when network is available.

**With OpenAI:** `pip install -e ".[live]"` and set `OPENAI_API_KEY` in `.env`.

Runtime note: `pipeline.run_workflow` auto-loads repo `.env` (no manual `export` required) unless `TDW_SKIP_REPO_ENV=1`.

Optional connector backend flags (safe rollout):

- `CONNECTOR_BACKEND=biomcp` (global override)
- `OPENTARGETS_BACKEND=biomcp`
- `CHEMBL_BACKEND=biomcp`
- `BIOTHINGS_BACKEND=biomcp`

If BioMCP is unavailable or returns invalid payloads, connectors fall back to native live logic and add warnings.

```bash
python -m pipeline.run_workflow --config configs/cases/sting_pdac.yaml --mode live
python -m evals.run_evals --case generated/cases/sting_pdac
python -m pipeline.artifact_writer generated/cases/sting_pdac --copy-to-web
# verify metadata run block reports synthesis_provider: openai when key is active
```

Complete `docs/LIVE_CASE_REVIEW.md` after manual scientific review.

## Validation

```bash
pytest tests/ -q
npm run build --prefix web
```

## Multi-agent development

- **Source of truth:** `MASTER_PRD.md` (v0.8.3) — [Development navigation](MASTER_PRD.md#development-navigation)
- **Historical v0.7:** `guide_v07.md` (frozen)
- **Orchestration:** `AGENT_ORCHESTRATION.md`
- **Launch prompts:** `LAUNCH_PROMPT.md`
- **Tasks:** `tasks/00`–`11`
- **Handoffs:** `*/AGENT_HANDOFF.md`

## License

Proprietary — see repository owner.
