"""Every pattern in `doctrine/lang/ru.md` fires on a positive case and stays quiet on a negative one.

`lang/_template.md` §2 makes this mandatory before a pattern may be merged, and `CONTRIBUTING.md`
repeats it, because the alternative has already shipped: the Ukrainian homoglyph guard
`\\b(?=\\p{Cyrillic})(?=\\p{Latin})\\S+\\b` compiled, reviewed cleanly, and had an empty match set
for as long as it existed. A dead rule reports success forever and nobody investigates a check that
never complains.

The negative case is not decoration. Constructing one for the «Данный» opener is what surfaced the
fact that the plural «данные» is the noun *data* far more often than an adjective, and that including
it would have fired on «Данные обновлены 07.08.2026» — correct writing, several times per page on the
target corpus. That entry was narrowed before the pack was committed.

Fixtures are (positive, negative) per entry. Patterns compile with IGNORECASE and MULTILINE
(`draft_score._compile_pack_pattern`), so an anchored `^` matches at the start of any line and a
negative must avoid the construction line-initially, not merely sentence-initially.
"""

from __future__ import annotations

import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

import draft_score as ds  # noqa: E402

RU_PACK = Path(__file__).resolve().parents[2] / "doctrine" / "lang" / "ru.md"

#: (set key, entry term) -> (must match, must not match)
CASES: dict[tuple[str, str], tuple[str, str]] = {
    # -- 3.1 anaphora_openers: anchored, section-initial only ---------------
    ("anaphora_openers", "Это"): (
        "Это правило действует до конца года.",
        "Мы считаем, что это правило разумно.",
    ),
    ("anaphora_openers", "Этот / Эта / Эти"): (
        "Этот банк закрыл отделения в 2024 году.",
        "Это решение банк принял в 2024 году.",
    ),
    ("anaphora_openers", "Такой подход"): (
        "Такой подход экономит заёмщику неделю.",
        "Так работает скоринг в большинстве банков.",
    ),
    ("anaphora_openers", "Он / Она / Они"): (
        "Она выдаёт займы без справки о доходах.",
        "Онлайн-заявка занимает пять минут.",
    ),
    ("anaphora_openers", "Данный"): (
        "Данный продукт снят с продажи.",
        "Данные обновлены 07.08.2026.",
    ),
    ("anaphora_openers", "Вышеуказанное / Вышеупомянутое"): (
        "Вышеуказанные условия действуют до 31 декабря.",
        "Указанные в договоре условия действуют до 31 декабря.",
    ),
    ("anaphora_openers", "Как отмечалось выше"): (
        "Как отмечалось выше, ставка плавающая.",
        "Как оформить кредит онлайн за пятнадцать минут.",
    ),
    ("anaphora_openers", "Эти факторы"): (
        "Эти факторы влияют на итоговую ставку.",
        "Ставку определяют три фактора.",
    ),
    ("anaphora_openers", "Кроме того"): (
        "Кроме того, банк берёт комиссию за досрочное погашение.",
        "Комиссия не берётся ни в одном случае, кроме того, что описан ниже.",
    ),
    ("anaphora_openers", "Однако"): (
        "Однако ставка выросла на два пункта.",
        "Ставка выросла на два пункта, однако осталась ниже рыночной.",
    ),
    ("anaphora_openers", "Именно поэтому"): (
        "Именно поэтому мы пересчитали ставку вручную.",
        "Поэтому мы пересчитали ставку вручную.",
    ),
    ("anaphora_openers", "Несмотря на"): (
        "Несмотря на снижение учётной ставки, кредиты не подешевели.",
        "Кредиты не подешевели, несмотря на снижение учётной ставки.",
    ),
    # -- 3.2 hedge_phrases --------------------------------------------------
    ("hedge_phrases", "важно отметить"): (
        "Важно отметить, что комиссия не входит в ставку.",
        "Комиссия не входит в ставку.",
    ),
    ("hedge_phrases", "стоит отметить"): (
        "Стоит обратить внимание на срок рассмотрения заявки.",
        "Срок рассмотрения заявки — два рабочих дня.",
    ),
    ("hedge_phrases", "следует отметить"): (
        "Следует иметь в виду, что ставка плавающая.",
        "Ставка плавающая и пересматривается раз в квартал.",
    ),
    ("hedge_phrases", "в этой статье мы рассмотрим"): (
        "В этой статье мы рассмотрим условия десяти банков.",
        "Ниже — условия десяти банков по состоянию на 07.08.2026.",
    ),
    ("hedge_phrases", "давайте разберёмся"): (
        "Давайте разберёмся, как считается эффективная ставка.",
        "Эффективная ставка считается по формуле из постановления НБУ.",
    ),
    ("hedge_phrases", "значения могут варьироваться"): (
        "Условия могут варьироваться в зависимости от банка.",
        "Условия отличаются у восьми банков из семнадцати — таблица ниже.",
    ),
    ("hedge_phrases", "на основе имеющейся информации"): (
        "На основании доступной информации ставка составляет около 20 %.",
        "По данным НБУ на 07.08.2026 учётная ставка составляет 15,5 %.",
    ),
    ("hedge_phrases", "хотя конкретные детали ограничены"): (
        "Хотя конкретные детали ограничены, условия выглядят стандартными.",
        "Банк раскрывает условия полностью: комиссия 1 %, срок до 24 месяцев.",
    ),
    ("hedge_phrases", "по состоянию на момент обновления"): (
        "По состоянию на момент обновления моей базы данных ставка была ниже.",
        "По состоянию на 07.08.2026 ставка составляет 15,5 %.",
    ),
    ("hedge_phrases", "как языковая модель"): (
        "Как большая языковая модель, я не даю финансовых советов.",
        "Мы не даём индивидуальных финансовых советов.",
    ),
    ("hedge_phrases", "надеюсь, это помогло"): (
        "Надеюсь, это помогло! Сообщите мне, если нужны детали.",
        "Если условия изменятся, мы обновим таблицу.",
    ),
    ("hedge_phrases", "рекомендуем проконсультироваться со специалистом"): (
        "Рекомендуем проконсультироваться со специалистом перед подписанием.",
        "Перед подписанием прочитайте пункт 4.2 договора.",
    ),
    ("hedge_phrases", "это лишь общая информация"): (
        "Это лишь общая информация, а не индивидуальная рекомендация.",
        "Расчёт сделан для суммы 50 000 грн на 12 месяцев.",
    ),
    # -- 3.3 closing_formulas ----------------------------------------------
    ("closing_formulas", "В заключение"): (
        "В заключение отметим главное.",
        "Главное в двух строках: комиссия 1 %, срок до 24 месяцев.",
    ),
    ("closing_formulas", "Подводя итог"): (
        "Подводя итог, отметим три вещи.",
        "Три вещи, которые стоит проверить перед подписанием.",
    ),
    ("closing_formulas", "Таким образом, можно сделать вывод"): (
        "Таким образом, можно сделать вывод о снижении ставок.",
        "Таким образом банк считает эффективную ставку.",
    ),
    ("closing_formulas", "Вкратце"): (
        "Вкратце: ставка выросла, комиссия осталась.",
        "Коротко о главном: ставка выросла, комиссия осталась.",
    ),
    ("closing_formulas", "В целом"): (
        "В целом рынок вырос на 4 %.",
        "Рынок вырос на 4 % за квартал.",
    ),
    ("closing_formulas", "Перспективы на будущее"): (
        "Перспективы на будущее выглядят умеренно позитивно.",
        "Прогноз НБУ на 2027 год опубликован 12 июля 2026 года.",
    ),
    ("closing_formulas", "heading «Заключение» / «Вывод»"): (
        "## Заключение",
        "## Что проверить перед подписанием",
    ),
    # -- 3.4 promo_lexicon --------------------------------------------------
    ("promo_lexicon", "играет ключевую роль"): (
        "Кредитная история играет ключевую роль при скоринге.",
        "Кредитная история влияет на скоринг: без неё отказ в 4 случаях из 10.",
    ),
    ("promo_lexicon", "подчёркивает его важность"): (
        "Это подчёркивает важность страхования залога.",
        "Страхование залога обязательно по пункту 5.1 договора.",
    ),
    ("promo_lexicon", "служит напоминанием"): (
        "Случай 2024 года служит напоминанием о рисках.",
        "В 2024 году два банка потеряли лицензию — решение НБУ № 112.",
    ),
    ("promo_lexicon", "неизгладимый след"): (
        "Реформа оставила неизгладимый след в банковской системе.",
        "После реформы число банков сократилось с 96 до 63.",
    ),
    ("promo_lexicon", "может похвастаться"): (
        "Банк может похвастаться сетью из 200 отделений.",
        "У банка 200 отделений в 24 областях.",
    ),
    ("promo_lexicon", "расположенный в самом сердце"): (
        "Отделение расположено в самом сердце города.",
        "Отделение работает по адресу: Крещатик, 22.",
    ),
    ("promo_lexicon", "богатый"): (
        "Богатый выбор программ кредитования.",
        "Семнадцать программ кредитования, таблица ниже.",
    ),
    ("promo_lexicon", "яркий"): (
        "Яркий пример — программа рефинансирования.",
        "Пример: программа рефинансирования от 12 % годовых.",
    ),
    ("promo_lexicon", "разнообразный"): (
        "Разнообразные условия для разных категорий клиентов.",
        "Условия отличаются для трёх категорий клиентов.",
    ),
    ("promo_lexicon", "уникальный"): (
        "Уникальное предложение на рынке.",
        "Единственное предложение с нулевой комиссией среди 17 проверенных.",
    ),
    ("promo_lexicon", "инновационный"): (
        "Инновационный подход к скорингу.",
        "Скоринг учитывает историю платежей за 24 месяца.",
    ),
    ("promo_lexicon", "широкий спектр"): (
        "Широкий спектр программ для малого бизнеса.",
        "Восемь программ для малого бизнеса.",
    ),
    ("promo_lexicon", "Это не просто X, это Y"): (
        "Это не просто кредит, это инструмент развития.",
        "Это кредит на развитие бизнеса под 14 % годовых.",
    ),
    # -- 3.5 vague_attribution ---------------------------------------------
    ("vague_attribution", "по данным экспертов"): (
        "По данным экспертов, ставки снизятся до конца года.",
        "По данным НБУ от 07.08.2026, учётная ставка — 15,5 %.",
    ),
    ("vague_attribution", "эксперты считают"): (
        "Эксперты считают, что рынок перегрет.",
        "Аналитик НБУ Иван Петров заявил 12 июля, что рынок перегрет.",
    ),
    ("vague_attribution", "как показывают исследования"): (
        "Как показывают исследования, заёмщики не читают договор.",
        "Опрос НБУ 2025 года: 62 % заёмщиков не читают договор целиком.",
    ),
    ("vague_attribution", "согласно статистике"): (
        "Согласно статистике, просрочка выросла.",
        "Согласно данным НБУ, просрочка выросла до 8,1 %.",
    ),
    ("vague_attribution", "многие считают"): (
        "Многие считают ипотеку недоступной.",
        "По опросу 2026 года ипотеку считают недоступной 71 % респондентов.",
    ),
    ("vague_attribution", "принято считать"): (
        "Принято считать, что рефинансирование всегда выгодно.",
        "Рефинансирование выгодно, если разница ставок превышает 3 пункта.",
    ),
    ("vague_attribution", "по последним данным"): (
        "По последним данным, число заявок выросло.",
        "По данным НБУ за июль 2026 года число заявок выросло на 12 %.",
    ),
    # -- 3.6 generational_stopwords ----------------------------------------
    ("generational_stopwords", "обеспечивает"): (
        "Страховка обеспечивает защиту залога.",
        "Страховка покрывает залог на 100 % оценочной стоимости.",
    ),
    ("generational_stopwords", "подчёркивает"): (
        "Это подчёркивает надёжность банка.",
        "Банк работает с 1991 года и не нарушал нормативы НБУ.",
    ),
    ("generational_stopwords", "демонстрирует"): (
        "Отчёт демонстрирует рост портфеля.",
        "Портфель вырос с 4,1 до 5,3 млрд грн.",
    ),
    ("generational_stopwords", "отражает"): (
        "Ставка отражает стоимость фондирования.",
        "Ставка складывается из учётной ставки НБУ и маржи банка.",
    ),
    ("generational_stopwords", "выделяет"): (
        "Банк выделяет три категории заёмщиков.",
        "У банка три категории заёмщиков: A, B и C.",
    ),
    ("generational_stopwords", "влияет"): (
        "Кредитная история влияет на решение банка.",
        "При просрочке свыше 30 дней банк отказывает в 8 случаях из 10.",
    ),
    ("generational_stopwords", "ключевой момент"): (
        "Ключевой момент — дата первого платежа.",
        "Первый платёж — через 30 дней после подписания.",
    ),
    ("generational_stopwords", "важный аспект"): (
        "Важный аспект — стоимость страховки.",
        "Страховка стоит 0,4 % от суммы в год.",
    ),
    ("generational_stopwords", "в современном мире"): (
        "В современном мире кредит стал обыденностью.",
        "В 2026 году кредит есть у 41 % взрослых украинцев.",
    ),
    ("generational_stopwords", "стремительно развивается"): (
        "Рынок стремительно развивается.",
        "Рынок вырос на 12 % за год.",
    ),
    ("generational_stopwords", "сталкиваются с рядом проблем"): (
        "Заёмщики сталкиваются с рядом проблем при рефинансировании.",
        "При рефинансировании банк требует три документа.",
    ),
    ("generational_stopwords", "в целях"): (
        "В целях снижения риска банк требует поручителя.",
        "Чтобы снизить риск, банк требует поручителя.",
    ),
    # -- 3.7 prescribed_phrases (not forbidden; the pattern is the phrase) --
    ("prescribed_phrases", "Х — это У"): (
        "Х — это У",
        "Кредит является заёмным продуктом банка.",
    ),
    ("prescribed_phrases", "но"): (
        "Ставка ниже, но комиссия выше.",
        "Ставка ниже, а комиссия выше.",
    ),
    ("prescribed_phrases", "поэтому"): (
        "Ставка плавающая, поэтому платёж меняется.",
        "Ставка плавающая, в связи с чем платёж меняется.",
    ),
    ("prescribed_phrases", "мы проверили"): (
        "Мы проверили 17 предложений вручную.",
        "Было проверено 17 предложений.",
    ),
    ("prescribed_phrases", "по состоянию на"): (
        "Ставки по состоянию на 07.08.2026.",
        "Актуальные ставки.",
    ),
    # -- 3.8 bureaucratic_constructions -------------------------------------
    ("bureaucratic_constructions", "является"): (
        "Кредит является продуктом банка.",
        "Кредит — это продукт банка.",
    ),
    ("bureaucratic_constructions", "осуществляется"): (
        "Погашение осуществляется ежемесячно.",
        "Заёмщик платит раз в месяц.",
    ),
    ("bureaucratic_constructions", "производится"): (
        "Списание производится автоматически.",
        "Банк списывает платёж автоматически.",
    ),
    ("bureaucratic_constructions", "в рамках"): (
        "В рамках программы доступно до 500 000 грн.",
        "По программе доступно до 500 000 грн.",
    ),
    ("bureaucratic_constructions", "на сегодняшний день"): (
        "На сегодняшний день ставка составляет 15,5 %.",
        "На 07.08.2026 ставка составляет 15,5 %.",
    ),
    ("bureaucratic_constructions", "в случае наличия"): (
        "В случае наличия поручителя ставка ниже.",
        "Если есть поручитель, ставка ниже.",
    ),
    ("bureaucratic_constructions", "вышеуказанный"): (
        "Вышеперечисленные документы подаются онлайн.",
        "Эти три документа подаются онлайн.",
    ),
    ("bureaucratic_constructions", "данный"): (
        "Данный продукт снят с продажи.",
        "Этот продукт снят с продажи.",
    ),
    ("bureaucratic_constructions", "verbal noun chain"): (
        "Осуществление погашения задолженности возможно онлайн.",
        "Долг можно погасить онлайн.",
    ),
    # -- 3.9 technical_defects_ru: deterministic, the only blocking set -----
    ("technical_defects_ru", "letters absent from the Russian alphabet"): (
        "Кредит онлайн на картку від українських банків",
        "Кредит онлайн на карту от украинских банков",
    ),
    ("technical_defects_ru", "zero-width and narrow no-break characters"): (
        "сло​во",
        "слово без скрытых символов",
    ),
    ("technical_defects_ru", "mojibake from cp1251/utf-8 confusion"): (
        "кредит".encode("utf-8").decode("latin-1"),
        "кредит онлайн на карту",
    ),
    ("technical_defects_ru", "wrong apostrophe character"): (
        "О`Коннор получил кредит",
        "О’Коннор получил кредит",
    ),
    ("technical_defects_ru", "straight double quotes in body prose"): (
        'Банк "Аваль" сменил название.',
        "Банк «Аваль» сменил название.",
    ),
}


