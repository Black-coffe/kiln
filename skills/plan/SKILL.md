---
name: plan
description: Build or update the content plan from clusters, trends, competitor gaps and Search Console opportunities, capped by review capacity. Use when planning what to write next, when refreshing the queue, when a trend fires, or when deciding which pages to update.
argument-hint: "[locale]"
allowed-tools: Read, Write, Edit, Grep, Glob
---

# Build the content plan

Governing doctrine: `${CLAUDE_PLUGIN_ROOT}/doctrine/04-trends-and-plan.md` for routes, scoring and
the `.kiln/plan.yml` schema. Inputs come from `02-semantics.md` (clusters and priority),
`03-competitors.md` (gaps) and `08-measurement.md` (opportunities). Read the governing file before
planning; the four routes have different entry conditions and different urgency.

Root principles: `P2` (the plan is capped by verification capacity), `P13` (unique value named
before the item enters the queue), `P14` (programmatic pages need real records).

## Four routes in

`NEWSJACK`, `SEASONAL`, `EMERGING`, `REFRESH`. Entry conditions and windows are in §5. Two things
that trip people up:

- A `NEWSJACK` item **preempts** rather than adds. If it were allowed on top of the cap, the cap
  would not exist. Something else leaves the queue.
- Seasonal lead time is a parameter in `.kiln/thresholds.yml`, never a constant. The circulating
  "three to six months before the peak" is practitioner consensus with no measurement behind it.

## Freshness is the age of what a page cites

Not its publication date. A page can be newly published and already stale if its sources are old.
`source_age_median` and the per-type thresholds are in §6. This is the cheapest refresh trigger
available and almost nobody uses it.

Changing a date without a substantive edit is forbidden — Google names date manipulation directly,
and the date implied by a page's contents makes the discrepancy detectable.

## The cap is hard

`max_wip` derives from actual review logs, not from intent. Refuse to add an item that breaches
it, and say which route it came from and what would have to leave. A plan that exceeds
verification capacity is the failure mode that took 54 % of AI-content-platform domains down by a
third or more of their traffic.

## Every queue entry carries its evidence

Mandatory fields are listed in §8. An entry without `unique_value_source` and its backing artefact
does not enter the queue; an entry without `cannibalization_checked` does not either. The
`dropped` section is never purged — rejected items are the calibration data for the whole gate.
