# Translational Diligence Workbench

Static-first, AI-assisted translational diligence for arbitrary target–indication pairs. The workbench converts heterogeneous biomedical sources into auditable artifacts: reports, evidence tables, risk maps, trial landscapes, knowledge graphs, source manifests, and evaluation outputs.

**This is not a chatbot.** It is structured scientific workflow infrastructure with contract-first, multi-agent development (see `MASTER_PRD.md`).

## Repository status

| Layer | Status |
|-------|--------|
| Scaffold & configs | ✅ This repo |
| JSON schemas & types | 🔲 `tasks/01_schema_agent.md` |
| Fixture case packets | 🔲 `tasks/02_fixture_agent.md` |
| Connectors | 🔲 `tasks/04_connector_agent.md` |
| Pipeline | 🔲 `tasks/05_pipeline_agent.md` |
| Synthesis | 🔲 `tasks/06_synthesis_agent.md` |
| Evals | 🔲 `tasks/07_evals_agent.md` |
| Frontend | 🔲 `tasks/03_frontend_agent.md` |
| Integration | 🔲 `tasks/08_integration_agent.md` |

## Prerequisites

- **Python 3.11+**
- **Node.js 20+** (for frontend workspace)
- Optional: `.env` with API keys for **live mode only** (fixture mode requires no keys)

## Setup

```bash
# Clone and enter repo
cd translational-diligence-workbench   # or your clone path

# Python environment
python3.11 -m venv .venv
source .venv/bin/activate   # Windows: .venv\Scripts\activate
pip install -e ".[dev]"

# Node workspace (frontend stub until frontend-agent completes)
npm install

# Optional: copy environment template for live mode
cp .env.example .env
```

## Demo cases

Four MVP target–indication configs live under `configs/cases/`:

| Case ID | Display name |
|---------|----------------|
| `sting_pdac` | STING / Pancreatic Cancer |
| `parp_breast` | PARP / Breast Cancer |
| `tau_alzheimers` | Tau / Alzheimer's Disease |
| `iaip_sepsis` | IAIP / Sepsis |

## Fixture demo commands

Fixture mode must run **without external API keys**. These commands are the integration acceptance chain (see PRD §22.6):

```bash
# Primary vertical slice (STING/PDAC)
python -m pipeline.run_workflow --config configs/cases/sting_pdac.yaml --mode fixture
python -m evals.run_evals --case generated/cases/sting_pdac
python -m pipeline.artifact_writer --copy-to-web generated/cases/sting_pdac

# Additional fixture cases (same architecture, no code changes)
python -m pipeline.run_workflow --config configs/cases/parp_breast.yaml --mode fixture
python -m pipeline.run_workflow --config configs/cases/tau_alzheimers.yaml --mode fixture
python -m pipeline.run_workflow --config configs/cases/iaip_sepsis.yaml --mode fixture

# Frontend (static files only at runtime)
npm run dev --prefix web
npm run build --prefix web
```

> **Note:** Pipeline, evals, and frontend modules are scaffolded but not yet implemented. Commands above will succeed once the corresponding agents complete their tasks.

### Shortcut scripts (root `package.json`)

```bash
npm run fixture:sting    # STING/PDAC fixture pipeline only
npm run fixture:all      # All four fixture cases (when pipeline exists)
npm run test:python      # Full Python test suite
```

## Live mode (optional)

Live mode may require `.env` (see `.env.example`). Do not use live mode in CI.

```bash
python -m pipeline.run_workflow --config configs/cases/sting_pdac.yaml --mode live
```

## Project layout

```
configs/cases/     # Case YAML configs (target, indication, sources, limits)
connectors/        # Public data source adapters
pipeline/          # Orchestration, normalization, artifact generation
skills/            # Translational diligence synthesis prompts
schemas/           # Canonical JSON Schema artifacts
evals/             # Citation fidelity, hallucination, coverage audits
generated/cases/   # Pipeline output (gitignored)
web/               # Next.js static frontend
tests/             # Unit, schema, fixture, and integration tests
tasks/             # Per-agent task specs for parallel development
```

## Multi-agent development

- **Source of truth:** `MASTER_PRD.md`
- **Orchestration:** `AGENT_ORCHESTRATION.md`
- **Launch prompts:** `LAUNCH_PROMPT.md`
- **Per-agent tasks:** `tasks/00_repo_scaffold.md` … `tasks/08_integration_agent.md`
- **Handoff status:** `AGENT_HANDOFF.md` in each owned directory

## Validation

```bash
# Schema validation (when implemented)
python -m pytest tests/schemas -q

# Full test suite
python -m pytest -q

# CI mirrors these checks — see .github/workflows/ci.yml
```

## License

Proprietary — see repository owner.
