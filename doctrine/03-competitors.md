# 03 — Competitive Intelligence

> Subordinate to `00-principles.md`. Any conflict resolves in favour of the principles.
> Changes only through a PR following the `RULE-CHANGE.md` template.

**Version:** 0.1.0 · **Date:** 2026-08-07 · **Review cycle:** every 90 days

|             |                                                                                                                                  |
| ----------- | -------------------------------------------------------------------------------------------------------------------------------- |
| **Purpose** | Find competitors from a cold start, quantify gaps, watch for change, and hand a task queue to the content plan                   |
| **Inputs**  | Site URL; query set (`.kiln/semantics/`); `project.yml` (geo, language, cluster business value); SERP provider keys              |
| **Outputs** | `.kiln/competitors/registry.json`, `.kiln/competitors/snapshots/`, `.kiln/competitors/serp/`, `.kiln/gaps.json`, the alert queue |
| **Owner**   | Code (collection, diffs, aggregation) + agent (classification, interpretation) + human (registry sign-off)                       |
| **Cadence** | GitHub Actions on cron. Not Claude Code session mechanisms, which do not survive the session closing                             |
| **Budget**  | ~$1.20/month per project without AI Overviews; ~$4.20/month with AIO on the money set (worked through in §12)                    |

---

## 1. The model: what a competitor is

### 1.1. A competitor is a domain, not a company

The unit of record is the domain standing between us and the click. Reddit, Wikipedia, YouTube,
marketplaces and aggregators routinely occupy the top 10 on commercial queries without being
business rivals at all. They must be detected, but handled under a different strategy: presence
**on** them rather than a fight **against** them.

So the data model carries no "is a competitor" flag. It carries a **competitor class**. A flat
list is useless because it merges objects that demand mutually exclusive responses.

### 1.2. The five classes

| Class        | Definition                                                               | Strategy                                                                  | Typical failure under a flat list                                |
| ------------ | ------------------------------------------------------------------------ | ------------------------------------------------------------------------- | ---------------------------------------------------------------- |
| `direct`     | A business rival that also ranks                                         | Displace: cover the intents more deeply and with genuine information gain | none                                                             |
| `serp_only`  | Ranks, but does not compete for revenue (trade media, blogs, references) | A source of topics and structures; a possible mention donor               | A task appears to "outrank a magazine", which earns nothing      |
| `platform`   | Reddit, Quora, YouTube, Wikipedia, marketplaces                          | Presence inside the platform                                              | A task appears to displace Wikipedia, which cannot be done       |
| `aggregator` | Roundups of the "10 best X" kind                                         | Get into the roundup, which directly affects AI citation                  | We write our own competing listicle, which the principles forbid |
| `ai_only`    | A brand LLMs recommend while its organic presence is absent or weak      | A separate loop: work out where the model is pulling it from              | Never detected at all                                            |

**`ai_only` is the most underrated class.** It is invisible to every organic tool, because such
a domain may hold no organic positions whatsoever. It surfaces only through the third detection
layer (§2). The practical value: if an LLM recommends a brand on our intent and that brand is
nowhere in the SERP, the model is drawing on sources we do not track, mentions in reviews,
roundups, discussions. That points at a channel, not at a page.

A separate consequence of `aggregator`: getting into someone else's roundup and writing our own
roundup are not symmetric acts. The first is permitted and useful. The second is forbidden by the
principles, since self-promoting listicles sink the whole domain rather than a single page.

### 1.3. Three independent detection layers

| Layer               | Definition                                     | How it is measured                                      | What it sees that the others miss                                    |
| ------------------- | ---------------------------------------------- | ------------------------------------------------------- | -------------------------------------------------------------------- |
| **SERP**            | Domain in the top 10 on our target queries     | Domain frequency across SERP snapshots of the query set | The state of play right now                                          |
| **Keyword overlap** | Domain whose ranking query set intersects ours | Share of shared keys against our set and against theirs | Competitors beyond our current query set, that is, where we could go |
| **AI citation**     | Brand or domain LLMs cite on our intents       | Share of prompts where it is mentioned or cited         | The `ai_only` class, organically invisible                           |

The layers overlap only partly, and all three are mandatory. Leaning on the SERP layer alone
gives a here-and-now snapshot with no sense of direction. Leaning on keyword overlap without SERP
gives a tool's list detached from what actually ranks in our locale. Leaving out the AI layer
loses an entire competitor class and the whole GEO loop with it.

Organic position remains the strongest single predictor of AI citation, yet the share of AI
Overview citations drawn from the top 10 fell from 76% to 38% over a year. The organic layer has
stopped being an adequate proxy for the AI layer. → `EVIDENCE.md#e01-geo-answer-engines`, `EVIDENCE.md#e02-practitioner-pulse`

---

## 2. Procedure C1: discovery from a cold start

Starting state: we have a site URL, no query set, no competitor list, and no Ahrefs API.

