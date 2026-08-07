# Language pack: Russian (`ru`)

> Subordinate to `00-principles.md` and to the language pack contract, `05-writing-core.md` §6 —
> this document is written in English because the doctrine is English-only (P5). Everything it
> _contains_ — every term, pattern and example — is Russian, because the content produced under this
> pack is Russian.
>
> Follows `_template.md`. On any conflict, `00-principles.md` and `05-writing-core.md` win and this
> file is the bug.

**Pack version:** 0.1.0 · **Date:** 2026-08-07 · **Review due:** 2026-11-05
**Maintainer:** kiln-core

---

## §1. Evidence position — read this before using anything below

**Russian is the one Cyrillic language in this repository that has a collectively maintained marker
list, and that list was read in full while writing this pack.** The Russian Wikipedia page
«Признаки сгенерированности текста» is compiled by editors reviewing suspect edits at volume. It was
opened and read on 2026-08-07 (§12), which is what P1 requires before a claim about the world enters
a document.

This is the material difference between this pack and `uk.md`. The Ukrainian pack states plainly
that no Ukrainian research and no Ukrainian marker list exist, so every lexical entry there is
carried from Russian by analogy and starts at `status: hypothesis`. Here the Russian list is a
**primary source for Russian**, and `uk.md` §9-6 anticipates exactly this: entries in `ru.md` may
legitimately start at `observed` where the Ukrainian ones start at `hypothesis`.

Three sources, in descending order of trust:

| Source                                          | What it gives                                                             | Trust                                                                          |
| ----------------------------------------------- | ------------------------------------------------------------------------- | ------------------------------------------------------------------------------ |
| The Russian collective marker list              | concrete phrases, formulas, structural and typographic markers in Russian | practitioner consensus at volume; not a controlled measurement                  |
| Language-independent metrics                    | sentence-length dispersion, opener repetition, claim density, TTR         | inherited from `05-writing-core.md` group E; thresholds remain English-derived  |
| This project's own corpus                       | real distributions for this language and this niche                       | the only thing that will ever be authoritative here, and it does not exist yet |

Four consequences, binding rather than advisory:

1. **`observed` here does not mean measured.** It means "recorded by editors who review generated
   text at volume, and read by us directly". Nothing in this pack is `calibrated` until §8 runs on a
   real Russian corpus in the target niche. A practitioner list is a good prior and a bad
   measurement, and the distance between those two is where confident nonsense lives.
2. **No stylistic rule in this pack may block publication.** The ceiling is `WARN`, and until §8
   completes the operational ceiling is `INFO`. P3, and `05-writing-core.md` §11-2.
3. **The one set permitted to block is 3.9**, and every entry in it is a fact about the Russian
   writing system or about character encoding, not a frequency claim.
4. **Practitioner consensus is not immune to the calque problem.** The Russian list was assembled
   largely on encyclopaedic prose. This pack is applied to consumer finance. Several markers that
   are decisive in an encyclopaedia article are ordinary in a rate comparison, and where that is
   true it is said at the entry.

---

## §2. Contract compliance

`05-writing-core.md` §6 requires seven named sets under fixed keys. All seven are declared in §3.
Two further sets are declared as pack-local extensions, marked `ru-local`.

**Key names.** Entries live under `items:` and each surface form under `phrase:`. This is stated
rather than assumed because the Ukrainian pack shipped with `entries:`/`term:` for ten sets: the
YAML parsed, the file read as complete, and every consumer received an **empty pack**. A locale with
no rules at all is indistinguishable from a locale whose rules all passed.

**Rule identifiers.** Each set declares `rule_id: LANG-RU-NN`, assigned in declaration order and
immutable. Findings are counted per rule in `.kiln/rules-stats.json`, and those counters are what P8
reads to retire a rule. A set whose meaning changes takes a new identifier; the old one is retired
and never reused, because reuse merges two different rules into one long history and does it
silently.

**Severity declaration.** Only 3.9 declares `severity: BLOCK`, and it declares
`default_status: deterministic` alongside it so that `rules_lint.py` check 9 can actually verify the
claim. `uk.md` uses `severity_ceiling: BLOCK` for the equivalent set, which no check reads — the
intent is right there and unverified. This pack prefers the form the linter can see. Recorded as an
inconsistency between the two packs in §11-2, to be resolved in one direction by PR rather than left
as two conventions.

### Pack metadata

The `normalization` block is not bookkeeping. The invariant
`prescribed_phrases ∩ ⋃(forbidden sets) = ∅` asks whether two entries are **the same phrase**, and
that question has no answer until the pack says how a phrase is normalized. A pack without the block
does not fail the invariant; the invariant becomes undefined, and an undefined check is
indistinguishable from a passing one.

```yaml
lang:
  code: ru
  script: Cyrl
  locales: [ru-UA, ru-RU]
  updated_at: 2026-08-07
  next_review: 2026-11-05
  maintainer: kiln-core

  # Deliberately empty. The Russian marker list is maintained by editors across many
  # models and does not attribute markers to a generation, so recording generations
  # here would claim a resolution the source does not have. Entries in 3.6 carry
  # `generation: unattributed` for the same reason.
  observed_generations: []
  observed_families: []
  evidence_basis: >
    Primary source read in full on 2026-08-07: the Russian Wikipedia page
    «Признаки сгенерированности текста», a collectively maintained marker list
    (see §12). Lexical entries drawn from it carry basis: ru_marker_list and
    status: observed. Entries reasoned from it rather than listed in it carry
    basis: reasoned and status: hypothesis. Entries in 3.9 are facts about the
    Russian writing system and carry basis: orthographic, status: deterministic.
    Structural metrics are inherited from 05-writing-core.md group E; their
    thresholds are English-derived and are held at INFO until §8 calibration.

  # Below this length a density rate is recorded and never compared: one hit in
  # 120 words reads as 8.3 per 1,000 and turns a frequency rule back into a
  # presence rule, which is the failure §2 of the template names.
  density_min_words: 400 # [expert judgement, needs calibration]

  normalization:
    case: lower
    unicode_form: NFC
    collapse_whitespace: true
    strip_trailing_ellipsis: true
    strip_terminal_punctuation: true
    tokenizer: unicode_words
    matching: longest_match_wins

    # Russian does not use a word-internal apostrophe natively, but transliterated
    # names carry one («О’Коннор», «д’Артаньян»). Stripping it merges and splits
    # tokens in exactly the same way it does in Ukrainian, so the setting is the
    # same for a narrower reason. Stated rather than inherited (§6).
    strip_internal_apostrophes: false
    apostrophe_chars: ["’", "ʼ"]

    # The hyphen is word-internal in Russian: «из-за», «по-моему», «кто-то»,
    # «когда-нибудь», «интернет-банкинг». A naive \w+ splits every one of them
    # and corrupts density, TTR and n-gram overlap quietly (RU-02).
    hyphen_is_word_internal: true

    # `ё` and `е` are the same letter for comparison purposes. Russian permits
    # both spellings and a corpus mixes them freely; treating «еще» and «ещё» as
    # different phrases would split every counter that touches them and would
    # make the intersection invariant depend on a typographic preference.
    fold_yo_to_ye: true

    # UNRESOLVED, and declared rather than omitted so the hole stays visible.
    # Russian inflects for six cases, three genders and two numbers, so surface-form
    # comparison makes the one-anchor-one-URL invariant (P6, 07-linking.md) report
    # clean while guaranteeing nothing: «кредит онлайн» and «кредита онлайн» never
    # collide, so no conflict is ever detected. Candidates in RU-03 are unevaluated.
    # Whatever is chosen is pinned by version in .kiln/project.yml, because a
    # lemmatizer upgrade silently re-partitions the anchor registry.
    lemmatizer: unresolved
```

**What `lemmatizer: unresolved` buys.** Nothing operationally. The anchor invariant stays ineffective
for this locale until a tool is chosen and pinned. What it buys is a value a script can read and
refuse to proceed on, instead of an absent field that reads as handled.

### Entry schema

```yaml
- phrase: "…" # the Russian surface form, or a short label when `match` carries the pattern
  match: "…" # literal or regex actually applied
  match_mode: phrase # phrase | density | regex
  risk: high # high | medium | low
  status: observed # see below
  basis: ru_marker_list # ru_marker_list | reasoned | language_independent | orthographic | pilot_corpus
  note: "…"
```

