---
name: measure
description: Pull Search Console data, run the opportunity and risk algorithms, and produce the leading-indicator report. Use when reviewing performance, hunting striking-distance or decay opportunities, calibrating CTR curves, or checking cohort risk after publishing.
argument-hint: "[--weekly|--monthly|--cohorts]"
allowed-tools: Read, Write, Edit, Bash, Grep
---

# Measurement and the leading-indicator report

Governing doctrine: `${CLAUDE_PLUGIN_ROOT}/doctrine/08-measurement.md`.
Read §2 (the eight leading indicators), §5 (the algorithms, each as input, formula, threshold,
output, action) and §6 (the two CTR curves) before reporting numbers.

Root principles: `P0` (rejection is the primary measure), `P8` (rules are measured), `P9` (three
learning loops at different speeds).

## What success looks like at 90 days

Leading indicators, not traffic. `LI-8`, the rejection funnel broken down by cause, sits on the
first screen — it is Kiln's primary measure of itself, and it is the fast loop's main input.

Traffic is a reference line. The asymmetry is deliberate: a rise proves little inside 90 days,
while a fall is read immediately.

## Numbers that are easy to get wrong

- **Average position** has three forms across the site table, the URL table and the API, and two
  of them are zero-based. Aggregation must be impression-weighted. Read §5.0 rather than
  recomputing from intuition.
- **Deduplicate before aggregating** in BigQuery exports, or every figure comes out inflated.
- **The anonymous query is an empty string, not NULL.** Filters written for NULL silently drop it,
  and the sums stop reconciling.
- **`epoch_version` is the only signal** that Google rewrote history. Recomputing silently when it
  increments is forbidden.
- **Cut the last three to four days** of the window; they are incomplete.
- **Segment by locale before applying any threshold.** Mixed locales produce averages describing
  no market. The same path in two locales is two pages.

## Thresholds disagree, and that is recorded rather than resolved

Two columns appear in §5 — the values from the owner's working analyzer and the values from
practice. The striking-distance thresholds differ by two orders of magnitude. The pilot uses the
low one deliberately. Do not silently pick one; report which was used, and every finding carries
`thresholds_used` so recalibration does not invalidate history.

## CTR curves are calibrated, never assumed

Two curves: clean SERP, and SERP with an AI overview. Public curves are cold-start priors only —
published values for position one range from 19 % to 39.8 %. Blend toward local data with
`w = min(1, impressions/10000)`, and mark every estimate provisional while `w < 0.3`. Absolute
traffic forecasts from a public curve are forbidden.

## Cohort risk

No manual action exists for scaled content abuse, so the penalty arrives silently and detection
has to be cohort-based: Kiln cohorts against the pre-Kiln baseline. `cohort_watch.py` exits
non-zero and pauses publishing; only a human releases the pause.

On a site with a long pre-existing corpus the control group is unusually clean. On a site
returning from a hiatus, the historical window describes a different site — usable for the cohort
baseline and for seasonality, not for CTR calibration.
