# Codex Development Plan

## Purpose

This repository should be developed through small, bounded Codex tasks that move the project from scaffold to executable vertical slice, then from vertical slice to broader feature coverage.

The goal is not to maximize autonomous activity. The goal is to create reliable, reviewable progress with minimal repo churn.

## Product target

`tdw_ai` is the Translational Diligence Workbench: a static-first scientific AI workflow system that converts biomedical source evidence into auditable diligence artifacts and a polished static dashboard.

The MVP must demonstrate applied AI workflow engineering:

- fixture-backed source retrieval
- schema-valid JSON artifacts
- evidence-grounded synthesis stubs
- deterministic eval checks
- static frontend rendering
- CI that runs without API keys

## Development doctrine

1. Fixture mode first.
2. One executable vertical slice before broadening.
3. No paid API calls in CI.
4. No live biomedical connectors until fixture connectors pass.
5. Small PRs only.
6. Every generated claim must be traceable to evidence or marked unsupported.
7. Frontend reads static artifacts only in MVP.
8. Codex must not invent scope beyond the issue it is assigned.

## Golden path

The first working path is:

```bash
python -m pipeline.run_workflow --config configs/cases/sting_pdac.yaml --mode fixture
python -m evals.run_evals --case generated/cases/sting_pdac
python -m pipeline.artifact_writer --copy-to-web generated/cases/sting_pdac
npm run build --prefix web
```

The golden path is complete when it succeeds on a clean clone without `.env`, API keys, or network calls.

## Branching model

- `main`: stable, reviewed state.
- `codex/dev-readiness`: setup branch for Codex task scaffolding.
- `codex/<short-task-name>`: one branch per Codex task.

## PR rules

Each PR must include:

- linked issue
- files changed
- test commands run
- evidence of fixture-mode behavior
- explicit note if tests were not run
- no secrets
- no live paid calls

## Review gates

A PR is not merge-ready unless at least one of these is true:

- it makes the fixture pipeline more executable
- it adds or tightens tests
- it improves schema validity
- it makes frontend rendering more robust
- it improves task/readme clarity for future Codex work

## Deferred until golden path works

- live PubMed/ClinicalTrials/OpenTargets/ChEMBL calls
- OpenAI synthesis calls
- auth
- SaaS packaging
- broad case expansion
- Rhode Island atlas overlays
- investor CRM features
- runtime chat

## Codex operating instructions

When Codex is assigned an issue:

1. Read only the issue, `MASTER_PRD.md`, this file, and directly relevant task files.
2. Modify only files listed in the issue unless fixing a directly blocking import/test problem.
3. Prefer explicit, boring code over clever abstractions.
4. Add or update tests for changed behavior.
5. Preserve fixture determinism.
6. Stop once acceptance criteria are met.
7. Do not opportunistically refactor unrelated modules.

## First development phase

Phase 1 is repo readiness for autonomous development:

- create Codex task format
- create issue and PR templates
- decompose MVP into ordered issues
- establish the STING/PDAC vertical slice as the first build target

Phase 2 is implementation:

- schema validation
- fixture connector envelope
- pipeline artifact writer
- eval stubs
- static web copy
- frontend build

Phase 3 is controlled expansion:

- add remaining fixture cases
- add one live connector at a time
- add OpenAI build-time synthesis after eval safeguards exist
