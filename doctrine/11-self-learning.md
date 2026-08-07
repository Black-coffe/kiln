# 11 — Self-learning

> Subordinate to `00-principles.md`. Implements **P8** (we measure the rules, not only the pages),
> **P9** (three learning loops), **P10** (the doctrine changes only through a PR carrying evidence),
> **P15** (negative results are recorded on equal footing).
> Any conflict with the principles is resolved in favour of the principles.

**Version:** 0.1.0 · **Date:** 2026-08-07 · **Review:** mandatory after the first merged rule change is verified

|              |                                                                                                                                                                                                                                             |
| ------------ | ------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| **Purpose**  | Turn observed outcomes into doctrine changes at a rate that is fast enough to calibrate anything, and slow enough not to learn from noise.                                                                                                  |
| **Inputs**   | `.kiln/reviews/*.yml` (human review logs, §06), `.kiln/gates/*.jsonl` (machine gate firings, §05/§10), `.kiln/measurements/*` (Search Console and derived numbers, §08), `.kiln/geo/*` (citation measurement, §09), `.kiln/thresholds.yml`. |
| **Outputs**  | `.kiln/rules-stats.json`, `.kiln/learning/disagreements.jsonl`, `.kiln/learning/queue.json`, `.kiln/learning/changes.jsonl`, a drafted `RULE-CHANGE.md` PR, an entry in `doctrine/CHANGELOG.md`.                                            |
| **Executor** | Code aggregates and computes. An agent drafts the PR. A human merges. Nothing else may write to `doctrine/`.                                                                                                                                |

---

## 0. What this section governs

Every other section of the doctrine states rules. This one states how those rules are allowed to
change, and it is the section most likely to decay into hand-waving, because "the framework learns"
is easy to say and hard to falsify.

So the whole section is written as machinery: a signal has a defined storage location, a defined
minimum sample, a defined class of rule it is permitted to touch, a defined verification metric and
a defined deadline after which an unverified change is reverted. If a proposed improvement cannot be
expressed in those five terms, it is not an improvement, it is an opinion, and the doctrine holds no
opinions.

**LRN-01 (BLOCK).** A change to `doctrine/` that does not carry all five terms (observations, data,
affected projects, verification metric, rollback condition) fails the PR checklist. See
`RULE-CHANGE.md`.

---

## 1. Why three loops, and why the slow one alone is useless

### 1.1 The arithmetic

Search feedback arrives on a horizon of three to six months. On the owner's own project this is
recorded plainly: the domain is six months old, ranking around position 56 is expected, is **not a
fixable on-page defect**, and the right response is to measure leading indicators rather than clicks
(`[internal observation, unpublished]` §5.12). That is a correct diagnosis, and it has a consequence nobody draws: a system
learning only from that signal completes **three or four learning cycles per year**.

Three or four observations is not a calibration. It is not enough to distinguish a rule that works
from a rule that coincided with a core update. And the slow signal is the most confounded of the
three: an algorithm update, a seasonal swing or a competitor's move all land in the same numbers.
Confounded signals need larger samples, which take longer to accumulate, which reduces the cycle
count further.

The fast loop exists because it is the only one that produces enough events to calibrate wording.
A review lens firing on a draft is an event; four lenses across twenty drafts is eighty events in a
month, on a system publishing four to eight articles. That is a usable sample for questions about
rule wording, and it costs nothing extra because the reviews were happening anyway.

### 1.2 What each loop is allowed to touch

The loops are not interchangeable. A fast-loop signal must never be used to justify a strategic
change, and a slow-loop signal must never be used to reword a checklist item, because in each case
the signal does not contain the information the change requires.

**LRN-02 (BLOCK).** A proposed change must declare which loop produced its evidence, and the change
class must be one that loop is permitted to touch (§2). A mismatch fails the PR.

---

## 2. The three loops

| Loop       | Period | Signal                                                                          | Storage                                                                 | May change                                                                                                           | Minimum sample before it may propose anything                                                        |
| ---------- | ------ | ------------------------------------------------------------------------------- | ----------------------------------------------------------------------- | -------------------------------------------------------------------------------------------------------------------- | ---------------------------------------------------------------------------------------------------- |
| **Fast**   | days   | review lens verdicts, lens disagreements, machine gate firings, human overrides | `.kiln/reviews/*.yml`, `.kiln/gates/*.jsonl` → `.kiln/rules-stats.json` | wording of rules; checklist questions; severity of a non-blocking rule; local thresholds of writing and review rules | 20 firings of the rule `[expert judgement, needs calibration]`                                       |
| **Medium** | weeks  | indexation and time to first impression, first positions, AI citation rate      | `.kiln/measurements/`, `.kiln/geo/`                                     | page structure rules; intent-to-surface routing; brief schema fields; local thresholds of structure rules            | 10 pages carrying the rule **and** 21 days since publication `[expert judgement, needs calibration]` |
| **Slow**   | months | GSC cohort dynamics, traffic, conversions                                       | `.kiln/measurements/cohorts/`                                           | cluster selection strategy; publishing pace; page-type mix; anything touching P2 capacity                            | 2 cohorts plus 1 control cohort, and 90 days `[expert judgement, needs calibration]`                 |

### 2.1 Fast loop

**Signal.** Three distinct events, all already produced by work that has to happen anyway:

