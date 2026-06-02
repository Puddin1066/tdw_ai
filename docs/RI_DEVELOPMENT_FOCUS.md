# RI platform development focus

**Purpose:** Keep every change aimed at **Rhode Island physician-led investment matching** — higher value, higher accuracy, and stronger cited appeal for local investors and clinicians. Avoid structural churn that does not serve that outcome.

**Audience:** Engineers, curators, and agents working on this repo.

**Related:** [RI_CASES_MONOLITHIC.md](./RI_CASES_MONOLITHIC.md) · [RI_ENRICHMENT_METHOD.md](./RI_ENRICHMENT_METHOD.md)

---

## North star

> Help RI physicians and RI-aligned investors decide whether to co-invest in a **specific translational opportunity** — with **cited, reviewable data**, not generic AI output.

Success looks like:

- A physician can read one memo and answer: *Who leads? What does my check buy? What comp path proves this is real?*
- An investor can trace every dollar anchor and clinical claim to a **primary URL** or **uploaded ground truth**.
- Empty fields are **honest** (no false trials, no wrong comps, no invented financing).

---

## Stakeholders (do not optimize for others first)

| Stakeholder | Primary question | What we must improve |
|-------------|------------------|----------------------|
| **Physician syndicate** | “Is this in my specialty, and can I oversee the next clinical step?” | NPI roster, inventor alignment, clinical allocation, pilot design (`clinical_*`) |
| **Right Hill Ventures** | “Is Brown/URI/RI Hospital IP + team credible vs a financable comp path?” | Patents, RI lead-author pubs, verified comps, thesis |
| **Slater Tech Fund** | “Is this a match-ready $400K package (≤$200K Slater)?” | `total_package_usd`, cited comp financing, use-of-funds split |

If a feature does not help at least one row in [`ri_cases_enriched.csv`](../data/ri/ri_cases_enriched.csv) answer those questions better, **defer it**.

---

## Use existing infrastructure only

All transforms and copies flow through the **current stack**. Extend it; do not fork parallel paths.

### Ground truth (never LLM-invent)

| Source | Role |
|--------|------|
| Lens / `ri_ip_assets.csv` | Patents, inventors |
| CMS / `ri_physicians.csv` | NPI syndicate pool |
| `tier_a/comparables.csv` | Human-reviewed comp seeds |
| `ri_trial_templates.csv` | RI pilot design analogs |
| Catalog / bootstrap | Case identity |

### Machine assist (propose → cite → curate)

| Tool | npm / module | Writes to |
|------|--------------|-----------|
| BioMCP + PubMed | `enrich:ri:biomcp`, `ri_biomcp_publications` | `suggest_publication_*`, evidence JSON |
| DuckDuckGo / comp resolve | `enrich_ri_cases_web`, `comp_link_resolve` | `suggest_comp*`, `web_search_*`, comp URLs |
| Brown VIVO | `ri:cases:vivo` | `physician_lead_profile_url` |
| ClinicalTrials.gov | `ri_trial_enrichment` | `trial_*` (strict) / `suggest_trial_*` |
| NPI + tags | `enrich_ri_cases_physicians` | `suggest_physician_*`, staffing scores |
| Inventor → NPI | `ri_inventor_npi_match` | lead alignment |
| OpenAI agent | `ri:cases:enrich:agent:live` | comps/R&D **proposals** in `suggest_*` / audit columns only |
| Remediate | `ri:cases:remediate` | mechanical fixes |
| **Case orchestrator** | `ri:cases:enrich:case` → `pipeline.enrich_ri_case` | chains all steps above per `--case-id` / `--mode` |

### Publish path (compile only)

```text
ri_cases_enriched.csv  ──►  npm run ri:cases:build  ──►  opportunities_combined.json  ──►  /opportunities/*
```

**Rule:** Build **compiles** the CSV; it does not infer new facts. After any CSV or tier-A comp change, run **`npm run ri:cases:build`**.

**Package pass (preferred batch):** `npm run ri:cases:enrich:package` — Tier-A comps + physician/inventor match + use-of-funds + build.

**Single case (preferred for Tier A curation):** `npm run ri:cases:enrich:case -- --case-id <id> --mode tier_a_full --build`. Approved copy-only: `--mode refresh_copy`.

---

## What to improve (in priority order)

1. **Accuracy** — wrong comps, wrong trials, mismatched NPIs, stale JSON vs CSV  
2. **Citation** — every promoted field has `*_source_url` or structured citations  
3. **Physician framing** — syndicate fit, clinical allocation, milestone a physician can oversee  
4. **Investor framing** — verified comp anchors, financing ladder, $400K policy package  
5. **Coverage** — fill gaps on Tier A first; Tier B stays `pending` until curated  

