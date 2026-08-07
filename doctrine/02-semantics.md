# 02 — Semantics: Building the Keyword Core, Clustering, Intent

**Version:** 0.1.0 · **Date:** 2026-08-07 · **Subordinate to:** `00-principles.md`

---

## Header

| Field           | Value                                                                                                                                                                                                                          |
| --------------- | ------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------ |
| **Purpose**     | Turn raw demand into a list of decisions of the form "this page should exist", each carrying an intent, a priority, and the existing page it maps to, if any                                                                   |
| **Inputs**      | GSC (mandatory), Ahrefs CSV export (if available), SERP provider, seeds from onboarding (`01-onboarding-grill.md`), corpus map `.kiln/corpus.json`                                                                             |
| **Outputs**     | `.kiln/semantics/` — edge graph, clustering run versions, active clusters, facet maps, priority queue                                                                                                                          |
| **Executed by** | Code — collection, normalization, edges, clustering, rule-based intent, priority. Agent — hypothesis generation and arbitration of ambiguous intent. Human — sign-off on large cluster merges and on cannibalization decisions |
| **Cost**        | Building a 5,000-query core ≈ $4–6; upkeep ≈ $1–3/month per locale                                                                                                                                                             |

This section answers **what to write**. **How to write** is `05-writing-core.md`; **whether we may write at all** is `10-safety-gates.md`.

---

## 1. Sources of Semantics: Priority and Trustworthiness

The ordering is deliberate: trustworthiness falls and the cost of error rises as you go down. Every query in the core carries `source`, `volume_source`, `volume_captured_at`, `is_verified` — a record without them is invalid.

### 1.1. Google Search Console — the primary source

| Parameter       | Value                                                                                                                                            |
| --------------- | ------------------------------------------------------------------------------------------------------------------------------------------------ |
| Cost            | $0                                                                                                                                               |
| Limits          | Search Analytics 1200 QPM per site, 30M QPD per project; 25,000 rows per request; 16-month window; 2–4 day lag `[source: EVIDENCE.md#e12-data-apis-and-pricing, EVIDENCE.md#e04-search-console]` |
| What it gives   | Real queries, impressions, clicks, position, broken down by query × page. The only **non-estimated** source of demand                            |
| Trustworthiness | `source=gsc`, `is_verified=true` with no further checks                                                                                          |

Three properties that break a naive implementation:

1. **Long-tail anonymization.** Google withholds rare queries entirely; in an anonymized row the query field is empty, not `NULL` `[source: EVIDENCE.md#e04-search-console]`. On small sites a substantial share of queries is lost, and query-level sums will not reconcile with page-level sums. This is not an export bug — it is a property of the source, and it has to be documented in reports, or people will go hunting for a bug in the code.
2. **The 16-month window is irreversible.** Older data is erased. Incremental export from day one is not an optimization; it is the only way to ever hold history deeper than a year and a half.
3. **Hourly data lives for 8 days** `[source: EVIDENCE.md#e08-trend-detection]`. If you need it — for detecting the newsjacking window, see `04-trends-and-plan.md` — you must warehouse it daily rather than query it on demand.

**SEM-01 (BLOCK).** Incremental GSC export is configured on day one of onboarding, before any semantics work begins. A project without warehoused export runs in `cold start` mode and is flagged as such in every report.

### 1.2. Ahrefs CSV export — volumes and competitor keywords

The project holds a UI subscription with no API `[owner decision]`. That means data arrives as manual exports, irregularly, and must carry a capture date.

| Parameter       | Value                                                                                                                             |
| --------------- | --------------------------------------------------------------------------------------------------------------------------------- |
| Cost            | included in the subscription; the API is not used ($500–10,000/month — outside the budget of a portable framework, `EVIDENCE.md#e12-data-apis-and-pricing`) |
| What it gives   | Volumes, KD, competitors' organic keywords, positions                                                                             |
| Trustworthiness | `volume_source=ahrefs_ui_csv`, `volume_captured_at` = export date, mandatory                                                      |

Column mapping for the export lives in `.kiln/project.yml`, never hardcoded: the set and the naming of columns depend on the UI version and on which report was exported (Keywords Explorer vs. Organic keywords in Site Explorer). The import script must fail loudly on an unknown column rather than silently substituting `null`.

**SEM-02 (WARN).** A volume figure older than 90 days is flagged stale and is not used in prioritization without a re-pull. Threshold `[expert judgement, needs calibration]`.

**SEM-03 (INFO).** Volume is a filter, not a prioritizer. It screens out zero-demand noise from autocomplete, but it does not predict traffic: 68.01% of US searches in January–April 2026 ended without a click `[source: SparkToro/Similarweb via Search Engine Land, EVIDENCE.md#e05-semantics-and-clustering]`. Priority is computed by the formula in §6.

### 1.3. DataForSEO — SERP, autocomplete, Labs

| Parameter       | Value                                                                                                                                                                   |
| --------------- | ----------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| Cost            | SERP Standard **$0.60/1000**, Priority $1.20, Live $2.00. Labs from $0.00012/row, $0.012 per task submission `[source: DataForSEO pricing, EVIDENCE.md#e05-semantics-and-clustering, EVIDENCE.md#e12-data-apis-and-pricing]` |
| Billing model   | pay-as-you-go, $50 deposit funded `[owner decision]`                                                                                                                    |
| Latency         | Standard ~5 minutes — acceptable for batches, unacceptable for interactive use                                                                                          |
| Trustworthiness | `is_verified=true` for queries returning a non-empty SERP                                                                                                               |