```
D0  Understand site  crawl our own site → topics, intents, geo, language, existing sections
D1  Seed             5–15 seed phrases (topic × intent × geo)      → OWNER CONFIRMS
D2  Expansion        autocomplete + PAA + related → 150–600 queries
D3  SERP sweep       top 10 + SERP features + AIO flag per query
D4  Aggregate        domain frequency + weighted share of voice
D5  Classify         heuristics (known platforms) + LLM on snippet and homepage → class
D6  Shortlist        direct top-N by SoV; separate lists for the other classes
D7  AI sweep         20–30 intent prompts × 3–4 engines → brands + cited URLs
D8  Merge & confirm  reconcile the lists → PUT IN FRONT OF THE OWNER FOR SIGN-OFF
D9  Baseline         capture sitemap and profile for every approved competitor
```

### 2.1. What each step does

**D0.** Crawling our own site produces the starting map: which sections exist, which intents are
covered, in what language, for what geo. Without it, the seed is guesswork.

**D1 is a mandatory human checkpoint.** Seed phrases define the entire downstream perimeter; an
error here is not repaired by anything further along the chain. The owner either confirms the
agent's proposed seed or corrects it. This happens inside the onboarding grill
(`01-onboarding-grill.md`), not as a separate meeting.

**D2.** Expansion runs through autocomplete, the "People also ask" block, and related searches.
The target volume is 150–600 queries: fewer yields no statistical signal on domains, more does not
pay for itself at the discovery stage.

**D3.** One SERP call per query, depth of top 10. The top 100 is not needed here: it costs 5–10
times more and does not change who the leaders are. SERP features and the presence of an AI
Overview are recorded as well, because they feed the prioritisation step; AIO shifts the expected
CTR of a cluster.

**D4.** Raw domain frequency is the worst available metric, because position 1 is not comparable
to position 10. We compute a weighted share of voice:

```
SoV(domain) = Σ_k [ CTR(pos(domain,k)) × weight(k) ] / Σ_k weight(k)
```

where `weight(k)` is search volume when we have it. Without the Ahrefs API we have no volumes,
so two degradations are permitted: `weight(k) = 1` for every query, or weights taken from cluster
business value in `project.yml`. The second is preferable, being closer to money.

The CTR curve comes from `08-measurement.md` and must be **two curves**: one for a clean SERP and
one for a SERP carrying an AI Overview. Mixing them is not allowed; measurements put the gap as
high as a 60% loss of clicks.

