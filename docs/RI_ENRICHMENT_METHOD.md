# RI enrichment method — cited, approval-gated translational diligence

**Audience:** RI physician investors, [Right Hill Ventures](https://righthillventures.com) (Brown/RI tech SPV), and Slater Tech Fund (SSBCI match for RI equity).

**Artifact:** [`data/ri/ri_cases_enriched.csv`](../data/ri/ri_cases_enriched.csv) — one row per catalog program; single source of truth for the opportunity UI.

**Related:** [RI_CASES_MONOLITHIC.md](./RI_CASES_MONOLITHIC.md) (column schema and locked policy rules).

---

## What this is

**RI-aligned, human-gated translational diligence catalog** — not autonomous “AI enrichment.”

| Layer | Role | Examples |
|-------|------|----------|
| **Ground truth** | Do not infer | Lens patents, `ri_ip_assets`, CMS NPI physicians, tier-A comp seeds |
| **Machine assist** | Proposals in `suggest_*` / `web_search_*` | BioMCP, PubMed, DuckDuckGo comp resolution, Brown VIVO |
| **Policy + human gate** | What investors see | Allowlists, $400K cap, 50/50 physician/Slater, `review_status=approved` |

```text
Lens / CMS uploads     ──┐
BioMCP + web search      ──┼──►  ri_cases_enriched.csv  ──►  validate  ──►  build  ──►  UI
Curator approval         ──┘
```

---

## Value for each stakeholder

| Stakeholder | What each row delivers |
|-------------|------------------------|
| **Physician syndicate** | RI lead PI, local supporters (NPI), RI lead-author pubs, clinical path, defined check (`physician_share_usd` ≤ $200K) |
| **Right Hill Ventures** | Brown/URI/RI Hospital IP anchor, inventor-aligned lead, science + dev-path comps, financable milestone narrative |
| **Slater Tech Fund** | Match-ready package: `slater_share_usd` ≤ $200K, cited comp financing URLs, no inflated “capital gap” UI |

---

## Enrichment tools (npm)

| Command | What it does |
|---------|----------------|
| `npm run ri:cases:bootstrap` | Rebuild CSV from catalog + IP + comps (preserve approved columns) |
| `npm run enrich:ri:biomcp -- --tier A` | Refresh `ri_opportunity_evidence.json` (patent-linked pubs/trials) |
| `npm run ri:cases:biomcp:apply` | Promote RI lead-author pubs → `publication_*`; others → `suggest_publication_*` |
| `npm run ri:cases:vivo` | Brown faculty → `https://vivo.brown.edu/display/{slug}` |
| `npm run ri:cases:enrich:web` | DuckDuckGo comp/profile/R&D queries → `suggest_comp*` + `web_search_*` audit |
| `npm run ri:cases:enrich:web:fast` | Heuristic comp links only (SEC/company pages; ~2s, no DDG) |
| `npm run ri:cases:remediate` | Mechanical fixes (thesis, leads, indications, comp types) |
| `npm run ri:cases:validate` | Errors only on `review_status=approved` rows |
| `npm run ri:cases:export-json` | Curator UI + build input |
| **`npm run ri:cases:enrich`** | **Full assist pass:** biomcp apply → vivo → web → export |

**Curator:** `/opportunities/curate` — review `suggest_*` and `web_search_notes`, copy into main columns, set `review_status=approved`.

---

## Column conventions

### Main columns (promoted after review)

- **Publications:** `publication_*` — 2–6 Tier A, RI lead author ([allowlist](../data/ri/ri_institution_allowlist.yaml))
- **Physicians:** `physician_lead_*`, `physician_supporters` (NPI pipe format)
- **Comps:** `comp1_*` … `comp3_*` — `value_source_url` must be PR/SEC/investor page, not Google search
- **Finance:** `total_package_usd` ≤ 400000, 50/50 physician/Slater (`build_thesis()`)

### Assist columns (scripts write; human promotes)

| Column | Source |
|--------|--------|
| `suggest_publication_*` | BioMCP patent-linked candidates failing RI lead-author rule |
| `suggest_comp1_*` | Web-resolved financing URL for comp1 |
| `web_search_queries` | Pipe-separated queries executed (audit trail) |
| `web_search_notes` | Newline results: `[compN] title \| url`, `[profile] url`, `[rd] title \| url` |

### Rules

1. **Never** auto-set `review_status=approved`.
2. **Comps:** science + development path precedent; not RI geography ([Eascra for NanoDe](../data/ri/tier_a/comparables.csv) is the model).
3. **Publications:** strict RI lead author; BioMCP alone is insufficient if first author is not RI-affiliated.
4. **Finance UI:** policy package only — no million-dollar inferred gaps in snapshot.

---

## Web search strategy (`enrich_ri_cases_web.py`)

For each `catalog_include=true` row with `review_status != approved`:

1. **Comparable financing** — for each comp missing `value_source_url`, run VC-biased DuckDuckGo queries ([`comp_financing.resolve_financing_queries`](../pipeline/tier_a/comp_financing.py)); store best hit in `suggest_comp1_*` or `web_search_notes` for comp2/3.
2. **Physician profile** — if lead lacks profile URL and is not Brown (VIVO handled separately): query `{name} site:lifespan.org OR site:web.uri.edu`.
3. **R&D context** — if `rd_plan_summary` empty: query `{title} {indication} preclinical milestone`; record top hit in `web_search_notes` (curator drafts `rd_plan_summary`).

Queries and hits are always recorded in `web_search_queries` / `web_search_notes` even when nothing is promoted.

---

## Typical workflow

```bash
# After patent/CMS upload changes
npm run ri:cases:bootstrap

# Full machine-assist pass (~5–15 min with web fetch)
npm run ri:cases:enrich

# Human: open /opportunities/curate or edit CSV
#   - promote suggest_* → main columns
#   - set review_status=approved per row

npm run ri:cases:validate
npm run ri:cases:build
```

---

## Quality bar before `approved`

| Check | Tier A |
|-------|--------|
| `publication_count` | 2–6, RI affiliations on allowlist |
| `physician_lead_name` | Present; profile URL when available |
| `comp1` verified | Requires `value_source_url` |
| Finance | physician + slater = total ≤ $400K |

---

## What this is not

- Not a live API — CSV is batch-refreshed.
- Not geography-based comp matching.
- Not full autonomous diligence — Rhodes/Noramco opioid rows may lack RI academic pubs by design.