**AI Overviews make SERP calls 4–15× more expensive**: $2.60/1k at n=10 against the $0.60 baseline, $9.20/1k at n=100 `[source: cloro 2026 via EVIDENCE.md#e12-data-apis-and-pricing]`. Hence:

**SEM-04 (BLOCK).** AIO is requested only for a priority subset of queries defined in `.kiln/project.yml` (`aio_watchlist`), never across the whole core. Default list size 200–300 queries `[expert judgement, needs calibration]`.

### 1.4. Serper — interactive one-off lookups

The key already exists `[owner decision]`. Cost $0.30–1.00 per 1000, latency 1–2 seconds `[source: EVIDENCE.md#e12-data-apis-and-pricing]`. **Credits expire after 6 months** — which disqualifies Serper as a dormant source and rules it out as the default for batch work.

Division of labour: **Serper handles synchronous one-off checks while an agent is working; DataForSEO handles every batch.**

### 1.5. Autocomplete and People Also Ask

Priced the same as a base SERP call through DataForSEO Autocomplete `[source: EVIDENCE.md#e05-semantics-and-clustering]`. Yields long tail and live phrasing — the thing no keyword tool has.

**SEM-05 (BLOCK).** Autocomplete and PAA are collected **only through an intermediary provider**, never by direct scraping from our own addresses and never from behind a login. Grounds: in hiQ v. LinkedIn, logged-out scraping of public data was shielded from CFAA, but hiQ lost on breach of the User Agreement — meaning ToS binds you even without a login `[source: EVIDENCE.md#e05-semantics-and-clustering, EVIDENCE.md#e07-competitive-intelligence]`. The dividing line runs through the login and through who actually issues the request.

### 1.6. Forums and UGC

The value here is the wording of a pain point **before** the person converted it into a search query. Especially on topics whose measured volume is zero.

The economics are closed off: Reddit's official commercial API is $12,000/month, free tier 100 QPM `[source: EVIDENCE.md#e05-semantics-and-clustering, EVIDENCE.md#e08-trend-detection]`. The workable route is `site:reddit.com` through an ordinary SERP call.

**SEM-06 (INFO).** A query sourced from a forum carries `source=forum`, `is_verified=false` until confirmed per §2. Reconnaissance separately recorded that Reddit was unreachable by every direct route at the time of collection `[source: EVIDENCE.md#e02-practitioner-pulse]` — the module must degrade gracefully rather than crash.

### 1.7. LLM generation — hypotheses, not data

Cost ~$0 on a local model. Yields facets, synonyms, and phrasings aimed at query fan-out.

**This is not a source of semantics. It is a hypothesis generator.** See §2.

---

## 2. The `is_verified` Rule — P1 Applied to Semantics

> **SEM-07 (BLOCK).** A query with `is_verified=false` takes no part in content planning, does not enter the clusters of an active run, and does not affect priorities. It sits in the database as a hypothesis.

Verification is reached under either of two conditions:

| Condition                                                        | What it means                                                       |
| ---------------------------------------------------------------- | ------------------------------------------------------------------- |
| The query returned a non-empty SERP from the provider            | The query exists in reality; Google knows what to show for it       |
| The query appears in the project's GSC with non-zero impressions | People genuinely ask this, and we have already been surfaced for it |

Why this is a matter of principle rather than paperwork. A model will happily invent plausible queries that nobody has ever typed. Planning on such queries produces pages serving demand that does not exist — precisely the "pages created for something other than the reader's benefit" that the scaled content abuse policy targets (see `10-safety-gates.md`). The check costs $0.0006 per query.

This is a direct consequence of **P1**: a model's output is not a fact. The fact here is not the text of the query but the existence of a SERP for it.

**SEM-08 (INFO).** The share of hypotheses failing verification is logged as a quality metric for the generator. A persistently high share (`>50%` `[expert judgement]`) signals that the facet-generation prompt is detached from the niche, and is grounds for an amendment under `11-self-learning.md`.

---

## 3. Clustering

### 3.1. The roles of the two methods

| Method                             | Role                          | Why that role                                                                                                                                                                                                                                        |
| ---------------------------------- | ----------------------------- | ---------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| **SERP overlap**                   | **arbiter**                   | Reads the ranker's own decision. It sees that «як обрати кредитну картку» and «найкраща кредитна картка 2026» are served by one page, while «ягуар тварина» and «ягуар авто» are served by different ones. Neither lexis nor embeddings can see this |
| **Embeddings (bge-m3, local, $0)** | **pair pre-filter and dedup** | Cut obviously distant pairs before overlap is computed; collapse near-duplicates before we pay for them; work on queries that have no SERP yet                                                                                                       |

A cost point that is usually misread: comparing every pair is O(N²) **comparisons** but only N **API calls**. A SERP is fetched once per query; edges are computed locally. The embedding pre-filter exists to save CPU time on large cores, not money.

**SEM-09 (BLOCK).** The final "one page or two" decision is made on SERP overlap. Embeddings may never be the sole basis for merging or splitting clusters.

### 3.2. Thresholds

