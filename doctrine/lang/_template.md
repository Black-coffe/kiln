# Language pack template

> Copy this file to `doctrine/lang/<code>.md`, fill every block, delete nothing.
> A pack that omits a required key fails `rules_lint.py` and the doctrine will not build.
>
> **Governed by:** `00-principles.md` (P3, P4, P5), `05-writing-core.md` §6 (the pack contract).
> On any conflict, those files win.

**Template version:** 0.1.0 · **Date:** 2026-08-07

---

## What a language pack is, and what it is not

A language pack holds **everything about writing that depends on a specific language**: vocabulary,
syntax, punctuation, and the structural habits that language's writers actually have. Nothing else.

The doctrine is written in English. The content is written in the language of the target site. The
pack is selected by the locale declared in `.kiln/project.yml`, never by the doctrine's own language
(P5).

A pack is **not**:

- a translation of another pack (see "What must never be copied", below);
- a definition of quality — it catches traces of carelessness, and a draft that is clean against the
  pack and empty of original claims is still a bad draft (P4);
- a detector-evasion tool (P3).

---

## Contract compliance

`rules_lint.py` checks the following and fails the build on any violation:

1. All seven required set keys are present: `anaphora_openers`, `hedge_phrases`, `closing_formulas`,
   `promo_lexicon`, `vague_attribution`, `generational_stopwords`, `prescribed_phrases`.
2. **Every set declares `forbidden: true|false`**, including any pack-local set beyond the seven.
   A pack may add sets its language needs and no other does; the Ukrainian pack carries a russism
   set, for instance.

   **The key names are contract.** Entries live under `items:` and each names its surface form under
   `phrase:`. Inventing your own key names does not produce an error: the file parses, the pack
   looks healthy, and every consumer reading the contract receives an **empty set**. The pack stops
   having opinions and nothing says so. This has already happened once, to nine sets at a time.

3. **Every set declares a `rule_id`** of the form `LANG-<LOCALE>-<NN>` — locale segment uppercase and
   equal to `lang.code`, number zero-padded, assigned in declaration order. Findings are counted per
   rule in `.kiln/rules-stats.json`, and an identifier invented at runtime cannot be counted because
   nothing outside the code that invented it knows it exists.

   **Identifiers are immutable once published.** A set whose meaning changes gets a new identifier;
   the old one is retired, never reused. Reuse corrupts every counter spanning the change and does
   it silently, showing one long history where there were two different rules.

4. The invariant holds:
   ```
   prescribed_phrases ∩ ( ⋃ every set where forbidden: true ) = ∅
   ```
   The union is computed over **all** forbidden sets in the pack, not a fixed list of five.
   A fixed list cannot see a pack-local set, which would let a pack prescribe a phrase its own
   russism set forbids while the build passed. A non-empty intersection is a build error, not a
   topic for discussion.
5. Every set carries `updated_at` and `next_review`.
6. `next_review` is not in the past. An expired pack raises a WARN on every run: stop-vocabulary is
   tied to model generations and goes stale within months.
7. Every item carries `phrase` and `risk`, and resolves a `status` — either on the entry itself or
   from a set-level `default_status`. An entry-level value overrides the set default. Declaring the
   status once per set is preferred where a whole set shares one evidential basis; repeating it on
   every entry of a five-hundred-entry set adds noise, not rigour.
8. **`status` is one of `hypothesis` | `observed` | `calibrated` | `deterministic`.** The first
   three are statistical claims about this language. `deterministic` is for entries that are not
   statistical at all: a letter absent from the alphabet, a Latin homoglyph inside a native token,
   a zero-width character, mojibake. Those are facts, and recording them as hypotheses would be
   false.
9. **Only `deterministic` entries may carry `BLOCK`.** Every stylistic entry is capped at `WARN` by
   the severity scale in `00-principles.md`, and sits at `INFO` until the language has calibration
   data. Gating publication on a stylometric score is the failure P3 forbids, and a pack must not
   reintroduce it with a home-made detector.
10. Every threshold carries `[source: …]` or `[expert judgement, needs calibration]`.

**Phrase normalization** must be declared in metadata, because the invariant is undefined without it.
Two entries are the same phrase if they are equal after normalization.

---

## 1. Metadata

