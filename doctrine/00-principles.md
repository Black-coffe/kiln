# Kiln: Iron Principles

> This is the root document of the doctrine. Everything else in `doctrine/` defers to it.
> Any conflict between a rule and this file is resolved in favour of this file.
> No clause may be changed except through a PR following the `RULE-CHANGE.md` template.

**Version:** 0.1.0 · **Date:** 2026-08-07 · **Review:** mandatory every 90 days

---

## Severity scale

Three levels, used identically in every doctrine file and by every script. There is no fourth level
and no synonyms; `BLOCKER`, `CRITICAL` and similar words must not appear in any rule.

| Level   | Meaning                                                          | Machine behaviour                                            |
| ------- | ---------------------------------------------------------------- | ------------------------------------------------------------ |
| `BLOCK` | the action must not proceed until the condition is satisfied     | non-zero exit; a publishing gate denies the operation        |
| `WARN`  | the action proceeds, a human must see the finding and may accept | zero exit; the finding is surfaced in the review pack        |
| `INFO`  | observation only, recorded for calibration                       | zero exit; written to statistics, never shown as a complaint |

**A `BLOCK` requires a named, reproducible check.** A rule that cannot be evaluated the same way
twice must not carry `BLOCK` severity, because an unreproducible blocker is an opinion with a
lock on it.

**Language pack metrics may never be `BLOCK`.** Everything in `doctrine/lang/*.md` that concerns
vocabulary, syntax, punctuation or form statistics is capped at `WARN`. This is not a stylistic
preference: gating publication on a stylometric score is the same failure P3 forbids, only with our
own detector instead of a purchased one. Language packs catch carelessness; they do not define
quality, and they must not hold the gate.

---

## P0. Kiln is a kiln, not a conveyor belt

The value of this system lies not in how much text it produces but in how much it **refuses to
ship**. Generation is cheap in 2026 and available to everyone. Projects die from the absence of a
brake, not from a shortage of content.

Direct consequence for metrics: the rejection rate and the reasons for rejection are the
**primary** measure of Kiln's operation. The number of published articles is secondary.

**Evidence.** Across 220+ domains served by AI content platforms: 54 % lost ≥30 % of peak traffic,
39 % lost ≥50 %, 22 % lost ≥75 %. The trajectory is identical in every case: growth for 6 to 12
months, a peak, then a collapse that frequently lands below the starting baseline. Most collapses
occurred **after** the vendors published case studies celebrating those same sites.
→ `[source: EVIDENCE.md#e14-content-operations]`

---

## P1. Evidence-first: model output is not a fact

A claim about the world enters the text only if it has a source that **we opened and read
ourselves**, carrying a URL and a date. The model may transform what has already been verified; it
must not originate a claim about the world.

This is not a stylistic preference. It defends against two distinct failures at once:

1. **Factual error.** Half of the "AI text markers" by which humans identify machine writing are
   not stylistic at all. They are unverified facts: broken DOIs, citations to a publication that
   carries no such material, figures with no source. A primary source gate closes half of
   "humanity" for free.
2. **Staleness.** Model knowledge lags by months. A rate, a tariff, a limit or a term may have
   changed yesterday. In YMYL this is not imprecision; it is harm to the reader.

**Severity: `BLOCK`.** A draft containing an unverified claim about the world must not be published.

---

## P2. Publishing pace equals verification capacity

Output speed is determined by how much material humans can review on the substance, never by how
much the model can write. It must not be raised on the grounds that production happens to be
running fast.

Two distinct numbers, in two distinct files, and confusing them is how the cap quietly disappears:

| Number                                                        | File                   | Origin                                                              |
| ------------------------------------------------------------- | ---------------------- | ------------------------------------------------------------------- |
| **Declared review capacity** — reviewers, hours, lens mapping | `.kiln/project.yml`    | stated by the owner at onboarding; changes only by a human decision |
| **Derived publishing cap** — items per period                 | `.kiln/thresholds.yml` | computed from actual review logs; recalculated automatically        |

The declared capacity is an input and is never overwritten by the system. The derived cap is
calibrated data under P10 and is never edited by hand. Until enough review logs exist to compute
it, the cap falls back to the declared capacity, and that fallback state is recorded explicitly so
nobody mistakes an assumption for a measurement.

**Evidence.** The difference between the survivors and the destroyed was **structural, not
stylistic**. Forbes Advisor fell from 23.6 M to 11 K visits (−99.95 %); CNN Underscored fell from
3.2 M to 945. Wirecutter and Strategist were untouched. The distinguishing factor was an in-house
editorial operation versus an outsourced one. Since 2024-11-19, first-party involvement
(white-label arrangements, licensing, an ownership stake) is explicitly not a defence.
→ `EVIDENCE.md#e13-policy-and-risk`