**D5.** Classification runs heuristics first against a list of known platforms (Reddit, Wikipedia,
YouTube, the region's large marketplaces), then an LLM classifier over the snippet and homepage
for everything else. The LLM proposes here; it does not decide.

**D6.** The shortlist is built **within a class**, never across classes. A mixed SoV ranking will
be led by Wikipedia, and that is useless.

**D7.** The AI sweep: 20–30 high-intent questions the audience genuinely asks, a mix of branded and
category prompts, run through 3–4 engines. Every answer is logged with the brands mentioned, the
URLs cited, and whether we appear. The measurement must be repeated: generative results are
unstable between runs, and citation drift reaches 40–60% per month. → `EVIDENCE.md#e01-geo-answer-engines`, `EVIDENCE.md#e05-semantics-and-clustering`

**D8 is the second mandatory human checkpoint.** Telling `direct` from `serp_only` is a business
judgement, not a technical one. An error here poisons the entire content plan: the system spends
months writing against a domain that is no rival, or ignoring the real one. Automation proposes,
the owner signs off.

**D9.** Every approved competitor gets a baseline capture: sitemap, section map, profile. That is
where the time series begins, and the time series is the module's real value.

### 2.2. Locale

> **CMP-27 (BLOCK).** Competitor discovery, classification and share of voice run per locale, using
> that locale's SERP settings. Share of voice is computed inside a locale and is **never summed or
> averaged across locales**.

**Discovery runs per locale, using that locale's SERP settings.** A competitor set collected under
the wrong region describes a different market, and every number derived from it, share of voice,
winnability, gap priority, describes that other market too.

For multi-locale projects the competitor tables are keyed by locale (`gl` and `hl` on every SERP
snapshot, §13). Share of voice is computed inside a locale and **never summed across locales**: a
domain dominant in one region and absent from another has no meaningful combined figure, and
averaging one into the other hides both facts.

Practically this means the D2–D6 sequence is executed once per locale, and the registry may well
carry the same domain under different classes in different locales. That is correct, not a
duplicate to be merged away. Cost scales linearly with locale count, which is the multiplier to
apply when reading §12.

### 2.3. Cost of the cold start

| Step                     | Volume                             | DataForSEO Standard       | Serper          |
| ------------------------ | ---------------------------------- | ------------------------- | --------------- |
| D3 full sweep of the set | 500 queries                        | **$0.30**                 | ~$0.50          |
| D3 with AI Overviews     | 500 queries                        | $1.30                     | partial support |
| D7 AI sweep              | 30 prompts × 4 engines × 3 repeats | cheap-model tokens, ~$0.5 | none            |
| D9 baseline              | 5 competitors                      | ~0 (our own GETs)         | ~0              |

Full competitor discovery on a project costs **less than a dollar**. That is two orders of
magnitude below any subscription and settles the question of whether the Ahrefs API is needed for
this job. → `EVIDENCE.md#e12-data-apis-and-pricing` (DataForSEO $0.60/1k Standard, $2.60/1k with AIO at n=10)

---

## 3. Procedure C2: profiling a competitor

The job is to turn a domain into a structure we can compare ourselves against.

1. **Section map** from the sitemap: which sections exist, how many URLs in each, how they are
   distributed over publication time.
2. **Page skeletons** for the top N by our importance estimate (§4.2); field list in §4.2.
3. **Entity coverage**: which subtopics and attributes appear on their pages and are missing from ours.
4. **Formats**: where the tables, calculators, video, original media and author pages are.
5. **Technical layer**: schema.org types, presence of `author` and `dateModified`, locale parity.

The fifth item often yields more than the first four combined. Checks on live projects show that
dates, authorship and locale parity break at scale on competitors' sites and on our own, and that
this is fixable in code without writing a single new article.

---

## 4. Procedure C3: change monitoring

### 4.1. The foundation is a daily sitemap diff

When a competitor publishes, the URL shows up in their `sitemap.xml` within hours. A daily diff
catches it the same day and costs essentially nothing: one GET on the sitemap index plus N GETs on
the children.

Captured:

- the URL set → diff against the previous snapshot → `added` / `removed`;
- `<lastmod>` → a trigger to re-crawl changed pages;
- the nested sitemap structure → the section map.

A caveat from practice: `<lastmod>` cannot be trusted. We have a live case on record where
`dateModified` was stamped with the request time, and `lastmod` on 54 of 58 items read as today.
Change detection therefore rests on `text_hash`, with `lastmod` demoted to a crawl-priority hint.
→ `[internal observation, unpublished]`

### 4.2. What to store: the skeleton, not the HTML

| Field                              | Why                                                                               |
| ---------------------------------- | --------------------------------------------------------------------------------- |
| `title`, `meta_description`        | The most frequent signal of repackaging toward a different intent                 |
| `h1`, the `h2/h3` stack            | Structure is the map of covered subtopics; a structural diff is a strategy change |
| `word_count`                       | Volume; **computed with unicode-aware tokenisation** (CMP-12)                     |
| `text_hash`                        | Proof the text changed, independent of any claimed dates                          |
| `canonical`, `robots`, `status`    | A move to `noindex` means they have written the page off themselves               |
| `schema.org` types                 | A new type appearing means they are going after a SERP feature                    |
| Internal links: count and anchors  | Their internal linking reveals their priorities                                   |
| `published_at`, `updated_at`       | Freshness gap                                                                     |
| Presence of tables, lists, figures | Extractability for LLMs                                                           |
| Share of text in the first third   | 44.2% of LLM citations come from there (`00-principles.md`, P12)                  |

### 4.3. Frequencies

| Object                         | Frequency                | Rationale                                    |
| ------------------------------ | ------------------------ | -------------------------------------------- |
| Competitor `sitemap.xml`       | 1×/day                   | New URLs appear within hours                 |
| New URLs (full parse)          | Within 24 h of detection | Cheap, small volume                          |
| Competitor's top 50 pages      | 1×/week or on `lastmod`  | Catches rewrites                             |
| All other pages                | 1×/month                 | Budget                                       |
| SERP on money keys (50–100)    | **1×/day**               | See below                                    |
| SERP across the full query set | 1×/month                 | Baseline SoV reading                         |
| AI prompts (20–30)             | 1×/week                  | Citation patterns shift faster than organics |

Daily cadence on money keys is not a luxury. AI Overviews and SERP features change within a week,
and without daily granularity there is no way to tell "an AIO squeezed us out" from "we lost
ranking". Those are two different diagnoses with two different treatments, and weekly reporting
fuses them into one.

Volatility estimates (roughly 12 changes per key per month, AIO on 15–25% of queries) come from
vendor material and count as a rough guide, not a measurement.

### 4.4. Traffic volume

For one mid-sized competitor (2,000 URLs): sitemap ~1–5 MB/day, new URLs a few MB per week, the
weekly re-crawl of the top 50 around 10 MB. Single-digit to low double-digit megabytes per week.

The bottleneck is not volume but **request rate** (§7).

### 4.5. Retention

| What                  | Term       | Why                                                |
| --------------------- | ---------- | -------------------------------------------------- |
| Page skeletons        | Indefinite | The time series is the module's value              |
| SERP snapshots        | Indefinite | Without them winnability cannot be computed (§5.2) |
| AI answer snapshots   | Indefinite | Baseline for citation drift                        |
| Raw HTML              | 7 days     | A debugging window and nothing more                |
| Images, personal data | Not stored | CMP-10                                             |

---

## 5. Procedure C4: gaps and priority

### 5.1. The seven gap types

Reducing "gap" to "keys they rank for and we do not" covers one type out of seven, and therefore
misses most of the real opportunities.

| #   | Type               | How it is detected                                                                                | Output artefact                                                  |
| --- | ------------------ | ------------------------------------------------------------------------------------------------- | ---------------------------------------------------------------- |
| 1   | **keyword**        | They are in the top 10, we are outside the top 100 on a query from our set                        | Candidate for a new page or for extending an existing one        |
| 2   | **topic / entity** | The topic is nominally covered, but entities present across the whole top 10 are absent from ours | List of missing entities for page extension                      |
| 3   | **depth**          | Both have a page; theirs has more subheadings, a table, a calculation, original data              | Deepening plan with a concrete list                              |
| 4   | **format**         | The SERP demands a format we lack (video, table, images, calculator)                              | A format task, not a text task                                   |
| 5   | **intent**         | Informational intent covered, commercial not, or the reverse                                      | The classic cause of "traffic but no conversions"                |
| 6   | **freshness**      | Their page has been updated, ours has gone stale                                                  | A task in the refresh queue                                      |
| 7   | **citation (GEO)** | On a given prompt their URL is cited and ours is not                                              | High priority: examine what their passage has that ours does not |

An extension to type 6 that almost nobody implements: **a page can be new and stale at the same
time** if it cites outdated sources. What matters is not the publication date but the median age
of the sources inside the material. → `EVIDENCE.md#e08-trend-detection`

### 5.2. The priority formula

```
GapScore = 100 × ( BV^0.4 × TP^0.3 × WP^0.3 ) / Effort_norm × (1 + 0.25 · AICite)

BV      cluster business value (0..1), set by the owner during onboarding
TP      traffic potential (0..1), from volume, or query frequency within the set when volumes are absent
WP      winnability (0..1), computed ONLY from our own SERP snapshots
Effort  production estimate (1..5), normalised
AICite  0/1, whether we can deliver genuine information gain
```

**`WP` is the one component no off-the-shelf tool carries.** It is computed as the rate of turnover
in the top 10 composition for that query across the observation window: a query whose top has not
moved in a year calls for a different decision than a query whose top reshuffles monthly. It can
only be derived from our own SERP snapshot archive, which is why retention there is indefinite (§4.5).

A priority matrix for fast triage:

| Business value | Difficulty | Action                                   |
| -------------- | ---------- | ---------------------------------------- |
| High           | Low        | First                                    |
| High           | High       | Second, via an information-gain strategy |
| Low            | Low        | Batch, on leftover capacity              |
| Low            | High       | Drop                                     |

The `AICite` multiplier exists because citation compounds across every platform at once, not only
in organic search. A gap where we can supply real information gain, our own data, our own
calculation, an expert attribution, is worth taking even at high difficulty.

### 5.3. The gate before a task is created

A gap does not become a task automatically. Two blocking rules:

- **CMP-19**: no task is created without a populated `unique_value_source` (principle P13). A gap
  says the competitor has something; it does not say we have anything to add.
- **CMP-20**: a `keyword` gap does not spawn a new page when we already hold a page on the same
  intent (principle P6). The task is to extend the existing page, not to create a second one.
  Otherwise the competitive intelligence module manufactures cannibalization by itself.

---

## 6. Alerts

| Trigger                                                               | What it means                              | Action                                                                |
| --------------------------------------------------------------------- | ------------------------------------------ | --------------------------------------------------------------------- |
| New competitor URL in a cluster where we hold a page                  | We may be overtaken                        | Check our page for depth and freshness                                |
| `title` or `h1` change on a competitor page ranking above ours        | Intent shift or repackaging                | Reconsider our intent on that query                                   |
| A domain entering or leaving the top 10 on a money key                | The competitive field moved                | Recompute SoV, possibly re-evaluate the registry                      |
| An AI Overview appearing where there was none                         | Expected cluster CTR drops                 | Recompute cluster priorities                                          |
| A competitor cited in an AI answer on a prompt where we are absent    | Citation gap                               | High priority: dissect their passage                                  |
| **Our page dropped more than 3 positions with `text_hash` unchanged** | **The cause is external, not the content** | Do not touch the text; look to the SERP, the competitors or an update |

The last trigger matters more than the rest combined. Without it the reflexive response to a drop
is to rewrite the page, which, when the cause is external, makes things worse: we discard the
accumulated signals and buy ourselves a fresh re-evaluation cycle.

---

## 7. Rule registry

| ID         | Rule                                                                                                                               | Severity | Basis                                                              |
| ---------- | ---------------------------------------------------------------------------------------------------------------------------------- | -------- | ------------------------------------------------------------------ |
| **CMP-01** | Every registry entry carries one of the five permitted classes. Entries without a class do not enter prioritisation                | BLOCK    | §1.2                                                               |
| **CMP-02** | `direct` / `serp_only` classification is signed off by a human (step D8)                                                           | BLOCK    | P11, §2.1                                                          |
| **CMP-03** | Seed phrases are confirmed by the owner before expansion (step D1)                                                                 | BLOCK    | P11                                                                |
| **CMP-04** | Every `ai_snapshots` record carries a `method` field valued `api` or `ui`. Mixing them inside one metric is forbidden              | BLOCK    | API and live-interface measurements ground differently             |
| **CMP-05** | Never create an account and never log in to a competitor's property                                                                | BLOCK    | §8                                                                 |
| **CMP-06** | Interval between requests to a single host ≥ 2 s; `Crawl-delay` from robots.txt is honoured when it is larger                      | BLOCK    | §8                                                                 |
| **CMP-07** | User-Agent is honest and carries a contact URL. Masquerading as a browser or as Googlebot is forbidden                             | BLOCK    | §8                                                                 |
| **CMP-08** | The target host's `robots.txt` is read and obeyed                                                                                  | BLOCK    | §8                                                                 |
| **CMP-09** | On 429 and 503, exponential backoff, not retry                                                                                     | BLOCK    | §8                                                                 |
| **CMP-10** | Personal data (authors as individuals, commenters, contact details) is neither collected nor stored                                | BLOCK    | §8                                                                 |
| **CMP-11** | Competitor text is never carried into our draft, whole or in fragments. Intelligence means analysing structure and topics          | BLOCK    | P1, copyright                                                      |
| **CMP-12** | `word_count` and every length metric are computed with unicode-aware tokenisation                                                  | BLOCK    | P5; `wc -w` inverted the conclusion on a live measurement          |
| **CMP-13** | Competitors' raw HTML is deleted after 7 days                                                                                      | WARN     | §4.5                                                               |
| **CMP-14** | SERP and AI answer snapshots are never deleted                                                                                     | WARN     | `WP` cannot be computed without them                               |
| **CMP-15** | SoV is weighted by CTR position. A flat count of top-10 appearances is forbidden                                                   | WARN     | §2.1                                                               |
| **CMP-16** | The tracked competitor set is maintained **per cluster**, not one set per domain                                                   | WARN     | §9                                                                 |
| **CMP-17** | AI Overview tracking is enabled only on the priority query set                                                                     | WARN     | AIO raises SERP cost 4–15×                                         |
| **CMP-18** | Money keys are sampled daily; weekly granularity on them is forbidden                                                              | WARN     | §4.3                                                               |
| **CMP-19** | A gap does not become a task without a populated `unique_value_source`                                                             | BLOCK    | P13                                                                |
| **CMP-20** | A `keyword` gap does not spawn a new page when we hold a page on the same intent                                                   | BLOCK    | P6                                                                 |
| **CMP-21** | All thresholds live in `.kiln/thresholds.yml`, not in code and not as constants in this document                                   | WARN     | P10                                                                |
| **CMP-22** | Every firing and every human override of any `CMP-*` rule is logged to `rules-stats.json`                                          | INFO     | P8                                                                 |
| **CMP-23** | The `platform` and `aggregator` classes never spawn "outrank them" tasks                                                           | WARN     | §1.2                                                               |
| **CMP-24** | A paid endpoint's price is verified against official documentation before the first production run                                 | WARN     | §12, sources disagree                                              |
| **CMP-25** | `ai_only` competitors appear in every report as their own section                                                                  | WARN     | Otherwise the class disappears                                     |
| **CMP-26** | Periodic runs are launched by an out-of-session scheduler (GitHub Actions). Session mechanisms are not used as the primary channel | WARN     | Inbound webhooks into a Claude Code session are effectively closed |

---

## 8. Legal boundaries (enforced in code, not in agent instructions)

The dividing line runs through **login**, not through scraping.

- **hiQ v. LinkedIn** (Ninth Circuit): scraping publicly accessible profiles does not violate the
  CFAA. But in November 2022 the court found a breach of the user agreement, because hiQ **created
  accounts** and thereby accepted the terms.
- **Meta v. Bright Data** (January 2024, N.D. Cal.): summary judgment for Bright Data. Meta's terms
  did not prohibit scraping public data **while logged out**.

Rules CMP-05 through CMP-11 follow from this. They are implemented at the HTTP client layer, not as
instructions to an agent: an agent can get it wrong, a client cannot.

Scope limit: the precedents cited are United States jurisdiction. Projects in the EU and Ukraine are
additionally governed by GDPR and the sui generis database right; that pass has not been done and
remains open (§16).

---

## 9. Thresholds

Every value below is an **expert proposal, not an industry standard**. No canonical public
thresholds exist: the closest analogue, Moz's `Rivalry` metric, is proprietary (all that is known
is that it analyses 500 fresh SERPs and returns up to 25 competitors; the formula is undisclosed).
These thresholds must be calibrated on the first two or three projects and live in
`.kiln/thresholds.yml` (CMP-21).

