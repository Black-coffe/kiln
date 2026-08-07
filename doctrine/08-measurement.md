# 08 — Measurement: Search Console, leading indicators, reporting

**Version:** 0.1.0 · **Date:** 2026-08-07 · **Review:** mandatory every 90 days
**Subordinate to:** [`00-principles.md`](00-principles.md) — on conflict, the principles win.
**Rests on:** P0 (rejection is the primary metric), P8 (we measure the rules), P9 (three loops), P2 (pace).
**Adjacent sections:** `09-geo.md` (citation measurement — an independent loop), `07-linking.md`
(cannibalization as an action), `10-safety-gates.md` (pace and policy), `11-self-learning.md`
(where measurements go).

---

## 0. What this section is for

This section answers one question: **how do you tell a working system from a broken one before it
is too late to matter.**

Traffic does not answer that question. It answers a different one — "what was true six months ago."
Between publication and a stable traffic signal sit 4–12 weeks of reindexing plus months of signal
accumulation. Over a 90-day pilot, traffic describes the site's past, not Kiln's quality.

Measurement in Kiln is therefore built around **leading** indicators, with traffic as a reference
line. This is not a softening of standards. It is protection against two opposite errors: writing
off a working system as a failure, and believing a rising curve that collapses six months later.

> The owner's own documents already record the precedent: a six-month-old domain ranking around
> position 56 is **expected and is not a fixable on-page defect**; results take 6–12 months;
> measure impressions, position and indexed page count, not clicks.
> `[internal observation, unpublished: content-plan-gsc-prioritized.md §0.5]`

### 0.1 Locale segmentation comes before any threshold

### MSR-22 · Locale segmentation precedes every threshold

**Severity: BLOCK**

Search Console data is segmented by locale before any threshold, detector or calibration is
applied. Cohort tracking, CTR calibration and cannibalization detection all run within a single
locale. For a multi-locale site, the same URL path under two locales is two distinct pages.

Search Console data is segmented by locale **before** a single threshold is applied. Mixing locales
in one calculation produces averages that describe no market: a Ukrainian query set and an English
one have different CTR curves, different SERP feature profiles and different competitive density,
and their blend is a number no decision can be made on.

Everything downstream runs per locale: cohort tracking, CTR calibration, cannibalization detection,
decay, striking distance, seasonality. For a multi-locale site, **the same URL path in two locales
is two distinct pages** — separate corpus entries, separate cohort membership, separate history.
Cross-locale aggregates may be reported, but never used as an input to a detector.

Implementation note: locale is derived from the URL (path prefix, subdomain or ccTLD) as declared
in `.kiln/project.yml`, not guessed from the `country` dimension. Country is where the searcher was;
locale is which page served them, and the two diverge constantly.

---

## 1. The measurement cycle

```
                       daily                        weekly                    monthly
                         │                             │                          │
  ┌──────────────────────▼─────┐   ┌───────────────────▼─────────┐   ┌────────────▼─────────┐
  │ gsc_pull  (incremental)    │   │ analyze  (all detectors)    │   │ ctr_calibrate        │
  │ hourly slice (lives 8 days)│   │ cohort_watch (cohorts)      │   │ recompute CTR curves │
  │ ExportLog.epoch_version    │   │ report → .kiln/measurements/│   │ threshold review     │
  └──────────────────────┬─────┘   └───────────────────┬─────────┘   └────────────┬─────────┘
                         │                             │                          │
                         └──────────────► .kiln/measurements/*.json ◄─────────────┘
                                                       │
                                         ┌─────────────▼─────────────┐
                                         │ findings → action tier    │
                                         │ automatic / semi / manual │
                                         └─────────────┬─────────────┘
                                                       │
                                           human: ack / do / dismiss
                                                       │
                                         mark optimised → re-measure
```

The closing step is **`mark optimised → re-measure next pull`**. Without it the system produces
findings but never learns whether the action helped. It is the only mechanism that turns measurement
into learning (P9, middle loop). `[internal observation, unpublished: GSC roadmap §5]`

---

## 2. Leading indicators

### MSR-01 · The indicator set is fixed and does not change within a quarter

**Severity: BLOCK** (for reporting; changing the set mid-window makes measurements incomparable)

Eight indicators in three groups. Each is computed by code, each has a direction that counts as good.

| ID       | Indicator                            | Formula                                                         | Good direction | P9 loop |
| -------- | ------------------------------------ | --------------------------------------------------------------- | -------------- | ------- |
| **LI-1** | Indexation of new pages              | `indexed / published` within the window                         | ↑              | middle  |
| **LI-2** | Time to index                        | median days from publication to first impression in GSC         | ↓              | middle  |
| **LI-3** | Position shift, target clusters      | `pos_now − pos_prior`, impression-weighted, non-branded only    | ↓ (position)   | middle  |
| **LI-4** | Share of queries in the visible band | `queries(pos ≤ 20) / queries(all)` per cluster                  | ↑              | middle  |
| **LI-5** | AI answer citation rate              | computed in `09-geo.md`, imported here                          | ↑              | middle  |
| **LI-6** | Technical defects closed             | count closed from the onboarding defect register                | ↑              | fast    |
| **LI-7** | Cannibalization                      | queries with `flip_rate ≥ threshold` and sufficient impressions | ↓              | middle  |
| **LI-8** | Rejection funnel                     | share of drafts stopped by gates, **broken down by cause**      | — (observed)   | fast    |

### MSR-02 · LI-8 is Kiln's primary measure, not a footnote

**Severity: BLOCK**

A direct consequence of P0. In the report the rejection funnel sits **on the first screen next to
LI-1**, not in an appendix. Track not only the rate but the distribution of causes: a shift in
causes over time is the fast learning loop's signal.

How to read it:

- rejection rate falling toward zero → either the writer learned, or the gates stopped firing.
  Distinguish via LI-6 and via the number of edits made at human review. If reviewers are catching
  what the gates missed, the gates have degraded;
- rejection rate steadily above 60% `[expert judgment, needs calibration]` → the problem is in the
  brief or in the rules, not in the writer. The rule firing most often goes into the revision
  queue (P8).

### MSR-03 · Traffic and conversions are a reference line, not an acceptance criterion in the first 90 days

**Severity: WARN**

Always displayed; no decision inside the 90-day window rests on them. One exception —
**a drop**: a traffic collapse is read immediately (see §8), because the risk is asymmetric.

### MSR-04 · All growth metrics are computed on the non-branded segment only

**Severity: BLOCK**

Growth in branded queries is a marketing result, not a content result, and it masks failures. The
branded segment is shown on its own line. `[source: EVIDENCE.md#e04-search-console]`

Mechanically: a regex filter over a list of brand tokens. **The API filter length limit is 4,096
characters**; a long list must be split across several requests. BigQuery has no such limit:
`REGEXP_CONTAINS(query, r'...')`. `[source: official Search Analytics API documentation]`

---

## 3. Sources and their limits

### 3.1 Search Analytics API

