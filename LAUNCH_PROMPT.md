# Launch Prompts

Copy the appropriate prompt into a new Cursor agent session. All agents must obey `MASTER_PRD.md` as the source of truth. **Do not call paid APIs unless live mode is explicitly requested.**

---

## Master build prompt

```
You are building the Translational Diligence Workbench. Read MASTER_PRD.md completely. Implement the repo in the required build order. First create the scaffold, schemas, fixture data, static frontend, pipeline stubs, eval stubs, and integration tests. Use fixture mode only. Do not call paid APIs. Do not add features outside the PRD. Every module must include an AGENT_HANDOFF.md. Stop when the STING/PDAC fixture case renders in the frontend and the documented test commands pass.
```

**Assigned task:** Read `AGENT_ORCHESTRATION.md` and your `tasks/NN_*_agent.md` file before writing code.

---

## Fixture-only build prompt

```
You are an agent on the Translational Diligence Workbench. Read MASTER_PRD.md sections relevant to your task file in tasks/. Read AGENT_HANDOFF.md in upstream directories you depend on. Implement only your owned files per the task spec. Use fixture mode exclusively — no OpenAI, PubMed, ClinicalTrials.gov, Open Targets, ChEMBL, or BioThings live calls. All connector and synthesis work must pass with tests/fixtures/ data. Update AGENT_HANDOFF.md when done with: files changed, interfaces, test commands, blockers. Do not modify files outside your ownership list.
```

---

## Live-integration build prompt

```
You are an agent enabling live mode for the Translational Diligence Workbench. Read MASTER_PRD.md connector and synthesis contracts. Read .env.example. Live mode requires explicit user approval and a populated .env — never commit secrets. Implement or extend live fetch paths only for connectors/sources already working in fixture mode. Preserve raw API responses in ConnectorResult. Do not break fixture tests. Run live commands only when the user confirms API keys are set. Document required env vars in AGENT_HANDOFF.md.
```

---

## Integration-agent prompt

```
You are the integration-agent for the Translational Diligence Workbench. Read MASTER_PRD.md sections 22, 25.2, and 25.12. Read all AGENT_HANDOFF.md files. Your job is holistic assembly: run the full fixture command chain for sting_pdac, then parp_breast, tau_alzheimers, and iaip_sepsis without code changes between cases. Fix cross-module import paths, CI, package scripts, and README only — do not silently change schema semantics, prompt behavior, connector normalization, or eval scoring rules (those require PRD revision). Ensure: python -m pipeline.run_workflow --config configs/cases/sting_pdac.yaml --mode fixture && python -m evals.run_evals --case generated/cases/sting_pdac && python -m pipeline.artifact_writer --copy-to-web generated/cases/sting_pdac && npm run build --prefix web all succeed without API keys. Update README with verified commands.
```

---

## Per-agent quick reference

| Agent | Task file |
|-------|-----------|
| scaffold-agent | `tasks/00_repo_scaffold.md` |
| schema-agent | `tasks/01_schema_agent.md` |
| fixture-agent | `tasks/02_fixture_agent.md` |
| frontend-agent | `tasks/03_frontend_agent.md` |
| connectors-agent | `tasks/04_connector_agent.md` |
| backend-pipeline-agent | `tasks/05_pipeline_agent.md` |
| synthesis-agent | `tasks/06_synthesis_agent.md` |
| evals-agent | `tasks/07_evals_agent.md` |
| integration-agent | `tasks/08_integration_agent.md` |
