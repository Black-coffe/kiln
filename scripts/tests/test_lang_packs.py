"""Tests for the language pack contract and the defects fixed on 2026-08-07.

Four defects shipped in `doctrine/lang/uk.md`, and every one of them failed silently. That is the
property worth testing, not the individual bugs:

1. All ten sets used `entries:`/`term:` where the contract says `items:`/`phrase:`. The YAML parsed,
   the file read as complete, and a consumer following the contract received an empty pack. The
   pilot locale had no lexical rules at all while appearing fully specified.
2. No `normalization` block, so the prescribed-versus-forbidden invariant was not false but
   *undefined* — and an undefined check is indistinguishable from a passing one.
3. Two entries in the only BLOCK-capable set carried literal invisible and control characters, so
   the block was not valid YAML and the set never loaded. The set that detects encoding damage was
   disabled by encoding damage.
4. The homoglyph pattern `\\b(?=\\p{Cyrillic})(?=\\p{Latin})\\S+\\b` required a single character to
   belong to two scripts at once. It compiled, it reviewed cleanly, and its match set was empty.

Each test below pins one of those open, plus the mechanisms added to stop them recurring.
"""

from __future__ import annotations

import re
import sys
from pathlib import Path

import pytest
import yaml

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

import draft_score as ds  # noqa: E402

DOCTRINE = Path(__file__).resolve().parents[2] / "doctrine"
UK_PACK = DOCTRINE / "lang" / "uk.md"
EN_PACK = DOCTRINE / "lang" / "en.md"
TEMPLATE = DOCTRINE / "lang" / "_template.md"

SHIPPED_PACKS = [UK_PACK, EN_PACK]


def _pack_meta(path: Path) -> dict:
    """The `lang:` metadata block, read straight from the file."""
    raw = path.read_text(encoding="utf-8")
    for block in re.findall(r"```ya?ml\n(.*?)```", raw, re.S):
        try:
            data = yaml.safe_load(block)
        except yaml.YAMLError:
            continue
        if isinstance(data, dict) and isinstance(data.get("lang"), dict):
            return data["lang"]
    return {}


# ---------------------------------------------------------------------------
# Defect 1: contract key names
# ---------------------------------------------------------------------------


@pytest.mark.parametrize("path", SHIPPED_PACKS, ids=lambda p: p.stem)
def test_shipped_pack_loads_without_defects(path: Path) -> None:
    pack = ds.parse_language_pack(path)
    assert pack.defects == [], pack.defects


def test_uk_pack_exposes_its_entries_under_the_contract_keys() -> None:
    """Read through `items:`/`phrase:` only. An alias would hide the original failure again."""
    raw = UK_PACK.read_text(encoding="utf-8")
    sets: dict[str, dict] = {}
    for block in re.findall(r"```ya?ml\n(.*?)```", raw, re.S):
        data = yaml.safe_load(block)
        if not isinstance(data, dict):
            continue
        for key, value in data.items():
            if isinstance(value, dict) and "items" in value:
                sets[key] = value

    assert len(sets) == 10, f"expected ten sets, got {sorted(sets)}"
    total = 0
    for key, value in sets.items():
        items = value.get("items") or []
        assert items or key == "prescribed_phrases", f"{key} is empty"
        for item in items:
            assert "phrase" in item, f"{key}: entry without `phrase`: {item}"
            assert "term" not in item, f"{key}: entry still carries the old `term` key"
        total += len(items)
    assert total > 100, f"only {total} entries reachable through the contract"


def test_no_shipped_pack_uses_the_old_key_names() -> None:
    for path in SHIPPED_PACKS:
        raw = path.read_text(encoding="utf-8")
        assert not re.search(r"(?m)^\s*entries:\s*$", raw), f"{path.name} still uses `entries:`"
        assert not re.search(r"(?m)^\s*- term:", raw), f"{path.name} still uses `term:`"


def test_renamed_contract_key_is_read_but_reported(tmp_path: Path) -> None:
    """Read it, and say so.

    Silently accepting the alias is exactly how the defect survived: the pack worked for the one
    consumer that tolerated it and was empty for every other.
    """
    from test_draft_score import MINIMAL_PACK

    text = MINIMAL_PACK.replace('  items:\n    - phrase: "Це"', '  entries:\n    - phrase: "Це"')
    path = tmp_path / "lang" / "uk.md"
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text, encoding="utf-8")

    pack = ds.parse_language_pack(path)
    assert pack.sets["anaphora_openers"].entries, "the set must still be read"
    assert any("`entries:`" in d for d in pack.defects), pack.defects


# ---------------------------------------------------------------------------
# Defect 2: normalization
# ---------------------------------------------------------------------------


