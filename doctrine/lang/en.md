# Language pack: English (`en`)

> Follows `_template.md`. Governed by `00-principles.md` (P3, P4, P5) and `05-writing-core.md` §6.
> On any conflict those files win.

**Pack version:** 0.1.0 · **Date:** 2026-08-07 · **Review due:** 2026-11-05

**What this pack is.** A record of the lexical, syntactic and punctuation habits that mark English
prose as machine-produced, plus the small set of forms English writing should actively use. It is a
carelessness detector, not a definition of quality. A draft that is clean against every list here and
carries no original claim is still a bad draft (P4, and `05-writing-core.md` group C).

---

## 1. Metadata

```yaml
lang:
  code: en
  script: Latn
  locales: [en-US, en-GB, en-AU, en-CA, en-IE, en-NZ]
  updated_at: 2026-08-07
  next_review: 2026-11-05
  maintainer: kiln-core

  observed_generations:
    - id: gpt-4
      window: "2023 — mid-2024"
    - id: gpt-4o
      window: "mid-2024 — mid-2025"
    - id: gpt-5
      window: "mid-2025 — present"

  # HONEST GAP: the published vocabulary evidence is almost entirely OpenAI-centric.
  # Anthropic, Google and Meta families are not separately characterised in any source
  # we found. This pack therefore under-detects non-OpenAI output, and the gap is not
  # quantified. Do not read a clean run as "not machine-written".
  observed_families: [openai]

  evidence_basis: >
    Wikipedia:Signs of AI writing (collective editorial practice, thousands of reviewed edits);
    Juzek & Ward, "Why Does ChatGPT 'Delve' So Much?", COLING 2025 (Florida State University),
    the first scientific account of lexical over-representation;
    the owner's production stop-rules at ai_docs/marketing/ai-content-stop-rules.md v1.0 (2026-05-19),
    in use on a live site with a working Search Console loop.
    Full citations in section 8.

  normalization:
    case: lower
    unicode_form: NFC
    collapse_whitespace: true
    strip_trailing_ellipsis: true
    strip_terminal_punctuation: true
    strip_internal_apostrophes: false # load-bearing, see below
    tokenizer: unicode_words
    matching: longest_match_wins
    lemmatizer: none # English inflects weakly; surface forms collide adequately
```

**Two normalization decisions carry weight and must not be changed casually.**

`strip_internal_apostrophes: false`. English contractions are _prescribed_ here while the bare
pronouns they contain are _forbidden_ as section openers. `it's` and `it`, `they're` and `they`,
`that's` and `that` must remain distinct strings, or the contract invariant collapses into a false
positive and the doctrine stops building.

`matching: longest_match_wins`. Several entries are substrings of others (`realm` and
`in the realm of`). The longest match consumes the span, so density is counted once. Without this the
same words inflate two counters and every threshold in section 6 becomes meaningless.

---

## 2. The seven required sets

### 2.1 `anaphora_openers` — BLOCK, feeds WRT-32

Referential openers. Forbidden as the **first sentence of a section**, unrestricted elsewhere.

The reason is retrieval, not taste. Extraction from AI answer engines operates at the passage level,
and a passage opening with a dangling reference cannot stand alone, so it is not cited (P12, and the
finding that 44.2% of citations come from the first third of a document). This is the one lexical set
in the pack that blocks.

```yaml
anaphora_openers:
  rule_id: LANG-EN-01
  forbidden: true
  # deterministic: "does this section begin with a bare demonstrative" is verifiable by
  # inspection, not a frequency claim, so BLOCK is permitted here. Feeds WRT-32, a
  # structural extractability rule, not a stylometric score.
  default_status: deterministic
  updated_at: 2026-08-07
  next_review: 2026-11-05
  applies_to: section_first_sentence
  severity: BLOCK
  items:
    - {
        phrase: "this",
        risk: high,
        note: "Bare demonstrative opening a section: the referent is gone the moment the passage is extracted.",
      }
    - {
        phrase: "that",
        risk: high,
        note: "Same failure as 'this'; also the most common LLM section-bridge in English.",
      }
    - {
        phrase: "these",
        risk: high,
        note: "Plural demonstrative, same extraction failure.",
      }
    - { phrase: "those", risk: medium }
    - {
        phrase: "it",
        risk: high,
        note: "Referential 'it' opening a section is unresolvable out of context. Expletive 'it is' constructions are caught separately by hedge_phrases.",
      }
    - {
        phrase: "they",
        risk: high,
        note: "Antecedent lives in the previous section, which the retriever does not fetch.",
      }
    - { phrase: "such", risk: medium }
    - { phrase: "such a", risk: medium }
    - { phrase: "such an", risk: medium }
    - {
        phrase: "this approach",
        risk: high,
        note: "Names a category without naming the thing; survives no extraction.",
      }
    - {
        phrase: "this means",
        risk: high,
        note: "Announces a consequence of an unstated premise.",
      }
    - {
        phrase: "this is why",
        risk: high,
        note: "Same as above, with added false causality.",
      }
    - { phrase: "these are", risk: medium }
    - { phrase: "the former", risk: medium }
    - { phrase: "the latter", risk: medium }
    - { phrase: "as mentioned", risk: medium }
    - { phrase: "as mentioned above", risk: medium }
    - { phrase: "as noted", risk: medium }
    - { phrase: "as discussed", risk: medium }
    - { phrase: "as we saw", risk: medium }
    - {
        phrase: "building on this",
        risk: high,
        note: "Explicit dependency on prior text; the strongest possible signal that the passage is not self-contained.",
      }
    - {
        phrase: "with that in mind",
        risk: high,
        note: "Pure connective tissue carrying no content of its own.",
      }
    - { phrase: "given this", risk: medium }
    - { phrase: "given that", risk: low }
    - {
        phrase: "however",
        risk: low,
        note: "Contrastive, not strictly anaphoric, but presupposes a proposition the extracted passage lacks.",
      }
```

