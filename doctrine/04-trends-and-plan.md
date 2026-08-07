# 04 — Trends and the Content Plan

> Subordinate to `00-principles.md`. On conflict, the principles file wins.
> Principles governing this section: **P0** (value lies in rejection), **P1** (evidence-first),
> **P2** (pace equals verification throughput), **P13** (unique value is mandatory),
> **P9** (three learning loops).

**Version:** 0.1.0 · **Date:** 2026-08-07 · **Revision:** every 90 days
**Intelligence base:** `EVIDENCE.md#e08-trend-detection`, `EVIDENCE.md#e14-content-operations`

---

## 0. What this module does and what it does not

This module answers exactly one question: **what to write next, and when.**

It does not answer "how to write it" (→ `05-writing-core.md`), "should this be written at all
given a competing page already exists" (→ `07-linking.md`, cannibalisation), or "will this clear
review" (→ `06-review-lenses.md`).

The module's output is a queue in `.kiln/plan.yml`. Anything that does not reach the queue does
not get written. The queue is hard-capped from above by verification throughput (**TRD-15**),
so by construction this module is not an idea generator but a **filter**: it always discards more
than it admits.

Honest boundaries to keep in mind while reading the thresholds below:

- We have no absolute search volumes — everything runs on relative indices.
- TikTok and Instagram are not covered: no commercial Research API exists.
- Seasonal publishing lead time is **practitioner consensus, not a measured quantity**.
- Every figure concerning the freshness of AI citations comes from industry write-ups **with no
  disclosed methodology**; they serve as priors for initial configuration, not as facts.

---

## 1. Signal sources

Ordered by priority. The first three are mandatory; the rest are switched on by project profile.

| #   | Source                                | Cost                               | Limits                                                                       | Legal standing                    | What it yields                                                                    |
| --- | ------------------------------------- | ---------------------------------- | ---------------------------------------------------------------------------- | --------------------------------- | --------------------------------------------------------------------------------- |
| 1   | **GSC** — Search Analytics + BigQuery | $0                                 | 25,000 rows/request; 50,000 rows / search type / site / day; 16-month window | first-party data                  | real demand, seasonality, the hourly newsjacking window                           |
| 2   | **DataForSEO Google Trends**          | $0.0027/task Standard; $0.011 Live | 5 keywords per task; $50 minimum deposit                                     | intermediary absorbs the ToS risk | external demand, rising, breakout, YoY                                            |
| 3   | **GDELT** — DOC 2.0 + GKG             | $0                                 | no hard quotas                                                               | research-grade, open              | news spikes across 100+ languages, volume-over-time, theme rollups                |
| 4   | Reddit API, free tier                 | $0                                 | 100 QPM (OAuth), ~10,000 requests/month                                      | official API                      | the phrasing of a pain point **before** a query exists; upvotes as a demand proxy |
| 5   | Hacker News — Algolia + Firebase      | $0                                 | 10,000 requests/hour per IP                                                  | public API                        | tech / dev / SaaS / AI niches only                                                |
| 6   | YouTube Data API                      | $0                                 | 10,000 units/day; **search costs 100** → ~100 searches/day                   | official API                      | video demand, a narrow daily slice                                                |
| 7   | PatentsView / USPTO ODP               | $0                                 | —                                                                            | open data                         | very early and very noisy signal for B2B and deep tech                            |
| 8   | Google Trends API (alpha)             | $0 once an application is approved | ~10,000 points per request → **~5 terms/day** at DAY resolution              | official                          | `searchInterest` (absolute values) plus a scale that is comparable across queries |

### Permanently excluded from Kiln

| Source                              | Reason                                                                                      |
| ----------------------------------- | ------------------------------------------------------------------------------------------- |
| TikTok / Instagram                  | no commercial Research API exists; only grey scraping remains                               |
| Google News RSS                     | ToS: personal, non-commercial use only; robots explicitly forbidden                         |
| pytrends and direct Trends scraping | repository archived 2025-04-17; scraping breaches ToS; HTTP 429 after 10–15 requests per IP |
| Exploding Topics / Glimpse          | UI products with no serious API; we take their logic, not their subscription                |

**Why the Trends API sits eighth rather than first.** It was announced on 2025-07-24 and a year
later remains an application-gated alpha with no self-serve registration and no public GA
timeline. It cannot be built upon. Even with approval, a quota of roughly 5 terms per day makes
it a tool for **validating a shortlist**, not for scanning. Its one genuinely unique offering is
the `searchInterest` field with absolute values and a scale that is comparable across queries —
the web Trends interface normalises 0–100 _within_ each query, so two queries cannot be spliced
together.

---

## 2. Why archiving is mandatory and fetch-on-demand is a mistake

