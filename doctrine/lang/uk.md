# Language pack: Ukrainian (`uk`)

> Subordinate to `00-principles.md` and to the language pack contract in `05-writing-core.md` §6.
> This document is written in English because the doctrine is English-only (P5). Everything it
> _contains_ — every term, pattern and example — is Ukrainian, because the content produced under
> this pack is Ukrainian.

**Version:** 0.1.0 · **Date:** 2026-08-07 · **Review:** mandatory every 90 days
**Locale:** `uk-UA` · **Loaded when:** `.kiln/project.yml` declares a `uk` locale
**Consumed by:** `scripts/draft_score.py`, `scripts/rules_lint.py`, the writer prompt, the voice
review lens (`06-review-lenses.md`)

---

## §1. Evidence position — read this before using anything below

**There is no published research on machine-text markers in Ukrainian.** Not a weak body of
research: none. At the time of collection there was no Ukrainian version of the Wikipedia
signs-of-generated-text page, and no academic work targeting the language. The reconnaissance
report states this outright and lists it as a candidate for original research.
→ `EVIDENCE.md#e03-ai-detection-and-humanization` §6, §Open questions

This pack is therefore built from three sources, in descending order of trust:

| Source                         | What it gives                                                      | Trust                                                                         |
| ------------------------------ | ------------------------------------------------------------------ | ----------------------------------------------------------------------------- |
| Language-independent metrics   | sentence-length dispersion, opener repetition, claim density, TTR  | inherited from `05-writing-core.md` group E; thresholds still English-derived |
| Russian generated-text markers | semantic constructions that models reproduce across both languages | analogy only; every carry-over is a hypothesis until measured                 |
| The pilot's own corpus         | real distributions for this language and this niche                | the only thing that will ever be authoritative here                           |

Three consequences that are binding, not advisory:

1. **Every lexical entry in this pack starts life as a hypothesis.** Each carries an explicit
   `status` field. An entry may not be treated as a finding because it appears in a doctrine file.
2. **No stylistic rule in this pack may block publication.** Ceiling is `WARN`, and until §8
   calibration completes the ceiling is `INFO`. This follows from P3 and from
   `05-writing-core.md` §11-2, and it is reinforced locally: detector false-positive rates are
   higher on Ukrainian than on English, so the one automated opinion available to us is the least
   reliable one we could lean on. → `EVIDENCE.md#e03-ai-detection-and-humanization` §1.5, §6
3. **A direct calque of the English stop-list is forbidden.** It produces false positives on
   correct Ukrainian. §4 lists the four specific ways this goes wrong, each as a prohibition.

---

## §2. Contract compliance

`05-writing-core.md` §6 requires every pack to declare seven named sets under fixed keys. All seven
are declared in §3. Three additional sets are declared as pack-local extensions, marked `uk-local`.

**Key names corrected 2026-08-07, and the failure is worth recording.** This pack originally listed
its entries under `entries:` and named each surface form `term:`, where the contract says `items:`
and `phrase:`. Ten sets, all of them. Nothing failed: the YAML parsed, the file read as complete,
and every consumer reading the contract received an **empty pack**. The Ukrainian locale therefore
had no lexical rules at all while appearing fully specified, and a clean scoring run against it was
indistinguishable from a clean run against a working pack. WRT-06 now reports this class of defect
from the loader, which is the only place that can tell "no matches" from "no rules were read".

**Rule identifiers added 2026-08-07.** Each set declares `rule_id: LANG-UK-NN`. Findings are counted
per rule in `.kiln/rules-stats.json` and feed the override rates P8 uses to retire rules; an
identifier synthesised at runtime from a set key cannot be counted, because nothing outside the code
that invented it knows the identifier exists. The numbers are assigned in declaration order and are
immutable: a set whose meaning changes takes a new identifier rather than reusing this one.

**Dependency resolved:** `doctrine/lang/_template.md` did not exist when this pack was first
written. It exists now and this pack conforms to it. Where the two ever diverge, the template and
`05-writing-core.md` §6 win and this pack is amended by PR.

**Required change to `rules_lint.py`.** The invariant in §6 unions five fixed forbidden sets. It
does not know about pack-local sets, so a phrase could sit in `prescribed_phrases` and in
`russisms_calques` at the same time and the build would pass. The invariant must be restated over
_all_ sets a pack declares as forbidden:

```
prescribed_phrases ∩ ⋃(sets where forbidden: true) = ∅
```

Every set below carries an explicit `forbidden: true|false` flag so this is machine-decidable.
**Ratified 2026-08-07.** The contract in `05-writing-core.md` §6 now computes the union over every
set carrying `forbidden: true`, including pack-local sets, and `rules_lint.py` check 1 implements
it. This pack's russism and technical-defect sets are covered.

### Pack metadata

The `normalization` block is not bookkeeping. The invariant
`prescribed_phrases ∩ ⋃(forbidden sets) = ∅` asks whether two entries are **the same phrase**, and
that question has no answer until the pack says how a phrase is normalized. A pack without this
block does not fail the invariant — the invariant is undefined, which is worse, because a check that
cannot run looks exactly like a check that passed.

```yaml
lang:
  code: uk
  script: Cyrl
  locales: [uk-UA]
  updated_at: 2026-08-07
  next_review: 2026-11-07
  maintainer: kiln-core

  # Empty on purpose, and the emptiness is the point. No Ukrainian corpus has been
  # observed for this pack; every lexical entry is carried by analogy from Russian.
  # A populated list here would claim evidence that does not exist (§1).
  observed_generations: []
  observed_families: []
  evidence_basis: >
    No published research on machine-text markers in Ukrainian exists (EVIDENCE.md#e03-ai-detection-and-humanization).
    Lexical entries are reasoned from the Russian generated-text marker list via
    EVIDENCE.md#e03-ai-detection-and-humanization and carry basis: ru_analogy. Orthographic entries in 3.10 are facts
    about the Ukrainian writing system and carry basis: orthographic.
    Structural metrics are inherited from 05-writing-core.md group E; their
    thresholds are English-derived and are held at INFO until §8 calibration.

  normalization:
    case: lower
    unicode_form: NFC
    collapse_whitespace: true
    strip_trailing_ellipsis: true
    strip_terminal_punctuation: true
    tokenizer: unicode_words
    matching: longest_match_wins

    # LOAD-BEARING. The apostrophe is part of the Ukrainian word: «п'ять»,
    # «об'єкт», «зв'язок». Stripping it merges distinct words and splits single
    # ones, and every density, TTR and n-gram number downstream is then wrong
    # while still looking plausible (UK-02).
    strip_internal_apostrophes: false
    apostrophe_chars: ["’", "ʼ"]

    # UNRESOLVED, and declared rather than omitted so the hole is visible.
    # Ukrainian inflects for seven cases and two numbers, so surface-form
    # comparison makes the one-anchor-one-URL invariant (P6, 07-linking.md)
    # report clean while guaranteeing nothing: «кредит онлайн» and
    # «кредиту онлайн» never collide, so no conflict is ever detected.
    # Candidates named in UK-03 are unevaluated. Whatever is chosen must be
    # pinned by version in .kiln/project.yml, because a lemmatizer upgrade
    # silently re-partitions the anchor registry.
    lemmatizer: unresolved
```

**What `lemmatizer: unresolved` buys.** Nothing operationally — the anchor invariant remains
ineffective for this locale until a tool is chosen. What it buys is that the gap is now a declared
value a script can read and refuse to proceed on, rather than an absent field that reads as handled.
This is the single highest-priority open item in the pack (§11-6).

### Entry schema

```yaml
- phrase: "…" # the Ukrainian surface form or a short label
  match: "…" # literal or regex actually applied
  match_mode: phrase # phrase | density | regex
  risk: high # high | medium | low
  status: hypothesis # see below
  basis: ru_analogy # ru_analogy | language_independent | pilot_corpus | orthographic
  note: "…"
```

`status` values:

| Value           | Meaning                                                                              |
| --------------- | ------------------------------------------------------------------------------------ |
| `hypothesis`    | no observation in a Ukrainian corpus; carried over by analogy or reasoning           |
| `observed`      | seen in our own corpus, but frequency not yet compared against a human baseline      |
| `calibrated`    | threshold derived from measured distributions in this locale and this niche          |
| `deterministic` | follows from Ukrainian orthography, not from frequency; no calibration is meaningful |

**`deterministic` was proposed by this pack and ratified into the shared schema on 2026-08-07.** The
other three values are all statistical, and labelling "the letter `ы` does not exist in the Ukrainian
alphabet" as a _hypothesis_ would be false. It is now part of the contract in `05-writing-core.md`
§6 and of `doctrine/lang/_template.md`, and it is the **only** status permitted to carry `BLOCK`.

### `match_mode` and why it matters here

`phrase` — multi-word constructions that are rarely legitimate. Judged by presence.

`density` — ordinary Ukrainian words that models overproduce. **Judged by frequency per 1,000 words
and never by presence.** Banning `демонструє` or `надійний` outright bans ordinary Ukrainian. This
distinction is the single most important safeguard in the pack; a pack that loses it turns into the
calque problem of §4.