**No reliable data on a "safe pace" exists.** Every circulating figure ("16+/month → 3.5×", "104
posts/month") is agency self-reporting, and the flagship case study is itself labelled an
"anonymised composite". Hard-coding those numbers is cargo cult. Kiln logs its own pace honestly
and will in time become the first genuine source of this data.

---

## P3. No detector and no content score may ever be a condition of publication

Gating publication on passing GPTZero, Originality, Copyleaks or any equivalent is forbidden.
Gating publication on a "content score" from Surfer, Clearscope, MarketMuse or any equivalent is
forbidden.

**Evidence.**

- Correlation between the share of AI-generated text on a page and its ranking position: **0.011**,
  which is noise. 5.3 % of top-3 results are fully AI-generated; 40 % of pages flagged "very high
  AI" are indexed. → `EVIDENCE.md#e03-ai-detection-and-humanization`
- Correlation between a vendor content score and ranking position: **0.28** on Surfer's own data;
  17.5 % for Clearscope. 74 % of the variance sits outside the score entirely. Pages scoring 85+
  have been documented on the third page of the SERP, and pages scoring 60 to 70 in position one.
  → `EVIDENCE.md#e11-content-quality-signals`
- Optimisers measure **similarity to the top**. That is the exact inverse of what is needed:
  information gain is difference from the top, not agreement with it. → `EVIDENCE.md#e15-market-landscape`
- "Humanisers" are snake oil. No independent measurement exists, every published test is an
  affiliate test, and bypass rates are falling. → `EVIDENCE.md#e03-ai-detection-and-humanization`

One tactic is separately dead: raising perplexity or burstiness to defeat a detector. Detectors in
2026 no longer rely on perplexity. → `EVIDENCE.md#e03-ai-detection-and-humanization`, arXiv:2602.05769

---

## P4. Humanity comes from specificity, not from styling

Humans identify machine-written text with 87.6 % accuracy across nine languages, and the gap runs
along three axes: **concreteness, cultural nuance, diversity**. It does not run along vocabulary or
sentence length.

Exactly one technique follows from this. The text must contain something the model could not have
known: our own data, our own measurement, our own screenshot, a named figure taken from a primary
source, a live quotation from a person, a description of how the checking was actually done.

Stop-word lists and syntactic metrics have their place, but they are **secondary** and they live in
the language packs at `doctrine/lang/*.md`, not here. They catch traces of carelessness; they do not
create quality.

→ `EVIDENCE.md#e03-ai-detection-and-humanization`, arXiv:2502.11614

---

## P5. The language-independent core is separate from the language packs

Metrics that do not depend on language (original claim density, unevenness of sentence length, share
of primary sources, n-gram overlap with the top results, time to answer the question posed by the
heading) live in the core and apply everywhere.

Everything touching the lexicon, syntax or punctuation of a specific language lives **only** in
`doctrine/lang/<code>.md` and is never carried across languages automatically.

**The doctrine's language is not the content's language.**

> The doctrine itself, along with all skills, agents, hooks and documentation, is written in
> English. The content Kiln produces is written in the language or languages of the target site,
> declared in `.kiln/project.yml`. The language pack is selected by the project's locale, never by
> the doctrine's language. Nothing in an English doctrine implies English output. Where a site runs
> several locales, each locale loads its own pack, and rules from one pack never apply to another.

**Evidence that the separation is necessary.** The rule "high dash density indicates AI authorship"
holds for English and breaks Cyrillic, where the dash is grammatically obligatory in the
construction «Х — це У». The precedent is on record: 349 correct occurrences were converted into
commas.

Second: any module that measures text length must use **Unicode-aware tokenisation**. `wc -w` does
not split Cyrillic into words, and on a live measurement it reported the English locale as six times
larger than the Ukrainian one when the two were in fact at parity. The conclusion was inverted.
→ `[internal observation, unpublished]`

---

## P6. One page, one intent, one URL

Two pages competing for the same intent damage each other. This is simultaneously the rule against
cannibalization and the rule against doorway pages, which spam policies penalise.

Machine-checkable invariant: **one normalised anchor phrase resolves to exactly one URL across the
entire site**. Automated internal linking driven by embeddings violates this invariant on its own
unless the violation is explicitly forbidden.

The fate of competing pages is decided from 90 days of GSC data, never by eye: different intent →
separate them by anchors and by content; same intent with a clear leader → 301; both valuable →
merge. → `EVIDENCE.md#e06-internal-linking`, `EVIDENCE.md#e04-search-console`

---

## P7. An irrelevant internal link is harmful, not neutral

Linking pages because "cosine similarity exceeds a threshold" is forbidden. Embeddings are a
**candidate retriever**, not a linking model; hierarchy gates and anchor relevance gates are
mandatory on top of them.

The decision criterion for a link is phrased as a question, not as a number: **would reading the
target page help the reader understand the paragraph they are in right now?** That question cuts
pairs with high cosine similarity and zero usefulness.

**Evidence.** The Content Warehouse leak contains `anchorMismatchDemotion`, a demotion for anchor
mismatch. Internal and external anchors are counted separately (`SimplifiedAnchor`), meaning the
internal anchor profile degrades independently of the external one. Controlled split tests: links
placed at the top of the body produced +25 % organic traffic, links in the footer +5 %; a test that
**reduced** the number of links produced a positive result. → `EVIDENCE.md#e06-internal-linking`

---

## P8. We measure the rules, not only the pages

Every rule in the doctrine carries counters: how many times it fired, how many times a human
overrode it, and what happened to the pages where it fired.

A rule that humans override more often than they accept is a candidate for deletion, not a subject
for argument. Disagreement between two review lenses on the same draft is evidence that the rule is
ambiguously worded, and such a disagreement enters the doctrine amendment queue automatically.

**Evidence that this is necessary.** In the owner's existing system, two mutually exclusive rules
coexisted: one document prescribed a phrase that another document forbade. Nobody noticed, because
nobody was counting. → `[internal observation, unpublished]`

---

## P9. Three learning loops, running at different speeds

| Loop   | Period | Signal                                                   | What it teaches              |
| ------ | ------ | -------------------------------------------------------- | ---------------------------- |
| Fast   | days   | review lens disagreements, gate hits and overrides       | writing rules, wording       |
| Medium | weeks  | indexation, first positions, citation rate in AI answers | page structure, topic choice |
| Slow   | months | GSC cohort dynamics, traffic, conversions                | strategy, cluster selection  |

Relying on the slow loop alone yields three or four learning cycles per year, which is far too few
to calibrate anything. The fast loop exists precisely for this reason.

---

## P10. The doctrine changes only through a PR carrying evidence

Automatic amendment of rules is forbidden. An agent may prepare a PR; an agent must not merge one.

A PR is accepted only if it contains: (1) sufficient evidence, defined below, (2) data with dates
and sources, (3) the list of affected projects, (4) the metric against which the amendment will be
verified, (5) the rollback condition.

**Sufficient evidence** means one of the following, and the PR must state which:

| Evidence class        | Minimum bar                                                                              |
| --------------------- | ---------------------------------------------------------------------------------------- |
| Controlled comparison | one measurement with a control group, reported in full including the group that lost     |
| Repeated observation  | at least 10 recorded instances across at least 2 projects, or 20 within a single project |
| Primary source        | a dated, first-party document (official documentation, policy, patent, filing, ruling)   |
| Recorded harm         | a single documented incident where the current rule caused damage, with the trace        |

A single project's data may propose an amendment but never justify one on its own, except under
"Recorded harm". The numeric bars above are themselves uncalibrated and are marked
`[expert judgement, needs calibration]`; their operational definition lives in
`11-self-learning.md`, which owns the counters they are read from.

The reason: the doctrine is shared across all projects and it is public. An amendment derived from
noise on one project moves every other project at the same time.

Threshold numbers (weights, limits, boundaries) are the exception. They are calibrated on project
data and remain **local**, in `.kiln/thresholds.yml`, and are never promoted into the shared doctrine
without a separate PR.

---

## P11. A human is mandatory at three points

1. **Project onboarding**, for everything that cannot be extracted from data (see
   `01-onboarding-grill.md`).
2. **Substantive review before publication**, by lens, with a log. "Substantive" carries the
   specific meaning the EU AI Act exemption requires and nothing looser: a **deliberate examination
   of the substance of the content by a natural person holding relevant knowledge of the subject
   matter**, recorded with what was changed and why. A proofread is not a review. An approval click
   is not a review. A reviewer without subject-matter competence in the topic does not discharge
   this for YMYL content. The log schema in `06-review-lenses.md` §6.2 is the operative
   specification, and it already meets this bar; this principle states the standard it enforces.
3. **Merges, redirects and page deletions**, which are irreversible actions on the existing corpus.

The human review log is a mandatory field, not an option. It closes three obligations at once:
exemption from labelling under EU AI Act Art. 50 (in force since 2026-08-02; a footer or general
terms are not sufficient), an E-E-A-T artefact, and an increase in the machine assessment of effort
invested (`contentEffort` in the Content Warehouse leak, described there as "LLM-based effort
estimation"). → `EVIDENCE.md#e10-eeat-entities-schema`, `EVIDENCE.md#e11-content-quality-signals`, `EVIDENCE.md#e13-policy-and-risk`

---

## P12. GEO is not a separate discipline and not a separate set of tags

Google states in its documentation that no additional requirements and no special markup exist for
appearing in AI Overviews or AI Mode. Since 2026-07-24 the spam policies cover attempts to
manipulate generative responses verbatim, which means GEO operates under the same enforcement regime
as SEO.

What is confirmed among the "GEO advice" and therefore adopted:

- **Server-side rendering is mandatory.** AI crawlers do not execute JavaScript. A CSR site is
  invisible to ChatGPT, Claude and Perplexity while remaining visible to Google. This is a blocking
  gate at onboarding.
- **robots.txt granularity.** Blocking `GPTBot` does not affect appearance in ChatGPT, whereas an
  accidental block of `OAI-SearchBot` produces complete invisibility. `ClaudeBot` ≠
  `Claude-SearchBot`.
- **Priority material belongs in the first third of the document.** 44.2 % of LLM citations come
  from the first 30 % of the text; extraction operates at the passage level, so sidebars, footers
  and "related reading" blocks never make it into the cited fragment.
- **Every passage is self-contained.** A section opening with "this", "it" or "such an approach"
  loses its meaning when pulled out of context and is not cited.

**Where self-contained ends and chunking begins.** These two rules look adjacent and are opposites,
so the boundary is stated here rather than left to judgement. Self-containment is a property of
_reference_: a passage must not depend on an antecedent that lives in another passage. Chunking is a
property of _structure_: cutting an argument into fragments sized for a retriever, at the cost of
the argument. The test is what happens to a human reader. If removing the dependency on the previous
paragraph also makes the text read better to a person, that is self-containment and it is required.
If a section was split, a heading invented, or a thought truncated so that a machine would find it
more conveniently, that is chunking and it is forbidden. A passage may be a thousand words long and
still be self-contained; length is not the variable.

What is rejected:

- **`llms.txt`.** 97 % of these files were never requested even once over a month, across 137 K
  domains. Google's position: it neither helps nor hurts. Generating one is permitted; treating it
  as a metric is not.
- **Splitting content into bite-sized chunks for LLMs.** Explicitly criticised by Google on
  2026-01-08.
- **Special schema for AI.** No such thing exists, and facts present in markup but absent from the
  visible text carry cloaking risk.

→ `EVIDENCE.md#e01-geo-answer-engines`, `EVIDENCE.md#e10-eeat-entities-schema`, `EVIDENCE.md#e13-policy-and-risk`

---

## P13. A page's unique value is mandatory and must be named

A page must not be published unless the `unique_value_source` field is populated, stating exactly how
this material differs from what already ranks. Permitted values are concrete: our own data, our own
measurement or test, an interview, a calculation performed by a named method, an analysis of a
primary source nobody has read, our own media.

Not permitted: "more detailed", "better structured", "fresher", with no statement of what actually
changed.

Honest limitation: **true information gain cannot be computed.** Patent US11354342B2 measures gain
relative to documents already shown to **one specific user within a session**; we hold no reading
history. Everything sold under that name is a proxy for "difference from the top 10". We use that
proxy and we call it by its real name. → `EVIDENCE.md#e11-content-quality-signals`

---

## P14. Programmatic generation is permitted only on top of real data

Mass generation of same-shaped pages is admissible if **each page carries a unique record from a
real database**. A template with a variable substituted into the prose is a doorway.

The survivors in this genre (Zapier, Wise, Airbnb, Canva) hold genuine data on the page; the
casualties substituted words into a template. → `EVIDENCE.md#e13-policy-and-risk`

---

## P15. Negative results are recorded on equal footing with positive ones

A hypothesis that failed to hold, and a rule that had to be withdrawn, are recorded in
`doctrine/CHANGELOG.md` with the date and the data. This is the only way to avoid walking in circles,
and the only thing that makes a public repository more valuable than a vendor blog.

---

## Appendix: what must never be built into Kiln

| Prohibition                                                  | Reason                                                                        |
| ------------------------------------------------------------ | ----------------------------------------------------------------------------- |
| An external AI detector as a condition of publication        | P3                                                                            |
| A "humaniser" service                                        | P3, snake oil                                                                 |
| Optimising for perplexity or burstiness to defeat a detector | P3, detectors no longer work that way                                         |
| A target word count as a requirement placed on the text      | P13, named by Google directly as a signal of unreliable content               |
| Splitting text into chunks for LLMs                          | P12, criticised by Google on 2026-01-08                                       |
| `llms.txt` treated as a metric                               | P12, 97 % are never requested                                                 |
| Automated internal linking on a cosine threshold alone       | P7, `anchorMismatchDemotion`                                                  |
| Self-promoting listicles ("10 best", with us at number one)  | P0, the whole domain falls, not just the page                                 |
| Automatic amendment of doctrine rules                        | P10                                                                           |
| An "written by AI" disclaimer used in place of human review  | P11, it grants no exemption under the EU AI Act; only substantive review does |
