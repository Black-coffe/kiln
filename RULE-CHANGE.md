# RULE-CHANGE

The only admitted route for changing anything under `doctrine/`. Copy this file into the pull
request body, fill every field, and delete nothing.

A rule without evidence is an opinion, and the doctrine holds no opinions (P10).

**Before you start, check that your change is actually a doctrine change.** Numeric thresholds,
weights, limits and windows are Tier L: they calibrate locally in `.kiln/thresholds.yml` and need no
PR. See `doctrine/11-self-learning.md` §5.2 for the exact classification. If your change is a number
and only a number, you are in the wrong place.

---

## 1. Summary

**Change ID:** `RC-YYYY-NNN`
**Class:** `rule_wording` | `rule_added` | `rule_deleted` | `severity_change` | `schema_change` | `procedure_change` | `threshold_promotion` | `revert`
**Loop that produced the evidence:** `fast` | `medium` | `slow`
**Rule IDs touched:**
**Section(s):**

One paragraph, plain language: what changes and why it should.

---

## 2. Observation

What was actually seen. Not what it means yet.

- **Number of independent observations:**
- **Unit of observation:** `draft` (fast) | `page` (medium) | `cohort` (slow)
- **Minimum sample required for this loop:** (see `11-self-learning.md` §3.5)
- **Sample met?** yes / no

> If no, stop. A proposal below the minimum sample is inadmissible even with a caveat (LRN-14).

**Record IDs backing this** (`DIS-…`, page slugs, cohort IDs):

**Observation window:** from `YYYY-MM-DD` to `YYYY-MM-DD`

---

## 3. Data

Every figure with a date and a source. Model output is not evidence (P1); this applies to evidence
about the doctrine exactly as it applies to evidence in an article.

| Figure | Value | Date | Source |
| ------ | ----- | ---- | ------ |
|        |       |      |        |

**`doctrine_commit` range of the material this draws on:**
(Required for medium-loop proposals. A proposal drawing on pages written under three different
versions of the rule in question is inadmissible, LRN-03.)

**Was there a control or holdout?** yes / no
**If no, why a controlled comparison was not feasible:**
**Resulting `attribution_confidence`:** `high` | `medium` | `low`

---

## 4. Affected projects

Every project running this doctrine, by name, with the expected effect. "No effect, because …" is a
valid answer. Leaving a project out is not (LRN-18).

| Project      | Expected effect | Reasoning |
| ------------ | --------------- | --------- |
| site-a         |                 |           |
| site-b           |                 |           |
| site-c         |                 |           |

**Corroborating evidence from a second project?** yes / no

> A behavioural change justified by one project alone is inadmissible (LRN-17). Wording
> clarifications with no behavioural effect are exempt; if you claim that exemption, say why the
> change cannot alter which drafts fire.

---

## 5. The change

**Before:**

```
(exact current text of the rule)
```

**After:**

```
(exact proposed text)
```

**Does this change what the rule means, or only how it is phrased?**
`meaning` | `phrasing only`

> If `meaning`: the old ID is deprecated and a new ID is issued, with `id_supersedes` pointing back.
> Reusing an ID after its meaning changed destroys the counter history (LRN-06).
>
> If `phrasing only`: state why no draft that currently fires would stop firing, or vice versa.

**New ID issued:** `—` / `XXX-NN`
**Old ID deprecated:** `—` / `XXX-NN`

---

## 6. Verification

**Metric:**
**Baseline value:** (measured, with date)
**Expected direction:** `up` | `down`
**Success threshold:**
**Minimum sample at deadline:**
**Deadline:** `YYYY-MM-DD` (fast 30d · medium 90d · slow 180d; shorter if `attribution_confidence: low`)

> A change that cannot name a metric that would move if it worked is not a change worth making
> (LRN-20).

---

## 7. Rollback

**Rollback condition:**
**Rollback action:**
**What is lost by reverting:**

> The revert is executed by a merged PR, never automatically. `change_verify.py` may open it and must
> not merge it (LRN-21).

---

## 8. Checklist

The PR fails if any box is unchecked. These are not suggestions; `rules_lint.py` and the reviewer
both enforce them.