`[all figures sourced from developers.google.com/webmaster-tools/v1/searchanalytics/query and /limits, current as of 2026-08-07]`

| Parameter              | Value                                                                                |
| ---------------------- | ------------------------------------------------------------------------------------ |
| Dimensions             | `country`, `device`, `page`, `query`, `searchAppearance`, `date`, `hour`             |
| `type`                 | `web` (default), `discover`, `googleNews`, `news`, `image`, `video`                  |
| `rowLimit`             | 1–25,000 (default 1,000), paginated via `startRow`                                   |
| `dataState`            | `final` (default), `all`, `hourly_all`                                               |
| Filter operators       | `contains`, `equals`, `notContains`, `notEquals`, `includingRegex`, `excludingRegex` |
| Filter length          | **4,096 characters**                                                                 |
| Search Analytics quota | 1,200 QPM per site · 1,200 QPM per user · 40,000 QPM and 30,000,000 QPD per project  |
| URL Inspection quota   | **2,000 QPD and 600 QPM per site** · 15,000 QPM / 10,000,000 QPD per project         |
| Other resources        | 20 QPS, 200 QPM per user                                                             |
| Retention window       | **16 months**; older data does not exist                                             |
| Lag                    | 2–4 days normally, 5–7 during Google system updates                                  |

Per-row response: `keys[]`, `clicks`, `impressions`, `ctr` (0–1.0), `position` (average, 1-based).

### MSR-05 · URL Inspection is a scarce resource; full-corpus sweeps are forbidden

**Severity: BLOCK**

Two thousand requests per day per site is the hardest limit in the entire system. On the reference pilot corpus
(4,075 URLs) a full sweep consumes two days of quota and leaves nothing for diagnosis.

Inspection is permitted only for URLs already flagged by another detector: suspected canonical
mismatch, a "lost" query, a new page with no impressions past the threshold. Budget: no more than
**300 inspections per day** `[expert judgment, needs calibration]`; the rest stays in reserve.

A separate trap: **the "quota exceeded" error text is identical for every quota type** — it cannot
tell you which one you hit. Track consumption with your own counter, not by parsing errors.

### MSR-06 · The last 3–4 days of any window are always trimmed

**Severity: BLOCK**

Recent days are systematically under-reported. Comparing windows without trimming produces false
decay on every run. `[source: EVIDENCE.md#e04-search-console; the exact figure is practice, not a Google guarantee]`

If reports are found to be stalled (multi-week incidents have occurred), widen the trim and mark
comparisons over the affected window as unreliable rather than silently recomputing them.

### MSR-07 · Rare-query anonymization is accounted for explicitly

**Severity: WARN**

Queries below the privacy threshold are removed from the report. **The sum over the `query`
dimension does not reconcile with the property total**, and the gap reaches tens of percent on the
long tail. This is by design, not a bug. `[source: Google Search Central, "A deep dive into Search
Console performance data filtering and limits", 2022-10]`

Mandatory consequences:

- never compute "this query's share of total traffic" from the query slice;
- keep a high threshold in the lost-query detector (see §5.8), otherwise half the list is queries
  that merely fell below the privacy cutoff;
- show the reconciliation gap on its own line in the report rather than hiding it.

### 3.2 Bulk Data Export to BigQuery

Three tables in the `searchconsole` dataset. `[source: support.google.com/webmasters/answer/12917991 and /12917174]`

| Table                        | Purpose               | Key position field                                                       |
| ---------------------------- | --------------------- | ------------------------------------------------------------------------ |
| `searchdata_site_impression` | property-level rollup | `sum_top_position` (0-based)                                             |
| `searchdata_url_impression`  | **the working table** | `sum_position` (0-based) + `url` + boolean `is_[search_appearance_type]` |
| `ExportLog`                  | operational           | `epoch_version`, `data_date`, `publish_time`                             |

The critical difference: if two of our URLs are shown for one query, the url-level table counts
**two separate impressions**. That is precisely why cannibalization can only be detected there, and
why the site-level table is unusable for it.

Access: a Google Cloud project with billing enabled; the service account
`search-console-data-export@system.gserviceaccount.com` is granted **BigQuery Job User** and
**BigQuery Data Editor**.

### MSR-08 · The BigQuery export is enabled on the day the project is onboarded

**Severity: BLOCK**

**The export has no backfill.** Data accumulates only from the moment it is switched on. Every day
of delay is lost permanently.

The justification for our scale. The argument "our site is small, the API is enough" fails on three
counts:

1. **The 25,000-row ceiling.** A `query × page × date` slice over 28 days on a 4,075-URL corpus hits
   the ceiling and forces pagination, with a real risk of gaps. This is not hypothetical.
2. **The 16-month cliff.** Eighteen months in, the project has no basis for year-over-year
   comparison. Seasonality in finance — rates, deposits, insurance — is not cosmetic; it is the
   dominant rhythm.
3. **The cost is near zero when configured correctly.** Tables are partitioned by `data_date`; with
   mandatory date filtering, the scanned volume on our corpus fits inside the BigQuery free tier.

Compromise if the owner cannot stand up a GCP project immediately: run through the API in
`cold start` mode (§10) and **enable the export no later than day 30**. This is recorded as a task
with a deadline, not as "eventually."

Mandatory settings: partition expiration ≥ 14 days (otherwise tables grow without bound); monitor
`ExportLog` — on persistent permission errors the export retries for about 7 days and then
**stops silently**.

---

## 4. Three ways the BigQuery export breaks your numbers

All three fail quietly, without raising an error. Each is closed by one line of code — provided you
know it exists.

### MSR-09 · A `GROUP BY` is mandatory before any aggregation

**Severity: BLOCK**

> "Performance data is accumulated by Search Console incrementally, resulting in table rows with
> repeated keys." `[source: official Google table schema reference]`

Rows are **not deduplicated**. A direct `SUM(clicks)` over the raw table inflates every figure. This
is the single most common mistake made with the export.

```sql
-- CORRECT: collapse by key first, then aggregate
SELECT query, url, SUM(clicks) AS clicks, SUM(impressions) AS impressions,
       SUM(sum_position) AS sum_position
FROM `PROJECT.searchconsole.searchdata_url_impression`
WHERE data_date BETWEEN @start AND @end     -- mandatory: partition pruning
GROUP BY query, url
```

### MSR-10 · An anonymized query is an empty string, not NULL

**Severity: BLOCK**

`WHERE query IS NOT NULL` does nothing and silently lets anonymized rows into the sample. Correct:

```sql
WHERE query != ''            -- or explicitly: AND is_anonymized_query = FALSE
```

### MSR-11 · `epoch_version` is checked on every run

**Severity: BLOCK**

`ExportLog.epoch_version` increments when Google has **recomputed historical data**. It is the only
programmatic signal that cached aggregates are stale and the past has been rewritten.

