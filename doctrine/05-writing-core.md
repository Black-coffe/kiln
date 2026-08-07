# 05. Writing Core — Language-Independent Rules and Draft Scoring

> Subordinate to `00-principles.md`. On conflict, the principles file wins.
> **In scope for this file:** everything that does not depend on language — the pipeline,
> artefact schemas, metrics, thresholds, gates.
> **Out of scope for this file:** the vocabulary, syntax and punctuation of any particular
> language. That lives in `doctrine/lang/<code>.md` and is bound here through the contract in §6.

**Version:** 0.1.0 · **Date:** 2026-08-07 · **Review:** every 90 days
**Implemented by:** `scripts/draft_score.py`, `scripts/ngram_overlap.py`,
`scripts/entity_coverage.py`, `scripts/rules_lint.py`, the `pre-publish` hook

---

## §0. The doctrine is English; the drafts are not

This doctrine is written in English. Every rule, schema, threshold and script contract in
this repository is English, and contributions are expected in English.

**Drafts are never written in the language of the doctrine.** A draft is written in the
language declared for its locale in `.kiln/project.yml`. The writer agent resolves the
locale from `brief.yml` and loads `doctrine/lang/<code>.md` for that locale before it
produces a single word. A project serving three locales runs three language packs and
produces three drafts; it does not produce one draft and translate it, unless the brief
explicitly declares a translation task.

The rules in _this_ file are language-independent and apply unchanged to every language.
Anything that touches vocabulary, syntax or punctuation lives only in the language pack
and **must never be carried across languages**. See §6 for the contract and for the
evidence behind that prohibition.

---

## §1. The text production pipeline

### 1.1. Stages

| #   | Stage        | Executed by                            | Output artefact         | Gate at exit                                           |
| --- | ------------ | -------------------------------------- | ----------------------- | ------------------------------------------------------ |
| 0   | Topic chosen | content plan (`04-trends-and-plan.md`) | `topic` record in queue | topic is not a duplicate (WRT-24)                      |
| 1   | Research     | researcher agent                       | `research_packet.json`  | ≥1 primary source, every link live                     |
| 2   | Brief        | planner agent + **human**              | `brief.yml`             | WRT-01…05, human confirms `unique_value_source`        |
| 3   | Outline      | writer agent                           | `outline.md`            | `answer_intent` covered, anti-cannibalization (WRT-24) |
| 4   | Draft        | writer agent                           | `draft.md`              | —                                                      |
| 5   | Self-check   | **code** `draft_score.py`              | `score.json`            | every BLOCK-level WRT                                  |
| 6   | Edit         | editor agent                           | `draft.md` (rev N)      | re-run `draft_score.py`                                |
| 7   | Review       | **humans**, 4 lenses                   | `review.json`           | `06-review-lenses.md`                                  |
| 8   | Publish      | project adapter                        | URL                     | WRT-60…62                                              |

Stages 5 and 6 loop until a clean run or a rejection. The iteration count is written to
`score.json`: a draft that needed more than three rounds is a signal about the brief, not
about the text, and goes into the review queue (`11-self-learning.md`).

### 1.2. Role contracts

Roles are separated not as a matter of taste but because role blending is the mechanism by
which unverified claims enter a text. Every contract is machine-checkable.

**WRT-R1. The researcher must not write prose.**
The output of stage 1 is structured records only: claim, verbatim quotation, URL, source
publication date, our fetch date, snapshot path. Connected prose must not appear in the
output of stage 1.
`Checked by: code.` No field in `research_packet.json` may hold free text longer than the
`verbatim` quotation.

**WRT-R2. The writer must not go beyond the research packet.**
Every claim about the world in the draft carries a reference to a `claim.id` from the packet.
A claim without a `claim.id` is either an opinion (and must be marked as one) or a violation
of P1.
`Checked by: code + agent.` Code verifies the markup; the agent answers the binary question
"is there a factual claim in this text not bound to a claim.id?".

**WRT-R3. The editor must not add facts.**
The editor deletes, shortens, reorders, rephrases. The set of `claim.id` may only narrow
after editing. Any expansion sends the work back to stage 1.
`Checked by: code.` By diffing the `claim.id` sets before and after.

**WRT-R4. Automated QA must run on a different model family.**
The agent checking a draft must not be the same model that wrote it. A model systematically
fails to see its own blind spots and confidently endorses its own phrasing.
`Checked by: code.` The writer model identifier and the judge model identifier are written to
`score.json` and compared; a family match is a BLOCK.

**WRT-R5. The human must not inherit the machine's verdict.**
The human reviewer at stage 7 is not shown the contents of `score.json` until they have
issued their own verdict for their own lens. Otherwise the independence of the signal that
the fast learning loop (P9) is built on is destroyed.
`Checked by: procedure + adapter UI.`

---

## §2. Artefact schemas

### 2.1. `research_packet.json`

```jsonc
{
  "topic_id": "uk/credit-online-comparison",
  "locale": "uk-UA",
  "created_at": "2026-08-07",
  "claims": [
    {
      "id": "c001",
      "text": "Ставка за кредитною карткою банку X становить 3,9 % на місяць",
      "kind": "figure", // fact | figure | quote | definition | opinion
      "provenance": "third_party", // first_party | third_party
      "artifact_id": null, // required when provenance=first_party
      "source_url": "https://...",
      "source_title": "...",
      "source_published_at": "2026-07-30",
      "source_fetched_at": "2026-08-07T09:12:00Z",
      "source_tier": "primary", // primary | secondary
      "snapshot_path": ".kiln/snapshots/....html",
      "verbatim": "verbatim quotation from the source",
      "http_status": 200,
    },
  ],
  "entity_map": {
    "core": ["…"], // entities present in ≥50 % of top documents — mandatory
    "ours": ["…"], // entities absent from the top — the source of gain
    "absent_ok": ["…"], // top entities we deliberately skip, with a reason
  },
  "top_corpus": [
    { "url": "…", "fetched_at": "…", "words": 0, "entities": ["…"] },
  ],
  "open_questions": ["what could not be established, and why"],
}
```

Note that the claim text is in the locale's language while the schema is in English. This is
the normal case, not an exception: the packet carries source material in the language it was
found in and the language the draft will be written in.

`open_questions` is a required field and must not default to empty. An empty list means the
researcher never looked for the boundaries of their own knowledge; that is a separate signal
into the fast loop.

### 2.2. `brief.yml`

Fields marked `!` are required; their absence blocks the transition to stage 3.