- [ ] Change ID assigned and unique
- [ ] Class and loop declared, and the class is one this loop may touch (LRN-02)
- [ ] Minimum sample for the loop is met (LRN-14)
- [ ] Every figure in §3 carries a date and a source (P1)
- [ ] `attribution_confidence` stated honestly
- [ ] Every project in §4 addressed by name (LRN-18)
- [ ] Single-project justification either avoided or explicitly exempted (LRN-17)
- [ ] Before/after text is exact, not paraphrased
- [ ] Meaning-vs-phrasing declared; new ID issued if meaning changed (LRN-06)
- [ ] Verification metric, baseline, threshold, sample and deadline all filled (LRN-20)
- [ ] Rollback condition and action filled
- [ ] No numeric threshold is being hard-coded into doctrine prose that belongs in `thresholds.yml` (LRN-12)
- [ ] No rule touched here has an open change in probation (LRN-23)
- [ ] `CHANGELOG.md` entry added, with `verification: pending`
- [ ] Nothing under `doctrine/` was edited by a script or agent on the main branch (LRN-10)

---

---

# Worked example

The standard expected. This is a real-shaped example, filled in as a contributor should fill it.

---

## 1. Summary

**Change ID:** `RC-2026-011`
**Class:** `rule_wording`
**Loop that produced the evidence:** `fast`
**Rule IDs touched:** `REV-29`, `REV-38`
**Section(s):** `06-review-lenses.md`

