# Translational Diligence Skill

Build-time synthesis skill for target–indication diligence packets.

## Step graph

1. `claim_extraction` → `evidence_table.json`
2. `risk_mapping` → `risk_map.json`
3. `report_generation` → `diligence_report.json` + `diligence_report.md`

## Providers

- **fixture / CI:** `MockProvider` reading `tests/fixtures/synthesis/{case_id}_{step}_data.json`
- **live:** `OpenAIProvider` when `OPENAI_API_KEY` is set; otherwise `MockProvider`

## Rules

- Every supported claim must cite `source_record_ids` present in input artifacts.
- Do not invent PMIDs or NCT IDs not in source records.
- Mark uncertain claims `insufficient_evidence` or `partially_supported`.