1. A machine gate fires on a draft (`05-writing-core.md`, `10-safety-gates.md`).
2. A human reviewer overrides a rule, recording it in `overridden_rules` (`06-review-lenses.md` §6.2).
3. Two lenses reach opposite verdicts on the same locus, recorded in `consensus.disagreements`.

**What it teaches.** Whether a rule is understandable, whether it is applicable, and whether it
contradicts another rule. It teaches nothing about whether the rule improves rankings, and must not
be used to claim that.

**Latency from signal to a mergeable proposal.** Target ≤14 days `[expert judgement, needs
calibration]`. Longer than that and the reviewers who generated the signal no longer remember the
context that would let them judge the proposal.

### 2.2 Medium loop

**Signal.** LI-1 (indexation rate), LI-2 (days to first impression), LI-4 (share of queries in the
visible zone), LI-5 (AI citation rate), as defined in `08-measurement.md` §2 and `09-geo.md`.

**What it teaches.** Whether a structural decision helped: heading form, answer placement, passage
self-sufficiency, internal link position, page type chosen for an intent.

**The attribution problem, stated honestly.** At a pace of four to eight articles per month (P2), a
sample of ten pages carrying one rule takes one to three months to accumulate, and by then the
doctrine has probably changed elsewhere. This is why every review log carries `doctrine_commit`
(`06-review-lenses.md` §6.2): pages are attributed to the doctrine version in force when they were
written, and a medium-loop comparison is only valid within a set of pages sharing the relevant rule
state.

**LRN-03 (WARN).** A medium-loop proposal must state the `doctrine_commit` range of the pages it
draws on. A proposal drawing on pages written under three different versions of the rule in question
is inadmissible.

### 2.3 Slow loop

**Signal.** Cohort dynamics from `08-measurement.md` §9: pages grouped by publication period,
compared against the `pre-kiln` cohort and against each other.

**What it teaches.** Whether the strategy is working, and whether the domain is being harmed. The
second is the more important of the two, because no manual action exists for scaled content abuse
and the penalty arrives silently (P2, `EVIDENCE.md#e13-policy-and-risk`).

**The control group we happen to own.** On the pilot, 4,075 URLs predating Kiln form a control group
of a quality a new site cannot provide. This is an asset, and it expires: once Kiln has touched a
page, that page leaves the control group permanently.

**LRN-04 (BLOCK).** A page used as a slow-loop control must not be modified by Kiln. The control set
is recorded at onboarding, is append-only in the sense that pages may leave it but never rejoin, and
its membership is stored in `.kiln/measurements/cohorts/control.json`.

---

## 3. Rule instrumentation

### 3.1 Every rule is counted

**LRN-05 (BLOCK).** Every rule in `doctrine/` carrying an ID is instrumented. A rule that cannot be
counted, because no code path and no reviewer checklist references its ID, is either dead or
misfiled, and `rules_lint.py` (`05-writing-core.md` §10) fails the build on it.

This includes the rules in this section. A self-learning mechanism that exempts itself from
measurement is the exact failure it exists to prevent.

### 3.2 Schema of `.kiln/rules-stats.json`

Regenerated in full on every run. Never hand-edited.

**Two scales, two fields, never one column.** This file records every rule in the doctrine, and the
corpus uses two vocabularies: machine rules carry `BLOCK` / `WARN` / `INFO`, while the human review
checklist in `06-review-lenses.md` carries its own declared verdict scale. Putting both in a single
`severity` key means a query filtering on it silently returns the wrong half of the rules, and the
mistake is invisible because every row still has a plausible value.

- `review_level` — the native review verdict level. Non-null only when `class` is `review`.
- `machine_severity` — always populated, in the three-level machine scale. For a review rule it is
  the mapped equivalent from the scale mapping declared in `06-review-lenses.md`.

Aggregating across all rules therefore reads `machine_severity` and never branches on `class`;
anything reasoning about the human checklist reads `review_level` and gets null for machine rules,
which is a loud absence rather than a wrong answer.

```json
{
  "_meta": {
    "generated_at": "2026-11-03T06:00:00Z",
    "doctrine_commit": "a1b2c3d",
    "window_days": 90,
    "drafts_in_window": 47,
    "reviews_in_window": 41,
    "generator": "rules_stats.py@0.1.0"
  },
  "rules": {
    "REV-29": {
      "class": "review",
      "review_level": "HIGH",
      "machine_severity": "WARN",
      "section": "06-review-lenses.md",
      "introduced_in": "a1b2c3d",
      "id_supersedes": null,
      "status": "probation",

      "applied": 41,
      "overridden": 19,
      "override_rate": 0.463,
      "not_applicable": 3,

      "conflicts_with": { "REV-38": 7 },

      "outcomes": {
        "pages_fired_on": ["kredyt-onlain-bez-vidmovy", "..."],
        "pages_count": 41,
        "indexed_rate": 0.85,
        "days_to_first_impression_median": 9,
        "ai_citation_rate": null,
        "comparison_set": "pages_where_rule_did_not_fire",
        "comparison_pages_count": 22,
        "attribution_confidence": "low"
      },

      "signals": ["override_rate_exceeded", "conflict_pair_escalated"],
      "first_seen": "2026-08-14",
      "last_fired": "2026-11-01",
      "last_evaluated": "2026-11-03",
      "open_change_id": "RC-2026-011"
    }
  },
  "aggregate": {
    "rules_total": 214,
    "rules_never_fired": 31,
    "rules_in_probation": 4,
    "rules_flagged_for_deletion": 2,
    "rules_deprecated": 1
  }
}
```