| Threshold                       | Setting     | When to use                                                             |
| ------------------------------- | ----------- | ----------------------------------------------------------------------- |
| 3 shared URLs in the top 10     | loose       | broad clusters, reconnaissance of a new niche                           |
| **4 shared URLs in the top 10** | **default** | the working setting `[source: practitioner consensus, EVIDENCE.md#e05-semantics-and-clustering]`     |
| 5+ shared URLs                  | strict      | competitive niches where thin pages spanning several intents do not win |

Comparing against the top 7 instead of the top 10 tightens the criterion without changing the numeric threshold — available as an alternative `serp_depth` setting.

**SEM-10 (BLOCK).** The threshold is a project parameter in `.kiln/thresholds.yml`, not a code constant. Grounds: the dominant defect across all clustering tools is **over-merging**, and it is worse in tools with a fixed threshold `[source: EVIDENCE.md#e05-semantics-and-clustering]`. This is consistent with **P10**: threshold numbers are calibrated locally and are not promoted into the shared doctrine without a separate PR.

**How to recognize over-merging in your own data.** Each of the following is grounds for raising the threshold:

- a single cluster contains queries of differing commercial intent (informational and transactional together);
- reading the cluster head by eye, it does not answer most of the cluster's queries;
- after publication the page picks up impressions for half the cluster and zero for the other half (visible in GSC after 4–8 weeks);
- the cluster contains queries on different cognitive axes (knowledge and output-seeking simultaneously).

### 3.3. Algorithm: centroid, not graph

**The graph form** — queries as vertices, an edge wherever `overlap >= threshold`, then connected components. It produces **chaining drift**: A is linked to B, B is linked to C, A and C have nothing in common with each other, yet all three land in one cluster. On large cores the cluster sprawls into meaninglessness.

**The centroid form (pivot)** — take the highest-priority unassigned query as the head, attach to **the head** everything that clears the threshold, repeat on the remainder. There is no drift, because every cluster member is compared against the head rather than against a neighbour. The result depends on traversal order, which is why the order is fixed and deterministic.

**SEM-11 (BLOCK).** Centroid clustering with deterministic sorting is used. The primary sort key is expected yield (§6), ties broken by `volume`, then lexicographically by `text_norm`. That last tiebreak exists so that two runs over the same data produce identical results: without it there is no way to tell SERP drift from implementation drift.

Every cluster has exactly one head (`is_head=true`), and it is the head that determines which page gets written. That is what is needed on the output side — not a pretty graph.

---

## 4. Storage: An Edge Graph, Not Clusters

> **SEM-12 (BLOCK).** Facts and edges are stored. Clusters are a derived quantity that is rebuilt and versioned. A cluster is never a primary record.

### 4.1. Data model

```
queries          id, text, text_norm, lang, geo, device,
                 volume, volume_source, volume_captured_at,
                 intent_commercial, intent_cognitive, intent_confidence,
                 source ENUM[gsc|ahrefs_csv|autocomplete|paa|forum|llm_hypothesis|manual],
                 is_verified BOOL,
                 first_seen, last_seen
                 UNIQUE(text_norm, geo, device, lang)

query_serps      query_id, fetched_at, engine, top_urls[],
                 serp_features[],          -- aio, paa, shopping, video, sitelinks, ...
                 has_aio, aio_cited_urls[],
                 ttl_expires_at

query_edges      query_a_id, query_b_id,   -- always a < b, stored once
                 serp_overlap SMALLINT,    -- number of shared URLs
                 embed_sim REAL,
                 computed_at
                 PRIMARY KEY (query_a_id, query_b_id)

cluster_runs     id, method, params, created_at, is_active
clusters         id, run_id, label, head_query_id, intent_commercial, intent_cognitive,
                 pillar_id,               -- FK to the pillar page grouping this cluster; NULL = standalone
                 pillar_source ENUM[declared|inferred]
cluster_members  cluster_id, query_id, membership_score, is_head

facets           id, cluster_id, question,
                 source ENUM[paa|autocomplete|llm|competitor],
                 is_covered, covered_by_url, covered_at

page_clusters    url, cluster_id, role ENUM[primary|secondary]
```

### 4.2. Why this shape

**The edge graph is the heart of the method, and `query_serps` is the heart of the storage.** One SERP run yields edges that remain usable until TTL expiry. Changing the threshold from 4 to 5, changing the algorithm, rebuilding after two thousand new queries are added — all of it is a local operation costing $0. Without an edge graph each of those operations would require a fresh round of API calls. This is the only design that survives growth of the core.

Note the direction of the dependency, because it decides what gets committed (§4.3): `query_edges` is **derived** from `query_serps` by set intersection, plus a locally computed embedding similarity. The observations are irreplaceable; the edges are reproducible. Retain the first, cache the second.

**`cluster_runs` with `is_active` gives versioning.** Clusters **must** be rebuilt, because the SERP changes. Versions exist so the diff can be surfaced: "query X moved from cluster A to cluster B, because Google stopped showing the same pages for it." Without versions that signal vanishes without trace — and it is **one of the earliest indicators of a SERP shift** available for free. It arrives before rankings drop, and long before traffic drops.

**SEM-13 (WARN).** Query drift between active clustering versions raises an alert. Threshold: `>10%` of a cluster's queries changed membership in a single rebuild `[expert judgement, needs calibration]`. The alert feeds the medium learning loop (**P9**).

**`facets` with `is_covered`** is the mechanism against blindness to query fan-out. The same table is where "content expansion" grows from: uncovered facets of an active cluster form a queue for improving an **existing** page, not a reason to create a new one.

