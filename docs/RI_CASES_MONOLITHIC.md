# RI cases — monolithic CSV implementation guide

**Objective:** Keep the **same opportunity UI** (`/opportunities/[caseId]`, catalog, pillars: Technology, Evidence, Market, Syndicate, Clinical, financing snapshot) but drive it from **one accurate, cited, human-reviewable CSV** instead of many drifting derived files.

**Non-goals:** New UI patterns, new JSON schemas unless necessary, multi-file curator workflows, or re-inferring dollars at build time.

**Methodology & enrichment tools:** [RI_ENRICHMENT_METHOD.md](./RI_ENRICHMENT_METHOD.md)  
**Development focus (agents & engineers):** [RI_DEVELOPMENT_FOCUS.md](./RI_DEVELOPMENT_FOCUS.md)

---

## Locked decisions (2026-05-28)

| # | Decision |
|---|----------|
| **Scope** | **Tier A + all catalog programs** (~49 rows with `catalog_include=true`) in one file |
| **Shape** | **Wide columns** — `comp1_name`, `comp2_name`, newline-separated `publication_urls`, etc. (Excel-friendly) |
| **Finance UI** | Show **only** the policy package (**≤ $400K**, 50/50 physician/Slater, Slater ≤ $200K). **No** million-dollar inferred `capital_gap` in the UI |
| **Publications** | **Strict RI lead author** — Brown, RI Hospital/Lifespan, URI, etc. (allowlist); 2–6 per approved case |
| **Web search** | Scripts write **`suggest_*` columns**; you copy good values into main columns and set `review_status=approved` |
| **File** | **`data/ri/ri_cases_enriched.csv`** — single source of truth |

---

## Core idea

| Today (problem) | Target (simple) |
|-----------------|-----------------|
| Patents, comps, pubs, physicians, finance spread across `ri_ip_assets`, `tier_a/*`, `ri_program_precedents`, BioMCP JSON, inferred catalog columns | **One row per case** in `data/ri/ri_cases_enriched.csv` |
| Build merges + guesses → UI shows wrong anchors/gaps | **Build only compiles** the CSV → `opportunities_combined.json` |
| Web search scattered in queue markdown | Web search writes **`suggest_*` columns**; you copy → main columns; `review_status=approved` |

```text
Your uploads (Lens, CMS, Seed notes)  ──┐
Web search (PR, PubMed, CT.gov, IR)   ──┼──►  ri_cases_enriched.csv  ──►  build  ──►  UI
Curator approval (review_status)      ──┘
```

---

## Single file

**Path:** `data/ri/ri_cases_enriched.csv`  
**Grain:** one row per `case_id` where `catalog_include=true` (~49 programs: Tier A + Tier B).

- Rows with `review_status=approved` → full validation → appear in UI.  
- Rows with `review_status=pending` → omitted from UI (or catalog shows “enrichment pending” if listed).  
- **Tier A** should meet all rules before `approved`; **Tier B** can stay `pending` until curated.

### Column groups (wide CSV — same spirit as `ri_opportunities_catalog_enrichment.csv`)

Use **pipe `|`** or **newline** inside cells for lists (already used for `physician_supporters` today). Prefer **stable prefixes** so columns sort together in Excel.

#### A. Identity & catalog (required)

| Column | Example | Notes |
|--------|---------|--------|
| `case_id` | `theromics_ri` | Primary key |
| `catalog_tier` | `A` | `A` \| `B` |
| `catalog_include` | `true` | |
| `review_status` | `approved` | `pending` \| `approved` — **UI only if approved** |
| `title_clean` | | |
| `company` | `Theromics Inc` | Operating company if any |
| `indication` | | |
| `opportunity_type` | `platform` | |
| `development_stage` | `validation` | |
| `ri_institution` | `Brown / RI Hospital` | |
| `data_caveat` | | UI badge |
| `ri_notes` | | Curator notes |
| `last_refreshed_at` | `2026-05-28` | |
| `reviewer` | `JJR` | |

#### B. Patents (Lens — from uploads)

| Column | Notes |
|--------|--------|
| `primary_lens_id` | Lead patent |
| `primary_display_key` | e.g. US 11076916 B2 |
| `primary_patent_title` | |
| `primary_patent_url` | `https://lens.org/{id}` |
| `assignee_company` | Normalized company on primary patent |
| `inventors` | Pipe-separated surnames |
| `ip_lens_ids` | Pipe-separated, max 2 for UI |
| `ip_titles` | Parallel to lens ids |
| `ip_urls` | Parallel Lens URLs |

**Source:** `ri_ip_assets.csv`, `source/ri-patents-2.csv` (import only; do not edit Lens exports in place).

#### C. Publications (2–6, RI lead author, cited)

| Column | Notes |
|--------|--------|
| `publication_count` | 2–6 when `review_status=approved` |
| `publication_titles` | Newline-separated |
| `publication_lead_authors` | Parallel — **must be lead author** |
| `publication_ri_affiliations` | Parallel — must match allowlist (Brown, RIH/Lifespan, URI, …) |
| `publication_urls` | PubMed or Lens per row |
| `publication_pmids` | Optional parallel |
| `literature_narrative` | 2–3 sentence summary |
| `literature_source_urls` | Newline `title \| url` — sources for narrative / suggest pubs / patent |