`regex` — patterns with morphological variation baked in.

---

## §3. Lexical sets

### 3.1 `anaphora_openers` — feeds WRT-32 (BLOCK)

Section-initial referential openers. WRT-32 is `BLOCK` in the core because a section opening with a
back-reference is unusable as an extracted passage (P12: extraction operates at passage level).
This is a **structural** rule, not a stylistic one, which is why it may block while §3.2–3.6 may not.

```yaml
anaphora_openers:
  rule_id: LANG-UK-01
  forbidden: true
  updated_at: 2026-08-07
  next_review: 2026-11-07
  applies_to: first sentence of a section only
  items:
    - phrase: "Це"
      match: '^Це\s'
      match_mode: regex
      risk: high
      status: hypothesis
      basis: language_independent
      note: "Bare demonstrative opener. Legitimate mid-paragraph, unusable as a section start."
    - phrase: "Цей / Ця / Це + noun"
      match: '^(Цей|Ця|Ці)\s'
      match_mode: regex
      risk: high
      status: hypothesis
      basis: language_independent
      note: "Refers to something in the previous section."
    - phrase: "Такий підхід"
      match: '^Так(ий|а|е|і)\s'
      match_mode: regex
      risk: high
      status: hypothesis
      basis: ru_analogy
      note: "Direct analogue of «Такой подход»."
    - phrase: "Він / Вона / Вони"
      match: '^(Він|Вона|Воно|Вони)\s'
      match_mode: regex
      risk: high
      status: hypothesis
      basis: language_independent
      note: "Pronoun with no antecedent inside the passage."
    - phrase: "Зазначене"
      match: "^(Зазначен|Вищезазначен|Вищенаведен)"
      match_mode: regex
      risk: high
      status: hypothesis
      basis: ru_analogy
      note: "Bureaucratic back-reference; also appears in 3.9."
    - phrase: "Наведене вище"
      match: "^Наведен(е|і) вище"
      match_mode: regex
      risk: high
      status: hypothesis
      basis: ru_analogy
      note: "—"
    - phrase: "Як було зазначено вище"
      match: "^Як (було |)(зазначено|сказано|згадано) (вище|раніше)"
      match_mode: regex
      risk: high
      status: hypothesis
      basis: ru_analogy
      note: "—"
    - phrase: "Даний"
      match: '^Дан(ий|а|е|і)\s'
      match_mode: regex
      risk: high
      status: hypothesis
      basis: ru_analogy
      note: "Calque of «данный» in the sense of «цей». Also a russism, see 3.8."
    - phrase: "Ці фактори"
      match: "^Ці (фактори|чинники|зміни|переваги|особливості)"
      match_mode: regex
      risk: high
      status: hypothesis
      basis: ru_analogy
      note: "—"
    - phrase: "Крім того"
      match: "^Крім того"
      match_mode: regex
      risk: medium
      status: hypothesis
      basis: ru_analogy
      note: "Legitimate inside a section. As a section opener it presumes the previous section."
    - phrase: "Однак"
      match: "^Однак"
      match_mode: regex
      risk: medium
      status: hypothesis
      basis: ru_analogy
      note: "Same reasoning as «Крім того»."
    - phrase: "Саме тому"
      match: "^Саме тому"
      match_mode: regex
      risk: medium
      status: hypothesis
      basis: ru_analogy
      note: "—"
```

### 3.2 `hedge_phrases` — didactic hedges

```yaml
hedge_phrases:
  rule_id: LANG-UK-02
  forbidden: true
  updated_at: 2026-08-07
  next_review: 2026-11-07
  severity_ceiling: WARN
  items:
    - phrase: "важливо зазначити"
      match: "важливо (зазначити|відзначити|розуміти|враховувати|пам.ятати)"
      match_mode: regex
      risk: high
      status: hypothesis
      basis: ru_analogy
      note: "From «важно отметить». Highest-confidence carry-over in the set."
    - phrase: "варто зазначити"
      match: "варто (зазначити|відзначити|врахувати|підкреслити|пам.ятати)"
      match_mode: regex
      risk: high
      status: hypothesis
      basis: ru_analogy
      note: "From «стоит отметить»."
    - phrase: "слід зазначити"
      match: "(слід|необхідно) (зазначити|враховувати|відзначити)"
      match_mode: regex
      risk: high
      status: hypothesis
      basis: ru_analogy
      note: "—"
    - phrase: "зверніть увагу"
      match: "зверніть увагу"
      match_mode: density
      risk: low
      status: hypothesis
      basis: ru_analogy
      note: "Legitimate in instructional content. Density only."
    - phrase: "не забувайте, що"
      match: "не забувайте, що"
      match_mode: phrase
      risk: medium
      status: hypothesis
      basis: ru_analogy
      note: "Addressing the reader as a pupil."
    - phrase: "значення можуть відрізнятися"
      match: "значення можуть (відрізнятися|варіюватися|змінюватися)"
      match_mode: phrase
      risk: medium
      status: hypothesis
      basis: ru_analogy
      note: "Hedge that removes the informational content of a figure."
    - phrase: "у кожному випадку по-різному"
      match: "(у|в) кожному (випадку|разі) по-різному"
      match_mode: phrase
      risk: medium
      status: hypothesis
      basis: ru_analogy
      note: "—"
    - phrase: "залежить від багатьох факторів"
      match: "залежить від (багатьох|низки|цілої низки) (факторів|чинників)"
      match_mode: phrase
      risk: high
      status: hypothesis
      basis: ru_analogy
      note: "Textbook non-answer. Strong candidate for the usefulness lens, not just style."
    - phrase: "на момент мого навчання"
      match: "на момент (мого |)(навчання|останнього оновлення)"
      match_mode: phrase
      risk: high
      status: hypothesis
      basis: ru_analogy
      note: "Training-cutoff disclaimer leaking into the text. Near-zero false positives."
    - phrase: "конкретна інформація обмежена"
      match: "(конкретна|детальна) інформація (обмежена|відсутня)"
      match_mode: phrase
      risk: high
      status: hypothesis
      basis: ru_analogy
      note: "Dialogue residue."
    - phrase: "рекомендуємо проконсультуватися з фахівцем"
      match: "рекоменду(ємо|ється) (про|)консультуватися"
      match_mode: density
      risk: low
      status: hypothesis
      basis: ru_analogy
      note: >-
        CAUTION. In YMYL finance this may be a regulatory requirement rather than a filler hedge.
        Density only, and never surfaced to the voice lens without the project's `forbidden` list
        checked first. See §11.
    - phrase: "це лише загальна інформація"
      match: "це (лише|тільки) (загальна|орієнтовна) інформація"
      match_mode: density
      risk: low
      status: hypothesis
      basis: ru_analogy
      note: "Same YMYL caution as above."
```

### 3.3 `closing_formulas`

```yaml
closing_formulas:
  rule_id: LANG-UK-03
  forbidden: true
  updated_at: 2026-08-07
  next_review: 2026-11-07
  severity_ceiling: WARN
  applies_to: final 15 % of the document, or any heading
  items:
    - phrase: "На завершення"
      match: "^На завершення"
      match_mode: regex
      risk: high
      status: hypothesis
      basis: ru_analogy
      note: "From «В заключение»."
    - phrase: "Підсумовуючи"
      match: "^Підсумовуючи"
      match_mode: regex
      risk: high
      status: hypothesis
      basis: ru_analogy
      note: "From «Подводя итог». Also a dangling adverbial participle, see 3.9."
    - phrase: "Коротко кажучи"
      match: "^Коротко кажучи"
      match_mode: regex
      risk: high
      status: hypothesis
      basis: ru_analogy
      note: "—"
    - phrase: "Отже, підіб'ємо підсумки"
      match: "підіб.ємо підсумки"
      match_mode: phrase
      risk: high
      status: hypothesis
      basis: ru_analogy
      note: "—"
    - phrase: "Таким чином"
      match: "^Таким чином,"
      match_mode: regex
      risk: medium
      status: hypothesis
      basis: ru_analogy
      note: "Legitimate as a logical connective mid-text. Flagged only in the closing zone."
    - phrase: "Висновок (heading with no new claim)"
      match: '^#{1,4}\s*(Висновок|Висновки|Підсумок|Коротко про головне)'
      match_mode: regex
      risk: medium
      status: hypothesis
      basis: ru_analogy
      note: >-
        The heading is not the defect. The defect is a closing section that introduces no claim
        absent from the body. Requires the judge question in §7, not a regex verdict.
    - phrase: "Незважаючи на виклики"
      match: "незважаючи на (виклики|труднощі|певні складнощі)"
      match_mode: phrase
      risk: high
      status: hypothesis
      basis: ru_analogy
      note: "From the «Despite its challenges» template ending."
    - phrase: "Сподіваємося, ця стаття була корисною"
      match: "сподіва(ємося|юся), (ця стаття|це) (був|буд)"
      match_mode: regex
      risk: high
      status: hypothesis
      basis: ru_analogy
      note: "Dialogue residue."
    - phrase: "Сучасні ініціативи можуть допомогти"
      match: "сучасні (ініціативи|заходи|рішення) можуть допомогти"
      match_mode: phrase
      risk: high
      status: hypothesis
      basis: ru_analogy
      note: "Second half of the «Despite… however initiatives» template."
    - phrase: "повідомте, якщо потрібно"
      match: "повідомте (мене |нам |)якщо"
      match_mode: phrase
      risk: high
      status: hypothesis
      basis: ru_analogy
      note: "Dialogue residue. Near-zero false positives in published prose."
```