### 2.2 `hedge_phrases` — WARN

Two classes. `hedge`: softening formulas carrying no information. `meta_bridge`: the writer narrating
what they are about to do instead of doing it.

The governing rule from the owner's production docs transfers verbatim, and it is general enough to
outlive any individual phrase on this list: **remove meta-commentary about what you are about to do;
just do it.**

```yaml
hedge_phrases:
  rule_id: LANG-EN-02
  forbidden: true
  default_status: hypothesis
  updated_at: 2026-08-07
  next_review: 2026-11-05
  severity: WARN
  density_warn_per_1000: 1.5 # [expert judgement, needs calibration]
  items:
    - {
        phrase: "it's important to note",
        risk: critical,
        class: hedge,
        note: "Highest-frequency English hedge in machine output across all three observed generations. Whatever follows is either important, in which case say it, or it is not.",
      }
    - { phrase: "it is important to note", risk: critical, class: hedge }
    - {
        phrase: "it's worth noting",
        risk: high,
        class: hedge,
        note: "Same construction, softened; appears where the model has no confidence in the claim.",
      }
    - { phrase: "it's worth mentioning", risk: high, class: hedge }
    - { phrase: "it should be noted", risk: high, class: hedge }
    - {
        phrase: "it goes without saying",
        risk: high,
        class: hedge,
        note: "Self-refuting: the sentence exists to say the thing it claims needs no saying.",
      }
    - { phrase: "needless to say", risk: high, class: hedge }
    - { phrase: "it's crucial to understand", risk: high, class: hedge }
    - { phrase: "one must consider", risk: medium, class: hedge }
    - {
        phrase: "when it comes to",
        risk: high,
        class: hedge,
        note: "Topic-shift filler; deletable in every observed instance without loss.",
      }
    - { phrase: "indeed", risk: medium, class: filler }
    - {
        phrase: "certainly",
        risk: medium,
        class: filler,
        note: "Chat-assistant residue when sentence-initial.",
      }
    - {
        phrase: "absolutely",
        risk: medium,
        class: filler,
        note: "Same residue; near-zero rate in edited human non-fiction.",
      }
    - { phrase: "of course", risk: low, class: filler }
    - { phrase: "arguably", risk: low, class: hedge }
    - {
        phrase: "here's the thing",
        risk: critical,
        class: meta_bridge,
        note: "Announces an insight instead of stating it. Independently flagged twice in the source system, as a cliché and as a bridge. See section 7 for the prescribed-versus-forbidden ruling on this phrase.",
      }
    - {
        phrase: "but here's the thing",
        risk: critical,
        class: meta_bridge,
        note: "The exact form that the source system simultaneously prescribed and forbade. Resolved in favour of forbidding. Section 7.",
      }
    - { phrase: "let me walk you through", risk: high, class: meta_bridge }
    - { phrase: "let me break this down", risk: high, class: meta_bridge }
    - { phrase: "allow me to explain", risk: high, class: meta_bridge }
    - { phrase: "here's what happens when", risk: medium, class: meta_bridge }
    - {
        phrase: "the reality is",
        risk: high,
        class: meta_bridge,
        note: "Asserts candour in place of evidence; typically precedes an unsourced claim.",
      }
    - {
        phrase: "let me be honest",
        risk: high,
        class: meta_bridge,
        note: "Implies the preceding text was not.",
      }
    - {
        phrase: "let's delve into",
        risk: critical,
        class: meta_bridge,
        note: "Combines the single most-flagged English lexical marker with a meta-bridge.",
      }
    - { phrase: "let's dive into", risk: high, class: meta_bridge }
    - {
        phrase: "in this comprehensive guide",
        risk: critical,
        class: meta_bridge,
        note: "Describes the artefact rather than serving the reader; near-absent from human-edited copy.",
      }
    - { phrase: "as we navigate", risk: high, class: meta_bridge }
    - { phrase: "in this article, we will", risk: high, class: meta_bridge }
    - { phrase: "by the end of this article", risk: medium, class: meta_bridge }
```

### 2.3 `closing_formulas` — WARN

Template endings and the reflex to restate. A closing section is a defect only when it introduces
nothing new, so the phrase match is paired with a new-claim check on the section it opens.

