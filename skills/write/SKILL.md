---
name: write
description: Produce a draft for one planned item under the Kiln writing rules and the locale's language pack, then score it against the pre-publication gate. Use when writing a new article, when a plan entry is ready to draft, or when a returned draft needs rework.
argument-hint: "[slug]"
allowed-tools: Read, Write, Edit, Grep, Glob
---

# Write a draft

Governing doctrine: `${CLAUDE_PLUGIN_ROOT}/doctrine/05-writing-core.md`.
Read §1 (pipeline and role contracts), §2 (artefact schemas), §3 (the scoring rules) and §5 (the
effort gate) before drafting. The 46 rules and their thresholds live there and are calibrated per
project; working from memory produces a draft that fails the gate for reasons you will not be able
to explain.

Language pack: read `${CLAUDE_PLUGIN_ROOT}/doctrine/lang/<code>.md` for the locale of this item,
taken from `.kiln/project.yml`. **The doctrine is written in English; the draft is not.** The pack
governs vocabulary, syntax and punctuation and never transfers across languages.

## Project state

- Profile: `.kiln/project.yml` — locale, taboos, product truth, proprietary assets, authors
- Plan entry: `.kiln/plan.yml` — the item, its cluster, its `unique_value_source`
- Corpus: `.kiln/corpus.json` — what already exists, for the cannibalization check
- Thresholds: `.kiln/thresholds.yml` — local calibration, overrides doctrine defaults

## The pipeline is not optional and the roles do not blend

Stages and their artefacts are specified in §1.1. The role contracts in §1.2 are machine-checked:

- the researcher gathers evidence and writes no prose
- the writer may not leave the research packet — a claim absent from it cannot enter the draft
- the editor may not introduce facts
- the judge must not share a model with the writer
- the human reviewer's own verdict is recorded before any machine verdict is shown to them

Spawn `kiln-researcher`, `kiln-writer`, `kiln-editor` and `kiln-judge` for these roles rather than
performing them yourself in one pass. A single agent playing every role satisfies none of the
contracts, and the fast learning loop under `P9` loses its independent signals.

## Two rules people break first

**No word-count target.** `P0` appendix and `WRT-04`. Google names writing to a length as a signal
of unreliable content. Length is an outcome of the brief, never an instruction. If you want a
proxy for padding, use words-per-claim from §4, not a minimum.

**Unique value must be named before drafting, not justified after.** `P13`. The plan entry carries
`unique_value_source` and the effort artefact that backs it. If it is empty, stop and say so:
the pre-publication gate will reject the draft anyway, and rejecting it now costs nothing.

## Gate before handing over

Run the draft scorer and read its findings. A `BLOCK` finding means the draft does not go to human
review — that would spend the scarcest resource in the system on a document the machine already
knows is unfit. Fix, or return the item to the plan with a reason.

Never gate on an AI detector or a third-party content score. `P3`. Those correlate with ranking at
0.011 and 0.28 respectively, and optimising for them optimises for similarity to the top, which is
the inverse of what a page needs.