| Threshold                        | Value                                                                     | Status                                                                         |
| -------------------------------- | ------------------------------------------------------------------------- | ------------------------------------------------------------------------------ |
| Domain becomes a candidate       | Top 10 on ≥ 5% of the query set **or** ≥ 20 queries (whichever is larger) | [expert judgement, needs calibration]                                          |
| Domain enters permanent tracking | SoV ≥ 2%                                                                  | [expert judgement, needs calibration]                                          |
| Size of the tracked set          | 3–5 domains **per cluster**                                               | [expert judgement, needs calibration]                                          |
| Expansion volume at D2           | 150–600 queries                                                           | [expert judgement, needs calibration]                                          |
| SERP depth at D3                 | Top 10                                                                    | Justified on cost: the top 100 is 5–10× dearer and does not change the leaders |
| AI prompt set size               | 20–30 at onboarding, 40–100 in steady state                               | [source: GEO measurement practice]                                             |
| AI measurement repeats           | ≥ 3                                                                       | [source: citation drift 40–60%/month]                                          |
| Position-drop alert threshold    | > 3 positions with `text_hash` unchanged                                  | [expert judgement, needs calibration]                                          |

Why the set is maintained per cluster rather than per domain: on a site spanning several verticals
(loans, deposits, insurance) a single competitor list is meaningless, since each vertical has its
own top. The price of this decision is linear growth in the number of tracked domains, offset by
deep monitoring being limited to each one's top 50 pages.

