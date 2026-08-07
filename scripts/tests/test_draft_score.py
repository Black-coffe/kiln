"""Tests for the draft scoring gate.

The fixtures are Ukrainian on purpose. Every counting bug this gate could have is invisible in
English: `wc -w` splits English correctly, `\\b` works on Latin, and an apostrophe inside a word is
rare. The pilot locale is Ukrainian, so the tests are written where the bugs actually live.
"""

from __future__ import annotations

import json
import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from kiln_common import KilnError, Thresholds, count_words, tokenize_words  # noqa: E402
import draft_score as ds  # noqa: E402


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------

MINIMAL_PACK = """# Language pack: test

```yaml
anaphora_openers:
  rule_id: LANG-UK-01
  forbidden: true
  applies_to: section_first_sentence
  items:
    - phrase: "Це"
      match: '^Це\\s'
      match_mode: regex
      risk: high
      status: hypothesis
```

```yaml
hedge_phrases:
  rule_id: LANG-UK-02
  forbidden: true
  severity_ceiling: WARN
  density_threshold_per_1000: 5.0
  items:
    - phrase: "важливо зазначити"
      match: "важливо зазначити"
      match_mode: phrase
      risk: high
      status: hypothesis
    - phrase: "демонструє"
      match: "демонстру(є|ють)"
      match_mode: density
      risk: medium
      status: hypothesis
```

```yaml
closing_formulas:
  rule_id: LANG-UK-03
  forbidden: true
  severity_ceiling: WARN
  items: []
promo_lexicon:
  rule_id: LANG-UK-04
  forbidden: true
  severity_ceiling: WARN
  items: []
vague_attribution:
  rule_id: LANG-UK-05
  forbidden: true
  severity_ceiling: WARN
  items: []
generational_stopwords:
  rule_id: LANG-UK-06
  forbidden: true
  severity_ceiling: WARN
  density_threshold_per_1000: null
  items:
    - phrase: "забезпечує"
      match: "забезпечу(є|ють)"
      match_mode: density
      risk: medium
      status: hypothesis
prescribed_phrases:
  rule_id: LANG-UK-07
  forbidden: false
  items:
    - phrase: "станом на"
      match: "станом на"
      match_mode: phrase
      status: hypothesis
```

```yaml
technical_defects_uk:
  rule_id: LANG-UK-10
  forbidden: true
  severity_ceiling: BLOCK
  items:
    - phrase: "Russian-only letters"
      match: "[ыъэё]"
      match_mode: regex
      risk: high
      status: deterministic
```
"""

# Same pack, but the blocking set holds a statistical entry. This is the malformed case: a language
# pack trying to hold a publication gate with a stylistic claim.
MALFORMED_PACK = MINIMAL_PACK.replace(
    """    - phrase: "Russian-only letters"
      match: "[ыъэё]"
      match_mode: regex
      risk: high
      status: deterministic""",
    """    - phrase: "Russian-only letters"
      match: "[ыъэё]"
      match_mode: regex
      risk: high
      status: deterministic
    - phrase: "надійний"
      match: "надійн(ий|ого)"
      match_mode: phrase
      risk: high
      status: hypothesis""",
)