```yaml
closing_formulas:
  rule_id: LANG-EN-03
  forbidden: true
  default_status: hypothesis
  updated_at: 2026-08-07
  next_review: 2026-11-05
  severity: WARN
  requires_new_claim_check: true
  items:
    - {
        phrase: "in conclusion",
        risk: critical,
        note: "The single most recognisable English closing formula in machine output; essentially absent from professional non-fiction.",
      }
    - { phrase: "in summary", risk: high }
    - { phrase: "in essence", risk: high }
    - { phrase: "to sum up", risk: high }
    - { phrase: "to wrap up", risk: medium }
    - { phrase: "wrapping up", risk: medium }
    - { phrase: "in closing", risk: high }
    - { phrase: "all in all", risk: high }
    - {
        phrase: "the bottom line is",
        risk: high,
        note: "Motivational-post register; flagged in the source system's dramatic-cliché list.",
      }
    - {
        phrase: "at the end of the day",
        risk: high,
        note: "Appears in the source system twice, as a cliché and as a closing formula. Counted here once.",
      }
    - {
        phrase: "key takeaways",
        risk: medium,
        note: "Acceptable as a genuine summary of new material; flagged when it restates.",
      }
    - { phrase: "final thoughts", risk: medium }
    - {
        phrase: "challenges and legacy",
        risk: high,
        note: "Encyclopaedic section title generated wholesale; documented in collective editorial practice.",
      }
    - {
        phrase: "future outlook",
        risk: high,
        note: "Same origin as the above.",
      }
    - {
        phrase: "despite its challenges",
        risk: high,
        note: "Opens the canonical machine-generated closing arc: concede a difficulty, gesture at initiatives, end.",
      }
    - { phrase: "despite these challenges", risk: high }
    - {
        phrase: "i hope this helps",
        risk: critical,
        note: "Direct chat-assistant residue. Near-zero false positive rate in published prose.",
      }
    - {
        phrase: "let me know if you'd like",
        risk: critical,
        note: "Chat-assistant residue addressed to the operator, not the reader.",
      }
    - { phrase: "feel free to reach out if", risk: low }
```

### 2.4 `promo_lexicon` — WARN

Advertising register: unearned significance, brochure adjectives, scene-setting filler. Distinguished
from `generational_stopwords` by function, not by frequency. A term belongs here if it signals
_selling_; it belongs in the generational set if it signals _over-production in neutral prose_. Each
phrase is assigned to exactly one set so density is counted once.

```yaml
promo_lexicon:
  rule_id: LANG-EN-04
  forbidden: true
  default_status: hypothesis
  updated_at: 2026-08-07
  next_review: 2026-11-05
  severity: WARN
  density_warn_per_1000: 2.0 # [expert judgement, needs calibration]
  items:
    - {
        phrase: "in today's ever-evolving world",
        risk: critical,
        note: "The canonical machine opener. Says nothing, dates instantly, and is absent from edited copy.",
      }
    - {
        phrase: "in today's fast-paced digital landscape",
        risk: critical,
        note: "Same construction; the source system forbids the whole 'in today's …' family of openers.",
      }
    - {
        phrase: "in today's",
        risk: high,
        note: "Family head. Longest-match handles the fuller variants above.",
      }
    - { phrase: "ever-evolving", risk: high }
    - { phrase: "in the realm of", risk: high }
    - { phrase: "in an era where", risk: high }
    - {
        phrase: "cutting-edge",
        risk: high,
        note: "Rated HIGH in the source system's production stop-list; brochure adjective carrying no measurable claim.",
      }
    - {
        phrase: "revolutionary",
        risk: high,
        note: "Rated HIGH in the source system; asserts significance the text never demonstrates.",
      }
    - { phrase: "groundbreaking", risk: high }
    - {
        phrase: "game-changer",
        risk: high,
        note: "Flagged in the source system as a TED-talk register marker.",
      }
    - {
        phrase: "take it to the next level",
        risk: high,
        note: "Same register test: if it belongs in a motivational post, cut it.",
      }
    - { phrase: "move the needle", risk: high }
    - { phrase: "in the trenches", risk: medium }
    - { phrase: "keep me up at night", risk: medium }
    - { phrase: "it's not rocket science", risk: medium }
    - {
        phrase: "elevate",
        risk: high,
        note: "Corporate verb; added by the source system's authenticity reviewer and its copywriting rules independently.",
      }
    - { phrase: "unlock", risk: high }
    - { phrase: "unleash", risk: high }
    - { phrase: "empower", risk: high }
    - { phrase: "supercharge", risk: high }
    - { phrase: "exceed", risk: medium }
    - {
        phrase: "nestled",
        risk: high,
        note: "Travel-brochure verb; documented as a strong marker in collective editorial practice.",
      }
    - { phrase: "in the heart of", risk: high }
    - { phrase: "diverse array", risk: high }
    - { phrase: "indelible mark", risk: high }
    - { phrase: "renowned", risk: medium }
    - { phrase: "exemplifies", risk: medium }
    - { phrase: "commitment to", risk: low }
    - { phrase: "world-class", risk: medium }
    - { phrase: "best-in-class", risk: medium }
    - { phrase: "profound", risk: low }
```

### 2.5 `vague_attribution` — WARN, escalates to BLOCK

This set is not about style. It is the linguistic surface of a missing source, and the cheapest
available signal that P1 was skipped. Half of the markers by which humans identify machine text are
not stylistic at all — they are unverified facts.

Every hit resolves one of two ways: a named source with a publication date, or deletion. When the
sentence also carries a figure, the finding escalates to BLOCK, because an unsourced number is the
exact failure mode P1 exists to stop.

Required replacement form, transferred verbatim from the source system: **"According to [Name],
[Publication], [Date]…"**

```yaml
vague_attribution:
  rule_id: LANG-EN-05
  forbidden: true
  default_status: hypothesis
  updated_at: 2026-08-07
  next_review: 2026-11-05
  severity: WARN
  escalate_to_block_if: sentence_contains_number
  items:
    - {
        phrase: "studies show",
        risk: critical,
        note: "Names no study. When it precedes a figure this is a fabricated-citation pattern, not a stylistic weakness.",
      }
    - { phrase: "research shows", risk: critical }
    - { phrase: "research suggests", risk: critical }
    - { phrase: "according to research", risk: critical }
    - {
        phrase: "some experts believe",
        risk: critical,
        note: "Names no expert. Documented in collective editorial practice as a primary fabrication tell.",
      }
    - { phrase: "experts argue", risk: high }
    - { phrase: "experts say", risk: high }
    - { phrase: "many sources claim", risk: high }
    - { phrase: "several sources", risk: high }
    - {
        phrase: "industry reports",
        risk: high,
        note: "Names no report; frequently attached to an invented market figure.",
      }
    - { phrase: "observers have cited", risk: high }
    - { phrase: "some critics argue", risk: high }
    - { phrase: "it is widely believed", risk: high }
    - { phrase: "data suggests", risk: high }
    - { phrase: "reports indicate", risk: high }
    - { phrase: "analysts predict", risk: high }
    - { phrase: "recent studies", risk: high }
```