@pytest.fixture(scope="module")
def pack() -> ds.LanguagePack:
    return ds.parse_language_pack(RU_PACK)


def _entry(pack: ds.LanguagePack, set_key: str, term: str) -> ds.PackEntry:
    return next(e for e in pack.sets[set_key].entries if e.term == term)


def test_pack_loads_without_defects(pack: ds.LanguagePack) -> None:
    assert pack.defects == [], pack.defects
    assert pack.code == "ru"


def test_every_entry_is_runnable(pack: ds.LanguagePack) -> None:
    """A pattern that fails to compile drops a rule silently; the loader must say so instead."""
    dead = [
        (key, e.term, e.compile_error)
        for key, s in pack.sets.items()
        for e in s.entries
        if not e.runnable
    ]
    assert dead == []


def test_every_pattern_has_a_case(pack: ds.LanguagePack) -> None:
    """No entry may be merged without a demonstration that it fires.

    This is the test that makes the promise in `lang/ru.md` §12 enforceable rather than a claim in
    prose. Adding an entry without a fixture fails here, which is the only way the requirement
    survives contact with a hurried commit.
    """
    missing = [
        (key, e.term)
        for key, s in pack.sets.items()
        for e in s.entries
        if e.compiled is not None and (key, e.term) not in CASES
    ]
    assert missing == [], f"entries with no positive/negative fixture: {missing}"


