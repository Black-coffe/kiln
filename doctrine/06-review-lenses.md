# 06 — Review Through Four Lenses

> Subordinate to `00-principles.md`. Implements **P11** (a human is mandatory), **P8** (we measure
> the rules, not only the pages), **P2** (pace equals verification capacity), **P9** (the fast
> learning loop). Any conflict with the principles resolves in favour of the principles.

**Version:** 0.1.0 · **Date:** 2026-08-07 · **Revision:** mandatory after the first 30 reviewed drafts

---

## 0. Scope

This section governs the last barrier before publication: **how a human looks at a draft, what
exactly they look at, in how much time, what they leave behind, and how the doctrine learns from it.**

It does not describe machine checks. Those live in `05-writing-core.md` and `10-safety-gates.md`.
Here the point is the opposite: the machine has already run, and the human **must not repeat its work**.

### 0.1 Language of review

Review is always performed in the language of the content, never in the language of the doctrine.
The doctrine is written in English; the drafts are not. A reviewer assigned to a locale must be
fluent in that locale's language. This matters most for the voice lens, which is meaningless
otherwise: judging whether a Ukrainian text reads like a living person requires a native reader of
Ukrainian, and no amount of doctrine compensates for its absence.

The checklist questions below are written in English and may be presented to reviewers translated
into their working language. Rule IDs and verdicts are always logged in their canonical English
form, so that statistics remain comparable across locales and projects.

---

## 1. Why lenses instead of a shared read

### 1.1 The arithmetic of coverage

Four people reading the same text with the instruction "have a look, is this alright" are asking
the same question four times. They find one class of defect, the most visible one, and then
disagree about taste. Four people asking different questions find four classes of defect.

This is not a metaphor. It follows directly from how failures are shaped. A broken number, a wrong
conclusion drawn from a correct number, dead prose, and a page nobody needs are four different
failures, and each is visible from a different position. A fact-checker will not catch a wrong
conclusion drawn from a correct source: they have no domain frame. A domain expert will not notice
that the text reads like a machine: they are reading the content, not the form.

### 1.2 The precedent that settles the argument

The owner's existing system records this verbatim: **"The weekly calendar didn't survive contact.
It ran for one week and stopped. This is the most important thing on this page."** (`[internal observation, unpublished]`
§5.12). That is a negative result for the "everyone does everything, every week" mode, obtained on
a real project rather than read in a blog post.

A mode that requires four people to perform the same full read is the most expensive one available
and the first to break under load. Splitting into lenses reduces each person's cost of
participation to a single zone and turns one person dropping out into a local failure rather than a
systemic one (§9).

### 1.3 The second effect: disagreements become data

Under a shared read, a disagreement between two reviewers is an argument settled by whoever is more
senior. Under lenses, a disagreement can only occur where two zones overlap and a rule is worded
ambiguously. Such a disagreement is **not an argument but a doctrine defect** (P8), and it enters
the amendment queue automatically (§7).

The mechanism is borrowed from the editorial pattern of double scoring: a role scores itself, the
consuming role scores it again, and the gap feeds rubric retuning (`EVIDENCE.md#e14-content-operations` §3.2). We apply it to
people rather than to agents, because here the people are the last loop.

### 1.4 No averaging

Lens verdicts **are not summed and not averaged**. A failure from one lens is not offset by three
passes. Stated directly in the owner's system: _"A brand-voice PASS combined with an audience-fit
FAIL … must not hide behind the average"_ (`[internal observation, unpublished]` §5.6).

Scoring on a scale is forbidden for the same reason it is forbidden for LLM judges: scales drift,
and an average conceals a failure (`EVIDENCE.md#e11-content-quality-signals` §7). Every check below is a question with a binary
answer.

---

## 2. Procedure

```
[draft ready]
      │
      ▼
① MACHINE PRE-GATE   ── any BLOCKER ──► returned to the writer, no human is called
      │  (05-writing-core criteria; safety criteria from 10-safety-gates)
      │  passed
      ▼
② PACK ASSEMBLY      review_pack.py × 4 → .kiln/reviews/<slug>/pack-{facts,domain,voice,utility}.md
      │
      ▼
③ FOUR LENSES IN PARALLEL, independently, each seeing only its own pack
      │   facts │ domain │ voice │ utility
      │
      ├── any BLOCKER ─────────────────────► rework request (§8), loop back to ②
      ├── HIGH only ───────────────────────► rework request, only the affected lenses re-run
      │
      ▼ all four pass
④ RECONCILIATION     review_stats.py: disagreements → doctrine amendment queue (§7)
      │
      ▼
⑤ FINAL APPROVAL     owner or designated responsible editor. Signature into the log.
      │
      ▼
⑥ LOG                .kiln/reviews/<slug>.yml is committed alongside the article. No log, no publish.
```

**Procedure invariants:**

- Lenses run **in parallel and blind to each other**. A reviewer does not see the other verdicts
  until ⑤. Otherwise the first verdict anchors the rest, and we lose precisely the disagreements
  the whole design exists to surface.
- A human is **never called on a draft that failed the machine pre-gate**. Human time is the most
  expensive resource in the system (P2); spending it on what a regular expression catches is
  forbidden.
- The order ① → ③ is irreversible. The machine does not "supplement" the human afterwards, it
  filters beforehand.
- Final approval (⑤) is separate from the lenses and cannot be performed by someone who reviewed
  a lens on the same draft. Grounds: the owner's system already states this as a distinct gate,
  _"Founder review of copy is a SEPARATE pre-ship gate, distinct from code review"_ (`[internal observation, unpublished]` §1.1).

---

## 3. The four checklists

**Severity:**

| Level     | Meaning                                                                                                             |
| --------- | ------------------------------------------------------------------------------------------------------------------- |
| `BLOCKER` | Publication is impossible. The draft is returned. Override only by an explicit owner decision, recorded in the log. |
| `HIGH`    | Returned for rework. Publishable once fixed; only this lens re-checks.                                              |
| `NOTE`    | Recorded as debt in `.kiln/corpus.json`. Does not stop publication.                                                 |

Every question is worded so that **"I don't know" counts as "no"**. This is the defence against a
gate that is satisfied by a filled-in field and therefore rewards silence.

Severity notation: `HIGH → BLOCKER (YMYL)` means HIGH normally and BLOCKER on YMYL topics;
`BLOCKER (YMYL)` means the rule blocks on YMYL topics.

**Why this ladder differs from the doctrine's, and how it maps.** `00-principles.md` defines
`BLOCK` / `WARN` / `INFO` for machine-enforced gates. These three levels are for **human verdicts**,
which need a distinction machines do not: who may override, and who re-checks afterwards. The two
scales are deliberately separate and the mapping is fixed, so no script has to guess:

| Review verdict | Doctrine severity | Distinction the review scale adds                                   |
| -------------- | ----------------- | ------------------------------------------------------------------- |
| `BLOCKER`      | `BLOCK`           | override requires an explicit owner decision, recorded              |
| `HIGH`         | `BLOCK`           | clears on rework; only the originating lens re-checks, not all four |
| `NOTE`         | `WARN`            | proceeds, carried as debt in `.kiln/corpus.json`                    |

`review_stats.py` emits doctrine severities, not review verdicts, so counters stay comparable with
every other rule in the corpus. No third ladder exists anywhere in Kiln.

---

### 3.1 Lens F — facts and figures (`REV-01`…`REV-12`)

**Applies to:** every draft. On YMYL the regime tightens, as marked in the severity column.

**What the human does NOT do:** check that links are alive (machine), compute the share of primary
sources (machine), look for date inconsistencies (machine). What lands on their desk is a list of
claims with their sources already attached.

| ID       | Question ("yes" = pass)                                                                                       | Severity              |
| -------- | ------------------------------------------------------------------------------------------------------------- | --------------------- |
| `REV-01` | Did I find every number in the text inside the attached source, with my own eyes?                             | BLOCKER               |
| `REV-02` | Is each number's source the party that produces the number, rather than someone repeating it?                 | HIGH → BLOCKER (YMYL) |
| `REV-03` | Does every source carry a date, and do I agree the number is not stale as of today?                           | BLOCKER               |
| `REV-04` | Is every claim free of reliance on "the model knows this" without external confirmation?                      | BLOCKER               |
| `REV-05` | Are all quotes from people and organisations verbatim, and did I find them in the source rather than a recap? | BLOCKER               |
| `REV-06` | Is the text free of anonymous attributions such as "studies show", "experts believe", "analysts report"?      | HIGH                  |
| `REV-07` | Are the numbers presented as ours genuinely ours, and do I know exactly where each came from?                 | BLOCKER               |
| `REV-08` | Are our own numbers free of suspicious roundness, reported as the source produced them?                       | HIGH                  |
| `REV-09` | Is every metric, testimonial, customer count, rating and growth figure real rather than invented?             | BLOCKER               |
| `REV-10` | Do screenshots and interface descriptions match what the product shows **today**?                             | HIGH                  |
| `REV-11` | Do units, currencies, and the tax and legal context match the market we are writing for?                      | HIGH → BLOCKER (YMYL) |
| `REV-12` | If a number changes next month, does the text make clear which date it was true on?                           | HIGH                  |

**Grounds.** `REV-03` and `REV-04` port the freshness gate from the owner's system verbatim: _"The
model's training data may be 6–12 months stale; an external fact … could have changed yesterday"_,
severity BLOCKER, "A wrong competitor price or a dead link is a NO-GO" (`[internal observation, unpublished]` §2.14). `REV-09`
is the zero-fabrication policy from the same source (§2.9). `REV-06` is its ban on vague source
attribution (§2.9, §5.5). `REV-08` comes from its specification of a real case study: unrounded
numbers (`[internal observation, unpublished]` §2.9, §5.3).

---

### 3.2 Lens D — domain expertise (`REV-13`…`REV-22`)

**Applies to:** every draft. On YMYL the reviewer of this lens must hold **verifiable domain
qualification**. That is the EU AI Act requirement for "natural persons possessing relevant
knowledge and professional judgement" (`EVIDENCE.md#e10-eeat-entities-schema` §7), and it also satisfies the page-level trust
signal catalogued as `EVIDENCE.md#e10-eeat-entities-schema P13`.

> **Citation convention, doctrine-wide.** A bare `P<number>` always means a principle in
> `00-principles.md` and nothing else. Identifiers that happen to share that shape but originate in a
> research report are always written with their source prefix, as `EVIDENCE.md#e10-eeat-entities-schema P13` above. The two are
> unrelated: `EVIDENCE.md#e10-eeat-entities-schema P13` is a trust signal, principle **P13** governs unique value.

**What the human does NOT do:** re-check numbers (that is lens F), assess style (lens V). They have
exactly one question: **is the conclusion drawn from correct data itself correct?**

| ID       | Question ("yes" = pass)                                                                         | Severity              |
| -------- | ----------------------------------------------------------------------------------------------- | --------------------- |
| `REV-13` | Does the conclusion follow logically from the data presented, rather than merely sit beside it? | BLOCKER               |
| `REV-14` | Are cause and correlation kept distinct?                                                        | BLOCKER               |
| `REV-15` | Is the text free of simplifications that would cost the reader money or lead them into error?   | HIGH → BLOCKER (YMYL) |
| `REV-16` | Are the conditions under which the advice does not hold stated explicitly?                      | HIGH                  |
| `REV-17` | Does the terminology match this market's professional norm rather than a calque from English?   | HIGH                  |
| `REV-18` | Are all material exceptions, caveats and limits a practitioner would know actually present?     | HIGH                  |
| `REV-19` | If a procedure is described, is it executable in reality and in the order given?                | BLOCKER               |
| `REV-20` | Is the regulatory and legal context described correctly as of today?                            | BLOCKER (YMYL)        |
| `REV-21` | Is the text free of claims about products, services or releases that do not yet exist?          | BLOCKER               |
| `REV-22` | Am I willing to put my own name on this text on an author page?                                 | BLOCKER (YMYL)        |

**Grounds.** This lens covers item 2 on the list of things that cannot be automated: _"checking
that a source exists is not checking that the conclusion drawn from it is correct"_ (`EVIDENCE.md#e11-content-quality-signals` §8).
`REV-21` is red flag no. 9 from Google's official list (`EVIDENCE.md#e11-content-quality-signals` §3.1). `REV-22` operationalises
`isAuthor`/`ProfilePage` and Google's requirement to name real human authors (`EVIDENCE.md#e10-eeat-entities-schema` §3, §7).

---

### 3.3 Lens V — voice and humanity (`REV-23`…`REV-34`)

**Applies to:** every draft.

**What the human does NOT do:** count sentence lengths, stop-word density, n-gram overlap or
anaphora at section openings. All of that is already computed by the machine and sits in the pack as
reference material. Their question is: **does this read as if written by a living person who knows
the subject?**

The three axes of questioning come from the only study that measured human ability to distinguish
machine text (87.6% across nine languages): **concreteness, cultural nuance, diversity**
(`EVIDENCE.md#e03-ai-detection-and-humanization`, arXiv:2502.11614). This is also P4.