```sql
SELECT data_date, MAX(epoch_version) AS ev
FROM `PROJECT.searchconsole.ExportLog`
WHERE agenda = 'SEARCHDATA' AND data_date BETWEEN @start AND @end
GROUP BY data_date
```

Procedure: store `epoch_version` alongside every saved aggregate. When the version increments,
recompute the affected dates and **mark every conclusion drawn on the old version as requiring
re-verification**. Silent recomputation is forbidden: it destroys any ability to understand why a
conclusion changed.

Also: **do not alter the table schema** — adding columns breaks the export.

---

## 5. Algorithms

All follow the same template: **input → formula/threshold → output → action**. Thresholds appear in
two columns: the value from the owner's working system and the value from published practice. The
disagreements are left visible on purpose and are resolved by calibration on project data, not by
argument.

### 5.0 Base formulas (used everywhere)

**Average position.** Three distinct cases, and they are confused more often than anything else:

```
BigQuery, site table:  avg_pos = SUM(sum_top_position) / SUM(impressions) + 1
BigQuery, url table:   avg_pos = SUM(sum_position)     / SUM(impressions) + 1
API (position already 1-based, averaged per row):
                       avg_pos = SUM(position × impressions) / SUM(impressions)
```

The `sum_*` fields in BigQuery are **0-based**, hence the `+ 1`. In the API, `position` is already
1-based and needs no adjustment — but when merging rows, aggregate **weighted by impressions**.

> Weighted aggregation is confirmed by working code: `_posw += position × impressions`.
> `[internal observation, unpublished: the audited system's analyzer]`

**CTR.** Never averaged across rows:

```
ctr = SUM(clicks) / SUM(impressions)      -- recompute, not AVG(ctr)
```

### MSR-12 · Position is aggregated weighted; CTR is recomputed

**Severity: BLOCK**

Naive `AVG(position)` and `AVG(ctr)` are systematically wrong: a long-tail query with one impression
carries the same weight as one with ten thousand.

---

### 5.1 Cannibalization

**Input:** `query`, `url`, `clicks`, `impressions`, `sum_position`, `data_date`, `is_anonymized_query`.
Windows: 28 days to detect, 90 days to decide (P6). Per locale (§0.1).

**Stage 1 — candidates:**

```sql
SELECT query,
       COUNT(DISTINCT url)                       AS competing_urls,
       ARRAY_AGG(url ORDER BY clicks DESC LIMIT 5) AS top_urls,
       SUM(clicks) AS total_clicks, SUM(impressions) AS total_impressions
FROM (
  SELECT query, url, SUM(clicks) clicks, SUM(impressions) impressions
  FROM `PROJECT.searchconsole.searchdata_url_impression`
  WHERE data_date BETWEEN DATE_SUB(CURRENT_DATE(), INTERVAL 31 DAY)
                      AND DATE_SUB(CURRENT_DATE(), INTERVAL 4 DAY)   -- MSR-06
    AND query != '' AND clicks >= 1
  GROUP BY query, url                                                 -- MSR-09
)
GROUP BY query
HAVING COUNT(DISTINCT url) >= @min_urls
```

**Stage 2 — leader instability.** Counting distinct URLs is not enough: two pages can legitimately
both appear for one query. The real signal is that Google cannot pick one:

```
flip_rate = (number of days the leading URL changed) / (days with impressions − 1)
```

**Stage 3 — semantics.** Cosine similarity between the competing pages' text decides "merge or
differentiate."

| Threshold                           | Value                         | Note                                                            |
| ----------------------------------- | ----------------------------- | --------------------------------------------------------------- |
| `min_urls`                          | **≥ 2**                       | `[internal observation, unpublished: the audited system's analyzer — working default]` |
| `min_urls` (strict)                 | **≥ 3**                       | `[source: EVIDENCE.md#e04-search-console, published practice]`                   |
| Clicks on the second URL            | **> 0**, tightened to **≥ 3** | `[source: JC Chouinard; n8n templates]`                         |
| `min_impressions` per (query, page) | **10**                        | `[internal observation, unpublished: the audited system's analyzer]`                   |
| `flip_rate`                         | **≥ 0.30**                    | `[expert judgment, needs calibration]`                          |
| Cosine for merging                  | **≥ 0.90**                    | `[source: EVIDENCE.md#e04-search-console, practice; validate on a sample]`       |
| Branded queries                     | excluded                      | `[source: EVIDENCE.md#e04-search-console]`                                       |

**Output:** a task type derived from the (cosine, click gap) pair — see P6 and `07-linking.md`:
(a) merge + 301, (b) differentiate intents, (c) canonicalize, (d) remove internal links pushing the
weaker page.

**Action:** merges, redirects and deletions go **through a human only** (P11, point 3). The system
prepares the diff; it does not apply it.

---

### 5.2 Striking distance and the click-through gap

**Input:** `query`, `url`, `impressions`, `clicks`, position.

```
opportunity_score = impressions × (CTR_expected(pos, serp_profile) − CTR_actual)
```

Rank tasks by `opportunity_score`, **not by impressions** — otherwise high-volume queries where we
are already at the ceiling float to the top.

| Threshold         | Working default | Practice       | Note                                |
| ----------------- | --------------- | -------------- | ----------------------------------- |
| `min_impressions` | **20**          | 1,000          | `[internal observation, unpublished]` / `[EVIDENCE.md#e04-search-console]` |
| Position band     | **5.0–20.0**    | 4–15, up to 10 | `[internal observation, unpublished]` / `[EVIDENCE.md#e04-search-console]` |
| CTR threshold     | —               | **< 0.02**     | `[source: EVIDENCE.md#e04-search-console]`           |
| Result cap        | 50              | —              | `[internal observation, unpublished]`                |

The two-order-of-magnitude gap in the impression threshold (20 versus 1,000) is not an error but a
difference in site scale. For the reference pilot, with 4,075 URLs and 29 months of dormancy, start from the
**low** threshold and raise it as data accumulates — otherwise the detector says nothing at all.

**Mandatory 2026 correction.** For queries carrying an AI Overview, target citation inside the AIO
first and the blue link second: moving from position 8 to 5 will yield far fewer clicks than the
clean curve predicts. The SERP profile comes from the SERP module, not from GSC.
`[source: EVIDENCE.md#e04-search-console]`

**Output:** good position with CTR below expectation → rewrite title and description. Position
8–15 → strengthen the content and internal links.

**Rule `MSR-23` (INFO, code).** A query whose impressions clear `min_impressions`, whose position
falls inside the band, and whose actual CTR sits below the expected curve for its SERP profile is
reported as a striking-distance opportunity, ranked by `opportunity_score` rather than by
impressions. `[expert judgment, needs calibration]` — the two threshold columns above differ by two
orders of magnitude, and only project data settles which applies.

---

### 5.3 CTR outliers

**Input:** `query`/`url`, position ≤ 10, impressions, clicks.

```
flag  ⟺  ctr_actual < ratio × CTR_expected(position, serp_profile)
```