CLEAN_DRAFT = """# Скільки насправді коштує кредит онлайн

Облікова ставка НБУ станом на 01.08.2026 дорівнює 13,5 % [[claim:c001]]. Ця цифра
визначає вартість грошей для самого банку, проте позичальник платить помітно більше.
Реальна річна ставка враховує комісія за видачу, страхові платежі та вартість
обслуговування рахунку. Кредитна історія лишається головним чинником при ухваленні
рішення, хоча вага цього чинника відрізняється від банку до банку.

Наша вибірка охоплює 240 заявок, поданих через сім онлайн-сервісів протягом червня і
липня. Медіанний строк розгляду склав п'ять робочих днів [[claim:c002]], тоді як самі
сервіси обіцяють два. Дострокове погашення дозволяють усі сім. Троє беруть за нього
окрему плату, і про це не сказано на сторінці з умовами.

## Чому оголошена ставка нічого не означає

Оголошена ставка описує лише тіло боргу. Поверх неї лягає разова комісія за видачу,
щомісячна плата за обслуговування та, у чотирьох випадках із семи, обов'язкове
страхування життя. Ми порахували підсумкову переплату для однакової суми та строку.
Розкид виявився втричі більшим за розкид оголошених ставок.

| Сервіс | Оголошена ставка | Підсумкова переплата |
| --- | --- | --- |
| А | 13,5 % | 4 120 грн |
| Б | 14,1 % | 3 480 грн |

Сервіс з найнижчою оголошеною ставкою опинився на п'ятому місці за підсумковою
переплатою. Це не помилка вибірки. Ми перевірили розрахунок двічі, а потім попросили
підтвердити його у службі підтримки кожного сервісу.

## Що показала перевірка відмов

Три з десяти заявок у нашій вибірці отримали відмову без пояснення причин
[[claim:c003]]. Це найгірший показник серед усіх категорій, які ми міряли протягом
року. Жоден із сервісів не надіслав письмових підстав навіть після повторного запиту.

Двоє з семи повідомили причину усно, телефоном. Формулювання при цьому відрізнялися
від того, що записано в їхніх же публічних умовах кредитування.

## Що перевірити перед подачею заявки

1. Порахуйте підсумкову переплату, а не оголошену ставку.
2. Перевірте розмір комісії за видачу та спосіб її нарахування.
3. Уточніть, чи стягується плата за дострокове погашення.
4. Запитайте письмову пропозицію до підписання договору.

Порівняно з торішніми умовами подорожчання склало 1,8 відсоткового пункту. Це менше,
ніж очікували аналітики ринку на початку року, але більше за офіційну інфляцію за той
самий період.
"""

# Deliberately short, for the density guard. A rate computed over this many words is arithmetic
# noise rather than evidence about the text.
SHORT_DRAFT = """# Коротка замітка

Ця послуга демонструє стабільність. Ставка НБУ не змінилася.
"""


def _brief(**overrides):
    brief = {
        "topic_id": "uk/credit-online",
        "locale": "uk-UA",
        "surface_type": "article",
        "target": "new: credit-online",
        "answer_intent": "Скільки насправді коштує кредит онлайн в Україні?",
        "audience": "Позичальник, який порівнює пропозиції",
        "unique_value_source": {
            "kind": "first_party_data",
            "description": "Власна вибірка з 240 заявок",
            "artifact_id": "a-2026-08-07-001",
        },
        "entity_map": {
            "core": ["НБУ", "кредитна історія", "комісія", "реальна річна ставка", "дострокове погашення"],
            "ours": ["наша вибірка", "медіанний строк розгляду"],
            "absent_ok": [],
        },
        "mandated_proof_sources": ["c001"],
        "cannibalization_check": {"max_cosine": 0.42, "nearest_url": "/credits/", "decision": "new_page"},
        "forbidden": ["гарантія схвалення"],
        "reviewers": ["facts", "domain", "voice", "utility"],
        "byline_date": "2026-08-07",
    }
    brief.update(overrides)
    return brief


