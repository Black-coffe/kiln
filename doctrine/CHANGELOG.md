# Doctrine changelog

Every change to `doctrine/`, in reverse chronological order.

**Negative results are recorded here with the same detail as positive ones** (P15). A reverted change
gets a full entry, not a deletion. This log is the only structure that makes the change queue
converge, and it is the single thing that makes a public repository more valuable than a vendor blog:
vendors publish what worked, on the projects where it worked, before the collapse.

Nothing is ever removed from this file. Corrections are appended.

---

## Entry format

```markdown
## YYYY-MM-DD · RC-YYYY-NNN · <one-line title>

|                            |                                                                                                                                                  |
| -------------------------- | ------------------------------------------------------------------------------------------------------------------------------------------------ |
| **Class**                  | rule_wording \| rule_added \| rule_deleted \| severity_change \| schema_change \| procedure_change \| threshold_promotion \| revert \| bootstrap |
| **Loop**                   | fast \| medium \| slow \| n/a                                                                                                                    |
| **Rules**                  | `XXX-NN`, `XXX-NN`                                                                                                                               |
| **Sections**               | `NN-name.md`                                                                                                                                     |
| **Evidence**               | link to the PR, and to the record IDs it rests on                                                                                                |
| **Attribution confidence** | high \| medium \| low                                                                                                                            |
| **Metric**                 | name of the verification metric                                                                                                                  |
| **Baseline → target**      | value → threshold, by deadline                                                                                                                   |
| **Verification**           | pending \| confirmed \| reverted \| inconclusive                                                                                                 |
| **Verified on**            | YYYY-MM-DD or `—`                                                                                                                                |
| **Outcome**                | filled in at verification, including what actually happened                                                                                      |

What changed and why, in prose. Two to five sentences.

**At verification:** what the metric did, whether it met the threshold, and what was concluded.
For a revert, what was learned that the next attempt should not repeat.
```

Rules for filling it in:

- The entry is created **at merge**, with `verification: pending`. It is not created after the fact.
- The `Outcome` row stays empty until the deadline. Filling it early is a prediction wearing the
  costume of a result.
- A `reverted` entry keeps its original text intact and gains a verification paragraph. The original
  reasoning is the useful part: it records what looked convincing and was not.
- An `inconclusive` entry states which sample was short and by how much.
- Rule IDs are never reused. A deprecated ID stays in this log forever and points at its successor.

---

## 2026-08-07 · RC-2026-000 · Doctrine v0.1.0 authored

|                            |                                                                                                                                                                                                                         |
| -------------------------- | ----------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| **Class**                  | bootstrap                                                                                                                                                                                                               |
| **Loop**                   | n/a                                                                                                                                                                                                                     |
| **Rules**                  | all: `ONB-01…23`, `SEM-01…24`, `CMP-01…26`, `TRD-01…18`, `WRT-*` (46), `REV-01…46`, `LNK-01…24` + `LNK-Z1…Z10`, `MSR-01…21`, `LRN-01…24`, and principles `P0…P15`                                                       |
| **Sections**               | `00-principles.md`, `01-onboarding-grill.md`, `02-semantics.md`, `03-competitors.md`, `04-trends-and-plan.md`, `05-writing-core.md`, `06-review-lenses.md`, `07-linking.md`, `08-measurement.md`, `11-self-learning.md` |
| **Evidence**               | a 19-agent research sweep on 2026-08-07, output in `research/seo-geo-framework/EVIDENCE.md#e01-geo-answer-engines…16` and `proj-01…03`; an owner interview the same day, output in `research/seo-geo-framework/grill/2026-08-07-brief-final.md`   |
| **Attribution confidence** | low, by construction                                                                                                                                                                                                    |
| **Metric**                 | n/a for the bootstrap; each subsequent change carries its own                                                                                                                                                           |
| **Baseline → target**      | n/a                                                                                                                                                                                                                     |
| **Verification**           | n/a                                                                                                                                                                                                                     |
| **Verified on**            | —                                                                                                                                                                                                                       |
| **Outcome**                | n/a                                                                                                                                                                                                                     |

The initial doctrine was written in one day from two inputs: a parallel research sweep across
nineteen agents covering answer engines, practitioner consensus, AI-text detection, Search Console
mining, semantics, internal linking, competitive intelligence, trend detection, Claude Code plugin
architecture, E-E-A-T and schema, content quality signals, data-source pricing, scaled-content
policy risk, content operations, the competitive product landscape, the three target sites, and the
an audit of an existing in-house content system; and a structured owner interview that fixed the
delivery form, the pilot, the review model, the change-approval model, the language scope and the
success measure.

**Everything numeric in this doctrine is uncalibrated.** Every threshold was set by engineering
judgement on 2026-08-07 against zero project data and is marked
`[expert judgement, needs calibration]` at its point of use. This includes the thresholds in
`11-self-learning.md` §3.5 that govern when other thresholds are allowed to change, which is
circular and is stated as such in that section's conflicts list. The first project to accumulate real
distributions is expected to replace them by PR.

Three positions are recorded as deliberate and load-bearing rather than provisional, because reverting
them would change what Kiln is:

1. **Rejection is the primary measure, not output** (P0). The rejection funnel occupies the first
   screen of the report; article count is secondary.
2. **No detector and no vendor content score may gate publication** (P3). Both were measured as
   noise-level or weak predictors, and vendor scores measure similarity to the top, which is the
   inverse of what is wanted.
3. **The doctrine never amends itself** (P10). An agent may draft a change; only a human may merge
   one, in both directions, including reverts.

Also recorded at bootstrap, as a known and accepted constraint rather than a defect: with one pilot
project, `LRN-17` blocks every behavioural Tier D change until a second project onboards. The
doctrine will appear frozen for its first months. That appearance is correct.

**Negative results inherited from prior work,** carried in at bootstrap because they were paid for
already and should not be paid for twice:

- A weekly editorial calendar on the owner's existing project ran for one week and stopped
  (`[internal observation, unpublished]` §5.12). Recorded as the precedent behind the P2 capacity cap and the per-lens review
  model.
- Two mutually exclusive rules coexisted in that system's canonical documents, one prescribing a
  phrase another forbade, unnoticed because nothing counted rule firings (`[internal observation, unpublished]` §6.2). This is
  the origin of P8 and of the entire instrumentation model.
- An advisory-only quality gate with no enforcing hook left compliance resting on human discipline
  (`[internal observation, unpublished]` §6.7). This is why gates in Kiln are executable.
- A stop-word dictionary went five months past its own stated review date without anyone noticing
  (`[internal observation, unpublished]` §6.4). This is why language packs are versioned and dated.
- Optimising text for low perplexity was carried in that system as a rule, and 2026 detectors no
  longer rely on perplexity (`EVIDENCE.md#e03-ai-detection-and-humanization`). Dropped at bootstrap rather than migrated.
