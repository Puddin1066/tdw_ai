# Tier A canonical sources

Editable ground truth for investor-facing RI programs (`catalog_tier=A`).

## Files

| File | Purpose |
|------|---------|
| `registry.csv` | Program identity, finance overrides, review metadata |
| `comparables.csv` | 1–3+ comparables per case (names, anchors, URLs) |
| `evidence_overrides.csv` | Human evidence depth grade and review status |
| `finance_policy.yaml` | Gap buckets and syndicate split when registry gap is blank |

## Workflow

```bash
# Initial backfill from current catalog + precedents
python -m pipeline.tier_a.backfill

# Validate sources only
npm run tier:a:validate

# Rebuild precedents + catalog inference for all programs (Tier A overrides applied)
npm run tier:a:build

# Fast RI exhibit rebuild (no BioMCP)
npm run build:ri:artifacts

# Full pipeline including BioMCP (slow)
npm run build:ri:combined

# Sync + build + artifacts + consistency check
npm run tier:a:verify
```

## Verify comparables with web search

```bash
# Export queue + markdown workbook with Google search links per comp
python3 -m pipeline.tier_a.comp_web_review queue

# Interactive: open search links, paste anchors/URLs
python3 -m pipeline.tier_a.comp_web_review step
python3 -m pipeline.tier_a.comp_web_review step --case-id theromics_ri

# Or edit data/ri/tier_a/comp_review_findings.csv (use init-findings to seed)
python3 -m pipeline.tier_a.comp_web_review init-findings
python3 -m pipeline.tier_a.comp_web_review apply
npm run tier:a:build
```

Regenerate the workbook (real URLs only, no Google search pages in the markdown):

```bash
npm run tier:a:comps:queue
# optional: web-resolve press/SEC/market links for rows still missing citations
npm run tier:a:comps:queue:fetch
```

Open `comp_review_queue.md` — each row has **Primary-source links** (SEC, press, market data).
Pick the URL that supports the anchor and paste it into `value_source_url` in findings.

## Add a new Tier A program

```bash
python -m pipeline.tier_a.add_case --case-id my_program_ri
# Or promote from an auto_* opportunity:
python -m pipeline.tier_a.add_case --case-id my_program_ri --from-case auto_brown_university_...
```

The script walks through registry, comparables, and evidence QC, runs validation, and (if `status=active`) sets `catalog_tier=A` in `ri_opportunities_catalog_enrichment.csv`.

## Rules

- Do **not** hand-edit `ri_program_precedents.csv` for Tier A cases — edit `comparables.csv` and run `tier:a:build`.
- `validation_status=verified` requires `value_anchor_usd` and `value_source_url`.
- Financing ground truth = **VC staging** (`total_raised`, `series_*`, `last_round`) with PR links;
  use `market_cap` only for public/path comps without a venture ladder.
- BioMCP output in `ri_opportunity_evidence.json` is assistive; set `canonical_evidence_status` in `evidence_overrides.csv` for display truth.
