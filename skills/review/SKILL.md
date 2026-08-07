---
name: review
description: Assemble the four per-lens human review packs for a draft, collect the verdicts, and log them. Use when a draft has passed the machine gate and needs human review, when reconciling lens disagreements, or when checking review capacity against the publishing pace.
argument-hint: "[slug] [lens]"
allowed-tools: Read, Write, Edit, Grep
---

# Assemble review packs

Governing doctrine: `${CLAUDE_PLUGIN_ROOT}/doctrine/06-review-lenses.md`.
Read it before assembling anything. All 46 checks `REV-01`…`REV-46`, the per-lens pack structure,
the capacity formula and the log schema live there.

Root principles: `P8` (rules are measured, not only pages), `P11` (substantive review before
publication is mandatory and logged).

## Four lenses, not four readings

- **F, facts** `REV-01`…`REV-12` — every figure and condition against a primary source
- **D, domain** `REV-13`…`REV-22` — meaning errors that fact-checking cannot catch
- **V, voice** `REV-23`…`REV-34` — does it read as a living text
- **U, usefulness** `REV-35`…`REV-46` — does the page close the reader's task; is the product
  truth present

Four different questions find four classes of defect. One question asked four times finds one
class four times, and the reviewers burn out inside a month. Each pack contains only its own lens.

## Rules that shape the packs

**Do not assemble a pack for a draft that failed the machine gate.** `review_pack.py` exits 2.
Human attention is the binding constraint on the whole system under `P2`; spending it on a
document already known to be unfit lowers the publishing ceiling for nothing.

**Lenses are blind to each other until reconciliation.** Showing one reviewer another's verdict
anchors them, and the disagreement between lenses is the raw material the fast loop runs on. A
disagreement is evidence that a rule is ambiguously worded — it is a doctrine defect, not an
argument between people, and it is logged either way.

**Each pack states what the machine already checked**, so the human does not re-run it. Lens D
receives plain text with no markup and no metrics. Lens U receives the current top five results,
because "would a competitor clone this with the same prompt" is guesswork without them.

**Review happens in the language of the content.** A reviewer assigned to a locale must be fluent
in it; the voice lens is meaningless otherwise. Checklist questions may be presented translated,
but rule IDs and verdicts are logged in their canonical English form.

## Logging

Write `.kiln/reviews/<slug>.yml` per the schema in §6.2, including `content_sha256`,
`reviewer_qualification`, `substantive_changes` and `doctrine_commit`.

An empty `substantive_changes` across all four lenses is a `BLOCKER`. Exemption from labelling
under EU AI Act Art. 50 requires examination of the substance, and a log recording no substance
does not evidence it. A merely formal review is more dangerous than no review, because it produces
a document that looks like grounds for exemption and is not.

The approver may not be any of the four lens reviewers on the same draft.

## Capacity

The publishing ceiling comes from the narrowest lens, not the sum of hours — see §5.1. Until
thirty logs exist, the ceiling is the number agreed at onboarding; the formula switches on after
that and uses the 80th percentile, so the ceiling survives a bad week rather than describing a
good one.