`status` values, as this pack uses them:

| Value           | Meaning here                                                                                       |
| --------------- | -------------------------------------------------------------------------------------------------- |
| `hypothesis`    | reasoned from the list or from the language, not itself listed and not observed in our corpus       |
| `observed`      | named in the Russian marker list read directly (§12), frequency not yet compared to a human baseline |
| `calibrated`    | threshold derived from measured distributions in this locale and this niche — nothing yet qualifies |
| `deterministic` | follows from Russian orthography or from encoding, not from frequency; calibration is meaningless   |

`deterministic` is the only status permitted to carry `BLOCK` (`05-writing-core.md` §6).

### `match_mode` and why it decides whether this pack helps or harms

`phrase` — multi-word constructions rarely legitimate in editorial prose. Judged by presence.

`density` — **ordinary Russian words that models overproduce. Judged by frequency per 1,000 words and
never by presence.** Banning «обеспечивает», «подчёркивает» or «важный» outright bans ordinary
Russian. This distinction is the single most important safeguard in the pack. A set that loses it
becomes the calque problem of §4 with a native accent.

`regex` — patterns with Russian morphology baked in. Every pattern in this file was demonstrated to
fire on a constructed positive case before it was committed (§11-5).

---

## §3. Lexical sets

### 3.1 `anaphora_openers` — feeds WRT-32

Section-initial referential openers: a passage that starts by pointing at something in the previous
passage cannot be extracted and cited on its own (P12). WRT-32 carries `BLOCK` in the core; the set
itself declares no severity, because the block belongs to the structural rule and not to the
vocabulary. This is the one lexical set whose findings can stop a publication, and it does so for a
retrieval reason rather than a stylistic one.

```yaml
anaphora_openers:
  rule_id: LANG-RU-01
  forbidden: true
  updated_at: 2026-08-07
  next_review: 2026-11-05
  applies_to: first sentence of a section only
  default_status: hypothesis
  items:
    - phrase: "Это"
      match: '^Это\s'
      match_mode: regex
      risk: high
      basis: language_independent
      note: "Bare demonstrative opener. Legitimate mid-paragraph, unusable as a section start."
    - phrase: "Этот / Эта / Эти"
      match: '^Эт(от|а|и)\s'
      match_mode: regex
      risk: high
      basis: language_independent
      note: "Points at a noun introduced in the previous section."
    - phrase: "Такой подход"
      match: '^Так(ой|ая|ое|ие)\s'
      match_mode: regex
      risk: high
      basis: language_independent
      note: "The construction the Ukrainian pack carries as an analogue of this one."
    - phrase: "Он / Она / Они"
      match: '^(Он|Она|Оно|Они)\s'
      match_mode: regex
      risk: high
      basis: language_independent
      note: "Pronoun with no antecedent inside the passage."
    - phrase: "Данный"
      match: '^Данн(ый|ая|ое)\s'
      match_mode: regex
      risk: high
      basis: reasoned
      note: >-
        Bureaucratic substitute for «этот» and simultaneously a back-reference. Also in 3.8.
        Unlike Ukrainian, where «даний» is additionally a calque, in Russian this is register
        alone — the entry is kept for the anaphora reason only.

        The plural «данные» is deliberately absent from the alternation. It is far more often the
        noun «data» than the adjective, and on a site whose sections routinely open with
        «Данные обновлены 07.08.2026» the plural form would fire on correct writing several times
        per page. Caught while constructing the negative case for this entry (§11-5), which is
        the entire reason that exercise is mandatory.
    - phrase: "Вышеуказанное / Вышеупомянутое"
      match: "^(Вышеуказанн|Вышеупомянут|Вышеприведённ|Вышеприведенн)"
      match_mode: regex
      risk: high
      basis: reasoned
      note: "Bureaucratic back-reference; also in 3.8."
    - phrase: "Как отмечалось выше"
      match: "^Как (было |)(отмечалось|сказано|указано|упомянуто) (выше|ранее)"
      match_mode: regex
      risk: high
      basis: reasoned
      note: "Explicit dependence on a passage the extractor will not have."
    - phrase: "Эти факторы"
      match: "^Эти (факторы|изменения|преимущества|особенности|условия|параметры)"
      match_mode: regex
      risk: high
      basis: reasoned
      note: "Names a list that lives in the previous section."
    - phrase: "Кроме того"
      match: "^Кроме того"
      match_mode: regex
      risk: medium
      basis: reasoned
      note: "Legitimate inside a section. As a section opener it presumes the previous one."
    - phrase: "Однако"
      match: "^Однако"
      match_mode: regex
      risk: medium
      basis: reasoned
      note: "Same reasoning as «Кроме того»: contrast requires something to contrast with."
    - phrase: "Именно поэтому"
      match: "^Именно поэтому"
      match_mode: regex
      risk: medium
      basis: reasoned
      note: "Announces a consequence of an argument made elsewhere."
    - phrase: "Несмотря на"
      match: "^Несмотря на"
      match_mode: regex
      risk: medium
      status: observed
      basis: ru_marker_list
      note: >-
        Named in the marker list as a template opener. As a section opener it also carries the
        anaphora defect, which is why it sits here rather than in 3.2.
```

### 3.2 `hedge_phrases` — didactic hedges and meta-commentary

The writer announcing what they are about to do instead of doing it, and softening formulas that
carry no information. The Russian list is unusually rich here, because a model addressing its user
is the most conspicuous thing it does.

