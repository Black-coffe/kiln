# 09. The AI Answer Engine Loop

> Scope note. This section does not restate the extractability rules. Answer-first placement,
> passage self-sufficiency, anaphora and first-third coverage are defined once in
> `05-writing-core.md` as `WRT-30` through `WRT-35`. What follows supplies the GEO evidence for
> why those rules exist, the access layer they depend on, and the measurement loop that tells us
> whether any of it worked.

**Purpose.** Keep the site reachable by AI answer engines, and measure how often it is cited,
without buying a monitoring subscription.

**Inputs.** `.kiln/project.yml` (locales, brand, competitor set) · `.kiln/semantics/clusters.json`
(cluster mapping for the prompt set) · `.kiln/geo/prompts.yml` and `.kiln/geo/brands.yml` (both
frozen) · server access logs · robots.txt and live crawler probes.

**Outputs.** `.kiln/geo/runs/` (raw stored answers) · `.kiln/geo/scores/` (computed metrics) ·
`.kiln/geo/access/` (crawler access from logs) · `LI-5` exported to `08-measurement.md`.

**Who executes.** Access checks and scoring: code. Prompt set design and competitor
classification: agent, confirmed by a human. Digital PR targets derived from the prompt set:
human decision.

---

## 1. The framing: there is no separate discipline here

State this first, plainly, because the surrounding market depends on the opposite being believed.

Google's documentation is explicit. From the AI features guide, updated 2025-12-10:

> "There are no additional requirements to appear in AI Overviews or AI Mode, nor other special
> optimizations necessary."

And from the generative-AI optimization guide, updated 2026-07-10:

> "You don't need to create new machine readable files, AI text files, or markup to appear in
> these features. There's also no special schema.org structured data that you need to add."

AI features are built on the core ranking systems through retrieval, so classical SEO remains the
substrate. Since 2026-07-24 the spam policies cover attempts to manipulate generative responses
verbatim, which means the enforcement regime is the same one, not a parallel one. This is `P12`.

Two consequences follow, and they are the whole reason this section is short on tactics and long
on measurement:

1. **There is no GEO module to build.** There is an access layer that can silently fail, a set of
   writing rules that already live in `05-writing-core.md`, and a measurement loop. Anything else
   offered under the GEO label is either one of those three or folklore.
2. **Query fan-out breaks the assumption that ranking gates citation.** Google documents that the
   engine decomposes a query into related sub-queries and assembles a broader source set than the
   ordinary SERP. Measured consequence: the share of AI Overview citations coming from the top 10
   fell from 76 % in July 2025 to 38 % in March 2026, with the remainder split roughly evenly
   between positions 11 to 100 and beyond position 100. `[source: EVIDENCE.md#e01-geo-answer-engines, Ahrefs, 863 K keywords
/ ~4 M URLs]` A page can be cited for a query it does not rank for, and a page that ranks can
   go uncited.

### 1.1 Where GEO advice must never come from