---

## 10. Division of labour

| **Code** does                                   | **Agent** does                            | **Human** does                                   |
| ----------------------------------------------- | ----------------------------------------- | ------------------------------------------------ |
| SERP sweep, domain aggregation, SoV computation | Proposes seed phrases from the site crawl | Confirms the seed (D1)                           |
| Sitemap diff, skeleton extraction, hashing      | Classifies domains into classes           | **Signs off the classification (D8)**            |
| Computes `WP` from the SERP snapshot archive    | Interprets a gap: what exactly they have  | Assigns cluster business value                   |
| Computes `GapScore`                             | Drafts a candidate `unique_value_source`  | Confirms the `unique_value_source` is real       |
| Enforces rate limits, robots, backoff           | Summarises changes over a period          | Decides on alerts requiring action on the corpus |
| Logs rule firings                               |                                           |                                                  |

The allocation rule: **code computes the numbers, the agent proposes the meanings, the human signs
off anything irreversible.** The reason is that an LLM does not reproduce the same computation
twice, so a model-computed metric is unfit for a time series, and this entire module is built on
time series.

---

## 11. Forbidden

| Prohibition                                                              | Reason                                                       |
| ------------------------------------------------------------------------ | ------------------------------------------------------------ |
| Logging in to a competitor's property                                    | §8, the single dividing line in the precedents               |
| Masquerading the User-Agent as a browser or Googlebot                    | §8, bad faith                                                |
| Carrying competitor text into our draft                                  | P1; intelligence is not reuse                                |
| Creating "outrank them" tasks for `platform` and `aggregator` classes    | Impossible by construction, or leads to a forbidden listicle |
| Writing our own "10 best" listicle with ourselves at number one          | Sinks the whole domain, not one page (`00-principles.md`)    |
| Flat counting of top-10 appearances instead of weighted SoV              | Position 1 is not comparable to position 10                  |
| Summing or averaging share of voice across locales                       | CMP-27; a combined figure describes no market                |
| Mixing `api` and `ui` AI measurements inside one metric                  | Different grounding                                          |
| Creating a page from a `keyword` gap when we hold one on the same intent | P6, manufacturing cannibalization by our own hand            |
| Hardcoding thresholds instead of using `thresholds.yml`                  | P10                                                          |
| Measuring text length in a non-unicode-aware way                         | P5                                                           |
| Building permanent monitoring on Claude Code session mechanisms          | They do not survive the session closing                      |
| Buying an AI visibility subscription as the primary source               | §12: our own module is 10–100× cheaper and yields raw data   |