### 4.3. Physical placement

State lives in `.kiln/` inside the project repository, as human-readable JSON and JSONL, exactly as the README and `adapter/SPEC.md` require. SQLite is permitted **only** as a derived cache: gitignored, and fully rebuildable from the committed files.

The dividing line is not size, it is **what money bought**. A SERP observation cost an API call and can never be recovered for that date once discarded. An edge is a set intersection over two observations plus a local embedding comparison, and recomputing the entire graph costs nothing but CPU.

| Artifact                                                | Where                                   | In git?                                                    |
| ------------------------------------------------------- | --------------------------------------- | ---------------------------------------------------------- |
| `queries`                                               | `.kiln/semantics/queries.jsonl`         | **yes** — the core itself                                  |
| `query_serps` (ranked URLs, SERP features, AIO fields)  | `.kiln/semantics/serps/<YYYY-MM>.jsonl` | **yes** — this is the paid artifact and a time series      |
| `cluster_runs`, `clusters`, `cluster_members`, `facets` | `.kiln/semantics/clusters.active.json`  | **yes** — what people read, and what must diff             |
| Merge and split decisions                               | `.kiln/semantics/decisions.jsonl`       | **yes** — human decisions, append-only, priceless          |
| `query_edges`, embedding vectors, similarity indexes    | `.kiln/cache/semantics.db` (SQLite)     | **no** — derived, gitignored, rebuilt by `edges.py`        |
| Raw SERP HTTP bodies                                    | `.kiln/cache/serp-raw/`                 | **no** — the parsed observation above is the retained form |

**Rationale, stated once for the whole doctrine.** A record that can be updated in place is not evidence. **P8** counts how often each rule fired and was overridden, and **P10** requires a rule change to carry dated evidence; both collapse if the underlying history can be silently rewritten. Git gives append-only history, review in a pull request, and `git revert` as a free rollback. A binary database gives none of the three.

Orders of magnitude, and why this is affordable: a 5,000-query core yields 12.5M candidate pairs, but the committed side is not the pairs. It is 5,000 query records plus roughly 5,000 SERP observations per refresh round, which is single-digit megabytes of JSONL per round and diffs cleanly. The derived edge graph is the large object: after a `cos >= 0.5` pre-filter, at an assumed 1% survival, ~125k edges on the order of ten megabytes. **The survival fraction is not established** — measure it on the pilot and record it here. That object is precisely the one that stays out of git, because `edges.py` reconstructs it from the committed observations on demand.

> **SEM-12a (BLOCK).** No artifact may exist only in the derived cache. Deleting `.kiln/cache/` in its entirety and running the rebuild must restore the project to a working state with no API spend. This is testable, and `doctor` tests it.

---

## 5. Intent: Two Axes

### 5.1. Why two

| Axis              | Values                                                    | What it determines                                                 |
| ----------------- | --------------------------------------------------------- | ------------------------------------------------------------------ |
| **A. Commercial** | informational / commercial / transactional / navigational | business value, monetization, type of call to action               |
| **B. Cognitive**  | knowledge-seeking / guidance-seeking / output-seeking     | the **format** of the page and its chance of entering an AI answer |

Axis B is taken from an academic primary source: Lichtenegger, Urman, Hannak, "A New Taxonomy of Web Search", CHI 2026, DOI 10.1145/3772318.3791050 `[source: EVIDENCE.md#e05-semantics-and-clustering]`. Its value is that it is **shared between search engine and chatbot** — the same query is labelled identically in both environments. For a system aiming at search and AI answer engines at once, that is exactly what is needed.

Practical consequence: **`output-seeking` is the type best protected against zero-click.** The user needs an artifact — a calculator, a template, a checklist, a table — not a paragraph of prose, and an AI answer cannot hand it over. All else equal, a cluster carrying this label moves up in priority.

### 5.2. Determined by SERP features, not by the text of the query

**SEM-14 (BLOCK).** Intent is determined by rules over SERP composition. Model classification of the query text is forbidden as the primary method.

The reason is the same as for SERP clustering: SERP composition is a reading of Google's decision, whereas text classification is a guess about a person's intention. For queries that sound identical Google may show fundamentally different results — and Google is right, the model is not.

Mapping rules `[method: EVIDENCE.md#e05-semantics-and-clustering; the specific signals are expert judgement, need calibration]`:

| SERP signal                                         | Axis A        | Axis B    |
| --------------------------------------------------- | ------------- | --------- |
| Shopping block, product ads on top                  | transactional | —         |
| Comparison listicles, "best/найкращі" in the top    | commercial    | guidance  |
| PAA + AIO + encyclopedic sources                    | informational | knowledge |
| Interactive tools, calculators in the top           | —             | output    |
| Sitelinks for a single brand, one domain dominating | navigational  | —         |
| Step-by-step guides, "як зробити"                   | informational | guidance  |

**SEM-15 (WARN).** Ambiguous cases go to an LLM arbiter with `intent_confidence` mandatorily recorded. Expected share of such cases is 10–15% `[source: estimate in EVIDENCE.md#e05-semantics-and-clustering, needs calibration]`. A share above 30% means the rules do not fit the niche — a signal for amendment under `11-self-learning.md`, not a licence to widen the model's role.

---

## 6. Prioritization in the Zero-Click Era

### 6.1. The formula

