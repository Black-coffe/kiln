# Open Questions

**Version:** 0.1.0 · **Compiled:** 2026-08-07 · **Review:** every 30 days until the pilot ships

Every unresolved question in the doctrine, gathered from the "Conflicts with the principles" section
of each file into one register. Ordered by **what it costs if it stays unanswered**, not by how
interesting it is.

Kiln's own rule is that a body of rules without counters diverges from itself and does not report it
(P8). The same applies to its gaps. A doctrine that hides its open questions in fourteen separate
closing sections is hiding them.

**Severity meanings.** `CRITICAL` — irreversible damage, legal exposure, or a dated deadline.
`HIGH` — silently produces wrong results. `MEDIUM` — degrades quality or wastes effort.
`LOW` — untidy, worth closing eventually.

**Who can answer.** `OWNER` — a decision, not a fact. `PILOT` — data that only the first run
produces. `LEGAL` — outside counsel; no research agent will settle it. `EXTERNAL` — a third party
controls the answer. `ENGINEERING` — resolvable by building or measuring something.

---

## Q1 · Extraterritoriality of EU AI Act Article 50 · `CRITICAL` · `LEGAL`

**Question.** Article 50 has applied since 2026-08-02. It is unresolved how its obligations attach
when publishing from outside the EU to an audience that includes EU residents. The pilot is a
Ukrainian financial marketplace, which is exactly the ambiguous case.

**Touches.** `00-principles.md` P11 · `06-review-lenses.md` §6, closing item 5 ·
`10-safety-gates.md` §9, §17.6 · `01-onboarding-grill.md` (`public_interest` field)

**Blocked by.** A legal question, not a research question. Every intel report that touched it said
so explicitly.

**Exposure.** Up to €15M or 3% of turnover. The doctrine's mitigation — logging substantive human
review to claim the exemption — is built and correct, but whether the exemption is even needed here
is the unanswered part.

**Do meanwhile.** Keep logging as though Art. 50 applies. The log costs little and is independently
justified by E-E-A-T and by `contentEffort`. Do not scale to a second EU-facing project before this
is answered.

---

## Q2 · Cloudflare's default AI-crawler policy lands 2026-09-15 · `CRITICAL` · `EXTERNAL`

**Question.** From 2026-09-15 Cloudflare blocks "mixed" AI crawlers by default on pages carrying
advertising. None of the three candidate projects has been checked against it.

**Touches.** `09-geo.md` §14.6, `GEO-01`–`GEO-06` · `01-onboarding-grill.md` (`ONB-10`, `ONB-11`)

**Blocked by.** Nothing. This is a five-minute check per domain that nobody has run.

**Why it ranks here.** It is dated, it is external, and the failure is silent: citation visibility
disappears with no error anywhere. The gates in `09-geo.md` re-run bot access on a schedule and would
eventually catch it, but "eventually" is after the damage.

**Do now.** Check all three domains before 2026-09-15, not after. Record the result in the project
profile.

---

## Q3 · No lemmatizer chosen for Ukrainian · `CRITICAL` · `ENGINEERING`

**Question.** The one-anchor-one-URL invariant (P6, `LNK-16`) requires normalised anchor phrases.
Ukrainian is inflected, so without lemmatization «кредит онлайн» and «кредиту онлайн» never collide.
No lemmatizer has been selected. `pymorphy3`, Stanza and UDPipe are named as unevaluated candidates.

**Touches.** `07-linking.md` §1.3, `LNK-16`, `LNK-17` · `doctrine/lang/uk.md` §11-6 ·
`02-semantics.md` `SEM-20`

**Blocked by.** Evaluation work nobody has done.

**Why this is the worst kind of gap.** The invariant does not fail loudly. It **reports clean and
guarantees nothing**, on the pilot's primary locale, on the exact mechanism that is supposed to
prevent cannibalization. A silent pass is worse than a failure, because it consumes the trust a
failure would have earned back.

**Do now.** Evaluate the three candidates against a sample of the pilot's own anchors before the
first linking wave. Until one is chosen, treat every "no anchor conflicts" result on `uk` as
unverified rather than as a pass.

---