---

## Anti-patterns (reject without explicit product approval)

| Anti-pattern | Why |
|--------------|-----|
| New JSON/CSV display sources parallel to `ri_cases_enriched.csv` | Drift; curators lose single source of truth |
| Auto `review_status=approved` | Physician/investor trust requires human gate |
| Institution-name search keys (“Brown”, inventor surname alone) | False positives (e.g. brown adipose) |
| CT.gov trials on memo when mechanism match is weak | Credibility harm; empty is OK |
| Million-dollar inferred “capital gaps” | Policy is ≤$400K physician/Slater package |
| MOCK/synthetic data in main columns | Must stay in `suggest_*` or audit fields |
| New UI sections without CSV columns + build wiring | Orphan UI; cannot curate |
| Generic enrichment metrics (“47/47 have trials”) | Optimize for **verified** coverage, not fill rate |
| Structural refactors “for cleanliness” | Only if they unblock accuracy or cited appeal |

---

## Pre-change checklist

Before adding code, columns, UI, or docs, answer **yes** to at least one:

- [ ] Improves **accuracy** of data shown to RI physicians/investors  
- [ ] Adds or strengthens **primary-source citations** for an existing column  
- [ ] Improves **physician syndicate matching** (NPI, specialty, inventor, allocation)  
- [ ] Improves **comp/financing precedent** quality (mechanism-aligned, verified URLs)  
- [ ] Makes **curation faster** (promote `suggest_*` → main with clear audit trail)  
- [ ] Fixes **build/sync** so memo matches CSV  

If none apply, **do not implement**.

### Structural change bar

New modules, schemas, pages, or pipelines require:

1. One sentence: **which stakeholder question** this answers  
2. Which **existing** enrich script or npm command will populate it  
3. Which **CSV columns** hold curated truth vs `suggest_*` assist  
4. How **`ri:cases:validate`** will guard approved rows  
5. Curator sign-off pattern (no auto-promote to investor UI)

---

## OpenAI API usage

Use the agent **only** to:

- Propose mechanism-aligned comps and R&D milestones when tier-A seeds are missing  
- Draft physician-readable prose **into assist columns**  
- Generate search queries for DuckDuckGo verification  

**Always:**

- Run with URL verification when writing CSV (`:live` + fetch)  
- Record queries in `web_search_queries` / `web_search_notes`  
- Strip MOCK from main columns (`ri_source_utils`)  
- Require curator promotion for investor-visible fields  

**Never:**

- Treat LLM output as ground truth without a cited URL  
- Skip human review for finance, comps, or physician lead  

---

## Web search usage

Web search exists to resolve **primary sources**:

- Comp financing (PR, SEC, investor pages — not Google redirect URLs)  
- Physician profiles (`site:lifespan.org`, `site:web.uri.edu`, VIVO)  
- R&D / regulatory context for milestones  

Every hit goes to **`web_search_notes`** or `suggest_*`; promotion to main columns is manual unless remediate/tier-A policy explicitly syncs verified comps.

---

## Continuous development workflow

```text
1. Identify gap on Tier A case (memo vs curate vs stakeholder feedback)
2. Fix upstream seed if needed (tier_a/comparables.csv, PHYSICIAN_FIXES, remediate)
3. Run targeted enrich npm script (not a new one-off script unless merged into pipeline)
4. Curate in /opportunities/curate or CSV
5. npm run ri:cases:validate  (approved rows)
6. npm run ri:cases:build
7. Spot-check localhost memo + citations
```

**Tier A before Tier B.** **Verified before suggested.** **Empty before wrong.**

---

## Definition of done (feature/enrichment)

- [ ] Data lands in `ri_cases_enriched.csv` (main or `suggest_*`)  
- [ ] Source URLs populated where policy requires  
- [ ] `npm run ri:cases:build` run; memo matches curate row  
- [ ] No new parallel artifact path for investor UI  
- [ ] Docs updated only if behavior or npm commands changed  
- [ ] Tests for matching/scoring logic if enrichment rules changed  

---

## Agent / IDE reminder

Cursor rule: [`.cursor/rules/ri-platform-focus.mdc`](../.cursor/rules/ri-platform-focus.mdc) — apply on all RI catalog, pipeline, and opportunity UI work.

When in doubt: **make the CSV more accurate and cited; rebuild; let curators approve.**