This is an architectural requirement, not an optimisation. It follows from two properties of GSC.

**Hourly data lives for 8 days, then disappears permanently.** Miss it and it is gone; nothing
recovers it. The hourly slice is precisely our detector for the newsjacking window — it shows
whether a fresh publication is accumulating impressions over hours rather than days.

**Sixteen months is deletion, not an archive.** Data older than 16 months is destroyed
irreversibly. For YoY seasonality, 16 months is exactly one cycle plus four months, which means
**there is nothing to compare against**. To hold three years of history two years from now, you
must start accumulating on the day of onboarding.

Hence the rule: harvesting runs **daily and unconditionally**, whether or not anyone needs the
data today. A skipped harvest is not a delayed task — it is an unrecoverable loss.

| Rule       | Statement                                                                                                                           | Enforcement                                                                                                                      |
| ---------- | ----------------------------------------------------------------------------------------------------------------------------------- | -------------------------------------------------------------------------------------------------------------------------------- |
| **TRD-01** | **Daily harvesting of the GSC hourly slice is mandatory.** A gap of more than 7 consecutive days means the window is lost for good. | `BLOCK` on the plan run: with an archive gap > 7 days, the `NEWSJACK` route is disabled until 30 days of continuity are restored |
| **TRD-02** | **BigQuery bulk export is connected on the day of onboarding**, even if seasonality will not be needed for another year.            | `WARN` at onboarding; the accumulation start date is recorded in `.kiln/project.yml`                                             |
| **TRD-03** | A series containing a gap longer than 14 days **is not used** for seasonality calculation or de-seasonalization.                    | `BLOCK` on the `SEASONAL` route for the affected clusters                                                                        |

---

## 3. Trend scoring

### 3.1 Why median and MAD rather than mean and sigma

The classical z-score `(x − mean) / stddev` breaks on search series for three reasons, and all
three occur simultaneously.

1. **Standard deviation is inflated by the very outliers you are hunting.** The spike you want to
   catch sits inside the baseline window and raises σ, thereby suppressing its own z-score. The
   stronger the anomaly, the worse it is detected — the exact inverse of the desired behaviour.
   The robust replacement (median + MAD) does not react to outliers: shifting the median requires
   corrupting half the points.
2. **The series are not normal** — heavy tails and seasonality. De-seasonalization therefore runs
   **before** scoring, and the z-score is computed on the residuals.
3. **Noise masquerades as signal** over short windows. This is treated by comparing anomaly
   strength in a short window against anomaly strength in a longer overlapping window (both on EWMA).

The constant `1.4826` in the formula below rescales MAD to the standard deviation of a normal
distribution — it exists so that the familiar thresholds of 2 and 3 retain their meaning.

### 3.2 Formulas

```
# step 0 — de-seasonalization (requires ≥2 full cycles of history)
x_t = raw_t / seasonal_index(week_of_year)

# step 1 — robust z over a rolling 90-day window
z(t)       = (x_t − median_90d) / (1.4826 × MAD_90d)

# step 2 — auxiliary components
growth(t)  = (x_t / x_{t−28d}) − 1          # 4-week growth
accel(t)   = z_7d(t) − z_28d(t)             # acceleration, both windows on EWMA
sources(t) = count of independent sources where z ≥ 2
season(t)  = |deviation from the seasonally expected value|

# step 3 — final score
TrendScore = 0.35·norm(z)
           + 0.25·norm(accel)
           + 0.25·(sources / max_sources)
           + 0.15·norm(season)
```

The weights are starting values, subject to calibration against the project's historical data,
and they live in `.kiln/thresholds.yml` as local settings (principle P10: thresholds are
calibrated locally and are not promoted into the shared doctrine without a separate PR).

**The `sources` component is load-bearing.** A lone spike in a single source does not pass by
default, however large it may be. This follows directly from P1: a signal from one place is not
a fact about the world.

### 3.3 Thresholds

| Threshold                             | Meaning               | Action                                     | Provenance                                 |
| ------------------------------------- | --------------------- | ------------------------------------------ | ------------------------------------------ |
| `z ≥ 2.0`                             | candidate             | enters the confirmation queue              | anomaly-detection practice (~5% of points) |
| `z ≥ 3.0`                             | strong signal         | prioritised in the queue                   | practice (~0.135% of points beyond 3σ)     |
| `sources ≥ 2`                         | **mandatory**         | otherwise discarded as noise               | expert judgement, requires calibration     |
| `persistence ≥ 3 days`                | confirmation          | a one-day spike is noise                   | expert judgement, requires calibration     |
| `persistence ≥ 1 day` + `sources ≥ 3` | news exception        | bypasses the three-day rule for QDF events | expert judgement, requires calibration     |
| `TrendScore ≥ 0.65`                   | into the content plan | —                                          | expert judgement, requires calibration     |
| `TrendScore 0.45–0.65`                | watchlist             | re-evaluated daily                         | expert judgement, requires calibration     |
| `TrendScore < 0.45`                   | discarded             | with the reason recorded                   | expert judgement, requires calibration     |

