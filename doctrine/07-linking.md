# 07 — Internal Linking, Topical Authority, Anti-Cannibalization

**Version:** 0.1.0 · **Date:** 2026-08-07 · **Review cadence:** every 90 days
**Subordinate to:** [`00-principles.md`](00-principles.md), above all **P6** (one page, one intent, one URL) and **P7** (an irrelevant link is harmful, not neutral).
**Depends on:** `02-semantics.md` (clusters, intents, embeddings), `08-measurement.md` (Search Console data), `06-review-lenses.md` (human confirmation).
**Writes to:** `.kiln/corpus.json`, `.kiln/links.json`, `.kiln/anchors.json`, `.kiln/measurements/linking/`.

---

## 0. What this module does and does not do

This module owns the thing the original brief called "turning the site into a Wikipedia": corpus connectivity. Wikipedia is not a volume of text, it is a graph in which every term has exactly one canonical page and links appear where they help you understand the paragraph you are reading.

**Does:** builds and maintains the page and anchor graph; proposes donor→target pairs; enforces the one-anchor-one-URL invariant; computes graph health and topical radius; detects cannibalization from Search Console data; prepares consolidation and redirect decisions for a human.

**Does not:** touch navigation, menus, breadcrumbs or the footer — a separate mechanism carrying different weight (`LNK-24`); execute consolidations, redirects or deletions on its own (P11); place any link that has not cleared every gate in §2.

**The unit of work is a wave.** The module never processes a whole site. It takes a slice (a cluster, a section, a sample), changes it, measures it under the protocol in §9, and only then moves on.

---

## 1. Graph model

### 1.1 `.kiln/corpus.json` — nodes

One record per indexable URL. Fields the module requires:

| Field                              | Type     | Source                    | Meaning                                                               |
| ---------------------------------- | -------- | ------------------------- | --------------------------------------------------------------------- |
| `url`                              | string   | adapter                   | canonical absolute URL, always a terminal 200                         |
| `status_code`                      | int      | crawl                     | 200 / 301 / 404; only a 200 may serve as a link target                |
| `canonical`                        | string   | HTML                      | if ≠ `url`, the node is excluded from the target pool                 |
| `type`                             | enum     | onboarding + rules        | `pillar` / `cluster` / `definition` / `commercial` / `index` / `news` |
| `cluster_id`                       | string   | `02-semantics.md`         | topical cluster membership                                            |
| `intent`                           | enum     | `02-semantics.md`         | the intent of the page, not of a query                                |
| `primary_entity`                   | string   | extraction                | the page's head entity; for `definition`, the term being defined      |
| `entities[]`                       | string[] | extraction                | entities mentioned                                                    |
| `page_embedding`                   | vector   | bge-m3, local             | embedding of the whole page                                           |
| `chunk_embeddings[]`               | vector[] | bge-m3                    | passage embeddings (~500 tokens) with each passage's document offset  |
| `word_count`                       | int      | code                      | **Unicode-aware tokenization, mandatory** (P5)                        |
| `depth_from_home`                  | int      | graph traversal           | minimum click depth from the home page                                |
| `inlinks_count` / `outlinks_count` | int      | graph                     | node degrees                                                          |
| `is_orphan`                        | bool     | graph                     | no inbound contextual links                                           |
| `link_score`                       | float    | computed                  | internal PageRank, normalized 0–100                                   |
| `site_radius`                      | float    | computed                  | cosine distance to the corpus centroid, see §8                        |
| `external_links_count`             | int      | Ahrefs CSV / OpenPageRank | external links: the entry ticket into the citation candidate pool     |
| `published_at` / `updated_at`      | date     | adapter                   | real dates, not `now()`                                               |
| `gsc_90d`                          | object   | `08-measurement.md`       | `{impressions, clicks, avg_position}` over 90 days, non-brand slice   |

**Rule `LNK-01` (BLOCK, code).** A node with `status_code ≠ 200` or `canonical ≠ url` cannot be a link target. Linking to a redirect is a cheap leak of authority; swapping 301s for their 200 destinations produced a positive result in a controlled split test. `[source: SearchPilot, "internal redirects"]`

### 1.2 `.kiln/links.json` — edges

| Field                              | Meaning                                                                                                 |
| ---------------------------------- | ------------------------------------------------------------------------------------------------------- |
| `from_url` / `to_url`              | donor and target                                                                                        |
| `anchor_raw` / `anchor_normalized` | anchor text as written, and normalized (case, punctuation, language-specific lemmatization)             |
| `anchor_type`                      | `exact` / `partial` / `entity` / `brand` / `natural`                                                    |
| `position_ratio`                   | where in the document the link sits: 0.0 is the opening, 1.0 the end                                    |
| `zone`                             | `body` / `nav` / `sidebar` / `footer` / `related` — only `body` counts toward the contextual link graph |
| `created_by`                       | `kiln` / `human` / `legacy`                                                                             |
| `wave_id`                          | the wave that placed it, required by the measurement protocol in §9                                     |
| `rule_ids[]`                       | which module rules fired at placement time (for P8)                                                     |

### 1.3 `.kiln/anchors.json` — the anchor registry

The single source of truth for the phrase → URL mapping. Keyed by `anchor_normalized`.