**`GEO-26 · BLOCK · SEO and GEO guidance is taken only from dated primary sources, never from a
model's own knowledge.**

This is `P1` applied reflexively, and the reason is specific rather than theoretical. A
practitioner published a deliberately fabricated claim (that Google had approved an update
"between slices of yesterday's pizza"); within 24 hours AI Overviews were serving that claim to
users. Separately, 56 % of factually correct AI Overview answers in the same body of work were
found to be ungrounded in their cited sources. `[source: EVIDENCE.md#e02-practitioner-pulse]`

An agent that researches SEO practice by asking a model, or by reading whatever the model
surfaces, will launder blogspam into our doctrine. Every claim entering this section carries a
URL and a date, and every threshold carries its provenance marker.

---

## 2. The access layer

Onboarding checks access once (`ONB-10`, `ONB-11`, `ONB-12`, `ONB-13`). Access then regresses:
a framework migration turns a server-rendered route into a client-rendered one, a WAF rule
tightens, a CDN vendor changes a default. The gates below are the same checks run **continuously**,
and a regression halts publishing to the affected locale rather than merely logging a warning.

### 2.1 JavaScript is the hard boundary

**`GEO-01 · BLOCK · Main content must be present in raw HTML.**

No major AI crawler executes JavaScript: `OAI-SearchBot`, `ChatGPT-User`, `GPTBot`, `ClaudeBot`,
`PerplexityBot`. JS files are fetched but never run (11.50 % of ChatGPT requests, 23.84 % of
Claude requests are JS assets that are downloaded and not executed).
`[source: EVIDENCE.md#e01-geo-answer-engines, Vercel + MERJ, 500 M fetches, 2024-12-17]`

Googlebot is the exception: it renders JavaScript, and Google's AI features ride that
infrastructure. The failure mode this creates is the one worth memorising, because it is invisible
from inside Google's own tooling:

> A client-rendered site can be perfectly visible in Google AI Overviews and completely invisible
> in ChatGPT, Claude and Perplexity at the same time.

Check: fetch with a crawler user-agent and no JS execution, count Unicode-aware words, compare
against the rendered version. Threshold: raw HTML yielding under **30 %** of the rendered word
count fails. `[expert judgement, needs calibration]` Identical to `ONB-10`, re-run on schedule.

### 2.2 Per-bot granularity, which is the most common technical error

**`GEO-02 · BLOCK · Search bots must be reachable; training bots are the owner's choice.**

The distinction that decides visibility, from OpenAI's own bot documentation:

| Bot                 | Purpose                                      | Gates ChatGPT search visibility                                                   |
| ------------------- | -------------------------------------------- | --------------------------------------------------------------------------------- |
| `OAI-SearchBot/1.4` | surfacing sites in ChatGPT's search features | **Yes.** Blocking it means the site "will not be shown in ChatGPT search answers" |
| `GPTBot/1.4`        | training data collection                     | No                                                                                |
| `ChatGPT-User/1.0`  | user-initiated fetch                         | No; robots rules "may not apply"                                                  |
| `OAI-AdsBot/1.0`    | ad landing page safety checks                | No                                                                                |

Anthropic splits the same three ways (`ClaudeBot` for training, `Claude-User` for user-initiated,
`Claude-SearchBot` for search indexing) and states that all three honour robots.txt, including the
user-initiated one. `Google-Extended` governs only training use by other Google AI systems, not
appearance in Search AI features. `[source: EVIDENCE.md#e01-geo-answer-engines]`

The widely repeated advice "block GPTBot" disables training and does not affect visibility. An
accidental block of `OAI-SearchBot` removes the site from ChatGPT entirely. Those two lines look
almost identical in a robots.txt file and have opposite consequences.

**`GEO-06 · INFO · Blocking training bots is never reported as a defect.**

If the owner blocks `GPTBot`, `ClaudeBot`, `CCBot` or `Google-Extended`, that is a legitimate
commercial decision about training use. Kiln records it and moves on. A framework that nags about
this is optimising for the vendor rather than the owner.

### 2.3 The edge is where access dies silently

**`GEO-04 · WARN · The CDN and WAF layer is probed separately from robots.txt.**

An `Allow` in robots.txt and a 403 at the edge produce the same outcome as an explicit block, with
none of the visibility. This is now a live default rather than a misconfiguration: Cloudflare's
Content Signals Policy (launched 2025-09-24) separates `search`, `ai-input` and `ai-train` uses,
and **from 2026-09-15** new sites and new customers default to permitting classical search
crawling while blocking AI training and agent use on pages carrying ads, with "mixed" crawlers
that have not separated their functions blocked by default. Pay Per Crawl has been restructured
into Pay Per Use, billing on appearance in an answer rather than on the crawl.
`[source: EVIDENCE.md#e01-geo-answer-engines]`

Check: probe the live URL with each bot user-agent and compare status code **and response body
size** against a browser user-agent. A body-size divergence is a cloaking indicator and escalates
to `BLOCK` with `cloaking_suspected`, matching `ONB-11`.

**`GEO-03 · BLOCK · No `noindex`, `nosnippet`, `max-snippet:0`or`data-nosnippet`on target
pages.** Google documents these as the controls that withdraw a page from AI features. They are
the intended opt-out, so their presence on a page we are actively promoting is a configuration
error rather than a policy choice.`[source: EVIDENCE.md#e01-geo-answer-engines, official documentation]`

### 2.4 Crawl waste is a GEO metric

**`GEO-05 · WARN · AI crawler 404 share below 15 %.** `[source: EVIDENCE.md#e01-geo-answer-engines]`

Baseline from the same 500 M fetch study: 34.82 % of ChatGPT fetches and 34.16 % of Claude fetches
resolve to 404, against 8.22 % for Googlebot. `[source: EVIDENCE.md#e01-geo-answer-engines, Vercel + MERJ]` These crawlers
spend roughly a third of their budget on our site fetching nothing. A clean sitemap, absent broken
links and stable URLs therefore convert directly into a larger share of useful fetches, which is a
cheaper lever than anything on the content side.

---

## 3. What is evidenced, and how strongly

The distinction between a controlled study, a correlation and a vendor claim is load-bearing here.
The GEO niche in 2026 is saturated with blogspam that reprints precise-looking percentages with no
traceable origin, so every figure below carries its evidence class.

### 3.1 The only peer-reviewed work

`[PEER]` Aggarwal et al., "GEO: Generative Engine Optimization", arXiv:2311.09735, ACM SIGKDD 2024.
GEO-bench: 10,000 queries drawn from MS Marco, Natural Questions, LIMA and Perplexity Discover.

| Strategy                                            | Effect on Position-Adjusted Word Count |
| --------------------------------------------------- | -------------------------------------- |
| Quotation Addition (quotes from named experts)      | ~ +27.8 %                              |
| Statistics Addition (figures over adjectives)       | ~ +25.9 %                              |
| Fluency Optimization                                | ~ +25.1 %                              |
| Cite Sources (outbound authoritative links)         | ~ +24.9 %                              |
| Authoritative tone                                  | positive                               |
| Easy-to-Understand / Technical Terms / Unique Words | weak or mixed                          |
| **Keyword Stuffing**                                | **approximately zero or negative**     |

**The methodological limitation must travel with the numbers.** Evaluation ran against a
_prototype_ generative engine (top-5 Google results plus GPT-3.5-turbo), not against live Google
AI Overviews, ChatGPT Search or Perplexity. The percentages describe a laboratory engine. They
justify the direction of a rule; they do not justify a threshold.

Two secondary findings that matter for how we deploy this:

- Effects were domain-dependent: `Cite Sources` performed best on factual queries, `Statistics` in
  law, government and opinion, `Quotation` in people and society, `Fluency` in business and
  science. A single global setting is wrong.
- **Sites ranking poorly gained the most, up to +115 % visibility.** GEO is primarily a lever for
  non-leaders, which is precisely the position of every project in our current portfolio.

The rules that carry these findings:

**`GEO-09 · WARN · Minimum count of sourced numeric claims per document.**
**`GEO-10 · WARN · Minimum count of direct quotations from identifiable experts.**
**`GEO-11 · WARN · Minimum count of outbound citations to authoritative primary sources.**
**`GEO-12 · BLOCK · Keyword density above the language pack's threshold fails.**

`GEO-09` and `GEO-11` overlap with `WRT` group B (claim provenance and primary source ratio) and
are satisfied by the same counters; they are stated here so the GEO rationale is recorded against
them. `GEO-10` is additive: a quotation from a named, identifiable person is not the same artefact
as a cited statistic, and nothing in `05-writing-core.md` requires one. `GEO-12` is the only
"optimisation" in this entire section that runs in the negative direction, and it is a `BLOCK`
because stuffing measurably costs visibility rather than merely wasting effort.

**`GEO-13 · WARN · Key term definitions are written as self-contained paragraphs.** Extraction
operates at passage level, so a definition split across a preceding sentence and a following list
is not retrievable as a unit.

### 3.2 First-third placement

`[measurement]` 44.2 % of LLM citations are drawn from the first 30 % of a document, and extraction
operates on passages rather than whole pages, which is why sidebars, footers and "related reading"
blocks never enter a cited fragment. `[source: EVIDENCE.md#e06-internal-linking]`

This is the evidentiary basis for `WRT-33` and for the link-placement rules in `07-linking.md`.
It is not restated as a separate GEO rule.

### 3.3 Off-site brand signals correlate far more strongly than links

`[measurement]` Ahrefs, 75,000 brands, two waves (2025-05-26 and 2025-12-12), Spearman, filtered to
DR > 40 and volume ≥ 800:

| Factor                | ChatGPT | AI Mode | AI Overviews |
| --------------------- | ------- | ------- | ------------ |
| YouTube mentions      | 0.737   | 0.737   | 0.737        |
| Branded web mentions  | 0.664   | 0.709   | 0.656        |
| Branded anchors       | 0.511   | 0.628   | 0.527        |
| Branded search volume | 0.352   | 0.466   | 0.392        |
| Domain Rating         | 0.266   | 0.285   | 0.326        |
| **Backlinks**         | ~0.19   | ~0.22   | ~0.24        |

**This is a correlation and must not be written up as a mechanism.** The authors state so
themselves: _"Correlation isn't causation… that doesn't mean improving these metrics will
automatically boost your AI visibility"_, and they characterise the coefficients as moderate to
very weak. Roughly 26 % of brands in the sample had no mentions at all.

One reading is defensible and useful: ChatGPT correlates least with classical metrics, which makes
it the most accessible surface for a young brand. `[source: EVIDENCE.md#e01-geo-answer-engines]`

### 3.4 The contradiction we are required to carry

Citation and mention are not the same objective, and the data actively disagree with treating them
as one:

- Ahrefs: branded web mentions are the strongest predictor of AI Overview citation (0.664).
- Semrush, counter-data: only **21 %** of the most-cited domains in a category were also the
  most-mentioned brand, the correlation between citation and mention is weakly **negative**
  (−0.229), and **62 %** of AI citations produce no brand mention at all ("ghost citations").
  `[source: EVIDENCE.md#e10-eeat-entities-schema]`

**`GEO-24 · WARN · Citation rate and mention rate are tracked as two separate metrics and never
substituted for one another.**

Optimising for citation (structure, extractability, facts) does not produce recognition.
Optimising for recognition (PR, YouTube, communities) does not produce citations. A report that
collapses them into one "AI visibility" number is describing neither.

### 3.5 Off-site: planning prompts, never gates

These three rules are the only place in Kiln where a correlation is allowed to influence what gets
planned. They are capped at `INFO` deliberately, and §14.3 explains why they must stay there.

**`GEO-15 · INFO · Each priority cluster carries an off-site asset plan.**

YouTube mentions show the highest single correlation with AI visibility in the measured data
(0.737, identical across ChatGPT, AI Mode and AI Overviews). `[measurement, source: EVIDENCE.md#e01-geo-answer-engines]`
YouTube is also a dominant cited domain inside AI Overviews, frequently cited for queries where it
does not rank organically. `[vendor, source: EVIDENCE.md#e01-geo-answer-engines]`

This does not establish causation, and the confound is obvious: brands large enough to sustain
YouTube reach are large enough to be cited for other reasons. The rule therefore produces a
planning line item and a question for the human, never a blocked publication.

**`GEO-16 · INFO · The digital PR target list is derived from the prompt set, not invented.**

`competitor_source_overlap` in `geo_score.py` already yields the third-party domains that answer
engines cite instead of us, per cluster and per engine. That list is the outreach target set: those
domains are demonstrably in the retrieval path for the exact prompts we care about.

This is the cheapest off-site input Kiln produces, because it costs nothing beyond a measurement we
run anyway, and it is specific to our prompts rather than to a generic authority score. The human
decides what to do with it; Kiln does not conduct outreach.

**`GEO-17 · INFO · Entity presence is checked, and inconsistency is reported.**

Check that the brand resolves to a Wikidata entity, that `sameAs` on the entity home lists at least
three reachable URLs, and that the author entities referenced by articles resolve consistently
across the external profiles they claim. `[best practice, source: EVIDENCE.md#e10-eeat-entities-schema]`

Two honest limits. First, entity work belongs to the trust-signal set and is only surfaced here
because the same signals correlate with citation; the authoritative treatment sits with the
site-level trust rules, not with GEO. Second, Wikidata is reachable where Wikipedia is not, and a
significant part of the Knowledge Graph is built from it, which is why the check targets Wikidata
specifically rather than "get a Wikipedia page".

### 3.6 Reserved and intentionally unused IDs

`GEO-07`, `GEO-08` and `GEO-14` are **deliberately absent**. They were reserved during drafting for
answer-first placement, passage self-sufficiency and machine-readable dates, and were then dropped
once those rules were confirmed to exist as `WRT-30`, `WRT-31`, `WRT-32` and `WRT-33` in
`05-writing-core.md`. Duplicating them here would have created two thresholds for one property,
which is precisely the failure `P8` exists to catch.

The gap is recorded rather than closed by renumbering, because rule IDs are cited from skills,
hooks and review logs, and renumbering silently invalidates that history.

---

## 4. What is rejected, with the evidence

| Rejected                                                           | Evidence                                                                                                                                                                                                                                                                                                                                                                                                                                                        |
| ------------------------------------------------------------------ | --------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| `llms.txt` as a visibility factor                                  | **97 % of these files received zero requests** over May 2026 across 137,210 domains. Of the requests the remaining 3 % did receive, AI retrieval bots accounted for 1.1 %; SEO auditors led at 21.7 %. Claude-Code outranked most search AI bots, so the real consumer is code agents. Google: neither helps nor hurts; Mueller compared it to the discredited `keywords` meta tag. `[source: EVIDENCE.md#e01-geo-answer-engines, EVIDENCE.md#e10-eeat-entities-schema]`                                        |
| Chunking content for LLMs                                          | Google's optimization guide states directly that content should not be broken into small pieces "so AI understands it better", and the position was restated publicly on 2026-01-08. `[source: EVIDENCE.md#e01-geo-answer-engines, EVIDENCE.md#e03-ai-detection-and-humanization]`                                                                                                                                                                                                                                             |
| AI-specific schema                                                 | Google verbatim: "There's also no special schema.org structured data that you need to add." `[source: EVIDENCE.md#e01-geo-answer-engines, EVIDENCE.md#e10-eeat-entities-schema]`                                                                                                                                                                                                                                                                                                                                      |
| Facts placed in markup but absent from visible text                | Williams-Cook, February 2026: an address present only inside deliberately invalid, invented JSON-LD (non-existent `@context`, non-existent `@type`) was extracted and returned by both ChatGPT and Perplexity. The correct inference is not "schema works" but that **LLMs tokenise `<script>` contents as plain text with no semantic parsing**. Exploiting this is a cloaking violation of Google's structured data rules. Forbidden. `[source: EVIDENCE.md#e10-eeat-entities-schema]` |
| Keyword stuffing                                                   | Approximately zero or negative in the only peer-reviewed test. `[source: EVIDENCE.md#e01-geo-answer-engines]`                                                                                                                                                                                                                                                                                                                                                                        |
| Self-promotional listicles                                         | Cited in 69 % of cases while recommending a competitor, and the penalty lands on the whole domain rather than the page. `[source: EVIDENCE.md#e02-practitioner-pulse]` Already in the `P` appendix.                                                                                                                                                                                                                                                                                       |
| `FAQPage` / `HowTo` as a citation lever                            | FAQ rich results stopped showing on 2026-05-07; HowTo desktop rich results were removed in September 2023. Vendor claims of "FAQPage parsing for AI answers" carry no disclosed method. The types themselves are not deprecated and need not be removed. `[source: EVIDENCE.md#e10-eeat-entities-schema]`                                                                                                                                                                                |
| Embedding optimisation, adversarial RAG injection, AI shadow sites | Unfalsifiable from outside (each platform uses its own embedding model), or an attack rather than a tactic, or a cloaking violation. `[source: EVIDENCE.md#e01-geo-answer-engines]`                                                                                                                                                                                                                                                                                                    |

The inverse of the JSON-LD finding is the part worth keeping: **if a fact matters, it belongs in
the visible text**, because the visible text is what is tokenised with certainty. Markup is a
duplicate, not a channel.

---

## 5. Platform divergence: there is no "optimise for LLMs"

Domain overlap between answer engines is approximately **11 %** across 5.5 M answers `[vendor,
Search Atlas]`. The figure itself is unverified, but the direction is corroborated independently:
source sets differ radically between engines.

Volume of sourcing differs just as sharply. ChatGPT cites on average ~15 sources per answer and
leans on community and reference properties (Reddit, Wikipedia); Gemini cites ~3.
`[vendor + measurement, Semrush AI Visibility Index, 126 M prompts, Jan–Apr 2026]` These are not
two settings of one market. One is a long tail, the other is close to an oligopoly, and a tactic
that works in the first is irrelevant in the second.

**`GEO-22 · BLOCK · Metrics are never averaged across engines or across locales.**

Operationally this means three things, and they are the reason the measurement design in §6 looks
heavier than a single tracker would:

1. Prompt sets are maintained per engine group where the query grammar differs, and always per
   locale.
2. Every stored metric is keyed by engine. A single "AI visibility score" is not produced, because
   there is no market it would describe.
3. Off-site target lists diverge by design: community and reference properties for ChatGPT,
   YouTube plus classical organic for Google's surfaces.

---

## 6. The measurement loop

This is the deliverable of the section. Commercial trackers cost between $29 and $489 per month
and all of them do the same thing: run a fixed prompt set and count mentions. None of them has
access to platform internals. `[source: EVIDENCE.md#e01-geo-answer-engines]` Running the same procedure with our own keys
costs a few dollars per month and leaves us holding the raw answers, which is what the learning
loops in `P9` actually need.

### 6.1 The prompt set

**`GEO-18 · BLOCK · The prompt set is frozen. Changing it starts a new series.**

Working range: **40 to 100 prompts**. `[source: EVIDENCE.md#e01-geo-answer-engines]` Below 40, variance consumes the
signal; above 100, cost outruns value. Prompts are distributed across 3 to 4 intent clusters:

| Cluster            | Shape                               | Buyer stage |
| ------------------ | ----------------------------------- | ----------- |
| Category discovery | `best X`, `X for <segment>`         | early       |
| Displacement       | `X alternatives`, `X vs Y`          | mid         |
| Commercial detail  | `X pricing`, `is X worth it`        | late        |
| Problem-phrased    | the user's symptom, product unnamed | early       |

Each prompt carries a `cluster_id` from `.kiln/semantics/clusters.json`, so citation results roll
up against the same clusters the content plan is built on. Without that key, GEO results cannot be
compared to anything else Kiln measures.

**`GEO-19 · BLOCK · The brand denominator is frozen.** Share of voice is
`our mentions / all category brand mentions`over the fixed set. If the denominator moves between
measurements, the series is not a series. New competitors discovered mid-series are recorded and
enter at the next explicit version bump of`brands.yml`, never retroactively.

### 6.2 Repetition is not optional

**`GEO-20 · BLOCK · Minimum 3 repeats per prompt, per engine, per measurement. Conclusions from a
single run are forbidden.**

Two independent reasons, both measured:

- Generative answers are unstable between runs for identical inputs. `[source: EVIDENCE.md#e05-semantics-and-clustering,
arXiv:2510.11560]`
- Citation drift runs at **40 to 60 % per month** at the level of an individual query.
  `[practitioner, source: EVIDENCE.md#e01-geo-answer-engines]`

At that drift rate, a single-run before-and-after comparison cannot distinguish an effect from
noise. That sets the honest floor on attribution:

**`GEO-23 · WARN · No change is attributed to an edit until it has been observed across at least
two consecutive measurement cycles.**

Deltas at 30, 60 and 90 days are reported alongside the drift caveat rather than in place of it. A
report showing a citation-rate movement without stating the drift band is not a measurement, it is
a coin flip with a chart.

### 6.3 Grounding provenance

**`GEO-21 · BLOCK · Every stored answer carries `grounding: api | ui`, and the two are never
pooled.**

An engine queried through its API and the same engine used through its consumer interface perform
different retrieval and return different source sets. `[source: EVIDENCE.md#e07-competitive-intelligence]` Mixing them produces a
number that describes neither. The API path is what we can automate cheaply; the UI path is what
users actually experience. Both are legitimate, separately.

### 6.4 Metrics

| Metric                      | Definition                                                                                               |
| --------------------------- | -------------------------------------------------------------------------------------------------------- |
| `citation_rate`             | share of prompts whose answer links to our domain                                                        |
| `share_of_voice`            | our brand mentions / all category brand mentions, frozen denominator                                     |
| `mention_rate`              | share of prompts where the brand is named, with or without a link                                        |
| `ghost_mention_rate`        | cited without being named, the inverse of the Semrush ghost-citation effect                              |
| `position_in_answer`        | which third of the answer the mention appears in, a proxy for the PAWC metric used in the Princeton work |
| `sentiment`                 | positive / neutral / listed among drawbacks                                                              |
| `competitor_source_overlap` | third-party domains cited instead of us, which is a ready-made digital PR target list                    |

`citation_rate` is exported as `LI-5` into `08-measurement.md`.

### 6.5 Storage

```
.kiln/geo/
├── prompts.yml                  frozen prompt set, versioned
├── brands.yml                   frozen denominator, versioned
├── runs/
│   └── 2026-08-07/
│       └── chatgpt/
│           └── p017__r2.json    one raw stored answer
├── scores/
│   └── 2026-08-07.json          computed metrics
└── access/
    └── 2026-08.json             crawler access from server logs
```

Raw answers are retained indefinitely. They are the only artefact that makes a past measurement
re-scorable when a metric definition changes, and re-scoring history is otherwise impossible
because the engines cannot be asked the same question twice.

### 6.6 Cost

100 prompts × 4 engines × 3 repeats = 1,200 calls per measurement cycle. At current API pricing
this lands in the range of **$2 to $5 per month** against $29 to $489 for a subscription that
returns less. `[source: EVIDENCE.md#e12-data-apis-and-pricing]` The saving is secondary; holding the raw answers is the point.

---

## 7. Log-based verification

Server logs answer a different question from the prompt set, and the difference is easy to blur.

**`GEO-25 · INFO · Crawler access is necessary, not sufficient, and is never reported as
citation.**

What the logs prove: an AI crawler fetched a specific URL at a specific time, and what status it
received. What they do not prove: that anything was cited, retrieved into an answer, or seen by a
user. A page can be fetched daily and never cited.

What to collect per bot (`OAI-SearchBot`, `Claude-SearchBot`, `PerplexityBot`, `GPTBot`,
`ClaudeBot`, `Google-Extended`, `CCBot`): fetch count, unique URLs, status code breakdown, 404
share, top URLs, first and last seen.

**Attribution caveat that must be implemented, not just documented.** User-agent strings are
trivially forged. Where a vendor publishes IP ranges or supports reverse DNS verification, verify
and record `verified_by: reverse_dns | ip_range`. Where verification is impossible, record
`verified_by: ua_only` and treat the figure as an upper bound. An unverified user-agent count is
not evidence of access.

Referral traffic from answer engines is a third, weaker signal: it confirms a human followed a
link, but under-counts severely, since clicks on links inside an AI summary occur in roughly 1 %
of visits. `[source: EVIDENCE.md#e01-geo-answer-engines, Pew Research, 900 US adults, 68,879 searches]`

---

## 8. What Search Console gives, and what it does not

The Generative AI performance report (launched 2026-06-03, expanded 2026-06-23, history from
2026-05-18) is the only official first-party source of GEO data. It reports **impressions only**:
no queries, no clicks, no CTR, no position. AI Overviews and AI Mode are merged into one surface,
and rollout is partial. Source-level breakdown is available only through manual CSV export from
the interface, not through the API and not through BigQuery.
`[source: EVIDENCE.md#e01-geo-answer-engines, EVIDENCE.md#e04-search-console, cross-referenced at `MSR-15`]`

The consequence is already recorded as `MSR-15 · BLOCK` in `08-measurement.md`: **the GEO loop is
measured independently of Search Console.** `LI-5` is produced here, by the mechanics of §6, and
imported there. Search Console contributes exactly one signal to this section, the ratio of AI
impressions to total impressions per page, and only via manual export.

Note also that AI impressions are a _subset_ of ordinary web impressions rather than additional
volume, so the ratio is well-formed and there is no double counting.

---

## 9. Locale

**`GEO-22`** covers this at the metric level; the operational rules are:

- Prompt sets are authored per locale and per language, in that locale's language. A prompt set
  translated from another locale measures translation quality, not market position.
- Citation in one language says nothing about another. A brand dominant in English answers may be
  absent from Ukrainian ones for the same query intent, and the reverse.
- Access checks run per locale, because rendering and edge rules frequently differ per subdirectory
  or subdomain.
- Share of voice is never summed or averaged across locales.

---

## 10. What code does, what the agent does, where a human is required

| Step                                               | Code | Agent | Human    |
| -------------------------------------------------- | ---- | ----- | -------- |
| Access gates (`GEO-01` to `GEO-06`)                | ✔    |       |          |
| Prompt set authoring                               |      | ✔     | approves |
| Brand denominator                                  |      | ✔     | approves |
| Running probes                                     | ✔    |       |          |
| Scoring stored answers                             | ✔    |       |          |
| Classifying a mention's sentiment                  |      | ✔     |          |
| Log parsing and bot verification                   | ✔    |       |          |
| Reading `competitor_source_overlap` into a PR plan |      | ✔     | decides  |
| Attributing a change to an edit                    |      | ✔     | confirms |

The split follows the rule used throughout the doctrine: code computes anything that must be
reproducible, an agent proposes interpretations, and a human decides anything irreversible or
budget-bearing. Scoring in particular must be deterministic, because a metric that cannot be
recomputed identically cannot support `P8`.

---

## 11. Prohibited

| Prohibited                                                     | Reason                                                                                       |
| -------------------------------------------------------------- | -------------------------------------------------------------------------------------------- |
| Building a "GEO markup" subsystem                              | Officially unnecessary; effect at best indirect (`P12`)                                      |
| Placing facts in JSON-LD that are absent from the visible text | Works on LLMs, violates Google's structured data rules, cloaking risk. Negative risk/benefit |
| Reporting `llms.txt` as an achievement or a factor             | 97 % are never requested                                                                     |
| Chunking content for LLM consumption                           | Contradicted by Google directly                                                              |
| Serving different content to AI crawlers                       | Cloaking                                                                                     |
| Conclusions from a single probe run                            | `GEO-20`; drift of 40–60 % per month                                                         |
| Pooling `api` and `ui` grounding                               | `GEO-21`; different retrieval, different source sets                                         |
| A single cross-engine "AI visibility score"                    | `GEO-22`; ~11 % domain overlap means it describes no market                                  |
| Reporting crawler hits as citations                            | `GEO-25`; access is necessary, not sufficient                                                |
| Treating unverified user-agent counts as access evidence       | User-agents are forged trivially                                                             |
| Sourcing SEO or GEO guidance from model knowledge              | `GEO-26`; a fabricated claim reached AI Overviews within 24 hours                            |
| Nagging the owner about blocked training bots                  | `GEO-06`; that is a commercial decision, not a defect                                        |

---

## 12. Layer 2 script specifications

Probing is non-deterministic by nature. Scoring must not be. The split below exists so that a
metric can be recomputed identically from stored answers months later, which is the only way GEO
results can participate in the learning loops.

### 12.1 `geo_probe.py`

Runs the frozen prompt set and stores raw answers. Makes network calls. Not deterministic.

**Input:** `--prompts .kiln/geo/prompts.yml` · `--brands .kiln/geo/brands.yml` ·
`--engines chatgpt,perplexity,google,claude` · `--repeats 3` · `--locale uk-UA` ·
`--grounding api|ui` · `--run-date YYYY-MM-DD` · `--out .kiln/geo/runs/`

**Output:** one file per probe at `runs/<run_date>/<engine>/<prompt_id>__r<n>.json`:

```json
{
  "run_date": "2026-08-07",
  "prompt_id": "p017",
  "prompt_text": "...",
  "cluster_id": "credit-online-comparison",
  "engine": "chatgpt",
  "model": "gpt-5.2",
  "grounding": "api",
  "locale": "uk-UA",
  "repeat_index": 2,
  "requested_at": "2026-08-07T09:14:22Z",
  "latency_ms": 4180,
  "answer_text": "...",
  "citations": [
    {
      "url": "https://...",
      "domain": "...",
      "anchor_text": "...",
      "position_index": 3
    }
  ],
  "raw_response": {},
  "error": null
}
```

**Exit codes:** `0` all probes stored · `1` configuration invalid (unfrozen prompt set, missing
`cluster_id`, unknown engine) · `2` partial failure, failed probes stored with `error` populated ·
`3` total failure (credentials or network).

A probe that fails is stored as a record with `error` rather than dropped, because a silently
shorter sample changes every rate it feeds.

### 12.2 `geo_score.py`

Computes metrics from stored answers. **Makes no network calls.** Given identical inputs it must
produce byte-identical output.

**Input:** `--runs .kiln/geo/runs/<run_date>/` (or a range for a series) ·
`--brands .kiln/geo/brands.yml` · `--clusters .kiln/semantics/clusters.json` ·
`--thresholds .kiln/thresholds.yml`

**Output:** `.kiln/geo/scores/<run_date>.json`:

```json
{
  "run_date": "2026-08-07",
  "locale": "uk-UA",
  "prompt_set_version": "3",
  "brands_version": "2",
  "repeats": 3,
  "engines": {
    "chatgpt": {
      "grounding": "api",
      "prompts_scored": 100,
      "prompts_failed": 2,
      "citation_rate": 0.14,
      "share_of_voice": 0.061,
      "mention_rate": 0.19,
      "ghost_mention_rate": 0.58,
      "position_in_answer": { "first_third": 5, "middle": 6, "last_third": 3 },
      "competitor_source_overlap": [{ "domain": "...", "citations": 41 }]
    }
  },
  "by_cluster": { "credit-online-comparison": { "citation_rate": 0.22 } },
  "thresholds_used": { "min_repeats": 3 },
  "warnings": ["drift_window_insufficient"]
}
```

**Exit codes:** `0` scored · `1` input invalid · `2` insufficient repeats, refuses to score rather
than emitting a number built on one sample.

`thresholds_used` is mandatory on every output. Without it, recalibrating a threshold silently
rewrites the meaning of the whole history.

### 12.3 `bot_logs.py`

Parses server access logs for AI crawler activity. Deterministic.

**Input:** `--logs <path or glob>` · `--format combined|json` · `--bots <list>` ·
`--window 2026-08` · `--verify reverse_dns|ip_range|none`

**Output:** `.kiln/geo/access/<window>.json`:

```json
{
  "window": "2026-08",
  "bots": {
    "OAI-SearchBot": {
      "fetches": 1841,
      "unique_urls": 612,
      "status_breakdown": { "200": 1502, "301": 44, "404": 288, "403": 7 },
      "share_404": 0.156,
      "top_urls": [{ "url": "...", "fetches": 61 }],
      "first_seen": "2026-08-01T02:11:04Z",
      "last_seen": "2026-08-31T22:47:19Z",
      "verified_by": "reverse_dns"
    }
  }
}
```

**Exit codes:** `0` parsed · `1` unparseable input · `2` `share_404` above threshold for at least
one bot, which is actionable rather than fatal.

---

## 13. Sources

All verified 2026-08-07. Full citation lists in `EVIDENCE.md#e01-geo-answer-engines` and
`EVIDENCE.md#e10-eeat-entities-schema`.

**Official documentation**

- Google Search Central, AI Features and Your Website (updated 2025-12-10) —
  https://developers.google.com/search/docs/appearance/ai-features
- Google Search Central, Guide to Optimizing for Generative AI Features (updated 2026-07-10) —
  https://developers.google.com/search/docs/fundamentals/ai-optimization-guide
- Google Search Central Blog, Generative AI performance reports in Search Console (June 2026) —
  https://developers.google.com/search/blog/2026/06/gen-ai-performance-reports
- OpenAI, bots and crawlers documentation — https://developers.openai.com/api/docs/bots

**Peer-reviewed**

- Aggarwal, Murahari, Rajpurohit, Kalyan, Narasimhan, Deshpande, "GEO: Generative Engine
  Optimization", arXiv:2311.09735, ACM SIGKDD 2024 — https://arxiv.org/abs/2311.09735

**Measurements**

- Vercel + MERJ, "The rise of the AI crawler", 2024-12-17 —
  https://vercel.com/blog/the-rise-of-the-ai-crawler
- Pew Research Center, 2025-07-22 —
  https://www.pewresearch.org/short-reads/2025/07/22/google-users-are-less-likely-to-click-on-links-when-an-ai-summary-appears-in-the-results/
- Ahrefs, AI Overview Brand Visibility Factors, 2025-05-26 —
  https://ahrefs.com/blog/ai-overview-brand-correlation/
- Ahrefs, Top Brand Visibility Factors in ChatGPT / AI Mode / AI Overviews, 2025-12-12 —
  https://ahrefs.com/blog/ai-brand-visibility-correlations/
- Ahrefs, "We Analyzed 137K Sites: 97% of llms.txt Files Never Get Read" —
  https://ahrefs.com/blog/llmstxt-study/
- Semrush, The Ghost Citations Study — https://www.semrush.com/blog/the-ghost-citations-study/
- Mark Williams-Cook, "Schema, LLMs and the Low Bar for Evidence in GEO" —
  https://markwilliamscook.substack.com/p/schema-llms-and-the-low-bar-for-evidence

**Infrastructure and access policy**

- Cloudflare Content Signals Policy and Pay Per Use coverage, via `EVIDENCE.md#e01-geo-answer-engines`

---

## 14. Conflicts with the principles

**14.1 `GEO-09` to `GEO-11` carry laboratory percentages into production thresholds.**
The Princeton figures were measured on a prototype engine, not on any live answer engine. The
direction is peer-reviewed; the magnitudes are not transferable. The minimum counts must therefore
ship as `[expert judgement, needs calibration]` and start in observe-only mode, exactly as
`05-writing-core.md` requires for its own uncalibrated group. Anyone reading "+27.8 %" as an
expected outcome on a live site has misread the study.

**14.2 `GEO-10` risks becoming a quota that manufactures fake quotes.**
A rule demanding "at least M expert quotations" creates direct pressure to invent or pad them, and
a fabricated quotation is a `P1` violation of the most damaging kind. The rule is only safe while
the primary-source gate in `05-writing-core.md` holds every quotation to an attributable, dated
source. If those two rules ever drift apart, `GEO-10` must be suspended, not softened.

**14.3 The off-site rules (`GEO-15` to `GEO-17`) rest on correlation and sit close to `P3`.**
YouTube presence correlating at 0.737 with AI visibility does not establish that publishing videos
causes citations; the likeliest confound is that brands large enough to have YouTube reach are
large enough to be cited for other reasons. These are planning prompts, never gates, and they must
never acquire a severity above `INFO` without an intervention study we have not run.

**14.4 The measurement loop cannot separate our effect from platform drift.**
At 40 to 60 % monthly citation drift, and with generative answers unstable between identical runs,
a 100-prompt set measured three times gives a confidence interval wide enough to swallow most
realistic improvements. `GEO-23` mitigates this by requiring two consecutive cycles, but it does
not solve it. Honest position: for the first two quarters this loop measures _presence and
direction_, not effect size, and any report implying otherwise is overclaiming. This is the single
weakest measurement in Kiln and it should be labelled as such on the dashboard.

**14.5 `GEO-01` conflicts with nothing in the doctrine but may conflict with the project.**
A `BLOCK` on client-side rendering can halt a project whose stack cannot deliver server rendering
without a rewrite. `ONB-10` catches this at onboarding, where the answer is "fix it or do not
onboard". Mid-flight, after months of work, the same gate is far more expensive to honour. The
rule stays a `BLOCK` because a silently invisible site is worse, but the escalation path (halt
publishing to the affected locale, not to the whole project) exists specifically to keep it
survivable.

**14.6 Unresolved: the Cloudflare default landing 2026-09-15.**
It takes effect in five weeks and applies to new sites and new customers, with "mixed" crawlers
blocked by default. Whether any of our three projects is affected has not been checked, and the
economics driving it (Anthropic's crawler reportedly making ~38,000 fetches per referral visit,
OpenAI's ~1,091) suggest further tightening rather than less. This needs a dated re-check before
the date, not after it.