Every threshold marked "expert judgement" is, on the first run against a new project, **written
to the log together with the observed distribution of values**, so that after 90 days it can be
calibrated from data rather than from intuition.

| Rule       | Statement                                                                                       | Enforcement                                       |
| ---------- | ----------------------------------------------------------------------------------------------- | ------------------------------------------------- |
| **TRD-04** | The z-score is computed **only** robustly (median + MAD) and **only** after de-seasonalization. | `BLOCK` on any use of the score                   |
| **TRD-05** | A trend with `sources = 1` never enters the plan, at any value of z.                            | `BLOCK`                                           |
| **TRD-06** | When a trend is discarded, the reason and all score components are written to the log.          | `WARN`; without the log there is no learning (P8) |

---

## 4. The breakout branch: "no history" is a division by zero

Google flags growth above 5000% as `Breakout`. In practice this is not a "super-trend" but a
housekeeping label: **volume was previously near zero, so no exact percentage can be computed.**
Scoring that with the same formula used for growth from 100 to 400 is a methodological error —
the robust z-score has no base in that situation, `MAD_90d` approaches zero, and the denominator
explodes.

A separate branch activates when either condition holds:

```
if history_points < 30  OR  the source flags Breakout:
    TrendScore = 0.6·(sources / max_sources)
               + 0.4·norm(velocity_since_first_seen)
    hard requirement: sources ≥ 2
```

Here `velocity_since_first_seen` is growth rate measured from the moment of first observation,
not against a historical base that does not exist. Statistics are replaced by **cross-source
confirmation**: absent history, the only evidence that the signal is real is that independent
observers see it too.

| Rule       | Statement                                                                                                                      | Enforcement |
| ---------- | ------------------------------------------------------------------------------------------------------------------------------ | ----------- |
| **TRD-07** | At `history_points < 30` the robust z **is not computed**. Applying the primary formula is a calculation error, not a warning. | `BLOCK`     |
| **TRD-08** | For the breakout branch, `sources ≥ 2` is a hard requirement with no exceptions, including the news route.                     | `BLOCK`     |

---

## 5. Four routes into the content plan

A trend that clears the gate must be classified into exactly one route. An unclassified trend
does not enter the plan.

### NEWSJACK

| Parameter           | Value                                                                                             |
| ------------------- | ------------------------------------------------------------------------------------------------- |
| **Entry condition** | GDELT spike + confirmation by search demand + **topical fit with the site**                       |
| **Urgency**         | 24–48 hour window                                                                                 |
| **Artifact**        | short piece, takes precedence over the queue                                                      |
| **Success check**   | hourly GSC: if the publication gains no impressions within the first 24 hours, the window is gone |

It works when the topic falls under query-deserves-freshness (a confirmed demand spike exists),
the site holds topical authority, and publication ships within the first 24–48 hours. It produces
garbage when the spike exists only on social with no search confirmation, when the topic is
unrelated to the site, and when publication ships on day four.

**No direct research on newsjacking effectiveness exists** — this is a zone without an evidence
base. The conditions above are derived from QDF mechanics, not measured.

| Rule       | Statement                                                                                     | Enforcement                                                                                                                                    |
| ---------- | --------------------------------------------------------------------------------------------- | ---------------------------------------------------------------------------------------------------------------------------------------------- |
| **TRD-09** | `NEWSJACK` without topical fit to the project profile is forbidden, however strong the spike. | `BLOCK`. Rationale: off-topic content unrelated to the publisher's business is one of eight documented patterns that fell to algorithm updates |
| **TRD-10** | A `NEWSJACK` piece that gains no impressions within 24 hours is **closed**, not reworked.     | `WARN`; continuing work is a loss, not an investment                                                                                           |

### SEASONAL

| Parameter           | Value                                                       |
| ------------------- | ----------------------------------------------------------- |
| **Entry condition** | seasonal pattern confirmed by **≥2 full cycles** of history |
| **Urgency**         | deadline `publish_by = peak_week − lead_time`               |
| **Artifact**        | planned article, or an update to an existing one            |
| **Success check**   | ranking before the climb begins, not at the peak            |

```
peak_week = median week of maximum across years
lead_time = project parameter   # NOT a constant
publish_by = peak_week − lead_time
```