**Suggest columns (scripts only — copy into main columns after review):**

| Column | Notes |
|--------|--------|
| `suggest_publication_titles` | Newline-separated candidates |
| `suggest_publication_urls` | Parallel |
| `suggest_publication_notes` | Why suggested / reject reason |

**Rule:** BioMCP/inventor-linked hits go in `suggest_*` only unless lead author is RI-affiliated. Curator promotes 2–6 into main columns.

**Allowlist file (to add):** `data/ri/ri_institution_allowlist.yaml`

#### D. Physicians (RI syndicate, cited profiles)

| Column | Notes |
|--------|--------|
| `physician_lead_npi` | |
| `physician_lead_name` | |
| `physician_lead_specialty` | |
| `physician_lead_institution` | |
| `physician_lead_profile_url` | Hospital/clinic page (web search) |
| `physician_supporters` | Existing format: `npi\|name\|specialty\|institution\|role` per line |
| `physician_supporter_profile_urls` | Parallel URLs if available |

**Source:** `ri_physicians.csv` (CMS) + `ri_physician_match_suggestions.csv` + institution web search.

#### E. Comparables (VC staging, not just valuation)

Up to **3 comps** inline (expand to comp2/comp3 columns, not separate file):

| Column | Comp 1 (lead) |
|--------|----------------|
| `comp1_name` | |
| `comp1_type` | startup \| incumbent \| public |
| `comp1_url` | Company site |
| `comp1_value_anchor_usd` | |
| `comp1_value_anchor_type` | `total_raised` \| `series_a` \| `last_round` \| `grant` \| `market_cap` (fallback) |
| `comp1_value_source_url` | **PR/SEC round announcement** |
| `comp1_total_raised_usd` | Lifecycle VC total |
| `comp1_last_round_usd` | |
| `comp1_financing_ladder` | Prose: seed → A → B |
| `comp1_development_path` | Tech/reg path |
| `comp1_validation_status` | `verified` \| `suggested` \| `skip` |

Repeat `comp2_*`, `comp3_*`.

**Suggest columns (scripts only):**

| Column | Notes |
|--------|--------|
| `suggest_comp1_value_source_url` | PR/SEC candidate |
| `suggest_comp1_financing_ladder` | Draft VC ladder text |
| `suggest_comp1_notes` | Source headline / search note |

(Same pattern for comp2/comp3 if needed.)

**Source:** bootstrap from `tier_a/comparables.csv` + `comp_review_findings`; web assist fills `suggest_*`.

#### F. RI financing package (policy — display truth)

| Column | Rule |
|--------|------|
| `financing_stage` | `seed` \| `series_a` |
| `total_package_usd` | **≤ 400000** |
| `physician_share_usd` | 50% of total |
| `slater_share_usd` | 50% of total, **≤ 200000** |
| `clinical_allocation_usd` | Optional split |
| `rd_allocation_usd` | Optional split |
| `financing_rationale` | One short paragraph |

**Build rule:** `build_ri_combined` maps `total_package_usd` → snapshot `capital_gap_usd` / physician / Slater shares for display. **Do not** surface old catalog `capital_gap_usd` or comparator-derived million-dollar “RI package” text in the UI.

Optional internal column `legacy_capital_gap_usd` may exist for audit only; never shown in UI.

#### G. Clinical trials (optional, cited)

**Policy:** High-confidence CT.gov matches only in main columns. Most rows stay empty. Pilot design uses `clinical_*` (template analog). Weak path analogs → `suggest_trial_*` (curate tab).

| Column | Notes |
|--------|--------|
| `trial_count` | 0 = no strong registry match (expected for many preclinical rows) |
| `trial_nct_ids` | Pipe-separated |
| `trial_titles` | Parallel |
| `trial_pi_names` | Parallel |
| `trial_urls` | `https://clinicaltrials.gov/study/{NCT}` |
| `trial_phases` | Parallel |
| `suggest_trial_nct_ids` | Low-confidence analogs (scripts / curate only) |
| `suggest_trial_titles` | Parallel |
| `suggest_trial_urls` | Parallel |
| `suggest_trial_notes` | Role + relevance score |

**Source:** comp-precedent + mechanism CT.gov search ([`ri_trial_enrichment.py`](../pipeline/ri_trial_enrichment.py)), `ri_trial_templates.csv` for `clinical_*`, not institution-name queries.

#### H. R&D plan (brief)

| Column | Notes |
|--------|--------|
| `rd_plan_summary` | 2–4 sentences |
| `rd_milestones` | Newline bullets: mouse model, in silico, preclinical, partner, small trial |
| `rd_milestone_source_urls` | Parallel newline `milestone \| url` — primary source per milestone |
| `rd_plan_source_url` | Primary URL backing `rd_plan_summary` |
| `rd_milestone_types` | Tags pipe-separated |

#### I. Build / legacy (optional bridge)