| ID       | Question ("yes" = pass)                                                                                           | Severity |
| -------- | ----------------------------------------------------------------------------------------------------------------- | -------- |
| `REV-23` | Does the text contain details obtainable only by dealing with the subject in person?                              | BLOCKER  |
| `REV-24` | Are the examples concrete, with names, numbers and circumstances, rather than "one company once"?                 | HIGH     |
| `REV-25` | Does the text state somewhere what failed, what proved harder than expected, or what we do not know?              | HIGH     |
| `REV-26` | Does the text disagree with received opinion anywhere, and explain why?                                           | NOTE     |
| `REV-27` | Is the rhythm uneven, mixing short clipped sentences with long ones?                                              | HIGH     |
| `REV-28` | Is the text free of the symmetry of "exactly three points, exactly three examples, three sections of equal size"? | HIGH     |
| `REV-29` | Is the text free of meta-commentary about what the author is about to do ("let's examine", "below I will cover")? | HIGH     |
| `REV-30` | Does the text avoid ending in a formal summary that restates what was already said?                               | HIGH     |
| `REV-31` | Do the local references, the address to the reader and the register match this market rather than a translation?  | HIGH     |
| `REV-32` | Reading three random paragraphs aloud, do I hear something other than a press release?                            | HIGH     |
| `REV-33` | Is every paragraph load-bearing, none removable without loss of meaning?                                          | HIGH     |
| `REV-34` | Do I recognise our publication's voice here, rather than the generic voice of "a useful article"?                 | HIGH     |

**An important limit on this lens.** `REV-27`, `REV-28`, `REV-29` and `REV-30` are partly computed
by the machine. The human here is **an arbiter on contested cases, not a counter**. Where machine
and human disagree, that disagreement goes to §7: most likely a threshold in the language pack is
set wrong.

**What this lens will never contain.** No question asks about passing an AI detector, about
perplexity, or about dash density. The first is forbidden by P3; the second is dead (2026 detectors
do not rely on perplexity, arXiv:2602.05769); the third breaks Cyrillic and lives only in
`doctrine/lang/en.md` (P5).

---

### 3.4 Lens U — reader usefulness and product truth (`REV-35`…`REV-46`)

**Applies to:** every draft. This is the only lens entitled to say "this page should not exist".

**What the human does NOT do:** check entity coverage or cannibalization (machine), measure
time-to-answer (machine).

| ID       | Question ("yes" = pass)                                                                                               | Severity |
| -------- | --------------------------------------------------------------------------------------------------------------------- | -------- |
| `REV-35` | Does a living reader need this page, not just a search engine?                                                        | BLOCKER  |
| `REV-36` | Would cloning this page with the same prompt take a competitor materially more than an hour?                          | BLOCKER  |
| `REV-37` | Would I show a public list of our pages of this type without wincing?                                                 | BLOCKER  |
| `REV-38` | After reading, can the reader do what they came to do without going off to search further?                            | BLOCKER  |
| `REV-39` | Does the headline promise exactly what the text delivers?                                                             | BLOCKER  |
| `REV-40` | If this is a comparison or a review, does it name the cases where a rival product is better than ours?                | BLOCKER  |
| `REV-41` | Are our product's limitations stated, including who should not buy it?                                                | HIGH     |
| `REV-42` | Are prices and terms stated plainly rather than hidden behind "contact us"?                                           | HIGH     |
| `REV-43` | Is the unique value declared in the brief (`unique_value_source`) actually present in the text?                       | BLOCKER  |
| `REV-44` | Is the page consistent with already published material in the same cluster, neither contradicting nor duplicating it? | HIGH     |
| `REV-45` | Is every project taboo from `.kiln/project.yml` respected?                                                            | BLOCKER  |
| `REV-46` | Is this something other than a self-promoting listicle where we rank ourselves first?                                 | BLOCKER  |

**Grounds.** `REV-35` through `REV-37` are Lily Ray's three gate questions, taken as written and
converted into blocking checks (`EVIDENCE.md#e14-content-operations` §2). `REV-38` operationalises `lastLongestClicks`: did
the page close the task well enough that the person stopped searching (`EVIDENCE.md#e11-content-quality-signals` §4.2). `REV-40`
and `REV-41` are Competitor Acknowledgment and Honest Limitations, taken from a production system
where the pattern is a disqualifying paragraph naming a threshold below which the reader should use
a free alternative instead of buying (`[internal observation, unpublished]`). That is also
the strongest available anti-AI signal, because a model will not by default write against the
product it is selling. `REV-44` ports the "compare against cluster siblings" rule (`[internal observation, unpublished]` §5.7).
`REV-46` targets the anti-pattern that the January 2026 update punished by 40–95% of traffic and,
more importantly, punished at **whole-domain** level rather than per page (`EVIDENCE.md#e14-content-operations` §2).

**Why `REV-43` is checked on substance.** The `unique_value_source` field is filled in at the brief
stage. A gate that merely checks the field is non-empty is useless and actively harmful: it rewards
writing anything at all. So the check is worded as "is what was promised in the field actually
present in the text", and a human performs it. The machine's contribution is a proxy (`EVIDENCE.md#e11-content-quality-signals`
§7) that only establishes that the text contains something absent from the top ten; it cannot know
whether that something is what we promised.

---

## 4. What the reviewer sees: pack structure

`review_pack.py` (§11.1) assembles the pack and writes it to `.kiln/reviews/<slug>/pack-<lens>.md`.
The pack is **different for each lens** and contains only what that lens needs.

### 4.1 Shared header (identical in all four)

```
ARTICLE:  <headline>
SLUG:     <slug>          LOCALE: uk      YMYL: yes
CLUSTER:  <cluster>       TYPE:   comparison
BRIEF:    .kiln/briefs/<slug>.yml  ← promised unique value: "<one line>"

THE MACHINE ALREADY CHECKED THIS AND IT PASSED — do not re-check:
  ✓ all 14 external links alive           ✓ 8-gram overlap with top 10: 0.014
  ✓ share of primary sources: 0.62        ✓ date consistency: 11 days
  ✓ entity coverage: 0.78                 ✓ proximity to existing pages: 0.71
  ✓ anaphora at section openings: 0       ✓ time to answer: 41 words

YOUR LENS: <name>. Questions: N. The other lenses are running in parallel;
you will see their verdicts only after reconciliation.
```

The "machine already checked" block exists precisely so that the human spends no time on what is
re-checkable. It is a direct saving against their budget (§5).

### 4.2 Lens F

- A table of **claims** extracted from the text: `claim → number → source (clickable) → source date
→ verification date → flag "primary / secondhand"`.
- A separate block of **claims with no source**, flagged as our own, each with the "where this came
  from" field taken from the brief. This is where `REV-07` operates.
- A separate block of **claims where the machine found no source at all**. Their presence means the
  machine pre-gate failed, so this pack should never have reached a human; the block is kept as
  insurance against a manual gate override.
- Links to **local source snapshots**, not only to live URLs: a live URL can change between review
  and publication.

### 4.3 Lens D

- **Text only.** No markup, no SEO fields, no metrics. A domain expert must read the content, not
  the interface.
- A separate list of **conclusions and recommendations** extracted from the text, so that the
  logical transitions are visible without reading through all the prose.
- The **intended audience** field from the brief: advice that is correct for one audience can be
  harmful to another.
- On YMYL, a block of the project's **regulatory requirements** from `.kiln/project.yml` (licences,
  mandatory disclosures, prohibited promises).

### 4.4 Lens V