def _packet(**overrides):
    packet = {
        "topic_id": "uk/credit-online",
        "locale": "uk-UA",
        "created_at": "2026-08-07",
        "claims": [
            {
                "id": "c001",
                "text": "Ставка НБУ дорівнює 13,5 %",
                "kind": "figure",
                "provenance": "third_party",
                "source_url": "https://bank.gov.ua/rates",
                "source_published_at": "2026-08-01",
                "source_tier": "primary",
                "http_status": 200,
                "volatile": True,
            },
            {
                "id": "c002",
                "text": "Середній строк розгляду — п'ять днів",
                "kind": "figure",
                "provenance": "first_party",
                "artifact_id": "a-2026-08-07-001",
                "source_url": "https://example.test/internal",
                "source_published_at": "2026-08-05",
                "source_tier": "primary",
                "http_status": 200,
            },
            {
                "id": "c003",
                "text": "Три з десяти заявок отримали відмову",
                "kind": "fact",
                "provenance": "first_party",
                "artifact_id": "a-2026-08-07-001",
                "source_url": "https://example.test/internal",
                "source_published_at": "2026-08-05",
                "source_tier": "primary",
                "http_status": 200,
            },
        ],
        "entity_map": {
            "core": ["НБУ", "кредитна історія", "комісія", "реальна річна ставка", "дострокове погашення"],
            "ours": ["наша вибірка", "медіанний строк розгляду"],
            "absent_ok": [],
        },
        # Four documents, so "present in at least half the top" is a real filter rather than the
        # degenerate case two documents produce.
        "top_corpus": [
            {
                "url": "https://a.test", "fetched_at": "2026-08-06", "words": 900,
                "entities": ["НБУ", "кредитна історія", "комісія", "реальна річна ставка",
                             "дострокове погашення", "офіційний дохід", "страховка"],
            },
            {
                "url": "https://b.test", "fetched_at": "2026-08-06", "words": 850,
                "entities": ["НБУ", "кредитна історія", "комісія", "реальна річна ставка",
                             "дострокове погашення", "офіційний дохід", "поручитель"],
            },
            {
                "url": "https://c.test", "fetched_at": "2026-08-06", "words": 1100,
                "entities": ["НБУ", "кредитна історія", "комісія", "реальна річна ставка",
                             "дострокове погашення", "штраф"],
            },
            {
                "url": "https://d.test", "fetched_at": "2026-08-06", "words": 700,
                "entities": ["НБУ", "кредитна історія", "комісія", "реальна річна ставка", "застава"],
            },
        ],
        "open_questions": ["Чи змінить НБУ ставку у вересні"],
    }
    packet.update(overrides)
    return packet


@pytest.fixture()
def pack(tmp_path: Path) -> ds.LanguagePack:
    path = tmp_path / "lang" / "uk.md"
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(MINIMAL_PACK, encoding="utf-8")
    return ds.parse_language_pack(path)


@pytest.fixture()
def artifacts_dir(tmp_path: Path) -> Path:
    import hashlib

    root = tmp_path / "artifacts" / "a-2026-08-07-001"
    root.mkdir(parents=True, exist_ok=True)
    data = root / "sample.csv"
    data.write_text("id,days\n1,5\n2,6\n", encoding="utf-8")
    digest = hashlib.sha256(data.read_bytes()).hexdigest()
    (root / "manifest.yml").write_text(
        "artifact_id: a-2026-08-07-001\n"
        "kind: export\n"
        "created_at: 2026-08-07\n"
        "created_by: reviewer-1\n"
        "files: ['sample.csv']\n"
        f"sha256: ['{digest}']\n"
        "method: Вивантаження з внутрішньої системи заявок\n"
        "claims: ['c002', 'c003']\n",
        encoding="utf-8",
    )
    return tmp_path / "artifacts"


def _thresholds(**local) -> Thresholds:
    return Thresholds(ds.DOCTRINE_DEFAULTS, local)


def _score(draft=CLEAN_DRAFT, brief=None, packet=None, pack=None, artifacts=None, **kwargs):
    return ds.score(
        draft,
        brief if brief is not None else _brief(),
        packet if packet is not None else _packet(),
        pack,
        _thresholds(),
        artifacts_dir=artifacts,
        **kwargs,
    )


def _mutate(text: str, old: str, new: str) -> str:
    """Replace, and fail loudly when the target is not there.

    A plain `str.replace` on a missing target returns the string unchanged, so a test that mutates
    a fixture into a violation quietly asserts against the clean fixture instead and passes. Every
    such test is then permanently green and permanently worthless.
    """
    if old not in text:
        raise AssertionError(f"fixture does not contain {old!r}; the test is not exercising what it claims")
    return text.replace(old, new, 1)


def _rule(result: ds.ScoreResult, rule_id: str) -> ds.RuleResult:
    for r in result.rules:
        if r.id == rule_id:
            return r
    raise AssertionError(f"{rule_id} not present in {[r.id for r in result.rules]}")


# ---------------------------------------------------------------------------
# Unicode handling
# ---------------------------------------------------------------------------