```json
{
  "кредит онлайн на карту": {
    "target_url": "https://example.com/credits/online-na-kartu",
    "usages": 14,
    "types": { "exact": 3, "partial": 6, "entity": 2, "natural": 3 },
    "locked_at": "2026-08-12",
    "locked_by": "human"
  }
}
```

**Locale note.** The registry is site-wide but maintained **per locale**, and the one-anchor-one-URL invariant is enforced _within_ a locale, never across locales. The same phrase in `uk` and `ru` is two separate records, because each locale has its own canonical URL; a cross-locale collision is not a conflict and must never be reported as one.

Anchor normalization — including the lemmatization the doctrine requires for inflected languages — is defined in the language pack (`doctrine/lang/<code>.md`), not here. This is not a formality: without lemmatization the invariant fails **silently** for Cyrillic, because inflected forms of the same phrase never collide in the registry and the conflict is simply never surfaced.

### 1.4 Build and refresh

```
0. The adapter yields the corpus (see adapter/SPEC.md): URL list + HTML or markdown + metadata.
1. graph_build.py: parse links, zones, anchors -> links.json; compute depth, link_score, orphans.
2. Embeddings: page + passages -> corpus.json (re-embed only what changed, keyed on text_hash).
3. Corpus centroid and per-page site_radius -> §8.
4. anchors.json is rebuilt from links.json; conflicts (§5) go into the report.
5. graph_health.py: metrics from §1.5 -> .kiln/measurements/linking/<date>.json.
6. link_suggest.py: proposals for the current wave -> human review.
```

The graph is rebuilt in full on every run; only embeddings (keyed on text hash) and Search Console data are updated incrementally.

**Rule `LNK-02` (WARN, code).** If more than 50% of corpus records carry an `updated_at` equal to the run date, the field is generated dynamically and is unusable. This has been observed on a live project: `dateModified` returned `now()` on every request, and two requests 27 seconds apart produced different timestamps. In that case the module must fall back to change detection by `text_hash` and flag `updated_at` as untrustworthy. `[internal observation, unpublished]`

### 1.5 Graph health metrics

Computed every run; history is retained, because the trend matters more than the absolute value.

| Metric                                                       | Computation                                            | Target / alert                                                                     |
| ------------------------------------------------------------ | ------------------------------------------------------ | ---------------------------------------------------------------------------------- |
| `orphan_rate`                                                | orphans among indexable / all indexable                | target 0 `[expert judgment]`                                                       |
| `depth_p50`, `depth_p90`, `share_deeper_3`, `share_deeper_5` | distribution of `depth_from_home`                      | priority pages ≤3, all ≤5 `[secondary source, not primarily verified]`             |
| `inlinks_p10`, `share_inlinks_lt_3`                          | distribution of inbound links                          | ≥3 inbound per indexable page `[expert judgment]`                                  |
| `link_score_gini`                                            | Gini coefficient over `link_score`                     | alert on a sharp rise: all authority has pooled in 5% of pages `[expert judgment]` |
| `redirect_links_count`                                       | links pointing at 301/404                              | target 0 `[source: SearchPilot]`                                                   |
| `body_link_share`                                            | share of internal links in the `body` zone             | trend upward                                                                       |
| `exact_match_share(target)`                                  | share of `exact` anchors pointing at a target          | alert above 30% `[expert judgment, needs calibration]`                             |
| `ambiguous_anchors`                                          | count of `anchor_normalized` values with >1 target     | alert above 0 — this is cannibalization in machine-readable form                   |
| `anchor_diversity(target)`                                   | unique phrases / total links to that target            | trend upward                                                                       |
| `site_focus`                                                 | mean cosine proximity of pages to the centroid         | trend, §8                                                                          |
| `site_radius_p90` + outlier list                             | §8                                                     | outliers go to human review                                                        |
| `cluster_coverage`                                           | share of clusters holding a `pillar` and ≥N satellites | target: every priority cluster                                                     |

---

## 2. Selecting the donor → target pair

Seven gates, in strict order. A link is placed only if **all** of them pass. Any failure is a rejection, with no route around it.

**Gate 1. Candidate retrieval (code).**
Cosine similarity between the donor passage and the target page. Threshold **0.78** `[expert judgment, needs calibration; working range 0.78–0.85]`. Anything below **0.50** is noise and is discarded unconditionally.
Embeddings operate here and only here. They take no part in any later gate.

**Gate 2. Hierarchy (code).**
Permitted directions:

| From      | To           | When                                  |
| --------- | ------------ | ------------------------------------- |
| `cluster` | `pillar`     | always                                |
| `pillar`  | `cluster`    | for priority satellites               |
| `cluster` | `cluster`    | **only within the same `cluster_id`** |
| any       | `definition` | on first mention of the term          |
| any       | `commercial` | on intent match                       |

Direct `cluster→cluster` links across different clusters are forbidden; cross-cluster movement runs through the `pillar`. This is the literal answer to Google's own warning: if every page links to every page, there is no structure and the system cannot tell which page matters. `[source: Google statement]`

**Gate 3. Anchor relevance (agent).**
Question to the model: "does anchor X describe the content of page Y?" The answer is binary. "No" is a rejection.
This guards against `anchorMismatchDemotion` — a demotion for topical mismatch between donor and target. Internal anchors are counted separately from external ones (`SimplifiedAnchor`), which means the internal anchor profile can be degraded independently of the external one, entirely by your own hand. `[source: Content Warehouse leak]`