### 3.4 `promo_lexicon`

```yaml
promo_lexicon:
  rule_id: LANG-UK-04
  forbidden: true
  updated_at: 2026-08-07
  next_review: 2026-11-07
  severity_ceiling: WARN
  items:
    - phrase: "розташований у самому серці"
      match: "розташован(ий|а|е) (у|в) (самому |)серці"
      match_mode: phrase
      risk: high
      status: hypothesis
      basis: ru_analogy
      note: "From «расположенный в самом сердце» / «nestled in the heart of»."
    - phrase: "багатий культурною спадщиною"
      match: "багат(ий|а|е) (культурною |)спадщиною"
      match_mode: phrase
      risk: high
      status: hypothesis
      basis: ru_analogy
      note: "—"
    - phrase: "захоплива краса"
      match: "захоплив(а|ої) крас(а|и)"
      match_mode: phrase
      risk: high
      status: hypothesis
      basis: ru_analogy
      note: "—"
    - phrase: "унікальна можливість"
      match: "унікальн(а|у) можливіст(ь|ю)"
      match_mode: density
      risk: medium
      status: hypothesis
      basis: ru_analogy
      note: "Occasionally literal. Density."
    - phrase: "широкий спектр"
      match: "широк(ий|ого) спектр"
      match_mode: density
      risk: medium
      status: hypothesis
      basis: ru_analogy
      note: "From «широкий спектр» / «diverse array»."
    - phrase: "неперевершений"
      match: "неперевершен"
      match_mode: density
      risk: medium
      status: hypothesis
      basis: ru_analogy
      note: "—"
    - phrase: "інноваційний"
      match: "інноваційн"
      match_mode: density
      risk: low
      status: hypothesis
      basis: ru_analogy
      note: "Legitimate in a technology context. Density only."
    - phrase: "передовий"
      match: "передов(ий|і|их)"
      match_mode: density
      risk: low
      status: hypothesis
      basis: ru_analogy
      note: "—"
    - phrase: "надійний партнер"
      match: "надійн(ий|ого) партнер"
      match_mode: phrase
      risk: high
      status: hypothesis
      basis: ru_analogy
      note: "Corporate boilerplate."
    - phrase: "індивідуальний підхід"
      match: "індивідуальн(ий|ого) підход"
      match_mode: phrase
      risk: high
      status: hypothesis
      basis: ru_analogy
      note: "Corporate boilerplate. Very common in Ukrainian financial marketing."
    - phrase: "висока якість за доступною ціною"
      match: "(висок|найкращ).{0,20}(якіст).{0,30}(доступн|вигідн)"
      match_mode: regex
      risk: high
      status: hypothesis
      basis: ru_analogy
      note: "—"
    - phrase: "вигідні умови"
      match: "вигідн(і|их) умов"
      match_mode: density
      risk: low
      status: hypothesis
      basis: ru_analogy
      note: >-
        CAUTION for the reference pilot: this is literal vocabulary in credit comparison content.
        Density only, and the threshold must be set from the niche corpus, not from general prose.
    - phrase: "відкриває нові горизонти"
      match: "відкрива(є|ють) нові (горизонти|можливості|перспективи)"
      match_mode: phrase
      risk: high
      status: hypothesis
      basis: ru_analogy
      note: "—"
    - phrase: "не має аналогів"
      match: "не ма(є|ють) аналогів"
      match_mode: phrase
      risk: medium
      status: hypothesis
      basis: ru_analogy
      note: "Unfalsifiable claim; also a WRT-11 candidate (claim without a source)."
```

### 3.5 `vague_attribution` — reinforces WRT-11

Every entry here is simultaneously a style flag and a **factual** flag. A vague attribution is an
unsourced claim wearing a citation costume, which is P1 territory, not stylistics. Where the core
gate WRT-11 fires on the same span, WRT-11 wins and the severity is `BLOCK` — not because of this
pack, but because the claim has no source.

```yaml
vague_attribution:
  rule_id: LANG-UK-05
  forbidden: true
  updated_at: 2026-08-07
  next_review: 2026-11-07
  severity_ceiling: WARN # escalates to BLOCK via WRT-11 when no claim.id is attached
  items:
    - phrase: "галузеві звіти"
      match: "галузев(і|их) звіт"
      match_mode: phrase
      risk: high
      status: hypothesis
      basis: ru_analogy
      note: "From «отраслевые отчёты» / «industry reports»."
    - phrase: "за словами експертів"
      match: "за словами (експертів|фахівців|аналітиків)"
      match_mode: phrase
      risk: high
      status: hypothesis
      basis: ru_analogy
      note: "Unnamed expert."
    - phrase: "експерти стверджують"
      match: "(експерти|фахівці|аналітики) (стверджують|вважають|зазначають|прогнозують)"
      match_mode: phrase
      risk: high
      status: hypothesis
      basis: ru_analogy
      note: "—"
    - phrase: "деякі критики"
      match: "деякі (критики|експерти|спостерігачі)"
      match_mode: phrase
      risk: high
      status: hypothesis
      basis: ru_analogy
      note: "—"
    - phrase: "низка джерел"
      match: "(низка|ряд) джерел"
      match_mode: phrase
      risk: high
      status: hypothesis
      basis: ru_analogy
      note: "—"
    - phrase: "дослідження показують"
      match: "дослідження (показують|свідчать|демонструють)"
      match_mode: phrase
      risk: high
      status: hypothesis
      basis: ru_analogy
      note: "Legitimate only when a specific study is named in the same sentence."
    - phrase: "за різними оцінками"
      match: "за різними оцінками"
      match_mode: phrase
      risk: high
      status: hypothesis
      basis: ru_analogy
      note: "—"
    - phrase: "вважається, що"
      match: "вважається, що"
      match_mode: phrase
      risk: medium
      status: hypothesis
      basis: ru_analogy
      note: "Agentless passive attribution."
    - phrase: "прийнято вважати"
      match: "прийнято вважати"
      match_mode: phrase
      risk: medium
      status: hypothesis
      basis: ru_analogy
      note: "—"
    - phrase: "як відомо"
      match: "як відомо"
      match_mode: phrase
      risk: medium
      status: hypothesis
      basis: ru_analogy
      note: "Asserts shared knowledge to avoid sourcing it."
    - phrase: "статистика свідчить"
      match: "статистика (свідчить|показує)"
      match_mode: phrase
      risk: high
      status: hypothesis
      basis: ru_analogy
      note: "Whose statistics, as of when."
```

### 3.6 `generational_stopwords`

Per the §6 contract this set carries a `generation` field. **Generation attribution for Ukrainian is
unverified.** The English list is generation-tagged from observed corpora
(`EVIDENCE.md#e03-ai-detection-and-humanization` §4.1, Juzek & Ward, COLING 2025); no equivalent work exists for Ukrainian. The tags
below record which English generation the _semantic_ construction corresponds to, not a measured
Ukrainian frequency. Treat the tag as a pointer for re-measurement, not as evidence.