### 2.6 `generational_stopwords` — WARN

Lexical over-representation, versioned by the model generation on which it was observed. Two classes:
`lexical` (content words) and `transition` (connectives the model reaches for by default).

The phenomenon has a scientific account rather than only folklore: words whose frequency had recently
risen in academic abstracts turned out to be the same words the model over-produces, which is why the
list shifts with each generation and why an inherited list ages into uselessness.

`risk` values for the first fifteen entries are carried over from the source system's production
stop-list, which assigns them without stating a derivation. Treat them as an experienced editor's
ranking, not as measured effect sizes.

```yaml
generational_stopwords:
  rule_id: LANG-EN-06
  forbidden: true
  default_status: hypothesis
  updated_at: 2026-08-07
  next_review: 2026-11-05
  severity: WARN
  density_warn_per_1000: 2.0 # [source: EVIDENCE.md#e03-ai-detection-and-humanization]
  items:
    - {
        phrase: "delve",
        risk: critical,
        class: lexical,
        generation: gpt-4,
        first_observed: 2023,
        note: "The most-studied single marker in English. Named in the COLING 2025 paper that first explained lexical over-representation. Rated CRITICAL in production use.",
        replacements: [explore, examine, look into, dig into],
      }
    - {
        phrase: "tapestry",
        risk: high,
        class: lexical,
        generation: gpt-4,
        first_observed: 2023,
        note: "Metaphor with essentially no base rate in technical prose.",
        replacements: [mix, combination, blend],
      }
    - {
        phrase: "multifaceted",
        risk: high,
        class: lexical,
        generation: gpt-4,
        first_observed: 2023,
        replacements: [complex, varied, diverse],
      }
    - {
        phrase: "leverage",
        risk: high,
        class: lexical,
        generation: gpt-4,
        first_observed: 2023,
        note: "As a verb. Survives all three generations and doubles as corporate register.",
        replacements: [use, apply],
      }
    - {
        phrase: "pivotal",
        risk: high,
        class: lexical,
        generation: gpt-4,
        first_observed: 2023,
        replacements: [important, key, decisive],
      }
    - {
        phrase: "robust",
        risk: high,
        class: lexical,
        generation: gpt-4,
        first_observed: 2023,
        replacements: [strong, solid, reliable],
      }
    - {
        phrase: "paramount",
        risk: medium,
        class: lexical,
        generation: gpt-4,
        first_observed: 2023,
        replacements: [essential, critical],
      }
    - {
        phrase: "underscore",
        risk: medium,
        class: lexical,
        generation: gpt-4,
        first_observed: 2023,
        replacements: [highlight, show],
      }
    - {
        phrase: "intricate",
        risk: medium,
        class: lexical,
        generation: gpt-4,
        first_observed: 2023,
        replacements: [complex, detailed],
      }
    - {
        phrase: "intricacies",
        risk: medium,
        class: lexical,
        generation: gpt-4,
        first_observed: 2023,
      }
    - {
        phrase: "nuanced",
        risk: medium,
        class: lexical,
        generation: gpt-4,
        first_observed: 2023,
        replacements: [subtle, fine],
      }
    - {
        phrase: "seamless",
        risk: medium,
        class: lexical,
        generation: gpt-4,
        first_observed: 2023,
        replacements: [smooth, easy],
      }
    - {
        phrase: "holistic",
        risk: medium,
        class: lexical,
        generation: gpt-4,
        first_observed: 2023,
        replacements: [complete, whole],
      }
    - {
        phrase: "synergy",
        risk: medium,
        class: lexical,
        generation: gpt-4,
        first_observed: 2023,
        replacements: [cooperation, teamwork],
      }
    - {
        phrase: "meticulous",
        risk: medium,
        class: lexical,
        generation: gpt-4,
        first_observed: 2023,
      }
    - {
        phrase: "meticulously",
        risk: medium,
        class: lexical,
        generation: gpt-4,
        first_observed: 2023,
      }
    - {
        phrase: "interplay",
        risk: medium,
        class: lexical,
        generation: gpt-4,
        first_observed: 2023,
      }
    - {
        phrase: "garner",
        risk: medium,
        class: lexical,
        generation: gpt-4,
        first_observed: 2023,
      }
    - {
        phrase: "bolstered",
        risk: medium,
        class: lexical,
        generation: gpt-4o,
        first_observed: 2023,
      }
    - {
        phrase: "enduring",
        risk: medium,
        class: lexical,
        generation: gpt-4o,
        first_observed: 2023,
      }
    - {
        phrase: "testament",
        risk: high,
        class: lexical,
        generation: gpt-4,
        first_observed: 2023,
        note: "Almost always in 'is a testament to', asserting significance the text has not demonstrated.",
      }
    - {
        phrase: "landscape",
        risk: medium,
        class: lexical,
        generation: gpt-4,
        first_observed: 2023,
        note: "As metaphor. Literal geographic use is fine; longest-match on 'ever-evolving' and 'in today's' families handles the worst compounds.",
      }
    - {
        phrase: "realm",
        risk: medium,
        class: lexical,
        generation: gpt-4,
        first_observed: 2023,
      }
    - {
        phrase: "vibrant",
        risk: medium,
        class: lexical,
        generation: gpt-4o,
        first_observed: 2023,
      }
    - {
        phrase: "boasts",
        risk: high,
        class: lexical,
        generation: gpt-4,
        first_observed: 2023,
        note: "Part of the copular-avoidance family: the model reaches for anything other than 'has'.",
      }
    - {
        phrase: "crucial",
        risk: medium,
        class: lexical,
        generation: gpt-4o,
        first_observed: 2023,
      }
    - {
        phrase: "valuable",
        risk: low,
        class: lexical,
        generation: gpt-4,
        first_observed: 2023,
      }
    - {
        phrase: "foster",
        risk: medium,
        class: lexical,
        generation: gpt-4o,
        first_observed: 2024,
      }
    - {
        phrase: "fostering",
        risk: medium,
        class: lexical,
        generation: gpt-4o,
        first_observed: 2024,
      }
    - {
        phrase: "align with",
        risk: medium,
        class: lexical,
        generation: gpt-4o,
        first_observed: 2024,
      }
    - {
        phrase: "emphasizing",
        risk: high,
        class: lexical,
        generation: gpt-5,
        first_observed: 2024,
        note: "One of four items present in all of gpt-4o and gpt-5 observations; the current-generation core.",
      }
    - {
        phrase: "enhance",
        risk: high,
        class: lexical,
        generation: gpt-5,
        first_observed: 2024,
      }
    - {
        phrase: "highlighting",
        risk: high,
        class: lexical,
        generation: gpt-5,
        first_observed: 2024,
      }
    - {
        phrase: "showcasing",
        risk: high,
        class: lexical,
        generation: gpt-5,
        first_observed: 2024,
      }
    - {
        phrase: "harness",
        risk: medium,
        class: lexical,
        generation: gpt-5,
        first_observed: 2025,
      }
    - {
        phrase: "navigate the",
        risk: medium,
        class: lexical,
        generation: gpt-5,
        first_observed: 2025,
      }
    - {
        phrase: "dive into",
        risk: medium,
        class: lexical,
        generation: gpt-5,
        first_observed: 2025,
      }
    - {
        phrase: "additionally",
        risk: high,
        class: transition,
        generation: gpt-4,
        first_observed: 2023,
        note: "Default connective across every generation. Replace with 'also', or with nothing.",
        replacements: [also],
      }
    - {
        phrase: "furthermore",
        risk: high,
        class: transition,
        generation: gpt-4,
        first_observed: 2023,
        replacements: [also, and],
      }
    - {
        phrase: "moreover",
        risk: high,
        class: transition,
        generation: gpt-4,
        first_observed: 2023,
        replacements: [also, and],
      }
    - {
        phrase: "consequently",
        risk: medium,
        class: transition,
        generation: gpt-4,
        first_observed: 2023,
        replacements: [so],
      }
    - {
        phrase: "subsequently",
        risk: medium,
        class: transition,
        generation: gpt-4,
        first_observed: 2023,
        replacements: [then, next],
      }
```