```yaml
lang:
  code: xx # ISO 639-1, lowercase
  script: Xxxx # ISO 15924: Latn, Cyrl, Grek …
  locales: [] # BCP-47 locales this pack serves, e.g. [uk-UA]
  updated_at: YYYY-MM-DD
  next_review: YYYY-MM-DD # updated_at + 90 days
  maintainer: "" # who answers for this pack

  # Which model generations the vocabulary below was observed on.
  # Vocabulary is generation-bound: a list derived from one generation
  # under-detects the next. Record what you actually observed, not what you assume.
  observed_generations: []
  observed_families: [] # openai | anthropic | google | meta | other
  evidence_basis: "" # corpus, study, editorial practice — with URLs

  # Required. The invariant is uncheckable without it: "are these the same phrase"
  # has no answer until the pack says how a phrase is normalized.
  normalization:
    case: lower
    collapse_whitespace: true
    strip_trailing_ellipsis: true
    strip_terminal_punctuation: true
    unicode_form: NFC
    # Unicode-aware only. `wc -w` and whitespace splits are forbidden (P5).
    tokenizer: unicode_words
    # Whether an apostrophe inside a word is removed before comparison.
    # Set false wherever the apostrophe is part of the word, either
    # morphologically (Ukrainian «п'ять») or contrastively (English `it's` vs `it`).
    strip_internal_apostrophes: false
    # When one entry is a substring of another, the longer one consumes the span
    # so density is counted once. Without this the same words feed two counters.
    matching: longest_match_wins
    # Required for inflected languages. Surface-form comparison in a language with
    # cases makes the one-anchor-one-URL invariant (P6) report clean while
    # guaranteeing nothing: the inflected forms never collide, so no conflict is
    # ever detected. Declare `unresolved` rather than omitting the field, so the
    # gap is visible instead of absent.
    lemmatizer: none # none | unresolved | <tool>@<pinned-version>
```

**`lemmatizer` is not optional bookkeeping.** For a language that inflects, an unset lemmatizer does
not degrade the anchor invariant, it disables it while leaving the check green. Declaring
`unresolved` records a known hole; omitting the field records nothing and reads as "handled".

---

## 2. The seven required sets

Every item takes the same shape:

```yaml
- phrase: "" # the literal phrase, or a short label when `match` carries the pattern
  risk: "" # critical | high | medium | low
  status: "" # hypothesis | observed | calibrated | deterministic
  class: "" # optional sub-type, set-specific
  note:
    "" # REQUIRED for risk: critical and risk: high.
    # Say why this is a signal, not merely why you dislike it.
  replacements: [] # optional, what to write instead
  match: "" # optional pattern; defaults to `phrase`
  match_mode: phrase # phrase | density | regex
  named_check: "" # optional, see below; mutually exclusive with `match`
  severity: "" # optional per-entry downgrade. Never an upgrade.
```

**`match_mode` is the most important field in the shape.**

`phrase` judges by presence. `density` judges by frequency per 1,000 words and **never** by
presence. `regex` is a pattern with morphology baked in.

Ordinary words that models over-produce must be `density`. Banning a normal word by presence bans
normal writing in your language, and the pack becomes the thing it exists to prevent. If you find
yourself listing a word a competent human writer uses several times per article, it is a `density`
entry or it is not an entry.

A `density` entry whose set declares no `density_warn_per_1000` is measured and reported, never
warned. That is correct for an uncalibrated language: measuring is honest, warning against a
threshold nobody derived manufactures confidence out of nothing.

Density also does not apply to short text. One hit in 120 words reads as 8.3 per 1,000 and trips a
threshold of 5, turning a frequency rule back into a presence rule. Below `lang.density_min_words`
the rate is recorded and not compared.

### Checks that cannot be written as patterns

Some deterministic facts are properties of a **token** or a **document**, not of a character stream.
Writing them as a regex anyway produces a rule that compiles, reviews cleanly, and never fires.

The recorded case is real. `\b(?=\p{Cyrillic})(?=\p{Latin})\S+\b` was written to catch Latin
homoglyphs inside Cyrillic words. Two lookaheads at one position require a **single character** to
belong to two scripts simultaneously, so the match set is empty. It shipped, and it protected
nothing.

Declare `named_check: <name>` instead of `match:` for these. The scorer resolves the name against
its registry, and **an unrecognised name is a pack defect rather than a silent skip** — a check that
cannot run has to say so, or it is worse than no check at all.

Registry: `mixed_script_token`.

**Before merging any new pattern, demonstrate it firing on a constructed positive case.** A dead
rule reports success forever, and nobody goes looking for a rule that never complains.

### 2.1 `anaphora_openers` → feeds WRT-32, severity **BLOCK**

Referential openers: words and phrases that cannot begin a section because they point at context the
reader does not have when the passage is extracted on its own. This is the one lexical set that
blocks, and it blocks for a retrieval reason rather than a stylistic one: extraction operates at the
passage level, and a passage opening with a dangling reference is not cited (P12).

```yaml
anaphora_openers:
  rule_id: LANG-XX-01 # required; XX = lang.code, uppercase
  forbidden: true
  updated_at: YYYY-MM-DD
  next_review: YYYY-MM-DD
  applies_to: section_first_sentence
  severity: BLOCK
  items: []