**Gate 4. The Wikipedia criterion (agent).**
"Would reading the target page help the reader understand this paragraph?" No is a rejection.

Why this question is mandatory on top of cosine similarity. High similarity means two pages are **about the same thing** — which is precisely the case where a link is useless: the reader is already in the relevant context, and the target adds nothing to their understanding of the paragraph. A useful link usually connects the text to something **mentioned but not unpacked**: a term, a method, an entity, an adjacent level of the hierarchy. Cosine similarity scores such pairs middling, and scores outright duplicates high. A mechanical threshold without this question therefore places links systematically in the wrong spots: it detects sameness where the job calls for complementarity.

**Gate 5. Target prioritization (code).**
Candidate ordering: (a) orphans and pages with `link_score` below the median; (b) `depth_from_home > 3`; (c) pages sitting in positions 5–20 in Search Console (striking distance); (d) pages with high conversion; (e) hubs that already hold external links — external links get a page into the citation candidate pool, internal links carry that status onward.

**Gate 6. Position (code).** See §3.

**Gate 7. The anchor invariant (code).** See §5.

**Rule `LNK-03` (BLOCK, code).** A link placed without clearing gates 2–4 is a defect, not an optimization. A cosine threshold is not sufficient grounds on its own (P7).

**Rule `LNK-04` (BLOCK, code).** The similarity threshold may not be lowered to fill a proposal quota. If fewer candidates survive the gates than the plan called for, the plan goes unmet, and that is a normal outcome of a run.

### Anchor generation

The agent receives: the donor paragraph, the target's `title` and opening paragraph, the target's `primary_entity`, and the list of anchors already pointing at it.

Requirements: the anchor is an existing phrase **from the donor's own text**, or a minimally altered one; it describes the destination's subject, not its format; 2–6 words. Forbidden: "read also", "here", "learn more", "my full guide" — none of them describe the target, and all of them are worthless for passage-level extraction.

Enforced type distribution per target: `exact` ≤ 30%, the remainder spread across `partial`, `entity`, `brand`, `natural`. Checked against `anchors.json` **before** the edge is written.

---

## 3. Link position

**Rule `LNK-05` (WARN, code).** Priority links go in the **first third of the document** (`position_ratio ≤ 0.33`), inside the body of a paragraph.

Two independent lines of evidence converge on the same point. This is the most robust conclusion in the entire body of research on the topic.

**Line 1 — ranking.** A controlled split test: subcategory link buttons placed at the top of a category page produced **+25%** organic traffic (roughly 9,200 sessions per month); semantically equivalent links in the home page footer produced **+5%**. A fivefold difference with identical link content. This is exactly what the reasonable surfer patent (US8117209B1) predicts: link weight is proportional to click probability, which is driven by position on the page, font size, and the topical relationship of the anchor. `[source: SearchPilot; patent US8117209B1]`

**Line 2 — citation.** **44.2%** of all LLM citations are drawn from the first 30% of a document. `[source: EVIDENCE.md#e06-internal-linking, §7]`

**Rule `LNK-06` (INFO, code).** Links in the `related`, `sidebar` and `footer` zones do not count as contextual and do not count toward a wave's plan.

The reason is technical rather than aesthetic: extraction for AI answers happens **at the passage level**, not the page level. A "read also" block, a sidebar and a footer never land inside an extracted passage, so as far as citability is concerned they do not exist. They remain useful for navigation and crawl paths, but that is a different job and a different module (`LNK-24`).

One further argument against building on such blocks: in a controlled test of a "related articles" module, the **donor** won, while the effect on targets was inconclusive. `[source: SearchPilot]`

---

## 4. Limits

Every value is a default in `.kiln/thresholds.yml`, calibrated per project, and never promoted into the shared doctrine (P10).

| ID       | Parameter                           | Value                                         | Rationale                                                                                                                                                                                        |
| -------- | ----------------------------------- | --------------------------------------------- | ------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------ |
| `LNK-07` | New links per run, per page         | **≤ 3**                                       | Dilution: every new link reduces the share carried by the rest. A test that **reduced** the number of links in a module produced a positive result. `[source: SearchPilot]`                      |
| `LNK-08` | Contextual links in body            | **≤ 1 per 250–300 words**, hard ceiling ~15   | Overlinking under the Wikipedia criterion, plus Google's warning about everything linking to everything. Word counts must be Unicode-aware (P5). `[expert judgment, needs calibration]`          |
| `LNK-09` | Links to one URL from one page      | **1**, on first mention                       | Wikipedia's first-mention rule. Probably related to `droppedLocalAnchorCount` — some internal links are not counted at all, mechanism unknown. `[source: Wikipedia MoS; Content Warehouse leak]` |
| `LNK-10` | Cosine threshold                    | **0.78** (range 0.78–0.85), noise cutoff 0.50 | Below this, `anchorMismatchDemotion` risk. Highly dependent on niche and embedding model. `[expert judgment, needs calibration]`                                                                 |
| `LNK-11` | Share of `exact` anchors per target | **≤ 30%**                                     | The internal anchor profile is counted separately (`SimplifiedAnchor`) and over-optimizes independently of the external one. `[source: leak]`                                                    |
| `LNK-12` | Click depth                         | **≤ 3** for priority pages, **≤ 5** for all   | A cheap, safe operational threshold. `[secondary source, not primarily verified]`                                                                                                                |
| `LNK-13` | Inbound links per indexable page    | **≥ 3**                                       | No orphans. `[expert judgment]`                                                                                                                                                                  |
| `LNK-14` | Share of site per wave              | **≤ 10%**                                     | Wave-based rollout is mandatory for a valid measurement (§9). `[expert judgment]`                                                                                                                |