```yaml
generational_stopwords:
  rule_id: LANG-UK-06
  forbidden: true
  updated_at: 2026-08-07
  next_review: 2026-11-07
  severity_ceiling: WARN
  generation_attribution: unverified_for_uk
  density_threshold_per_1000: null # unset until §8 calibration; see §6 of this pack
  items:
    - phrase: "занурюємося у"
      match: "(занур|пірна)(имося|ємось|ємося|ьмося) (у|в)"
      match_mode: phrase
      risk: high
      status: hypothesis
      basis: ru_analogy
      generation: gpt4
      note: "Semantic analogue of «delve into» / «давайте погрузимся»."
    - phrase: "підкреслює"
      match: "підкреслю(є|ють)"
      match_mode: density
      risk: medium
      status: hypothesis
      basis: ru_analogy
      generation: gpt4
      note: "Analogue of «underscore». Ordinary verb; density only."
    - phrase: "демонструє"
      match: "демонстру(є|ють)"
      match_mode: density
      risk: medium
      status: hypothesis
      basis: ru_analogy
      generation: gpt4o
      note: "Analogue of «showcasing»."
    - phrase: "сприяє"
      match: "сприя(є|ють)"
      match_mode: density
      risk: medium
      status: hypothesis
      basis: ru_analogy
      generation: gpt4o
      note: "Analogue of «fostering»."
    - phrase: "забезпечує"
      match: "забезпечу(є|ють)"
      match_mode: density
      risk: medium
      status: hypothesis
      basis: ru_analogy
      generation: gpt4o
      note: "Analogue of «ensuring». Very frequent in Ukrainian corporate prose independently."
    - phrase: "відображає"
      match: "відобража(є|ють)"
      match_mode: density
      risk: low
      status: hypothesis
      basis: ru_analogy
      generation: gpt4o
      note: "Analogue of «reflecting»."
    - phrase: "яскравий"
      match: "яскрав(ий|им|ою)"
      match_mode: density
      risk: low
      status: hypothesis
      basis: ru_analogy
      generation: gpt4
      note: "Analogue of «vibrant»."
    - phrase: "комплексний підхід"
      match: "комплексн(ий|ого) підход"
      match_mode: phrase
      risk: medium
      status: hypothesis
      basis: ru_analogy
      generation: gpt5
      note: "—"
    - phrase: "невід'ємна частина"
      match: "невід.ємн(а|ою) частин"
      match_mode: phrase
      risk: high
      status: hypothesis
      basis: ru_analogy
      generation: gpt4
      note: "—"
    - phrase: "розкрити потенціал"
      match: "розкри(ти|ває) (весь |повний |)потенціал"
      match_mode: phrase
      risk: high
      status: hypothesis
      basis: ru_analogy
      generation: gpt5
      note: "Analogue of «unlock the potential»."
    - phrase: "стрімко змінюваний ландшафт"
      match: "(стрімко |постійно |)(змінюваном|мінлив).{0,10} (ландшафт|середовищ)"
      match_mode: regex
      risk: high
      status: hypothesis
      basis: ru_analogy
      generation: gpt4
      note: "Analogue of «ever-evolving landscape»."
    - phrase: "відіграє важливу роль"
      match: "відігра(є|ють) (важливу|ключову|значну|вирішальну) роль"
      match_mode: phrase
      risk: high
      status: hypothesis
      basis: ru_analogy
      generation: gpt4
      note: "From «играет важную роль». One of the strongest carry-overs."
    - phrase: "має вирішальне значення"
      match: "ма(є|ють) (вирішальне|ключове|важливе) значення"
      match_mode: phrase
      risk: high
      status: hypothesis
      basis: ru_analogy
      generation: gpt4
      note: "—"
    - phrase: "є ключовим фактором"
      match: "є ключов(им|ими) (фактор|чинник)"
      match_mode: phrase
      risk: high
      status: hypothesis
      basis: ru_analogy
      generation: gpt4o
      note: "—"
    - phrase: "слугує нагадуванням"
      match: "(слугує|виступає|є) (нагадуванням|свідченням|відображенням|символом)"
      match_mode: phrase
      risk: high
      status: hypothesis
      basis: ru_analogy
      generation: gpt4
      note: "From «служит напоминанием» / «is a testament to»."
    - phrase: "не лише … але й"
      match: "не (лише|тільки) [^,.]{1,60} (але|а) й"
      match_mode: regex
      risk: medium
      status: hypothesis
      basis: ru_analogy
      generation: gpt4
      note: >-
        Negative parallelism. Grammatical and common in Ukrainian; density only, and the threshold
        must come from the human baseline corpus, not from the English rule.
    - phrase: "це не просто X — це Y"
      match: "це не просто [^,.]{1,40}[,—-] це"
      match_mode: regex
      risk: high
      status: hypothesis
      basis: ru_analogy
      generation: gpt4o
      note: "The construction is the marker, not the dash. See §4.1."
```

### 3.7 `prescribed_phrases`

Patterns the writer prompt is instructed to prefer. Deliberately kept small: a prescribed list that
grows becomes a template, and templates are the thing we are trying to avoid. These are **shapes**,
not fillers — each forces a concrete fact into the sentence.

```yaml
prescribed_phrases:
  rule_id: LANG-UK-07
  forbidden: false
  updated_at: 2026-08-07
  next_review: 2026-11-07
  items:
    - phrase: "за даними <named source> від <date>"
      match: 'за даними .{2,60} від \d{1,2}\.\d{2}\.\d{4}'
      match_mode: regex
      risk: null
      status: hypothesis
      basis: language_independent
      note: >-
        Attribution shape that carries a named source and a date. The direct antidote to 3.5.
        Not to be confused with the training-cutoff disclaimer in 3.2: the defect there is
        «на момент мого навчання», not a dated statement about the world.
    - phrase: "станом на <date>"
      match: 'станом на \d{1,2}\.\d{2}\.\d{4}'
      match_mode: regex
      risk: null
      status: hypothesis
      basis: language_independent
      note: >-
        Correct and expected in Ukrainian financial content, where every rate is time-bound.
        Explicitly NOT a marker, despite its Russian counterpart «по состоянию на» appearing in
        the ru list — there the flagged form is the undated training disclaimer.
    - phrase: "ми перевірили / ми порахували / ми зафіксували"
      match: "ми (перевірили|порахували|зафіксували|виміряли|запитали)"
      match_mode: phrase
      risk: null
      status: hypothesis
      basis: language_independent
      note: "First-party framing. Only permitted when an artifact_id backs it (05 §5)."
    - phrase: "у нашій вибірці з <N>"
      match: '(у|в) наш(ій|ому) (вибірці|наборі|аналізі) (з|із) \d+'
      match_mode: regex
      risk: null
      status: hypothesis
      basis: language_independent
      note: "Forces the sample size into the sentence."
    - phrase: "це не спрацювало"
      match: "(це |)не спрацювало"
      match_mode: phrase
      risk: null
      status: hypothesis
      basis: language_independent
      note: >-
        Admission of a negative result. Models do not volunteer these; carried over from the
        owner's existing spec for what makes a case study real ([internal observation, unpublished]).
    - phrase: "нижче наведено методику"
      match: "(нижче |)наведено (методику|порядок перевірки|як ми це перевіряли)"
      match_mode: phrase
      risk: null
      status: hypothesis
      basis: language_independent
      note: "The Wirecutter «how we tested» section, which cannot be faked without fabrication."
    - phrase: "Х — це У"
      match: '^\S.{2,60} — це '
      match_mode: regex
      risk: null
      status: deterministic
      basis: orthographic
      note: >-
        The definitional construction. Listed as PRESCRIBED specifically to make the §4.1
        prohibition machine-visible: any rule that penalises this shape is wrong for Ukrainian.
    - phrase: "порівняно з <named competitor/benchmark>"
      match: "порівняно з "
      match_mode: phrase
      risk: null
      status: hypothesis
      basis: language_independent
      note: "Forces a named comparison rather than an absolute superlative (antidote to 3.4)."
    - phrase: "джерело: <URL>"
      match: "[Дд]жерело: https?://"
      match_mode: regex
      risk: null
      status: hypothesis
      basis: language_independent
      note: "Inline source marker."
    - phrase: "ми не змогли перевірити"
      match: "ми не (змогли|мали змоги) перевірити"
      match_mode: phrase
      risk: null
      status: hypothesis
      basis: language_independent
      note: >-
        Explicit statement of a knowledge boundary. Mirrors the mandatory `open_questions` field
        in research_packet.json (05 §2.1).
```

**Invariant check.** No entry above appears in 3.1–3.6 or 3.8–3.9. The two near-collisions are
deliberate and documented: `станом на` versus the training-cutoff hedge, and `Х — це У` versus the
dash-density rule. Both are the exact traps §4 exists to prevent, so they are pinned here where
`rules_lint.py` will see them.

### 3.8 `russisms_calques` — `uk-local`

Markers that the text was translated rather than written. Not a style preference: a machine
pipeline that goes through Russian, or a model whose Ukrainian is thin, produces these at a rate
human editors do not. This is the set with the highest expected value for Ukrainian **and** the
highest false-positive risk, because usage is genuinely contested for some items and because
quotation is a legitimate context (§4.4).