```yaml
topic_id: !  # topic key
locale: !  # bcp-47; determines which language pack is loaded
surface_type:
  !  # article | comparison | glossary | tool | listing
  # derived from intent (see 02-semantics.md)
target: !  # new: <slug> | update: <existing_url>

answer_intent:
  !  # ONE line: the exact question this page answers
  # not a topic, not a keyword — a question
audience: !  # who, and in what situation

unique_value_source:
  ! # WHAT makes this different from the top. enum + description
  kind:
    !  # first_party_data | own_measurement | interview
    # | own_calculation | primary_source_analysis
    # | original_media | proprietary_tool
  description: !
  artifact_id: !  # reference into .kiln/artifacts/ — see §5

originality_asset: # readability alias for artifact_id; stored once
entity_map: !  # copy from research_packet, frozen at brief time
mandated_proof_sources:
  !  # claim.id values that MUST be cited
  # (regulator, primary source of a figure, official document)
cannibalization_check: ! # result of the run against the corpus
  max_cosine: !
  nearest_url: !
  decision:
    !  # new_page | extend_existing | merge | redirect
    # extend_existing when max_cosine exceeds the threshold — not a new page
forbidden: !  # project taboos applicable to this topic (from project.yml)
reviewers: !  # which lenses are mandatory (06-review-lenses.md)
required_blocks: # table / procedure / calculation / diagram — what must be present
volume_expectation: # an ESTIMATE in words, not a target. See §4. May be absent.
```

**What is genuinely new here relative to a conventional "content brief":**
`answer_intent` is phrased as a question rather than a topic, because WRT-30 (time to answer)
cannot be computed otherwise; `unique_value_source` is not accepted without an `artifact_id`;
`cannibalization_check` runs **before** writing rather than a week later from search data,
and its `extend_existing` outcome cancels the new page entirely.

---

## §3. Draft scoring

Notation: `D` is the draft, `T` is the top-N corpus for the target query (N = 10 by default),
`E(x)` is the set of normalized named entities in a document.

Every threshold marked `[expert judgement, needs calibration]` is taken from the literature and
is **not calibrated**. The first run on a project must collect the distributions for its niche
and write local values into `.kiln/thresholds.yml` (P10: thresholds are local and are not
promoted into the shared doctrine).

### Group A — input and intent

| ID         | What is checked                                                                  | Threshold                         | Sev   | Computed by    |
| ---------- | -------------------------------------------------------------------------------- | --------------------------------- | ----- | -------------- |
| **WRT-01** | `brief.yml` contains every `!` field                                             | 100 % complete                    | BLOCK | code           |
| **WRT-02** | `unique_value_source.kind` is in the allowed enum and `description` is non-empty | —                                 | BLOCK | code           |
| **WRT-03** | `artifact_id` exists in `.kiln/artifacts/` and its manifest is valid             | —                                 | BLOCK | code           |
| **WRT-04** | Neither brief, prompt nor rules contain a word-count requirement                 | occurrences = 0                   | BLOCK | code           |
| **WRT-05** | The topic does not violate a project taboo from `forbidden`                      | —                                 | BLOCK | agent (binary) |
| **WRT-06** | The language pack loaded for this locale satisfies the §6 contract               | defects = 0 [source: §6 contract] | WARN  | code           |

WRT-04 is treated separately in §4.

Why this rule exists: **a malformed pack fails silently.** A pack that misnames its item key still
parses as valid YAML and still looks healthy; every consumer reading the contract simply sees an
empty set and reports nothing. The finding therefore has to come from the loader, which is the only
component that can tell "no matches" from "no rules were read". Severity is WARN rather than BLOCK
because a pack defect is our fault, not the draft's, and blocking the draft punishes the wrong
artefact. It is a WARN that must never be waved through: a clean run against a pack that loaded
nothing is indistinguishable from a clean run against a working one.

### Group B — claim provenance

