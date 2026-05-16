# Agent Orchestration

This document defines how multiple Cursor agents build the Translational Diligence Workbench in parallel without merge chaos.

**Canonical spec:** `MASTER_PRD.md` (v0.8.1) — start at **Development navigation** (top of PRD). **Historical:** `guide_v07.md` (frozen). Agents must not invent product scope outside the PRD.

## Core rule

Agents coordinate through **schemas, fixtures, file ownership, CLI contracts, and acceptance tests** — not private assumptions. See PRD §22.1.

## Workstreams and owners

| Workstream | Agent ID | Owns | Task file |
|------------|----------|------|-----------|
| Scaffold | scaffold-agent | README, configs, launch kit, CI stub | `tasks/00_repo_scaffold.md` |
| Schemas | schema-agent | `schemas/`, `pipeline/types.py`, `web/types/artifacts.ts` | `tasks/01_schema_agent.md` |
| Fixtures | fixture-agent | `tests/fixtures/cases/` | `tasks/02_fixture_agent.md` |
| Frontend | frontend-agent | `web/` | `tasks/03_frontend_agent.md` |
| Connectors | connectors-agent | `connectors/`, `tests/connectors/` | `tasks/04_connector_agent.md` |
| Pipeline | backend-pipeline-agent | `pipeline/`, `tests/pipeline/` | `tasks/05_pipeline_agent.md` |
| Synthesis | synthesis-agent | `skills/`, synthesis pipeline modules | `tasks/06_synthesis_agent.md` |
| Evals | evals-agent | `evals/`, `tests/evals/` | `tasks/07_evals_agent.md` |
| Integration | integration-agent | glue, CI, README updates, cross-module paths | `tasks/08_integration_agent.md` |
| Synthesis (Phase 2) | synthesis-agent | `pipeline/llm_provider.py`, `skills/` | `tasks/09_synthesis_agent.md` |
| Live connector (Phase 2) | connectors-agent | one live source for `sting_pdac` | `tasks/10_live_connector_agent.md` |
| Integration (Phase 2) | integration-agent | schema validation, strict CI, live review | `tasks/11_integration_v08_agent.md` |

## Build order (recommended)

**Tier A (complete):** PRD §0B.

**Tier B (Phase 2):** PRD §5A:

1. `pipeline/llm_provider.py` + `skills/` (in progress)
2. Wire `generate_*` to providers in live mode
3. One live connector (PubMed or ClinicalTrials.gov)
4. Live `sting_pdac` E2E + `docs/LIVE_CASE_REVIEW.md`
5. Strict CI + schema validation in `artifact_writer`

**Vertical slice first:** `sting_pdac` config → `generated/cases/sting_pdac/*` → `web/public/data/cases/sting_pdac/*` → rendered dashboard. No other feature outranks this until it works (PRD §25.2).

## Parallel development pattern

1. **schema-agent** defines artifact contracts.
2. **fixture-agent** creates representative fixture artifacts.
3. **frontend-agent** builds against fixtures only.
4. **connectors-agent** builds mocked + live adapters.
5. **backend-pipeline-agent** orchestrates via `ConnectorResult`, not source internals.
6. **synthesis-agent** runs against normalized fixtures.
7. **evals-agent** audits generated artifacts.
8. **integration-agent** runs full chain and resolves contract mismatches.

## Handoff protocol

Each owned directory maintains `AGENT_HANDOFF.md` with:

- Files modified
- Interfaces consumed / produced
- Test commands
- Assumptions
- Blockers
- Downstream consumers

Required handoff locations: `schemas/`, `connectors/`, `pipeline/`, `skills/`, `evals/`, `web/`.

## Integration gates

| Module | Gate |
|--------|------|
| Schemas | All fixture artifacts validate |
| Connectors | All return `ConnectorResult` in fixture mode |
| Pipeline | Fixture case produces all 12 artifacts |
| Synthesis | Report, evidence table, risk map validate |
| Evals | Hallucinated NCT/PMID and unsupported claims detected |
| Frontend | Static build from `web/public/data/cases/` only |
| E2E | `sting_pdac` fixture chain with no API keys |

## Merge conflict policy

High-risk shared files — modify only by designated owner or **integration-agent** (PRD §22.7):

- `pipeline/types.py`
- `web/types/artifacts.ts`
- `schemas/*.schema.json`
- `README.md`
- `MASTER_PRD.md`

Non-owners propose changes via handoff notes or PRD revision.

## Launching an agent

1. Read `MASTER_PRD.md` (relevant sections only if token-limited — see PRD §25.11).
2. Read assigned `tasks/NN_*.md`.
3. Read `AGENT_HANDOFF.md` in owned and upstream directories.
4. Use prompt from `LAUNCH_PROMPT.md`.
5. Update `AGENT_HANDOFF.md` on completion.

## Fixture vs live

- **Default for all agents:** fixture mode only; no paid API calls.
- **Live mode:** explicit user request; requires `.env`.
- **CI:** fixture only; never calls paid APIs (PRD §18).

## Definition of efficient MVP done

Per PRD §25.12: clean clone installs; fixture mode without keys; one full case E2E; four case cards; 12 artifacts for primary fixture; schema validation passes; eval stubs run; frontend build succeeds; README documents single-command fixture demo; launch kit matches workstreams.
