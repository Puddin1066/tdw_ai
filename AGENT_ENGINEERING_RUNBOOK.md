# Agentic Engineering Runbook

This file defines how Codex, Cursor agents, or other coding agents should operate on this repository without requiring repeated human prompt turns.

The purpose is to convert the Translational Diligence Workbench from a prompt-driven project into an issue-driven engineering workflow.

## 1. Operating mode

Agents must work from repository state, GitHub issues, task files, and tests.

Humans should not need to restate the architecture in every session. The agent must discover its task by reading:

1. `MASTER_PRD.md`
2. `AGENT_ORCHESTRATION.md`
3. The assigned GitHub issue
4. The matching `tasks/NN_*_agent.md` file
5. Relevant upstream `AGENT_HANDOFF.md` files
6. Existing tests and fixtures

If instructions conflict, precedence is:

1. GitHub issue acceptance criteria
2. `MASTER_PRD.md`
3. `AGENT_ORCHESTRATION.md`
4. Assigned task file
5. Existing implementation conventions
6. Agent inference

Agents must not invent scope beyond these sources.

## 2. Autonomous issue pickup

An agent may select the next task using this order:

1. Open issues labeled `agent-ready`
2. Lowest-numbered milestone issue first
3. Schema and fixture issues before frontend, pipeline, synthesis, evals, or live connectors
4. Integration issues only after upstream handoffs exist

Recommended order:

1. `milestone-1` / schema contracts
2. fixture case packets
3. static frontend against fixtures
4. pipeline fixture orchestration
5. connector fixture mode
6. synthesis stubs
7. evals
8. integration pass
9. optional live mode

## 3. Branch policy

For each issue, create a branch:

```text
agent/<issue-number>-<short-slug>
```

Examples:

```text
agent/1-schema-contracts
agent/2-fixture-packets
agent/3-static-frontend
```

Never commit directly to `main` unless the repository owner explicitly requests a direct commit.

## 4. Work ownership boundaries

Agents must follow file ownership in `AGENT_ORCHESTRATION.md`.

Read access is global. Write access is limited to the assigned workstream unless the issue explicitly grants cross-module edits.

High-risk shared files require special care:

- `MASTER_PRD.md`
- `README.md`
- `pipeline/types.py`
- `web/types/artifacts.ts`
- `schemas/*.schema.json`
- `.github/workflows/*`

When uncertain, update the relevant `AGENT_HANDOFF.md` instead of changing another agent's owned file.

## 5. Required development loop

For every issue, the agent must:

1. Read the issue and source-of-truth docs.
2. Identify owned files.
3. Inspect current repo state before editing.
4. Implement the smallest complete slice that satisfies acceptance criteria.
5. Add or update tests.
6. Run relevant local commands when available.
7. Update the owned `AGENT_HANDOFF.md`.
8. Commit changes to an issue branch.
9. Open a pull request into `main`.
10. Include exact commands run and results in the PR body.

## 6. Testing rules

Default mode is fixture-only.

Agents must not call paid APIs or live biomedical APIs unless the issue is explicitly labeled `live-mode-approved`.

Minimum expected checks by workstream:

| Workstream | Minimum checks |
|---|---|
| Schemas | `python -m pytest tests/schemas -q` |
| Fixtures | schema validation over all fixture artifacts |
| Frontend | `npm run build --prefix web` |
| Pipeline | `python -m pytest tests/pipeline -q` and fixture run command |
| Connectors | `python -m pytest tests/connectors -q` |
| Synthesis | `python -m pytest tests/synthesis -q` |
| Evals | `python -m pytest tests/evals -q` |
| Integration | full fixture chain for `sting_pdac` |

If a command cannot run because the repo is not yet ready, document the exact blocker in the PR body and `AGENT_HANDOFF.md`.

## 7. PR body template

Every agent PR must include:

```md
## Summary
- 

## Issue
Closes #<issue-number>

## Files changed
- 

## Interfaces produced
- 

## Commands run
```bash
# command
```
Result: pass/fail/not run + reason

## Handoff notes
- 

## Scope control
- No paid APIs used
- No secrets committed
- No scope added outside PRD
```

## 8. Stop conditions

Agents must stop and open a PR when:

- The issue acceptance criteria are met.
- A blocker requires human credentials or secret values.
- A required upstream contract is missing.
- A test failure requires changing another agent's owned interface.
- The agent would need to expand the PRD to proceed.

Stopping with a clear PR and handoff is preferred over improvising.

## 9. Live mode rules

Live mode is opt-in only.

Agents may not call:

- OpenAI API
- PubMed live retrieval
- ClinicalTrials.gov live retrieval
- Open Targets live retrieval
- ChEMBL live retrieval
- BioThings live retrieval
- Any paid, metered, or credentialed API

unless the GitHub issue explicitly says live mode is approved.

Fixture mode must remain functional after live mode is added.

## 10. Definition of agentic engineering done

This repository is considered agentic-engineering ready when:

- GitHub issues define executable slices.
- Each slice maps to a task file.
- Each slice has acceptance criteria.
- Agents can pick up issues without new architecture prompts.
- Every PR updates an `AGENT_HANDOFF.md`.
- CI or documented local commands verify fixture-mode correctness.
- The full `sting_pdac` fixture case can run end-to-end without API keys.

The goal is not to maximize automation theater. The goal is to let agents produce small, reviewable, testable engineering increments with minimal human prompting.
