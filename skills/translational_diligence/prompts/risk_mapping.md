Prompt Name: risk_mapping
Purpose: Generate translational risk map from evidence and trials.
Input Artifacts: evidence_table.json, clinical_trials.json, target_biology.json
Output Artifact: risk_map.json
Output Schema: schemas/risk_map.schema.json
Allowed Claim Sources: evidence_table evidence_ids and source_record_ids only
Failure Behavior: Return low-confidence inferred risks when support is weak; maximum 10 risks.
Max Output Tokens: 4000

Categorize risks using: translational, clinical, biomarker, safety, competition, evidence_gap, manufacturing, regulatory.