def test_no_orphan_cases(pack: ds.LanguagePack) -> None:
    """A fixture naming an entry that no longer exists is a stale test pretending to cover one."""
    live = {(key, e.term) for key, s in pack.sets.items() for e in s.entries}
    orphans = sorted(k for k in CASES if k not in live)
    assert orphans == [], f"fixtures for entries that do not exist: {orphans}"


@pytest.mark.parametrize("key", sorted(CASES), ids=lambda k: f"{k[0]}::{k[1]}")
def test_pattern_fires_on_positive_and_is_quiet_on_negative(
    pack: ds.LanguagePack, key: tuple[str, str]
) -> None:
    positive, negative = CASES[key]
    entry = _entry(pack, *key)
    assert entry.compiled is not None, f"{key} carries no pattern"
    assert entry.compiled.search(positive), f"{key}: must fire on {positive!r}"
    assert not entry.compiled.search(negative), f"{key}: must stay quiet on {negative!r}"


def test_homoglyph_entry_is_a_named_check_not_a_pattern(pack: ds.LanguagePack) -> None:
    """The one entry that cannot be a regex, for the reason the Ukrainian pack proved."""
    entry = _entry(pack, "technical_defects_ru", "Latin homoglyphs inside Cyrillic tokens")
    assert entry.named_check == "mixed_script_token"
    assert entry.compiled is None
    assert entry.runnable
    assert ds.check_mixed_script_token("крeдит"), "Latin e inside a Cyrillic word"
    assert not ds.check_mixed_script_token("кредит онлайн на карту")
    assert not ds.check_mixed_script_token("SMS-уведомление"), "legitimate compound"