**`lead_time` is a parameter, not a constant, and this matters.** 2026 practice converges on
"3–6 months for competitive terms", but **no specific study of "N weeks before the peak" exists**.
It is consensus, not a measured result. The starting value comes from `.kiln/thresholds.yml`
(recommended start: 12 weeks for medium competition, 20 for high) and is calibrated against
outcomes: after the first cycle, measure how many weeks before the peak the page actually reached
the top, and correct the parameter from project data.

| Rule       | Statement                                                                                | Enforcement            |
| ---------- | ---------------------------------------------------------------------------------------- | ---------------------- |
| **TRD-11** | `lead_time` may not be hard-coded in source or in a prompt. Only `.kiln/thresholds.yml`. | `BLOCK` at code review |

### EMERGING

| Parameter           | Value                                                         |
| ------------------- | ------------------------------------------------------------- |
| **Entry condition** | breakout or zero history, `sources ≥ 2`, persistence ≥ 7 days |
| **Urgency**         | 2 weeks                                                       |
| **Artifact**        | new beachhead page for the growing topic                      |
| **Success check**   | indexation and first impressions within 30 days               |

### REFRESH

| Parameter           | Value                                                                                                                                                 |
| ------------------- | ----------------------------------------------------------------------------------------------------------------------------------------------------- |
| **Entry condition** | existing page + rising interest **OR** median age of cited sources above the type threshold **OR** loss of an AI citation **OR** an age-based trigger |
| **Urgency**         | per the cadence of the content type                                                                                                                   |
| **Artifact**        | update to an existing URL — **not a new page**                                                                                                        |
| **Success check**   | re-indexation within 1–2 weeks, position trend over 3–8 weeks                                                                                         |

| Rule       | Statement                                                                                                            | Enforcement                                                    |
| ---------- | -------------------------------------------------------------------------------------------------------------------- | -------------------------------------------------------------- |
| **TRD-12** | If one of our URLs already serves the intent, the route can **only** be `REFRESH`. Creating a new page is forbidden. | `BLOCK`. Grounds: principle P6 — one page, one intent, one URL |

---

## 6. Freshness is the age of cited sources, not the publication date

The most under-exploited idea in the entire intelligence base: **a page can be simultaneously new
and stale.** Published yesterday, citing data from the year before last — for both the reader and
the answer engine it is out of date, whatever the timestamp says.

Hence a metric almost nobody computes, and which costs next to nothing:

```
source_age_median(page) = median( today − published_at(source) )
                          across all external sources cited on the page
```

Computed daily across the whole corpus. A page citing sources older than its own update cadence
enters the `REFRESH` queue — **even if traffic has not dropped**. This is a leading indicator of
falling out of AI citation pools, which places it in the medium learning loop (P9), not the slow one.

### Cadence by content type

| Content type                     | Update cadence | `source_age_median` threshold |
| -------------------------------- | -------------- | ----------------------------- |
| Prices, comparisons, market data | monthly        | 60 days                       |
| Regulation and compliance        | quarterly      | 120 days                      |
| How-to guides                    | semi-annually  | 240 days                      |
| Definitions and frameworks       | annually       | 400 days                      |

The threshold values are expert judgement, derived from the reported half-life of citations by
type (6–8 weeks for market data, ~3 months for regulation, ~6 months for how-to, ~12 months for
definitions). **The underlying figures come from industry write-ups with no disclosed methodology**
and serve as an initial configuration subject to calibration.

| Rule       | Statement                                                                                                                                                                      | Enforcement                                                                                                                |
| ---------- | ------------------------------------------------------------------------------------------------------------------------------------------------------------------------------ | -------------------------------------------------------------------------------------------------------------------------- |
| **TRD-13** | `source_age_median` is computed daily for every published page and stored in `.kiln/corpus.json`. Exceeding the type threshold is an automatic entry into the `REFRESH` queue. | `WARN`, escalating to `BLOCK` on new publications in the cluster if the share of overdue pages in that cluster exceeds 40% |

The escalation in the second column exists because of P0: if the corpus rots faster than we repair
it, writing new material increases the debt rather than the asset.

---

## 7. The refresh loop

### 7.1 Update priority

```
OpportunityScore = TrafficPotential × BusinessValue × EffortEfficiency
```

- **TrafficPotential** — current traffic, position (top 10 / second page / deeper), query volume
- **BusinessValue** — funnel stage (bottom outranks top), historical conversion, strategic weight
- **EffortEfficiency** — existing external links, quality of the current text, estimated effort

### 7.2 Four buckets

