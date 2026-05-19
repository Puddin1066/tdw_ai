Prompt Name: report_generation
Purpose: Generate structured diligence report JSON.
Input Artifacts: evidence_table.json, risk_map.json
Output Artifact: diligence_report.json
Output Schema: schemas/diligence_report.schema.json
Allowed Claim Sources: evidence rows and risk map only
Failure Behavior: Lower overall_confidence when evidence is thin; do not fabricate citations.
Max Output Tokens: 4000

Produce title, executive_summary, overall_confidence (0-1), maturity_stage, sections, cited_source_record_ids, cited_nct_ids, cited_pmids, and optional diligence_questions.

Requirements for grounded report richness:
- Return at least 4 sections: Mechanistic basis, Clinical landscape, Risk posture, Decision rationale.
- Each section should reference relevant `evidence_ids` from `evidence_table.json`.
- `cited_source_record_ids`, `cited_nct_ids`, and `cited_pmids` must be subsets of IDs present in input artifacts.
- Include 3-5 `diligence_questions` that are specific and actionable.
- If evidence is mixed or sparse, state uncertainty explicitly instead of broad claims.