**Rule `LNK-15` (WARN, code).** `LNK-07`, `LNK-08` and `LNK-14` are evaluated as a 90-day rolling accumulation per page, not per run. A per-run limit alone is trivially circumventable: three consecutive runs place three links each and the page has nine.

---

## 5. The one-anchor-one-URL invariant

**Rule `LNK-16` (BLOCK, code).** One `anchor_normalized` value points at exactly one URL within a locale. A violation is cannibalization in machine-verifiable form.

**How it is checked.** After every rebuild of `anchors.json`, group edges by `anchor_normalized` and compute `COUNT(DISTINCT to_url)`. Any value above 1 is a conflict.

**Normalization** must be language-specific and lives in `doctrine/lang/<code>.md`: lowercasing, punctuation stripping, lemmatization. For Ukrainian and Russian the invariant does not function without lemmatization — "кредит онлайн" and "кредиту онлайн" land in separate records and the conflict never surfaces. For English, casing plus stemming suffices.

**On conflict.**

1. Establish the owner of the phrase: the page with greater impressions for the corresponding query over 90 days. Impressions, not clicks: impressions tell you what Google considers relevant, clicks tell you what it considers attractive.
2. Repoint every other link carrying that phrase to the owner, **or** rewrite the anchor to match its own target's actual subject.
3. Record `locked_at` / `locked_by` in the registry. A locked phrase is never reassigned by automation again.
4. If the conflicting pages compete not only in anchors but in the SERP, hand off to §6.

**Rule `LNK-17` (BLOCK, code).** Automated embedding-based linking breaks the invariant of its own accord: two pages in the same cluster have neighbouring embeddings, and the anchor generator hands them identical natural phrases. The anchor gate (gate 7) is therefore mandatory at **every single placement**, not merely in a periodic audit. Without an explicit prohibition, the auto-linking mechanism **produces** the very cannibalization this module later treats.

---

## 6. Cannibalization decision tree

### 6.1 Detection (code)

The source is the URL-level Search Console table (`searchdata_url_impression` in BigQuery, or the `page × query` slice from the API). The property-level table is unusable for this: it does not separate two of our URLs answering the same query. `[source: official Google documentation]`

Mandatory preprocessing, without which the numbers lie:

- `GROUP BY` before aggregation — export rows are **not deduplicated**;
- an anonymized query arrives as an empty string, not NULL: `WHERE query != ''`;
- drop the last **3–4 days**; they are always understated;
- use the **non-brand** slice only: for its own brand a site legitimately holds several positions;
- average position is `SUM(sum_position)/SUM(impressions) + 1` — the field is 0-based.

Candidate thresholds `[expert judgment, needs calibration; thresholds sourced from practitioners]`:

| Condition                   | Value                      |
| --------------------------- | -------------------------- |
| Distinct URLs for the query | ≥ 3 (lenient variant: ≥ 2) |
| Clicks on the second URL    | ≥ 3 over the window        |
| Window                      | 90 days                    |
| `flip_rate`                 | ≥ 0.30                     |

```
flip_rate = (number of days the leading URL changed) / (days with impressions − 1)
```

`flip_rate` is the most honest signal available: it separates "Google cannot decide" from "two pages simply both surface sometimes". A candidate without a high `flip_rate` is usually not cannibalization but ordinary coexistence.

**Rule `LNK-25` (WARN, code).** A query meeting every candidate condition above **and** carrying a `flip_rate` at or over the threshold is reported as a cannibalization candidate. The finding carries the decision package required by `LNK-18`: both pages, the window metrics, `flip_rate`, cosine similarity where embeddings were supplied, and the proposed branch of §6.2 with its rationale. It proposes; it never executes. Severity is WARN rather than BLOCK because the finding stops nothing on its own — the block sits on the irreversible action, in `LNK-18`.

**Rule `LNK-26` (INFO, code).** A query meeting the candidate conditions but whose `flip_rate` falls below the threshold is recorded as coexistence rather than discarded. Two pages legitimately surfacing for one query is a normal state, and the record exists so the first runs on a project accumulate the real `flip_rate` distribution. Every threshold in §6.1 is uncalibrated, and an observation thrown away cannot calibrate anything later.

### 6.2 Decision (agent prepares, human approves)

```
Do the pages share the same INTENT (not merely the same query)?
│
├── NO ───────────────► DIFFERENTIATE
│     Different target queries, different title/H1, different angle.
│     Remove cross-links carrying the competing anchors.
│     Each page links to its own pillar.
│     Lock the anchor phrases to their owners (§5).
│     Reversible. Executor: agent + human confirmation.
│
└── YES
    │  cosine between page texts ≥ 0.90 -> the texts duplicate each other
    │
    ├── One page is clearly stronger (impressions, external links, conversion)
    │   and the weaker one adds nothing new
    │        ───────────► 301 the weak page onto the strong one
    │                     + rewrite EVERY internal link to the final URL,
    │                       never to the redirect (LNK-01)
    │                     Irreversible. Human only (P11).
    │
    └── Both carry value / both hold external links
             ───────────► CONSOLIDATE
                          One document, 301 the rest,
                          migrate the unique blocks,
                          rebuild the anchor profile.
                          Irreversible. Human only (P11).
```