def test_fixture_is_long_enough_for_density_rules_to_mean_anything():
    """Guards the fixture itself, not the code.

    Several tests below assert that a density rule fires or does not fire. All of them become
    meaningless if the fixture drops under the minimum length, because the guard then converts
    every density verdict into an INFO report and the assertions pass for the wrong reason.
    """
    assert count_words(CLEAN_DRAFT) > ds.DOCTRINE_DEFAULTS["lang.density_min_words"]
    assert count_words(SHORT_DRAFT) < ds.DOCTRINE_DEFAULTS["lang.density_min_words"]


def test_apostrophe_word_is_one_token():
    """«п'ять» is one word. A naive \\w+ splits it and every density metric downstream is wrong."""
    assert tokenize_words("п'ять") == ["п'ять"]
    assert count_words("п'ять робочих днів") == 3
    assert tokenize_words("об'єкт") == ["об'єкт"]
    assert tokenize_words("будь-який") == ["будь-який"]


def test_cyrillic_and_latin_are_counted_by_the_same_rule():
    """The failure this guards against reported one locale as six times larger than the other.

    Both strings below are eight words. A tokenizer that splits on whitespace gets this right by
    accident; one that relies on an ASCII word class returns zero for the Cyrillic line.
    """
    uk = "Ставка змінилася вчора і це важливо для позичальника"
    en = "The rate changed yesterday and this matters greatly"
    assert count_words(uk) == 8
    assert count_words(en) == 8
    assert count_words("а б в г д") == 5


def test_entity_matching_does_not_use_word_boundaries():
    """Entity presence is a token-sequence match, which behaves identically in every script."""
    tokens = tokenize_words("Ставка НБУ станом на сьогодні")
    assert ds._entity_present(ds._entity_tokens("НБУ"), tokens)
    assert not ds._entity_present(ds._entity_tokens("НБУ України"), tokens)


def test_entity_matching_is_surface_form_only_and_inflection_defeats_it():
    """A known limitation, asserted so it cannot be mistaken for a guarantee.

    Ukrainian inflects for seven cases. «наша вибірка» in the entity map does not match
    «нашій вибірці» in the text, so entity coverage and entity gain both under-report on
    inflected languages until a lemmatizer is chosen. The doctrine records this as the pilot
    locale's highest-priority open item; the test exists so a future lemmatizer has a failing
    assertion to flip.
    """
    tokens = tokenize_words("У нашій вибірці з 240 заявок")
    assert not ds._entity_present(ds._entity_tokens("наша вибірка"), tokens)
    assert ds._entity_present(ds._entity_tokens("наша вибірка"), tokenize_words("Наша вибірка охоплює 240 заявок"))


# ---------------------------------------------------------------------------
# The clean case
# ---------------------------------------------------------------------------


def test_clean_draft_blocks_nothing(pack, artifacts_dir):
    result = _score(pack=pack, artifacts=artifacts_dir)
    assert result.blocked_by == [], f"unexpected blocks: {result.blocked_by}"
    assert result.verdict == "REWORK"


def test_clean_draft_cannot_reach_pass_without_the_agent(pack, artifacts_dir):
    """PASS requires every BLOCK rule to have actually evaluated. Four of them belong to the agent.

    This is the central safety property: an unrun check is not a passed check. If this test ever
    starts returning PASS from code alone, a `requires_agent` placeholder has been allowed to count
    as a pass, and the gate has stopped gating.
    """
    result = _score(pack=pack, artifacts=artifacts_dir)
    assert result.verdict != "PASS"
    for rule_id in ("WRT-05", "WRT-10", "WRT-11", "WRT-15"):
        assert _rule(result, rule_id).status == "requires_agent"
        assert rule_id in result.unresolved


def test_agent_rules_are_never_marked_pass(pack, artifacts_dir):
    result = _score(pack=pack, artifacts=artifacts_dir)
    for rule_id in ds.AGENT_RULES:
        assert _rule(result, rule_id).status != "pass"


# ---------------------------------------------------------------------------
# Blocking rules
# ---------------------------------------------------------------------------


def test_missing_artifact_blocks_on_the_effort_gate(pack):
    """No artefact means OCD is zero, and zero is a block. This is P13 made executable."""
    result = _score(pack=pack, artifacts=None)
    assert _rule(result, "WRT-03").status == "requires_input"

    packet = _packet()
    for claim in packet["claims"]:
        claim["provenance"] = "third_party"
        claim.pop("artifact_id", None)
    result = _score(pack=pack, packet=packet, artifacts=None)
    wrt20 = _rule(result, "WRT-20")
    assert wrt20.status == "fail" and wrt20.severity == "BLOCK"
    assert "WRT-20" in result.blocked_by
    assert result.verdict == "BLOCK"


