# 11 Integration Agent (Phase 2)

**Agent:** integration-agent

**Objective:** Tier B integration — live mock E2E, schema validation on publish, strict CI, `LIVE_CASE_REVIEW.md`, README live path.

## May modify

- `README.md`
- `.github/workflows/ci.yml`
- `docs/LIVE_CASE_REVIEW.md`
- `pipeline/artifact_writer.py`
- `MASTER_PRD.md` Development navigation (status rows)

## Verify

```bash
pytest tests/ -q -m "not live"
npm run build --prefix web
python -m pipeline.run_workflow --config configs/cases/sting_pdac.yaml --mode live
python -m evals.run_evals --case generated/cases/sting_pdac
python -m pipeline.artifact_writer generated/cases/sting_pdac --copy-to-web
```

## Acceptance

- §20A Tier B checklist items addressed
- CI fails on test/build errors (no continue-on-error on core steps)
