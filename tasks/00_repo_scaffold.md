# 00 Repo Scaffold Agent

**Agent:** scaffold-agent

**Objective:** Create repository foundation, case configs, launch kit, CI stub, and placeholder handoffs so parallel agents can start without merge conflicts.

## May modify

- `README.md`
- `pyproject.toml`
- `package.json`
- `web/package.json` (stub only)
- `.env.example`
- `.gitignore`
- `configs/cases/**`
- `AGENT_ORCHESTRATION.md`
- `LAUNCH_PROMPT.md`
- `tasks/**`
- `.github/workflows/ci.yml`
- `*/AGENT_HANDOFF.md` (placeholder status only)

## Must not modify

- `schemas/*.schema.json` (content)
- `connectors/*.py` (implementations)
- `pipeline/*.py` (implementations)
- `skills/**` (content)
- `evals/*.py` (implementations)
- `web/app/**`, `web/components/**` (implementations)
- `tests/fixtures/cases/**` (fixture JSON data)
- `MASTER_PRD.md`

## Input contracts consumed

- PRD §7 Repository Layout
- PRD §17 CLI Requirements
- PRD §19 Repo Foundation Requirements
- PRD §24.2 Case Config Contract
- PRD §25.8–25.10 Launch Kit

## Output contracts produced

- Valid case YAML configs for four MVP cases
- Python project metadata with declared dependencies
- Node workspace root scripts
- Launch kit and task file index
- CI workflow stub (allow failures until modules exist)

## Implementation steps

1. Create `pyproject.toml` with Python 3.11+, pydantic v2, pytest, pyyaml, jsonschema, httpx.
2. Create root `package.json` with workspace scripts for web and fixture shortcuts.
3. Create `.env.example`, `.gitignore` (Python, Node, `generated/`, `web/public/data/cases/`).
4. Add four case configs under `configs/cases/` per §24.2 template.
5. Write `README.md` with setup, fixture demo commands, project overview.
6. Write `AGENT_ORCHESTRATION.md` and `LAUNCH_PROMPT.md`.
7. Create `tasks/00`–`08` task files with ownership and acceptance criteria.
8. Add `.github/workflows/ci.yml` stub with `continue-on-error` where needed.
9. Place `AGENT_HANDOFF.md` with `status: pending` in `schemas/`, `connectors/`, `pipeline/`, `skills/`, `evals/`, `web/`.

## Tests to run

```bash
# Verify configs parse
python -c "import yaml; [yaml.safe_load(open(f)) for f in ['configs/cases/sting_pdac.yaml','configs/cases/parp_breast.yaml','configs/cases/tau_alzheimers.yaml','configs/cases/iaip_sepsis.yaml']]"

# Verify pyproject loads
pip install -e ".[dev]"
python -m pytest --collect-only 2>/dev/null || true
```

## Acceptance criteria

- [ ] All launch kit files from PRD §25.8 exist
- [ ] Four case YAML files validate against §24.2 rules (`case_id` snake_case, `workflow: translational_diligence`, explicit source booleans, positive limits)
- [ ] README documents setup and fixture command chain from §22.6
- [ ] `.gitignore` excludes `generated/` and copied public case data
- [ ] CI workflow file exists; steps may fail until downstream agents complete
- [ ] No schema, connector, pipeline, fixture JSON, or frontend component implementations added

## Handoff notes required

Update each `AGENT_HANDOFF.md` placeholder with:

- Scaffold completion date
- Pointer to relevant `tasks/NN_*.md` for next agent
- Blocker: downstream modules not yet implemented