Field notes that matter:

- **`applied` counts firings, not drafts.** A rule firing three times in one draft is three.
- **`not_applicable`** is distinct from `overridden`. A reviewer marking a rule inapplicable to this
  page type is not disagreeing with the rule; conflating the two inflates the override rate and
  deletes good rules.
- **`outcomes.attribution_confidence`** is `low` unless the comparison set was formed by the
  controlled procedure in §6.2. It is `low` by default and must be earned.
- **`open_change_id`** links to `.kiln/learning/changes.jsonl`. A rule with an open change is frozen
  from further proposals until that change is verified or reverted (§7.4).

### 3.3 Rule status lifecycle

```
     proposed ──merge──► probation ──verified──► active
                             │                     │
                             │                     ├─signal──► flagged_for_deletion ──merge──► deprecated
                             │                     │
                             └──not verified by deadline──► reverted
```

`deprecated` rules keep their IDs forever and are never reused.

**LRN-06 (BLOCK).** Rule IDs are immutable. If a change alters what a rule means, rather than only
how it is phrased, the old ID is deprecated and a new ID is issued, with `id_supersedes` pointing
back. Reusing an ID for changed semantics destroys the counter history and silently corrupts every
comparison that spans the change.

Cosmetic rewording that provably does not change which drafts fire keeps the ID, and the PR must say
so explicitly.

### 3.4 The three signals and what they mean

| Signal                                    | Diagnosis                                       | Action                                                   |
| ----------------------------------------- | ----------------------------------------------- | -------------------------------------------------------- |
| `override_rate` high at sufficient sample | the rule obstructs more often than it helps     | candidate for **deletion**, not for argument (P8)        |
| `conflicts_with` growing on one pair      | two rules contradict each other                 | candidate for rewording one of the pair                  |
| never fired at a large sample             | the rule is dead, or duplicates a machine check | candidate for deletion or for demotion into the pre-gate |

### 3.5 Thresholds

Aligned with `06-review-lenses.md` §7.3. Where both documents state a number, this table is the
canonical one and the other defers to it.

| Threshold                                                        | Starting value | Status                                  |
| ---------------------------------------------------------------- | -------------- | --------------------------------------- |
| Minimum sample before any judgement about a rule                 | 20 firings     | `[expert judgement, needs calibration]` |
| `override_rate` making a rule a deletion candidate               | 0.40           | `[expert judgement, needs calibration]` |
| Conflicts on one pair before escalation                          | 5              | `[expert judgement, needs calibration]` |
| "Dead rule": 0 firings across                                    | 50 drafts      | `[expert judgement, needs calibration]` |
| Minimum pages for a medium-loop claim                            | 10             | `[expert judgement, needs calibration]` |
| Minimum days since publication for a medium-loop claim           | 21             | `[expert judgement, needs calibration]` |
| Minimum cohorts for a slow-loop claim                            | 2 + 1 control  | `[expert judgement, needs calibration]` |
| Projects required to promote a local threshold into the doctrine | 2              | `[expert judgement, needs calibration]` |

Every number here is an engineering guess made on 2026-08-07 with no calibration data in existence.
They are starting values whose only virtue is being written down, and the first project to accumulate
real distributions is expected to replace them by PR.

---

## 4. Disagreement as a defect signal

### 4.1 The rule

**LRN-07.** When two review lenses reach opposite verdicts on the same locus, the fault lies with the
wording of the rule, not with either reviewer. The disagreement enters the change queue regardless of
how it was resolved, and regardless of which reviewer turned out to be right.

Resolution and record are independent operations. The approver decides what happens to the draft
today (`resolution: kept | reworked | escalated`, `06-review-lenses.md` §6.2). The record exists to
answer a different question: why was it possible for two competent people applying the doctrine to
reach opposite conclusions? That question survives the draft.

**LRN-08 (BLOCK).** A disagreement record must not be deleted, edited or resolved away.
`.kiln/learning/disagreements.jsonl` is append-only. Corrections are appended as new records
referencing the original by `id`.

### 4.2 Record schema

`.kiln/learning/disagreements.jsonl`, one JSON object per line:

```json
{
  "id": "DIS-2026-0142",
  "recorded_at": "2026-08-14T18:22:10Z",
  "slug": "kredyt-onlain-bez-vidmovy",
  "locale": "uk",
  "content_sha256": "9f2c...",
  "doctrine_commit": "a1b2c3d",
  "locus": "section «Кому підходить», paragraph 2",
  "excerpt": "...",
  "lens_a": "voice",
  "rule_a": "REV-29",
  "verdict_a": "rework",
  "rationale_a": "reads as generated: three parallel clauses, no concrete detail",
  "lens_b": "utility",
  "rule_b": "REV-38",
  "verdict_b": "pass",
  "rationale_b": "the parallel structure is what makes the comparison scannable",
  "resolution": "kept",
  "resolved_by": "reviewer-1",
  "pair_key": "REV-29|REV-38",
  "pair_count_after": 7,
  "queued": true,
  "change_id": "RC-2026-011"
}
```