```yaml
russisms_calques:
  rule_id: LANG-UK-08
  forbidden: true
  updated_at: 2026-08-07
  next_review: 2026-11-07
  severity_ceiling: WARN
  never_applies_inside: [quotation, code, cited_verbatim]
  items:
    - phrase: "являється"
      match: "явля(є|ються)ться|являється|являються"
      match_mode: phrase
      risk: high
      status: hypothesis
      basis: ru_analogy
      note: >-
        Strongest single item in the pack. «Являтися» in Ukrainian means to appear as an
        apparition; as a copula it is a direct calque of «является». Correct form: «є».
    - phrase: "на протязі"
      match: "на протязі"
      match_mode: phrase
      risk: high
      status: hypothesis
      basis: ru_analogy
      note: "«Протяг» is a draught of air. Correct: «протягом»."
    - phrase: "приймати участь"
      match: "прийма(ти|є|ють) участь"
      match_mode: phrase
      risk: high
      status: hypothesis
      basis: ru_analogy
      note: "Correct: «брати участь»."
    - phrase: "у якості"
      match: "(у|в) якості "
      match_mode: phrase
      risk: high
      status: hypothesis
      basis: ru_analogy
      note: "Calque of «в качестве». Correct: «як»."
    - phrase: "в залежності від"
      match: "(в|у) залежності від"
      match_mode: phrase
      risk: high
      status: hypothesis
      basis: ru_analogy
      note: "Correct: «залежно від»."
    - phrase: "діючий"
      match: "діюч(ий|е|а|і)"
      match_mode: phrase
      risk: high
      status: hypothesis
      basis: ru_analogy
      note: >-
        Correct: «чинний» (законодавство, договір). High value for the reference pilot, where
        «чинне законодавство» is frequent vocabulary.
    - phrase: "відмінити"
      match: "відміни(ти|в|ла|ли)"
      match_mode: phrase
      risk: medium
      status: hypothesis
      basis: ru_analogy
      note: "Correct: «скасувати»."
    - phrase: "слідуючий"
      match: "слідуюч(ий|а|е|і)"
      match_mode: phrase
      risk: high
      status: hypothesis
      basis: ru_analogy
      note: "Correct: «наступний»."
    - phrase: "наступний in the sense of «такий»"
      match: "наступн(і|их) (переваги|особливості|умови|вимоги)"
      match_mode: regex
      risk: medium
      status: hypothesis
      basis: ru_analogy
      note: >-
        «Наступні переваги» before an enumeration is a calque of «следующие преимущества».
        Correct: «такі переваги». Requires context, so density and a judge question.
    - phrase: "даний"
      match: "дан(ий|а|е|ої|ому) (продукт|випадок|метод|сервіс|документ|розділ)"
      match_mode: regex
      risk: high
      status: hypothesis
      basis: ru_analogy
      note: "Calque of «данный». Correct: «цей». Also in 3.1 as a section opener."
    - phrase: "на сьогоднішній день"
      match: "на сьогоднішній день"
      match_mode: phrase
      risk: high
      status: hypothesis
      basis: ru_analogy
      note: "Pleonasm calqued from «на сегодняшний день». Correct: «сьогодні», «нині»."
    - phrase: "мати місце"
      match: "ма(є|ють|ло) місце"
      match_mode: phrase
      risk: high
      status: hypothesis
      basis: ru_analogy
      note: "Calque of «иметь место»."
    - phrase: "носити характер"
      match: "нос(ить|ять) .{0,20}характер"
      match_mode: regex
      risk: high
      status: hypothesis
      basis: ru_analogy
      note: "Calque of «носить характер»."
    - phrase: "в кінці кінців"
      match: "(в|у) кінці кінців"
      match_mode: phrase
      risk: medium
      status: hypothesis
      basis: ru_analogy
      note: "Correct: «зрештою», «врешті-решт»."
    - phrase: "відношення in the sense of «ставлення»"
      match: "відношення до"
      match_mode: phrase
      risk: medium
      status: hypothesis
      basis: ru_analogy
      note: >-
        «Відношення» is legitimate in mathematics and in «відношення між величинами».
        «Відношення до людей» is the calque. Context-dependent; judge question required.
    - phrase: "виключно in the sense of «лише»"
      match: "виключно"
      match_mode: density
      risk: low
      status: hypothesis
      basis: ru_analogy
      note: >-
        Contested. Widely used and defended by some editors. Density only, low risk, and a
        candidate for removal if the human baseline corpus shows normal frequency."
    - phrase: "більш детальніше"
      match: "більш (детальніше|краще|зручніше|швидше)"
      match_mode: regex
      risk: high
      status: hypothesis
      basis: ru_analogy
      note: "Double comparative. Grammatical error, not a stylistic preference."
    - phrase: "згідно without «з»"
      match: 'згідно (?!з|із)\S'
      match_mode: regex
      risk: medium
      status: hypothesis
      basis: ru_analogy
      note: "«Згідно чинного законодавства» is wrong; «згідно з чинним законодавством»."
    - phrase: "по мірі того як"
      match: "по мірі того"
      match_mode: phrase
      risk: medium
      status: hypothesis
      basis: ru_analogy
      note: "Correct: «у міру того як»."
    - phrase: "міроприємство"
      match: "міроприємств"
      match_mode: phrase
      risk: high
      status: hypothesis
      basis: ru_analogy
      note: "Correct: «захід»."
    - phrase: "получати"
      match: "получа(ти|є|ють)"
      match_mode: phrase
      risk: high
      status: hypothesis
      basis: ru_analogy
      note: "Correct: «отримувати»."
    - phrase: "вірний in the sense of «правильний»"
      match: "вірн(ий|а|е) (відповідь|варіант|рішення|спосіб)"
      match_mode: regex
      risk: medium
      status: hypothesis
      basis: ru_analogy
      note: "«Вірний» means faithful. Correct here: «правильний»."
```

### 3.9 `bureaucratic_constructions` — `uk-local`

Nominalization chains and agentless constructions. These are the shape machine translation from
English produces, and also the shape of Ukrainian officialese — which means a corpus of government
or bank sources will be full of them legitimately. **Density only, no phrase bans.**

```yaml
bureaucratic_constructions:
  rule_id: LANG-UK-09
  forbidden: true
  updated_at: 2026-08-07
  next_review: 2026-11-07
  severity_ceiling: WARN
  items:
    - phrase: "verbal nouns -ання/-ення/-ація"
      match: '\p{L}+(ання|ення|ація)\b'
      match_mode: density
      risk: medium
      status: hypothesis
      basis: ru_analogy
      note: >-
        Threshold in the ru list is >25 per 1,000 words. Carried over unmeasured. Ukrainian
        financial and legal vocabulary is nominalization-heavy by nature, so the human baseline
        for this niche may sit above the general-prose baseline.
    - phrase: "adverbial participle clauses (дієприслівникові звороти)"
      match: '\p{L}+(ючи|вши|ши)\b'
      match_mode: density
      risk: medium
      status: hypothesis
      basis: ru_analogy
      note: >-
        Threshold in the ru list is >6 per 1,000. The real defect is the dangling variety with a
        lost subject («використовуючи цей метод, результати покращуються»), which density alone
        does not detect. Needs a judge question, not a counter.
    - phrase: "здійснювати"
      match: "здійсн(ювати|ює|юють|ення)"
      match_mode: density
      risk: medium
      status: hypothesis
      basis: ru_analogy
      note: "Officialese verb-of-all-work. Usually replaceable by the specific verb."
    - phrase: "шляхом + verbal noun"
      match: 'шляхом \p{L}+(ання|ення)'
      match_mode: regex
      risk: medium
      status: hypothesis
      basis: ru_analogy
      note: "«Шляхом проведення аналізу» → «проаналізувавши»."
    - phrase: "з метою"
      match: "з метою"
      match_mode: density
      risk: low
      status: hypothesis
      basis: ru_analogy
      note: "Usually «щоб». Legitimate in formal register."
    - phrase: "в рамках"
      match: "(в|у) рамках"
      match_mode: density
      risk: low
      status: hypothesis
      basis: ru_analogy
      note: "Calque of «within the framework of»."
    - phrase: "на постійній основі"
      match: "на постійній основі"
      match_mode: phrase
      risk: medium
      status: hypothesis
      basis: ru_analogy
      note: "Calque of «on an ongoing basis». Correct: «постійно»."
    - phrase: "має можливість"
      match: "ма(є|ють) можливість"
      match_mode: density
      risk: low
      status: hypothesis
      basis: ru_analogy
      note: "Usually «може»."
    - phrase: "є важливим"
      match: "є (важлив|необхідн|доцільн)(им|ою)"
      match_mode: density
      risk: low
      status: hypothesis
      basis: ru_analogy
      note: "Copula + adjective where the adjective alone suffices."
    - phrase: "у зв'язку з тим, що"
      match: "(у|в) зв.язку з тим, що"
      match_mode: phrase
      risk: medium
      status: hypothesis
      basis: ru_analogy
      note: "Usually «бо» or «оскільки»."
    - phrase: "проводити роботу"
      match: "провод(ити|иться|ять) роботу"
      match_mode: phrase
      risk: medium
      status: hypothesis
      basis: ru_analogy
      note: "—"
    - phrase: "є таким, що"
      match: "є так(им|ими), що"
      match_mode: phrase
      risk: medium
      status: hypothesis
      basis: ru_analogy
      note: "—"
```

### 3.10 `technical_defects_uk` — `uk-local`, BLOCK

The only set in this pack permitted to block. Every entry is a fact about Ukrainian orthography or
character encoding, not a frequency claim, hence `status: deterministic`. False-positive rate is
effectively zero outside quoted spans.

**Patterns in this set are written with escape sequences, never with literal characters, and the
reason is embarrassing enough to record.** Two entries here originally carried the very characters
they detect: the zero-width entry held real zero-width characters, and the mojibake entry held a raw
C1 control byte. The block stopped being valid YAML, so the entire set — the only BLOCK-capable set
in the pack — silently failed to load. The set that detects encoding damage was disabled by encoding
damage. Every character in this set that is invisible, a control code, or outside printable ASCII
must be written as `\uXXXX` or `\xXX`. A pattern you cannot see is a pattern you cannot review.