- **The full text in readable layout**, as close as possible to how the reader will see it.
- Machine metrics presented **as reference, not as verdict**: sentence length distribution, language
  pack stop-phrases found, share of passive constructions. Explicitly captioned: _"this is a hint,
  not a ruling; the final call on `REV-27`…`REV-30` is yours"_.
- **Three random paragraphs pulled out separately**, so `REV-32` can be tested aloud without
  reading everything.
- A link to a **reference piece** of this type from the corpus, if one exists (`REV-34`).

### 4.5 Lens U

- The text plus the **target query and intent** from the brief.
- **The top five SERP results for the target query**, as collapsed cards: headline, what it gives,
  what it withholds. Without this, `REV-36` ("would a competitor clone it") becomes guesswork.
- **A list of already published cluster material**, one line each (`REV-44`).
- **Project taboos** from `.kiln/project.yml`, spelled out in full (`REV-45`).
- The promised unique value from the brief, prominently (`REV-43`).

### 4.6 On the time allowance

Each pack carries an `expected time: N min` field. The number comes from `.kiln/thresholds.yml` and
**at the outset is an assumption, not a norm**; see §5.2. It is shown to the reviewer as a bearing,
not a limit, and actual time is logged separately regardless.

---

## 5. Time budget and the publication ceiling

### 5.1 The ceiling formula

The classic mistake is dividing total hours by total minutes. Lenses **are not interchangeable**: a
domain expert cannot close the voice lens, and a fact-checker will not become a domain expert. So
the ceiling is set not by the sum but by **the narrowest lens**.

```
capacity = min over lenses L of  ( H_L × 60 ) / ( t_L × (1 + r_L) )

where
  H_L — hours per week available to the reviewer of lens L
  t_L — minutes per draft on lens L
  r_L — expected share of repeat passes on that lens (the rework rate)

publish_cap_per_week = floor( capacity )
```

The `(1 + r_L)` multiplier is mandatory: a rework costs the lens almost as much as the first pass,
and without it the ceiling is systematically overstated.

The resulting number is written to `.kiln/project.yml` as `publish_cap_per_week` and is a **hard
constraint** (P2). It is not raised "because it's going quickly"; it is recalculated only after
`t_L` and `r_L` have been recalculated from actual logs.

### 5.2 Starting values are an assumption, not a norm

**No reliable data on per-stage timings exists.** The research states this outright: every
distribution found was either aggregated or vendor-published, and there are no primary measurements
(`EVIDENCE.md#e14-content-operations` §11). The only thing known above vendor-level confidence is the ratio between stages,
not their absolute duration: writing is 15–20% of the cycle, research 25–35%, review and rework
20–25% (`EVIDENCE.md#e14-content-operations` §3.2, evidence level C: the shape of the process, not a measured quantity).

Starting `t_L` values are therefore **a hypothesis to be measured over the first 30 drafts**, and
they are marked as such in `thresholds.yml`:

| Lens    | `t_L` start | `r_L` start | Status                              |
| ------- | ----------- | ----------- | ----------------------------------- |
| facts   | —           | —           | measure, `source: measure_on_pilot` |
| domain  | —           | —           | measure, `source: measure_on_pilot` |
| voice   | —           | —           | measure, `source: measure_on_pilot` |
| utility | —           | —           | measure, `source: measure_on_pilot` |

**Calibration procedure.** For the first two weeks, `publish_cap_per_week` is taken conservatively
from agreement with the team rather than from the formula. Every review log records actual time.
After 30 records, `review_stats.py` computes the median and the 80th percentile per lens; the
formula consumes **the 80th percentile, not the median**, because the ceiling has to survive a bad
week, not an average one. From that point the formula takes effect.

### 5.3 What to do when the ceiling is lower than you wanted

There are three legitimate ways out and one illegitimate one.

Legitimate: cut `t_L` using the machine (move a check out of the lens and into the pre-gate, the
cheapest path); increase `H_L` on the narrow lens; reduce `r_L` by fixing the cause of reworks,
which usually sits in the brief (§8.3).

Illegitimate: raising `publish_cap_per_week` by hand. That is a direct violation of P2, and it is
exactly the step reproduced in the "6–12 months of growth → peak → collapse below baseline"
trajectory (`EVIDENCE.md#e14-content-operations` §2).

---

## 6. The review log

The log is **a mandatory field, not an option** (P11). A draft without a complete log is not
published. The log is committed to the repository alongside the article.

### 6.1 Why this way: three jobs, one subsystem

1. **EU AI Act, Art. 50, in force since 2026-08-02.** Text published to inform the public on matters
   of public interest is subject to labelling. **Human review or editorial control grants
   exemption**, but only as defined: "deliberate examination of the substance of the content by one
   or more natural persons possessing relevant knowledge and professional judgement". Superficial
   spelling-level checks do not count, and a footer or general terms are insufficient (`EVIDENCE.md#e10-eeat-entities-schema`
   §7). So what must be logged is **substantive intervention**, not the fact that a button was
   pressed. Penalties run to EUR 15M or 3% of turnover.
2. **An E-E-A-T artifact.** The log supplies material for author pages and `ProfilePage`, and binds
   a real qualified person to a specific piece: the direct analogue of `isAuthor`/`authorName` from
   the Content Warehouse leak (`EVIDENCE.md#e10-eeat-entities-schema` §3).
3. **Machine estimation of effort.** `contentEffort` is described as "LLM-based effort estimation
   for article pages", and under the dominant reading its criterion is ease of reproduction
   (`EVIDENCE.md#e11-content-quality-signals` §2.2). Substantive expert edits are exactly what cannot be reproduced.

The overlap between "YMYL under Google" and "matters of public interest under the AI Act" is large,
especially after YMYL was extended to Government/Civics/Society in the QRG revision of 2025-09-11.
Hence the rule: **a topic falls under YMYL → the editorial loop with logging is mandatory**
(`EVIDENCE.md#e10-eeat-entities-schema` §7).

### 6.2 Schema: `.kiln/reviews/<slug>.yml`