| Threshold         | Value    | Note                                          |
| ----------------- | -------- | --------------------------------------------- |
| `min_impressions` | **50**   | `[internal observation, unpublished: the audited system's analyzer]` |
| `ratio`           | **0.5**  | `[internal observation, unpublished]`                          |
| Position          | **≤ 10** | `[internal observation, unpublished]`                          |

> The comment in the original source is honest and travels with the threshold: the curve is
> "used only to flag _relative_ under-performance, not as ground truth."

**Rule `MSR-24` (INFO, code).** A page or query at position ≤ 10 whose actual CTR falls below
`ratio × CTR_expected` is reported as a click-through outlier. The finding states relative
under-performance against the curve in force and never asserts an absolute click shortfall — the
curve is a prior until calibrated (MSR-14). `[internal observation, unpublished: the audited system's analyzer]`

---

### 5.4 Page decay

**Input:** `url`, `clicks`, `data_date`. Two 28-day windows.

```
decay  ⟺  clicks_prior ≥ @min_prior  AND  (clicks_now − clicks_prior) / clicks_prior ≤ @drop
```

| Threshold              | Value                       | Note                                         |
| ---------------------- | --------------------------- | -------------------------------------------- |
| `min_prior`            | **50** clicks               | `[source: EVIDENCE.md#e04-search-console]`                    |
| `drop`                 | **≤ −0.25**                 | `[source: EVIDENCE.md#e04-search-console]`                    |
| Conservative benchmark | −20 to −40% over 8–12 weeks | `[source: EVIDENCE.md#e04-search-console, industry practice]` |

**Two mandatory corrections, without which the detector is pure noise:**

1. **A rolling 6–12 month window**, not just the last 30 days — otherwise seasonality produces
   false positives continuously.
2. **Differencing against the cluster.** Did only our page drop, or did the whole category? Compare
   against the median for pages of the same type. A drop shared with the cluster is not decay but a
   shift in demand or in the SERP, and it needs a different remedy.

**Output:** refresh / rewrite / consolidate / delete. Expect reindexing after an update to take
**4–12 weeks** `[source: EVIDENCE.md#e04-search-console]`; re-measuring sooner is meaningless and is forbidden as a
basis for further action.

**Rule `MSR-25` (WARN, code).** A page whose prior-window clicks clear `min_prior` and whose
period-over-period change falls at or below `drop` is reported as decaying. The finding is invalid
without the two corrections above: it must state whether the cluster median moved with it, and it
must not be raised on a window shorter than the seasonality guard allows.
`[source: EVIDENCE.md#e04-search-console]`

---

### 5.5 Rising queries and pages

```
rising  ⟺  clicks_now ≥ 25  AND  (clicks_prior IS NULL  OR  clicks_now − clicks_prior ≥ 25)
```

`[source: EVIDENCE.md#e04-search-console]` · `min_impressions = 30` for movers `[internal observation, unpublished]`

**Output:** reinforce with internal links, expand into adjacent subtopics, consider as a cluster hub
candidate. It is cheaper to win where momentum already exists.

**Rule `MSR-26` (INFO, code).** A query or page meeting the rising condition is reported as a
momentum candidate. `[source: EVIDENCE.md#e04-search-console]`

---

### 5.6 Query–page mismatch

**Input:** the "query ↔ highest-impression URL" pair, plus query intent classification and page
type (`02-semantics.md`).

```
mismatch  ⟺  intent(query) ≠ expected_intent(page_type(url))
```

Weight by impressions — a mismatch on a query with three impressions is not worth attention.

**Supporting signal:** the Google-selected canonical from URL Inspection. If Google picked a
different URL than we did, that is direct confirmation of the problem. Spend strictly within MSR-05:
flagged URLs only.

**Output:** rework the page's intent, or create the missing page for the other intent.

**Rule `MSR-27` (WARN, code).** A query whose classified intent disagrees with the expected intent
of its highest-impression URL's page type is reported as a mismatch, weighted by impressions. The
rule fires only where both classifications exist: an absent intent classification produces no
finding rather than a default one, since a guessed intent on both sides manufactures agreement or
disagreement at random. `[expert judgment, needs calibration]`

---

### 5.7 Branded and non-branded segments

See MSR-04. Brand tokens are fixed at onboarding in `.kiln/project.yml` and versioned: changing the
list changes every historical series, so retroactive recomputation requires an explicit note in the
report.

---

### 5.8 Lost queries

```
lost  ⟺  impressions_prior ≥ @min_prior  AND
          (impressions_now = 0  OR  (impressions_now − impressions_prior)/impressions_prior ≤ −0.80)
```

| Threshold   | Value                 | Note                                                                                      |
| ----------- | --------------------- | ----------------------------------------------------------------------------------------- |
| `min_prior` | **≥ 100 impressions** | `[source: EVIDENCE.md#e04-search-console]` — below this, half the list is anonymization artifacts (MSR-07) |
| Drop        | **≤ −80%**            | `[source: EVIDENCE.md#e04-search-console]`                                                                 |

**Output:** verify the URL is indexed (URL Inspection, within the MSR-05 budget), check whether a
competitor took the top, check whether an AI Overview appeared for the query.

**Rule `MSR-28` (WARN, code).** A query whose prior-window impressions clear `min_prior` and which
has since lost impressions entirely or dropped by at least the stated share is reported as lost.
Below `min_prior` the rule does not fire at all: at that volume the list is dominated by
anonymization artifacts rather than by real losses (MSR-07). `[source: EVIDENCE.md#e04-search-console]`

---

### 5.9 Seasonality

**Input:** `query`/`url` × `date` over the longest available history.

Compare **year over year by week**, not period over period. Without YoY, any seasonal dip reads as
decay. With ≥ 2 years of history, decompose the series into trend / seasonality / residual and alert
on the residual only. `[source: EVIDENCE.md#e04-search-console]`

This is the direct argument for MSR-08: on the API, 16 months yields exactly one YoY comparison, and
that one sits at the edge of the window where data is already crumbling.

**Rule `MSR-29` (INFO, code).** A week whose impressions fall against the same ISO week a year
earlier, by at least the residual threshold and on a prior base clearing `min_impressions`, is
reported as a seasonal observation. It is an observation and never an action: without decomposition
into trend, seasonality and residual, a year-over-year fall cannot be told from a trend decline.
`[source: EVIDENCE.md#e04-search-console]`

**Rule `MSR-30` (INFO, code).** Where the available history is shorter than one year-over-year
comparison, the seasonality detector reports the shortfall instead of a result, naming the history
it has and the history it needs. It must not fall back to period-over-period comparison, which is
precisely the substitution that makes every seasonal dip read as decay. The finding's action is to
enable the BigQuery export (MSR-08), because the export has no backfill and each day of delay is
lost permanently.

---

### 5.10 Coverage gaps

```
gap  ⟺  impressions ≥ 30  AND  best_position > 20
```

`[internal observation, unpublished: the audited system's analyzer]` — plenty of impressions, weak best position. Demand is
confirmed, the page does not reach. A candidate for the rework queue, not for a new article.