```

### 2.2 `hedge_phrases` → WARN

Didactic caveats and meta-commentary: the writer announcing what they are about to do instead of
doing it, and softening formulas that carry no information.

```yaml
hedge_phrases:
  rule_id: LANG-XX-02 # required; XX = lang.code, uppercase
  forbidden: true
  updated_at: YYYY-MM-DD
  next_review: YYYY-MM-DD
  severity: WARN
  density_warn_per_1000: null # [expert judgement, needs calibration]
  items: [] # class: hedge | meta_bridge | filler
```

### 2.3 `closing_formulas` → WARN

Template endings and the mandatory-summary reflex. A closing section is only a defect when it adds
nothing that was not already said; the check therefore pairs the phrase match with "does this section
contain a new claim?".

```yaml
closing_formulas:
  rule_id: LANG-XX-03 # required; XX = lang.code, uppercase
  forbidden: true
  updated_at: YYYY-MM-DD
  next_review: YYYY-MM-DD
  severity: WARN
  requires_new_claim_check: true
  items: []
```

### 2.4 `promo_lexicon` → WARN

Advertising register: unearned significance, brochure adjectives, scene-setting filler.

```yaml
promo_lexicon:
  rule_id: LANG-XX-04 # required; XX = lang.code, uppercase
  forbidden: true
  updated_at: YYYY-MM-DD
  next_review: YYYY-MM-DD
  severity: WARN
  density_warn_per_1000: null # [expert judgement, needs calibration]
  items: []
```

### 2.5 `vague_attribution` → reinforces WRT-11

Attribution that names no one. This set is not really about style: it is the linguistic surface of a
missing source, and it is the cheapest signal that P1 was skipped. Every hit should resolve either to
a named source with a date, or to deletion.

```yaml
vague_attribution:
  rule_id: LANG-XX-05 # required; XX = lang.code, uppercase
  forbidden: true
  updated_at: YYYY-MM-DD
  next_review: YYYY-MM-DD
  severity: WARN # escalates to BLOCK when the sentence carries a figure
  escalate_to_block_if: sentence_contains_number
  items: []
```

### 2.6 `generational_stopwords` → WARN

Lexical over-representation, versioned by model generation. Each item records the generation it was
observed on, so the list can be aged rather than blindly inherited.

```yaml
generational_stopwords:
  rule_id: LANG-XX-06 # required; XX = lang.code, uppercase
  forbidden: true
  updated_at: YYYY-MM-DD
  next_review: YYYY-MM-DD
  severity: WARN
  density_warn_per_1000: null # [expert judgement, needs calibration]
  items: [] # each adds: generation, first_observed, class (lexical|transition)
```

### 2.7 `prescribed_phrases` → writer prompt

What the pack actively wants. **Keep this set small and structural.**

A prescribed _catchphrase_ becomes a formula the moment it is prescribed: every article starts saying
the same thing, and the pack has manufactured a new tell. Prescribe grammatical forms and function
words, not personality. Voice comes from specific facts, not from a phrase bank (P4).

```yaml
prescribed_phrases:
  rule_id: LANG-XX-07 # required; XX = lang.code, uppercase
  forbidden: false
  updated_at: YYYY-MM-DD
  next_review: YYYY-MM-DD
  severity: INFO
  items: [] # class: contraction | simple_transition | grammatical_form
```

---

## 3. Language-specific structural rules

Prose section. Cover, at minimum:

- **Repetition and parallelism.** Which structural repetitions read as machine output in this
  language, and at what count.
- **Heading conventions.** Capitalization rules that actually exist in this language. Do not import a
  rule from a language that capitalizes differently.
- **Opening paragraph.** Patterns to avoid, above all defining the headline term back at the reader.
- **List construction.** Symmetry, item length, the bolded-lead-in pattern.
- **Closing.** Whether a summary section is idiomatic in this language's non-fiction.
- **Named-entity handling.** Whether elegant variation (substituting synonyms for a name already
  introduced) is a marker here.

Each rule needs an ID of the form `<CODE>-S<nn>`, a severity, and a threshold marked with its
provenance.

---

## 4. Language-specific punctuation rules

Prose section plus a YAML block. Cover the punctuation this language actually uses, and state the
severity for each rule.

```yaml
punctuation:
  updated_at: YYYY-MM-DD
  next_review: YYYY-MM-DD
  rules: [] # id, description, severity, threshold, provenance