---

## 12. Budget and schedule

Computed for one project: a 500-key query set, 50 money keys, 5 competitors, default provider
DataForSEO Standard ($0.60 per 1,000 SERPs). **Multiply by locale count** (§2.2).

| Task                                    | Frequency | Requests/month | $/month             |
| --------------------------------------- | --------- | -------------- | ------------------- |
| Sitemap diff × 5 competitors            | Daily     | ~150 GET       | ~0                  |
| Parsing new URLs                        | On event  | ~300–600 GET   | ~0                  |
| Re-crawl of top 50 × 5                  | Weekly    | ~1,000 GET     | ~0                  |
| SERP: money keys (50)                   | Daily     | 1,500          | $0.90               |
| SERP: money keys **with AIO**           | Daily     | 1,500          | $3.90               |
| SERP: full query set (500)              | Monthly   | 500            | $0.30               |
| AI prompts (30 × 4 engines × 3 repeats) | Weekly    | 1,440 calls    | tokens, ~$2         |
| **Total without AIO**                   |           |                | **~$1.20 + tokens** |
| **Total with AIO on the money set**     |           |                | **~$4.20 + tokens** |

Three architectural consequences:

1. **The organic layer can be dense.** It costs a dollar. Economising on it is pointless; the saving
   is smaller than a single expensive-model call.
2. **AI Overviews are a separate cost line**, raising SERP cost 4–15×. Hence CMP-17: AIO tracking on
   the priority set only.
3. **We build AI visibility ourselves.** Subscriptions run $25–489/month for what our own keys
   deliver at $2–5/month, and a subscription does not hand over the raw data the fast learning loop
   (P9) depends on.

Our own HTTP requests cost only time, but they are precisely what demands rate-limit discipline.