```yaml
technical_defects_uk:
  rule_id: LANG-UK-10
  forbidden: true
  updated_at: 2026-08-07
  next_review: 2026-11-07
  severity_ceiling: BLOCK
  never_applies_inside: [quotation, code, cited_verbatim]
  items:
    - phrase: "Russian-only letters in Ukrainian text"
      match: "[ыъэё]"
      match_mode: regex
      risk: high
      status: deterministic
      basis: orthographic
      note: >-
        ы, ъ, э, ё do not exist in the Ukrainian alphabet. Presence outside a quoted Russian span
        means the text passed through Russian or a mixed corpus. BLOCK.
    - phrase: "Latin homoglyphs inside Cyrillic tokens"
      named_check: mixed_script_token
      match_mode: named
      risk: high
      status: deterministic
      basis: orthographic
      note: >-
        A token containing both Cyrillic and Latin characters (a/е/о/р/с/х/і/у substituted).
        Produced by copy-paste and by some generation pipelines. Breaks search, anchors and
        deduplication silently. BLOCK.

        WAS DEAD UNTIL 2026-08-07. The previous pattern was
        `\b(?=\p{Cyrillic})(?=\p{Latin})\S+\b`, which requires a SINGLE CHARACTER to belong to
        two scripts at once. It compiled, it reviewed cleanly, and its match set was empty:
        the check reported success on every document for as long as it shipped. Homoglyph
        substitution is a property of a token, not of a character, so no lookahead formulation
        can express it and it is now a named check resolved in code (05-writing-core.md §6).
    - phrase: "wrong apostrophe character"
      match: "[`ʹ′']"
      match_mode: regex
      risk: high
      status: deterministic
      basis: orthographic
      note: >-
        Ukrainian requires U+2019 (or U+02BC) in «п'ять», «об'єкт», «зв'язок». A backtick, prime
        or straight quote is a technical defect and additionally breaks tokenization (§4.2).
    - phrase: "Russian-style quotation nesting"
      match: '"[^"]{2,}"'
      match_mode: regex
      severity: WARN
      risk: medium
      status: deterministic
      basis: orthographic
      note: >-
        Straight double quotes where Ukrainian typography requires «» at the outer level.
        See §5.2. WARN, not BLOCK, because CMS pipelines legitimately produce them, and a
        typographic preference must not stop a publication. The set ceiling is BLOCK, so this
        entry declares its own downgrade: before 2026-08-07 the note said WARN while the
        machine read BLOCK from the set, and prose that disagrees with the field is prose the
        machine ignores.
    - phrase: "zero-width and narrow no-break characters"
      match: "[\u200B\u200C\u200D\uFEFF\u202F\u00AD]"
      match_mode: regex
      risk: high
      status: deterministic
      basis: orthographic
      note: >-
        Already covered by the language-independent WRT-52. Repeated here because the Ukrainian
        pipeline passes through more copy-paste stages than the English one.
    - phrase: "mojibake from cp1251/utf-8 confusion"
      match: "[\xD0\xD1][\x80-\xBF]"
      match_mode: regex
      risk: high
      status: deterministic
      basis: orthographic
      note: "Encoding damage. BLOCK."
```

---

## §4. The four traps — prohibitions

These exist because the cheapest way to build this pack would be to translate the English one, and
that produces a pack that damages correct Ukrainian. Each trap is a rule, not a caution.

### UK-01. The dash is not a marker. `BLOCK` on any rule that treats it as one.

**Prohibition.** No rule in this pack, in any script, or in any writer prompt may penalise the
presence of the dash `—`, or convert it to a comma, or use dash density as evidence of machine
authorship in the way the English rule does.

**Why.** In Ukrainian the dash is grammatically obligatory in the copula-ellipsis construction
«Х — це У» and in «Х — У», where English would use a verb. Penalising it does not clean the text,
it makes the text ungrammatical.

**Recorded incident.** Applying the English rule to Cyrillic converted **349 correct occurrences
into commas** before it was caught. → P5, project memory `uk-dash-ban-is-for-english`

**What is permitted instead.** Anomalous _density_ only, as an `INFO` metric, with no automatic
rewriting: `> 8` dashes per 1,000 words, or `> 25 %` of sentences containing one
`[expert judgement, needs calibration — carried from the ru list, never measured on Ukrainian]`.
If a replacement is ever made, the dash `—` may be replaced only by an en dash `–`, never by a
comma.

The construction `Х — це У` is listed in `prescribed_phrases` (3.7) precisely so that
`rules_lint.py` fails the build if anyone later adds a rule forbidding it.

### UK-02. Word counting and tokenization must be Unicode-aware. `BLOCK`.

**Prohibition.** `wc -w`, whitespace splitting, and `\b`/`\w` under a non-Unicode regex mode are
forbidden anywhere a Ukrainian text is measured.

**Recorded incident.** A live measurement using `wc -w` reported the English locale as **six times
larger** than the Ukrainian one when the two were at parity. The conclusion drawn from it was the
exact inverse of the truth. → P5, `[internal observation, unpublished]`

**Ukrainian-specific addition beyond the general rule.** The apostrophe is part of the word. A naive
`\w+` splits «п'ять» into `п` and `ять`, «об'єкт» into `об` and `єкт`, «зв'язок» into `зв` and
`язок`. Hyphenated forms («будь-який», «по-перше», «врешті-решт») split likewise. Any tokenizer used
on Ukrainian must treat U+2019 and the hyphen as word-internal. This corrupts every downstream
number — density thresholds, TTR, claim density, n-gram overlap — and it corrupts them _quietly_,
which is worse than failing.

### UK-03. Anchor normalization requires lemmatization. `BLOCK` on the invariant otherwise.

**Prohibition.** The one-anchor-one-URL invariant (P6, `07-linking.md`) must not be enforced on
surface forms for this locale.

**Why.** Ukrainian inflects for seven cases and two numbers. The same anchor appears as
**«кредит онлайн» / «кредиту онлайн» / «кредити онлайн» / «кредитом онлайн»**. On surface forms these
are four distinct keys, they never collide, and the invariant reports clean while four different
pages compete on the same anchor. The failure is silent: the check passes, and the guarantee it was
written to provide does not exist.

**Requirement.** `07-linking.md` reads anchor normalization from this pack. For `uk` it must lemmatize
before comparison, and it must lowercase using Unicode-aware case folding.

**Tooling — unverified.** Candidate lemmatizers for Ukrainian include `pymorphy3` with the Ukrainian
dictionary package, Stanza, and UDPipe. **None has been evaluated for this project.** Selecting one
is a task, not a decision recorded here; whichever is chosen, its version must be pinned in
`.kiln/project.yml`, because a lemmatizer upgrade silently re-partitions the anchor registry.

**Declared as `lemmatizer: unresolved` in §2 metadata rather than omitted.** The distinction
matters. An absent field reads as "handled by the default"; an explicit `unresolved` is a value a
script can read and refuse to proceed on. It changes nothing operationally — the invariant is still
ineffective for this locale — but the hole is now visible to a machine instead of buried in prose.

### UK-04. Surzhyk and register are not automatable. `WARN` ceiling, quote-exempt, always.

**Prohibition.** No rule in §3.8 or §3.9 may be applied inside a quotation, a `verbatim` field from
`research_packet.json`, or any cited span. Automatic rewriting of any of them is forbidden anywhere.

**Why this is a correctness issue and not a style issue.** Two distinct failures:

1. **Editing a quote falsifies evidence.** If a source said «на протязі року», that is what they
   said. Correcting it inside quotation marks misrepresents the source — a P1 violation with a
   legal dimension in YMYL, and one that a purely stylistic module would commit cheerfully.
2. **It destroys the strongest anti-machine signal we have.** P4 states the human-machine gap runs
   through concreteness, cultural nuance and diversity. Surzhyk in a real person's speech _is_
   cultural nuance. Sanding it off makes the text more machine-like, not less, while the style
   metrics improve. That is the precise failure mode P3 warns about: the metric goes up and the
   thing it proxies goes down.

**Third failure, in the other direction: over-purification is itself a tell.** Aggressive russism
removal produces stilted, hyper-correct prose that no Ukrainian writes naturally. Several items in
3.8 are genuinely contested among editors (`виключно`, `відношення`). A pack that treats contested
usage as error yields text that reads as machine-edited even when a human wrote it.

**Operational rule.** Editorial voice — the site's own prose — is in scope for §3.8. Quoted speech,
user reviews, official document titles and legal formulations are out of scope entirely. The
distinction is made by span, by code, before any rule runs. If span detection is unavailable, the
rules do not run at all.

---

## §5. Structure, punctuation and typography

### 5.1 Headings

Ukrainian uses **sentence case**. Title Case is an English convention and, applied to Ukrainian,
is a direct machine-translation marker.

| Rule                                                                            | Severity |
| ------------------------------------------------------------------------------- | -------- |
| `UK-10` Capital letters in a heading other than the first word or a proper noun | WARN     |
| `UK-11` Heading ends with a full stop                                           | WARN     |
| `UK-12` Heading level skipped (H2 → H4)                                         | WARN     |
| `UK-13` First paragraph opens by defining the word in the heading               | WARN     |

`UK-13` note: the pattern is «„Вплив тривожності на навчання" — це стан, за якого…». The core rule
WRT-30 (time to answer) covers the useful half of this; `UK-13` catches the specific dictionary-entry
opening, which is a Russian-list carry-over `[status: hypothesis]`.

### 5.2 Quotation marks

Ukrainian typography nests as **«…» outer, „…" inner**. Straight `"` are a CMS artifact; English
curly `"…"` are a translation artifact.