```yaml
slug: kredyt-onlain-bez-vidmovy
content_sha256: 9f2c… # hash of the draft at review time; a mismatch voids the review
locale: uk
cluster: credits/online

classification:
  ymyl: true
  public_interest: true # EU AI Act Art. 50 criterion
  ai_involvement: assisted # none | assisted | generated
  disclosure_required: false # false if the human-review exemption applied
  disclosure_basis: art50_human_review

machine_gate:
  run_id: 2026-08-14T09:12:03Z
  thresholds_version: 3
  doctrine_commit: a1b2c3d # which doctrine version was applied
  passed: [A1, A2, A4, B1, B3, C2, C3, C4, D1, D2]
  failed: []

lenses:
  - lens: facts
    reviewer_id: vadym
    reviewer_qualification: "…" # AI Act: relevant knowledge and professional judgement
    substitution: false # true when run by the ring backup, not the named primary
    covered_for: null # reviewer_id of the absent primary; required when substitution: true
    started_at: 2026-08-14T10:02:11Z
    finished_at: 2026-08-14T10:36:40Z
    minutes_actual: 34
    verdict: pass # pass | rework | block
    checks:
      REV-01: pass
      REV-02: pass
      REV-08: rework
    substantive_changes: # THE CORE OF THE LOG. An empty list with verdict: pass is a validation error
      - locus: "section «Rates», paragraph 3"
        before: "rate 18.9%"
        after: "rate 21.4%"
        reason: "source updated 2026-08-11; the old value covered Q1"
        source: "https://bank.gov.ua/…  (verified 2026-08-14)"
        snapshot: .kiln/snapshots/…
    overridden_rules: [] # doctrine rules the reviewer judged inapplicable
    notes: ""

  # The three remaining lenses repeat the structure of `facts` above, field for field.
  # Elided here as comments rather than as a bare ellipsis: an ellipsis on its own line is
  # not valid YAML, and a schema example that does not parse cannot be validated against.
  - lens: domain
    # … same fields as the facts lens
  - lens: voice
    # … same fields as the facts lens
  - lens: utility
    # … same fields as the facts lens

consensus:
  disagreements:
    - locus: "section «Who it suits», paragraph 2"
      lens_a: voice
      verdict_a: rework
      rule_a: REV-29
      lens_b: utility
      verdict_b: pass
      rule_b: REV-38
      resolution: kept # kept | reworked | escalated
      queued_for_doctrine: true
  final_verdict: publish # publish | rework | drop
  approved_by: reviewer-1
  approved_at: 2026-08-14T18:20:05Z
  approval_is_separate_person: true # the approver is none of the lens reviewers on this draft
```

### 6.3 Log validation rules

| Rule                                                       | Severity |
| ---------------------------------------------------------- | -------- |
| `content_sha256` matches the draft being published         | BLOCKER  |
| All four lenses present, each carrying a `verdict`         | BLOCKER  |
| On YMYL: `reviewer_qualification` filled in for every lens | BLOCKER  |
| `substantive_changes` non-empty **on at least one lens**   | BLOCKER  |
| `minutes_actual` filled in on every lens                   | HIGH     |
| `approval_is_separate_person: true`                        | BLOCKER  |
| `doctrine_commit` filled in                                | BLOCKER  |

**On requiring non-empty `substantive_changes`.** This is neither bureaucracy nor a device to make
people invent something. A review that changed nothing of substance is either a review that did not
happen or a draft the machine should have passed without a human. Both cases need to be visible. If
a reviewer genuinely changed nothing and believes that is correct, they write an explicit entry with
`locus: none` and a justification; the record is then non-empty and the fact is stated honestly.

This is also a direct AI Act requirement: the exemption is granted for **examination of the
substance**, and an empty log does not evidence it.

---

## 7. Disagreement between lenses as a learning signal

### 7.1 The rule