### 2.7 `prescribed_phrases` — INFO, feeds the writer prompt

**Deliberately minimal, and structural rather than expressive.**

A prescribed catchphrase becomes a formula the instant it is prescribed. Fifty articles opening with
the same wry aside is a new tell, manufactured by the pack that was supposed to prevent one. Voice
comes from specific facts, not from a phrase bank (P4). So this set holds grammatical forms and
function words only. No personality, no openers, no signature moves.

The human-voice _techniques_ the source system documents — breaking a pattern on the third repetition,
self-correction, incomplete sentences, parenthetical asides, admitting what did not work — are real
and are kept. They live in section 3 as structural guidance, where they cannot degrade into a
vocabulary list.

```yaml
prescribed_phrases:
  rule_id: LANG-EN-07
  forbidden: false
  default_status: hypothesis
  updated_at: 2026-08-07
  next_review: 2026-11-05
  severity: INFO
  items:
    - {
        phrase: "don't",
        risk: low,
        class: contraction,
        note: "Contractions are mandatory in English body copy; their absence is itself a machine marker.",
      }
    - { phrase: "won't", risk: low, class: contraction }
    - { phrase: "can't", risk: low, class: contraction }
    - { phrase: "isn't", risk: low, class: contraction }
    - { phrase: "doesn't", risk: low, class: contraction }
    - { phrase: "didn't", risk: low, class: contraction }
    - { phrase: "it's", risk: low, class: contraction }
    - { phrase: "that's", risk: low, class: contraction }
    - { phrase: "you're", risk: low, class: contraction }
    - { phrase: "we're", risk: low, class: contraction }
    - { phrase: "they're", risk: low, class: contraction }
    - { phrase: "we've", risk: low, class: contraction }
    - { phrase: "you'll", risk: low, class: contraction }
    - {
        phrase: "and",
        risk: low,
        class: simple_transition,
        scope: sentence_internal,
      }
    - {
        phrase: "but",
        risk: low,
        class: simple_transition,
        scope: sentence_internal,
      }
    - {
        phrase: "so",
        risk: low,
        class: simple_transition,
        scope: sentence_internal,
      }
    - {
        phrase: "also",
        risk: low,
        class: simple_transition,
        scope: sentence_internal,
      }
    - {
        phrase: "next",
        risk: low,
        class: simple_transition,
        scope: sentence_internal,
      }
    - {
        phrase: "then",
        risk: low,
        class: simple_transition,
        scope: sentence_internal,
      }
```