`rationale_a` and `rationale_b` are mandatory. Without them the record proves that a disagreement
happened but not what was ambiguous, and the change queue receives a number instead of a defect.

**LRN-09 (BLOCK).** A disagreement recorded without both rationales is counted in the pair statistics
but may not be cited as evidence in a PR. `BLOCK` rather than `WARN`: the check is mechanical, the
record either carries both rationales or it does not, and a PR citing one that does not must fail
rather than proceed with a reviewer's assurance that the missing rationale was obvious.

### 4.3 From queue to proposal

```
① Reviews close for a draft
        │
        ▼
② disagreement_queue.py extracts pairs, normalises to pair_key, appends records
        │
        ▼
③ Pair count reaches the escalation threshold (5)
        │
        ▼
④ Pair enters .kiln/learning/queue.json with all its records attached
        │
        ▼
⑤ An agent drafts RULE-CHANGE.md: the ambiguity, the records, the proposed wording,
   the verification metric (expected drop in the pair's disagreement rate), the deadline
        │
        ▼
⑥ A human merges or rejects. Automatic amendment is forbidden (P10).
```

**LRN-10 (BLOCK).** The agent drafting the proposal may write only to `.kiln/learning/` and to a PR
branch. It must not write to `doctrine/` on the main branch under any circumstance.

---

## 5. The two-tier change model

### 5.1 The two tiers

|                 | **Tier L (local)**                                 | **Tier D (doctrine)**                                                         |
| --------------- | -------------------------------------------------- | ----------------------------------------------------------------------------- |
| What            | numeric thresholds, weights, limits, windows, caps | rule text, checklist questions, prohibitions, severities, procedures, schemas |
| Lives in        | `.kiln/thresholds.yml` in the project repository   | `doctrine/*.md` in the Kiln repository                                        |
| Changes by      | automatic calibration on project data, logged      | merged PR only                                                                |
| Scope of effect | one project                                        | every project                                                                 |
| Reversible by   | rerunning calibration                              | git revert of the PR                                                          |

### 5.2 Precise classification

Tier L, calibrated automatically:

- SERP overlap threshold for clustering, embedding pre-filter cutoff (`02-semantics.md`)
- Candidate and tracking thresholds for competitors, monitoring cadences (`03-competitors.md`)
- `z` thresholds, persistence, `lead_time`, `source_age_median` limits (`04-trends-and-plan.md`)
- Original claim density floor, entity coverage band, n-gram overlap ceiling, time to answer
  (`05-writing-core.md`)
- Per-lens minutes and rework multipliers feeding the capacity formula (`06-review-lenses.md`)
- Link counts, anchor share limits, wave size, click depth (`07-linking.md`)
- Striking distance bounds, cannibalization `flip_rate`, CTR curve values, cohort alert bounds
  (`08-measurement.md`)
- Every threshold in §3.5 of this section

Tier D, PR only:

- The existence of any gate and its severity
- The wording of any rule or checklist question
- Anything in `00-principles.md`
- The set of required fields in any schema (`project.yml`, `brief.yml`, review log, this section's
  files)
- The classification of a parameter as Tier L or Tier D, including this list

**LRN-11 (BLOCK).** Changing a rule's severity is a Tier D change even when the numeric threshold
attached to it is Tier L. Demoting a `BLOCK` to a `WARN` removes a brake, which is exactly the class
of change P0 exists to slow down.

### 5.3 What stops a local threshold from silently becoming a doctrine change

Three mechanisms, because one is not enough.

**Provenance on every key.** `.kiln/thresholds.yml` stores, for each key, where its current value
came from:

```yaml
writing.original_claim_density_min:
  value: 2.4
  provenance: calibrated # doctrine_default | calibrated | manual_override
  calibrated_at: 2026-10-19
  calibration_run: .kiln/learning/calibrations/2026-10-19-ocd.json
  sample_n: 63
  doctrine_default: 2.0
  drift_from_default: 0.20
```

**A lint that forbids numbers in prose.** `rules_lint.py` fails the build when a doctrine document
states a numeric threshold that also exists as a `thresholds.yml` key, unless the number is
explicitly labelled as the doctrine default. Otherwise the two drift apart and readers follow the
prose.

**A drift report, not an auto-promotion.** When a key's `drift_from_default` exceeds 25 %
`[expert judgement, needs calibration]` in the same direction on at least 2 projects, the drift
report proposes a PR to move the doctrine default. It does not move it.

**LRN-12 (BLOCK).** A local threshold is never promoted into the doctrine automatically, at any drift
magnitude, on any sample size. Promotion is a Tier D change and requires a merged PR (P10).

**LRN-13 (WARN).** `provenance: manual_override` requires a one-line reason in
`.kiln/thresholds.yml`. A hand-set number with no reason is indistinguishable from a typo six months
later.

---

## 6. Guards against learning on noise

The failure this section is most likely to produce is not inaction. It is a plausible change derived
from four data points, merged because it sounded right, propagated to every project at once.

### 6.1 Minimum samples

**LRN-14 (BLOCK).** No proposal may be drafted below the minimum sample for its loop (§3.5). The
agent must refuse rather than caveat: a proposal with an explicit "small sample" note still gets
merged by a tired human on a Friday.