def test_word_count_requirement_in_brief_blocks(pack, artifacts_dir):
    brief = _brief(required_blocks=["minimum 1900 words", "table"])
    result = _score(pack=pack, brief=brief, artifacts=artifacts_dir)
    wrt04 = _rule(result, "WRT-04")
    assert wrt04.status == "fail"
    assert "WRT-04" in result.blocked_by


def test_volume_expectation_is_a_forecast_and_is_exempt(pack, artifacts_dir):
    """The doctrine permits a length forecast and forbids a length target. The field is the tell."""
    brief = _brief(volume_expectation="around 1800 words")
    result = _score(pack=pack, brief=brief, artifacts=artifacts_dir)
    assert _rule(result, "WRT-04").status == "pass"


def test_dead_link_blocks(pack, artifacts_dir):
    packet = _packet()
    packet["claims"][0]["http_status"] = 404
    result = _score(pack=pack, packet=packet, artifacts=artifacts_dir)
    assert _rule(result, "WRT-13").status == "fail"
    assert "WRT-13" in result.blocked_by


def test_tool_marker_blocks(pack, artifacts_dir):
    draft = CLEAN_DRAFT + "\n\nДжерело: oai_citation щось\n"
    result = _score(draft=draft, pack=pack, artifacts=artifacts_dir)
    assert _rule(result, "WRT-50").status == "fail"
    assert "WRT-50" in result.blocked_by


def test_invisible_character_blocks(pack, artifacts_dir):
    draft = _mutate(CLEAN_DRAFT, "ставка НБУ", "ставка​НБУ")
    result = _score(draft=draft, pack=pack, artifacts=artifacts_dir)
    assert _rule(result, "WRT-52").status == "fail"


def test_missing_cannibalization_check_blocks(pack, artifacts_dir):
    """A brief with no stage-2 check is a brief where the check did not run."""
    brief = _brief(cannibalization_check={})
    result = _score(pack=pack, brief=brief, artifacts=artifacts_dir)
    assert _rule(result, "WRT-24").status == "fail"


def test_cannibalization_above_threshold_blocks(pack, artifacts_dir):
    brief = _brief(cannibalization_check={"max_cosine": 0.91, "nearest_url": "/credits/", "decision": "new_page"})
    result = _score(pack=pack, brief=brief, artifacts=artifacts_dir)
    wrt24 = _rule(result, "WRT-24")
    assert wrt24.status == "fail"
    assert "extend_existing" in wrt24.reason


def test_anaphora_at_section_start_blocks_via_the_core_rule(pack, artifacts_dir):
    """WRT-32 blocks because the core says so; the pack only supplies the word list."""
    draft = _mutate(
        CLEAN_DRAFT,
        "Оголошена ставка описує лише тіло боргу.",
        "Це описує лише тіло боргу.",
    )
    result = _score(draft=draft, pack=pack, artifacts=artifacts_dir)
    wrt32 = _rule(result, "WRT-32")
    assert wrt32.status == "fail" and wrt32.severity == "BLOCK"
    assert "WRT-32" in result.blocked_by


def test_same_model_family_fails_the_judge_separation(pack, artifacts_dir):
    result = _score(pack=pack, artifacts=artifacts_dir, writer_model="claude-opus-5", judge_model="claude-sonnet-5")
    assert _rule(result, "WRT-61").status == "fail"
    result = _score(pack=pack, artifacts=artifacts_dir, writer_model="claude-opus-5", judge_model="gemini-2.5-pro")
    assert _rule(result, "WRT-61").status == "pass"


# ---------------------------------------------------------------------------
# Language pack behaviour
# ---------------------------------------------------------------------------


