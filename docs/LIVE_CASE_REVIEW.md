# Live Case Review — STING / PDAC (`sting_pdac`)

**Status:** Template — complete after first live or live+mock synthesis run.

## Run metadata

| Field | Value |
|-------|--------|
| Case ID | `sting_pdac` |
| Mode | `live` (MockProvider or OpenAI) |
| Date | _YYYY-MM-DD_ |
| Reviewer | _Name_ |

## Data sources

- [ ] PubMed live fetch attempted
- [ ] Other connectors: fixture fallback / errors documented

## Scientific plausibility

| Area | Plausible? | Notes |
|------|------------|-------|
| Mechanism claims | | |
| Trial references | | |
| Risk framing | | |
| Confidence scores | | |

## Eval gates

- [ ] `python -m evals.run_evals --case generated/cases/sting_pdac` — overall pass or documented warnings

## Known limitations

- MOCK/SYNTHETIC fixtures used when `OPENAI_API_KEY` unset (MockProvider).
- Not for clinical decision-making.

## Sign-off

Reviewer sign-off: ______________________
