# 03 Frontend Agent

**Agent:** frontend-agent

**Objective:** Build static Next.js application that renders four demo cases from `web/public/data/cases/` only — no runtime API or OpenAI dependency.

## May modify

- `web/**` (except generated `web/public/data/cases/` content — populated by pipeline)
- `tests/frontend/**` (if created)

## Must not modify

- `pipeline/**`
- `connectors/**`
- `evals/**`
- `schemas/*.schema.json` (request schema-agent for changes)
- `web/types/artifacts.ts` only if schema-agent approves or co-owns

## Input contracts consumed

- PRD §11 Frontend UX Contract
- PRD §12 Frontend Component API Requirements
- PRD §24.12 Frontend Data Loading Contract
- `web/types/artifacts.ts` from schema-agent
- Fixture data copied to `web/public/data/cases/{case_id}/`

## Output contracts produced

- Next.js app with Tailwind + shadcn/ui
- Components: `CaseCard`, `ExecutiveSnapshot`, `EvidenceTable`, `TrialsTable`, `RiskMap`, `KnowledgeGraph`, `SourceManifest`, `EvalPanel`
- Routes: case library (`/`), case dashboard (`/cases/[caseId]`) with seven tabs
- Polished scientific cockpit UX

## Implementation steps

1. Initialize Next.js in `web/` with TypeScript, Tailwind, shadcn/ui.
2. Replace stub `web/package.json` scripts with real `dev` and `build`.
3. Implement static data loader reading `public/data/cases/{caseId}/*.json`.
4. Build case library page with four `CaseCard` components.
5. Build case dashboard with seven tabs and graceful empty states.
6. Add Recharts for charts; Cytoscape.js or React Flow for knowledge graph.
7. Update `web/AGENT_HANDOFF.md` and root README frontend section if integration-agent delegates.

## Tests to run

```bash
npm install
npm run build --prefix web
npm run dev --prefix web   # manual smoke test with fixture data
```

## Acceptance criteria

- [ ] Frontend works using only static files from `web/public/data/cases/`
- [ ] No runtime dependency on OpenAI or biomedical APIs
- [ ] Four demo case cards render from fixture data
- [ ] Case dashboard renders all seven tabs
- [ ] Missing optional fields show empty states, not crashes
- [ ] `npm run build --prefix web` succeeds in CI
- [ ] `web/AGENT_HANDOFF.md` complete

## Handoff notes required

- Public data path conventions
- Tab-to-artifact mapping
- Any UI assumptions needing schema fields
- Blockers if fixture data not yet copied to `web/public/`
