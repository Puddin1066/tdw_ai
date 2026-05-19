# BioMCP Migration Guide (Connector Layer Only)

This guide defines a low-risk way to adopt BioMCP for richer biomedical retrieval while preserving TDW contracts, eval behavior, and UI expectations.

Primary reference: [BioMCP](https://biomcp.org/)

## Objective

Increase source depth and reliability by using BioMCP as a retrieval backend for selected connectors, without changing:

- artifact schemas,
- pipeline orchestration contract,
- eval scoring behavior,
- frontend component APIs.

## Non-goals

- No product/UI rewrite.
- No replacement of `pipeline.run_workflow`.
- No bypass of existing provenance and warning contracts.

## Adapter Contract: BioMCP -> ConnectorResult

Every BioMCP-backed connector must still return TDW `ConnectorResult` with existing fields:

- `connector_name`
- `case_id`
- `mode`
- `query`
- `retrieved_at`
- `records`
- `errors`
- `warnings`
- `provenance`
- `raw_payload`

### Required mapping rules

1. `query`:
   - Preserve TDW query object from `build_query(config)`.
   - Optional BioMCP query details go into `raw_payload`.

2. `records`:
   - Normalize each BioMCP item to TDW source record shape used by downstream builders.
   - Preserve stable `source_record_id` (`<source>:<id>`).
   - Include `source_type`, `source_name`, `title`, `url`, `retrieved_at`, `raw_record_ref`.

3. `raw_payload`:
   - Store BioMCP command/arguments and raw response body for auditability.
   - Include pagination and query count metadata when available.

4. `warnings` and `errors`:
   - If BioMCP succeeds with sparse results, use warnings (not hard errors).
   - If BioMCP call fails, return `errors` and let existing fallback behavior apply.
   - If fallback is used, warning text must explicitly include `MOCK/SYNTHETIC fallback`.

5. `provenance`:
   - Keep connector source fields (`source_name`, `source_url`, `api_endpoint`, `api_version`) filled.
   - Identify BioMCP transport in `api_endpoint` or `raw_payload`.

## Source-Specific Mapping Notes

### OpenTargets (BioMCP `disease` / `gene` / `drug` paths)

- Favor records that expose target/disease associations.
- Map to TDW `source_type: target_biology` or `relationship`.
- Populate:
  - `biology_source: opentargets`
  - `target_id`, `disease_id`, `association_score` when present.

### ChEMBL (BioMCP `drug` or source-backed sections)

- Map molecules and mechanism snippets.
- Use:
  - `source_type: compound` for molecule-level rows,
  - `source_type: relationship` for activity/mechanism rows.
- Populate:
  - `biology_source: chembl`
  - `molecule_chembl_id`, `mechanism_of_action`, `activity_summary`.

### BioThings (BioMCP `gene` / `disease` paths)

- Map gene-context and pathway/summary context as relationship rows.
- Use:
  - `source_type: relationship`
  - `biology_source: biothings`
  - `subject`, `predicate`, `object`, `relationship_confidence`.

## Minimal Migration Sequence

1. Add optional BioMCP execution helper module (no connector behavior change yet).
2. Migrate one connector first (`opentargets`) behind a flag.
3. Run live workflow and compare richness metrics against baseline.
4. Migrate `chembl`.
5. Migrate `biothings`.
6. Remove flag only after tests + evals + build pass.

## Acceptance Gates (must stay green)

- `pytest tests/ -q`
- `python -m pipeline.run_workflow --config configs/cases/sting_pdac.yaml --mode live`
- `python -m evals.run_evals --case generated/cases/sting_pdac`
- `npm run build --prefix web`

## Richness Gate Targets (post-migration)

For `sting_pdac`, target minimums:

- `source_manifest` shows all migrated connectors as live (no fallback warning).
- `target_biology.json` records >= 120.
- `knowledge_graph.json` edges >= 150.
- `evidence_table.json` rows >= 10 with non-empty `source_record_ids`.
- `eval_results.json` remains `overall_passed: true`.

## Fast Rollback Plan

If BioMCP path regresses reliability or causes eval failures:

1. Re-enable native connector code path.
2. Keep BioMCP adapter module isolated for iteration.
3. Preserve failed run artifacts for diff-based debugging.

