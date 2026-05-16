Prompt Name: claim_extraction
Purpose: Extract evidence rows from normalized biomedical source artifacts.
Input Artifacts: literature_records.json, clinical_trials.json, target_biology.json, normalized_entities.json
Output Artifact: evidence_table.json
Output Schema: schemas/evidence_table.schema.json
Allowed Claim Sources: source_record_ids from input records only
Failure Behavior: Emit rows with support_status insufficient_evidence when citations are missing.
Max Output Tokens: 4000

Extract mechanistic, translational, clinical, and safety claims as evidence rows. Each row must include evidence_id, claim_text, claim_type, support_status, confidence, source_record_ids, and quoted_evidence when available.