`scope: sentence_internal` matters. These are prescribed as replacements for
`additionally`/`furthermore`/`moreover` inside a passage. They are not endorsed as **section**
openers, where a bare contrastive conjunction has the same extraction problem as an anaphor.

**Invariant check.** No string in `prescribed_phrases` appears in any forbidden set under this pack's
normalization. The near-collisions are all contraction-versus-pronoun pairs (`it's`/`it`,
`that's`/`that`, `they're`/`they`), which stay distinct only because internal apostrophes are
preserved. `also` is prescribed precisely as the replacement for `additionally`, which is forbidden;
the two are different strings and the pairing is intentional.

---

## 3. Structural rules

| ID         | Rule                                                                                                               | Threshold                                            | Severity |
| ---------- | ------------------------------------------------------------------------------------------------------------------ | ---------------------------------------------------- | -------- |
| **EN-S01** | Headings in sentence case. Capitalize the first word, proper nouns, brands and acronyms only                       | Title Case headings = 0                              | WARN     |
| **EN-S02** | No identical structure repeated more than twice in a row. On the third occurrence, break the pattern               | runs > 2                                             | WARN     |
| **EN-S03** | Lists of exactly three items                                                                                       | > 50% of lists [expert judgement, needs calibration] | WARN     |
| **EN-S04** | Item-length symmetry within a list                                                                                 | σ of item length < 3 words                           | WARN     |
| **EN-S05** | List items shaped `**Bold lead-in:** text`                                                                         | > 40% of all items [source: EVIDENCE.md#e03-ai-detection-and-humanization]           | WARN     |
| **EN-S06** | Mechanical step sequences with near-identical heading lengths                                                      | σ of step-heading length < 2 words                   | WARN     |
| **EN-S07** | Opening paragraph defines the headline term back at the reader                                                     | = 0                                                  | WARN     |
| **EN-S08** | Closing section that introduces no claim absent from the body                                                      | = 0                                                  | WARN     |
| **EN-S09** | Elegant variation: an already-introduced name replaced by a descriptor ("the search giant", "the veteran analyst") | > 2 occurrences                                      | WARN     |
| **EN-S10** | Horizontal rule immediately preceding a heading                                                                    | = 0                                                  | INFO     |
| **EN-S11** | Emoji outside quoted material                                                                                      | = 0                                                  | WARN     |

**EN-S01, why it earns a rule of its own.** Title Case in headings is the single most reliable
formatting marker in English machine output, and it is trivially auto-fixable, which is why it stays a
WARN rather than a BLOCK. It is also strictly English-bound: languages that do not capitalize
mid-sentence have no equivalent defect, and a pack for such a language must not carry this rule.

**On human-voice techniques.** These are the moves that produce English prose a reader recognizes as
written by a person. They are guidance for the writer, not machine-checkable rules, and they are
recorded here rather than in `prescribed_phrases` so they cannot ossify into a phrase list:

- Break the pattern on the third repetition rather than completing the triad.
- Kitchen-level detail instead of a category ("an e-commerce site selling hiking gear, about 200
  pages, mostly product listings" beats "one of our clients").
- Uneven paragraph lengths: some one sentence, some five.
- Self-correction in the open ("a 40% improvement — closer to 38%, actually").
- Admitting what did not work, what took longer than expected, who never replied.
- Emotional reaction to a real number, where a real number exists.
- Parenthetical asides.

The last three do double duty. A model writing on inertia does not volunteer failures, does not argue
against its own product, and does not report the unrounded number. Those passages are close to
impossible to generate without fabricating, which is exactly why they read as human — and exactly why
they must never be fabricated (P1).

**Case-study realism.** A case study is suspect when it shows round numbers, a clean arc from problem
to happy ending, no complications, and no mention of what failed. The specification transfers from the
source system unchanged: unrounded figures, the count that did not respond, the step that took six
weeks instead of one.

---

## 4. Punctuation

```yaml
punctuation:
  updated_at: 2026-08-07
  next_review: 2026-11-05
  rules:
    - id: EN-P01
      description: "Em-dash (U+2014) in body prose"
      threshold: 0
      severity: WARN
      basis: house_rule
      exportable: false
    - id: EN-P02
      description: "Curly quotes and apostrophes inconsistent with the rest of the site corpus"
      threshold: "any, when the corpus baseline is straight"
      severity: WARN
      basis: "[source: EVIDENCE.md#e03-ai-detection-and-humanization]"
      exportable: false
    - id: EN-P03
      description: "Trailing ellipsis in body prose (chat-assistant register)"
      threshold: "> 1 per 1000 words [expert judgement, needs calibration]"
      severity: INFO
      exportable: false
    - id: EN-P04
      description: "Serial comma usage inconsistent within a single document"
      threshold: "mixed within one document"
      severity: INFO
      basis: house_style
      exportable: false
```

**EN-P01 is a house rule, and the pack says so out loud.** The evidence supports high em-dash
_density_ as one formatting marker among several. It does not support a categorical ban. The ban is a
project style decision, adopted because it is unambiguous and cheap to enforce, and a project may
downgrade it to a density threshold in its own configuration. It is recorded as `basis: house_rule`
rather than dressed up as a finding.

**EN-P01 is WARN, and it was BLOCK until this revision.** A house rule cannot hold a publication
gate. `00-principles.md` caps everything in a language pack touching vocabulary, syntax, punctuation
or form statistics at WARN, and grants exactly one exception: `status: deterministic`, for facts
about the writing system rather than claims about frequency. A stylistic preference the pack itself
labels `house_rule` is the clearest possible case of what the cap is for — gating publication on a
style score is P3's failure mode with our own detector substituted for a purchased one. The rule
still fires, still appears in the review pack, and a human still decides. It no longer stops a draft
on its own authority.

`anaphora_openers` keeps BLOCK for the opposite reason: "does this section open with a bare
demonstrative" is verifiable by inspection rather than by counting, it is declared
`default_status: deterministic`, and it serves WRT-32, a structural extractability rule. The
distinction is not severity shopping — it is whether the claim is a fact or a frequency.

**EN-P01 must never be exported.** Every rule in this block carries `exportable: false`, and this one
carries the scar. In Cyrillic-script languages the dash is grammatically obligatory in the copular
construction «Х — це У». Porting this rule to Ukrainian once converted 349 grammatically correct
dashes into commas and broke the text. A Cyrillic pack measures anomalous dash _density_ and never
bans the character.

Invisible characters, tool residue and UTM tails are language-independent and are handled by the core
(`05-writing-core.md` group F). They are not repeated here.

---

## 5. Statistical form metrics, English-calibrated

Mirrors `05-writing-core.md` group E with English ranges. Computed on sentences outside quotations,
code and tables, with Unicode-aware tokenization (P5).

```yaml
form_metrics:
  updated_at: 2026-08-07
  next_review: 2026-11-05
  calibration_status: uncalibrated
  corpus_size_docs: 0
  metrics:
    - {
        id: WRT-40,
        description: "σ of sentence length in words",
        warn_below: 6.0,
        provenance: "[source: EVIDENCE.md#e03-ai-detection-and-humanization]",
      }
    - {
        id: WRT-41,
        description: "share of sentences 12–22 words",
        warn_above: 0.65,
        provenance: "[expert judgement, needs calibration]",
      }
    - {
        id: WRT-42,
        description: "share of paragraphs of equal length ±1 sentence",
        warn_above: 0.60,
        provenance: "[expert judgement, needs calibration]",
      }
    - {
        id: WRT-43,
        description: "repeated sentence openers, first two words",
        warn_above: 0.12,
        provenance: "[expert judgement, needs calibration]",
      }
    - {
        id: WRT-44,
        description: "type-token ratio over a 500-word window",
        warn_below: 0.38,
        provenance: "[expert judgement, needs calibration]",
      }
    - {
        id: WRT-45,
        description: "consecutive lists with no prose bridge",
        warn_above: 2,
        provenance: "[source: EVIDENCE.md#e03-ai-detection-and-humanization]",
      }
    - {
        id: WRT-46,
        description: "share of lists containing exactly three items",
        warn_above: 0.50,
        provenance: "[expert judgement, needs calibration]",
      }
    - {
        id: EN-F01,
        description: "share of passive constructions (English-specific detection)",
        warn_above: 0.18,
        provenance: "[expert judgement, needs calibration]",
      }
  reference_points:
    - "Machine mean sentence length observed at 37+ words (ChatGPT) and 26 words (DeepSeek); human non-fiction 15–20 words with high variance. [internal observation, unpublished: the owner's production rules]"
    - "Lexical density: human 0.5–0.6; machine output reported close to 1.0. [internal observation, unpublished] — unverified, no methodology given. Not used as a threshold."
```

Every one of these is a hypothesis until the first observation run. Until `calibration_status` reaches
`calibrated`, run `draft_score.py --observe`: compute everything, block nothing, accumulate the
distribution for the niche.

**These metrics never block publication.** They sit one step from what P3 forbids, since detectors were
historically built on exactly these features. The separation holds only while they stay diagnostic. If
anyone starts tuning drafts to hit a sentence-length variance target, the metric has become the thing
the doctrine prohibits and must be withdrawn rather than defended.

---

## 6. What must never be copied from this pack

**The em-dash ban (EN-P01).** English-only. See section 4 and the 349-replacement precedent.

**Title Case detection (EN-S01).** Only meaningful in languages that capitalize headline words. Absent
as a defect in Cyrillic-script languages; a mechanical port produces noise.

**Contractions as prescribed forms.** English-specific morphology. Most languages have no equivalent,
and requiring one produces nonsense.

**The vocabulary lists in their entirety.** `delve` is a statistical artefact of English training
corpora. Its translation into another language carries none of that history and will fire on ordinary
human writing. Vocabulary is derived from a corpus in the target language or it is not derived at all.

**The passive-voice threshold (EN-F01).** Passive construction and detection differ structurally
across languages; both the measurement and the number are English-bound.

**What does travel:** the _shape_ of the seven sets, the invariant, the requirement that vocabulary be
generation-versioned and dated, and the discipline that thresholds carry provenance markers. Those are
contract, not content.

---

## 7. The prescribed-versus-forbidden ruling: "here's the thing"

The source system contained a live contradiction. Its copywriting playbook (§13.11) prescribed
conversational asides and offered **"But here's the thing…"** as an example. Its stop-rules forbade
"Here's the thing…" twice, independently, as a cliché (§1.5) and as a bridge (§3.5). One phrase sat in
both a prescribed and a forbidden list. A writer could not satisfy both, and the review board's verdict
on any given draft became a coin flip.

**Ruling: the forbidding side wins. The phrase is in `hedge_phrases`, class `meta_bridge`, risk
`critical`, and appears nowhere in `prescribed_phrases`.**

Four reasons, in order of weight:

1. **The prohibition was reached twice, independently.** Two separate analyses of the same corpus
   arrived at the same phrase from different directions. The prescription appears once, as a single
   illustrative example inside a list of twelve techniques. Convergent judgement outranks an
   illustration.
2. **The prohibition's rationale is general; the prescription's is not.** "Remove meta-commentary about
   what you are about to do — just do it" is a principle that holds for every phrase of this shape.
   "Here's the thing" announces an insight rather than delivering one. The rule survives the phrase.
3. **Nothing of value is lost.** The prescription's purpose was human voice through conversational
   register. That purpose is preserved in full, in section 3, as technique rather than vocabulary. Only
   the single most worn instance is discarded.
4. **A prescribed catchphrase defeats its own purpose (P4).** Voice comes from specificity. A phrase
   that is mandated stops being voice and becomes formula — and once every article carries it, the pack
   has produced a new machine marker with its own hands.

**The structural fix matters more than the ruling.** This class of contradiction cannot recur, for two
reasons. `prescribed_phrases` now holds only contractions and function words, so there is no catchphrase
inventory to collide with. And `rules_lint.py` computes the intersection at build time, so a collision
becomes a failed build rather than a disagreement discovered months later in a review verdict — which
is the whole point of P8: nobody noticed the original contradiction because nobody was counting.

---

## 8. Provenance, gaps and review

**Sources.**

| Source                                                                                                                                           | What was taken                                                                                                   |
| ------------------------------------------------------------------------------------------------------------------------------------------------ | ---------------------------------------------------------------------------------------------------------------- |
| [Wikipedia:Signs of AI writing](https://en.wikipedia.org/wiki/Wikipedia:Signs_of_AI_writing)                                                     | generational vocabulary, syntactic markers, formatting markers, closing formulas. Collective editorial practice. |
| Juzek T., Ward Z., ["Why Does ChatGPT 'Delve' So Much?"](https://aclanthology.org/2025.coling-main.426/), COLING 2025, Florida State University  | the mechanism behind lexical over-representation, and therefore the case for versioning the list                 |
| [arXiv:2502.11614](https://arxiv.org/abs/2502.11614) — multilingual human detection, 9 languages, 19 annotators, 87.6% human accuracy            | the three axes that actually separate human from machine text: concreteness, cultural nuance, diversity          |
| [arXiv:2602.05769](https://arxiv.org/abs/2602.05769) — contemporary detectors operate effectively without relying on perplexity                  | the basis for excluding every perplexity-targeting technique                                                     |
| `ai_docs/marketing/ai-content-stop-rules.md` v1.0 (2026-05-19), `lp-copywriting-rules.md` v1.0 — production rules on a live site, via `[internal observation, unpublished]` | risk ratings, forbidden openers/closings/fillers/clichés/bridges, structural rules, case-study realism spec      |
| `EVIDENCE.md#e03-ai-detection-and-humanization` §4, §7, §9                                                                                               | consolidated English marker set, form-metric thresholds, the snake-oil determination                             |

**Known gaps, stated rather than papered over.**

1. **The evidence is OpenAI-centric.** No source we found characterizes the lexical signature of
   Anthropic, Google or Meta models separately. This pack under-detects them by an unknown margin. A
   clean run is not evidence that a text was written by a person.
2. **Risk ratings are editorial judgement, not measurement.** The critical/high/medium assignments come
   from a working stop-list whose author did not publish a derivation. They rank plausibly; they are not
   effect sizes.
3. **Every form-metric threshold is uncalibrated.** They come from literature and practice, not from a
   corpus in any specific niche. The first observation run replaces them with local values in
   `.kiln/thresholds.yml` (P10: thresholds stay local).
4. **Density thresholds for `hedge_phrases` and `promo_lexicon` are guesses.** Only the
   `generational_stopwords` figure of 2.0 per 1000 words has a stated source.
5. **The contract's invariant omits `vague_attribution`** from the forbidden union. This pack satisfies
   the invariant as written, and also happens to have no collision with `vague_attribution` — but the
   omission looks like an oversight in `05-writing-core.md` §6, and a future pack could legally prescribe
   "studies show". Flagged for the doctrine maintainer rather than fixed here: amending the contract is a
   `RULE-CHANGE.md` PR, not a language pack's business (P10).

**Review.** `next_review: 2026-11-05`. Vocabulary is generation-bound and decays within months; the
source system's own stop-list carried a review date that had lapsed by five months, which is precisely
the failure this field exists to prevent. An expired pack raises a WARN on every run and its findings
should be treated as suspect until re-derived.

---

## 9. What this pack must not do

| Prohibition                                                                      | Basis                                                                                     |
| -------------------------------------------------------------------------------- | ----------------------------------------------------------------------------------------- |
| Gate publication on an external AI detector                                      | P3. Correlation of AI share with ranking position is 0.011, which is noise.               |
| Route text through a "humanizer"                                                 | P3. No independent measurement exists; every published test is an affiliate test.         |
| Optimize for perplexity, entropy or burstiness                                   | P3, and arXiv:2602.05769 — detectors no longer rely on perplexity. The technique is dead. |
| Prescribe or require a word count                                                | `05-writing-core.md` §4. Named by Google directly as a signal of search-first content.    |
| Let any set in section 2 block publication, except EN-P01 and `anaphora_openers` | §11-2 of the writing core: form metrics are diagnostic, never a target.                   |
| Carry any rule from this pack into a non-English pack                            | P5, section 6, and the 349-replacement precedent.                                         |