```

**Mandatory in every pack:** a written statement of which punctuation rules are specific to this
language and must never be exported. See section 6.

---

## 5. Statistical form metrics

The language-independent core (`05-writing-core.md`, group E) defines the metrics. The pack supplies
**ranges calibrated for this language**, because sentence length, morphology and word-formation
differ enough that one set of numbers cannot serve all languages.

Every range ships as `[expert judgement, needs calibration]` until the first observation run on a real
corpus in the target niche has produced local distributions. Until then, run
`draft_score.py --observe`: compute everything, block nothing.

```yaml
form_metrics:
  updated_at: YYYY-MM-DD
  next_review: YYYY-MM-DD
  calibration_status: uncalibrated # uncalibrated | observed | calibrated
  corpus_size_docs: 0
  metrics: [] # id (mirrors WRT-40…46), warn_threshold, provenance
```

These metrics never block publication (`05-writing-core.md` §11-2). The moment anyone starts tuning a
draft to hit a sentence-length variance target, the metric has become the thing P3 forbids and must be
withdrawn.

---

## 6. What must never be copied from another language

Fill this section with the specific cross-language traps for your language. It is not boilerplate. The
rule exists because the failure has already happened.

**The dash precedent.** "High em-dash density indicates AI authorship" is a valid signal in English,
where the em-dash is a stylistic choice. It is invalid in Cyrillic-script languages, where the dash is
grammatically obligatory in the copular construction «Х — це У». Porting the English rule to Ukrainian
converted 349 grammatically correct dashes into commas and broke the text. A pack must never inherit a
punctuation rule from a language with different grammar.

**Vocabulary does not translate.** A stop-word list is a record of what one model family
over-produced in one language. Translating "delve" into another language produces a word that carries
none of that statistical history, and the translated list will fire on ordinary human writing.
Vocabulary lists are derived from a corpus in the target language, or they are not derived at all.

**Structural metrics do travel, but their thresholds do not.** Sentence-length variance is meaningful
everywhere; the number that counts as low is not. Morphologically rich languages produce different
token counts for the same content, and word-count thresholds imported across that boundary are simply
wrong.

**Measurement itself is language-specific.** Any module measuring text length must use Unicode-aware
tokenization. `wc -w` does not split Cyrillic into words; on a live measurement it reported an English
locale as six times larger than a Ukrainian one that was in fact at parity, inverting the conclusion
(P5).

**Where no research exists, say so.** If there is no published work on machine-text markers for your
language, do not invent authority. Build on (a) the closest researched language with which yours
shares the constructions models actually produce, and (b) the language-independent structural metrics.
Mark every borrowed item as borrowed, and put a corpus study on the roadmap.

---

## 7. Provenance and review

- Every item traces to a source: a study, a documented editorial practice, or an observation on your
  own corpus. Mark which.
- Every threshold carries `[source: …]` or `[expert judgement, needs calibration]`.
- `next_review` is 90 days out. Vocabulary ages with model releases; an expired pack is a WARN on
  every run and its findings should be treated as suspect.
- Negative results belong in `doctrine/CHANGELOG.md` alongside positive ones (P15). A rule you had to
  withdraw is more useful to the next maintainer than a rule you kept.

---

## 8. Checklist before submitting a new pack

- [ ] All seven set keys present and non-empty (except `prescribed_phrases`, which may be
      deliberately minimal).
- [ ] Entries live under `items:` and name their surface form under `phrase:`. Not `entries:`, not
      `term:`. A renamed key delivers an empty set to every consumer and reports nothing.
- [ ] Every set, including any pack-local one, declares `forbidden: true|false`.
- [ ] Every set declares a unique `rule_id` of the form `LANG-<LOCALE>-<NN>`, locale segment
      matching `lang.code`.
- [ ] Every ordinary word that models over-produce is `match_mode: density`, never `phrase`.
- [ ] Every pattern has been demonstrated to fire on a constructed positive case. A rule that
      compiles and cannot match reports success forever.
- [ ] `named_check` used wherever the fact is a property of a token or document rather than of a
      character stream, and every name used is in the registry.
- [ ] Every entry declares `status`; nothing is marked `calibrated` without a distribution behind it.
- [ ] No stylistic entry carries `BLOCK`; only `deterministic` entries may.
- [ ] `rules_lint.py` passes, including the intersection invariant.
- [ ] `normalization` block filled, so the invariant is well-defined.
- [ ] Every `risk: critical` and `risk: high` item has a `note` explaining why it is a signal.
- [ ] Every threshold has a provenance marker.
- [ ] Section 6 filled with this language's actual traps, not copied text.
- [ ] Nothing in the pack optimizes against a detector, targets perplexity, or sets a word count.
- [ ] `next_review` set 90 days out.