**LRN-15 (BLOCK).** Sample size is counted in independent units, not in observations. Twenty firings
across three drafts is three units, not twenty. The unit is the draft for the fast loop, the page for
the medium loop, the cohort for the slow loop. `BLOCK` rather than `WARN`, because LRN-14 is
otherwise trivially bypassable: counting observations instead of units clears any minimum sample on
demand, and the resulting proposal looks fully evidenced.

### 6.2 Control where a control is possible

**LRN-16 (WARN).** Where a controlled comparison is feasible, it is mandatory, and the doctrine
already specifies the shape of one: the three-group protocol in `07-linking.md` (donors, targets,
and untouched pages in the same section). A before-and-after comparison with no untouched group
measures the season, the algorithm and the rule together, and cannot separate them.

Where a control is genuinely impossible, the proposal says so and its `attribution_confidence` stays
`low`. A `low`-confidence proposal may still be merged, but it enters `probation` with a shorter
verification deadline (§7.2).

### 6.3 Never infer from one project

**LRN-17 (BLOCK).** A Tier D change may not be justified by evidence from a single project unless the
change is a wording clarification with no behavioural effect. Everything behavioural requires
corroboration from a second project or an explicit, argued statement of why the finding is expected
to generalise.

The reasoning is P10's: the doctrine is shared and public, so a change derived from one site's niche,
one site's audience and one site's four reviewers moves every other project simultaneously. On
2026-08-07 Kiln has one pilot, which means **behavioural Tier D changes are effectively blocked until
a second project onboards**, and that is the correct state, not a defect to be worked around.

**LRN-18 (BLOCK).** Every proposal must state its expected effect on the other projects by name,
including "no effect, because ...". A proposal that has not considered the other projects has not
been thought through, and the field is not optional.

### 6.4 Do not learn from the vendor pattern

The failure mode documented across 220+ domains was a system that grew for six to twelve months, was
celebrated, and then collapsed (P0, `EVIDENCE.md#e14-content-operations`, `EVIDENCE.md#e15-market-landscape`). Most of those collapses happened after
the case study was published. The lesson for this section is narrow and specific: **an improving
metric over a period shorter than the feedback horizon is not evidence that the change was safe.**

**LRN-19 (WARN).** A slow-loop proposal citing fewer than 90 days of data must state explicitly that
it cannot yet distinguish improvement from the early phase of the documented collapse trajectory.

---

## 7. Verification after merge

### 7.1 Every change carries a metric and a deadline

**LRN-20 (BLOCK).** A merged change enters `probation` and is recorded in
`.kiln/learning/changes.jsonl` with a verification metric, a baseline value, an expected direction,
a deadline and a rollback condition. A change that cannot name a metric that would move if it worked
is not a change worth making.

`.kiln/learning/changes.jsonl`, one object per line, append-only:

```json
{
  "change_id": "RC-2026-011",
  "merged_at": "2026-11-05T00:00:00Z",
  "doctrine_commit": "e4f5a6b",
  "class": "rule_wording",
  "loop": "fast",
  "rules": ["REV-29", "REV-38"],
  "observation": "7 disagreements on the pair over 41 reviews",
  "metric": "disagreement_rate(REV-29|REV-38)",
  "baseline": 0.171,
  "expected_direction": "down",
  "success_threshold": 0.08,
  "deadline": "2026-12-05",
  "min_sample_at_deadline": 20,
  "rollback": "revert PR #— and reopen DIS records",
  "affected_projects": ["site-a", "site-b", "site-c"],
  "expected_effect_elsewhere": "site-b: same pair, expect same drop; site-c: no effect, voice lens not staffed",
  "attribution_confidence": "medium",
  "status": "probation",
  "verified_at": null,
  "outcome": null
}
```

### 7.2 Deadlines

| Loop   | Default verification deadline | If `attribution_confidence: low`       |
| ------ | ----------------------------- | -------------------------------------- |
| Fast   | 30 days                       | 21 days                                |
| Medium | 90 days                       | 60 days                                |
| Slow   | 180 days                      | not admissible; gather a control first |

All `[expert judgement, needs calibration]`.

Lower confidence gets a **shorter** deadline, not a longer one. A weakly-supported change should be
tested against reality sooner and discarded faster; extending its rope is how a guess becomes a
permanent fixture.

### 7.3 The three outcomes

| Outcome        | Condition                                                                                          | Action                                                                                |
| -------------- | -------------------------------------------------------------------------------------------------- | ------------------------------------------------------------------------------------- |
| `confirmed`    | metric passed `success_threshold` at or before the deadline, with `min_sample_at_deadline` reached | status → `active`; CHANGELOG entry updated                                            |
| `reverted`     | deadline reached, metric did not move, sample sufficient                                           | `change_verify.py` opens a **revert PR**; a human merges it                           |
| `inconclusive` | deadline reached, sample insufficient                                                              | one extension of the same length, once only; a second insufficiency forces `reverted` |

**LRN-21 (BLOCK).** A revert is a Tier D change and is executed by a merged PR, never by an automatic
edit. `change_verify.py` may open the PR and must not merge it. This is P10 applied symmetrically:
the prohibition on automatic amendment covers amendments that undo things as well as amendments that
add them.

**LRN-22 (BLOCK).** `inconclusive` may be extended exactly once. An indefinitely extended probation
is a rule that was never tested, wearing the appearance of one that was. `BLOCK` rather than `WARN`:
the extension count is a stored number, so the second request is refusable mechanically, and this is
the only thing standing between probation and a permanent unexamined state.

