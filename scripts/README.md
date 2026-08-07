# Layer 2: autonomous scripts

These are the calculations. They exist because a model does not produce the same number twice, and
a learning loop built on numbers that drift teaches nothing.

**They know nothing about any particular site.** Input is a file, output is a file. No database
connection, no CMS client, no site-specific path. That is what makes them copyable between
projects verbatim, and it is the line separating this layer from the adapter, which is written per
project against `adapter/SPEC.md`.

Every script is specified in the doctrine file that owns it. The specification is authoritative:
field names, thresholds and exit behaviour live there, not here. This file is an index.

---

## Conventions every script follows

**JSON or JSONL in, JSON or JSONL out.** Nothing writes to a terminal for a human to read back;
nothing parses prose. Where a source is only available as CSV — a Search Console or Ahrefs export
— the reader normalises it to JSONL first.

**Deterministic.** Identical input produces byte-identical output, including ordering. Sorts are
total, with an explicit tiebreak. Without this it is impossible to tell a change in the SERP from
a change in our own implementation, and the medium learning loop reads exactly that difference.

**Unicode-aware text handling.** Word counts, sentence splitting, normalisation and truncation all
operate on Unicode, never on bytes and never on whitespace splitting alone. `wc -w` does not split
Cyrillic into words: on a live measurement it reported an English locale as six times larger than
a Ukrainian one that was in fact at parity, and the conclusion drawn from it was inverted.

**Non-zero exit on gate failure.** A script that finds a blocking condition exits non-zero. Hooks
and CI depend on this; a gate that only prints a warning is documentation.

**`thresholds_used` on every finding.** Each finding records the thresholds that produced it and
where they came from — doctrine default or local calibration. Thresholds are recalibrated over
time, and without this a recalibration silently invalidates every stored finding.

**No secrets on the command line.** Credentials arrive through the environment as
`CLAUDE_PLUGIN_OPTION_*`, or through a file path for keys too large for the credential store.
Plugin configuration is deliberately not read from project settings files, so nothing sensitive
belongs in the repository.

**No writes under `${CLAUDE_PLUGIN_ROOT}`.** That directory is replaced on every plugin update and
the previous one is deleted. All state goes to `.kiln/` in the consuming repository.

---

## Index

### Semantics — `doctrine/02-semantics.md`

| Script         | Purpose                                                                             |
| -------------- | ----------------------------------------------------------------------------------- |
| `normalize.py` | Normalise and deduplicate raw queries; assign `is_verified: false` to every one     |
| `edges.py`     | Build the query edge graph from SERP overlap and embedding similarity               |
| `cluster.py`   | Centroid clustering over the edge graph; `--diff-against` compares two cluster runs |
| `intent.py`    | Classify intent from SERP features on two axes, flagging cases needing arbitration  |
| `priority.py`  | Expected clicks with SERP-feature CTR modifiers; records `curve_source`             |

The edge graph is the primary record, not the clusters. Re-clustering at a different threshold is
then free, and query drift between cluster runs is the earliest available signal that the SERP has
moved.

### Competitors — `doctrine/03-competitors.md`

| Script            | Purpose                                                                                  |
| ----------------- | ---------------------------------------------------------------------------------------- |
| `discover.py`     | Cold-start discovery: domain frequency across a core SERP sweep, weighted share of voice |
| `sitemap_diff.py` | Daily sitemap diff; new and removed URLs. Detection rests on `text_hash`, not `lastmod`  |
| `gap.py`          | Seven gap types with priority. Blocked entries carry `blocked_by`, never dropped         |

`gap.py` keeps rejected entries with their reason attached. A gap that was skipped silently reads
as a gap that does not exist.

### Trends and plan — `doctrine/04-trends-and-plan.md`