| ID         | Metric                           | Formula                                                     | Threshold                                                                            | Sev   | By           |
| ---------- | -------------------------------- | ----------------------------------------------------------- | ------------------------------------------------------------------------------------ | ----- | ------------ |
| **WRT-10** | Claims outside the packet        | `count(claims without claim.id)`                            | `= 0`                                                                                | BLOCK | code + agent |
| **WRT-11** | Share of facts carrying a source | `sourced / factual_claims`                                  | `≥ 0.85`; YMYL `= 1.00` [source: EVIDENCE.md#e11-content-quality-signals]         | BLOCK | code + agent |
| **WRT-12** | Share of primary sources         | `PSR = primary / all_sources`                               | `≥ 0.50` [expert judgement, needs calibration]                                       | WARN  | code         |
| **WRT-13** | Link liveness                    | share of 2xx at publication time                            | `= 1.00` [internal observation, unpublished: owner mandate]                | BLOCK | code         |
| **WRT-14** | Date consistency                 | \|`bylineDate` − semantic date\|                            | `≤ 90 days` [expert judgement, needs calibration; basis: `semanticDate` in the leak] | WARN  | code         |
| **WRT-15** | Freshness of external facts      | age of source for volatile values (price, tariff, rate, UI) | `≤ 30 days` [expert judgement, needs calibration]                                    | BLOCK | code + agent |
| **WRT-16** | Mandated sources are cited       | `mandated_proof_sources ⊆ used`                             | 100 % complete                                                                       | BLOCK | code         |
| **WRT-17** | Identifier validity              | DOI/ISBN pass their checksum                                | `= 100 %`                                                                            | BLOCK | code         |

**WRT-15 — why it is separate from WRT-13.** A link can return 200 and lead to a page where the
price changed yesterday. The mandate wording transfers verbatim:

> Model knowledge lags by 6–12 months; an external fact — a price, a plan name, a tool's
> interface, a condition — may have changed **yesterday**. Verify against a live source dated
> close to today, preferring the vendor's primary source over a third-party blog. Any hard
> claim without a current source is a **blocker of the same severity as a fabrication**.

### Group C — gain and originality

| ID         | Metric                            | Formula                                                                                 | Threshold                                                                                                   | Sev                        | By   |
| ---------- | --------------------------------- | --------------------------------------------------------------------------------------- | ----------------------------------------------------------------------------------------------------------- | -------------------------- | ---- |
| **WRT-20** | Original claim density `OCD`      | `count(claims where provenance=first_party) / (words/1000)`                             | `≥ 2.0`; `= 0` is a BLOCK [expert judgement, needs calibration; EVIDENCE.md#e11-content-quality-signals] | BLOCK at 0, otherwise WARN | code |
| **WRT-21** | Entity gain `EG`                  | `\|E(D) \ E(T)\| / \|E(D)\|`                                                            | `≥ 0.15`; `< 0.08` is a BLOCK [expert judgement, needs calibration]                                         | BLOCK/WARN                 | code |
| **WRT-22** | Core coverage `EC`                | `\|E(D) ∩ E_core(T)\| / \|E_core(T)\|`, where `E_core` are entities in ≥50 % of the top | `0.70 ≤ EC ≤ 0.90` [expert judgement, needs calibration]                                                    | WARN on both sides         | code |
| **WRT-23** | N-gram overlap with the top `NGO` | `max_{t∈T} \|8gram(D) ∩ 8gram(t)\| / \|8gram(D)\|`                                      | `≤ 0.03` [expert judgement, needs calibration]                                                              | BLOCK                      | code |
| **WRT-24** | Cannibalization risk `CR`         | `max_{p∈site} cos(emb(D), emb(p))`                                                      | `≤ 0.85` [expert judgement, needs calibration]                                                              | BLOCK                      | code |
| **WRT-25** | Drift from the site core          | `cos_dist(emb(D), centroid(site))`                                                      | `≤ 0.45` [expert judgement, needs calibration; basis: `siteRadius`]                                         | WARN                       | code |
| **WRT-26** | Filler ratio `WPC`                | `words / claims_total`                                                                  | `≤ 250` [expert judgement, needs calibration]                                                               | WARN                       | code |

**WRT-22 reads in both directions, and this is the central difference between Kiln and the
commercial optimizers.** Coverage below 0.70 means the topic is not covered. Coverage above
0.90 means we have paraphrased the top, and raises an over-optimization warning. The upper
bound exists because vendor scores measure similarity to the top, whereas what is needed is
gain relative to it (P3, P13).

**WRT-24 runs twice:** at stage 2 against the corpus (the "write or extend" decision) and at
stage 5 against the final draft. The first run is cheaper and prevents writing a page that
cannot be published.

### Group D — structure and extractability

| ID         | Metric                                                                                                                     | Threshold                                                                                            | Sev   | By                                            |
| ---------- | -------------------------------------------------------------------------------------------------------------------------- | ---------------------------------------------------------------------------------------------------- | ----- | --------------------------------------------- |
| **WRT-30** | Time to answer: position of the first sentence that answers `answer_intent`                                                | `≤ 60 words` from the start of the main content [expert judgement, needs calibration]                | WARN  | code + agent (binary "is this the answer?")   |
| **WRT-31** | Passage self-sufficiency `PSS`: share of sections whose first paragraph is comprehensible without the rest of the document | `≥ 0.90` [expert judgement, needs calibration]                                                       | WARN  | agent (binary, one paragraph without context) |
| **WRT-32** | Anaphora at section start: the first sentence opens with a back-reference                                                  | `= 0`                                                                                                | BLOCK | code + list from `lang/<code>`                |
| **WRT-33** | Priority material in the first third: mandatory entities and the main conclusion appear within the first 30 % of the text  | `E_core` coverage in the first third `≥ 0.60` [expert judgement, needs calibration]                  | WARN  | code                                          |
| **WRT-34** | Structural variety: table / numbered procedure / calculation / original diagram                                            | `≥ 2` distinct block types for material longer than 1200 words [expert judgement, needs calibration] | WARN  | code                                          |
| **WRT-35** | Heading hierarchy with no skipped levels                                                                                   | skips `= 0`                                                                                          | WARN  | code                                          |

### Group E — form statistics

Computed only over sentences outside quotations, code and tables. Tokenization must be
unicode-aware (P5): `wc -w` and any whitespace split are forbidden.

| ID         | Metric                                                    | WARN threshold                                                                               | By   |
| ---------- | --------------------------------------------------------- | -------------------------------------------------------------------------------------------- | ---- |
| **WRT-40** | σ of sentence length (in words)                           | `< 6.0` [expert judgement, needs calibration; EVIDENCE.md#e03-ai-detection-and-humanization] | code |
| **WRT-41** | Share of sentences 12–22 words long                       | `> 65 %` [expert judgement, needs calibration]                                               | code |
| **WRT-42** | Share of paragraphs of identical length ±1 sentence       | `> 60 %` [expert judgement, needs calibration]                                               | code |
| **WRT-43** | Repeated sentence openings (first 2 words)                | `> 12 %` [expert judgement, needs calibration]                                               | code |
| **WRT-44** | Type-token ratio over a 500-word window                   | `< 0.38` [expert judgement, needs calibration]                                               | code |
| **WRT-45** | Consecutive lists with no prose bridge                    | `> 2`                                                                                        | code |
| **WRT-46** | Share of lists with exactly three items ("rule of three") | `> 50 %` [expert judgement, needs calibration]                                               | code |

Group E is **secondary diagnostics** (P4). It catches traces of carelessness; it does not create
quality and it must never block publication. A draft that is clean on group E and empty on
group C is a bad draft.

### Group F — machine traces

Language-independent, near-zero false positive rate.

| ID         | What                                                                                                                                                                                             | Sev   |
| ---------- | ------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------ | ----- |
| **WRT-50** | Tool markers: `contentReference`, `oai_citation`, `turn\d+search\d+`, `attributableIndex`, `[cite: N]`, `[span_N](start_span)`, `grok_card`, `ppl-ai-file-upload`, `attached_file`, `:::writing` | BLOCK |
| **WRT-51** | Generator UTM tails: `utm_source=chatgpt.com`, `utm_source=openai`, `utm_source=perplexity`                                                                                                      | BLOCK |
| **WRT-52** | Invisible characters: zero-width, `U+202F`, `U+00AD` outside the permitted list                                                                                                                  | BLOCK |
| **WRT-53** | Markdown leaking into a CMS that expects different markup                                                                                                                                        | BLOCK |

### Group G — process

| ID         | What                                                                | Sev   | By   |
| ---------- | ------------------------------------------------------------------- | ----- | ---- |
| **WRT-60** | The human review log is complete for every mandatory lens           | BLOCK | code |
| **WRT-61** | Writer model family ≠ judge model family (WRT-R4)                   | BLOCK | code |
| **WRT-62** | Publication does not exceed the pace declared in `project.yml` (P2) | BLOCK | code |

### Composite gate

```
BLOCK  ⟸  any of: WRT-01..05, 10, 11, 13, 15, 16, 17,
                  20 (when OCD=0), 21 (when EG<0.08), 23, 24,
                  32, 50..53, 60..62
REWORK ⟸  ≥ 2 WARN rules triggered
PASS   ⟸  everything else
```

A counter for every rule (how many times it fired, how many times a human overrode the verdict)
is written to `.kiln/rules-stats.json` — this is the input to P8 and to the fast loop of P9.

---

## §4. Length: why word-count targets are forbidden

**WRT-04, severity BLOCK.** Neither the brief, nor the writer's prompt, nor the rules may
contain "minimum N words", "optimal length", or "2000–3000 words".

The basis is direct: in its helpful-content document Google lists **"writing to a particular
word count"** among the signals of content made for a search engine rather than for a person
(document updated 2025-12-10). That is the same list against which core updates are calibrated.

The owner's existing system violates this rule: `lp-copywriting-rules §17` sets "1900+ word
minimum (2900+ for competitive topics)" and "2000–3000 words = sweet spot". The rule is
deleted, not softened.

**What replaces it.** Length becomes a consequence and is measured from above, not from below:

| Instead of                     | We set                                                                                                                                                          |
| ------------------------------ | --------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| "at least 1900 words"          | WRT-22: core entity coverage `≥ 0.70`                                                                                                                           |
| "2000–3000 is the sweet spot"  | WRT-26: `words / claims ≤ 250` — the filler check                                                                                                               |
| "2900+ for competitive topics" | WRT-21: entity gain `≥ 0.15`                                                                                                                                    |
| —                              | `volume_expectation` in the brief as a **forecast**; a ±40 % divergence from actual raises a WARN, because that is a signal about the brief, not about the text |

The difference is operational, not philosophical. A floor requirement makes the writer pad to
length and directly raises `WPC`. A ceiling check makes the writer find more facts.

---

## §5. The effort-invested gate

This is the enforcement of P13. Without it `unique_value_source` degenerates into a field the
model fills with confident text.

### 5.1. The rule

**No claim receives `provenance: first_party` unless it carries an `artifact_id` pointing at a
file in `.kiln/artifacts/`.** WRT-20 counts only such claims. No artefact means `OCD = 0`,
which is a BLOCK.

### 5.2. Artefact types

| Type              | What is deposited                                                                               | Reproducible by a competitor |
| ----------------- | ----------------------------------------------------------------------------------------------- | ---------------------------- |
| `export`          | an export from our own system (Search Console, CRM, product), CSV/JSON                          | impossible                   |
| `measurement`     | measurement log, timings, screenshots of the process                                            | expensive                    |
| `interview`       | transcript with attribution and date                                                            | low                          |
| `survey`          | raw responses, `n ≥ 100`                                                                        | low                          |
| `calculation`     | spreadsheet with source data and a documented method                                            | medium                       |
| `primary_reading` | verbatim quotations from a primary source plus a statement of what had not been examined before | medium                       |
| `original_media`  | our own diagram, chart, photograph, screenshot                                                  | medium                       |

Cheapest at high return: `primary_reading` and `original_media`. Most defensible: `export` —
it cannot be reproduced in principle, and it exists for every product that has users.

### 5.3. Artefact manifest

```yaml
artifact_id: a-2026-08-07-001
kind: export
created_at: 2026-08-07
created_by: <human> # not an agent; an agent cannot originate first-party material
files: [".kiln/artifacts/a-.../gsc-export.csv"]
sha256: [...]
method: "how it was obtained, one paragraph"
claims: ["c014", "c015"] # which claims rest on it
```

### 5.4. What the code checks and what it cannot

`Code checks:` the file exists, the hash matches, `created_by` is a human, every `first_party`
claim references an existing `artifact_id`, and the figures in the text occur in the artefact file.

`Code does not check and cannot:` that the measurement actually took place, that the export was
not doctored, that the interview happened. **This is the point where a human is mandatory**, and
it is also the boundary of the framework's responsibility. Kiln guarantees that the claimed
first-party material is attached, not that it is authentic.

---

## §6. The language pack contract

The mechanism that makes the defect "one phrase simultaneously prescribed and forbidden"
impossible (see §9.2).

**Scope reminder.** This doctrine is English. Drafts are written in the locale language declared
in `.kiln/project.yml`, and the writer loads `doctrine/lang/<code>.md` for that locale. Rules in
this file apply to every language unchanged. Rules about words, syntax or punctuation exist only
inside a pack and must never be copied from one pack to another.

Two pieces of evidence make that prohibition concrete rather than stylistic:

- **Dash density is a valid English signal and is grammatically wrong for Cyrillic.** A high
  em-dash rate is a legitimate English AI tell; in Ukrainian and Russian the dash is
  grammatically obligatory in the copular construction ("Х — це У"), so the same rule mangles
  correct text. A previous transfer of this rule converted 349 correct dashes into commas.
- **Word counting must be unicode-aware.** `wc -w` does not split Cyrillic into words. On a live
  measurement it reported an English locale as six times larger than the Ukrainian one when the
  two were in fact at parity — the conclusion was inverted. Any module that measures text length
  must tokenize with unicode awareness (P5).

Every `doctrine/lang/<code>.md` file must declare named sets under fixed keys. The core
references them by key and knows nothing of their contents.

| Key                      | Contents                                        | `forbidden` | Used by                    |
| ------------------------ | ----------------------------------------------- | ----------- | -------------------------- |
| `anaphora_openers`       | back-referencing sentence openings              | `true`      | WRT-32                     |
| `hedge_phrases`          | didactic hedges                                 | `true`      | WARN rules inside the pack |
| `closing_formulas`       | formulaic endings                               | `true`      | same                       |
| `promo_lexicon`          | promotional clichés                             | `true`      | same                       |
| `vague_attribution`      | vague source attributions                       | `true`      | reinforces WRT-11          |
| `generational_stopwords` | stop-lexicon with a `generation` field and date | `true`      | same                       |
| `prescribed_phrases`     | phrases the pack **recommends**                 | `false`     | writer prompt              |

A pack may declare **additional sets of its own** beyond these seven. The Ukrainian pack, for
example, needs a russism set that no other language has. Every set, named or pack-local, must carry
an explicit `forbidden: true|false` flag.

### Set keys and item shape

The key names are contract, not preference. A set lists its entries under `items:`, and each entry
names its surface form under `phrase:`. A pack that invents its own key names still parses as valid
YAML, still looks healthy on inspection, and delivers an **empty set** to every consumer reading the
contract. That failure produces no error and no output — the pack simply stops having opinions, and
a clean run against it is indistinguishable from a clean run against a working pack. WRT-06 exists
to make it visible.

```yaml
<set_key>:
  rule_id: LANG-XX-NN # required, see below
  forbidden: true|false # required
  updated_at: YYYY-MM-DD # required
  next_review: YYYY-MM-DD # required
  severity: BLOCK|WARN|INFO # optional; capped in code regardless of what is written here
  default_status: hypothesis # optional; entry-level `status` overrides it
  density_warn_per_1000: null # optional; required for `match_mode: density` to fire
  applies_to: section_first_sentence # optional scope restriction
  never_applies_inside: [quotation, code, cited_verbatim] # optional span exemptions
  items:
    - phrase: "" # required: the surface form, or a short label for a pattern
      risk: critical|high|medium|low
      status: hypothesis|observed|calibrated|deterministic
      match: "" # optional: the pattern actually applied; defaults to `phrase`
      match_mode: phrase|density|regex # optional; defaults to `phrase`
      named_check: "" # optional; see "Checks that cannot be regexes"
      severity: WARN # optional per-entry downgrade; never an upgrade
      note: "" # required for risk: critical and risk: high
      replacements: [] # optional
```

**`match_mode` is load-bearing and is not decoration.** `phrase` judges by presence; `density`
judges by frequency per 1,000 words and **never** by presence. Ordinary words that models
over-produce — `demonstrates`, `забезпечує`, `надійний` — must be `density`, because banning them by
presence bans ordinary language. A pack that loses this distinction has become the calque problem it
was written to prevent.

A `density` entry with no `density_warn_per_1000` on its set is reported and never warned. That is
the correct behaviour for an uncalibrated locale: measuring is honest, warning against an unmeasured
threshold manufactures confidence that does not exist.

**Density is meaningless on short text.** One occurrence in 120 words is 8.3 per 1,000 and trips a
threshold of 5 — which converts a frequency rule back into a presence rule, precisely the failure
`density` exists to prevent. Below `lang.density_min_words` (default 300, calibratable) a rate is
recorded and never compared against a threshold.

### Rule identifiers

**Every set declares a `rule_id`.** Findings from a pack are findings like any other: they are
counted in `.kiln/rules-stats.json`, they carry override rates, and P8 turns those counters into
decisions about which rules survive. An identifier synthesised at runtime from a set key cannot be
counted, because nothing outside the code that invented it knows the identifier exists.

Format: `LANG-<LOCALE>-<NN>`. The locale segment is uppercase and must equal the pack's own
`lang.code`; the number is zero-padded and assigned in declaration order on first publication.

**An identifier is immutable once published.** If a set's meaning changes, it receives a new
identifier and the old one is retired. Reusing an identifier for a changed rule corrupts every
counter that spans the change, and it does so silently: the rule appears to have a long history of
overrides when in fact two different rules have been sharing a name. This is the same rule that
governs core identifiers in `11-self-learning.md`, applied to packs.

### Checks that cannot be regexes

Some deterministic facts are not expressible as a pattern over a character stream, and writing one
anyway produces a rule that compiles, passes review, and can never fire.

The recorded case: `\b(?=\p{Cyrillic})(?=\p{Latin})\S+\b`, intended to catch Latin homoglyphs inside
Cyrillic tokens. Two lookaheads at the same position demand that a **single character** belong to
two scripts at once. The pattern is well-formed and its match set is empty. Homoglyph substitution
is a property of a **token**, not of a character, so no lookahead formulation can express it.

An entry that needs such a check declares `named_check: <name>` instead of `match:`, and the scorer
resolves the name against its registry. **An unrecognised name is a pack defect, never a silent
skip** — the whole point of the mechanism is that a check which cannot run says so.

| Name                 | What it detects                                                         |
| -------------------- | ----------------------------------------------------------------------- |
| `mixed_script_token` | a single word whose characters span two scripts (Latin inside Cyrillic) |

A rule that compiles and cannot match is worse than a missing rule. A missing rule is visible; a
dead one reports success forever. Any pattern added to a pack must be demonstrated to fire on a
constructed positive case before it is merged.

**Invariant checked by `rules_lint.py`:**

```
prescribed_phrases ∩ ( ⋃ every set where forbidden: true ) = ∅
```

The union is computed over **all** forbidden sets present in the pack, not over a fixed list of
five. A fixed list cannot see a pack-local set, so a pack could prescribe a phrase its own russism
set forbids and the build would pass — reintroducing exactly the defect this contract exists to
prevent (§9.2), just one level deeper.

A non-empty intersection is a doctrine build error, not a matter for discussion. The writer
prompt and the reviewer rules are generated from the same file, so they cannot diverge.

**Entry status.** Every lexical entry carries a `status`:

| Status          | Meaning                                                                      |
| --------------- | ---------------------------------------------------------------------------- |
| `hypothesis`    | reasoned by analogy or judgement; never measured in this language            |
| `observed`      | seen in this language's corpus, not yet quantified                           |
| `calibrated`    | a distribution exists for this language and the threshold derives from it    |
| `deterministic` | not a statistical claim at all — a fact about the writing system or encoding |

`deterministic` exists because the other four are all statistical, and some entries are not. A letter
absent from a language's alphabet appearing in its text, a Latin homoglyph inside a Cyrillic token, a
zero-width character, mojibake: these are facts, and calling them hypotheses would be false. Only
`deterministic` entries may carry `BLOCK`; everything stylistic is capped at `WARN` by the severity
scale in `00-principles.md`, and at `INFO` until calibrated.

Every set carries `updated_at` and `next_review`. A pack with an overdue review raises a WARN on
every run: stop-lexicon is tied to model generations and goes stale within months.

---

## §7. Binary verdicts instead of scales

The judge agent does not assign scores on a scale. Scales drift between runs in language models
and make the feedback link "rule → outcome" impossible. The judge answers **yes/no** to a
specific question and supplies a quotation from the text as justification.

The question wording is part of the doctrine, because the wording determines the verdict.

| Rule   | Question to the judge                                                                                        | Answer format        |
| ------ | ------------------------------------------------------------------------------------------------------------ | -------------------- |
| WRT-05 | "Does this text violate at least one of the listed project prohibitions? Quote it."                          | `yes/no` + quotation |
| WRT-10 | "Is there a factual claim about the world in this text that is bound to no claim.id? Quote the first one."   | `yes/no` + quotation |
| WRT-11 | "Is this sentence a factual claim rather than an opinion or an assessment?" (per candidate)                  | `yes/no`             |
| WRT-15 | "Can the value named here change within a month?"                                                            | `yes/no`             |
| WRT-30 | "Does this sentence answer the question: `<answer_intent>`? Not 'is related to the topic' — answers it."     | `yes/no`             |
| WRT-31 | "Here is one paragraph without context. Is it clear what it is about, and does it contain a complete claim?" | `yes/no`             |
| §5.4   | "Does this figure from the text occur in the attached artefact file?"                                        | `yes/no` + file line |

Rules for composing questions: one decision per question; never "rate the quality"; negative
phrasing where scrutiny is required ("is there a violation" rather than "is everything fine");
a mandatory quotation so the verdict can be checked and contested.

---

## §8. What cannot be automated

Six points where neither code nor agent produces a trustworthy result. Attempting to automate
them is the principal failure mechanism of content factories.

1. **Whether the first-hand experience actually happened.** An agent will verify the presence of
   the phrase "we tested" but not the fact of the test. Partially closed by the artefact gate
   (§5): the framework guarantees attachment, not authenticity.
2. **Whether the conclusion drawn from a source is correct.** WRT-11 checks that a source exists,
   not that the inference is sound. A mistaken interpretation of a correct figure passes every gate.
3. **Whether this is useful to this particular audience.** Proxies appear after the fact and are noisy.
4. **Whether the author's authority is real.** A synthetic author is a direct violation and the
   principal long-term risk for YMYL.
5. **Editorial fakery.** Polished emptiness is systematically missed by an LLM editor, because
   the LLM editor is what produces it.
6. **Whether the reader's task was closed well enough that they stopped searching.** Before
   publication this is expert judgement only.

Points 1, 4 and 6 are closed by the review lenses (`06-review-lenses.md`); points 2 and 5 by the
subject-matter lens; point 3 by the medium learning loop (P9).

---

## §9. Audit of a production content system

Source: an existing in-house content system, audited with the owner's permission. Three canonical
rule documents totalling roughly 4,200 lines, 21 published articles, and a live Search Console
loop. It is the only system available to us that has been tested in production, which is why its
defects are worth more here than its successes. `[internal observation, unpublished]`

### 9.1. Transfers verbatim

| What                                                                                                                                                                                                                                                                               | Where to                           | Why                                                                                 |
| ---------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- | ---------------------------------- | ----------------------------------------------------------------------------------- |
| External-fact freshness gate, severity BLOCK                                                                                                                                                                                                                                       | WRT-15                             | A ready editorial formulation of P1                                                 |
| Zero-fabrication policy                                                                                                                                                                                                                                                            | WRT-10, WRT-20                     | Short, unambiguous, checkable                                                       |
| Specification of a "real" case study: unrounded numbers, what **did not** work, how many did not respond, how much took longer than expected                                                                                                                                       | §5.2 `measurement`, the voice lens | Such details cannot be synthesized, only possessed                                  |
| Mandatory acknowledgement of product and competitor limitations                                                                                                                                                                                                                    | the product-truth lens             | A model will not write against its own product by default — near-impossible to fake |
| The split between a "positive playbook" and a "negative checklist"                                                                                                                                                                                                                 | `05` + `lang/*`                    | The writer reads the first, the reviewer the second; they do not blur each other    |
| The "nothing auto-publishes" rule and the three action tiers                                                                                                                                                                                                                       | `08-measurement.md`, WRT-60        | The best separation of automation and accountability found                          |
| Publication as code: explicit fields, a pass through the application's real sanitizer, verification that structured blocks extract correctly before sending, idempotency by slug, PUT of the changed field only, draft + localhost defaults, credentials from the environment only | `adapter/SPEC.md`                  | A ready adapter template                                                            |

### 9.2. Three defects, examined on request

**Defect 1. Optimizing for perplexity — discard entirely.**

Was (`ai-content-stop-rules §4.1`, `§9.2`): "Make unexpected word choices… Avoid the 'obvious'
word", Shannon entropy "human 4–5 bits/character; AI often <3".

Why it cannot stand: contemporary detectors do not rely on perplexity — this was shown by a
direct re-examination of the old assumption across three detector families
(arXiv:2602.05769, 2026-02-06): _"contemporary detectors operate effectively without relying on
perplexity"_. The technique optimizes for a dead metric. Worse, it conflicts with a neighbouring
rule in the same document, `§1.1 "Clarity Over Creativity"` and `§1.3 "every word must earn its
place"` — the writer is simultaneously asked to choose non-obvious words and to write as plainly
as possible.

Replacement: **WRT-40** (σ of sentence length), **WRT-43** (repeated openings), **WRT-44** (TTR).
These are computable quantities, they were already present in the owner's rules and they are
valid. Word choice is not touched at all.

Doctrine wording: _"The rhythm of a text is measured by the spread of sentence lengths and the
variety of sentence openings. The choice of an individual word is not subject to automated
checking: the rule 'avoid the obvious word' optimizes for a metric that 2026 detectors do not
rely on, and contradicts the requirement of clarity."_

**Defect 2. Mutual contradiction between two canonical documents.**

Was: `lp-copywriting-rules §13.11` prescribes conversational interjections and gives
**"But here's the thing…"** among its examples. `ai-content-stop-rules` forbids "Here's the
thing…" twice — in `§1.5` (clichés) and `§3.5` (bridges). One phrase sits in the prescribed and
the forbidden list at the same time. The writer cannot resolve this, and the review verdict
becomes a lottery.

Why it happened: two free-form markdown documents, no machine intersection of sets, nobody counting.

Replacement: **the contract in §6** — phrase sets are machine-readable, live in one file per
language, and `rules_lint.py` checks the invariant `prescribed ∩ forbidden = ∅` and fails the
doctrine build on any intersection. The writer prompt and the reviewer rules are generated from
one source.

Doctrine wording: _"A phrase cannot be simultaneously recommended and forbidden. An intersection
of the sets is a build error discoverable before the run, not a difference of opinion discoverable
in the verdict."_

**Defect 3. Minimum word count.**

Was (`§17`): "1900+ word minimum (2900+ for competitive topics)", "Minimum 1500+ words for
competitive keywords", "2000–3000 words = sweet spot".

Why it cannot stand: see §4. A direct red flag from Google's official list.

Replacement: **WRT-04** forbids such requirements in the brief and the prompt; **WRT-22**
(coverage as a floor), **WRT-26** (filler) and **WRT-21** (gain) take its place;
`volume_expectation` remains as a forecast with a two-sided tolerance.

Doctrine wording: _"Length is a consequence of topic coverage and claim density. A floor
requirement makes the writer pad; a ceiling check makes the writer find facts. A length forecast
is permitted in the brief; a length requirement is not."_

### 9.3. Everything else that gets rebuilt

| Defect                                                                                                              | Replacement                                                                                            |
| ------------------------------------------------------------------------------------------------------------------- | ------------------------------------------------------------------------------------------------------ |
| Rules are English-only; the "em-dash density is an AI tell" rule mangles Cyrillic                                   | P5 + the §6 contract: a language-independent core, with independent packs per language                 |
| The stop-word list is static and its `Next Review` is five months overdue                                           | `generational_stopwords` with `generation`, `updated_at`, `next_review`; an overdue review raises WARN |
| The strategic layer has gone stale (dead schema types listed as "best", refuted correlations)                       | dated and re-measurable claims; `09-geo.md` with a "verified on" field                                 |
| Not a single computed metric; everything by agent eyeball                                                           | groups C, D and E are computed by code; the agent is left only the binary judgements of §7             |
| The gate is advisory and the hook was never built                                                                   | `hooks/pre-publish` physically refuses to pass a BLOCK                                                 |
| Internal linking is a hand-written dictionary of four pairs                                                         | `07-linking.md`                                                                                        |
| The evidence gate exists in the rules but not in the code: no snapshots, no HTTP check, no claim → URL → date store | `research_packet.json` §2.1 + WRT-13 + `.kiln/snapshots/`                                              |
| Semantics is a one-off manual export                                                                                | `02-semantics.md`                                                                                      |
| The admin guide and the writing rules diverged: the heading example in the guide violates its own stop-list         | the single source of §6; examples are generated from the rules rather than written alongside           |

### 9.4. What we take from the failures

The owner's documents record negative results, and that is worth more than half of the positive
ones: _"The weekly calendar didn't survive contact. It ran for one week and stopped"_ — and the
honest admission that the domain is six months old, that a position around 56 is expected, that
this is not a fixable page defect, and that leading indicators rather than clicks are what should
be measured.

Both are carried over: the first into P2 (pace equals verification capacity, not plan), the second
into `08-measurement.md` as a reporting rule. The practice of recording failures in the same
document that holds the rules becomes mandatory (P15).

---

## §10. Layer 2 script specifications

Common requirements for all of them: no network access (except where explicitly stated), no
knowledge of any specific project, files in and files out, determinism given identical input,
unicode-aware tokenization (P5), JSON on stdout, non-zero exit code on BLOCK.

### `draft_score.py`

```
Input:
  --draft      path      markdown or html of the draft
  --brief      path      brief.yml
  --packet     path      research_packet.json
  --corpus     path      .kiln/corpus.json (for WRT-24, WRT-25)
  --top        path      directory of top-N snapshots (for WRT-21..23)
  --lang       path      doctrine/lang/<code>.md
  --thresholds path      .kiln/thresholds.yml (overrides doctrine defaults)
Output: score.json
  { "verdict": "PASS|REWORK|BLOCK",
    "iteration": 2,
    "writer_model": "...", "judge_model": "...",
    "rules": [ { "id":"WRT-21", "value":0.11, "threshold":0.15,
                 "severity":"WARN", "status":"fail",
                 "evidence":["..."], "computed_by":"code" } ],
    "blocked_by": ["WRT-20"] }
Exit code: 0 PASS · 1 REWORK · 2 BLOCK
```

Orchestrator: invokes `ngram_overlap.py` and `entity_coverage.py`, computes groups D, E, F and G
itself, and calls the judge agent with the questions from §7.

### `ngram_overlap.py`

```
Input:  --draft path  --top path  [--n 8]  [--normalize lemma|surface]
Output: { "max_overlap": 0.021, "per_document": [ {"url":"...","overlap":0.021,
          "samples":["the matched 8-gram", ...] } ] }
```

Normalization defaults to `surface`; lemmatization is an option for inflected languages.
Comparison is over sets, not sequences: the goal is to catch paraphrase, not borrowed ordering.

### `entity_coverage.py`

```
Input:  --draft path  --top path  [--min-doc-freq 0.5]  [--aliases path]
Output: { "entity_gain": 0.19,
          "entity_coverage": 0.78,
          "core_entities": ["..."],       # document frequency in the top ≥ min-doc-freq
          "missing_core": ["..."],
          "our_entities": ["..."],        # absent from the top
          "first_third_coverage": 0.64 }  # for WRT-33
```

`--aliases` is a dictionary of synonyms and spellings; without it "Національний банк" and "НБУ"
count as different entities and `entity_gain` is inflated. For Cyrillic, matching must be
case-insensitive **with unicode-aware case folding**, and word boundaries must not be determined
via `\b`.

### `rules_lint.py`

P8 applied to the doctrine itself. Runs in the Kiln repository's CI and during onboarding.

```
Input:  --doctrine path   the doctrine/ directory
Checks:
  1. prescribed_phrases ∩ (⋃ all sets with forbidden: true) = ∅ in every language
     pack (§6). The union is computed over every forbidden set present in the pack,
     including pack-local ones, not over a fixed list.
  2. every WRT-* rule has: a threshold, a severity, an executor, and either a
     [source] or an [expert judgement] marker
  3. no two rules share an ID
  4. every rule referenced in the composite gate exists
  5. next_review is not overdue
  6. every numeric claim in the doctrine carries a source marker
  7. rule IDs occurring in scripts/ exist in the doctrine, and vice versa
  8. no threshold key is stated with two different values in two doctrine files.
     Each key has one canonical home; a restatement elsewhere must either match
     exactly or be a reference rather than a value.
  9. only entries with status: deterministic carry BLOCK severity inside a language
     pack; stylistic entries are capped at WARN (00-principles.md, severity scale)
 10. every set in a language pack declares forbidden: true|false, and every lexical
     entry resolves a status from {hypothesis, observed, calibrated, deterministic},
     either on the entry or via a set-level default_status
 11. a bare P<number> reference resolves to a principle in 00-principles.md;
     identifiers borrowed from intel reports must carry their source prefix
 12. every language pack set declares a rule_id of the form LANG-<LOCALE>-<NN>;
     identifiers are unique across the doctrine and the locale segment matches the
     pack's own lang.code. Pack-declared identifiers count as definitions for
     check 7, so a script emitting LANG-UK-01 resolves.
Output: { "errors": [...], "warnings": [...] }
Exit code: 0 clean · 2 errors. Warnings alone exit 0.
```

**Warnings do not fail the build, and that is deliberate.** An exit code that fires on warnings
makes the pipeline permanently red, and a permanently red pipeline stops being read — which costs
more than the warnings were worth. It also collides with the shared convention that exit 1 means the
script could not complete: a crash and a warning must not be indistinguishable to a caller.

Check 1 is the direct defence against defect 9.2-2. Check 7 catches divergence between doctrine
and code — precisely what caused the owner's admin guide to drift away from its own stop-list.
Check 8 is the same defence applied to numbers rather than phrases: a threshold copied into two
files drifts apart silently, which is how `06-review-lenses.md` and `11-self-learning.md` came to
hold the same four counters twice. Check 11 keeps principle IDs unambiguous, since research reports
use the same `P<number>` shape for unrelated objects.

---

## §11. Contradictions and open questions

Recorded honestly, because this is a doctrine and not an advertisement for one.

**1. WRT-31 and the ban on chunking sit next to a cliff.**
We require passage self-sufficiency while also accepting Google's direct criticism (2026-01-08) of
the advice to break content into bite-sized chunks. The distinction is stated as follows and must
be checked by the usefulness lens: **self-sufficiency is a paragraph's property of being
comprehensible; chunking is the destruction of a document's coherence for the benefit of a
machine.** The first is tested by the question "is it clear"; the second by "does the document
read as one text". If WRT-31 starts producing documents that fall apart into cards, the rule is to
be revised, not defended.

**2. Group E sits close to what we forbade ourselves.**
P3 forbids optimizing for detectors, and WRT-40…46 are exactly the metrics detectors were
historically built on. The separation: these metrics **never block publication** and never serve
as a target; they are reporting only. The moment a practice of "tuning σ of sentence length"
appears, the rule has become the thing P3 was written against and must be withdrawn.

**3. The thresholds are uncalibrated, and there are many of them.**
Over twenty numbers, the majority of them expert judgement. Until the first run they are
hypotheses. The risk: a system stuffed with uncalibrated thresholds issues confident verdicts on
no basis. Mitigation is a mandatory first run in observation mode — `draft_score.py --observe`
computes everything, blocks nothing, and accumulates distributions until a niche sample exists.

**4. WRT-23 (n-gram overlap) will produce false positives across closely related languages.**
Terminology in a narrow niche inevitably coincides, and Ukrainian and Russian additionally overlap
between locales of the same site. The 0.03 threshold was taken for English. Locales of the same
project must be excluded from the comparison corpus, otherwise translating our own page will be
blocked as plagiarism.

**5. `EG ≥ 0.15` measures entities, not thoughts.**
A page can introduce fifteen percent new entities and say nothing new. Conversely, a strong
original conclusion built on well-known entities will score a low `EG`. This is an acknowledged
limitation of the proxy (P13). It is compensated by the subject-matter lens, not by adjusting the
threshold.

**6. `first_party` rests on human honesty.**
`created_by: <human>` in the artefact manifest is a signature, not a proof. The framework verifies
attachment, not authenticity (§5.4). The only defence is that the signature leaves a trace and is
visible in the history.

---

## Forbidden

| Prohibition                                                      | Basis                                  |
| ---------------------------------------------------------------- | -------------------------------------- |
| Setting a target length in words                                 | §4, official Google red flag           |
| Using an external AI detector as a condition of publication      | P3                                     |
| Running text through a "humanizer"                               | P3                                     |
| Optimizing perplexity/entropy to evade a detector                | §9.2-1, detectors do not rely on it    |
| Blocking publication on group E metrics                          | §11-2                                  |
| Giving the LLM judge a scale instead of a binary question        | §7, scales drift between runs          |
| Letting the writer introduce a claim outside the research packet | WRT-R2, P1                             |
| Letting the editor add facts                                     | WRT-R3                                 |
| Checking a draft with a model from the same family that wrote it | WRT-R4                                 |
| Counting `first_party` without an artefact                       | §5.1, P13                              |
| Keeping the same phrase in both prescribed and forbidden lists   | §6, build invariant                    |
| Carrying language rules across languages automatically           | P5                                     |
| Measuring text length with `wc -w` or a whitespace split         | P5, Cyrillic is counted incorrectly    |
| Showing a human reviewer the machine verdict before their own    | WRT-R5                                 |
| Claiming `EG` is "information gain"                              | P13, it is a proxy and is named as one |

---

## Sources

**Read in full while writing this file:**

| File                                            | What was taken                                                                                                                                                                                                                                                     |
| ----------------------------------------------- | ------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------ |
| `doctrine/00-principles.md`                     | P1, P3, P4, P5, P6, P8, P9, P10, P11, P12, P13                                                                                                                                                                                                                     |
| `README.md`                                     | the three-layer model, the `.kiln/` structure                                                                                                                                                                                                                      |
| `EVIDENCE.md#e03-ai-detection-and-humanization` | §9.0 language-independent rules and group E thresholds; machine traces; arXiv:2602.05769 (perplexity); arXiv:2502.11614 (three axes of humanness, 87.6 %); Google's position on scaled content; Sullivan 2026-01-08 on chunking                                    |
| `EVIDENCE.md#e11-content-quality-signals`       | §7 — group C and D metrics with formulas and thresholds; §8 — the six non-automatable points; §9 — first-party artefact types; patent US11354342B2; `contentEffort`, `OriginalContentScore`, `semanticDate`, `siteRadius` from the leak; vendor score correlations |
| `[internal observation, unpublished]`           | §2 verbatim rules; §3 pipeline and publication path; §5 strengths; §6 defects 1, 2, 9 (examined in §9.2); §7 gaps                                                                                                                                                  |

**Referenced via a secondary summary; the primary file was not opened in this session
(this marker is required by P1):**

- `EVIDENCE.md#e14-content-operations` — the "Editorial Mesh" role contracts (researcher does not
  write prose, writer does not go beyond the packet, editor does not add facts, QA on a different
  model family). The basis for WRT-R1…R4. **Verify against the original at the first revision.**

**External primary sources, cited through the intelligence reports:**

- Google, "Creating helpful, reliable, people-first content", updated 2025-12-10 — the list of
  signals of search-engine-first content, including writing to a particular word count.
- Google, Search Quality Rater Guidelines, 2025-09-11 — the definition of Lowest via the triad
  effort × originality × added value.
- arXiv:2602.05769 (2026-02-06) — contemporary detectors do not rely on perplexity.
- arXiv:2502.11614 — the three axes of the gap: concreteness, cultural nuance, diversity.
- Patent US11354342B2 — Information Gain is computed relative to the user's session.
- Google Content Warehouse API leak (2024-05) — `contentEffort`, `semanticDate`, `siteRadius`,
  `OriginalContentScore` (7 bits, 0..127, short pages only).

**Unverified and moved to open questions:** every threshold marked
`[expert judgement, needs calibration]`; vendor content-score correlations originate from
interested parties; the claimed percentage uplifts in AI-engine citation are reported in the
intelligence without a disclosed methodology and did not enter the rules.