| Bucket                  | Signals                             | Action                                               | Human involvement                                  |
| ----------------------- | ----------------------------------- | ---------------------------------------------------- | -------------------------------------------------- |
| **Quick Wins**          | good positions + onset of decline   | update the numbers, fix links, title, meta           | standard review                                    |
| **Competitive Threats** | a competitor recently gained ground | gap analysis, fill what is missing, add our own data | standard review                                    |
| **Foundation Rebuilds** | high-volume term underperforming    | full rework, new structure, new angle                | **approval mandatory**                             |
| **Consolidation**       | cannibalisation                     | merge thin pieces, redirects, rewrite internal links | **approval mandatory** (P11: irreversible actions) |

### 7.3 Triggers

**By age:** 6 months — correct the numbers; 12 — competitive gap analysis; 18 — assess for full
refresh; 24+ — rewrite or delete.

**By performance:** traffic decline over 3 months → urgent refresh; a competitor overtakes us on a
key term → competitive refresh; **loss of an AI citation → freshness refresh**.

Loss of an AI citation is a standalone trigger, equal in standing to a traffic drop rather than
derived from it. The reason: citation disappears before traffic sags, making it an early signal.
The signal originates in the GEO module (`09-geo.md`), which maintains a fixed prompt set.

### 7.4 Honest update labelling

| Rule       | Statement                                                                                                                                                                   | Enforcement                     |
| ---------- | --------------------------------------------------------------------------------------------------------------------------------------------------------------------------- | ------------------------------- |
| **TRD-14** | The update date changes **only** on a substantive edit. A cosmetic change (reordered paragraphs, synonyms, an added empty section) accompanied by a date bump is forbidden. | `BLOCK` on publishing a refresh |

The rationale is direct: date manipulation is named by Google among the markers of unreliable
content. There is an additional technical risk — a machine-estimated date derived from document
content, anchors and related documents exists, so a divergence between the stamped date and the
substantive one is detectable.

The minimum substantiveness threshold for an edit is fixed in `.kiln/thresholds.yml`; absent
calibration, the starting requirement is that the edit touches claims about the world (figures,
terms, sources), not merely phrasing.

---

## 8. The content plan as an artifact

The file `.kiln/plan.yml` is the single source of truth about what gets written. Anything not in
it does not exist as far as the pipeline is concerned.

```yaml
version: 1
generated_at: 2026-08-07T09:00:00Z
project: example.com

capacity: # see §9 — computed, never entered by hand
  review_hours_per_week: 10 # from .kiln/project.yml
  hours_per_item: 1.75 # calibrated from actual review logs
  max_wip: 5 # floor(review_hours_per_week / hours_per_item)
  current_wip: 4

queue:
  - id: TRD-2026-0814
    route: SEASONAL # NEWSJACK | SEASONAL | EMERGING | REFRESH
    status: in_progress # queued | in_progress | in_review | published | dropped
    cluster_id: cl-credit-online
    locale: uk-UA # trend history is kept per locale; see §10.2
    target_url: null # for REFRESH — the existing URL; otherwise null
    trend:
      score: 0.71
      z: 2.8
      accel: 0.9
      growth_28d: 0.42
      sources: # P1: every source carries a URL and a date
        - source: gsc
          observed_at: 2026-08-05
          evidence: "impressions +38% w/w, cluster cl-credit-online"
        - source: dataforseo_trends
          observed_at: 2026-08-05
          evidence: "rising, index 34 -> 61"
      history_points: 412 # <30 switches to the breakout branch
    seasonality:
      peak_week: 36
      lead_time_weeks: 12 # from thresholds.yml, NOT a constant
      publish_by: 2026-06-15
    deadline: 2026-06-15
    priority: 2
    unique_value_source: # P13 — mandatory, and substantive
      type: own_data
      description: "Own sample of rates across 14 MFIs, collected 2026-08-01, with stated measurement method"
      artifact: .kiln/assets/mfo-rates-2026-08-01.csv
    reviewer_assignments: # see 06-review-lenses.md
      facts: vadym
      domain: liosha
      voice: reviewer-3
      reader_value: yura
    cannibalization_checked: true
    cannibalization_report: .kiln/reports/cann-cl-credit-online.json
    source_age_median_days: null # populated after publication

dropped: # P8/P15 — rejections are retained, never deleted
  - id: TRD-2026-0809
    route: null
    locale: uk-UA
    reason: sources_insufficient
    score: 0.58
    z: 3.4
    sources_count: 1
    dropped_at: 2026-08-06
```

### Mandatory fields on a queue entry

| Field                     | Why it is mandatory                                                      |
| ------------------------- | ------------------------------------------------------------------------ |
| `trend.sources[]`         | P1: every source carries a URL/evidence and an observation date          |
| `unique_value_source`     | P13: without a named unique value the material is not published          |
| `reviewer_assignments`    | P2/P11: without an assigned reviewer an item cannot enter work           |
| `cannibalization_checked` | P6: competition against the existing corpus is checked before, not after |
| `route` + `deadline`      | an unclassified trend does not enter the plan                            |