@pytest.mark.parametrize("path", SHIPPED_PACKS, ids=lambda p: p.stem)
def test_shipped_pack_declares_normalization(path: Path) -> None:
    """Without it the intersection invariant has no definition of "the same phrase"."""
    norm = _pack_meta(path).get("normalization")
    assert norm, f"{path.name} declares no normalization block"
    assert norm.get("tokenizer") == "unicode_words"


def test_uk_normalization_keeps_internal_apostrophes() -> None:
    """The apostrophe is part of the Ukrainian word: «п'ять», «об'єкт», «зв'язок».

    Stripping it merges distinct words and splits single ones, and every density, TTR and n-gram
    number downstream is then wrong while still looking plausible.
    """
    norm = _pack_meta(UK_PACK)["normalization"]
    assert norm.get("strip_internal_apostrophes") is False


def test_uk_declares_its_lemmatizer_gap_rather_than_omitting_it() -> None:
    """An absent field reads as handled. An explicit `unresolved` is a value code can refuse on.

    Ukrainian inflects for seven cases, so surface-form comparison makes the one-anchor-one-URL
    invariant report clean while guaranteeing nothing.
    """
    assert _pack_meta(UK_PACK)["normalization"].get("lemmatizer") == "unresolved"


def test_template_documents_the_lemmatizer_field() -> None:
    assert "lemmatizer" in TEMPLATE.read_text(encoding="utf-8")


# ---------------------------------------------------------------------------
# Defect 3: literal invisible and control characters in patterns
# ---------------------------------------------------------------------------


@pytest.mark.parametrize("path", SHIPPED_PACKS, ids=lambda p: p.stem)
def test_pack_source_has_no_literal_invisible_characters(path: Path) -> None:
    """A pattern you cannot see is a pattern you cannot review."""
    raw = path.read_text(encoding="utf-8")
    bad = sorted(
        {
            hex(ord(c))
            for c in raw
            if (ord(c) < 32 and c not in "\n\t")
            or 0x7F <= ord(c) <= 0x9F
            or ord(c) in (0x200B, 0x200C, 0x200D, 0xFEFF, 0x00AD, 0x202F)
        }
    )
    assert not bad, f"{path.name} carries literal invisible or control characters: {bad}"


def test_uk_technical_defects_set_loads_and_every_entry_runs() -> None:
    pack = ds.parse_language_pack(UK_PACK)
    td = pack.sets["technical_defects_uk"]
    assert len(td.entries) == 6
    for entry in td.entries:
        assert entry.runnable, f"{entry.term}: {entry.compile_error or entry.named_check}"


def test_mojibake_pattern_fires_on_real_mojibake() -> None:
    pack = ds.parse_language_pack(UK_PACK)
    entry = next(e for e in pack.sets["technical_defects_uk"].entries if "mojibake" in e.term)
    damaged = "кредит".encode("utf-8").decode("latin-1")
    assert entry.compiled.search(damaged), "must fire on genuine cp1251/utf-8 damage"
    assert not entry.compiled.search("кредит онлайн на картку")
    assert not entry.compiled.search("credit online")


def test_zero_width_pattern_fires_on_zero_width() -> None:
    pack = ds.parse_language_pack(UK_PACK)
    entry = next(e for e in pack.sets["technical_defects_uk"].entries if "zero-width" in e.term)
    assert entry.compiled.search("сло​во")
    assert not entry.compiled.search("слово чисте")


# ---------------------------------------------------------------------------
# Defect 4: the rule that could never fire
# ---------------------------------------------------------------------------


@pytest.mark.parametrize(
    "text,expected,why",
    [
        ("кредит", False, "clean Ukrainian"),
        ("credit", False, "clean Latin"),
        ("кредит онлайн на картку", False, "clean Ukrainian sentence"),
        ("PDF-файл", False, "legitimate compound; the hyphen splits the token"),
        ("IT-компанія", False, "legitimate compound"),
        ("SMS-повідомлення", False, "legitimate compound"),
        ("Google і Apple", False, "Latin brand names beside Cyrillic words"),
        ("крeдит", True, "Latin e inside a Cyrillic word"),
        ("баnк", True, "Latin n inside a Cyrillic word"),
        ("Укpаїна", True, "Latin p inside a Cyrillic word"),
    ],
)
def test_mixed_script_named_check(text: str, expected: bool, why: str) -> None:
    """The replacement for a rule that compiled and could never match.

    Homoglyph substitution is a property of a token, not of a character, so no lookahead
    formulation can express it. Detection is per letter-run, which is what keeps legitimate
    hyphenated compounds quiet.
    """
    assert bool(ds.check_mixed_script_token(text)) is expected, why


def test_homoglyph_entry_is_wired_to_the_named_check() -> None:
    pack = ds.parse_language_pack(UK_PACK)
    entry = next(e for e in pack.sets["technical_defects_uk"].entries if "homoglyph" in e.term)
    assert entry.named_check == "mixed_script_token"
    assert entry.compiled is None, "a named check must not also carry a pattern"
    assert entry.runnable