```yaml
hedge_phrases:
  rule_id: LANG-RU-02
  forbidden: true
  updated_at: 2026-08-07
  next_review: 2026-11-05
  severity: WARN
  default_status: observed
  density_warn_per_1000: null # [expert judgement, needs calibration] — unset until §8
  items:
    - phrase: "важно отметить"
      match: '(важно|критично|необходимо)\s+(отметить|подчеркнуть|учитывать|помнить)'
      match_mode: regex
      risk: high
      basis: ru_marker_list
      class: hedge
      note: >-
        Named in the marker list. Carries no information: either the following sentence matters,
        in which case it is stated, or it does not and it is deleted. High risk because it is the
        single most frequent formula in the list and the cheapest to remove.
    - phrase: "стоит отметить"
      match: 'стоит\s+(отметить|учесть|запомнить|обратить внимание)'
      match_mode: regex
      risk: high
      basis: ru_marker_list
      class: hedge
      note: "Named in the marker list, alongside «стоит учесть» and «стоит запомнить»."
    - phrase: "следует отметить"
      match: 'следует\s+(отметить|учитывать|помнить|иметь в виду)'
      match_mode: regex
      risk: medium
      basis: reasoned
      class: hedge
      note: "Same construction as the two above with a different auxiliary."
    - phrase: "в этой статье мы рассмотрим"
      match: 'в (этой |данной |)(статье|материале|обзоре) (мы |)рассмотрим'
      match_mode: regex
      risk: high
      basis: ru_marker_list
      class: meta_bridge
      note: >-
        The list records «В этом эссе мы рассмотрим». Announcing the structure of a document to a
        reader who can see its headings is pure meta-commentary, and the passage it opens is never
        the answer to anything.
    - phrase: "давайте разберёмся"
      match: 'давайте (разбер|рассмотр|погруз|посмотр)'
      match_mode: regex
      risk: medium
      basis: reasoned
      class: meta_bridge
      note: "Conversational bridge to the reader. Same defect, warmer register."
    - phrase: "значения могут варьироваться"
      match: '(значения|условия|ставки|тарифы) могут (варьироваться|различаться|отличаться)'
      match_mode: regex
      risk: medium
      basis: ru_marker_list
      class: hedge
      note: >-
        Named in the marker list. On a rate comparison this sentence is sometimes true and
        necessary — but then it names what varies, between whom, and as of when. Unqualified it is
        a hedge that removes the value of the figure above it.
    - phrase: "на основе имеющейся информации"
      match: 'на осно(ве|вании) (имеющейся|доступной) информации'
      match_mode: regex
      risk: high
      basis: ru_marker_list
      class: hedge
      note: >-
        Named in the marker list. This is a model describing its own epistemic state, which is
        never a fact about the world. In YMYL it also reads as an admission that the figure was
        not verified (P1).
    - phrase: "хотя конкретные детали ограничены"
      match: 'конкретн(ые|ых) (детали|данных|сведени)\w* (ограничен|скудн|не широко)'
      match_mode: regex
      risk: high
      basis: ru_marker_list
      class: hedge
      note: >-
        Named in the marker list together with «не широко доступны/задокументированы». It is the
        surface of a missing source and should resolve to a source or to deletion, exactly as 3.5.
    - phrase: "по состоянию на момент обновления"
      match: '(на момент|по состоянию на момент) (моего |моей |)(обучения|последнего обновления|обновления (моей |)базы)'
      match_mode: regex
      risk: high
      basis: ru_marker_list
      class: meta_bridge
      note: >-
        Named in the marker list. A model self-reference that leaked into the text. Distinct from
        a legitimate «по состоянию на 07.08.2026», which is required on this project and is
        prescribed in 3.7 — see the note there before touching this pattern.
    - phrase: "как языковая модель"
      match: 'как (большая |)(языковая модель|нейросеть|искусственный интеллект)'
      match_mode: regex
      risk: high
      basis: ru_marker_list
      class: meta_bridge
      note: >-
        Named in the marker list. Unambiguous leakage of the assistant frame. Never legitimate
        outside an article whose subject is language models, where it appears inside quotation.
    - phrase: "надеюсь, это помогло"
      match: '(надеюсь, это (помогло|будет полезно)|сообщите мне|дайте мне знать|если хотите (спросить|уточнить|узнать))'
      match_mode: regex
      risk: high
      basis: ru_marker_list
      class: meta_bridge
      note: >-
        Named in the marker list under addressing-the-user. A chat turn pasted into an article.
    - phrase: "рекомендуем проконсультироваться со специалистом"
      match: '(рекомендуем|советуем) (проконсультироваться|обратиться) (со?|к) (специалист|эксперт|юрист|финансов)'
      match_mode: regex
      risk: low
      status: hypothesis
      basis: reasoned
      class: hedge
      note: >-
        UNRESOLVED, and deliberately the lowest risk in the set. On a Ukrainian consumer finance
        portal this sentence may be a required disclosure rather than a hedge. The Ukrainian pack
        records the same conflict unresolved (`lang/uk.md` §11-3). Until the regulatory position
        is established, the project's own required-disclosure list from onboarding takes
        precedence over this entry. Getting this backwards means advising the removal of a
        legally mandated sentence.
    - phrase: "это лишь общая информация"
      match: '(это|данная информация) (лишь|только|носит) (общ|справочн|информационн|ознакомительн)'
      match_mode: regex
      risk: low
      status: hypothesis
      basis: reasoned
      class: hedge
      note: "Same unresolved disclosure conflict as the entry above. Same precedence rule."
```

### 3.3 `closing_formulas`

Template endings and the mandatory-summary reflex. The Russian list names both the phrases and the
structural habit of a separate «Заключение» section. A closing section is a defect **only when it
adds nothing that was not already said**, so the phrase match is paired with a new-claim check.

```yaml
closing_formulas:
  rule_id: LANG-RU-03
  forbidden: true
  updated_at: 2026-08-07
  next_review: 2026-11-05
  severity: WARN
  requires_new_claim_check: true
  default_status: observed
  items:
    - phrase: "В заключение"
      match: "^В заключение"
      match_mode: regex
      risk: high
      basis: ru_marker_list
      note: >-
        Named in the marker list. Fires only when the section it opens carries no claim absent
        from the body — see RU-43 in §7, which is the question that decides it.
    - phrase: "Подводя итог"
      match: "^Подводя итог"
      match_mode: regex
      risk: high
      basis: ru_marker_list
      note: "Named in the marker list."
    - phrase: "Таким образом, можно сделать вывод"
      match: 'Таким образом,? можно сделать вывод'
      match_mode: regex
      risk: high
      basis: reasoned
      note: "The full formula. «Таким образом» alone is an ordinary connective and is not listed."
    - phrase: "Вкратце"
      match: "^Вкратце"
      match_mode: regex
      risk: medium
      basis: ru_marker_list
      note: "Named in the marker list."
    - phrase: "В целом"
      match: "^В целом"
      match_mode: regex
      risk: low
      basis: ru_marker_list
      note: >-
        Named in the marker list, but as a sentence opener it is ordinary Russian. Kept at low
        risk and only as a section-initial pattern; anything stricter fires on normal prose.
    - phrase: "Перспективы на будущее"
      match: '^(Перспективы на будущее|Взгляд в будущее|Что нас ждёт (в будущем|дальше))'
      match_mode: regex
      risk: medium
      basis: ru_marker_list
      note: >-
        Named in the marker list. A heading that promises speculation. On YMYL it is where
        unsourced forecasts enter, so it is worth catching for a reason beyond style.
    - phrase: "heading «Заключение» / «Вывод»"
      match: '^#{2,4}\s*(Заключение|Вывод(ы)?|Итоги)\s*$'
      match_mode: regex
      risk: medium
      basis: ru_marker_list
      note: >-
        Named in the marker list as a structural marker. A summary section is not idiomatic in
        Russian non-fiction outside academic writing; in a consumer article it repeats the body.
        Fires together with the new-claim check, never alone.
```

### 3.4 `promo_lexicon`

Advertising register: unearned significance, brochure adjectives, scene-setting filler. Nearly every
entry is `density`, because each of these words is ordinary Russian in isolation and it is the rate
that carries the signal.

```yaml
promo_lexicon:
  rule_id: LANG-RU-04
  forbidden: true
  updated_at: 2026-08-07
  next_review: 2026-11-05
  severity: WARN
  default_status: observed
  density_warn_per_1000: null # [expert judgement, needs calibration] — unset until §8
  items:
    - phrase: "играет ключевую роль"
      match: 'играет (важную|значительную|ключевую|решающую) роль'
      match_mode: regex
      risk: high
      basis: ru_marker_list
      note: >-
        Named in the marker list. Asserts importance instead of demonstrating it, and is
        compatible with any subject whatsoever — which is what makes it a marker rather than a
        preference.
    - phrase: "подчёркивает его важность"
      match: '(подчёркивает|подчеркивает|отражает|демонстрирует) (его |её |их |)(важность|значимость|значение)'
      match_mode: regex
      risk: high
      basis: ru_marker_list
      note: "Named in the marker list, in the same family as «служит напоминанием»."
    - phrase: "служит напоминанием"
      match: '(служит|выступает|является) напоминанием'
      match_mode: regex
      risk: high
      basis: ru_marker_list
      note: "Named in the marker list."
    - phrase: "неизгладимый след"
      match: '(неизгладимый след|устойчивое влияние|непреходящее значение)'
      match_mode: regex
      risk: medium
      basis: ru_marker_list
      note: "Named in the marker list. Encyclopaedic inflation; rare in finance prose, kept for completeness."
    - phrase: "может похвастаться"
      match: 'мож(ет|но) похвастаться'
      match_mode: regex
      risk: medium
      basis: ru_marker_list
      note: "Named in the marker list."
    - phrase: "расположенный в самом сердце"
      match: 'в самом сердце'
      match_mode: regex
      risk: low
      basis: ru_marker_list
      note: "Named in the marker list. Travel-brochure register; included because the family is."
    - phrase: "богатый"
      match: "богат"
      match_mode: density
      risk: low
      basis: ru_marker_list
      note: "Ordinary word. Rate only, never presence."
    - phrase: "яркий"
      match: "ярк"
      match_mode: density
      risk: low
      basis: ru_marker_list
      note: "Ordinary word. Rate only."
    - phrase: "разнообразный"
      match: "разнообраз"
      match_mode: density
      risk: low
      basis: ru_marker_list
      note: "Ordinary word. Rate only."
    - phrase: "уникальный"
      match: "уникальн"
      match_mode: density
      risk: medium
      basis: reasoned
      note: >-
        Ordinary word, and on a comparison site it is also a claim: if a product is called unique,
        P13 requires the page to say in what respect. Rate only here; the claim is the writer's
        problem, not the pack's.
    - phrase: "инновационный"
      match: "инновацион"
      match_mode: density
      risk: low
      basis: reasoned
      note: "Rate only."
    - phrase: "широкий спектр"
      match: 'широкий (спектр|выбор|ассортимент|перечень)'
      match_mode: regex
      risk: medium
      basis: reasoned
      note: >-
        Substitutes a quantity for a count. On this project the count is in the database and can
        be stated: «17 предложений», not «широкий выбор».
    - phrase: "Это не просто X, это Y"
      match: 'Это не просто [^,.]{3,40}, это'
      match_mode: regex
      risk: medium
      basis: ru_marker_list
      note: >-
        Named in the marker list under parallelisms. Rhetorical elevation with no informational
        content. The related «не только… но и…» is measured as a rate instead (RU-34), because a
        single occurrence is ordinary Russian.
```