`REV-29` (voice lens: "does this passage read as generated?") and `REV-38` (utility lens: "is the
comparison scannable?") reach opposite verdicts on the same construction: a run of parallel clauses
in an audience-fit paragraph. Both reviewers are applying their rule correctly. The rules are silent
on which one governs when a parallel structure is doing comparison work, so the outcome depends on
which lens looks first. The change adds that carve-out to `REV-29` and a matching pointer to
`REV-38`.

---

## 2. Observation

- **Number of independent observations:** 7
- **Unit of observation:** `draft`
- **Minimum sample required for this loop:** 5 conflicts on one pair (escalation threshold, §3.5)
- **Sample met?** yes

**Record IDs backing this:** `DIS-2026-0142`, `DIS-2026-0151`, `DIS-2026-0158`, `DIS-2026-0163`,
`DIS-2026-0166`, `DIS-2026-0171`, `DIS-2026-0180`

**Observation window:** from `2026-08-14` to `2026-11-01`

Six of the seven occurred in a paragraph immediately following a comparison table. All seven carry
both rationales, so all seven are admissible as evidence (LRN-09).

---

## 3. Data

| Figure                                   | Value  | Date       | Source                                             |
| ---------------------------------------- | ------ | ---------- | -------------------------------------------------- |
| Reviews in window                        | 41     | 2026-11-03 | `.kiln/rules-stats.json` `_meta.reviews_in_window` |
| Disagreements on pair `REV-29 \| REV-38` | 7      | 2026-11-03 | `.kiln/learning/queue.json`                        |
| Disagreement rate on the pair            | 0.171  | 2026-11-03 | 7 / 41, computed                                   |
| `REV-29` override rate                   | 0.463  | 2026-11-03 | `.kiln/rules-stats.json`                           |
| `REV-29` firings                         | 41     | 2026-11-03 | `.kiln/rules-stats.json`                           |
| Occurrences in a post-table paragraph    | 6 of 7 | 2026-11-03 | `queue.json` `loci_summary`                        |

**`doctrine_commit` range:** not applicable, fast-loop wording proposal.

**Was there a control or holdout?** no
**If no, why a controlled comparison was not feasible:** the signal is reviewer disagreement, not page
performance. There is no untouched group to compare against, because the comparison is between two
rules applied to the same text.
**Resulting `attribution_confidence`:** `medium`

Note on `REV-29`'s override rate: at 0.463 it is above the 0.40 deletion-candidate threshold. This
proposal argues the override rate is a symptom of the same ambiguity rather than grounds for
deletion, and the verification metric below is chosen so that a failure to reduce disagreement leaves
the deletion question open rather than answered.

---

## 4. Affected projects

| Project      | Expected effect                                | Reasoning                                                                                          |
| ------------ | ---------------------------------------------- | -------------------------------------------------------------------------------------------------- |
| site-a         | disagreement rate on the pair falls below 0.08 | source of the observation; comparison tables are common in the credits and deposits clusters       |
| site-b           | same direction, smaller magnitude              | `/vs/*` pages use comparison tables heavily, so the construction occurs; the voice lens is staffed |
| site-c         | no effect                                      | the voice lens is not staffed on that project and no comparison-table pages are published yet      |

**Corroborating evidence from a second project?** no

This is claimed as a **wording clarification with no behavioural effect**: the carve-out states which
of two already-existing rules governs an already-existing case. No draft that currently passes both
rules will begin to fail, and no draft that currently fails `REV-29` on grounds other than a
comparison-adjacent parallel structure is affected. On that basis the single-project restriction in
LRN-17 does not apply.

---

## 5. The change

**Before:**

```
REV-29 (HIGH). Does this passage read as generated? Three or more parallel clauses in
sequence with no concrete detail between them is the primary tell.
```

**After:**

```
REV-29 (HIGH). Does this passage read as generated? Three or more parallel clauses in
sequence with no concrete detail between them is the primary tell.

Carve-out: parallelism that is carrying comparison work, in a paragraph adjacent to a
comparison table or list, is out of scope for this rule. Judge that construction under
REV-38 instead. If the parallelism is not doing comparison work, this rule governs.
```

**Does this change what the rule means, or only how it is phrased?**
`phrasing only`

The carve-out removes a case `REV-29` was never intended to cover, and `REV-38` already covers it.
No draft changes its overall verdict: a comparison-adjacent parallel structure that is genuinely bad
still fails, under `REV-38`. What changes is which rule ID records the failure, which is precisely
what makes the current counters unreadable.

**New ID issued:** `—`
**Old ID deprecated:** `—`

---

## 6. Verification

**Metric:** `disagreement_rate(REV-29|REV-38)`
**Baseline value:** 0.171, measured 2026-11-03
**Expected direction:** `down`
**Success threshold:** ≤ 0.08
**Minimum sample at deadline:** 20 reviews
**Deadline:** `2026-12-05` (fast loop, 30 days)

Secondary observation, not a success condition: `REV-29`'s override rate should fall if the ambiguity
was the cause. If it does not, the deletion-candidate question stands and is handled by a separate
proposal.

---

## 7. Rollback

**Rollback condition:** at `2026-12-05`, disagreement rate on the pair is above 0.08 with at least 20
reviews in the window; or a new disagreement pair appears at `REV-38` with count ≥ 3 that did not
exist before, indicating the ambiguity moved rather than resolved.

**Rollback action:** revert the merge commit. Reopen `DIS-2026-0142` and the six related records by
appending a correction record referencing them, per LRN-08. Return the pair to
`.kiln/learning/queue.json` with `open_change_id: null`.

**What is lost by reverting:** nothing durable. The disagreement records survive the revert by design,
so the next attempt starts from the same evidence plus the knowledge that this wording did not work,
which goes into `CHANGELOG.md` as a negative result (P15, LRN-24).

---

## 8. Checklist

- [x] Change ID assigned and unique
- [x] Class and loop declared, and the class is one this loop may touch (LRN-02)
- [x] Minimum sample for the loop is met (LRN-14)
- [x] Every figure in §3 carries a date and a source (P1)
- [x] `attribution_confidence` stated honestly
- [x] Every project in §4 addressed by name (LRN-18)
- [x] Single-project justification either avoided or explicitly exempted (LRN-17)
- [x] Before/after text is exact, not paraphrased
- [x] Meaning-vs-phrasing declared; new ID issued if meaning changed (LRN-06)
- [x] Verification metric, baseline, threshold, sample and deadline all filled (LRN-20)
- [x] Rollback condition and action filled
- [x] No numeric threshold is being hard-coded into doctrine prose that belongs in `thresholds.yml` (LRN-12)
- [x] No rule touched here has an open change in probation (LRN-23)
- [x] `CHANGELOG.md` entry added, with `verification: pending`
- [x] Nothing under `doctrine/` was edited by a script or agent on the main branch (LRN-10)