def test_deterministic_entry_keeps_block(pack, artifacts_dir):
    """Russian-only letters in Ukrainian text are a fact about the alphabet, not a style opinion."""
    draft = _mutate(CLEAN_DRAFT, "ставка НБУ", "ставка НБУ ы")
    result = _score(draft=draft, pack=pack, artifacts=artifacts_dir)
    rule = _rule(result, "LANG-UK-10")
    assert rule.status == "fail"
    assert rule.severity == "BLOCK"
    assert "LANG-UK-10" in result.blocked_by


def test_malformed_pack_is_capped_at_warn_and_reported(tmp_path: Path, artifacts_dir):
    """A pack cannot promote a stylistic entry to BLOCK by declaring a ceiling.

    The cap is applied in code rather than read from the pack, because a pack that declares its
    severity honestly today is not a guarantee about the pack somebody contributes next month.
    """
    path = tmp_path / "lang" / "uk.md"
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(MALFORMED_PACK, encoding="utf-8")
    bad_pack = ds.parse_language_pack(path)

    assert any("non-deterministic" in d for d in bad_pack.defects), bad_pack.defects

    draft = _mutate(CLEAN_DRAFT, "Кредитна історія лишається", "Надійний партнер поруч. Кредитна історія лишається")
    result = ds.score(draft, _brief(), _packet(), bad_pack, _thresholds(), artifacts_dir=artifacts_dir)
    rule = _rule(result, "LANG-UK-10")
    assert rule.status == "fail"
    assert rule.severity == "WARN", "a hypothesis entry must never hold the gate"
    assert "LANG-UK-10" not in result.blocked_by
    assert _rule(result, "WRT-06").status == "fail"


def test_density_entry_is_not_judged_by_presence(pack, artifacts_dir):
    """Banning an ordinary word by presence bans ordinary language. One occurrence must pass."""
    draft = _mutate(CLEAN_DRAFT, "Оголошена ставка описує", "Практика демонструє це. Оголошена ставка описує")
    result = _score(draft=draft, pack=pack, artifacts=artifacts_dir)
    hedge = _rule(result, "LANG-UK-02")
    assert hedge.status == "pass", hedge.evidence


def test_density_entry_fires_above_the_threshold(pack, artifacts_dir):
    """Repeat it enough and frequency, not presence, is what trips the rule."""
    filler = " ".join(["Практика демонструє це."] * 12)
    draft = CLEAN_DRAFT + "\n\n" + filler
    result = _score(draft=draft, pack=pack, artifacts=artifacts_dir)
    hedge = _rule(result, "LANG-UK-02")
    assert hedge.status == "fail"
    assert any("per 1000 words" in e for e in hedge.evidence)


def test_short_draft_never_lets_density_degenerate_into_presence(pack, artifacts_dir):
    """A single occurrence in a 120-word draft scores 8.3 per 1000 and would trip a threshold of 5.

    That converts a density rule into the presence rule it exists to prevent, which the pack
    contract calls its single most important safeguard. Below the minimum length the number is
    reported and nothing is raised.
    """
    result = _score(draft=SHORT_DRAFT, pack=pack, artifacts=artifacts_dir)
    hedge = _rule(result, "LANG-UK-02")
    assert hedge.status != "fail"
    assert any("not evidence" in e for e in hedge.evidence), hedge.evidence


def test_density_guard_threshold_is_configurable(pack, artifacts_dir):
    """The guard is a threshold like any other, and a project may calibrate it down."""
    local = Thresholds(ds.DOCTRINE_DEFAULTS, {"lang.density_min_words": 5})
    result = ds.score(SHORT_DRAFT, _brief(), _packet(), pack, local, artifacts_dir=artifacts_dir)
    hedge = _rule(result, "LANG-UK-02")
    assert hedge.status == "fail"


def test_phrase_entry_is_judged_by_presence(pack, artifacts_dir):
    draft = _mutate(CLEAN_DRAFT, "Кредитна історія лишається", "Важливо зазначити, що кредитна історія лишається")
    result = _score(draft=draft, pack=pack, artifacts=artifacts_dir)
    assert _rule(result, "LANG-UK-02").status == "fail"