**The `dropped` section is never purged.** Rejections are the data for threshold calibration and
for the fast learning loop (P8, P15). Deleting them means destroying the only material by which,
90 days later, one could determine whether the `sources ≥ 2` threshold was too strict.

---

## 9. The plan is hard-capped by verification throughput

This is principle P2 enforced at the level of the data structure.

```
max_wip = floor(review_hours_per_week / hours_per_item)
```

`review_hours_per_week` comes from `.kiln/project.yml` and is filled in by a human at onboarding.
`hours_per_item` starts as an estimate and is thereafter **computed from actual review logs**
(`.kiln/reviews/`) — meaning the system learns its true throughput within the first few weeks and
stops guessing.

| Rule       | Statement                                                                                                                                                                                                      | Enforcement                       |
| ---------- | -------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- | --------------------------------- |
| **TRD-15** | The number of queue items in status `in_progress` + `in_review` may not exceed `max_wip`. Once the cap is reached, new items receive status `queued` and **are not started**, however high their `TrendScore`. | `BLOCK` on generating a new draft |
| **TRD-16** | `max_wip` increases **only** when a human edits `review_hours_per_week` in `.kiln/project.yml`. Neither an agent nor a script may raise it.                                                                    | `BLOCK`                           |
| **TRD-17** | `NEWSJACK` does not bypass `max_wip`. It preempts the lowest-priority item back to `queued` rather than being added on top of the cap.                                                                         | `BLOCK`                           |

**Why TRD-17 is worded exactly this way.** The temptation to make newsjacking an exception is
strong — the topic is hot, the window is 24 hours, it is "just one article". That is precisely how
a cap ceases to exist: exceptions come to outnumber rules. Preemption instead of addition
preserves the invariant and, as a bonus, makes the cost of urgency visible — something planned got
pushed back.

---

## 10. Niche-agnosticism

### 10.1 No topical knowledge in code

The module's code contains no topical entity whatsoever. Subject matter lives entirely in the
project config.

The **seed set** is assembled once at onboarding:

1. Entities from the site itself — brand, products, categories.
2. Top queries from GSC — the first 200–500 by impressions.
3. Competitor entities — from module `03-competitors.md`.
4. GDELT GKG themes relevant to the seed terms (via Theme Lookup).
5. 5–15 niche subreddits — selected once, by a human or by an LLM with human confirmation.

**Expansion is driven by the data itself:** rising queries from the current cycle enter the seed
pool of the next. The module does not know what "credit" or "XDR" means — it only knows that a
term is growing and is confirmed by two sources.

| Rule       | Statement                                                                                                         | Enforcement                                                              |
| ---------- | ----------------------------------------------------------------------------------------------------------------- | ------------------------------------------------------------------------ |
| **TRD-18** | Topical dictionaries, topic lists and industry heuristics are forbidden in module code. Only `.kiln/project.yml`. | `BLOCK` at code review. Grounds: portability is Kiln's defining property |

### 10.2 Locale scoping

**Trend signals are locale-specific.** A spike observed in one language or region does not
transfer to another, and treating it as if it did is the single most common way to import
phantom demand into a content plan.

Every source in §1 carries the project's locale: GSC archiving is scoped by country and search
type, DataForSEO trend calls take an explicit location and language, and GDELT queries are issued
per language. For a multi-locale project each locale therefore maintains its **own trend history,
its own seasonal index and its own thresholds** — a route may fire for one locale while remaining
dormant for another, and this is normal rather than a defect to be reconciled.

Practical consequences:

- Queue entries and `dropped` records carry a `locale` field; scores are never pooled across locales.
- The `history_points < 30` breakout branch is evaluated per locale. A term with years of history
  in one locale may legitimately be a breakout in another.
- `sources ≥ 2` must be satisfied _within_ a locale. Confirmation of a spike in a different
  language does not count as a second source.
- `SEASONAL` peaks differ by region even for the same product; `peak_week` is computed per locale.
- Locale multiplies the cost of every paid source — see the same multiplier in `02-semantics.md`.

Like everything else in §10, locale is configuration and not code: the module holds no notion of
which locales exist, only that entries are grouped by whichever ones `.kiln/project.yml` declares.

---

## 11. Layer-2 script specifications

The scripts are autonomous: they know nothing about any particular site, never reach into a
foreign database, and take files in and hand files out. This is the condition for 100% portability.

### `scripts/gsc_hourly_archive.py`

Daily archiving of the GSC hourly slice. Runs on a schedule; idempotent.