## Q4 · The pre-AI Ukrainian baseline is destroyed by the first refresh · `CRITICAL` · `PILOT`

**Question.** The reference pilot holds 186 wiki pages dated 2021 and 776 news items ending 2024-03-07:
human-written Ukrainian in the target niche, produced before mass AI content. This is the only
available calibration baseline for the Ukrainian language pack, where 118 of 124 entries are
hypotheses. Once Kiln refreshes those pages, it is gone.

**Touches.** `doctrine/lang/uk.md` §8.1 · `04-trends-and-plan.md` (`REFRESH` route) ·
`11-self-learning.md` (calibration)

**Blocked by.** Nothing. It is a snapshot.

**Why it ranks here.** Irreversibility. Every other item on this list can be answered later at
greater cost; this one cannot be answered at all once the corpus is rewritten, and the refresh queue
will reach those pages early precisely because they are the stalest thing on the site.

**Do now.** Freeze an immutable snapshot before any refresh runs. This is the cheapest item in the
register and the only one with a hard, self-inflicted deadline.

---

## Q5 · The review ring covers one absence, not two · `HIGH` · `OWNER` + `PILOT`

**Status.** Resolved with a caveat, 2026-08-07. Each lens now has a named backup forming a ring
(`REV-B1`), capacity during substitution is roughly halved and the arithmetic is stated, substitution
reviews are excluded from rule statistics but still count for AI Act and `HTPI_true`, and a backup
may not cover a second lens on a draft they already reviewed (`REV-B2`).

**What remains open.** There are four people for four lenses, so the ring is a permutation of the
same staff. It covers **one** absence. Two adjacent absences, or one absence during a busy week,
returns the line to zero. The ring has never met a holiday season, an illness or a launch.

The domain lens is the weakest link by construction: its expertise is the least transferable, and on
YMYL an unqualified backup is not a backup at all but a broken AI Act exemption.

**Touches.** `06-review-lenses.md` §9.1 · `10-safety-gates.md` §17.2, K6 · `00-principles.md` P2

**Do meanwhile.** Track the substituted share of reviews from week one. A rising share is the
leading indicator of the ring failing, and it arrives well before throughput collapses.

---

## Q6 · Wave throughput against a 4,000-URL corpus · `HIGH` · `PILOT`

**Question.** `LNK-14` caps a wave at 10% of the site and §9 requires 4–12 weeks before measuring,
giving a full cycle in twelve to eighteen months. `SEM-25` now permits parallel waves across clusters
that do not share a `pillar_id`, which recovers throughput — but only if the corpus actually
decomposes that way.

**Touches.** `07-linking.md` §14.3, `LNK-14` · `02-semantics.md` §9.3, `SEM-25`

**Blocked by.** `pillar_id` has never been populated, so nobody knows the shape of the pilot's
cluster graph.

**The risk.** If most clusters hang off a few pillars, the independence constraint bites, parallelism
mostly disappears, and we are back to a year-plus cycle on the project chosen specifically for fast
feedback.

**Do now.** Populate `pillar_id` and count the distinct pillar groups **before** planning wave one.
That number decides whether the linking programme is feasible as designed.

---

## Q7 · Cross-vendor judge separation is not achievable in-plugin · `HIGH` · `ENGINEERING`

**Question.** `WRT-R4` requires the QA judge to run on a different model family from the writer.
Plugin-defined agents can only select Claude models, so the requirement degrades to Opus-judging-
Sonnet: different sizes, one family, shared blind spots.

**Touches.** `05-writing-core.md` `WRT-R4` · `agents/kiln-judge.md`

**Blocked by.** A platform constraint, not a design choice.

**Why it matters.** The rule exists because a model endorses its own phrasing. Same-family judging
weakens exactly the check meant to catch self-endorsement, and the current arrangement satisfies the
letter of `WRT-R4` while missing its point.

**Options.** Move the judge into a layer-2 script making an external API call, which restores genuine
cross-vendor separation at the cost of another credential; or accept the degradation and record it
honestly. The judge agent currently states the limitation in its own body rather than hiding it.

---

## Q8 · Every threshold in the doctrine is uncalibrated · `HIGH` · `PILOT`