def test_uncalibrated_density_reports_info_not_warn(pack, artifacts_dir):
    """A threshold nobody has measured produces a number, not a verdict.

    Warning against an unmeasured threshold manufactures false confidence, which is exactly the
    risk the doctrine records for this locale.
    """
    draft = CLEAN_DRAFT + "\n\n" + " ".join(["Система забезпечує стабільність."] * 6)
    result = _score(draft=draft, pack=pack, artifacts=artifacts_dir)
    rule = _rule(result, "LANG-UK-06")
    assert rule.severity == "INFO"
    assert rule.status == "not_applicable"
    assert any("no threshold set" in e for e in rule.evidence)


def test_prescribed_set_is_never_scored_as_a_violation(pack, artifacts_dir):
    result = _score(pack=pack, artifacts=artifacts_dir)
    assert all(r.id != "LANG-UK-07" for r in result.rules)


def test_missing_pack_fails_loudly(tmp_path: Path):
    with pytest.raises(KilnError) as exc:
        ds.parse_language_pack(tmp_path / "lang" / "sv.md")
    assert "forbidden" in str(exc.value).lower()


def test_locale_selects_the_pack_not_the_doctrine_language(tmp_path: Path):
    doctrine = tmp_path / "doctrine"
    (doctrine / "lang").mkdir(parents=True)
    (doctrine / "lang" / "uk.md").write_text(MINIMAL_PACK, encoding="utf-8")
    resolved = ds.resolve_pack_path(_brief(), doctrine, None)
    assert resolved.name == "uk.md"

    with pytest.raises(KilnError):
        ds.resolve_pack_path({"locale": ""}, doctrine, None)


def test_pcre_property_classes_are_translated_not_dropped():
    compiled, err = ds._compile_pack_pattern(r"\p{L}+(ання|ення)")
    assert err == ""
    assert compiled is not None
    assert compiled.search("проведення")


def test_uncompilable_pattern_becomes_a_visible_defect(tmp_path: Path):
    broken = MINIMAL_PACK.replace('match: "важливо зазначити"', 'match: "важливо ((зазначити"')
    path = tmp_path / "lang" / "uk.md"
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(broken, encoding="utf-8")
    bad = ds.parse_language_pack(path)
    assert any("uncompilable" in d for d in bad.defects)


# ---------------------------------------------------------------------------
# Observe mode and determinism
# ---------------------------------------------------------------------------


def test_observe_downgrades_blocks_and_still_reports_them(pack):
    packet = _packet()
    for claim in packet["claims"]:
        claim["provenance"] = "third_party"
        claim.pop("artifact_id", None)

    hard = _score(pack=pack, packet=packet, artifacts=None)
    assert hard.verdict == "BLOCK"

    soft = _score(pack=pack, packet=packet, artifacts=None, observe=True)
    assert soft.verdict != "BLOCK"
    assert soft.blocked_by == []
    wrt20 = _rule(soft, "WRT-20")
    assert wrt20.status == "fail", "observe hides the block, never the finding"
    assert wrt20.severity == "WARN"
    assert "observe" in wrt20.reason


def test_scoring_is_byte_identical_across_runs(pack, artifacts_dir):
    """Without this, a change in our implementation is indistinguishable from a change in the SERP."""
    a = json.dumps(_score(pack=pack, artifacts=artifacts_dir).as_record(), sort_keys=True, ensure_ascii=False)
    b = json.dumps(_score(pack=pack, artifacts=artifacts_dir).as_record(), sort_keys=True, ensure_ascii=False)
    assert a == b


def test_findings_carry_the_thresholds_that_produced_them(pack, artifacts_dir):
    """A stored finding without its thresholds cannot be re-read after a recalibration."""
    result = _score(pack=pack, artifacts=artifacts_dir)
    wrt26 = _rule(result, "WRT-26")
    keys = {t["key"] for t in wrt26.thresholds_used}
    assert "wrt26.words_per_claim_max" in keys
    assert all(t["source"] in {"doctrine", "local", "fallback"} for t in wrt26.thresholds_used)


def test_local_threshold_overrides_doctrine_and_says_so(pack, artifacts_dir):
    local = Thresholds(ds.DOCTRINE_DEFAULTS, {"wrt26.words_per_claim_max": 10})
    result = ds.score(CLEAN_DRAFT, _brief(), _packet(), pack, local, artifacts_dir=artifacts_dir)
    wrt26 = _rule(result, "WRT-26")
    assert wrt26.status == "fail"
    entry = next(t for t in wrt26.thresholds_used if t["key"] == "wrt26.words_per_claim_max")
    assert entry["source"] == "local"