### 7.4 Freezing

**LRN-23.** While a rule has an open change in `probation`, no further proposal touching that rule is
admissible. Two concurrent changes to the same rule make both unverifiable.

### 7.5 Who closes the loop

Code computes the verdict. A human merges the confirmation or the revert. There is no third role, and
in particular there is no reviewer discretion to leave a probation open because the rule "feels
right": the metric and the deadline were chosen before the outcome was known, which is the only point
at which they could be chosen honestly.

---

## 8. Negative results

**LRN-24 (BLOCK).** Every `reverted` and every `inconclusive` outcome produces a CHANGELOG entry with
the same detail as a confirmed one: what was tried, on what evidence, what was expected, what
happened. Deleting or condensing away a negative result is forbidden.

Two reasons, one internal and one external.

**Internal.** Without the record, the same idea returns. A rule reverted in November is proposed again
in March by an agent reading the same disagreement records, and the second attempt costs the same as
the first while adding nothing. The negative log is the only structure that makes the queue converge.

**External.** This is the single thing that makes a public repository more valuable than a vendor
blog (P15). Vendors publish what worked, on the projects where it worked, before the collapse. The
documented pattern is precisely that: case studies published shortly before the traffic fell
(`EVIDENCE.md#e14-content-operations`, `EVIDENCE.md#e15-market-landscape`). A doctrine that publishes its retractions with the same prominence as its
rules is making a claim no vendor blog can make, and it is a cheap claim to make honestly, because
the reverts are already in git.

The owner's own system already does this in one place, and does it well: `"The weekly calendar didn't
survive contact. It ran for one week and stopped. This is the most important thing on this page."`
(`[internal observation, unpublished]` §5.12). That sentence is the standard.

---

## 9. What Kiln measures about itself

Computed over a rolling 90-day window unless stated. All counts are per project; cross-project
aggregation is a separate report and is never used as evidence for a Tier D change without §6.3.

### 9.1 Rejection rate by cause

```
RR(c)     = drafts_stopped_with_first_blocking_cause_c / drafts_entering_the_gate
RR_total  = Σ_c RR(c)
```

Attribution is to the **first** blocking cause in gate order, so the causes partition the rejected
set and `RR_total` is well-formed. A draft blocked by three things is counted once, under the
earliest gate.

This is LI-8 in `08-measurement.md` §2, and per P0 it sits on the first screen of the report. There is
no target value. A rising `RR_total` is not automatically bad, and a falling one is not automatically
good: both are questions. `RR_total` near zero on a working system means the gates are not gating.

### 9.2 Human time per published item

```
HTPI_published = Σ minutes_actual over lenses of drafts published in window
                 / count(published in window)

HTPI_true      = Σ minutes_actual over lenses of ALL drafts reviewed in window
                 / count(published in window)
```

`HTPI_true` is the real cost of a published article, because the time spent on drafts that were
rejected was still spent. Reporting only `HTPI_published` flatters the system exactly in proportion
to how much it rejects, which is the one direction we must not flatter.

`HTPI_true` feeds the P2 capacity formula in `06-review-lenses.md` §4.

### 9.3 Rework rate

```
RWR = drafts with ≥1 rework_request / drafts entering review
RWI = Σ rework iterations / drafts entering review          (mean iterations per draft)
```

A high `RWR` with a low `RWI` means the brief is adequate and the writer is sloppy. A high `RWI`
means the brief is inadequate, which is the presumption the third-iteration stop rule already
encodes (`06-review-lenses.md` §8).

### 9.4 Rule churn

```
CHURN = (rules_added + rules_modified + rules_deleted) / rules_total     per 90 days
```

Read as a band, not as a target. Sustained churn above roughly 15 % per quarter means the doctrine is
unstable and no page can be attributed to a rule state. Churn at zero, while the loops are producing
signals and the queue is non-empty, means the loops are decorative. Both bounds are
`[expert judgement, needs calibration]`.

### 9.5 Time from signal to merged change

```
TSM = median(merge_date − threshold_reached_date)   over changes merged in window
```

Reported per loop. The fast loop target is ≤14 days (§2.1). A `TSM` that grows while the queue grows
is the signal that the human merge step has become the bottleneck, and it is the one bottleneck this
section is not permitted to automate away (P10).

### 9.6 Verification confirmation rate

```
VCR = confirmed / (confirmed + reverted + inconclusive)
```

The honesty metric. A `VCR` near 1.0 does not mean the doctrine is excellent; it means the
verification metrics were chosen to be easy to pass, or the deadlines are being extended. A `VCR`
somewhere in the middle is what a system that actually tests its own changes looks like. No target is
set, deliberately, because any target here would corrupt the metric it measures.

---

## 10. Script specifications (Layer 2)

All three are deterministic, network-free, Unicode-aware (P5), and read only from `.kiln/`. None of
them writes to `doctrine/`.

### 10.1 `rules_stats.py`

```
rules_stats.py --kiln .kiln
               --window-days 90
               --doctrine ./doctrine        # read-only, for the rule inventory and IDs
               --out .kiln/rules-stats.json
               [--fail-on-signal]
```

**Input.** `.kiln/reviews/*.yml`, `.kiln/gates/*.jsonl`, `.kiln/measurements/pages.json`, the rule
inventory parsed from `doctrine/*.md`.