The cosine threshold of **0.90** for the consolidate-or-differentiate decision is `[expert judgment, needs calibration]`: below it the pages are genuinely distinct and are treated by differentiation; above it they are consolidation candidates.

**Rule `LNK-18` (BLOCK, human).** Consolidation, 301s and page deletion are executed by a human only. These are irreversible actions against an existing corpus (P11). The agent prepares the package: both pages, 90-day metrics, `flip_rate`, cosine similarity, the list of internal links that will have to be rewritten, and a proposed decision with its rationale.

**Rule `LNK-19` (WARN, agent).** Differentiating intents is preferred over a 301 whenever the weaker page carries any unique value at all. Internal anchors are the fastest way to tell a search engine which page owns a topic; once every link carrying a phrase points at a single owner, cannibalization frequently subsides without any redirect.

---

## 7. The definition page layer

**Rule `LNK-20` (INFO, human + agent).** Every niche gets a layer of canonical definition pages: one page per term or entity. This layer is the foundation of the graph and the first wave's priority on any new project.

**Why this layer specifically.**

1. **It is the best citation asset available.** Extraction works in passages, and a definition is the ideal self-contained passage: it answers the question in full, with no surrounding context required. The self-sufficiency requirement from P12 is satisfied naturally by a definition page.
2. **It gives the graph its convergence points.** Any overview article mentioning a term has one unambiguous target. Without such a layer, links to a term scatter across arbitrary pages and generate the conflicts described in §5.
3. **There is confirmation at scale.** Investopedia's A–Z glossary draws roughly 44 million visits a month, and most of its entries run past 2,000 words — full articles, not stubs. `[source: Investopedia teardown, secondary]`
4. **There are unclaimed niches.** Established on one of our own projects: a major vendor glossary has a Russian version and no Ukrainian one, while a second has English only. Ukrainian-language terminology in that field is claimed by nobody. A definition layer is the cheapest way into a niche like that. `[internal observation, unpublished]`