### 3.5 `vague_attribution` — reinforces WRT-11

Attribution that names nobody. This set is not about style: it is the linguistic surface of a
missing source, and the cheapest available signal that P1 was skipped. Every hit resolves either to
a named source with a date, or to deletion. **This is the highest-value set in the pack for a YMYL
finance site**, and the only one that escalates.

```yaml
vague_attribution:
  rule_id: LANG-RU-05
  forbidden: true
  updated_at: 2026-08-07
  next_review: 2026-11-05
  severity: WARN
  escalate_to_block_if: sentence_contains_number
  default_status: hypothesis
  items:
    - phrase: "по данным экспертов"
      match: 'по (данным|мнению|оценкам) (экспертов|аналитиков|специалистов)'
      match_mode: regex
      risk: high
      basis: reasoned
      note: >-
        Which experts, where, when. In a sentence carrying a figure this escalates to BLOCK: an
        unattributed rate on a financial page is the exact failure P1 exists to prevent, and it is
        the one this project's own corpus is most exposed to.
    - phrase: "эксперты считают"
      match: '(эксперты|аналитики|специалисты) (считают|полагают|отмечают|прогнозируют|сходятся)'
      match_mode: regex
      risk: high
      basis: reasoned
      note: "Same defect in the active voice."
    - phrase: "как показывают исследования"
      match: 'как (показывают|свидетельствуют) (исследования|данные|результаты)'
      match_mode: regex
      risk: high
      basis: reasoned
      note: "A named study with a date and a link, or the sentence goes."
    - phrase: "согласно статистике"
      match: 'согласно (статистике|исследованиям|данным)(?!\s+(НБУ|Нацбанка|Национального банка))'
      match_mode: regex
      risk: high
      basis: reasoned
      note: >-
        The negative lookahead exempts the named regulator, because «согласно данным НБУ» is
        attribution rather than its absence. Extending that exemption list is the correct way to
        tune this entry; loosening the base pattern is not.
    - phrase: "многие считают"
      match: '(многие|некоторые) (считают|полагают|отмечают|уверены)'
      match_mode: regex
      risk: medium
      basis: reasoned
      note: "Manufactured consensus."
    - phrase: "принято считать"
      match: '(принято считать|считается, что|известно, что)'
      match_mode: regex
      risk: medium
      basis: reasoned
      note: "Attribution to nobody at all. In an encyclopaedia this is weasel wording; on a rate page it is a liability."
    - phrase: "по последним данным"
      match: 'по (последним|свежим|актуальным) данным(?!\s+(НБУ|Нацбанка|Национального банка))'
      match_mode: regex
      risk: high
      basis: reasoned
      note: >-
        Claims recency without a date. On this project every rate carries an as-of date in the
        database, so the honest form is available and the vague one is never necessary.
```

### 3.6 `generational_stopwords`

Lexical over-representation. Every entry is `density`. The Russian marker list does not attribute
its items to a model generation, so each entry records `generation: unattributed` rather than
inventing an attribution — the field exists so the list can be aged, and a fabricated value would
defeat exactly that.

```yaml
generational_stopwords:
  rule_id: LANG-RU-06
  forbidden: true
  updated_at: 2026-08-07
  next_review: 2026-11-05
  severity: WARN
  default_status: observed
  density_warn_per_1000: null # [expert judgement, needs calibration] — unset until §8
  items:
    - phrase: "обеспечивает"
      match: "обеспечива"
      match_mode: density
      risk: medium
      basis: ru_marker_list
      generation: unattributed
      first_observed: 2026-08-07
      class: lexical
      note: >-
        Named in the marker list among the verbs models reach for. Ordinary Russian and common in
        product copy, so presence matching would fire on every page this project has.
    - phrase: "подчёркивает"
      match: "подчёркива|подчеркива"
      match_mode: density
      risk: medium
      basis: ru_marker_list
      generation: unattributed
      first_observed: 2026-08-07
      class: lexical
      note: "Named in the marker list. Both spellings, because ё-folding happens after matching in some pipelines."
    - phrase: "демонстрирует"
      match: "демонстриру"
      match_mode: density
      risk: medium
      basis: ru_marker_list
      generation: unattributed
      first_observed: 2026-08-07
      class: lexical
    - phrase: "отражает"
      match: "отража"
      match_mode: density
      risk: low
      basis: ru_marker_list
      generation: unattributed
      first_observed: 2026-08-07
      class: lexical
    - phrase: "выделяет"
      match: "выделя"
      match_mode: density
      risk: low
      basis: ru_marker_list
      generation: unattributed
      first_observed: 2026-08-07
      class: lexical
    - phrase: "влияет"
      match: "влия"
      match_mode: density
      risk: low
      basis: ru_marker_list
      generation: unattributed
      first_observed: 2026-08-07
      class: lexical
    - phrase: "ключевой момент"
      match: '(ключев(ой|ым|ого)|поворотн(ый|ым|ого))\s+момент'
      match_mode: regex
      risk: medium
      basis: ru_marker_list
      generation: unattributed
      first_observed: 2026-08-07
      class: lexical
      note: "Named in the marker list as «ключевой/поворотный момент»."
    - phrase: "важный аспект"
      match: 'важн(ый|ым|ого) аспект'
      match_mode: regex
      risk: medium
      basis: reasoned
      generation: unattributed
      first_observed: 2026-08-07
      class: lexical
    - phrase: "в современном мире"
      match: 'в (современном мире|условиях современн|нынешних реалиях|эпоху цифров)'
      match_mode: regex
      risk: high
      basis: reasoned
      generation: unattributed
      first_observed: 2026-08-07
      class: lexical
      note: >-
        Scene-setting opener that carries no information and fits any topic. High risk because it
        almost always occupies the first sentence, which is the part of the document LLM
        extraction reads first (P12).
    - phrase: "стремительно развивается"
      match: '(стремительно|активно|динамично) (развива|раст|набира)'
      match_mode: regex
      risk: medium
      basis: reasoned
      generation: unattributed
      first_observed: 2026-08-07
      class: lexical
    - phrase: "сталкиваются с рядом проблем"
      match: 'сталкива(ются|ется) с (рядом|целым рядом) (проблем|вызовов|трудностей)'
      match_mode: regex
      risk: medium
      basis: ru_marker_list
      generation: unattributed
      first_observed: 2026-08-07
      class: lexical
      note: "Named in the marker list."
    - phrase: "в целях"
      match: 'в целях'
      match_mode: density
      risk: low
      basis: reasoned
      generation: unattributed
      first_observed: 2026-08-07
      class: transition
      note: "Also in 3.8; counted here as a rate, there as register."
```

### 3.7 `prescribed_phrases` — writer prompt

**Small and structural, by design.** A prescribed catchphrase becomes a formula the moment it is
prescribed: every article starts saying the same thing and the pack has manufactured a new tell.
What is prescribed here is grammatical form and function words, never personality. Voice comes from
specific facts (P4).

The first entry has a second job. Listing «Х — это У» as prescribed makes `rules_lint.py` fail the
build if anyone later adds a rule forbidding the dash — the intersection invariant becomes the
enforcement mechanism for RU-01.