**Rule `MSR-31` (INFO, code).** A query carrying impressions at or above the floor whose best
position never reaches the first two pages is reported as a coverage gap, routed to the rework
queue. It must not be routed to new-page creation: demand is confirmed and a page already exists,
so a second page on the same demand is the doorway pattern P6 forbids.
`[internal observation, unpublished: the audited system's analyzer]`

---

## 6. Two click-through curves

### MSR-13 · One CTR curve per SERP profile, not one curve for everything

**Severity: BLOCK**

There is no such thing as a single curve. Store at least two tables plus device coefficients.

**Curve A — clean SERP** `[source: First Page Sage, 2026 meta-analysis, via indexsy.com]`

| Position | 1     | 2     | 3    | 4    | 5    | 6    | 7    | 8    | 9    | 10   |
| -------- | ----- | ----- | ---- | ---- | ---- | ---- | ---- | ---- | ---- | ---- |
| CTR      | 26.4% | 12.1% | 6.7% | 4.8% | 3.4% | 2.9% | 2.0% | 1.4% | 1.2% | 1.0% |

**Curve B — SERP with an AI Overview.** A multiplier applied to Curve A: **×0.39** (−61%)
`[source: Seer Interactive, September 2025, 3,119 informational queries: 1.76% → 0.61%]`

**SERP feature modifiers** `[source: SISTRIX]` — applied on top:

| Feature                  | Effect at position 1                  |
| ------------------------ | ------------------------------------- |
| Sitelinks                | up to 46.9%                           |
| Featured snippet present | drops to 23.3%                        |
| Clean organic, mobile    | 34.2% / 17.1% / 11.4% (positions 1–3) |

**Effect of being cited in an AIO:** cited brands receive roughly **+120% organic clicks per
impression** versus uncited brands on the same query `[source: Seer, 2026; an earlier measurement in
Sept 2025 gave +35%]`. This is the key argument for LI-5 sitting among the leading indicators
alongside position.