def test_the_old_homoglyph_pattern_really_was_dead() -> None:
    """Pinning the failure so nobody reintroduces it believing it worked.

    This is the pattern that shipped. Both lookaheads apply at the same position, so the character
    there would have to be Cyrillic and Latin simultaneously.
    """
    dead = re.compile(r"\b(?=[Ѐ-ӿ])(?=[A-Za-z])\S+\b")
    for sample in ("кредит", "credit", "крeдит", "баnk", "PDF-файл", "Укpаїна"):
        assert not dead.search(sample), f"expected the old pattern to be inert on {sample!r}"


def test_unknown_named_check_is_a_defect_not_a_silent_skip(tmp_path: Path) -> None:
    """A check that cannot run has to say so, or it is the dead rule with extra steps."""
    from test_draft_score import MINIMAL_PACK

    text = MINIMAL_PACK.replace(
        '    - phrase: "Russian-only letters"',
        '    - phrase: "invented"\n      named_check: no_such_check\n'
        '      status: deterministic\n'
        '    - phrase: "Russian-only letters"',
    )
    path = tmp_path / "lang" / "uk.md"
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text, encoding="utf-8")

    pack = ds.parse_language_pack(path)
    assert any("unknown check" in d for d in pack.defects), pack.defects
    entry = next(e for e in pack.sets["technical_defects_uk"].entries if e.term == "invented")
    assert not entry.runnable


# ---------------------------------------------------------------------------
# Rule identifiers
# ---------------------------------------------------------------------------


@pytest.mark.parametrize("path", SHIPPED_PACKS, ids=lambda p: p.stem)
def test_every_set_declares_a_well_formed_rule_id(path: Path) -> None:
    """Findings are counted per rule; an identifier invented at runtime cannot be counted."""
    pack = ds.parse_language_pack(path)
    code = pack.code.upper()
    for key, s in sorted(pack.sets.items()):
        assert s.rule_id, f"{key} declares no rule_id"
        assert re.fullmatch(rf"LANG-{code}-\d{{2}}", s.rule_id), (key, s.rule_id)
    ids = [s.rule_id for s in pack.sets.values()]
    assert len(ids) == len(set(ids)), "identifiers must be unique within a pack"


def test_missing_rule_id_is_reported(tmp_path: Path) -> None:
    from test_draft_score import MINIMAL_PACK

    text = MINIMAL_PACK.replace("  rule_id: LANG-UK-01\n", "", 1)
    path = tmp_path / "lang" / "uk.md"
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text, encoding="utf-8")

    pack = ds.parse_language_pack(path)
    assert any("no `rule_id`" in d for d in pack.defects), pack.defects


# ---------------------------------------------------------------------------
# Severity: the P3 cap and per-entry downgrades
# ---------------------------------------------------------------------------


def test_entry_may_lower_severity_below_the_set_ceiling() -> None:
    """Prose reading "WARN, not BLOCK" beside a field reading BLOCK is prose nothing enforces."""
    pack = ds.parse_language_pack(UK_PACK)
    td = pack.sets["technical_defects_uk"]
    quotes = next(e for e in td.entries if "quotation nesting" in e.term)
    assert quotes.severity == "WARN"
    assert ds.cap_pack_severity(td, quotes) == "WARN"
    letters = next(e for e in td.entries if "Russian-only letters" in e.term)
    assert ds.cap_pack_severity(td, letters) == "BLOCK"


def test_entry_severity_cannot_raise_above_the_ceiling(tmp_path: Path) -> None:
    """A downgrade is legitimate; an upgrade would let a pack promote itself past the P3 cap."""
    from test_draft_score import MINIMAL_PACK

    text = MINIMAL_PACK.replace(
        '    - phrase: "важливо зазначити"\n      match: "важливо зазначити"',
        '    - phrase: "важливо зазначити"\n      severity: BLOCK\n      match: "важливо зазначити"',
    )
    path = tmp_path / "lang" / "uk.md"
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text, encoding="utf-8")

    pack = ds.parse_language_pack(path)
    hedge = pack.sets["hedge_phrases"]
    entry = next(e for e in hedge.entries if e.term == "важливо зазначити")
    assert entry.severity == "BLOCK"
    assert ds.cap_pack_severity(hedge, entry) == "WARN", "a stylistic entry must never hold the gate"


def test_no_shipped_stylistic_set_holds_a_block() -> None:
    """P3, applied to our own detector rather than a purchased one."""
    for path in SHIPPED_PACKS:
        pack = ds.parse_language_pack(path)
        for key, s in pack.sets.items():
            for entry in s.entries:
                if ds.cap_pack_severity(s, entry) == "BLOCK":
                    assert entry.is_deterministic, (
                        f"{path.name}:{key}:{entry.term} blocks without status: deterministic"
                    )