```yaml
prescribed_phrases:
  rule_id: LANG-RU-07
  forbidden: false
  updated_at: 2026-08-07
  next_review: 2026-11-05
  severity: INFO
  default_status: deterministic
  items:
    - phrase: "Х — это У"
      match_mode: phrase
      risk: low
      class: grammatical_form
      basis: orthographic
      note: >-
        The copular dash is grammatically required in Russian when the predicate is a noun and the
        copula is absent. It is listed here so that any future rule penalising the dash collides
        with the intersection invariant and fails the build rather than reaching a corpus (RU-01).
    - phrase: "но"
      match_mode: phrase
      risk: low
      class: simple_transition
      basis: language_independent
      note: >-
        Prescribed against «однако» and «тем не менее» in mid-sentence position. A plain
        conjunction where a heavy one would do is the cheapest register correction available.
    - phrase: "поэтому"
      match_mode: phrase
      risk: low
      class: simple_transition
      basis: language_independent
      note: >-
        Prescribed against «в связи с этим» and «таким образом». Distinct from «Именно поэтому»
        as a section opener, which 3.1 forbids for an unrelated reason: the normalized forms
        differ, so the invariant is satisfied and both rules stand.
    - phrase: "мы проверили"
      match_mode: phrase
      risk: low
      class: grammatical_form
      basis: language_independent
      note: >-
        First person plural with a past-tense verb, for statements about our own work: what we
        measured, checked, counted, called. This is a grammatical frame, not a slogan — the
        sentence that follows must contain the actual finding, and it is the frame P4 identifies
        as the thing a model cannot produce without having done the work.
    - phrase: "по состоянию на"
      match_mode: phrase
      risk: low
      class: grammatical_form
      basis: language_independent
      note: >-
        Prescribed with an explicit date attached. Read together with the entry in 3.2 that
        forbids «по состоянию на момент обновления моей базы»: the difference is a real date
        versus a model's self-reference, and on this project every rate carries one in the
        database. The normalized forms differ, so both stand.
```

### 3.8 `bureaucratic_constructions` — `ru-local`

Канцелярит: the Russian bureaucratic register. It is a native tradition with its own literature and
its own name, which is why it earns a set rather than living in `promo_lexicon`. Two independent
reasons it belongs in a machine-text pack: models reproduce it heavily, and it is the register in
which a sentence can be grammatical, long and contentless at the same time.

Entirely `density` and `regex` at low-to-medium risk. Any one of these constructions is legitimate
Russian; a page built out of them is a page that says nothing.

```yaml
bureaucratic_constructions:
  rule_id: LANG-RU-08
  forbidden: true
  updated_at: 2026-08-07
  next_review: 2026-11-05
  severity: WARN
  default_status: hypothesis
  density_warn_per_1000: null # [expert judgement, needs calibration] — unset until §8
  never_applies_inside: [quotation, code, cited_verbatim, legal_boilerplate]
  items:
    - phrase: "является"
      match: "явля(ется|ются)"
      match_mode: density
      risk: medium
      basis: reasoned
      note: >-
        The copula-as-filler. «Кредит является продуктом банка» carries less than «Кредит — это
        продукт банка», which is why the dash construction is prescribed in 3.7. Rate only: in
        definitional prose the verb is sometimes correct.
    - phrase: "осуществляется"
      match: "осуществля"
      match_mode: density
      risk: medium
      basis: reasoned
      note: "Nominalized action with the agent removed. «Погашение осуществляется» — by whom?"
    - phrase: "производится"
      match: "производ(ится|ятся)"
      match_mode: density
      risk: low
      basis: reasoned
    - phrase: "в рамках"
      match: "в рамках"
      match_mode: density
      risk: low
      basis: reasoned
    - phrase: "на сегодняшний день"
      match: 'на (сегодняшний день|данный момент|текущий момент)'
      match_mode: regex
      risk: medium
      basis: reasoned
      note: >-
        Says «now» in five words and dates nothing. On this project the honest replacement is the
        as-of date the database already carries (3.7).
    - phrase: "в случае наличия"
      match: 'в случае (наличия|отсутствия|необходимости)'
      match_mode: regex
      risk: medium
      basis: reasoned
      note: "Conditional inflation: «если есть» is the same sentence."
    - phrase: "вышеуказанный"
      match: "выше(указанн|упомянут|приведённ|приведенн|перечисленн)"
      match_mode: regex
      risk: medium
      basis: reasoned
      note: "Also in 3.1 as a section opener; here it is counted anywhere in the body."
    - phrase: "данный"
      match: "данн(ый|ая|ое|ые|ого|ой|ым|ых)"
      match_mode: density
      risk: low
      basis: reasoned
      note: >-
        Rate only, and deliberately low risk. «Данные» as a noun is an ordinary and frequent word
        on this project; a presence rule here would fire on every page carrying a table.
    - phrase: "verbal noun chain"
      match: '\w+(ание|ение|ация)\s+\w+(ания|ения|ации)'
      match_mode: regex
      risk: medium
      basis: reasoned
      note: >-
        Two stacked nominalizations in the genitive («осуществление погашения задолженности»).
        This is the construction Russian editorial tradition names first, and the rate of it is
        measured separately as RU-31.
```

### 3.9 `technical_defects_ru` — `ru-local`, the only set permitted to block

Every entry is a fact about the Russian writing system or about character encoding. None is a
frequency claim, so all carry `status: deterministic`, which is the only status the doctrine permits
to hold a `BLOCK`. False-positive rate outside quoted spans is effectively zero, and quoted spans
are excluded by code before any rule runs.

**Patterns here are written with escape sequences, never with the literal characters they detect.**
The Ukrainian pack learned this expensively: its zero-width entry contained real zero-width
characters and its mojibake entry a raw control byte, so the block stopped being valid YAML and the
only BLOCK-capable set in the pack silently failed to load. The set that detects encoding damage was
disabled by encoding damage, and nothing reported it.

```yaml
technical_defects_ru:
  rule_id: LANG-RU-09
  forbidden: true
  updated_at: 2026-08-07
  next_review: 2026-11-05
  severity: BLOCK
  default_status: deterministic
  never_applies_inside: [quotation, code, cited_verbatim, proper_name_foreign]
  items:
    - phrase: "letters absent from the Russian alphabet"
      match: "[іїєґІЇЄҐ]"
      match_mode: regex
      risk: high
      basis: orthographic
      note: >-
        і, ї, є, ґ and their capitals do not exist in the Russian alphabet. Presence outside a
        quoted Ukrainian span means the text passed through Ukrainian or through a mixed corpus.
        On a site whose ru locale is produced alongside a uk one this is the single most likely
        pipeline defect, and it is the exact mirror of the ы/ъ/э/ё rule in `lang/uk.md` 3.10.

        This is a character-inventory fact and nothing more. It is NOT a stylistic
        «ukrainianisms» set: `lang/uk.md` §9-2 states that the reverse of the russism set does not
        exist, linguistically or as a pipeline signal, and this pack does not create one (§4,
        RU-04).
    - phrase: "Latin homoglyphs inside Cyrillic tokens"
      named_check: mixed_script_token
      match_mode: named
      risk: high
      basis: orthographic
      note: >-
        A token containing both Cyrillic and Latin characters — а, е, о, р, с, х, у and А, В, Е,
        К, М, Н, О, Р, С, Т, Х substituted from Latin. Produced by copy-paste and by some
        generation pipelines. Breaks search, anchors and deduplication silently.

        Declared as a named check rather than a pattern because homoglyph substitution is a
        property of a token, not of a character, and no lookahead formulation can express it. The
        Ukrainian pack shipped `\b(?=\p{Cyrillic})(?=\p{Latin})\S+\b` for this, which requires one
        character to belong to two scripts at once: it compiled, reviewed cleanly, and matched
        nothing for as long as it existed.
    - phrase: "zero-width and narrow no-break characters"
      match: "[\u200B\u200C\u200D\uFEFF\u202F\u00AD]"
      match_mode: regex
      risk: high
      basis: orthographic
      note: >-
        Already covered by the language-independent WRT-52. Repeated here because these leak from
        model output directly and because this locale's text passes through a translation stage
        that adds copy-paste opportunities.
    - phrase: "mojibake from cp1251/utf-8 confusion"
      match: "[\xD0\xD1][\x80-\xBF]"
      match_mode: regex
      risk: high
      basis: orthographic
      note: >-
        Encoding damage. Russian legacy content in cp1251 is common enough that a migration
        touches it, and this project's corpus came out of an older stack.
    - phrase: "wrong apostrophe character"
      match: "[`ʹ′']"
      match_mode: regex
      severity: WARN
      risk: medium
      basis: orthographic
      note: >-
        Narrower than the Ukrainian rule and downgraded accordingly. Russian has no word-internal
        apostrophe of its own; it needs U+2019 only in transliterated names («О’Коннор»). A
        backtick or prime there is a defect, but it cannot break tokenization across the corpus
        the way it does in Ukrainian, so this is WARN and the set ceiling does not apply. Stated
        as a per-entry downgrade because prose that disagrees with the field is prose the machine
        ignores.
    - phrase: "straight double quotes in body prose"
      match: '"[^"]{2,}"'
      match_mode: regex
      severity: WARN
      risk: medium
      basis: orthographic
      note: >-
        Russian typography requires «…» at the outer level (§5.2). WARN rather than BLOCK because
        CMS pipelines legitimately produce straight quotes and a typographic preference must never
        stop a publication.