**Question.** Essentially every number in Kiln is `[expert judgement, needs calibration]`, set on
2026-08-07 with no data in existence. This includes the thresholds that decide when a _rule_ is bad
(`11-self-learning.md` §3.5) — guesses about how to evaluate guesses.

**Touches.** All eleven doctrine files, `.kiln/thresholds.yml`

**Blocked by.** Data that only running the pilot produces.

**Why it is `HIGH` and not `CRITICAL`.** It is disclosed everywhere and the architecture handles it:
thresholds are local, calibratable and never promoted into the shared doctrine without a PR. The
danger is not the numbers, it is that a number in a doctrine acquires authority regardless of its
footnote.

**Do meanwhile.** Run the first cycle in observe mode where the doctrine offers one. Collect
distributions before letting any expert-judgement threshold block anything.

---

## Q9 · Cohort sizes may never reach usability per locale · `HIGH` · `PILOT`

**Question.** The cohort monitor is the only detector for silent algorithmic penalties, since no
manual action exists for scaled content abuse. It needs roughly ten pages per cohort. P2 caps the
pilot at a handful of articles a month, and `MSR-22` now requires per-locale segmentation, dividing
an already thin sample.

**Touches.** `08-measurement.md` §14.6, §14.7, `MSR-22` · `10-safety-gates.md` `SAF-18` K1 ·
`00-principles.md` P2

**The bind.** Quarterly cohorts on the primary locale only, which is the current compromise, means
the kill switch's main trigger is least sensitive early on a small corpus — precisely when a young
domain is most vulnerable.

**Do meanwhile.** Treat K1 as a slow backstop for the first two quarters and lean on K2, K4 and K5,
which do not depend on cohort statistics.

---

## Q10 · The GEO loop cannot measure effect size yet · `MEDIUM` · `PILOT`

**Question.** Citation drift between runs is 40–60% per month. With a fixed prompt set and three
repeats, the loop reliably measures **presence and direction**, not magnitude, for at least two
quarters.

**Touches.** `09-geo.md` §14.4, §6 · `08-measurement.md` `LI-5`

**Honest position.** This is Kiln's weakest measurement and is labelled as such in its own file. Do
not let a GEO number justify a content decision on its own before the drift envelope is known.

---

## Q11 · The `platform` competitor class has no working method · `MEDIUM` · `EXTERNAL`

**Question.** Reddit sits between a free tier of 100 QPM and a commercial tier at $12,000/month,
with nothing in between, and was unreachable by every route during research. Reddit now appears in
millions of AI Overviews, so the `platform` class matters more than its tooling allows.

**Touches.** `03-competitors.md` §16, class `platform` · `04-trends-and-plan.md` (Reddit as a trend
source)

**Do meanwhile.** Treat `platform` competitors as observable only through SERP and AI-answer
citation, not through their own APIs, and say so in reports rather than leaving a silent gap.

---

## Q12 · `GEO-10` creates pressure to fabricate quotations · `MEDIUM` · `OWNER`

**Question.** A minimum count of expert quotations is a quota, and quotas applied to a generative
system produce fabricated quotes. The rule is safe only while the primary-source gate (P1) holds
absolutely.

**Touches.** `09-geo.md` §14.2, `GEO-10` · `00-principles.md` P1 · `06-review-lenses.md` lens F

**Do meanwhile.** Never let `GEO-10` reach `BLOCK` while P1 enforcement is anything less than total.
A quota that can only be satisfied by inventing evidence is a defect, not a standard.

---

## Q13 · Behavioural doctrine changes are frozen until a second project exists · `MEDIUM` · `OWNER`

**Question.** `LRN-17` requires two projects before a behavioural rule may change, so for the first
months the doctrine will look inert while evidence accumulates from one source.

**Touches.** `11-self-learning.md` §14.2, `LRN-17` · `00-principles.md` P10

**Position.** This is working as intended, not a defect. It is listed so nobody "fixes" it in month
two out of impatience. Threshold calibration continues locally throughout; only shared behavioural
rules are frozen.

---

## Q14 · P8 and P0 pull against each other on rule deletion · `MEDIUM` · `OWNER`