**How to build it.** Terms are drawn from the corpus `entities[]` and from semantics, then ranked by frequency of mention inside the corpus multiplied by evidence of search demand. A definition page must: answer "what is it" within the first 40–60 words; carry a single `primary_entity`; and contain original contribution under P13 (a case from the project's own practice, an original calculation, an analysis of a primary source). Without that it is a dictionary paraphrase, and a paraphrase does not clear the gates in `10-safety-gates.md`.

**Rule `LNK-21` (WARN, code).** A link to a definition page is placed on the **first occurrence** of the term in a document. Repetition is permitted only in tables, captions and callouts. This replaces the "N links per article" quota: a quota breeds artificial insertions, a first-mention rule does not.

---

## 8. Topical radius

The Content Warehouse leak contains `siteFocusScore` (how tightly a site holds a single topic) and `siteRadius` (how far a page's embedding deviates from the site's). The exact formula is unknown, but **an approximation is computable on our own embeddings**, and its trend is useful. `[source: Content Warehouse leak]`

**Computation (code).**

```
centroid       = mean(page_embedding for page in corpus if page.indexable)
site_radius(p) = 1 − cosine(p.page_embedding, centroid)
site_focus     = 1 − mean(site_radius(p) for p in corpus)
```

The centroid is computed over indexable pages only, excluding utility pages and `index` listings — otherwise navigational pages drag it toward boilerplate.

**How to read it.**

| Observation                                   | Interpretation                                     | Action                                                                            |
| --------------------------------------------- | -------------------------------------------------- | --------------------------------------------------------------------------------- |
| `site_focus` rising                           | the corpus is consolidating around its topic       | continue                                                                          |
| `site_focus` falling as page count grows      | the site is spreading across topics                | check whether a new vertical was opened without a decision                        |
| A single page in the top 10% of `site_radius` | either foreign material or a legitimate new branch | human review                                                                      |
| An entire cluster at high radius              | a new vertical                                     | owner's decision: develop as a separate direction, move to a subdomain, or retire |

**Rule `LNK-22` (INFO, human).** `site_radius` outliers are never removed automatically. A high radius raises the question "why is this here", not a verdict. The answer comes from a human at onboarding or at the quarterly review.

**An honest limitation.** The absolute value of our approximation is not comparable to Google's internal metric — it can only be compared against our own past values computed with the same embedding model. Changing the embedding model resets the metric's history, and that reset must be recorded in `CHANGELOG.md`.

---

## 9. Effect measurement protocol

**Rule `LNK-23` (BLOCK, code).** A linking measurement without all three groups is invalid and does not enter any report.

| Group                          | Membership                                                                                     | What it catches                     |
| ------------------------------ | ---------------------------------------------------------------------------------------------- | ----------------------------------- |
| A. Donors                      | pages that received new outbound links                                                         | the effect on the donor page itself |
| B. Targets                     | pages that received new inbound links                                                          | the classic expected effect         |
| C. **Untouched, same section** | pages the wave never touched, but which share a section and the same sources of link authority | **dilution**                        |

Group C is not a formality. Without it the module will report gains on B while failing to notice that the authority drained out of C, leaving the net result flat or negative.

A second consequence of the data: **the effect must be measured in both directions**. The naive model in which authority flows from donor to target is wrong — in the controlled "related articles" test only the donor won, while in the button test both groups won. Adding relevant links improves the relevance signals of the donor page itself. `[source: SearchPilot]`

**Procedure.**

1. Fix the group membership before the wave and record `wave_id` in `links.json`.
2. Take the baseline: 28 days prior to the wave, non-brand slice, metrics per group.
3. Roll out the wave across ≤10% of the site (`LNK-14`).
4. Wait for reindexing: **4–12 weeks**. Do not measure earlier.
5. Take the measurement; compare deltas for A, B and C against the baseline and against the site-wide median.
6. Record the result in `.kiln/measurements/linking/`, including a **negative** one (P15).

Waves must not overlap on pages: a page that entered group C of one wave cannot serve as a donor or target of another wave until that measurement closes.

---

## 10. Prohibitions

| ID        | Prohibition                                                                                 | Why                                                                                                                         |
| --------- | ------------------------------------------------------------------------------------------- | --------------------------------------------------------------------------------------------------------------------------- |
| `LNK-Z1`  | Linking everything to everything inside a section                                           | Google's explicit statement: if every page links to every page there is no structure and nothing signals which page matters |
| `LNK-Z2`  | Placing a link on cosine similarity alone, without the hierarchy and anchor relevance gates | `anchorMismatchDemotion` makes an irrelevant link a negative event, not a neutral one (P7)                                  |
| `LNK-Z3`  | One anchor pointing at two different URLs                                                   | Direct manufacture of cannibalization (`LNK-16`)                                                                            |
| `LNK-Z4`  | The same `exact` anchor on every link to a page                                             | The internal anchor profile over-optimizes independently of the external one (`SimplifiedAnchor`)                           |
| `LNK-Z5`  | Lowering the similarity threshold to fill a quota                                           | The quota is not the goal; falling short of candidates is normal (`LNK-04`)                                                 |
| `LNK-Z6`  | Rolling a new rule out across the whole site at once                                        | Without a control group the result is uninterpretable (`LNK-23`)                                                            |
| `LNK-Z7`  | Handling navigation, menus, footer and breadcrumbs with the same module as contextual links | Different mechanisms carrying different weight; mixing them renders measurement meaningless                                 |
| `LNK-Z8`  | Linking to 301s and 404s                                                                    | Authority leak; replacing 301s with their destinations yields a measurable gain                                             |
| `LNK-Z9`  | Expecting a GEO effect from links in sidebars, footers and "read also" blocks               | They never land in an extractable passage                                                                                   |
| `LNK-Z10` | Measuring text length without Unicode-aware tokenization                                    | `wc -w` does not split Cyrillic into words; on a live measurement the conclusion came out inverted (P5)                     |

**Rule `LNK-24` (BLOCK, code).** Navigational and template links are excluded from the contextual link graph at parse time, by zone, but still count toward `depth_from_home`. Mixing zones is the single most common reason graph metrics look healthy on a dead site.

---

## 11. Layer 2 scripts

Autonomous: they know nothing about any specific site, and their input and output are files. No calls into a project database, no secrets inside.

### `graph_build.py`

```
In:   --corpus corpus.json  (URL, html|markdown, adapter metadata)
      --config thresholds.yml
Out:  links.json, corpus.json (enriched: depth, link_score, is_orphan,
      inlinks_count, outlinks_count), anchors.json
```

Parses links with zone detection (`body` / `nav` / `sidebar` / `footer` / `related`), normalizes anchors using the language rules selected by `--lang`, computes `depth_from_home` by breadth-first traversal from the root, and `link_score` as an iterative PageRank over contextual links, normalized to 0–100.

### `link_suggest.py`

```
In:   --corpus corpus.json --links links.json --anchors anchors.json
      --embeddings embeddings.npz --gsc gsc_90d.json
      --wave-size N --config thresholds.yml
Out:  suggestions.json
```

Proposal format:

```json
{
  "from_url": "...",
  "to_url": "...",
  "paragraph_id": "p17",
  "position_ratio": 0.28,
  "anchor_proposed": "...",
  "anchor_type": "partial",
  "cosine": 0.81,
  "gates": { "hierarchy": "pass", "anchor_relevance": null, "wikipedia": null },
  "acceptor_reason": "orphan|striking_distance|low_link_score|depth>3|conversion",
  "rule_ids": ["LNK-05", "LNK-09"]
}
```

The script deliberately **does not execute** gates 3 and 4. It leaves them `null` and hands them to the agent. The script does only what code can compute reproducibly.

### `cannibal_detect.py`

```
In:   --gsc gsc_url_query.csv|json  (query, url, clicks, impressions, sum_position, date)
      --embeddings embeddings.npz
      --brand-tokens brand.txt
      --window 90 --config thresholds.yml
Out:  cannibalization.json
```

Performs the §6.1 preprocessing (deduplication, empty-query filtering, the 3–4 day tail cut, the non-brand filter), computes daily `flip_rate` and the cosine similarity between pages, and assigns each candidate to one of the three outcomes in the §6.2 tree as a **proposal**, never as a decision.

### `graph_health.py`

```
In:   --corpus corpus.json --links links.json --anchors anchors.json
      --embeddings embeddings.npz --history .kiln/measurements/linking/
Out:  health-<date>.json + health-report.md
```

Computes every metric in §1.5, compares against the previous run, and emits the alert list plus `site_radius` outliers for review.

---

## 12. Rule summary

| ID       | Rule                                                              | Severity | Executor      |
| -------- | ----------------------------------------------------------------- | -------- | ------------- |
| `LNK-01` | Targets must be terminal 200s with a self-referencing canonical   | BLOCK    | code          |
| `LNK-02` | Dynamic `updated_at` → fall back to `text_hash` detection         | WARN     | code          |
| `LNK-03` | A link placed without gates 2–4 is a defect                       | BLOCK    | code          |
| `LNK-04` | The threshold is never lowered to fill a quota                    | BLOCK    | code          |
| `LNK-05` | Priority links go in the first third, inside a paragraph          | WARN     | code          |
| `LNK-06` | Links outside `body` do not count as contextual                   | INFO     | code          |
| `LNK-07` | ≤3 new links per run, per page                                    | WARN     | code          |
| `LNK-08` | ≤1 contextual link per 250–300 words, ceiling ~15                 | WARN     | code          |
| `LNK-09` | 1 link per URL per page, on first mention                         | WARN     | code          |
| `LNK-10` | Cosine threshold 0.78; noise cutoff 0.50                          | INFO     | code          |
| `LNK-11` | `exact` anchors ≤30% per target                                   | WARN     | code          |
| `LNK-12` | Depth ≤3 for priority pages, ≤5 for all                           | INFO     | code          |
| `LNK-13` | ≥3 inbound links per indexable page                               | WARN     | code          |
| `LNK-14` | ≤10% of the site per wave                                         | BLOCK    | code          |
| `LNK-15` | Limits accumulate on a 90-day rolling basis                       | WARN     | code          |
| `LNK-16` | One anchor, one URL                                               | BLOCK    | code          |
| `LNK-17` | The anchor gate runs at every placement, not periodically         | BLOCK    | code          |
| `LNK-18` | Consolidation, 301s and deletion are human-only                   | BLOCK    | human         |
| `LNK-19` | Differentiation is preferred over a 301 where value exists        | WARN     | agent         |
| `LNK-20` | The definition page layer is the first wave's priority            | INFO     | human + agent |
| `LNK-21` | Definition links are placed on first mention                      | WARN     | code          |
| `LNK-22` | `site_radius` outliers are never removed automatically            | INFO     | human         |
| `LNK-23` | A measurement without three groups is invalid                     | BLOCK    | code          |
| `LNK-24` | Navigation is excluded from the contextual link graph             | BLOCK    | code          |
| `LNK-25` | A cannibalization candidate is reported with its decision package | WARN     | code          |
| `LNK-26` | Coexistence below the flip threshold is recorded, not discarded   | INFO     | code          |

Every rule carries a counter in `.kiln/rules-stats.json`: applications, human overrides, and the outcome across affected pages (P8).

---

## 13. Not established — excluded from the rules

Listed explicitly so it does not seep back in during a future edit.

| Claim                                                                                    | Status                                                                                                                                                                                                             |
| ---------------------------------------------------------------------------------------- | ------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------ |
| "Ten internal links per page is optimal"                                                 | Never reproduced in any controlled test. Not taken into the spec                                                                                                                                                   |
| "+30% traffic with 3+ contextual links", "+43% organic"                                  | Before/after measurements with no control group, confounded by algorithm updates and parallel work. Usable only as a source of hypotheses                                                                          |
| "94% of top pages sit within 3 clicks of the home page"                                  | The primary publication is unverified; all available sources are secondary. Correlation, not causation: deep pages are often simply less valuable. `LNK-12` is retained as a cheap heuristic, not as a proven rule |
| The exact `siteFocusScore` / `siteRadius` formula                                        | Unknown. We use our own approximation and compare only against our own history                                                                                                                                     |
| The mechanics of `droppedLocalAnchorCount`                                               | It is unknown which internal links get discarded. Hypotheses: template blocks, duplicate anchors, exceeding a limit. Testable only by our own experiment                                                           |
| The optimal cosine threshold                                                             | 0.78 is a starting point, not a constant. Highly dependent on niche and embedding model                                                                                                                            |
| Cannibalization detection thresholds (≥3 URLs, ≥3 clicks, `flip_rate` ≥0.3, cosine 0.90) | Practitioner heuristics. The first run on a project must collect the distributions and calibrate them                                                                                                              |
| "The `babyPandaV2` hypothesis equals the Helpful Content Update"                         | Flagged as speculation by the author of the leak analysis himself. Not used                                                                                                                                        |

---

## 14. Conflicts and open questions

1. **A link that helps the reader versus a link that helps the graph.** Gates 3 and 4 optimize for the reader; gate 5 optimizes the distribution of authority. They diverge: an orphan needs a link, but no suitable paragraph may exist anywhere for it. Resolved in favour of the reader — an orphan for which no honest placement exists stays an orphan and lands in the report as a _content_ task (write the material where a link to it belongs), not as a linking task. This will look like an unmet wave plan; that is expected behaviour.

2. **The cosine threshold and the complementarity criterion pull in opposite directions** (§2, gate 4). High similarity raises the chance of clearing gate 1 and lowers the chance of clearing gate 4. For now the ordering of the gates papers over this, but the correct approach would be to find candidates not by page similarity but by "mentioned yet unexplained" — that is, by the entities in a paragraph that are absent from the donor's own corpus. This is a candidate doctrine change after the first run; it must reach a PR with a measurement attached, not with an argument.

3. **`LNK-14` (≤10% per wave) against the 4–12 week measurement window** (§9) yields a full site cycle in ten waves, i.e. a year to eighteen months. For a 4,000-URL corpus that is unacceptably slow. The compromise for the first project: waves are formed per cluster and group C is drawn from inside the same cluster, which allows several independent waves to run in parallel provided the clusters are genuinely unrelated.

   **Independence is now a recorded fact rather than an assumption.** `02-semantics.md` §9.3 adds `pillar_id` to the cluster model and `SEM-25 (BLOCK)` forbids assigning two clusters that share a non-NULL `pillar_id` to separately measured concurrent waves. Cross-cluster movement routes through the pillar (§4), so a shared pillar is a shared link path and the arms are not independent.

   What this does **not** solve: on a site where most clusters hang off a small number of pillars, the constraint bites hard and the parallelism largely disappears, returning us to the year-plus cycle. Whether the pilot's corpus is shaped that way is unknown until `pillar_id` is populated, and it should be checked before the first wave is planned rather than after. Recorded in `OPEN-QUESTIONS.md`.

4. **Search Console holds no citation data.** The generative surfaces report gives impressions only, with no queries, clicks or position. The effect of `LNK-05` and `LNK-20` on citation is therefore measured by the independent loop in `09-geo.md`, not by this module. Here we can measure ranking and nothing else.

---

## Sources

**Controlled experiments:** [SearchPilot: increasing internal linking (+25%)](https://www.searchpilot.com/resources/case-studies/seo-split-test-lessons-increasing-internal-linking) · [SearchPilot: impact of internal linking](https://www.searchpilot.com/resources/case-studies/impact-of-internal-linking-seo) · [SearchPilot: how to test internal links](https://www.searchpilot.com/resources/blog/internal-linking-tests) · [SearchPilot: split-test methodology](https://www.searchpilot.com/data-analysts)

**Leak and patents:** [iPullRank: Content Warehouse leak analysis](https://ipullrank.com/google-algo-leak) · [Search Engine Land: unpacking the leak](https://searchengineland.com/unpacking-googles-massive-search-documentation-leak-442716) · [Hobo: siteFocusScore / siteRadius](https://www.hobo-web.co.uk/topical-authority/) · [Szymon Słowik: SiteFocus and SiteRadius](https://www.szymonslowik.com/sitefocus-siteradius-and-topical-authority-in-seo/) · [Patent US8117209B1 — reasonable surfer](https://patents.google.com/patent/US8117209B1/en) · [SEO by the Sea: 2016 patent update](https://www.seobythesea.com/2016/04/googles-reasonable-surfer-patent-updated/)

**Google statements:** [SEJ: caution against too many internal links](https://www.searchenginejournal.com/google-cautions-against-using-too-many-internal-links/412553/)

**Search Console:** [Table guidelines and reference (BigQuery bulk export)](https://support.google.com/webmasters/answer/12917991) · [Search Analytics: query — API reference](https://developers.google.com/webmaster-tools/v1/searchanalytics/query) · [A deep dive into Search Console performance data filtering and limits](https://developers.google.com/search/blog/2022/10/performance-data-deep-dive)

**Cannibalization:** [Search Engine Land: cannibalization guide](https://searchengineland.com/guide/keyword-cannibalization) · [JC Chouinard: Keyword Cannibalization Tool with Python](https://www.jcchouinard.com/keyword-cannibalization-tool-with-python/) · [SEJ: cannibalization via embeddings](https://www.searchenginejournal.com/find-keyword-cannibalization-using-openai-text-embeddings-examples/520274/)

**Content graphs:** [Wikipedia MoS: Linking](https://en.wikipedia.org/wiki/Wikipedia:Manual_of_Style/Linking) · [Investopedia SEO teardown](https://www.spicymargarita.co/archive/investopedia-seo-case-study)

**GEO:** [Lumar: content chunking and AI extractability](https://www.lumar.io/blog/best-practice/content-chunking-ai-extractability-geo-aeo-explainer/) · [Neal Schaffer: internal linking for AI Overviews](https://nealschaffer.com/internal-linking/)

**Automation:** [Niko Alho: automating internal linking with embeddings](https://nikoalho.fi/writing/automating-internal-linking/) · [Screaming Frog: Link Score](https://www.screamingfrog.co.uk/seo-spider/tutorials/link-score/) · [Linkbot: a critical review of Link Whisper](https://library.linkbot.com/link-whisper-review/)

**Internal:** `EVIDENCE.md#e06-internal-linking` · `EVIDENCE.md#e04-search-console` · `[internal observation, unpublished]` · `[internal observation, unpublished]`