| Script                  | Purpose                                                                            |
| ----------------------- | ---------------------------------------------------------------------------------- |
| `gsc_hourly_archive.py` | Archive hourly Search Console data daily; writes `_manifest.json` with gaps        |
| `trend_score.py`        | Robust z-score via median and MAD after de-seasonalization; pure maths, no network |
| `refresh_queue.py`      | Refresh priority, including source-age triggers                                    |

`gsc_hourly_archive.py` must run daily rather than on demand: the hourly window is eight days and
what falls out of it is gone permanently. It is idempotent and exits non-zero when it finds a gap
in the archive, because a silent gap becomes a false seasonal signal a year later.

### Writing — `doctrine/05-writing-core.md`

| Script               | Purpose                                                                   |
| -------------------- | ------------------------------------------------------------------------- |
| `draft_score.py`     | The machine gate: every rule, verdict, evidence, threshold and its origin |
| `ngram_overlap.py`   | N-gram overlap against the current top results                            |
| `entity_coverage.py` | Entity coverage and gain relative to the top                              |
| `rules_lint.py`      | Lints the doctrine itself against seven invariants                        |

`rules_lint.py` is the one script that audits the doctrine rather than the site. It catches a
document prescribing what another forbids, rule IDs referenced in code but missing from the
doctrine, and language packs whose prescribed and forbidden sets intersect. That last case fails
the build: a writer cannot satisfy both.

### Review — `doctrine/06-review-lenses.md`

| Script            | Purpose                                                                      |
| ----------------- | ---------------------------------------------------------------------------- |
| `review_pack.py`  | Assemble the per-lens human review pack. Exits 2 if the machine gate failed  |
| `review_stats.py` | Per-rule fired and overridden counters; reports insufficient samples plainly |

`review_pack.py` refuses to assemble a pack for a draft that failed scoring. Human attention is
the binding constraint on the entire system, and spending it on a document already known unfit
lowers the publishing ceiling for nothing.

`review_stats.py` never edits `doctrine/`. It reports; a human opens the PR.

### Linking — `doctrine/07-linking.md`

| Script               | Purpose                                                                      |
| -------------------- | ---------------------------------------------------------------------------- |
| `graph_build.py`     | Build `corpus.json`, `links.json` and the per-locale anchor registry         |
| `link_suggest.py`    | Candidate donor to target pairs, computable gates only                       |
| `cannibal_detect.py` | Competing pages from Search Console, including leader flip rate              |
| `graph_health.py`    | Orphans, click depth, anchor concentration, topical radius, cluster coverage |

`link_suggest.py` deliberately leaves the semantic gates as `null` for an agent to fill. Whether
reading the target would help someone understand the current paragraph is not a number, and
pretending otherwise is how automated linking produces pages that are all about the same thing and
help nobody.

### Measurement — `doctrine/08-measurement.md`

| Script             | Purpose                                                                    |
| ------------------ | -------------------------------------------------------------------------- |
| `gsc_pull.py`      | Pull Search Console data via API or BigQuery, normalised to JSONL          |
| `analyze.py`       | Cannibalization, striking distance, CTR anomalies, decay, rising, mismatch |
| `ctr_calibrate.py` | Blend the local CTR curve against the prior; marks estimates provisional   |
| `cohort_watch.py`  | Publication cohorts against the pre-Kiln baseline; pauses publishing       |

`cohort_watch.py` exists because no manual action is issued for scaled content abuse. The penalty
arrives silently, so detection has to be cohort-based. It exits non-zero and pauses publishing;
only a human lifts the pause.

`analyze.py` descends from a working `the audited system's analyzer` that operated on Search Console
exports rather than on a site's own database. That is precisely why it transfers between projects
unchanged, and it is the clearest illustration of where layer 2 ends and the adapter begins.

---

## Runtime

Python 3.11 or later. Dependencies install on `SessionStart` into `${CLAUDE_PLUGIN_DATA}`, which
survives plugin updates. `/kiln:doctor` reports whether the runtime and credentials are present.
