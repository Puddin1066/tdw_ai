# 08 Integration Agent

**Agent:** integration-agent

**Objective:** Holistic assembly — verify full fixture command chain for all four cases, fix cross-module glue, harden CI, and update README with verified commands.

## May modify

- `README.md`
- `package.json`, `web/package.json` scripts
- `.github/workflows/ci.yml` (remove `continue-on-error` when green)
- Cross-module import paths
- Fixture copy scripts
- Non-domain glue code in `pipeline/`, `tests/` (paths only — not semantics)

## Must not modify (without PRD revision)

- Schema semantics (`schemas/*.schema.json`)
- Prompt behavior (`skills/**/prompts/**`)
- Connector normalization logic
- Evaluation scoring rules

## Input contracts consumed

- PRD §22.6 Holistic Assembly Requirement
- PRD §25.12 Definition of Efficient MVP Done
- All `AGENT_HANDOFF.md` files
- Integration gates from PRD §22.4

## Output contracts produced

- Green CI on fixture-only path
- Verified README command block
- Resolved import/path issues across modules
- Integration test (optional) under `tests/integration/`

## Implementation steps

1. Read all handoff files; triage blockers.
2. Run STING/PDAC chain:
   ```bash
   python -m pipeline.run_workflow --config configs/cases/sting_pdac.yaml --mode fixture
   python -m evals.run_evals --case generated/cases/sting_pdac
   python -m pipeline.artifact_writer --copy-to-web generated/cases/sting_pdac
   npm run build --prefix web
   ```
3. Repeat pipeline for `parp_breast`, `tau_alzheimers`, `iaip_sepsis` without code changes.
4. Fix broken imports, missing `__init__.py`, package entry points.
5. Tighten CI: remove `continue-on-error` on passing steps.
6. Confirm clean clone + `pip install -e ".[dev]"` + `npm install` + fixture chain.
7. Update README and orchestration docs with verified status.

## Tests to run

```bash
# Full E2E fixture chain (all four cases)
python -m pipeline.run_workflow --config configs/cases/sting_pdac.yaml --mode fixture
python -m evals.run_evals --case generated/cases/sting_pdac
python -m pipeline.artifact_writer --copy-to-web generated/cases/sting_pdac
npm run build --prefix web

python -m pipeline.run_workflow --config configs/cases/parp_breast.yaml --mode fixture
python -m pipeline.run_workflow --config configs/cases/tau_alzheimers.yaml --mode fixture
python -m pipeline.run_workflow --config configs/cases/iaip_sepsis.yaml --mode fixture

python -m pytest -q
```

## Acceptance criteria

- [ ] Clean clone installs and runs fixture chain without API keys
- [ ] `sting_pdac` renders in frontend with all seven tabs
- [ ] Four case cards visible on library page
- [ ] All 12 artifacts exist for primary fixture case
- [ ] Schema validation passes on generated output
- [ ] Eval suite runs deterministically
- [ ] CI passes without paid API calls
- [ ] README single-command fixture demo is accurate

## Handoff notes required

- Final integration status table
- Remaining known gaps for Phase 2
- Any PRD revision requests discovered during assembly
- Commands verified on which OS/Python/Node versions