**Output.** `.kiln/rules-stats.json` exactly as specified in §3.2.

**Behaviour.** Counts firings, overrides and `not_applicable` separately. Joins page outcomes for
rules that fired, and sets `attribution_confidence` to `low` unless a comparison set produced by the
§6.2 protocol is present. Detects rules present in the inventory but absent from all logs and reports
them under `rules_never_fired`.

**Exit codes.** `0` clean · `1` malformed input or an unparseable log · `2` at least one rule crossed
a §3.5 threshold (with `--fail-on-signal`, so CI can surface it).

### 10.2 `disagreement_queue.py`

```
disagreement_queue.py --kiln .kiln
                      --append .kiln/learning/disagreements.jsonl
                      --queue  .kiln/learning/queue.json
                      [--escalation-threshold 5]
```

**Input.** `consensus.disagreements` blocks from `.kiln/reviews/*.yml`.

**Output.** Append-only records per §4.2, plus `.kiln/learning/queue.json`:

```json
{
  "generated_at": "2026-11-03T06:00:00Z",
  "pairs": [
    {
      "pair_key": "REV-29|REV-38",
      "count": 7,
      "escalated": true,
      "first_seen": "2026-08-14",
      "last_seen": "2026-11-01",
      "records": ["DIS-2026-0142", "..."],
      "loci_summary": "6 of 7 in an audience-fit paragraph following a comparison table",
      "both_rationales_present": 7,
      "admissible_as_evidence": true,
      "open_change_id": null
    }
  ]
}
```

**Behaviour.** Idempotent: rerunning does not duplicate records, matched on
`(slug, content_sha256, locus, pair_key)`. Never rewrites or removes an existing line (LRN-08).
Records missing a rationale are counted but marked `admissible_as_evidence: false` (LRN-09).

**Exit codes.** `0` clean · `1` malformed input · `2` at least one pair reached the escalation
threshold.

### 10.3 `change_verify.py`

```
change_verify.py --kiln .kiln
                 --changes .kiln/learning/changes.jsonl
                 --as-of 2026-12-05
                 --out .kiln/learning/verification-report.json
                 [--open-revert-pr]
```

**Input.** `.kiln/learning/changes.jsonl`, plus whichever of `rules-stats.json`,
`.kiln/measurements/`, `.kiln/geo/` the declared metric requires.

**Output.**

```json
{
  "as_of": "2026-12-05",
  "evaluated": 3,
  "results": [
    {
      "change_id": "RC-2026-011",
      "metric": "disagreement_rate(REV-29|REV-38)",
      "baseline": 0.171,
      "current": 0.052,
      "success_threshold": 0.08,
      "sample_n": 24,
      "min_sample_at_deadline": 20,
      "verdict": "confirmed",
      "action": "promote to active",
      "extension_used": false
    }
  ],
  "reverts_required": [],
  "extensions_granted": []
}
```

**Behaviour.** Computes the declared metric for each change past its deadline. Emits `confirmed`,
`reverted` or `inconclusive` per §7.3. With `--open-revert-pr` it opens a pull request reverting the
change's commit; it never merges (LRN-21) and never edits `doctrine/` on the main branch. Enforces
the single-extension limit (LRN-22).

**Exit codes.** `0` all evaluated changes confirmed or not yet due · `1` malformed input · `2` at
least one change requires a revert · `3` at least one change is stuck at a second `inconclusive`,
which forces a revert.

---

## 11. What code does, what the agent does, where a human is required

| Step                                                    | Code             | Agent         | Human                 |
| ------------------------------------------------------- | ---------------- | ------------- | --------------------- |
| Count firings, overrides, disagreements                 | ✅ deterministic | —             | —                     |
| Detect a threshold crossing                             | ✅               | —             | —                     |
| Read the disagreement rationales and name the ambiguity | —                | ✅            | —                     |
| Draft `RULE-CHANGE.md` with all five terms              | —                | ✅            | —                     |
| Judge whether the proposed wording is better            | —                | —             | ✅                    |
| Merge a Tier D change                                   | —                | —             | ✅ **only**           |
| Calibrate a Tier L threshold                            | ✅               | —             | —                     |
| Promote a Tier L value into the doctrine                | —                | drafts the PR | ✅ merges             |
| Compute a verification verdict                          | ✅               | —             | —                     |
| Open a revert PR                                        | ✅               | —             | —                     |
| Merge a revert                                          | —                | —             | ✅ **only**           |
| Write the CHANGELOG entry                               | —                | ✅ drafts     | ✅ approves in the PR |

The dividing line is the same one used throughout the doctrine: code computes what is reproducible,
an agent proposes what requires reading, a human decides what is irreversible. A merged doctrine
change is irreversible in the sense that matters here, because it has already run on live content
before anyone knows whether it was right.

---

## 12. Prohibited