| Rule                                                      | Severity |
| --------------------------------------------------------- | -------- |
| `UK-14` Straight `"` in body prose                        | WARN     |
| `UK-15` English curly quotes `"…"` anywhere in body prose | WARN     |
| `UK-16` Outer level not `«»`                              | INFO     |

### 5.3 Other typography

| Rule                                                                             | Severity                                                               |
| -------------------------------------------------------------------------------- | ---------------------------------------------------------------------- |
| `UK-17` Apostrophe not U+2019/U+02BC in words requiring it                       | BLOCK (3.10)                                                           |
| `UK-18` Bold applied at every repetition of a term                               | WARN                                                                   |
| `UK-19` List items formatted `**Заголовок:** текст` above a share threshold      | WARN                                                                   |
| `UK-20` Emoji outside quoted spans                                               | WARN — BLOCK when the project declares a design system forbidding them |
| `UK-21` Month names, weekdays or nationalities capitalized                       | WARN                                                                   |
| `UK-22` Numerals with a comma decimal separator inconsistent within the document | WARN                                                                   |

`UK-21` note: Ukrainian does not capitalize «серпень», «понеділок», «українець» — English does. A
reliable translation marker `[status: hypothesis]`.

`UK-22` note: Ukrainian uses the comma as decimal separator («3,9 %») and a non-breaking space for
thousands. A document mixing `3.9` and `3,9` has been assembled from two pipelines. Directly
relevant to the reference pilot, where every page carries rates.

---

## §6. Statistical form metrics

The language-independent metrics WRT-40…WRT-46 apply to Ukrainian in full. **Their thresholds do
not.** Every number in the core group E was derived from English-language literature.

**Status for this locale: all group E metrics are `INFO` until §8 calibration completes.** They are
computed, recorded and reported; they do not raise WARN and they never raise BLOCK. Reporting a
WARN against an unmeasured threshold manufactures false confidence, which is the specific risk
recorded in `05-writing-core.md` §11-3.

Ukrainian-specific candidate metrics, all `INFO`, all hypotheses carried from the Russian list:

| ID      | Metric                                                           | Carried threshold                  | Status |
| ------- | ---------------------------------------------------------------- | ---------------------------------- | ------ |
| `UK-30` | Adverbial participle clauses per 1,000 words                     | `> 6` `[ru_analogy, unmeasured]`   | INFO   |
| `UK-31` | Verbal nouns `-ання/-ення/-ація` per 1,000 words                 | `> 25` `[ru_analogy, unmeasured]`  | INFO   |
| `UK-32` | Identical list-item openings                                     | `> 8 %` `[ru_analogy, unmeasured]` | INFO   |
| `UK-33` | Dash density per 1,000 words                                     | `> 8` `[ru_analogy, unmeasured]`   | INFO   |
| `UK-34` | Proper noun replaced by a descriptive synonym after introduction | `> 2` occurrences `[ru_analogy]`   | INFO   |
| `UK-35` | Russism density per 1,000 words (3.8, high-risk entries only)    | unset                              | INFO   |

`UK-32` is set stricter than the general opener-repetition rule (WRT-43, `> 12 %`) in the Russian
source. That asymmetry is itself unverified and is a specific thing to test in §8: if Ukrainian
list openers repeat naturally at 10 %, the stricter threshold is pure false-positive generation.

`UK-34` note: the pattern is substituting «головний герой», «ключовий гравець», «провідний
експерт» for a name already introduced — the elegant-variation habit. Requires coreference, so it
is a judge question in practice, not a counter.

---

## §7. Judge questions for this locale

Per `05-writing-core.md` §7, binary questions only, with a required quotation. These supplement the
core questions; they do not replace them. Asked in Ukrainian to the judge model, since the text is
Ukrainian.

| Rule    | Question to the judge                                                                                                            |
| ------- | -------------------------------------------------------------------------------------------------------------------------------- |
| `UK-40` | «Чи є в тексті дієприслівниковий зворот, у якому втрачено підмет? Наведи цитату.»                                                |
| `UK-41` | «Чи читається цей абзац як переклад з іншої мови, а не як текст, написаний українською? Наведи цитату.»                          |
| `UK-42` | «Чи є цей фрагмент прямою мовою або цитатою?» — asked **before** any rule from 3.8 or 3.9 runs, when span detection is uncertain |
| `UK-43` | «Чи містить фінальний розділ хоча б одне твердження, якого немає в тілі статті?» — feeds 3.3 `Висновок`                          |
| `UK-44` | «Чи вжито тут слово „наступний" у значенні „такий" перед переліком? Наведи цитату.»                                              |

---

## §8. Calibration protocol

This is the section that turns the pack from hypotheses into measurements. Until it runs, everything
in §3 and §6 is an educated guess and is labelled as one.

### 8.1 What to collect

Three corpora, per locale and per niche. Mixing niches invalidates the result: Ukrainian financial
prose is nominalization-heavy in ways general prose is not, and a threshold set on general prose
will fire constantly on legitimate credit-comparison content.

| Corpus                     | Content                                                                              | Target size                     | Why this one                                                                      |
| -------------------------- | ------------------------------------------------------------------------------------ | ------------------------------- | --------------------------------------------------------------------------------- |
| **H — human baseline**     | Text published in this niche and language before 2023, by identifiable human authors | ≥ 100 documents, ≥ 80,000 words | The distribution we are trying to match                                           |
| **C — competitor current** | Current top-10 pages for the project's core clusters                                 | ≥ 100 documents                 | What the niche looks like now, machine-written parts included                     |
| **M — our machine drafts** | Kiln drafts for this project before human review                                     | ≥ 100 drafts                    | What our own pipeline produces, which is what the thresholds must separate from H |

**The reference pilot has an unusually good human-written corpus and it should be captured before it is touched.** It
carries 186 wiki pages dated 2021 and 776 news items ending 2024-03-07 — Ukrainian, in-niche, and
predating the period when machine-assisted publishing became common in this market. That is a
pre-contamination human baseline of a quality that a new site cannot obtain at any price. Freeze a
snapshot of it before any rewriting begins. Once those pages are refreshed under Kiln, the baseline
is gone.

Caveat recorded honestly: pre-2023 does not guarantee human authorship, only that machine authorship
was less common. Sample and spot-check by hand, and record the check.

### 8.2 What to compute

For every metric in §6 and every `density` entry in §3, compute the full distribution over H, C and
M separately. Record mean, median, p50/p75/p90/p95/p99, and the overlap between H and M.

### 8.3 Promotion criteria

| From   | To      | Requirement                                                                                                                                                                                                                                      |
| ------ | ------- | ------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------ |
| `INFO` | `WARN`  | H and M both have n ≥ 100 in this locale and niche; the distributions separate; the threshold is placed at a point where **fewer than 5 % of H documents** exceed it; the threshold is written to `.kiln/thresholds.yml`, not to this file (P10) |
| `WARN` | `BLOCK` | **Not available for any stylistic metric.** Ceiling is WARN, permanently.                                                                                                                                                                        |

**Why the BLOCK path is closed for style.** `05-writing-core.md` §11-2 states that group E metrics
never block, because a blocking style metric turns into an optimization target and that is precisely
what P3 forbids. The same reasoning applies to every set in §3.2 through §3.9. The only BLOCK-capable
set in this pack is §3.10, and those are orthographic facts, not style.

**Status transitions on entries.** An entry moves `hypothesis → observed` when it is found in M at a
rate measurably above H. It moves `observed → calibrated` when a threshold derived from the measured
distributions is recorded. An entry that appears in H at the same rate as in M is **deleted**, not
downgraded: it was never a marker, and keeping it costs reviewer attention. Deletions go to
`doctrine/CHANGELOG.md` with the numbers, per P15.

### 8.4 Cadence

First calibration: after the first 30 drafts through the pipeline, or 90 days, whichever comes first.
Re-calibration: every 90 days, and immediately after any writer-model change. Model changes shift
the M distribution and invalidate thresholds without touching a single rule.

### 8.5 The open research question

`EVIDENCE.md#e03-ai-detection-and-humanization` records this as a candidate for original work, and it remains the highest-value gap: a
corpus of Ukrainian articles of known provenance, measured against these metrics, would be the first
such dataset. If Kiln produces it, it is publishable, and it is exactly the kind of first-party
asset P13 asks every project to find.