```

---

## §4. The four traps — prohibitions

The cheapest way to build this pack would be to translate the English one, or — more tempting here,
and worse — to mirror the Ukrainian one. Both produce a pack that damages correct Russian. Each trap
below is a rule, not a caution.

### RU-01. The dash is not a marker, and the primary source is wrong about it in this language

**Prohibition.** No rule in this pack, no script, and no writer prompt may penalise the presence of
`—`, convert it to a comma, or use dash density as evidence of machine authorship in the way the
English rule does.

**Why this trap is sharper here than in Ukrainian.** The Russian marker list — the primary source
this whole pack is built on — names «чрезмерное использование длинного тире» as a marker. It is
right about the excess and it cannot be applied as written, because in Russian the dash is
**grammatically obligatory** between subject and predicate when the predicate is a noun and the
copula is absent: «Кредит — это заём». A rule that counts dashes and rewrites them does not clean the
text, it makes it ungrammatical. The two statements are only compatible if the metric is a rate and
the remedy is never a rewrite.

**Recorded incident.** Applying the English rule to Cyrillic converted **349 grammatically correct
occurrences into commas** before anyone noticed. → P5, and `lang/uk.md` §4 UK-01, which records the
same incident from the Ukrainian side.

**What is permitted instead.** Anomalous _density_ only, as an `INFO` metric, with no automatic
rewriting: `> 8` dashes per 1,000 words, or `> 25 %` of sentences containing one
`[expert judgement, needs calibration — carried from the marker list, never measured on Russian]`.
If a replacement is ever made, `—` may become an en dash `–` and never a comma.

The construction «Х — это У» is listed in `prescribed_phrases` (3.7) precisely so that the
intersection invariant fails the build if anyone later adds a rule forbidding it.

### RU-02. Word counting and tokenization must be Unicode-aware

**Prohibition.** `wc -w`, whitespace splitting, and `\b`/`\w` under a non-Unicode regex mode are
forbidden anywhere Russian text is measured.

**Recorded incident.** A live measurement using `wc -w` reported an English locale as **six times
larger** than a Ukrainian one when the two were at parity, and the conclusion drawn from it was the
exact inverse of the truth. → P5

**A second form of the same trap, met while writing this pack.** In JavaScript, `\w` remains
ASCII-only even under the `u` flag, so the natural-looking class `[^\W\d_]` matches no Cyrillic at
all. Counting the rendered text of a Russian page with it returned **47 words where the correct
count was 601**. The failure is silent, the number is plausible, and it is off by a factor of
thirteen. Cyrillic word counting in JavaScript requires `\p{L}` with the `u` flag; in Python, `re`
under `str` patterns is already Unicode-aware.

**Russian-specific addition.** The hyphen is word-internal: «из-за», «по-моему», «кто-то»,
«когда-нибудь», «интернет-банкинг». A naive `\w+` splits every one of them. Unlike Ukrainian, the
apostrophe is not a general concern — it appears only in transliterated names — but the setting is
the same because the failure mode is.

### RU-03. Anchor normalization requires lemmatization

**Prohibition.** The one-anchor-one-URL invariant (P6, `07-linking.md`) must not be enforced on
surface forms for this locale.

**Why.** Russian inflects for six cases, three genders and two numbers. The same anchor appears as
**«кредит онлайн» / «кредита онлайн» / «кредиту онлайн» / «кредитом онлайн» / «кредиты онлайн»**. On
surface forms these are five distinct keys, they never collide, and the invariant reports clean while
five pages compete for one anchor. The failure is silent: the check passes and the guarantee it was
written to provide does not exist.

**Tooling — unverified.** Candidates include `pymorphy3`, Natasha (`razdel` plus `slovnet`), Stanza
and UDPipe. **None has been evaluated for this project.** Whichever is chosen is pinned by version in
`.kiln/project.yml`, because a lemmatizer upgrade silently re-partitions the anchor registry.

**Declared as `lemmatizer: unresolved` in §2 rather than omitted**, so the hole is a value a script
can read instead of an absence that reads as handled.

### RU-04. The sibling locale is not a mirror, and it is not a comparison corpus

This is the trap specific to `ru`, and it has three faces. It exists because on the projects Kiln is
deployed to, the Russian locale is produced alongside a Ukrainian one rather than independently.

**First: do not build a «ukrainianisms» set.** It is the obvious counterpart to `russisms_calques` in
`lang/uk.md` 3.8 and it must not be written. `lang/uk.md` §9-2 states the position: the reverse set
is not symmetric to the original, neither linguistically nor in what it indicates about the pipeline.
Ukrainian influence on Russian in Ukraine is ordinary regional usage, not a defect, and a pack that
treats it as one would flag correct Russian and sand off exactly the cultural nuance P4 names as the
strongest human signal. What **is** legitimate is the character-inventory rule in 3.9: `і`, `ї`, `є`,
`ґ` are not letters of the Russian alphabet, which is an orthographic fact and not an opinion about
register.

**Second: n-gram overlap must exclude the sibling locale.** WRT-23 compares a draft against the
corpus it competes with. If the project's own Ukrainian version of the same page is inside that
corpus, the Russian translation is flagged as plagiarism of itself, at a similarity that looks
damning. Locale siblings are excluded in `project.yml`, by configuration, never by loosening the
threshold. → `lang/uk.md` §9-5

**Third: thresholds do not cross.** Both packs write to `.kiln/thresholds.yml` under separate locale
keys. A threshold calibrated on Ukrainian text is not evidence about Russian text, however close the
languages are — closeness is what makes the mistake easy rather than what makes it safe. Neither pack
imports from the other at runtime, and a change to one is not a change to the other.

---

## §5. Structure, punctuation and typography

### 5.1 Headings

Russian uses **sentence case**. Title Case is an English convention, and applied to Russian it is a
direct machine-translation marker — the Russian list names «все слова в заголовках написаны с
заглавной буквы» outright.

| Rule    | Description                                                                | Severity |
| ------- | -------------------------------------------------------------------------- | -------- |
| `RU-10` | Capitals in a heading beyond the first word or a proper noun               | WARN     |
| `RU-11` | Heading ends with a full stop                                              | WARN     |
| `RU-12` | Heading level skipped (H2 → H4)                                            | WARN     |
| `RU-13` | First paragraph opens by defining the term in the heading back at the reader | WARN     |

`RU-13` note: the pattern is «„Кредитная история" — это состояние, при котором…». The core rule
WRT-30 covers the useful half of this; `RU-13` catches the dictionary-entry opening specifically.

### 5.2 Quotation marks

Russian typography nests as **«…» outer, „…" inner**. Straight `"` are a CMS artifact; English curly
`"…"` are a translation artifact. The marker list separately names «чрезмерное выделение кавычками» —
scare quotes used for emphasis rather than for quotation.

| Rule    | Description                                                     | Severity   |
| ------- | --------------------------------------------------------------- | ---------- |
| `RU-14` | Straight `"` in body prose                                      | WARN (3.9) |
| `RU-15` | English curly quotes anywhere in body prose                     | WARN       |
| `RU-16` | Outer level not `«»`                                            | INFO       |
| `RU-17` | Quotation marks used for emphasis rather than quotation         | INFO       |

### 5.3 Other typography