**The curve from the owner's working code** `[internal observation, unpublished: the audited system's analyzer]` — included
for comparison, because it differs noticeably at positions 2–5:
`1: 0.28, 2: 0.15, 3: 0.10, 4: 0.07, 5: 0.05, 6: 0.04, 7: 0.03, 8: 0.025, 9: 0.02, 10: 0.018`,
then "shrink ~15% per position past 10, floor 0.003".

### MSR-14 · Public curves are cold-start priors only; after that, calibrate

**Severity: BLOCK**

The spread between studies for position 1 is **19–39.8%**. That means absolute values are usable
**only for ranking tasks against each other** and are categorically unusable for forecasting traffic
in absolute terms. Forecasting clicks in a report from a public curve is forbidden (see
"Prohibited").

**Calibration procedure** (`ctr_calibrate.py`, monthly, per locale):

1. Take a `query × page × date` slice over 90 days, trimming the last 4 days (MSR-06), non-branded
   queries only (MSR-04), `query != ''` only (MSR-10).
2. Bucket by rounded average position: 1, 2, 3, …, 10, 11–15, 16–20.
3. In each bucket compute `ctr = SUM(clicks)/SUM(impressions)` — **not** a row average (MSR-12).
4. Split buckets by SERP profile (AIO present / absent). The profile comes from the SERP module per
   query, not from GSC — GSC exposes no such field.
5. Discard buckets where `SUM(impressions) < 1,000` `[expert judgment, needs calibration]` — too
   little data; the public prior stands.
6. Blend with the prior in proportion to volume:
   `ctr_final = w × ctr_own + (1 − w) × ctr_prior`, where `w = min(1, impressions_bucket / 10,000)`
   `[expert judgment, needs calibration]`.
7. Write to `.kiln/thresholds.yml` with the date, sample size and the value of `w`.

Blending with the prior keeps the curve from jumping around on noise early on, and lets it become
genuinely ours as data accumulates. `w` is shown in the report: while it is **below 0.3, every
potential estimate is marked provisional**.

---

## 7. What GSC gives and does not give about AI answers

On **3 June 2026** Google shipped Search Generative AI performance reports.
`[source: developers.google.com/search/blog/2026/06/gen-ai-performance-reports]`

| Available                               | Not available                                   |
| --------------------------------------- | ----------------------------------------------- |
| Impressions                             | Clicks                                          |
| Dimensions: page, country, device, date | CTR                                             |
| —                                       | Position                                        |
| —                                       | **Queries**                                     |
| —                                       | Separation of AI Overviews and AI Mode (merged) |

Also: this is a **subset** of ordinary web impressions, not additional volume — there is no double
counting, so the ratio of AI impressions to total is valid. Rollout is gradual; on some properties
data begins on 2026-05-18.

### MSR-15 · The GEO loop is measured independently of GSC

**Severity: BLOCK**

GSC yields neither citation data, nor queries, nor clicks for AI answers. For source-level detail
there is no access through the Search Analytics API or through BigQuery — **manual CSV export from
the interface only**. `[source: EVIDENCE.md#e04-search-console, aioseo.fr 2026-07-18]`

LI-5 is therefore computed by the machinery in `09-geo.md`: a fixed prompt set, repeated
measurements, log analysis by AI crawler user-agent, referral traffic. GSC contributes exactly one
signal — the share of AI impressions out of total per page, and only via manual CSV.

### MSR-16 · Checking for `is_ai_overview` is task #1 when connecting a project

**Severity: WARN**

There is an unresolved conflict in the sources: one practitioner blog lists a boolean
`is_ai_overview` column in the `searchdata_url_impression` schema, while the official reference does
not name it, listing columns generically as `is_[search_appearance_type]`. The conservative position
is to assume the column does not exist.

It takes a minute to check, so it is always checked:

```sql
SELECT column_name
FROM `PROJECT.searchconsole.INFORMATION_SCHEMA.COLUMNS`
WHERE table_name = 'searchdata_url_impression' AND column_name LIKE 'is_%'
ORDER BY column_name;
```

Plus `searchanalytics.query` with `dimensions: ["searchAppearance"]`, to see whether an AI value has
appeared. The result is recorded in `.kiln/project.yml` with the check date. The answer determines
whether a separate manual CSV import loop is needed.

---

## 8. Risk monitoring: cohort dynamics

### MSR-17 · Risk is tracked by publication cohort, not by site-wide traffic

**Severity: BLOCK**

**No manual action for "Scaled content abuse" exists in Search Console** — it is absent from the
official list of manual actions. The penalty arrives algorithmically and silently.
`[source: EVIDENCE.md#e13-policy-and-risk]`

Risk monitoring therefore cannot be built on the Manual Actions API. It is built on a different
observation: if **the whole site drops at once**, that is an update or a season. If **the pages Kiln
published drop while the old ones hold**, the problem is in our production.

**Procedure (`cohort_watch.py`, weekly, per locale):**

1. Split the corpus into cohorts by month of first publication. One separate cohort is `pre-kiln`
   (everything predating adoption). On the reference pilot that is 4,075 URLs, and it is an ideal control group:
   a comparison that clean does not exist on a new site.
2. For each cohort over a 28-day window, compute — normalized by the number of pages in the cohort —
   clicks per page, impressions per page, median position (weighted, MSR-12), and the share of pages
   with non-zero impressions.
3. Compute the cohort's **relative** movement against `pre-kiln` over the same window:
   `rel_delta = Δ(cohort) − Δ(pre-kiln)`.
4. Alert on `rel_delta`, never on the absolute drop.

**Alert thresholds** `[all expert judgment, to be calibrated over the first quarter]`:

| Level     | Condition                                                       | Action                                     |
| --------- | --------------------------------------------------------------- | ------------------------------------------ |
| **Watch** | `rel_delta ≤ −15%` for two consecutive weeks                    | into the report, investigate causes        |
| **Alarm** | `rel_delta ≤ −30%` for two consecutive weeks **or** ≤ −40% once | **publishing paused**, human investigation |
| **Stop**  | two consecutive cohorts in alarm                                | full halt of output, doctrine review (P10) |

An additional independent trigger, not cohort-dependent: **more than 40% of Kiln pages still at zero
impressions 60 days after publication** `[expert judgment]`. That is an early sign the content is
failing a quality filter before ranking is even in play.

### MSR-18 · The publishing pause is automatic; lifting it is human-only

**Severity: BLOCK**

The risks are asymmetric: a false pause costs weeks of delay, a missed penalty costs the domain. The
"6–12 months of growth → peak → collapse below the starting point" trajectory reproduced on 54% of
220+ domains `[source: EVIDENCE.md#e14-content-operations]`, and it is only catchable in its early phase.

---

## 9. Bing and IndexNow

| Tool                                      | What it gives                                          | Limit                                                            |
| ----------------------------------------- | ------------------------------------------------------ | ---------------------------------------------------------------- |
| `GetPageQueryStats` / `GetQueryPageStats` | the same query × page slice needed for cannibalization | OAuth 2.0                                                        |
| URL Submission API                        | direct URL submission                                  | **10,000 URLs/day**, resets at midnight GMT, raisable on request |
| IndexNow                                  | instant change ping                                    | **no limit**, outside the Bing quota                             |

`[source: learn.microsoft.com/bingwebmaster; indexnow.org/documentation; EVIDENCE.md#e12-data-apis-and-pricing]`

### MSR-19 · IndexNow is a mandatory hook on publish and update

**Severity: BLOCK**

It costs $0, takes an hour to implement, and typical crawl-after-ping is within 24 hours. It speeds
up entry into the Bing, Yandex and Seznam indexes and into the surfaces fed by them, Copilot
included. It improves LI-2 directly.

Implementation lives in the adapter (`adapter/SPEC.md`), because it depends on how the project
publishes. The key file is placed at the site root during onboarding.

### MSR-20 · The Bing Webmaster API wrapper is written against JSON from the start

**Severity: WARN**

**After 2026-08-31 the Bing Webmaster API accepts JSON only**; SOAP/POX are being retired. Accounts,
keys and quotas are unchanged — only the request format changes.
`[source: EVIDENCE.md#e12-data-apis-and-pricing, "Deadline calendar"]` That date is 24 days out from this document's version, so
writing it any other way is already pointless.

---

## 10. Cold start mode

GSC is a rear-view mirror: it shows only where we already appear. Until data exists, prioritization
runs on other sources. This is **a different operating mode**, not a blocker.

|                               | `cold start`                                                        | `steady state`             |
| ----------------------------- | ------------------------------------------------------------------- | -------------------------- |
| Primary prioritization source | competitors + our own SERP reconnaissance                           | GSC / BigQuery             |
| CTR curve                     | public prior, `w = 0`                                               | own, calibrated (MSR-14)   |
| Detector thresholds           | bottom of the range                                                 | calibrated on our own data |
| Cohort monitor (MSR-17)       | inactive (no baseline)                                              | active                     |
| What substitutes for GSC      | competitor keyword gap, PAA, Reddit threads, support and sales logs | —                          |

**Switchover:** after **90 days** of our own data. `[source: EVIDENCE.md#e04-search-console]`

### MSR-21 · The mode is stated explicitly in the report

**Severity: WARN**

Conclusions drawn in `cold start` are labeled as such. Otherwise, six months later, nobody can work
out why the early priorities look strange.

**The reference pilot special case.** Formally the project is not cold start: 4,075 URLs and 16 months of GSC
history are available immediately. But 29 months of dormancy mean that history describes **a
different site** — the one that existed before the content pause. Practical rule: historical data is
used for the cohort baseline (§8) and for seasonality, but **not** for CTR calibration until 90 days
of fresh data accumulate. `[expert judgment, needs calibration]`

---

## 11. Layer 2 script specifications

Shared contract: **input is a file or an export, output is JSON**. The scripts know nothing about any
particular CMS, database or site. That is exactly what makes them portable without modification:
`analyze.py` works against a Search Console export, not against somebody's database.

All are CLI tools, deterministic, network-free (except `gsc_pull.py`), with `--dry-run`.

### 11.1 `gsc_pull.py`

The only script with network access. Pulls data and lands it in `.kiln/measurements/raw/`.

```
Input:   --property <sc-domain:example.com | https://example.com/>
         --start YYYY-MM-DD --end YYYY-MM-DD
         --source api|bigquery         (default: api)
         --credentials <path>          (service account JSON)
         [--dimensions query,page,date,device,country]
         [--type web|discover|news|...]
         [--hourly]                    (dataState=hourly_all)

Output:  .kiln/measurements/raw/<property>/<YYYY-MM-DD>.json
         .kiln/measurements/raw/<property>/_manifest.json
```

```jsonc
// _manifest.json
{
  "property": "sc-domain:example.com",
  "source": "bigquery",
  "pulled_at": "2026-08-07T05:00:00Z",
  "window": { "start": "2026-05-09", "end": "2026-08-03" },
  "trimmed_days": 4, // MSR-06
  "epoch_versions": { "2026-08-01": 3 }, // MSR-11
  "row_count": 184213,
  "anonymized_share": 0.31, // MSR-07, reported on its own line
  "quota_used": { "search_analytics_queries": 42, "url_inspection": 0 },
}
```

Requirements:

- **read-only scope, never write.** "No write scopes ever" carries over verbatim from the working
  system `[internal observation, unpublished]`;
- re-pulls are **idempotent**: delete-by-date-range plus insert, not row-level upsert;
- `--hourly` is invoked **daily and archived**, because hourly data lives 8 days and then disappears
  permanently `[source: EVIDENCE.md#e08-trend-detection]`. Fetching it on demand is already too late;
- on an `epoch_version` increment, automatically re-pull the affected dates and flag it in the
  manifest;
- quota consumption is tracked by our own counter (MSR-05), not by parsing error text.

### 11.2 `analyze.py`

The core. A direct descendant of `the audited system's analyzer` — the same pure functions, the same
thresholds as defaults, plus what was missing there: `flip_rate`, YoY seasonality, lost queries,
SERP-profile splitting, and every threshold moved out into config.

```
Input:   --raw .kiln/measurements/raw/<property>/
         --window 28 --compare-window 28
         --thresholds .kiln/thresholds.yml
         [--locale uk]                                          # §0.1, one locale per run
         [--brand-tokens .kiln/project.yml:brand_tokens]
         [--serp-profiles .kiln/semantics/serp_profiles.json]   # for CTR curve B
         [--detectors cannibalization,striking,ctr_outliers,decay,rising,mismatch,lost,gaps]

Output:  .kiln/measurements/findings/<YYYY-MM-DD>.json
```

```jsonc
{
  "generated_at": "2026-08-07T06:00:00Z",
  "window": {
    "now": ["2026-07-06", "2026-08-03"],
    "prior": ["2026-06-08", "2026-07-05"],
  },
  "mode": "steady_state", // MSR-21
  "locale": "uk", // §0.1
  "segment": "non_brand", // MSR-04
  "leading_indicators": {
    "LI-1_indexation_rate": 0.82,
    "LI-2_days_to_first_impression_median": 9,
    "LI-3_position_shift_weighted": -2.4,
    "LI-4_visible_query_share": 0.31,
    "LI-5_ai_citation_rate": null, // imported from 09-geo
    "LI-6_defects_closed": 14,
    "LI-7_cannibalized_queries": 37,
    "LI-8_rejection": {
      "rate": 0.34,
      "by_reason": { "P1_unverified_fact": 11, "P13_no_unique_value": 6 },
    },
  },
  "findings": [
    {
      "id": "CANNIBAL-0007",
      "type": "cannibalization",
      "severity": "high",
      "query": "кредит онлайн на картку",
      "urls": ["/credits/online", "/credit-online", "/mfo/online"],
      "metrics": {
        "flip_rate": 0.41,
        "impressions": 8120,
        "clicks": 96,
        "cosine_max": 0.93,
      },
      "thresholds_used": { "flip_rate": 0.3, "cosine_merge": 0.9 },
      "suggested_action": "merge_301",
      "tier": "manual", // merges are human-only, P11
      "state": "new",
    },
  ],
  "warnings": [
    "anonymized_share=0.31 — query sums do not reconcile with the property total (MSR-07)",
  ],
}
```

Requirements:

- **DB-free**, pure functions, no state beyond the input files;
- position aggregated weighted by impressions, CTR recomputed (MSR-12);
- every finding carries `thresholds_used` — otherwise, a month later, there is no way to reconstruct
  why it fired, and recalibrating thresholds retroactively destroys the history;
- `state` field: `new / ack / in_progress / done / dismissed / snoozed` — the adapter maintains the
  state, but the schema is defined here;
- `tier`: `automatic` (read-only) / `semi_automatic` (one click produces a **draft**) / `manual`
  (a human acts). **Nothing is ever published automatically.**
  `[internal observation, unpublished: GSC roadmap §5]`

### 11.3 `ctr_calibrate.py`

```
Input:   --raw .kiln/measurements/raw/<property>/ --days 90
         --priors doctrine/data/ctr_priors.json
         [--locale uk]                                          # §0.1
         [--serp-profiles .kiln/semantics/serp_profiles.json]

Output:  .kiln/thresholds.yml  (ctr_curves section, appended, never overwritten)
         .kiln/measurements/ctr_calibration_<YYYY-MM-DD>.json
```

```jsonc
{
  "calibrated_at": "2026-08-07",
  "locale": "uk",
  "sample_days": 90,
  "curves": {
    "clean": {
      "1": { "ctr": 0.241, "impressions": 41200, "w": 1.0 },
      "2": { "ctr": 0.118, "impressions": 12800, "w": 1.0 },
      "11-15": { "ctr": 0.004, "impressions": 620, "w": 0.06 },
    },
    "aio": { "1": { "ctr": 0.094, "impressions": 8100, "w": 0.81 } },
  },
  "blend_formula": "ctr_final = w*ctr_own + (1-w)*ctr_prior, w = min(1, impressions/10000)",
  "note": "w<0.3 — potential estimates are marked provisional",
}
```

### 11.4 `cohort_watch.py`

```
Input:   --raw .kiln/measurements/raw/<property>/
         --corpus .kiln/corpus.json      (first-publication dates)
         --window 28
         [--locale uk]                   # §0.1
         --thresholds .kiln/thresholds.yml

Output:  .kiln/measurements/cohorts/<YYYY-MM-DD>.json
         exit code 0 — normal, 1 — watch, 2 — alarm, 3 — stop
```

```jsonc
{
  "baseline_cohort": "pre-kiln",
  "locale": "uk",
  "cohorts": [
    {
      "cohort": "pre-kiln",
      "pages": 4075,
      "clicks_per_page": 0.41,
      "delta_pct": -3.1,
    },
    {
      "cohort": "2026-06",
      "pages": 12,
      "clicks_per_page": 0.22,
      "delta_pct": -34.0,
      "rel_delta_pct": -30.9,
      "zero_impression_share_60d": 0.17,
      "alert": "alarm",
    },
  ],
  "verdict": "alarm",
  "publishing_paused": true, // MSR-18
  "unpause_requires": "human",
}
```

The non-zero exit code is the point where the script becomes a **gate** rather than advice: the
publish hook reads it and physically refuses to release while `verdict: alarm`. This is exactly what
the previous system lacked, where the gate was advisory and rested on human discipline
`[internal observation, unpublished]`.

---

## 12. Roles: code / agent / human

| Work                                   | Owner                         | Why                                                                                                             |
| -------------------------------------- | ----------------------------- | --------------------------------------------------------------------------------------------------------------- |
| Export, deduplication, `epoch_version` | **code**                      | deterministic; failure here is silent and expensive                                                             |
| All formulas, thresholds, aggregations | **code**                      | an LLM does not compute the same number twice; without reproducible numbers there is nothing to learn from (P8) |
| Curve and threshold calibration        | **code**                      | arithmetic, per the §6 procedure                                                                                |
| Cohort monitor and pause               | **code**                      | must fire without being asked                                                                                   |
| Query intent classification            | **agent**                     | a binary judgment, not computable                                                                               |
| Hypotheses for "why did it drop"       | **agent**                     | generates candidate explanations from data, not a verdict                                                       |
| Report prose draft                     | **agent**                     | fixed template; the numbers are substituted by code                                                             |
| Prioritizing findings into the plan    | **human** + agent as prompter | the cost of error is a quarter of work                                                                          |
| Merges, redirects, deletions           | **human**                     | P11, irreversible                                                                                               |
| Lifting the publishing pause           | **human**                     | MSR-18                                                                                                          |
| Changing the leading indicator set     | **human**, via PR             | MSR-01, P10                                                                                                     |

---

## 13. Prohibited

| Prohibition                                                   | Rule   | Why                                                                          |
| ------------------------------------------------------------- | ------ | ---------------------------------------------------------------------------- |
| Absolute traffic forecasts from a public CTR curve            | MSR-14 | 19–39.8% spread at position 1; the curve only ranks tasks against each other |
| `AVG(position)` or `AVG(ctr)` when merging rows               | MSR-12 | a one-impression tail query gets the weight of a head term                   |
| `SUM()` over a raw BigQuery table without `GROUP BY`          | MSR-09 | rows are not deduplicated; figures inflate silently                          |
| `WHERE query IS NOT NULL` as an anonymization filter          | MSR-10 | an anonymized query is an empty string                                       |
| Full-corpus URL inspection                                    | MSR-05 | 2,000 QPD per site; the quota burns in a day                                 |
| Comparing windows without trimming the last 3–4 days          | MSR-06 | false decay on every run                                                     |
| Growth metrics computed on the branded segment                | MSR-04 | marketing masks a content failure                                            |
| Applying thresholds across mixed locales                      | MSR-22 | the average describes no market                                              |
| Penalty monitoring via the Manual Actions API                 | MSR-17 | no manual action for scaled content abuse exists                             |
| Re-measuring decay sooner than 4 weeks after a fix            | §5.4   | reindexing takes 4–12 weeks                                                  |
| Silent recomputation on an `epoch_version` increment          | MSR-11 | destroys the ability to understand why a conclusion changed                  |
| Automatically lifting the publishing pause                    | MSR-18 | asymmetry: a false pause costs weeks, a missed penalty costs the domain      |
| Auto-publishing off the back of any finding                   | §11.2  | "nothing auto-publishes", P11                                                |
| Using traffic as an acceptance criterion in the first 90 days | MSR-03 | a lagging indicator; it will write off a working system                      |
| Measuring AI citation rate through GSC                        | MSR-15 | impressions only, no queries and no clicks                                   |

---

## 14. Conflicts and open questions

**1. Striking-distance thresholds disagree by two orders of magnitude.** The owner's working system:
`min_impressions = 20`, band 5–20. Published practice: `impressions ≥ 1000`, position ≤ 10. Both are
correct at their own scale. Resolved by calibration in the first quarter; until then the reference pilot runs the
low threshold, and that is recorded as a decision rather than a default.

**2. Cannibalization threshold: 2 or 3 URLs.** The working code flags from two, the reviews recommend
three. Two produces more noise, but on a YMYL corpus with an obvious `/credits/` × `/credit-online/`
× `/mfo/` problem, missing it costs more than double-checking. Start at two, tighten as noise
dictates.

**3. The two CTR curves disagree at positions 2–5** (12.1% versus 15%; 3.4% versus 5%). Both are in
this file deliberately. Which is closer to the truth for Ukrainian financial SERPs is unknown and
will only be settled by calibration. Until then, every potential estimate is provisional.

**4. `is_ai_overview` in BigQuery is unresolved** (MSR-16). Closed by a single query on the day the
project is connected.

**5. Every `[expert judgment]` threshold is uncalibrated on any corpus.** This applies to all of §8
(cohort alarms), to `flip_rate`, to the inspection budget and to the blend formula `w`. The pilot's
first quarter is for collecting distributions, not for testing hypotheses. The first quarterly report
must contain a "what we had to change and why" section (P15).

**6. Scale conflict with P2.** The cohort monitor needs roughly 10 pages per cohort for the
normalized metrics to hold still. At 4–8 articles a month, a monthly cohort is too small. Pilot
resolution: cohorts are **quarterly**, not monthly, while the pace is under 10 pages per month. This
reduces sensitivity, and it is a conscious price paid for P2.

**7. Locale multiplies the sample problem.** §0.1 requires every detector to run per locale, which
divides an already thin sample. On a three-locale site with the pilot's publishing pace, per-locale
cohorts may never reach usable size. Pilot resolution: cohort monitoring runs on the primary locale
only, and secondary locales are watched through the technical-defect register (LI-6) until their
volume supports statistics. Flagged, not solved.

---

## Sources

Official Google documentation:

- [Search Analytics: query — API reference](https://developers.google.com/webmaster-tools/v1/searchanalytics/query)
- [Search Console API usage limits](https://developers.google.com/webmaster-tools/limits)
- [Table guidelines and reference (BigQuery bulk export)](https://support.google.com/webmasters/answer/12917991)
- [Query guidelines and sample queries](https://support.google.com/webmasters/answer/12917174)
- [About bulk data export to BigQuery](https://support.google.com/webmasters/answer/12918484)
- [BigQuery efficiency tips for Search Console bulk data exports](https://developers.google.com/search/blog/2023/06/bigquery-efficiency-tips)
- [A deep dive into Search Console performance data filtering and limits (2022-10)](https://developers.google.com/search/blog/2022/10/performance-data-deep-dive)
- [Introducing Search Generative AI performance reports (2026-06-03)](https://developers.google.com/search/blog/2026/06/gen-ai-performance-reports)
- [Bing Webmaster Tools documentation](https://learn.microsoft.com/en-us/bingwebmaster/) · [IndexNow](https://www.indexnow.org/documentation)

Studies and analyses:

- First Page Sage / SISTRIX, 2026 CTR summary — [indexsy.com/ctr-statistics](https://indexsy.com/ctr-statistics/)
- Seer Interactive, AI Overviews CTR — [wordsatscale.com](https://wordsatscale.com/ai-overviews-ctr-statistics-2026/)
- [Search Engine Journal — Google Now Reports AI Search Impressions (2026-08-04)](https://www.searchenginejournal.com/google-reports-ai-search-impressions-how-to-read-them/582824/)
- [aioseo.fr — Generative AI Report (2026-07-18)](https://aioseo.fr/en/google-search-console-generative-ai-report-how-to-analyze-it/)
- [thatdevpro — GSC Audit Framework + SQL](https://www.thatdevpro.com/insights/framework-gscanalysis/)
- [JC Chouinard — Keyword Cannibalization Tool with Python](https://www.jcchouinard.com/keyword-cannibalization-tool-with-python/)
- [SEJ — Find Keyword Cannibalization Using Text Embeddings](https://www.searchenginejournal.com/find-keyword-cannibalization-using-openai-text-embeddings-examples/520274/)

Internal:

- `EVIDENCE.md#e04-search-console` — the section's primary source
- `[internal observation, unpublished]` — `the audited system's analyzer`, thresholds, the three action tiers
- `EVIDENCE.md#e12-data-apis-and-pricing` — Bing limits, the 2026-08-31 JSON deadline
- `EVIDENCE.md#e13-policy-and-risk` — the absence of a manual action for scaled content
- `EVIDENCE.md#e14-content-operations` — the cohort collapse trajectory
- `EVIDENCE.md#e08-trend-detection` — GSC hourly data lives 8 days