**Question.** P8 marks a rule overridden more often than accepted as a deletion candidate. P0 says
rejection is the point. A strict, valuable gate will be overridden often under deadline pressure and
would be deleted by its own statistics.

**Touches.** `00-principles.md` P0, P8 · `11-self-learning.md` §14.3

**Current mitigation.** A `BLOCK` rule may not be deleted on override rate alone. Whether that is
sufficient is unknown until real override data exists.

---

## Q15 · A Ukrainian YMYL hedge may be a legal requirement, not filler · `MEDIUM` · `LEGAL`

**Question.** «рекомендуємо проконсультуватися з фахівцем» is flagged as filler by analogy with
Russian, but in Ukrainian consumer finance it may be a mandated disclosure. The rule as written could
advise deleting a legally required sentence.

**Touches.** `doctrine/lang/uk.md` §11-3 · `01-onboarding-grill.md` (project disclosure list)

**Current mitigation.** Both entries held at `risk: low`, density-matched only, with the project's
onboarding disclosure list taking precedence. Correct as a default; still not an answer.

---

## Q16 · The English pack's evidence is single-vendor · `MEDIUM` · `ENGINEERING`

**Question.** The English stop-vocabulary derives from observations of one vendor's model
generations. Its under-detection rate for other families is unknown.

**Touches.** `doctrine/lang/en.md` metadata · `00-principles.md` P4

**Consequence to state in reports.** A clean pass is evidence of no _familiar_ markers, not evidence
of human authorship. The pack is capped at `WARN` for exactly this reason.

---

## Q17 · Residual items · `LOW`

| Item                                                                                                     | Touches                       | Resolve by    |
| -------------------------------------------------------------------------------------------------------- | ----------------------------- | ------------- |
| `SAF-04` Level C programmatic thresholds should be deleted if the pilot never runs programmatic pages    | `10-safety-gates.md` §17.4    | `OWNER`       |
| `MSR-13` promises device coefficients; no device table is supplied                                       | `08-measurement.md`           | `ENGINEERING` |
| DataForSEO `competitors_domain` unit price disagrees between the vendor page and third-party summaries   | `03-competitors.md` `CMP-24`  | `ENGINEERING` |
| Pair survival rate after the embedding pre-filter is unmeasured, so graph size is a guess                | `02-semantics.md` §4.3        | `PILOT`       |
| CTR modifiers other than AIO are pure judgement                                                          | `02-semantics.md` §14.2       | `PILOT`       |
| Legal review of scraping covers US precedent only; EU and Ukraine unexamined                             | `03-competitors.md` §16       | `LEGAL`       |
| `REV-27`…`REV-30` deliberately duplicate machine metrics as an arbitration measure                       | `06-review-lenses.md` item 1  | `PILOT`       |
| Requiring non-empty `substantive_changes` may produce cosmetic edits for the sake of the field           | `06-review-lenses.md` item 2  | `PILOT`       |
| The four-lens regime's endurance is an agreement, not a measurement; the only precedent is negative      | `06-review-lenses.md` item 3  | `PILOT`       |
| Verification metrics for a doctrine change are chosen by the party proposing it                          | `11-self-learning.md` §14.4   | `OWNER`       |
| Fast-loop signals come from four people who know each other, so independence is social as well as formal | `11-self-learning.md` §14.6   | `PILOT`       |
| Section topical radii are not yet calibrated; `SAF-09` records `INFO` until they are                     | `10-safety-gates.md` `SAF-09` | `PILOT`       |
| The reference pilot's pre-hiatus Search Console history describes a different site and cannot calibrate CTR      | `08-measurement.md` §10       | `PILOT`       |

---

## How to use this register

1. Nothing here is a reason to delay the pilot. Q2, Q3, Q4 and Q6 are cheap and should be closed in
   the first week; the rest are answered by running the thing.
2. When an item closes, move it to `CHANGELOG.md` with the evidence, including the ones that closed
   badly. Negative results carry equal weight (P15).
3. New conflicts found in any doctrine file are added here at the same time they are added to that
   file's closing section. A register that is only compiled once is a snapshot, not a register.
4. This file is reviewed every 30 days until the pilot ships, then every 90 with the doctrine.