# ---------------------------------------------------------------------------
# Draft parsing
# ---------------------------------------------------------------------------


def test_tables_and_code_do_not_become_sentences():
    draft = ds.parse_draft(CLEAN_DRAFT, "draft.md")
    assert draft.has_table
    assert not any("---" in s for s in draft.sentences)
    assert all("|" not in s for s in draft.sentences)


def test_heading_level_skip_is_detected(pack, artifacts_dir):
    draft = _mutate(CLEAN_DRAFT, "## Що показала перевірка відмов", "#### Що показала перевірка відмов")
    result = _score(draft=draft, pack=pack, artifacts=artifacts_dir)
    assert _rule(result, "WRT-35").status == "fail"


def test_entity_coverage_reads_in_both_directions(pack, artifacts_dir):
    """Below the floor the topic is uncovered; above the ceiling the top has been paraphrased."""
    result = _score(pack=pack, artifacts=artifacts_dir)
    wrt22 = _rule(result, "WRT-22")
    assert wrt22.status in {"pass", "fail"}
    assert wrt22.threshold is not None


def test_ngram_overlap_needs_a_corpus_and_says_so(pack, artifacts_dir):
    result = _score(pack=pack, artifacts=artifacts_dir)
    wrt23 = _rule(result, "WRT-23")
    assert wrt23.status == "requires_input"
    assert "WRT-23" in result.unresolved


def test_ngram_overlap_catches_a_copied_passage(pack, artifacts_dir):
    passage = (
        "Кредитна історія лишається головним чинником хоча банки зважають і на офіційний дохід "
        "позичальника а також на його поточні зобов'язання перед іншими фінансовими установами"
    )
    draft = "# Заголовок\n\n" + passage + "\n\n## Розділ\n\n" + passage
    result = ds.score(
        draft,
        _brief(),
        _packet(),
        pack,
        _thresholds(),
        artifacts_dir=artifacts_dir,
        top_docs={"competitor.md": passage},
    )
    wrt23 = _rule(result, "WRT-23")
    assert wrt23.status == "fail"
    assert wrt23.value > 0.03


def test_shipped_uk_pack_blocks_a_homoglyph_end_to_end(artifacts_dir):
    """The named check reaches the verdict, not just the loader.

    Wiring is the half that gets missed: a check can be implemented, registered, and still never
    consulted. This asserts the draft is actually blocked.
    """
    real = Path(__file__).resolve().parents[2] / "doctrine" / "lang" / "uk.md"
    pack = ds.parse_language_pack(real)
    draft = _mutate(CLEAN_DRAFT, "ставка", "cтавка")  # Latin c
    result = ds.score(draft, _brief(), _packet(), pack, _thresholds(), artifacts_dir=artifacts_dir)
    rule = _rule(result, "LANG-UK-10")
    assert rule.status == "fail"
    assert rule.severity == "BLOCK"
    assert "LANG-UK-10" in result.blocked_by


def test_pack_contract_defects_are_reported_as_wrt_06(artifacts_dir, tmp_path: Path):
    """WRT-06: a malformed pack is our defect, so it warns and does not block the draft."""
    text = MINIMAL_PACK.replace("  rule_id: LANG-UK-02\n", "", 1)
    path = tmp_path / "lang" / "uk.md"
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text, encoding="utf-8")
    bad = ds.parse_language_pack(path)

    result = ds.score(CLEAN_DRAFT, _brief(), _packet(), bad, _thresholds(), artifacts_dir=artifacts_dir)
    rule = _rule(result, "WRT-06")
    assert rule.status == "fail"
    assert rule.severity == "WARN"
    assert "WRT-06" not in result.blocked_by


def test_clean_pack_records_wrt_06_as_passing(pack, artifacts_dir):
    """A pack that loaded nothing must not look like a pack with nothing to say."""
    result = _score(draft=CLEAN_DRAFT, pack=pack, artifacts=artifacts_dir)
    assert _rule(result, "WRT-06").status == "pass"