---

## 13. Data model

| Entity            | Key fields                                                                                                                                                                               |
| ----------------- | ---------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| `competitors`     | `domain`, `class`, `locale`, `sov`, `clusters[]`, `first_seen`, `status`, `confirmed_by`, `confirmed_at`                                                                                 |
| `competitor_urls` | `competitor_id`, `url`, `section`, `first_seen`, `last_seen`, `importance_score`                                                                                                         |
| `url_snapshots`   | `url_id`, `taken_at`, `title`, `meta_description`, `h_stack`, `word_count`, `schema_types`, `canonical`, `robots`, `status`, `text_hash`, `published_at`, `updated_at`, `internal_links` |
| `serp_snapshots`  | `query`, `taken_at`, `engine`, `gl`, `hl`, `positions[]`, `features[]`, `aio_present`, `aio_sources[]`                                                                                   |
| `ai_snapshots`    | `prompt`, `platform`, `taken_at`, `run_index`, `brands_mentioned[]`, `urls_cited[]`, `our_mention`, `our_citation`, **`method`**                                                         |
| `gaps`            | `type`, `target`, `competitor_id`, `evidence_url`, `gap_score`, `unique_value_source`, `status`                                                                                          |

`confirmed_by` and `confirmed_at` on `competitors` implement CMP-02: an entry lacking them does not
enter prioritisation. `run_index` on `ai_snapshots` enforces the three-repeat requirement. `locale`
on `competitors`, together with `gl`/`hl` on `serp_snapshots`, keys the registry per locale (§2.2);
the same domain may legitimately hold different classes in different locales.

---

## 14. Layer 2 script specifications

The scripts are self-contained: they know nothing about any particular site, never touch the
project's database, and need no adapter. Files in, files out.

### `discover.py`

```
Purpose  : steps D2–D6 of the cold start
Input    : --queries queries.txt        (one query per line)
           --provider dataforseo|serper
           --gl UA --hl uk
           --own-domain example.com
           --weights weights.json       (optional: cluster/query weight)
           --ctr-curve ctr.json         (two curves: clean and with_aio)
Output   : discovery.json
           {
             "generated_at": "...", "queries_total": N, "cost_usd": X,
             "locale": { "gl": "UA", "hl": "uk" },
             "domains": [
               { "domain": "...", "hits": N, "avg_position": F,
                 "sov": F, "queries": ["..."], "class_hint": "platform|null" }
             ],
             "serp_snapshots": [ ... ]        // raw snapshots for the archive
           }
Rules    : CMP-06..09 in the HTTP layer; CMP-15 in the SoV computation
Does not : classify (that is the agent), decide registry inclusion (that is the human)
```

### `sitemap_diff.py`

```
Purpose  : daily diff of competitors' sitemaps
Input    : --state .kiln/competitors/sitemaps/     (previous snapshots)
           --targets competitors.json              (domains + sitemap URLs)
           --rate-limit 2.0
Output   : sitemap_diff.json
           {
             "generated_at": "...",
             "per_domain": [
               { "domain": "...", "added": ["..."], "removed": ["..."],
                 "lastmod_changed": ["..."], "total_urls": N,
                 "sections": { "/blog/": N, "/tools/": N } }
             ]
           }
           + refreshed snapshots written into --state
Rules    : CMP-06..09; `lastmod` is treated as a hint, not a fact (§4.1)
Cost     : ~0, bandwidth only
```

### `gap.py`

```
Purpose  : gap computation and GapScore
Input    : --ours corpus.json               (our corpus: URL, intent, cluster, entities)
           --theirs snapshots.json          (competitors' page skeletons)
           --serp serp_snapshots.json       (archive, for computing WP)
           --business-value bv.json         (cluster value, from the owner)
           --thresholds .kiln/thresholds.yml
Output   : gaps.json
           [ { "type": "keyword|topic|depth|format|intent|freshness|citation",
               "target": "...", "competitor": "...", "evidence_url": "...",
               "bv": F, "tp": F, "wp": F, "effort": N, "ai_cite": 0|1,
               "gap_score": F,
               "blocked_by": ["CMP-19"|"CMP-20"|null],
               "unique_value_source": null } ]
Rules    : CMP-12 (unicode length), CMP-19, CMP-20 set `blocked_by`
           but do NOT drop the record: the reason for blocking must stay visible to the human
Does not : populate `unique_value_source`; the agent drafts it, the human confirms it
```

Common to all three: output is deterministic, and re-running on the same inputs yields the same
result. That is the precondition for the data being fit for a time series.

---

## 15. What to take off the shelf

Part of this work is already done and sits under MIT. Verify the licence against the `LICENSE` file
in the repository before use; the notes below come from a survey and need checking.