**When two lenses return opposite verdicts on the same locus in the text, the wording of a rule is
at fault, not the person.** The disagreement is recorded in `consensus.disagreements` and enters the
doctrine amendment queue automatically (P8, and P9's fast loop).

A disagreement is not grounds for argument and not grounds for a vote. It is settled on the spot by
the approver (`resolution: kept | reworked | escalated`), but **the record survives regardless of
who prevailed**. Resolving a conflict does not erase the fact that it existed.

### 7.2 Mechanism

```
① review_stats.py finds pairs (locus, lens_a≠lens_b, verdict_a≠verdict_b)
      │
      ▼
② The pair is normalised into a record: rule A × rule B × context
      │
      ▼
③ The pair counter is incremented in .kiln/rules-stats.json
      │
      ▼
④ Threshold reached ──► an agent drafts RULE-CHANGE.md
      │                 (observations, data, affected projects, verification metric, rollback)
      ▼
⑤ A human merges or rejects. Automatic amendment is forbidden (P10).
```

### 7.3 Rule counters

`.kiln/rules-stats.json`, updated after every review:

```json
{
  "REV-29": {
    "applied": 41,
    "overridden": 19,
    "override_rate": 0.463,
    "conflicts_with": { "REV-38": 7 },
    "first_seen": "2026-08-14",
    "pages": ["kredyt-onlain-bez-vidmovy", "…"]
  }
}
```

Three signals and what they mean:

| Signal                                      | Diagnosis                                       | Action                                           |
| ------------------------------------------- | ----------------------------------------------- | ------------------------------------------------ |
| High `override_rate` on a sufficient sample | the rule obstructs more often than it helps     | candidate for **deletion**, not debate (P8)      |
| `conflicts_with` growing on one pair        | two rules contradict each other                 | candidate for rewording one of the pair          |
| Rule never fired across a large sample      | the rule is dead, or duplicates a machine check | candidate for deletion or move into the pre-gate |

**Thresholds live in one place.** The four numbers governing these signals — minimum sample before
judging a rule, the `override_rate` that makes a rule a deletion candidate, the pair-conflict count
that triggers escalation, and the firing count below which a rule is dead — are defined in
`11-self-learning.md` §3.5, which is canonical. They are not restated here.

Restating them would create exactly the failure §7.4 describes below: two documents holding the same
number, drifting apart, with nobody counting. A reader who needs the values reads the canonical
section; `rules_lint.py` fails the build if any doctrine file states a threshold key with a value
different from its canonical home (`05-writing-core.md` §10.4, check 8).

All four are `[expert judgement, needs calibration]`.

### 7.4 Why this is needed at all

The precedent is documented on a live project: in the owner's system **two mutually exclusive rules
coexisted**. `lp-copywriting §13.11` prescribes a phrase that `stop-rules §1.5` and `§3.5` expressly
forbid. Nobody noticed, because nobody was counting (`[internal observation, unpublished]` §6.2). A body of rules without
counters diverges from itself and does not report it.

---

## 8. The rework path

### 8.1 Form

A rework is a typed `rework-request`, not a free-form comment. Schema:

```yaml
rework_request:
  from_lens: facts
  iteration: 1
  items:
    - rule: REV-08
      locus: "section «Results», table"
      problem: "all three numbers are round: 40%, 60%, 80%"
      expected: "numbers as they appear in the source, unrounded"
      blocking: true
  scope: partial # partial | full — whether a full rewrite is required
```

Three fields are mandatory: **what is wrong, where, and what counts as fixed**. A rework without
`expected` is not accepted: it sends the writer off to guess and all but guarantees a second
iteration.

Any lens may initiate a rework. This is a mesh, not a conveyor (`EVIDENCE.md#e14-content-operations` §3.2).

### 8.2 How many iterations

| Iteration | What happens                                                                         |
| --------- | ------------------------------------------------------------------------------------ |
| 1         | Ordinary fix. Only the returning lens re-checks.                                     |
| 2         | Fix. The returning lens re-checks and the approver is notified.                      |
| 3         | **Stop rule.** The draft leaves the pipeline and goes to a brief post-mortem (§8.3). |

A draft never goes past the third iteration. This limit protects the lens budget: three passes over
one piece consume the quota that could have covered three different ones.

### 8.3 A third rework means a defective brief, not a defective text

At the third rework the presumption is that **the problem is upstream**. A writer cannot fix what
was specified wrongly.

The post-mortem runs three questions, in this order:

1. **Is the promised unique value unattainable?** If `unique_value_source` requires data we do not
   have, no amount of editing will produce it. The topic returns to the backlog flagged "primary
   data required" (`EVIDENCE.md#e11-content-quality-signals`, appendix, rule 2).
2. **Was the intent misidentified?** When lens U returns a draft on `REV-38` ("the reader cannot do
   what they came to do"), page type and query intent are usually mismatched.
3. **Is this topic not ours?** When the domain lens returns on `REV-15` or `REV-20` twice, we lack
   expertise in the subject. Entering a niche without real expertise is an explicit Google red flag
   (`EVIDENCE.md#e11-content-quality-signals` §3.1).

The outcome is recorded in `doctrine/CHANGELOG.md` as a negative result (P15), even when the topic
is simply dropped. A dropped topic with an explanation is knowledge; one deleted in silence is loss.

---

## 9. Degradation and fallbacks

### 9.1 A reviewer drops out

**The problem this solves.** The ceiling in §5.1 is a minimum across lenses, so one absent reviewer
sets `capacity` to zero. Throughput does not fall by a quarter; it stops. On a four-person team with
four lenses that is not a rare edge case, it is every holiday, illness and busy fortnight.

**REV-B1 (`BLOCK` on large corpora, `WARN` otherwise).** Every lens has a **named primary and a named
backup**, both declared at onboarding in `project.yml` (§9.1.1). A lens with no named backup is a
`WARN` at onboarding, and becomes a `BLOCK` once the corpus passes the same threshold that governs
manual publishing in `01-onboarding-grill.md` ONB-13, currently 100 URLs.

The escalation is not bureaucratic tidiness. A single point of failure on a large corpus is the
condition that structurally converts an in-house editorial operation into the outsourced-partner
arrangement described in `10-safety-gates.md` §4 — the arrangement that cost four documented
properties nearly all of their traffic. A team that cannot review is a team that either stops or
waves things through, and only one of those is survivable.

There are exactly four people for four lenses. **No spare staff exists, and the ring does not invent
any.** The only resource available is a second competence in the same four people.

#### 9.1.1 The ring is data, not code

Each reviewer is primary on one lens and backup on one neighbouring lens, forming a ring. The
pairing lives in `project.yml` and is never hard-coded:

```yaml
review:
  lenses:
    facts:
      primary: reviewer-3
      backup: vadym
    domain:
      primary: yura # weakest link in the ring, see below
      backup: oleksii
    voice:
      primary: oleksii
      backup: yura
    utility:
      primary: vadym
      backup: reviewer-4
```

**Pair the lenses whose expertise transfers most easily.** Domain expertise is the hardest to
substitute and, on YMYL, cannot be substituted at all by an unqualified person without breaking the
AI Act exemption. Its backup assignment therefore deserves the most care and is **flagged at
onboarding as the ring's weakest link**, in writing. Voice and utility transfer most readily; facts
sits in between, since it is procedural rather than judgement-heavy.

#### 9.1.2 What a backup costs

A substituting reviewer carries two lenses, so their hours split between them. The formula must say
so rather than pretending the ring is free:

```
During a substitution period, for a reviewer R covering lenses {L1, L2}:

  H_L1 + H_L2 = H_R          (their total available hours, unchanged)

capacity is still min over ALL lenses of ( H_L × 60 ) / ( t_L × (1 + r_L) )
```

The absent reviewer's hours do not reappear elsewhere. With an even split and comparable `t_L`, a
substituting reviewer supplies roughly half the normal throughput on each of their two lenses, and
since the ceiling is a minimum, **the whole line runs at roughly half pace for the duration**. That
is the honest number. Expect it, plan around it, and do not quietly raise the cap to compensate —
that is the P2 violation §5.3 names as illegitimate.

#### 9.1.3 The one thing a backup may not do

**REV-B2 (`BLOCK`).** Blind review still holds. A backup covering lens B **must not** have already
reviewed that same draft as primary on lens A. If the ring leaves no valid reviewer for a given
draft, **that draft waits**.

One person applying two lenses to one text destroys the independence the entire disagreement signal
is built on (§1.3, §7). A disagreement with yourself is not a signal, and a record of one is worse
than no record: it enters the queue looking like evidence about a rule when it is evidence about
nothing. Waiting is cheap. Poisoned learning data is not.

Note this constrains scheduling, not staffing: the same person may be primary on lens A for draft 1
and backup on lens B for draft 2. The prohibition is per draft.

#### 9.1.4 Order of response

1. **Recalculate the ceiling.** `H_L` for that lens is 0, so `capacity` is 0 by the formula in §5.1.
   Publication stops by default, and that default is correct.
2. **Activate the named backup**, applying the split in §9.1.2 and the constraint in §9.1.3. For
   lens D on YMYL, handing over to an unqualified person is **forbidden**: it breaks the AI Act
   exemption, regardless of what the ring says.
3. **Reduce pace, not quality.** Publishing a third as much is legitimate. Publishing without a lens
   is not.
4. **Never merge one lens into another.** One person reading with two questions at once asks both
   worse than two people asking one each, and we lose the disagreements (§1.3). A backup runs the
   second lens as a **separate pass**, not as a combined read.

### 9.2 Switching to on-call

On-call is a mode in which one person covers all four lenses in a week, in separate passes. It is
permitted as a **temporary** measure when people are short.

What is lost, stated plainly:

- disagreements between lenses cease to exist, so the fast learning loop (P9) switches off;
- anchoring is unavoidable: having worked lens F, the person has already formed a view of the text;
- verdicts become incomparable between weeks, since they depend on who was on call.

On-call is therefore flagged in the log (`consensus.mode: duty`) and **excluded from rule
statistics**. Otherwise it poisons the counters in §7.

**Substitution reviews are excluded on the same grounds.** A review carrying `substitution: true`
(§6.2) is left out of `override_rate` and out of the disagreement queue, for exactly the reason
on-call is: a backup applies a checklist they use less often, so their override pattern is evidence
about their familiarity with the lens, not about the rule. Feeding it to `review_stats.py` would
mark good rules as obstructive precisely when the team is already short-handed.

What substitution reviews **do** still count for, and this distinction matters:

| Purpose                                       | Counted? | Why                                                                      |
| --------------------------------------------- | -------- | ------------------------------------------------------------------------ |
| EU AI Act Art. 50 human-review exemption      | **yes**  | a qualified person examined the substance; the ring does not change that |
| `HTPI_true` (human time per published item)   | **yes**  | the hours were really spent and the metric must not flatter the system   |
| `override_rate`, deletion candidacy           | no       | familiarity effect, not rule quality                                     |
| Disagreement queue and the fast learning loop | no       | same reason, and §9.1.3 already restricts who may pair                   |

`REV-B3 (BLOCK).` `substitution: true` without a `covered_for` value is a log validation error. An
unattributed substitution cannot be excluded from statistics correctly, and silently counting it is
the failure mode this rule exists to prevent.

### 9.3 Measuring whether the regime holds, from week three

The hypothesis that four people will sustain the regime is **unverified** and is the main
operational risk in this section. Measurement begins in week three, because the first two run on
enthusiasm and tell you nothing.

| Metric                                                 | What a decline means             |
| ------------------------------------------------------ | -------------------------------- |
| Share of drafts passing all four lenses on time        | the regime is not holding        |
| Median lag between pack assembly and verdict           | a lens has become the bottleneck |
| Share of `pass` verdicts with no `substantive_changes` | review is becoming a formality   |
| Spread of `minutes_actual` within a lens               | widening spread indicates haste  |
| Share of weeks falling back to on-call                 | hidden degradation               |

The third row matters most. **A merely formal review is more dangerous than no review at all**: it
produces a log that looks like grounds for the AI Act exemption while not being grounds for it.

The intervention threshold is expert judgement: if the share of `pass` verdicts without substantive
edits exceeds 0.5 on a sample of 20 drafts or more, the regime is considered degraded and the
publication ceiling is halved pending a post-mortem.

---

## 10. What cannot be handed to a machine

Six items on which neither code nor an LLM agent produces a reliable result. Attempting to automate
them is the primary failure source for content factories (`EVIDENCE.md#e11-content-quality-signals` §8).

| #   | What                                                       | Why the machine cannot                                                                                                                            | Lens |
| --- | ---------------------------------------------------------- | ------------------------------------------------------------------------------------------------------------------------------------------------- | ---- |
| 1   | Whether first-hand experience is real                      | An agent verifies the phrase "we tested this", not the test. Hence the requirement for an input artifact: an export, a photo, a log, a transcript | F, V |
| 2   | Whether a conclusion from a correct source is correct      | Verifying a source exists is not verifying the logic. These are different operations                                                              | D    |
| 3   | Value to a specific audience                               | "Existing audience would find it useful" is not computable; proxies arrive after the fact and are noisy                                           | U    |
| 4   | The author's expert authority                              | Requires a real person with a real footprint. A synthetic author is a direct violation and a long-term liability                                  | D    |
| 5   | Editorial fakery and polished emptiness                    | An LLM editor catches the crude cases and systematically misses polished emptiness, **because it produces that emptiness itself**                 | V    |
| 6   | Whether the reader's task was closed (`lastLongestClicks`) | Measurable only after the fact and only indirectly. Before publication it is expert judgement                                                     | U    |

Item 5 is why lens V cannot be replaced by an editor agent, however good. A model does not see its
own register.

---

## 11. Script specifications (layer 2)

Both scripts are autonomous utilities: they know nothing about any particular site, they read files
and write files. They port between projects unchanged.

### 11.1 `review_pack.py`

**Purpose:** assemble the review pack for one lens.

```
Input:
  --draft      path      draft (md or json)
  --brief      path      .kiln/briefs/<slug>.yml
  --lens       enum      facts | domain | voice | utility
  --gate       path      machine pre-gate result (json)
  --corpus     path      .kiln/corpus.json
  --project    path      .kiln/project.yml
  --serp       path      top-N snapshot for the target query (json, optional)
  --thresholds path      .kiln/thresholds.yml
  --out        path      where to write the pack

Output:
  <out>/pack-<lens>.md         human-readable pack (§4)
  <out>/pack-<lens>.json       the same structure machine-readable, for a future UI
  exit code 0 | 2 (pre-gate not passed, pack not assembled)
```

Requirements:

- If `--gate` contains even one BLOCKER-level failure, the script **does not assemble a pack** and
  exits with code 2. No human is called (§2).
- For lens F, claims are extracted together with **local snapshots** of their sources; where no
  snapshot exists, the claim is flagged explicitly.
- For lens V, machine metrics are printed **under a "hint" heading**, not a "result" heading, and
  contain no word resembling "fail".
- All word and length counts use **Unicode-aware tokenisation** (P5). `wc -w` and a naive `split()`
  are forbidden: on Cyrillic they return wrong values and invert conclusions.
- The script is deterministic: identical input yields a byte-identical pack. Otherwise reviews
  cannot be compared with each other.

### 11.2 `review_stats.py`

**Purpose:** compute rule statistics and prepare the doctrine amendment queue. Implements P8.

```
Input:
  --reviews    dir       .kiln/reviews/
  --doctrine   dir       doctrine/
  --thresholds path      .kiln/thresholds.yml
  --out        dir       .kiln/

Output:
  .kiln/rules-stats.json          per-rule counters (§7.3)
  .kiln/review-timing.json        median and 80th percentile of t_L, r_L per lens (§5.2)
  .kiln/doctrine-queue.json       amendment candidates with justification
  stdout                          summary: publication ceiling, regime degradation, top conflicts
```

Requirements:

- Computes `publish_cap_per_week` per §5.1 and **compares it against the value recorded** in
  `project.yml`. A discrepancy in the upward direction produces a warning on stdout and an entry in
  the queue.
- Excludes from rule statistics every review carrying `consensus.mode: duty` (§9.2) and every lens
  entry carrying `substitution: true` (§9.2). Exclusion is per lens entry, not per draft: a draft
  where one lens ran on its backup still contributes its other three lenses to the counters.
- Counts substitution reviews toward `HTPI_true` and toward AI Act evidence regardless of the above,
  and reports the substituted share of reviews in the summary. A rising substituted share is an
  early degradation signal (§9.3) and must not be invisible just because those reviews are excluded
  from rule statistics.
- Errors (non-zero exit) on any lens entry with `substitution: true` and no `covered_for`
  (`REV-B3`), because such a record cannot be excluded correctly.
- Modifies no file under `doctrine/`. It only prepares `doctrine-queue.json`; the PR is written by a
  human or an agent following the `RULE-CHANGE.md` template, and merged only by a human (P10).
- Computes the regime degradation metrics (§9.3) and prints them always, not on request.
- Where the sample threshold is not met, the rule **does not enter the queue** but does appear in
  the summary as "observed, insufficient data". Silence about an insufficient sample is forbidden.

---

## Prohibited

| Prohibition                                                                  | Grounds                                                                                                                                   |
| ---------------------------------------------------------------------------- | ----------------------------------------------------------------------------------------------------------------------------------------- |
| Scoring a draft on a scale instead of a binary verdict                       | scales drift and hide failure behind an average; `EVIDENCE.md#e11-content-quality-signals` §7, `[internal observation, unpublished]` §5.6 |
| Averaging lens verdicts, or offsetting one failure with other passes         | §1.4                                                                                                                                      |
| Showing a reviewer the other lenses' verdicts before reconciliation          | anchoring destroys the disagreements the fast loop is built on (§1.3)                                                                     |
| Calling a human on a draft that failed the machine pre-gate                  | P2: human time is the most expensive resource                                                                                             |
| Combining final approval with any lens in one person on the same draft       | `[internal observation, unpublished]` §1.1, "separate pre-ship gate"                                                                      |
| Publishing with `substantive_changes` empty across all lenses                | §6.3; the AI Act exemption requires examination of the substance                                                                          |
| Merging two lenses into one pass by one person when short-staffed            | §9.1                                                                                                                                      |
| Including a question about passing an AI detector in any checklist           | P3                                                                                                                                        |
| Amending rules automatically from disagreement statistics                    | P10                                                                                                                                       |
| Raising `publish_cap_per_week` by hand without recalculating `t_L` and `r_L` | P2, §5.3                                                                                                                                  |
| Counting on-call or substitution reviews in rule statistics                  | §9.2, poisons the counters with a familiarity effect                                                                                      |
| One person covering two lenses on the **same draft**, primary or backup      | `REV-B2`, §9.1.3; a disagreement with yourself is not a signal                                                                            |
| Operating a lens with no named backup on a corpus above the ONB-13 threshold | `REV-B1`, §9.1; a single point of failure is a structural risk (`10` §4)                                                                  |
| Measuring text length without Unicode-aware tokenisation                     | P5; `wc -w` inverted a conclusion on a live measurement                                                                                   |

---

## Conflicts and open questions

**1. `REV-27`…`REV-30` duplicate machine metrics.** Rhythm, symmetry, meta-commentary and the formal
summary are partly computed in code in `05-writing-core.md`. Formally this violates the "the human
does not repeat the machine" rule (§2). It is retained deliberately: the thresholds on those metrics
are expert judgement and uncalibrated, so the human is the arbiter here, and their disagreement with
the machine is a calibration signal rather than noise. **Revision condition:** once the thresholds
are calibrated over 100+ drafts, these four checks move into the pre-gate entirely, provided
human-versus-machine disagreement falls below 10%.

**2. Requiring non-empty `substantive_changes` may generate cosmetic edits for the sake of the box.**
The risk is real and acknowledged. It is mitigated by the explicit `locus: none` entry with a
justification (§6.3) plus the "share of `pass` without substantive edits" metric (§9.3). If that
metric shows people writing `locus: none` en masse, the requirement must be reworded, not tightened.

**3. The regime-endurance hypothesis is unverified.** Four lenses and 10+ hours a week is an
agreement, not a measured quantity. The only precedent available to us is negative (`[internal observation, unpublished]`
§5.12). The measurement in §9.3 exists precisely for this, and until week three of the pilot this
section should be treated as unproven.

**4. Every time-based threshold is an assumption.** `t_L`, `r_L`, the rule counters canonically
defined in `11-self-learning.md` §3.5, and the thresholds in §9.3 are all marked expert. No primary
data on review timings exists in any source we found (`EVIDENCE.md#e14-content-operations` §11). None of these numbers should
enter the shared doctrine as a constant; they live in `.kiln/thresholds.yml` and are calibrated
locally (P10).

**5. AI Act extraterritoriality is unresolved.** How Art. 50 obligations apply when publishing from
outside the EU to an EU audience is a legal question that fell outside the research (`EVIDENCE.md#e10-eeat-entities-schema` §10).
For the Ukrainian pilot this is material and requires separate verification before scaling.

---

## Sources

| What was taken                                                                           | From                                                              |
| ---------------------------------------------------------------------------------------- | ----------------------------------------------------------------- |
| Lily Ray's three gate questions (`REV-35`…`REV-37`), anti-patterns, 54% / 39% / 22%      | `EVIDENCE.md#e14-content-operations` §2                           |
| Editorial Mesh: typed rework requests, double scoring, disagreement as signal            | `EVIDENCE.md#e14-content-operations` §3.2                         |
| Cycle stage ratios; absence of primary timing data                                       | `EVIDENCE.md#e14-content-operations` §3.2, §11                    |
| Three-tier fact-checking model; human mandatory for quotes and primary sources           | `EVIDENCE.md#e14-content-operations` §5                           |
| The six non-automatable items                                                            | `EVIDENCE.md#e11-content-quality-signals` §8                      |
| Binary verdicts instead of scales; the machine criteria set                              | `EVIDENCE.md#e11-content-quality-signals` §7                      |
| `contentEffort` as "LLM-based effort estimation for article pages"                       | `EVIDENCE.md#e11-content-quality-signals` §2.2                    |
| `lastLongestClicks` as an editorial KPI (`REV-38`)                                       | `EVIDENCE.md#e11-content-quality-signals` §4.2                    |
| Google red flags: unreleased products, entering a niche without expertise                | `EVIDENCE.md#e11-content-quality-signals` §3.1                    |
| EU AI Act Art. 50: in force 2026-08-02, definition of human review, exemption, penalties | `EVIDENCE.md#e10-eeat-entities-schema` §7                         |
| YMYL Government/Civics/Society, QRG of 2025-09-11                                        | `EVIDENCE.md#e10-eeat-entities-schema` §2                         |
| `isAuthor`, `ProfilePage`, requirement to name real authors                              | `EVIDENCE.md#e10-eeat-entities-schema` §3, §7                     |
| External-fact freshness gate, severity BLOCKER (`REV-03`, `REV-04`, `REV-10`)            | `[internal observation, unpublished]` §2.14                       |
| Zero-fabrication policy (`REV-09`)                                                       | `[internal observation, unpublished]` §2.9                        |
| Vague source attribution (`REV-06`), real case study spec (`REV-08`, `REV-25`)           | `[internal observation, unpublished]` §2.9                        |
| Competitor Acknowledgment, Honest Limitations, Price Transparency (`REV-40`…`REV-42`)    | `[internal observation, unpublished]` §2.12                       |
| "Audience-fit must not hide behind the average" (§1.4)                                   | `[internal observation, unpublished]` §5.6                        |
| Comparison against cluster siblings (`REV-44`)                                           | `[internal observation, unpublished]` §5.7                        |
| Approval separated from review, "separate pre-ship gate"                                 | `[internal observation, unpublished]` §1.1                        |
| Negative result: "ran for one week and stopped" (§1.2, §9.3)                             | `[internal observation, unpublished]` §5.12                       |
| Mutually exclusive rules in one body, the case for counters (§7.4)                       | `[internal observation, unpublished]` §6.2                        |
| Three axes of human recognition: concreteness, cultural nuance, diversity                | `EVIDENCE.md#e03-ai-detection-and-humanization`, arXiv:2502.11614 |
| 2026 detectors do not rely on perplexity                                                 | `EVIDENCE.md#e03-ai-detection-and-humanization`, arXiv:2602.05769 |