|                  |                                                                                                                                         |
| ---------------- | --------------------------------------------------------------------------------------------------------------------------------------- |
| **Input**        | `--credentials <path>` (service account JSON), `--site <property>`, `--out-dir <path>`, `--days 8`                                      |
| **Output**       | `<out-dir>/hourly/YYYY-MM-DD.jsonl` — one row per `(date, hour, query, page, device, country)` with `clicks`, `impressions`, `position` |
| **Idempotency**  | re-running for the same date overwrites that file; dates already present are not re-requested without `--force`                         |
| **Additionally** | writes `<out-dir>/hourly/_manifest.json` listing covered dates and gaps — this is the input to the TRD-01 check                         |
| **Exit code**    | non-zero exit code on an archive gap, so that the scheduler raises an alarm                                                             |

### `scripts/trend_score.py`

Pure arithmetic. No network calls — it only computes over series already collected.

|                  |                                                                                                                                                           |
| ---------------- | --------------------------------------------------------------------------------------------------------------------------------------------------------- |
| **Input**        | `--series <path.jsonl>` — series shaped `{term, source, date, value}`; `--thresholds <path.yml>`; `--seasonal-index <path.json>` (optional)               |
| **Output**       | JSON: array of `{term, score, z, growth_28d, accel, sources, history_points, branch: "robust"\|"breakout", verdict: "plan"\|"watchlist"\|"drop", reason}` |
| **Behaviour**    | at `history_points < 30`, or on a breakout flag, switches to the §4 branch and **does not compute** the robust z                                          |
| **Required**     | all score components appear in the output even for discarded terms (TRD-06)                                                                               |
| **Tokenization** | not applicable; the module works with numbers, but term normalisation uses Unicode-aware comparison (P5)                                                  |

### `scripts/refresh_queue.py`

Builds the update queue across the corpus.

|                |                                                                                                                  |
| -------------- | ---------------------------------------------------------------------------------------------------------------- |
| **Input**      | `--corpus .kiln/corpus.json`, `--gsc <dir>`, `--geo-citations <path.json>` (optional), `--thresholds <path.yml>` |
| **Output**     | JSON: array of `{url, bucket, opportunity_score, triggers[], source_age_median_days, requires_human_approval}`   |
| **Buckets**    | `quick_win`, `competitive_threat`, `foundation_rebuild`, `consolidation`                                         |
| **Human flag** | `requires_human_approval = true` for `foundation_rebuild` and `consolidation` (P11)                              |
| **Triggers**   | age, traffic decline, competitor overtake, loss of an AI citation, `source_age_median` exceeded                  |

### Requirements common to all three

- Input and output are files and stdout only; no writes into foreign databases.
- Every threshold arrives as a parameter or from `thresholds.yml`; no values live in the code.
- Non-zero exit code when a blocking rule is violated, so a hook can halt the run.
- Any text-length measurement goes through Unicode-aware tokenization (P5).

---

## 12. Forbidden

| Prohibition                                                        | Rationale                                                                                                                          |
| ------------------------------------------------------------------ | ---------------------------------------------------------------------------------------------------------------------------------- |
| Using pytrends or scraping Google Trends directly                  | repository archived 2025-04-17; scraping breaches ToS; HTTP 429 after 10–15 requests per IP. Trends data comes via an intermediary |
| Using Google News RSS                                              | ToS explicitly forbids commercial use, robots, and reformatting of results                                                         |
| Building the module on TikTok / Instagram                          | no commercial Research API exists; only grey scraping remains                                                                      |
| Treating the Google Trends API as a foundation                     | a year in application-gated alpha, no self-serve, no public GA timeline                                                            |
| Computing the z-score via mean + stddev                            | σ is inflated by the very outliers being sought → the stronger the anomaly, the worse it is detected                               |
| Computing the z-score without de-seasonalization                   | search series are not normal; seasonality produces false positives twice a year                                                    |
| Admitting a trend to the plan at `sources = 1`                     | P1: a signal from a single place is not a fact                                                                                     |
| Applying the robust z to breakout terms                            | no base exists, `MAD → 0`, the denominator explodes                                                                                |
| Hard-coding the seasonal `lead_time`                               | "3–6 months" is practitioner consensus; no study exists                                                                            |
| Hard-coding any AI-citation figure as fact                         | all are drawn from write-ups with no disclosed methodology; they are starting priors                                               |
| Pooling trend scores or history across locales                     | §10.2: a spike in one locale is not evidence in another                                                                            |
| Creating a new page when one of our URLs already serves the intent | P6; the only paths are `REFRESH` or consolidation                                                                                  |
| Bumping the publication date without a substantive edit            | date manipulation is named by Google as a marker of unreliable content; the divergence is machine-detectable                       |
| Exceeding `max_wip`, including for an urgent newsjack              | P2; an exception to the cap destroys the cap                                                                                       |
| Raising `max_wip` automatically                                    | P2: the number comes from a human and does not grow "because we seem to be fast"                                                   |
| Publishing an off-topic newsjack to chase a spike                  | off-topic content is one of eight documented patterns that fell to algorithm updates                                               |
| Deleting entries from the `dropped` section                        | P8, P15: rejections are the material for threshold calibration and the fast learning loop                                          |
| Embedding topical dictionaries in module code                      | breaks portability — Kiln's defining property                                                                                      |