def test_ukrainian_letters_rule_is_deterministic_and_may_block(pack: ds.LanguagePack) -> None:
    """The character-inventory rule is the only kind of cross-locale rule this pack allows.

    `lang/uk.md` §9-2 forbids a stylistic «ukrainianisms» set as the mirror of the russism set.
    A letter that is not in the Russian alphabet is a different claim: orthographic, not
    evaluative, and therefore the one status permitted to carry BLOCK.
    """
    s = pack.sets["technical_defects_ru"]
    entry = _entry(pack, "technical_defects_ru", "letters absent from the Russian alphabet")
    assert s.declared_severity == "BLOCK"
    assert s.default_status == "deterministic"
    assert ds.cap_pack_severity(s, entry) == "BLOCK"


def test_typographic_entries_downgrade_themselves_below_the_set_ceiling(
    pack: ds.LanguagePack,
) -> None:
    """Two entries sit in a BLOCK set and are not orthographic facts about Russian.

    A straight quotation mark is a CMS artifact and a backtick apostrophe matters only in
    transliterated names. Both declare `severity: WARN` on the entry, and the point of asserting
    it here is that the machine reads the field rather than the prose beside it.
    """
    for term in ("wrong apostrophe character", "straight double quotes in body prose"):
        entry = _entry(pack, "technical_defects_ru", term)
        assert ds.cap_pack_severity(pack.sets["technical_defects_ru"], entry) == "WARN", term


