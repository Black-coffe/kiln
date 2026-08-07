---
name: audit
description: Full project health check against every Kiln gate — corpus, graph, semantics, competitors, safety, doctrine consistency and rule statistics. Use for a periodic sweep, before scaling publishing, after a core update, or when something is wrong and the cause is unknown.
argument-hint: "[--section <name>]"
allowed-tools: Read, Bash, Grep, Glob
---

# Full project audit

This skill runs the checks that other skills own, in one pass, and produces a single report. It
defines no rules of its own. Every finding cites the rule ID and the doctrine file it came from.

Sections and their governing files, all under `${CLAUDE_PLUGIN_ROOT}/doctrine/`:

| Section              | Governing file           | Rule prefix |
| -------------------- | ------------------------ | ----------- |
| Eligibility          | `01-onboarding-grill.md` | `ONB-`      |
| Semantics            | `02-semantics.md`        | `SEM-`      |
| Competitors          | `03-competitors.md`      | `CMP-`      |
| Plan and trends      | `04-trends-and-plan.md`  | `TRD-`      |
| Drafts and corpus    | `05-writing-core.md`     | `WRT-`      |
| Review discipline    | `06-review-lenses.md`    | `REV-`      |
| Graph and duplicates | `07-linking.md`          | `LNK-`      |
| Measurement          | `08-measurement.md`      | `MSR-`      |
| Safety gates         | `10-safety-gates.md`     | `SAF-`      |

## Also audit the doctrine itself

`P8`. Run `rules_lint.py` over `${CLAUDE_PLUGIN_ROOT}/doctrine/` and report:

- rules that contradict each other — one document prescribing what another forbids is the failure
  this whole mechanism exists to catch, and it has happened in production before
- rule IDs referenced by scripts but absent from the doctrine, and the reverse
- thresholds present in the doctrine with no calibration record in `.kiln/thresholds.yml`
- rules whose override rate exceeds 0.40 at a sample of 20 or more — those are candidates for
  deletion, not for argument
- rules that have never fired, which are either dead or unimplemented

A rule nobody measures drifts, and a set of rules nobody measures contradicts itself without
anyone noticing.

## Report shape

Findings first, ranked by severity, each with: rule ID, what was measured, the threshold and where
it came from, the affected URLs or entities, and the action. Then the rejection funnel and rule
statistics. Then what could not be checked and why — a section that was skipped because access was
missing must be named, not silently omitted, or the report reads as coverage it does not have.

Every finding carries `thresholds_used`.

## This skill proposes; it does not execute

Merges, redirects, deletions and pace changes are human decisions under `P11`. Produce the
decision with its evidence and stop there. Doctrine amendments follow `P10` — a PR carrying
observations, dated data, affected projects, the verification metric and the rollback condition.
An agent may prepare that PR and must not merge it.