---

## §9. The `ru` locale

**`ru.md` is a separate pack. Rules never cross between the two.** This is P5, and it is not
negotiable by convenience even though the languages are close — closeness is what makes the mistake
easy.

Concretely, for a site running both locales (one reference project runs `uk`, `ru`, `en`; another runs `uk`
and `ru`):

1. **`russisms_calques` (3.8) has no counterpart in `ru.md` and must never be loaded for `ru`.** The
   entire set is meaningless there — «являється» is correct Russian.
2. **The reverse set does not exist either.** Ukrainianisms in Russian text are not symmetric to
   russisms in Ukrainian text, either linguistically or in what they indicate about the pipeline.
3. **The Russian generated-text list is the _base_ for uk hypotheses, not a shared asset.** It is
   cited here as provenance (`basis: ru_analogy`) and consumed once, at authoring time. `uk.md` does
   not import from `ru.md` at runtime, and a change to one is not a change to the other.
4. **Thresholds are per locale.** Both packs write to `.kiln/thresholds.yml` under separate locale
   keys. A Ukrainian threshold calibrated on Ukrainian text is not evidence about Russian text.
5. **n-gram overlap must exclude sibling locales.** `05-writing-core.md` §11-4 already records this:
   WRT-23 compares a draft against the top corpus, and if a project's own `ru` translation of the
   same page is in scope, the Ukrainian original is flagged as plagiarism of itself. Locale
   siblings are excluded from the comparison corpus by `project.yml`, not by threshold tuning.
6. **What may be reused when `ru.md` is written:** the structure of this file, the entry schema, the
   `match_mode` distinction, the trap framing of §4 (Russian shares UK-01 on the dash and UK-02 on
   tokenization verbatim; UK-03 on lemmatization applies with the same force, since Russian inflects
   comparably), and §8 wholesale. The lexical content is written from the Russian source list
   directly, which for `ru` is a primary source rather than an analogy — so `ru.md` entries may
   legitimately start at `observed` where these start at `hypothesis`.

---

## §10. Prohibitions

| Prohibition                                                               | Basis                                       |
| ------------------------------------------------------------------------- | ------------------------------------------- |
| Penalising the dash, or replacing it with a comma                         | UK-01, P5                                   |
| `wc -w`, whitespace splitting, non-Unicode `\b` on Ukrainian text         | UK-02, P5                                   |
| Splitting tokens at the apostrophe or hyphen                              | UK-02                                       |
| Enforcing the anchor invariant on surface forms                           | UK-03, P6                                   |
| Applying §3.8 or §3.9 inside quotations or `verbatim` spans               | UK-04, P1                                   |
| Automatically rewriting surzhyk or register anywhere                      | UK-04, P4                                   |
| Blocking publication on any stylistic metric in this pack                 | §8.3, P3                                    |
| Using an AI detector as a gate for Ukrainian content                      | P3; FPR is higher on Ukrainian than English |
| Translating the English stop-list into Ukrainian and shipping it          | §1, `EVIDENCE.md#e03-ai-detection-and-humanization` §6                           |
| Treating a `hypothesis` entry as a finding because it is in the doctrine  | §1                                          |
| Promoting a threshold into this file rather than `.kiln/thresholds.yml`   | P10                                         |
| Banning a `match_mode: density` term by presence                          | §2                                          |
| Adding a pattern without demonstrating it fires on a positive case        | 3.10, the dead homoglyph rule               |
| Writing a literal invisible or control character into a pattern           | 3.10, the unparseable set                   |
| Renaming a contract key (`items`, `phrase`) to something the pack prefers | §2, the empty-pack failure                  |

---

## §11. Conflicts and open items

**1. RESOLVED 2026-08-07 — the `deterministic` status value.** Proposed by this pack because the
other three statuses are all statistical and an orthographic fact is not a hypothesis. Ratified into
`05-writing-core.md` §6 and `_template.md`, and it is the only status permitted to carry BLOCK.

**2. RESOLVED 2026-08-07 — the invariant now unions every forbidden set.** The contract previously
unioned five fixed sets and could not see this pack's three pack-local ones, so a prescribed phrase
colliding with a russism would have passed. `rules_lint.py` check 1 computes the union over every
set declaring `forbidden: true`. The check additionally reports when a pack declares no
`normalization` block, because without one the invariant is not false, it is **undefined** — and an
undefined check looks identical to a passing one.

**2a. RESOLVED 2026-08-07 — three defects that made this pack partly inert.** Recorded because each
failed silently, which is the pattern worth remembering rather than the individual bugs. The set
keys were wrong, so the pack loaded empty (§2). The homoglyph pattern demanded that one character be
both Cyrillic and Latin, so it could never match (3.10). Two entries in 3.10 contained literal
invisible and control characters, so the only BLOCK-capable set in the pack failed to parse at all
(3.10). None of the three produced an error message; all three reported success.

**3. The YMYL hedge conflict is unresolved.** Two entries in 3.2 —
«рекомендуємо проконсультуватися з фахівцем» and «це лише загальна інформація» — are flagged as
filler hedges by analogy with the Russian list, but in Ukrainian financial content they may be
required disclosures. Neither the regulatory requirement nor its exact wording was established:
`[internal observation, unpublished]` explicitly records Ukrainian regulatory disclosure requirements for financial
portals as an open branch that was never closed. **Until it is closed, both entries stay at
`risk: low`, `match_mode: density`, and the project's `forbidden`/required-disclosure list from
onboarding takes precedence over this pack.** Getting this backwards means the pack advises removing
a legally mandated sentence.

**4. Almost every threshold here descends from the Russian list, which itself is uncalibrated.**
The ru numbers (`> 6`, `> 25`, `> 8 %`, `> 8`) are expert judgement in their own source. Carrying
them into Ukrainian compounds an unmeasured value with an unverified analogy. This is why §6 keeps
all of them at `INFO`. The risk if that ceiling is ever lifted early: a pack full of confident
verdicts built on two layers of guessing.

**5. `russisms_calques` will produce false positives on quoted official language.** Ukrainian
statutes, bank terms and court documents contain constructions this set flags — sometimes because
officialese is genuinely calqued, sometimes because the phrasing is fixed by law and may not be
altered. Span exemption (UK-04) handles the quoted case. It does not handle paraphrase of a legal
requirement, where the writer must stay close to the statutory wording. Open.

**6. Lemmatizer choice is unresolved and it is load-bearing.** UK-03 requires lemmatization for the
anchor invariant to work at all, and no tool has been evaluated. A wrong or unpinned choice makes
`07-linking.md` silently ineffective for the pilot locale — the check reports clean and guarantees
nothing. This is the highest-priority open item in the pack.

**7. The dash density metric (`UK-33`) sits uncomfortably close to UK-01.** It is retained as INFO
only, and it must never trigger a rewrite. If it ever begins to be used as grounds for editing
dashes, it becomes the rule UK-01 forbids and must be removed rather than defended.

---

## §12. Sources

**Read in full while writing this file:**

| File                                    | What was taken                                                                                                                                                                            |
| --------------------------------------- | ----------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| `doctrine/00-principles.md`             | P1, P3, P4, P5, P6, P10, P12, P13, P15                                                                                                                                                    |
| `doctrine/05-writing-core.md`           | §6 language pack contract and the seven set keys; §7 binary judge questions; group E metrics; §11-2, §11-3, §11-4                                                                         |
| `EVIDENCE.md#e03-ai-detection-and-humanization` | §5 Russian marker list (the basis for every `ru_analogy` entry); §6 the absence of Ukrainian research; §9.2 and §9.3 thresholds; §9.4 what not to gate on; §1.5 detector FPR on Ukrainian |

**Cited through the reconnaissance reports, primary source not opened in this session (P1 marking
required):**

- ru.wikipedia «Признаки сгенерированности текста» — the origin of the Russian marker list.
  Every `basis: ru_analogy` entry traces here through `EVIDENCE.md#e03-ai-detection-and-humanization` §5. **Verify against the original
  at first revision.**
- `[internal observation, unpublished]` — reference pilot corpus figures (186 wiki pages dated 2021, 776 news items ending
  2024-03-07) used in §8.1, and the open branch on Ukrainian financial disclosure requirements
  used in §11-3. Not re-opened here.
- `[internal observation, unpublished]` — the `wc -w` incident cited in UK-02, reached via P5.
- Project memory `uk-dash-ban-is-for-english` — the 349-dash incident cited in UK-01, reached via P5.
- Juzek T., Ward Z., COLING 2025 — generation-tagged lexical overrepresentation, English only.
  Cited in 3.6 to explain why the Ukrainian generation tags are _not_ comparable evidence.

**Not verified, carried as open:** every threshold in §6; the asymmetry of `UK-32` against WRT-43;
the generation attribution in 3.6; the contested status of `виключно` and `відношення`; the
lemmatizer candidates named in UK-03.
