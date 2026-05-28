# RI CSV Static Intake

Use this flow to bake Rhode Island physician/IP opportunities into the repo without runtime API dependence.

## Normalize external RI source exports

Before importing RI case YAMLs, normalize the three raw source exports:

- `/Users/JJR/Downloads/data.csv` (RI clinicians)
- `/Users/JJR/Downloads/Other/Data/CSV/ri-database-patents.csv` (RI patents)
- `/Users/JJR/Downloads/ctg-studies (21).csv` (historical RI trial records)
- Optional supplemental Lens export: `data/ri/source/ri-patents-2.csv` (merged by Lens ID automatically)

Run:

```bash
python -m pipeline.normalize_ri_sources
```

To merge an additional patent export (e.g. ProThera / expanded RI set):

```bash
cp /path/to/ri-patents-2.csv data/ri/source/ri-patents-2.csv
python -m pipeline.normalize_ri_sources
# or: python -m pipeline.normalize_ri_sources --supplemental-patents-csv /path/to/file.csv
```

Normalization automatically runs `pipeline.apply_seed_resolution` afterward (curated Tier A seed patent/physician fixes).

Optional controls:

```bash
# keep max 2 patents per opportunity; default max-generated-opportunities=0 means include all clusters
python -m pipeline.normalize_ri_sources --max-assets-per-opportunity 2 --max-generated-opportunities 0
```

Patent rows are **deduped by invention family** (similar title token sets within each owner/type group) so continuation filings do not create separate syndicate opportunities. Curated seed rows (for example `theromics_ri`) absorb matching patent families before auto-generation.

Re-apply seed patches without re-normalizing (if you edited `apply_seed_resolution.py` only):

```bash
python -m pipeline.apply_seed_resolution
```

Scan **uncatalogued** patent opportunities for Tier A promotion candidates (exports CSV + markdown report):

```bash
python -m pipeline.scan_ri_uncatalogued
```

Outputs under `data/ri/`: `ri_uncat_patent_scan.csv`, `ri_uncat_promotion_shortlist.csv`, `ri_uncat_physician_match_suggestions.csv`, `RI_UNCAT_TIER_A_RECOMMENDATIONS.md`.

Validate Tier A consistency (catalog, IP, opportunities, combined JSON, web profiles):

```bash
python -m pipeline.validate_ri_tier_a
```

After normalization, sync case configs:

```bash
python -m pipeline.import_ri_csv --csv data/ri/ri_opportunities.csv --overwrite
python -m pipeline.batch_ri_fixture
python -m pipeline.build_opportunity_bundle --sync-cases
```

Or from the repo root:

```bash
npm run batch:ri:fixture
npm run publish:ri
```

This command writes deterministic static tables into `data/ri/`:

- `ri_opportunities.csv` (opportunity-level rows, includes deterministic LLM-label proxy fields)
- `ri_ip_assets.csv` (max 2 patent assets per opportunity, policy-enforced)
- `ri_physicians.csv` (normalized RI clinician roster, `mocked=false`)
- `ri_trial_templates.csv` (RI trial-derived templates, `mocked=false`)
- `ri_capital_sources.csv` (fixed policy sources for 50/50 physician + Slater SSBCI split)
- `ri_governance_rules.csv` (static COI/role policy constraints)

## Input CSV

Canonical seed file:

- `data/ri/ri_physicians_ip_seed.csv`
- `data/ri/ri_physicians.csv`
- `data/ri/ri_trial_templates.csv`
- `data/ri/ri_capital_sources.csv`
- `data/ri/ri_lens_mock_signals.csv`

Each row represents one opportunity and is converted into one case config in `configs/cases/`.

## Import command

```bash
python -m pipeline.import_ri_csv --csv data/ri/ri_physicians_ip_seed.csv --overwrite
```

Notes:

- generated configs are static-first:
  - `fixture_allowed: true`
  - `live_allowed: false`
- this step only writes YAML configs; it does not call connectors.

During workflow generation, RI CSV inputs are converted into additional case artifacts:

- `ri_clinical_inflection.json`
- `ri_physician_match.json`
- `ri_capital_match.json`
- `ri_financing_readiness.json`

## Publish static artifacts

After configs exist, generate and publish static packets:

```bash
python -m pipeline.publish_static --case theromics_ri --mode fixture
python -m pipeline.publish_static --case monaghan_sepsis_diagnostic_ri --mode fixture
python -m pipeline.publish_static --case cbt_pain_digital_platform_ri --mode fixture
python -m pipeline.publish_static --case nanode_ri --mode fixture
```

## CSV field guidance

High-value fields to populate early:

- `case_id`
- `display_name`
- `target`
- `indication`
- `opportunity_type` (`platform`, `diagnostic`, `digital_therapeutic`, `medical_device`, `therapeutic`)
- `company`
- `slater_invested` (`true`/`false`)
- `development_stage`
- `strategic_question`

Helpful RI-specific context columns (kept in CSV for later mapping/detail refinement):

- `ri_physician_lead`
- `ri_physician_specialty`
- `ri_institution`
- `ri_ip_source`
- `ri_notes`

## Optional aggregate export

If you want a single aggregate RI payload for ad hoc analysis:

```bash
python -m pipeline.export_ri_lens_mock
```

Output:

- `web/public/data/ri/ri_lens_mock_signals.json`

## Tier A canonical sources (editable comps / finance / evidence QC)

Tier A programs use static source files under `data/ri/tier_a/`:

- `registry.csv` — program identity and finance overrides
- `comparables.csv` — curated comparables (replaces auto precedent templates for Tier A)
- `evidence_overrides.csv` — human evidence grade and review status
- `finance_policy.yaml` — gap buckets when registry `capital_gap_usd` is blank

```bash
# Backfill from current catalog + precedents (refresh tier_a CSVs)
python -m pipeline.tier_a.backfill

# Validate editable sources
npm run tier:a:validate

# Rebuild precedents + catalog inference (Tier A overrides applied)
npm run tier:a:build

# Add or update one Tier A program (interactive walkthrough)
python -m pipeline.tier_a.add_case --case-id theromics_ri
python -m pipeline.tier_a.add_case --case-id my_new_ri --from-case auto_brown_university_...
```

See `data/ri/tier_a/README.md`.

## Monolithic case enrichment (display truth)

**Canonical file:** `data/ri/ri_cases_enriched.csv` — one row per catalog program (~49).  
See **`docs/RI_CASES_MONOLITHIC.md`** for column layout and locked decisions.

```bash
npm run ri:cases:bootstrap    # merge catalog + IP + comparables + BioMCP suggest_*
npm run ri:cases:suggest      # refresh suggest_* columns
# edit CSV in Excel; copy suggest → main; set review_status=approved
npm run ri:cases:validate
npm run ri:cases:build        # → web/public/data/ri/opportunities_combined.json
npm run ri:cases:refresh      # bootstrap + suggest + validate + build
```

`npm run build:ri:artifacts` uses this path by default. Legacy: `npm run build:ri:artifacts:legacy`.

## Patent-linked BioMCP literature

Publications are filtered to match **anchored patent inventors** (surname overlap) and **science overlap** with the primary patent title.

```bash
# Catalog programs with catalog_include=true (default)
PATH="${PWD}/.venv/bin:${PATH}" python3 -m pipeline.enrich_ri_biomcp --tier A --refresh

# All RI opportunities that have ri_ip_assets rows (~212 cases; slow)
npm run enrich:ri:biomcp:all

python3 -m pipeline.build_ri_combined
```

Evidence file: `data/ri/ri_opportunity_evidence.json` (includes `network_edges` for shared-inventor case links).

## Comparator company site dossiers

Enrich lead comparators from their corporate websites (clinical, publications, reimbursement, KOL signals):

```bash
# Seed fixture dossiers (offline / CI)
python -m pipeline.enrich_ri_comp_sites --seed-fixture

# Tier A live fetch (requires network)
python -m pipeline.enrich_ri_comp_sites --tier A --fetch

# Single case refresh
python -m pipeline.enrich_ri_comp_sites --case-id theromics_ri --fetch --refresh
```

Writes `data/ri/ri_comp_site_dossiers.json`. Merged into exhibits via `python -m pipeline.build_ri_combined`.

Human-reviewed dossiers (`human_reviewed: true`) are not overwritten unless `--refresh` is passed.