```
expected_clicks = volume × ctr_modifier(serp_features)
priority        = expected_clicks × commercial_value(intent) × winnability
```

Where:

- `volume` — from GSC (real impressions, preferred) or from the Ahrefs CSV export;
- `ctr_modifier` — a multiplier keyed to SERP composition, table below;
- `commercial_value` — the weight of the intent, set by the owner in `.kiln/project.yml`, **not in the doctrine**: only the business knows what a transaction is worth relative to an informational visit;
- `winnability` — an estimate of how breakable the top is, computed from our own SERP snapshots, defined in `03-competitors.md`.

**SEM-16 (BLOCK).** Prioritizing on `volume` alone is forbidden. Grounds: 68.01% of searches end without a click; per 1000 searches, 276 clicks reach the open web against 374 in 2024 `[source: SparkToro/Similarweb, EVIDENCE.md#e02-practitioner-pulse, EVIDENCE.md#e05-semantics-and-clustering]`. Volume has stopped predicting traffic, and prioritizing on it systematically overvalues precisely the queries an AI Overview eats.

### 6.2. CTR modifiers

| SERP composition                          | Modifier | Status                                                                   |
| ----------------------------------------- | -------- | ------------------------------------------------------------------------ |
| Clean organic                             | 1.00     | baseline                                                                 |
| **AI Overview present**                   | **0.40** | `[source: three independent measurements, spread 0.39–0.53 — see below]` |
| PAA block                                 | 0.90     | `[expert judgement, needs calibration]`                                  |
| Video block in the top                    | 0.90     | `[expert judgement, needs calibration]`                                  |
| Shopping/ads on top, informational intent | 0.85     | `[expert judgement, needs calibration]`                                  |
| Someone else's featured snippet           | 0.85     | `[expert judgement, needs calibration]`                                  |
| Navigational query for another brand      | 0.30     | `[expert judgement, needs calibration]`                                  |

**An honest caveat on the 0.40 figure.** Three sources give different values for the CTR drop when an AIO is present: −60% `[Ahrefs via EVIDENCE.md#e05-semantics-and-clustering]`; 15% → 8% of clicks `[Pew, 900 people, 68,879 searches, EVIDENCE.md#e01-geo-answer-engines]`, which is 0.53; and −61% `[Seer, 3119 queries, EVIDENCE.md#e04-search-console]`, which is 0.39. We take 0.40 as a conservative default, mark it a **prior**, and calibrate it against our own GSC data after 90 days of observation.

**SEM-17 (INFO).** Public position-based CTR curves are used only as priors for a cold start. From the moment a project accumulates 90 days of its own data, the curve is recomputed on its own impressions and clicks, and the local version takes precedence.

### 6.3. What to do with high-volume definitional queries

Deliberately **demote** them. Definitions and FAQs are the first thing an AI Overview takes. This does not mean "don't write them"; it means don't build the plan on them and don't measure success by them. Their role is to be the foundation of the entity graph and an anchor for internal linking (see `07-linking.md`), not a source of clicks.

---

## 7. Multilingual Work and Locales

**The doctrine is written in English; the work is not.** Keyword research, clustering and intent classification always run in the language and region of the target locale declared in `.kiln/project.yml`. Every SERP call must carry that locale's `gl`/`hl` (or the provider's equivalent). A core built against the wrong locale is invalid data, not merely imprecise — it describes a different market's demand. Clusters are never merged across locales.

### 7.1. Cost

A SERP is fetched for a specific **geo × lang** pair. That is a direct multiplier on budget: a project in Ukrainian and Russian within the Ukrainian region is ×2 on the entire SERP layer. None of the providers reviewed charges a separate rate for non-US SERPs `[source: EVIDENCE.md#e12-data-apis-and-pricing]`.

**SEM-18 (BLOCK).** Queries from different locales are never mixed in one cluster. The uniqueness key of a query includes `geo`, `lang`, `device`. Clustering always runs within a locale.

### 7.2. Locale parity

**SEM-19 (WARN).** A divergence of more than 10% in page count between locales signals a broken hreflang cluster `[expert judgement, needs calibration]`. This has already been observed on the pilot: the `/mfo/` section holds 169 Ukrainian URLs against 70 Russian `[internal observation, unpublished]`.

The parity check belongs to onboarding rather than semantics, but semantics must account for it: a cluster with a page in one locale and none in another enters the queue as a translation task, not as a task to write new text.

### 7.3. Tokenization

**SEM-20 (BLOCK).** Every operation over text length — normalization, dedup, word counts, n-grams — uses Unicode-aware tokenization. A direct application of **P5**.

The precedent that cost a wrong conclusion: `wc -w` does not split Cyrillic into words and reported the English locale as six times larger than the Ukrainian one when the two were at parity. A Unicode-correct counter inverted the finding `[internal observation, unpublished]`.

From the same root: `text_norm` normalization cannot rely on `\b` in regular expressions — that mechanism does not correctly identify word boundaries in Cyrillic.

---

## 8. Cost of a Run

Computed for DataForSEO Standard, $0.0006 per SERP, top 10, one locale.