| Rule    | Description                                                                  | Severity                                                               |
| ------- | ---------------------------------------------------------------------------- | ---------------------------------------------------------------------- |
| `RU-18` | Bold applied at every repetition of a term                                   | WARN                                                                   |
| `RU-19` | List items formatted `**Заголовок:** текст` above a share threshold          | WARN                                                                   |
| `RU-20` | Emoji or non-standard bullets outside quoted spans                           | WARN — BLOCK when the project declares a design system forbidding them |
| `RU-21` | Month names, weekdays or nationalities capitalized                           | WARN                                                                   |
| `RU-22` | Decimal separator inconsistent within the document                           | WARN                                                                   |
| `RU-23` | `ё` and `е` used inconsistently for the same word within one document        | INFO                                                                   |

`RU-19` note: the marker list names «вертикальные списки с жирными заголовками и двоеточием» and
«чрезмерное использование жирного шрифта» as separate markers. Both are share metrics, never presence
rules: one bolded lead-in is normal formatting.

`RU-21` note: Russian does not capitalize «август», «понедельник», «украинец»; English does. A
reliable translation marker.

`RU-22` note: Russian uses the comma as decimal separator («3,9 %») and a non-breaking space for
thousands. A document mixing `3.9` and `3,9` was assembled from two pipelines. Directly relevant to
this project, where every page carries rates.

`RU-23` note: **INFO and never higher.** Both spellings are permitted in Russian and consistency is
an editorial preference, not a rule. It is recorded only because a document that switches between
them mid-way was usually assembled from two sources. `fold_yo_to_ye` in §2 means this never affects
matching.

---

## §6. Statistical form metrics

The language-independent metrics WRT-40…WRT-46 apply to Russian in full. **Their thresholds do not.**
Every number in core group E was derived from English-language literature.

**Status for this locale: all group E metrics are `INFO` until §8 calibration completes.** They are
computed, recorded and reported; they never raise WARN and never raise BLOCK. Reporting a WARN
against an unmeasured threshold manufactures confidence out of nothing, which is the specific risk
`05-writing-core.md` §11-3 records.

Russian-specific candidate metrics, all `INFO`:

| ID      | Metric                                                              | Carried threshold                              | Status |
| ------- | ------------------------------------------------------------------- | ---------------------------------------------- | ------ |
| `RU-30` | Adverbial participle clauses (деепричастные обороты) per 1,000 words | `> 6` `[marker list, unmeasured]`              | INFO   |
| `RU-31` | Verbal nouns `-ание/-ение/-ация` per 1,000 words                    | `> 25` `[marker list, unmeasured]`             | INFO   |
| `RU-32` | Identical list-item openings                                        | `> 8 %` `[marker list, unmeasured]`            | INFO   |
| `RU-33` | Dash density per 1,000 words                                        | `> 8` `[marker list, unmeasured]`              | INFO   |
| `RU-34` | Parallel constructions «не только… но и…» per 1,000 words           | unset `[expert judgement, needs calibration]`  | INFO   |
| `RU-35` | Rule of three: three homogeneous adjectives or phrases in a row     | `> 2` occurrences `[marker list, unmeasured]`  | INFO   |
| `RU-36` | Proper noun replaced by a descriptive synonym after introduction    | `> 2` occurrences `[marker list, unmeasured]`  | INFO   |
| `RU-37` | Bureaucratic construction density (3.8, medium-risk entries only)   | unset `[expert judgement, needs calibration]`  | INFO   |

`RU-30` note: the marker list names «бесконечные деепричастные обороты» and illustrates the failure
with the classic dangling participle «подъезжая к станции, с меня слетела шляпа». The subject-loss
case is a judge question (RU-40), not a counter; the rate is what is counted here.

`RU-32` is set stricter than the general opener-repetition rule (WRT-43, `> 12 %`). That asymmetry
is inherited from the marker list and is itself unverified — a specific thing to test in §8. If
Russian list openers repeat naturally at 10 %, the stricter threshold is pure false-positive
generation.

`RU-35` note: the marker list calls this «правило трёх» — three homogeneous adjectives or phrases in
sequence («богатый, яркий и разнообразный»). It needs syntactic parsing to count reliably and is
recorded as a candidate rather than a working counter.

`RU-36` note: substituting «ключевой игрок», «главный герой», «ведущий эксперт» for a name already
introduced — elegant variation. Requires coreference, so it is a judge question in practice.

---

## §7. Judge questions for this locale

Per `05-writing-core.md` §7, binary questions only, each requiring a quotation. These supplement the
core questions and do not replace them. They are asked **in Russian**, because the text is Russian.

| Rule    | Question to the judge                                                                                                        |
| ------- | ---------------------------------------------------------------------------------------------------------------------------- |
| `RU-40` | «Есть ли в тексте деепричастный оборот, в котором потерян субъект действия? Приведи цитату.»                                 |
| `RU-41` | «Читается ли этот абзац как перевод с другого языка, а не как текст, написанный по-русски? Приведи цитату.»                  |
| `RU-42` | «Является ли этот фрагмент прямой речью, цитатой или названием документа?» — asked **before** any rule from 3.8 or 3.9 runs  |
| `RU-43` | «Содержит ли финальный раздел хотя бы одно утверждение, которого нет в теле статьи?» — decides 3.3                           |
| `RU-44` | «Есть ли в тексте число, ставка или срок без указания источника и даты? Приведи цитату.» — reinforces 3.5 and P1             |
| `RU-45` | «Обращается ли текст к читателю от лица ассистента или упоминает собственные ограничения? Приведи цитату.» — reinforces 3.2  |

`RU-44` is the question that matters most on this project. Everything else in this pack is style;
this one is the difference between a page that is merely machine-written and a page that is wrong
about money.

---

## §8. Calibration protocol

Until this runs, everything in §3 and §6 is a prior and is labelled as one. The protocol is taken
wholesale from `lang/uk.md` §8, as that pack's §9-6 anticipates, with the sampling frame changed to
Russian.

### 8.1 What to collect

- **Human baseline.** At least 100 Russian documents in the target niche, written before 2023 by
  identifiable humans, in the genres the project actually publishes: product descriptions, news,
  reference entries. Pre-2023 matters — a corpus assembled later is contaminated by the thing being
  measured.
- **Machine baseline.** At least 100 documents generated for the same briefs, across at least two
  model families, unedited.
- **Our own published corpus.** Everything the project has shipped in `ru`, tagged by whether it
  passed human review.

### 8.2 What to compute

For every `density` entry: the rate distribution in each of the three corpora. For every `phrase` and
`regex` entry: the share of documents containing at least one hit. For every metric in §6: the full
distribution, not the mean.

### 8.3 Promotion criteria

An entry moves from `observed` to `calibrated` only when the human and machine distributions
separate: the machine median sits outside the human interquartile range, on at least 100 documents
per side. A threshold is then set at the human 90th percentile, never at the machine median, because
the cost of a false positive here is a reviewer's attention and the cost of a false negative is one
paragraph nobody rewrote.

**No entry is ever promoted to `BLOCK` by this protocol.** Calibration raises `INFO` to `WARN` and
stops there. Only 3.9 blocks, and its entries are not statistical.

### 8.4 Cadence

Recompute quarterly, aligned with `next_review`. An entry whose distributions have converged is
**deleted**, not downgraded: it was never a marker, and keeping it costs reviewer attention every
run. Deletions and the data behind them go to `doctrine/CHANGELOG.md` (P15).

### 8.5 The open research question

The Russian marker list was assembled on encyclopaedic prose by editors reviewing Wikipedia
submissions. This pack is applied to consumer finance. Nobody has measured how much of that list
transfers, and the honest expectation is that the promotional entries in 3.4 transfer poorly while
3.2 and 3.5 transfer well. §8 is the only thing that will settle it, and until it runs the transfer
assumption is the largest unmeasured quantity in this file.

---

## §9. The `uk` sibling locale

**`uk.md` is a separate pack. Rules never cross between the two** (P5). Stated from this side because
a reader arriving at `ru.md` first will not have read the Ukrainian one.

1. **`russisms_calques` (`lang/uk.md` 3.8) must never be loaded for `ru`.** The entire set is
   meaningless here: «являється» is a russism in Ukrainian, and «является» is simply correct Russian.
