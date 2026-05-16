Prompt Name: report_generation
Purpose: Generate structured diligence report JSON.
Input Artifacts: evidence_table.json, risk_map.json
Output Artifact: diligence_report.json
Output Schema: schemas/diligence_report.schema.json
Allowed Claim Sources: evidence rows and risk map only
Failure Behavior: Lower overall_confidence when evidence is thin; do not fabricate citations.
Max Output Tokens: 4000

Produce title, executive_summary, overall_confidence (0-1), maturity_stage, sections, cited_source_record_ids, cited_nct_ids, cited_pmids, and optional diligence_questions.