| Core           | Expansion (autocomplete + PAA)    | SERP over the core | **Launch**       | TTL re-fetch, monthly |
| -------------- | --------------------------------- | ------------------ | ---------------- | --------------------- |
| 1,000 queries  | ~400–1,000 calls = $0.24–0.60     | $0.60              | **$0.85–1.20**   | ~$0.28                |
| 5,000 queries  | ~2,000–5,000 calls = $1.20–3.00   | $3.00              | **$4.20–6.00**   | ~$1.40                |
| 20,000 queries | ~8,000–20,000 calls = $4.80–12.00 | $12.00             | **$16.80–24.00** | ~$5.60                |

Re-fetch is computed on a TTL rule of 30 days for the priority top 20% of the core and 90 days for the rest: `0.2N + 0.8N/3 ≈ 0.47N` calls per month.

**AIO monitoring is a separate line.** A $2.00 per 1000 surcharge over the base price. A 200-query watchlist checked weekly: 800 calls × $0.0026 = **$2.08/month**.

**The locale multiplier** applies to every line. For two locales, everything doubles.

Embeddings, clustering, edge construction, rule-based intent assignment — **$0** (local `bge-m3` and pure computation).

**Design conclusion.** At these magnitudes, any heuristic aimed at saving SERP calls is premature optimization. The savings to chase are $500–1000/month subscriptions, not $0.0006 calls. Fetch the SERP for the whole core and cache it.

---

## 9. Relationship to Anti-Cannibalization

A direct consequence of **P6**: one page — one intent — one URL.

**SEM-21 (BLOCK).** A cluster has exactly one page with the role `primary`. Two or more `primary` pages on a cluster is a cannibalization state requiring resolution.

### 9.1. Three outcomes when mapping a cluster onto the corpus

| State                          | Action                                                               |
| ------------------------------ | -------------------------------------------------------------------- |
| Cluster with no page           | Into the writing queue, prioritized per §6                           |
| Cluster with one page          | Check uncovered facets → into the queue to improve the existing page |
| Cluster with two or more pages | Cannibalization → resolve via the decision tree below                |

### 9.2. When to split the cluster and when to merge the pages

The decision is made on 90 days of GSC data, not by eye `[source: EVIDENCE.md#e04-search-console, EVIDENCE.md#e06-internal-linking]`:

- **Intents inside the cluster differ** (axis A or B has diverged; the two pages take impressions on non-overlapping subsets of queries) → this is **over-merging**; split the cluster, keep both pages, and separate them by content and anchors.
- **One intent, a clear leader** (one page collects the overwhelming majority of the cluster's clicks) → 301 to the leader.
- **One intent, both pages valuable** (each has its own audience or its own funnel stage) → merge, keeping the stronger URL.

The mechanics of cannibalization detection, `flip_rate` thresholds, and the "one anchor phrase — one URL" rule live in `07-linking.md`. Semantics only supplies the input here: the cluster and its membership.

**SEM-22 (BLOCK).** Merges, redirects and page deletions are executed only after human confirmation. A direct application of **P11**: these are irreversible actions on an existing corpus.

**SEM-23 (WARN).** Automatic merging of clusters larger than 20 queries requires human confirmation `[expert judgement, needs calibration]`. The threshold exists because the cost of an over-merging error grows with cluster size, and on the pilot the clusters are large.

### 9.3. Pillar grouping and measurement independence

Clusters are not statistically independent of one another. Two clusters hanging off the same pillar page share a link path, and `07-linking.md` routes all cross-cluster movement through the pillar (§4 of that file). A change applied to one of them propagates to the other through that shared node.

This matters because `07-linking.md` §14.3 proposes running internal-linking waves in parallel across "unrelated" clusters to get through a large corpus faster. That plan is only valid if unrelatedness is a recorded fact rather than an assumption, which is why `pillar_id` exists in the model above.

> **SEM-25 (BLOCK).** Two clusters sharing a non-NULL `pillar_id` are **not independent** and must not be assigned to different arms of the same controlled comparison, nor to concurrent linking waves that are to be measured separately. Either place them in the same arm, or measure them jointly and report a single combined effect.

`pillar_source` records how the grouping was established. `declared` means a human mapped the cluster to a pillar during onboarding or planning. `inferred` means the system derived it from the existing link graph. Inferred groupings are usable for the **exclusion** above — treating clusters as related when they might not be is the safe direction of error — but must not be used to claim independence. A cluster with `pillar_id` NULL and `pillar_source` `inferred` means only that no pillar was found, not that none exists, and it cannot be certified independent until a human confirms it.

---

## 10. Facets and Query Fan-Out — an Important Distinction

AI Mode decomposes a user's question into sub-queries and runs them in parallel. This is confirmed by Google's own blog, not merely by practitioner analyses `[source: Google blog "AI in Search", PDF "AI Overviews and AI Mode", via EVIDENCE.md#e05-semantics-and-clustering]`. Google does not publish the exact number of sub-queries; analyses cite estimates of 8–16.

**What follows from this.** The planning unit is neither a keyword nor a cluster but a **set of facets of a topic**. A page must cover the facets that fan-out will generate: comparisons, conditions, prices, limitations, "who is this for", "what if it doesn't fit".

**What does NOT follow from this.**

> **SEM-24 (BLOCK).** A facet map is a tool for verifying the **completeness of a single page**. It is not an instruction to slice text into short blocks for LLMs, and it is not grounds for creating a separate page per facet.

Grounds: chunking content into bite-sized blocks for language models was criticized directly by Google (2026-01-08) `[source: EVIDENCE.md#e03-ai-detection-and-humanization]`, and creating many similar pages out of one cluster is a doorway `[source: EVIDENCE.md#e13-policy-and-risk]`. Both errors grow naturally out of a misread fan-out, which is why the prohibition sits here and not only in `10-safety-gates.md`.

The splitting threshold is unchanged: a separate page appears if and only if SERP overlap says Google serves that facet with a separate page.

---

## 11. Who Does What

| Stage                            | Code        | Agent    | Human              |
| -------------------------------- | ----------- | -------- | ------------------ |
| GSC export, CSV import           | ✅          |          |                    |
| Normalization, dedup, embeddings | ✅          |          |                    |
| Facet and hypothesis generation  |             | ✅       |                    |
| SERP fetch, cache                | ✅          |          |                    |
| Hypothesis verification          | ✅          |          |                    |
| Edge construction                | ✅          |          |                    |
| Clustering                       | ✅          |          |                    |
| Rule-based intent                | ✅          |          |                    |
| Intent under ambiguity           |             | ✅       |                    |
| Prioritization                   | ✅          |          |                    |
| Mapping onto the corpus          | ✅          |          |                    |
| Merging clusters > 20 queries    |             |          | ✅ confirms        |
| 301 / page-merge decision        |             | proposes | ✅ approves        |
| Threshold calibration            | ✅ computes | proposes | ✅ approves via PR |

---

## 12. Forbidden

| Prohibition                                                   | Grounds                                                                   |
| ------------------------------------------------------------- | ------------------------------------------------------------------------- |
| Planning content on unverified queries                        | SEM-07, **P1**                                                            |
| Prioritizing by search volume                                 | SEM-16; volume does not predict traffic at 68% zero-click                 |
| Storing clusters as the primary record                        | SEM-12; destroys the ability to re-cluster and loses the drift signal     |
| Using graph clustering                                        | SEM-11; chaining drift                                                    |
| Deciding "one page or two" on embeddings                      | SEM-09; embeddings cannot see intent overlap that exists only in the SERP |
| Classifying intent from query text with a model               | SEM-14; a guess in place of reading Google's decision                     |
| A fixed overlap threshold in code                             | SEM-10; the industry's principal defect is over-merging                   |
| Mixing locales in one cluster                                 | SEM-18                                                                    |
| Scraping autocomplete and PAA directly or from behind a login | SEM-05; hiQ lost on ToS even without a login                              |
| Requesting AIO across the whole core                          | SEM-04; 4–15× cost increase                                               |
| Creating a separate page per facet                            | SEM-24; doorway                                                           |
| Chunking text "for LLMs"                                      | SEM-24; criticized by Google 2026-01-08                                   |
| Automatically merging or redirecting pages                    | SEM-22, **P11**                                                           |
| `wc -w` and `\b` on Cyrillic                                  | SEM-20, **P5**                                                            |

---

## 13. Layer 2 Script Specifications

Every script is autonomous: it knows nothing about any particular site, reads files and writes files, and makes no network calls beyond those explicitly stated. The SERP provider is invoked by a separate wrapper; the scripts receive snapshots that have already been collected.

### 13.1. `normalize.py`

Normalization and dedup before spending money on SERPs.

- **Input:** `queries.raw.jsonl` — `{"text", "source", "lang", "geo", "device", "volume"?, "volume_source"?, "volume_captured_at"?}`
- **Output:** `queries.norm.jsonl` — the same fields plus `{"text_norm", "dedup_group", "is_verified": false}`
- **Does:** Unicode NFC normalization, whitespace and case folding, local `bge-m3` embeddings, collapsing of near-duplicates at `cos > 0.95`, dropping of records with no text.
- **Does not:** make network calls, decide intent, or filter by volume (that is a prioritization decision, not a normalization one).

### 13.2. `edges.py`

Construction of the edge graph.

- **Input:** `queries.norm.jsonl` + `serps.jsonl` — `{"query_id", "fetched_at", "top_urls": [...], "serp_features": [...], "has_aio": bool, "aio_cited_urls": [...]}`
- **Output:** `edges.jsonl` — `{"a": id, "b": id, "serp_overlap": int, "embed_sim": float, "computed_at": iso}`, always `a < b`
- **Does:** pre-filters pairs at `embed_sim >= 0.5`, counts the intersection of `top_urls` for survivors.
- **Parameters:** `--prefilter` (default 0.5), `--serp-depth` (10 or 7).

### 13.3. `cluster.py`

Centroid clustering on SERP overlap.

- **Input:** `queries.norm.jsonl`, `edges.jsonl`, `priorities.jsonl` (optional, for sorting)
- **Output:** `clusters.json`:
  ```json
  {
    "run_id": "2026-08-07T10:00:00Z",
    "method": "centroid",
    "params": { "threshold": 4, "serp_depth": 10, "prefilter": 0.5 },
    "clusters": [
      {
        "id": "c-001",
        "head_query_id": "q-123",
        "label": "кредитна картка порівняння",
        "members": [
          { "query_id": "q-123", "is_head": true, "membership_score": 1.0 },
          { "query_id": "q-456", "is_head": false, "membership_score": 0.7 }
        ]
      }
    ]
  }
  ```
  `membership_score` = `serp_overlap / serp_depth`.
- **Does:** deterministic sorting, attachment to the head, recording of a new run.
- **Additionally:** given `--diff-against <prev_run.json>` it emits `cluster_drift.json` — the list of queries that changed membership, for SEM-13.

### 13.4. `intent.py`

Two-axis intent labelling from SERP composition.

- **Input:** `serps.jsonl`, `rules.yml` (the table from §5.2, editable at project level)
- **Output:** `intents.jsonl` — `{"query_id", "intent_commercial", "intent_cognitive", "intent_confidence": 0..1, "matched_rules": [...], "needs_arbitration": bool}`
- **Does:** matches `serp_features` against the rules, computes confidence as the share of concordant signals, sets `needs_arbitration=true` on conflicting signals or at `intent_confidence < 0.5`.
- **Does not:** call a model. Arbitration is the agent's job; the script only flags.

### 13.5. `priority.py`

Computation of expected yield and priority.

- **Input:** `queries.norm.jsonl`, `serps.jsonl`, `intents.jsonl`, `ctr_curve.json` (local curve or prior), `project.yml` (`commercial_value` weights), `winnability.jsonl` (optional, from `03-competitors.md`)
- **Output:** `priorities.jsonl` — `{"query_id", "expected_clicks", "ctr_modifier", "applied_modifiers": [...], "commercial_value", "winnability", "priority", "curve_source": "local"|"prior"}`
- **Does:** applies the modifiers from §6.2, multiplies, sorts.
- **Important:** `curve_source` is mandatory in the output — reports must show whether the figures were computed on the project's own data or on priors.

### 13.6. Adjacent scripts

Not part of semantics, but consumers of its output, with contracts defined in neighbouring sections: cannibalization detection and the internal link graph — `07-linking.md`; `winnability` computation and content gap — `03-competitors.md`; facet routes into the content plan — `04-trends-and-plan.md`.

---

## 14. Contradictions and Tensions with `00-principles.md`

Recorded honestly, as **P15** requires.

### 14.1. Resolved tensions

**Thresholds in the doctrine vs. P10.** This section ships numeric defaults (overlap threshold 4, pre-filter 0.5, AIO modifier 0.40). **P10** requires thresholds to be calibrated locally and to live in `.kiln/thresholds.yml`. There is no contradiction: the doctrine supplies starting values and the obligation to calibrate them; the local file overrides them. Promoting a local value back into the doctrine requires a separate PR.

**Collecting AIO data vs. P12.** **P12** rejects GEO as a separate discipline with special markup. Here we collect `has_aio` and `aio_cited_urls`. This is not optimization for AI but **measurement**: without those fields it is impossible to compute the CTR modifier or to understand why a query yields no clicks despite a good position. Measuring is permitted and necessary; adjusting markup is not.

**Facets vs. the ban on chunking.** The most dangerous spot in this section. A facet map naturally invites two forbidden practices — slicing text into blocks and creating a page per facet. That is exactly why the prohibition is stated explicitly in SEM-24 and repeated in §12.

### 14.2. Unresolved

**The survival rate of pairs after pre-filtering is not established.** The real size of the graph depends on it, and therefore so does the justification for §4.3. Measure it on the pilot's first run and record it here.

**CTR modifiers other than AIO are pure judgement.** Not one of them is backed by measurement. They are flagged and are to be replaced with local values after 90 days of data. Until then, prioritization carries a systematic error of unknown magnitude, and reports must expose that through `curve_source`.

---

## 15. Sources

| Reference                                                  | What was taken                                                                                                                    |
| ---------------------------------------------------------- | --------------------------------------------------------------------------------------------------------------------------------- |
| `EVIDENCE.md#e05-semantics-and-clustering`                         | the SERP clustering method, thresholds 3/4/5, centroid vs. graph, storage schema, CHI 2026 taxonomy, query fan-out, run economics |
| `EVIDENCE.md#e12-data-apis-and-pricing`                            | DataForSEO/Serper/SerpApi pricing, the AIO surcharge, GSC limits, embedding costs, the default stack                              |
| `EVIDENCE.md#e04-search-console`                       | GSC limits and quirks, anonymization, the 16-month window, CTR curves, the Seer measurement                                       |
| `EVIDENCE.md#e01-geo-answer-engines`                           | the Pew measurement of CTR under AIO, instability of generative SERPs                                                             |
| `EVIDENCE.md#e02-practitioner-pulse`                           | zero-click at 68.01%, 276 clicks per 1000 searches, Reddit unreachable                                                            |
| `EVIDENCE.md#e03-ai-detection-and-humanization`                    | Google's criticism of chunking content (2026-01-08)                                                                               |
| `EVIDENCE.md#e06-internal-linking`           | the cannibalization decision tree on GSC data                                                                                     |
| `EVIDENCE.md#e07-competitive-intelligence`                             | the legal frame for scraping, the dividing line at login                                                                          |
| `EVIDENCE.md#e13-policy-and-risk`                   | doorway abuse arising from naive clustering                                                                                       |
| `[internal observation, unpublished]`                                    | locale asymmetry in `/mfo/`, 169 uk against 70 ru                                                                                 |
| `[internal observation, unpublished]`                                 | the `wc -w` precedent on Cyrillic                                                                                                 |
| CHI 2026, DOI 10.1145/3772318.3791050                      | the cognitive intent axis                                                                                                         |
| Google blog "AI in Search", PDF "AI Overviews and AI Mode" | query fan-out as a primary source                                                                                                 |
| SparkToro/Similarweb via Search Engine Land                | zero-click at 68.01% for January–April 2026                                                                                       |