| Project                                                                                      | Licence     | What it covers                                                               | How to use it                                                                           |
| -------------------------------------------------------------------------------------------- | ----------- | ---------------------------------------------------------------------------- | --------------------------------------------------------------------------------------- |
| [`AgriciDaniel/claude-seo`](https://github.com/AgriciDaniel/claude-seo), 13.6k ★             | MIT         | 25 skills + 18 agents, including `seo-cluster`, `seo-backlinks`, `seo-drift` | Read as a coverage checklist; borrow the skill decomposition, not the logic             |
| [`dredozubov/mcp-serp-clustering`](https://github.com/dredozubov/mcp-serp-clustering)        | verify      | MCP server for SERP-overlap clustering                                       | Directly relevant to D4–D6; check whether it beats building our own                     |
| [`HasData/python-for-seo`](https://github.com/HasData/python-for-seo)                        | verify      | Cannibalization and SERP overlap via Jaccard index                           | Borrow the overlap computation                                                          |
| [`FassihFayyaz/SEO-Clustering-Tool`](https://github.com/FassihFayyaz/SEO-Clustering-Tool)    | verify      | SERP clustering with a **built-in SERP cache**                               | The cache architecture is exactly where we arrive independently                         |
| [`OpenClaudia/openclaudia-skills`](https://github.com/OpenClaudia/openclaudia-skills), 621 ★ | MIT         | Among others, `content-gap-analysis`, `geo-difficulty`                       | Cross-check our gap module against their approach                                       |
| [`dataforseo/mcp-server-typescript`](https://github.com/dataforseo/mcp-server-typescript)    | official    | SERP, keywords, backlinks, domains                                           | ⚠️ Risk: unbounded agent loops produce runaway bills. A budget gate on top is mandatory |
| Apify Sitemap Change Detector                                                                | pay-per-use | Sitemap and robots.txt diffs as JSON                                         | An alternative to our own `sitemap_diff.py` if we would rather not maintain it          |

What **not** to take: `seranking/seo-skills`, MIT-licensed code that is useless without a paid SE
Ranking subscription with API access, which contradicts the portability principle.
Conductor/ContentKing performs exactly the change logging our C3 does, at an estimated ~$6,000/year
according to survey material.

**A deliberate decision to skip the Ahrefs API.** It is not needed for this module: competitor
discovery is done with our own SERP sweep for a dollar, and the backlink layer is covered by
OpenPageRank ($0) plus targeted DataForSEO Backlinks calls ($0.05 per 1,000 against $5.00 at
Ahrefs). The existing UI subscription serves as a source of one-off CSV exports for cross-checking
and threshold calibration, not as a pipeline dependency.

---

## 16. Conflicts with the principles, and open branches

### Conflicts resolved in favour of the principles

| What the industry proposes                                | Why it is rejected                                                          |
| --------------------------------------------------------- | --------------------------------------------------------------------------- |
| "Find the competitors and write whatever they write"      | P13: a gap does not create information gain. Hence CMP-19                   |
| "Cover every competitor keyword with its own page"        | P6 and the doorway prohibition. Hence CMP-20                                |
| "Write our own listicle since the competitor's one ranks" | The self-promoting listicle ban in `00-principles.md`                       |
| "Monitor AIO across the whole query set"                  | §12: 4–15× cost increase with no improvement in decision quality. CMP-17    |
| "Buy an AI visibility subscription"                       | P9: a subscription withholds raw data, so the fast learning loop cannot run |

### Not closed

1. **The EU and Ukraine legal pass has not been done.** GDPR and the sui generis database right were
   not examined; §8 covers United States precedent only.
2. **The price of DataForSEO's `competitors_domain` endpoint disagrees between sources**: the
   official pricing page against a third-party survey ($0.1 per task + $0.001 per domain). Hence CMP-24.
3. **The thresholds in §9 are uncalibrated.** The first two or three projects must collect the
   distributions, after which the thresholds are revised through a PR.
4. **SERP volatility estimates are vendor-sourced** (~12 changes per key per month, AIO on 15–25% of
   queries): a guide, not a measurement.
5. **Reddit is programmatically inaccessible both as a source and as a `platform` class member.**
   Between the free tier (100 QPM) and the commercial API ($12,000/month) there is nothing, and
   during reconnaissance Reddit proved unreachable by every workaround attempted. The method of
   working with this class remains unresolved.

---

## 17. Sources

Every claim in this section rests on the reconnaissance reports, where the primary sources and
their dates are recorded:

- `EVIDENCE.md#e07-competitive-intelligence` — taxonomy, SoV, thresholds, frequencies, precedents, pricing
- `EVIDENCE.md#e12-data-apis-and-pricing` — SERP provider pricing, AIO surcharge, backlinks, AI visibility
- `EVIDENCE.md#e01-geo-answer-engines` — the fall in the top-10 share of AIO citations, citation drift
- `EVIDENCE.md#e02-practitioner-pulse` — position as a predictor of AI citation
- `EVIDENCE.md#e05-semantics-and-clustering` — instability of generative results between runs
- `EVIDENCE.md#e08-trend-detection` — age of cited sources as a freshness metric
- `EVIDENCE.md#e15-market-landscape` — off-the-shelf repositories and MCP servers
- `[internal observation, unpublished]` — the live case of untrustworthy `lastmod`
- `[internal observation, unpublished]` — unicode tokenisation in length counting