---

## 13. Division of labour: code / agent / human

| Task                                           | Performed by | Why that one                                                                  |
| ---------------------------------------------- | ------------ | ----------------------------------------------------------------------------- |
| Harvesting GSC, Trends, GDELT, Reddit          | **code**     | scheduling, idempotency, the unrecoverable cost of a miss                     |
| De-seasonalization, z-score, TrendScore        | **code**     | an LLM does not compute the same way twice; reproducible numbers are required |
| `source_age_median` across the corpus          | **code**     | date arithmetic, daily, over the whole corpus                                 |
| Classifying a trend into a route               | **agent**    | requires judgement about topical fit, but under the hard rules of §5          |
| Selecting niche subreddits at onboarding       | **agent**    | with mandatory human confirmation                                             |
| Drafting `unique_value_source`                 | **agent**    | proposes it; counts only when an artifact is attached (P13)                   |
| Confirming `unique_value_source`               | **human**    | a gate triggered by a filled field rewards box-ticking                        |
| `review_hours_per_week` and `max_wip`          | **human**    | P2; the one input the system has no right to estimate for itself              |
| Approving Foundation Rebuild and Consolidation | **human**    | P11: irreversible actions against the corpus                                  |
| Threshold calibration after 90 days            | **human**    | P10: changes go through a PR with evidence                                    |

---

## 14. Conflicts with the principles, and open questions

This section is kept honestly and grows as issues are found (P15).

**1. Tension between `NEWSJACK` and P2.**
A 24–48 hour window sits poorly with substantive human review, especially with four reviewers each
holding a different lens. TRD-17 resolves the conflict formally (preemption rather than addition)
but not substantively: if reviewers are physically unavailable within a day, the `NEWSJACK` route
is useless for that project. **The decision is deferred to onboarding:** a project explicitly
declares whether same-day review is available to it. If it is not, the route is switched off
entirely rather than run with a weakened gate.

**2. Tension between REFRESH escalation (TRD-13) and the growth plan.**
The rule halts new publications in any cluster where more than 40% of pages are overdue. On an
abandoned corpus (the reference pilot: ~4,000 URLs, ~2 years idle) this will block almost
everything at once. That is deliberate and consistent with P0, but the 40% threshold is
uncalibrated and will almost certainly need correction after the first run. The first run is
required to record the actual distribution of overdue pages across clusters **before** the
escalation is enabled.

**3. Not covered by the intelligence base.**
There is no data on how `source_age_median` behaves as a predictor — the metric is proposed on
reasoning, but its relationship to citation loss has been measured by nobody. It is the number-one
candidate for our own measurement: if the relationship holds on our corpus, that would be the
first published evidence of it.

**4. Dependence on a single paid source.**
DataForSEO is the module's only paid dependency. If it is unavailable, `sources` for external
demand collapses to GDELT and Reddit, meaning the `sources ≥ 2` requirement begins to fail
systematically for non-newsworthy queries. No fallback path has been worked out.

---

## Sources

All data in this section is drawn from `EVIDENCE.md#e08-trend-detection` and
`EVIDENCE.md#e14-content-operations`, where the primary sources are listed with URLs and dates.
Key primary sources:

- Google Search Central — Introducing the Google Trends API (alpha), 2025-07-24
- Search Console API — Usage Limits · About bulk data export to BigQuery
- Google News — Terms of Use (prohibition on commercial use and robots)
- Google News Initiative — Basics of Google Trends (definitions of Rising / Top / Breakout)
- GDELT Project — DOC 2.0 API
- Lily Ray — analysis of 220+ domains served by AI content platforms (evidence level A)
- Similarweb — Zero-Click Marketing, clickstream panel, 2026-06-10 (evidence level A)
- Booking.com Engineering — Anomaly Detection in Time Series Using Statistical Analysis
- Tobias Willmann — hands-on test of the Google Trends API v1alpha

**Marked unverified and not used as constants:** seasonal publishing lead time (3–6 months), all
percentages concerning AI-citation freshness (25.7%; 3.2×; 13 weeks), citation half-life by content
type, and claimed refresh uplift (20–40%).