Keep a few columns so existing `build_ri_combined` can be adapted incrementally:

| Column | Notes |
|--------|--------|
| `investment_thesis` | Shown in headline |
| `mcq_lead_pillar` | ip \| market \| physicians \| clinical |
| `enrichment_status` | `canonical_csv` |

---

## Pipeline (minimal)

```bash
# 1. Refresh staging from uploads (existing, when patents/CMS change)
python -m pipeline.normalize_ri_sources

# 2. Bootstrap monolithic CSV (~49 catalog rows)
npm run ri:cases:bootstrap

# 3. Web-assist: fill suggest_* columns only (optional)
npm run ri:cases:suggest

# 4. Edit data/ri/ri_cases_enriched.csv — copy suggest → main, set review_status=approved

# 5. Validate (errors only on approved rows)
npm run ri:cases:validate

# 6. Build UI JSON
npm run ri:cases:build
# or full refresh:
npm run ri:cases:refresh
```

**Default `build:ri:artifacts`** now runs bootstrap → suggest → comp-site seed → build from `ri_cases_enriched.csv`.

Legacy path: `npm run build:ri:artifacts:legacy`

---

## Validation (keep strict, keep small)

Fail build if `review_status=approved` and any of:

| Rule | Check |
|------|--------|
| Patents | `primary_patent_url` contains `lens.org` |
| Pubs | `publication_count` 2–6; each lead author + RI affiliation on allowlist; URLs non-empty |
| Physicians | lead NPI + name; `physician_lead_profile_url` recommended |
| Comps | `comp1_validation_status=verified` → `comp1_value_source_url` required; no `google.com/search` |
| Finance | `total_package_usd <= 400000`, `slater_share_usd <= 200000`, physician + slater = total |
| Trials | if `trial_nct_ids` set, every `trial_urls` is clinicaltrials.gov |

**Tier A** (`catalog_tier=A`): all rules required for `approved`.  
**Tier B**: may stay `pending` until curated; do not set `approved` until pubs/comps/finance pass.

---

## Web search vs uploads

**Rule:** Uploads (Lens, CMS, catalog, `tier_a/comparables`) populate **main columns** on bootstrap. Scripts may only write **`suggest_*` columns** — never `approved` or `verified` without you.

**Curator loop:**

1. `ri:cases:bootstrap` → ~49 rows in `ri_cases_enriched.csv`.  
2. `ri:cases:suggest` → fills `suggest_*` (PubMed, comp PRs, profile URLs).  
3. In Excel: copy good suggestions → main columns; fix finance package; set `review_status=approved` when done.  
4. `ri:cases:validate` → `ri:cases:build` → check UI.

**Do not** auto-set `comp1_validation_status=verified` or copy `suggest_*` → main without review.

---

## UI mapping (unchanged components)

| UI section | Monolithic columns |
|------------|-------------------|
| Headline / thesis | `title_clean`, `investment_thesis`, `data_caveat` |
| Technology | `ip_*`, `primary_patent_*` |
| Evidence | `publication_*`, `literature_narrative` |
| Market | `comp1_*` … `comp3_*` |
| Syndicate | `physician_lead_*`, `physician_supporters` |
| Clinical | `trial_*`, `rd_*` |
| Investment package | `total_package_usd`, `physician_share_usd`, `slater_share_usd` only (≤ $400K) |
| Citation links | `*_url` columns → existing `ComparableCitationLinks` |

**Not in UI:** legacy multi-million gaps, comparator value bands as “your raise,” or unverified `suggest_*` values.

No new React sections required for v1.

---

## Migration (phased)

1. **Bootstrap** `ri_cases_enriched.csv` with all `catalog_include=true` rows (~49) from catalog + `ri_ip_assets` + `tier_a/comparables`.  
2. **Implement** suggest → validate → build from this file only (stop editing `ri_program_precedents.csv` by hand).  
3. **Curate Tier A first** (set `approved` on ~24 rows); leave Tier B `pending` until ready.  
4. **Change build** so snapshot financing comes from `total_package_usd`, not inferred catalog gaps.  
5. Deprecate `ri_opportunities_catalog_enrichment.csv` as display source once parity is verified.

---

## What to do next (implementation)

1. Add `pipeline/bootstrap_ri_cases_enriched.py` — one row per catalog case, wide columns.  
2. Add `pipeline/suggest_ri_cases_enriched.py` — writes `suggest_*` only.  
3. Add `pipeline/validate_ri_cases_enriched.py` — enforces locked rules + RI pub allowlist.  
4. Adapt `build_ri_combined` — `review_status=approved` rows only; finance from `total_package_usd`.  
5. Curate **5 seed Tier A rows** as golden examples, then remaining Tier A, then Tier B.

---

## Related docs

- `docs/RI_CSV_STATIC_INTAKE.md` — Lens/CMS normalize (inputs to bootstrap)  
- `data/ri/tier_a/README.md` — comp web review (feeds `comp1_*` columns until merged)  
- `data/ri/Seed Tier A — 5 programs.txt` — narrative ground truth for five seeds  