| Prohibition                                                                                      | Reason                                         |
| ------------------------------------------------------------------------------------------------ | ---------------------------------------------- |
| Any automatic write to `doctrine/` on the main branch, by any agent or script, including reverts | P10, LRN-10, LRN-21                            |
| Merging a rule change with no evidence attached                                                  | P10, LRN-01                                    |
| Promoting a local threshold into the doctrine without a PR, at any drift magnitude               | P10, LRN-12                                    |
| Deleting, editing or condensing a negative result in `CHANGELOG.md`                              | P15, LRN-24                                    |
| Deleting or rewriting a line in `disagreements.jsonl`                                            | LRN-08                                         |
| Reusing a rule ID after its meaning changed                                                      | LRN-06, destroys counter history               |
| Drafting a proposal below the minimum sample, even with a caveat                                 | LRN-14                                         |
| Justifying a behavioural Tier D change from one project                                          | LRN-17                                         |
| Extending a probation more than once                                                             | LRN-22                                         |
| Two concurrent open changes on the same rule                                                     | LRN-23                                         |
| Demoting a `BLOCK` to a `WARN` as a Tier L change                                                | LRN-11, it removes a brake                     |
| Setting a target value for `VCR`                                                                 | §9.6, a target corrupts the metric it measures |
| Modifying a page that belongs to the slow-loop control set                                       | LRN-04                                         |

---

## 13. Sources

| Claim                                                                                     | Source                                                             |
| ----------------------------------------------------------------------------------------- | ------------------------------------------------------------------ |
| Two mutually exclusive rules coexisted unnoticed because nobody counted                   | `[internal observation, unpublished]` §6.2                                                    |
| "The weekly calendar didn't survive contact. It ran for one week and stopped."            | `[internal observation, unpublished]` §5.12                                                   |
| Six-month-old domain at position ~56 is expected, measure leading indicators not clicks   | `[internal observation, unpublished]` §5.12                                                   |
| Advisory-only gate with no hook: compliance rests on human discipline                     | `[internal observation, unpublished]` §6.7                                                    |
| The stop-word dictionary was unversioned and five months past its own review date         | `[internal observation, unpublished]` §6.4                                                    |
| 220+ domains, 54 % lost ≥30 % of peak traffic; collapses followed the vendor case studies | `EVIDENCE.md#e14-content-operations` §2, via P0                                              |
| Double-rating with disagreement routed back into rubric retuning                          | `EVIDENCE.md#e14-content-operations` §3.2, via `06-review-lenses.md` §1.3                    |
| Review log as the EU AI Act Art. 50 exemption artefact                                    | `EVIDENCE.md#e10-eeat-entities-schema`, via `06-review-lenses.md` §6.1                         |
| Rule counters, override rate, conflict pairs, dead-rule detection                         | `06-review-lenses.md` §7.3 (canonical thresholds now in §3.5 here) |
| Three-group measurement protocol used as the control template                             | `07-linking.md`                                                    |
| Leading indicators LI-1 … LI-8                                                            | `08-measurement.md` §2                                             |
| Cohort monitoring and the `pre-kiln` control cohort                                       | `08-measurement.md` §9                                             |

---

## 14. Conflicts with the principles

**14.1 P9 promises three loops; on 2026-08-07 only one can run.** The medium loop needs ten pages
carrying a rule, the slow loop needs two cohorts plus a control, and the pilot publishes four to
eight articles per month under P2. The medium loop therefore produces its first admissible claim
around month two or three, and the slow loop around month six. For the first quarter Kiln learns from
the fast loop alone. This is stated here rather than discovered later; the medium and slow thresholds
in §3.5 must not be lowered to make the loops appear active sooner.

**14.2 LRN-17 blocks behavioural changes until a second project exists, which is a real constraint,
not a formality.** With one pilot, the only Tier D changes admissible are wording clarifications with
no behavioural effect. Everything else waits for a second and third project to onboard. The
alternative, allowing single-project inference "just at the start", is exactly how a niche artefact
becomes a universal rule, so the constraint stands. The practical consequence: the doctrine will look
frozen for its first months, and that appearance is correct.

**14.3 P8 says a rule overridden more often than accepted is a deletion candidate; P0 says the
value is in rejection.** These pull against each other. A strict gate is overridden often _because_
it is strict, and deleting it on override rate alone dismantles the brake P0 exists to protect. The
resolution adopted here: `override_rate` makes a rule a **candidate**, and a `BLOCK`-severity rule
may not be deleted on override rate alone. It requires either evidence that the pages it blocked were
fine, or a second signal (conflict pair, or dead-rule). This is a judgement call made on 2026-08-07
with no data, and it is the first thing to revisit once override distributions exist.

**14.4 The verification metrics are chosen by the same party that proposes the change.** Nothing here
prevents an agent, or a human, from picking a metric that is easy to pass. `VCR` (§9.6) exists to make
that visible in aggregate, but it cannot catch an individual case, and a doctrine that graded its own
homework would be exactly the vendor pattern P15 objects to. The honest statement is that this is an
unresolved weakness; the partial mitigation is that the metric and threshold are fixed in writing
before the outcome is known, and the record is public.

**14.5 §3.5 thresholds are guesses about how to evaluate guesses.** Every number in this section was
set without data, including the numbers that govern when other numbers may change. There is no
non-circular way out of this at version 0.1.0. The mitigation is that they are all marked, all in one
table, and all first-in-line for replacement by the first project that accumulates real
distributions.

**14.6 Fast-loop signals are generated by four people who know each other.** Lens disagreements
measure ambiguity as experienced by one small team on one site in one language. Wording that is
unambiguous to them may be ambiguous to a contributor elsewhere, and the fast loop will never say so.
Public PRs from outside the team are the only corrective, and until the repository has outside
contributors, the fast loop is calibrating the doctrine to four readers.