2. **The reverse set is not created** — see RU-04, first face.
3. **`bureaucratic_constructions` exists in both packs and they are not copies.** The Ukrainian set
   is scoped to constructions that are simultaneously calques; this one is scoped to канцелярит,
   which is native. Overlapping surface forms are coincidence, not shared provenance, and the two
   sets carry different rule identifiers and separate counters.
4. **Thresholds are per locale**, in `.kiln/thresholds.yml` under separate keys.
5. **n-gram overlap excludes the sibling** — RU-04, second face.
6. **This pack does not import from `lang/uk.md` at runtime.** Where a construction appears in both,
   it was written twice on purpose.

---

## §10. Prohibitions

| Prohibition                                                               | Basis                          |
| ------------------------------------------------------------------------- | ------------------------------ |
| Penalising the dash, or replacing it with a comma                         | RU-01, P5                      |
| `wc -w`, whitespace splitting, non-Unicode `\b` on Russian text           | RU-02, P5                      |
| ASCII-only `\w` classes in JavaScript on Cyrillic                         | RU-02                          |
| Splitting tokens at the hyphen                                            | RU-02                          |
| Enforcing the anchor invariant on surface forms                           | RU-03, P6                      |
| Building a «ukrainianisms» set as the mirror of `lang/uk.md` 3.8          | RU-04, `lang/uk.md` §9-2       |
| Including the sibling locale in the n-gram comparison corpus              | RU-04                          |
| Carrying a threshold calibrated on Ukrainian into this pack               | RU-04, P10                     |
| Applying 3.8 or 3.9 inside quotations, legal wording or `verbatim` spans  | §3.8, §3.9, P1                 |
| Automatically rewriting register anywhere                                 | P4                             |
| Blocking publication on any stylistic entry in this pack                  | §8.3, P3                       |
| Using an AI detector as a gate for Russian content                        | P3                             |
| Translating the English stop-list into Russian and shipping it            | §1, §4                         |
| Treating an `observed` entry as a measurement                             | §1-1                           |
| Promoting a threshold into this file rather than `.kiln/thresholds.yml`   | P10                            |
| Banning a `match_mode: density` term by presence                          | §2                             |
| Adding a pattern without demonstrating it fires on a positive case        | §11-5                          |
| Writing a literal invisible or control character into a pattern           | §3.9                           |
| Renaming a contract key (`items`, `phrase`) to something the pack prefers | §2                             |

---

## §11. Conflicts and open items

**1. The template prescribes a form that fails the linter.** `lang/_template.md` §2.1 shows
`anaphora_openers` carrying `severity: BLOCK`. `rules_lint.py` check 9 errors on any set declaring
`severity: BLOCK` without `default_status: deterministic`, and the entries in that set are
necessarily statistical. A pack that follows the template literally does not build. This pack
follows `lang/uk.md` instead and declares no severity on the set, leaving the BLOCK where it
belongs — on WRT-32 in the core. **Proposed fix:** the template should show the set without
`severity:` and say in prose that the block lives on the structural rule. Submitted as an open item
rather than fixed here, because amending the template is a change to the shared contract and P10
requires that to arrive as its own PR.

**2. Two conventions for the BLOCK-capable set.** `lang/uk.md` 3.10 declares `severity_ceiling:
BLOCK`, which no check reads; this pack's 3.9 declares `severity: BLOCK` with
`default_status: deterministic`, which check 9 verifies. Both express the same intent and only one
is machine-checkable. They should converge on the checkable form, in one PR that touches both packs.

**3. The disclosure conflict is unresolved, and it is inherited.** Two entries in 3.2 —
«рекомендуем проконсультироваться со специалистом» and «это лишь общая информация» — are flagged as
filler hedges while possibly being required disclosures in Ukrainian consumer finance. Neither the
regulatory requirement nor its exact wording has been established. `lang/uk.md` §11-3 records the
same open item for the same reason. **Until it is closed, both entries stay at `risk: low`,
`match_mode: regex` at low risk, and the project's required-disclosure list from onboarding takes
precedence over this pack.** Backwards, this advises deleting a legally mandated sentence.

**4. `observed` is doing more work here than in `uk.md`, and the difference should be watched.**
Twenty-two entries carry it on the strength of a practitioner list rather than a measurement. That is
a better prior than Ukrainian has, and it is still a prior. The specific risk is that the status word
makes the entries feel settled and nobody runs §8. The mitigation is that §6 holds every metric at
INFO regardless of entry status, so nothing in this pack can act on the distinction until real
distributions exist.

**5. Every regex in this file was demonstrated firing on a constructed positive case and staying
quiet on a constructed negative one** before commit, in `scripts/tests/test_lang_ru.py`. The
requirement is enforced by a test rather than by prose: an entry added without a fixture fails the
suite, which is the only form of the rule that survives a hurried commit.

**Three defects were found by that exercise, all of them in patterns that had already been reviewed
by eye.** They are recorded because the class matters more than the individual bugs — each one would
have shipped as a rule that reports success forever:

- **«ключевой момент» matched nothing.** The pattern was `(ключев|поворотн)(ый|ым|ого) момент`, which
  quietly assumes both stems take the same ending. They do not: «ключев**ой**» takes `-ой` and
  «поворотн**ый**» takes `-ый`, so the shared alternation matched neither word. Split into two stems
  with their own endings.
- **«со специалистом» matched nothing.** The pattern required the preposition `(с|к)`, and the
  natural Russian is «проконсультироваться **со** специалистом». Fixed to `(со?|к)`. A rule aimed at
  the most frequent disclosure phrase in the niche could not see its most frequent form.
- **The «Данный» opener would have fired on correct writing.** The alternation included the plural
  `ые`, which makes it match «Данные обновлены 07.08.2026» — where «данные» is the noun _data_, not
  an adjective, and where the sentence is exactly what this project's sections open with. Narrowed
  to the singular; the reasoning is recorded at the entry.

The first two are dead rules, the third is a false-positive generator, and eye review caught none of
the three. The Ukrainian pack's homoglyph guard is the precedent: it compiled, it reviewed cleanly,
and its match set was empty for as long as it shipped.

**6. The transfer assumption is unmeasured** — §8.5. Largest open quantity in the pack.

**7. Lemmatizer choice is unresolved and load-bearing.** RU-03 requires it for the anchor invariant
to function at all, and no tool has been evaluated. Until one is pinned, `07-linking.md` is silently
ineffective for this locale: the check reports clean and guarantees nothing. Highest-priority open
item.

---

## §12. Sources

**Primary, opened and read in full while writing this file (P1):**

| Source                                                                                       | Date read  | What was taken                                                                                                              |
| -------------------------------------------------------------------------------------------- | ---------- | --------------------------------------------------------------------------------------------------------------------------- |
| ru.wikipedia, «Википедия:Признаки сгенерированности текста» — https://ru.wikipedia.org/wiki/Википедия:Признаки_сгенерированности_текста | 2026-08-07 | every entry marked `basis: ru_marker_list`; the structural, typographic and user-addressing markers in §5 and §6            |

**Internal, read in full:**

| File                        | What was taken                                                                                            |
| --------------------------- | --------------------------------------------------------------------------------------------------------- |
| `00-principles.md`          | P1, P3, P4, P5, P6, P10, P12, P13, P15                                                                    |
| `05-writing-core.md`        | §6 pack contract and the seven set keys; §7 binary judge questions; group E metrics; §11-2, §11-3, §11-4  |
| `lang/_template.md`         | the entry schema, the contract checklist, the `match_mode` distinction — and the defect recorded in §11-1 |
| `lang/uk.md`                | §9 the mandate for this pack; §4 the trap framing; §8 the calibration protocol; the recorded incidents    |
| `EVIDENCE.md`               | e03 — detector unreliability, the marker-list provenance, invisible-character leakage                     |

**Verification performed:** every `regex` entry in §3 was compiled and run against a constructed
positive and a constructed negative case; `rules_lint.py` was run against the doctrine with this pack
present. Results in the pull request that introduces this file.

**Not opened, and therefore not cited as evidence:** no academic study of machine-text markers in
Russian was located. The claim in §1 that the marker list is the best available Russian source is a
statement about what was found, not a survey of what exists.