def test_no_stylistic_set_can_block(pack: ds.LanguagePack) -> None:
    """P3: a language pack must not become an in-house detector holding the publication gate."""
    for key, s in pack.sets.items():
        if key == "technical_defects_ru":
            continue
        for entry in s.entries:
            assert ds.cap_pack_severity(s, entry) != "BLOCK", f"{key}::{entry.term}"


def test_prescribed_and_forbidden_do_not_intersect(pack: ds.LanguagePack) -> None:
    """The invariant that exists because two documents once prescribed and forbade one phrase.

    Checked here as well as in `rules_lint.py` so that a pack edit fails in the pack's own test
    run rather than only in the doctrine build.
    """
    prescribed = {e.term.casefold().strip() for e in pack.sets["prescribed_phrases"].entries}
    for key, s in pack.sets.items():
        if key == "prescribed_phrases" or not s.forbidden:
            continue
        clash = prescribed & {e.term.casefold().strip() for e in s.entries}
        assert not clash, f"{key} forbids a prescribed phrase: {clash}"


def test_dash_construction_is_prescribed_so_a_dash_ban_cannot_be_added(
    pack: ds.LanguagePack,
) -> None:
    """RU-01 is enforced by the intersection invariant, not by prose.

    Listing «Х — это У» as prescribed means any future entry forbidding the copular dash collides
    with the invariant and fails the build before it reaches a corpus. The recorded cost of
    getting this wrong is 349 grammatically correct dashes converted to commas.
    """
    prescribed = {e.term for e in pack.sets["prescribed_phrases"].entries}
    assert "Х — это У" in prescribed


def test_source_has_no_literal_invisible_characters() -> None:
    """The set that detects encoding damage must not be disabled by encoding damage.

    Written as its own test rather than relying on the shared one, because this pack was drafted
    with the literal characters in place and they were replaced with `\\uXXXX` escapes only after
    a byte-level check caught them.
    """
    raw = RU_PACK.read_text(encoding="utf-8")
    bad = sorted(
        {
            hex(ord(c))
            for c in raw
            if (ord(c) < 32 and c not in "\n\t")
            or 0x7F <= ord(c) <= 0x9F
            or ord(c) in (0x200B, 0x200C, 0x200D, 0xFEFF, 0x00AD, 0x202F)
        }
    )
    assert not bad, f"ru.md carries literal invisible or control characters: {bad}"
