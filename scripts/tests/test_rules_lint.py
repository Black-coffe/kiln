"""Tests for `rules_lint.py`.

Each invariant gets a constructed violating fixture and a clean one. Testing only the violating
case would leave the linter free to fire on everything, which is the failure mode that gets a
linter switched off rather than fixed.

The final test runs the linter against the real `doctrine/` tree. It asserts that the linter
completes and produces a well-formed report; it deliberately does **not** assert the doctrine is
clean. The doctrine has real violations today, and a test that demanded silence would create
pressure to edit the doctrine until the linter passed, which inverts the relationship between the
two.
"""

from __future__ import annotations

import json
import subprocess
import sys
from datetime import date
from pathlib import Path
from textwrap import dedent

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

import rules_lint  # noqa: E402
from rules_lint import (  # noqa: E402
    EXIT_CLEAN,
    EXIT_ERRORS,
    EXIT_WARNINGS,
    DoctrineLinter,
    _expand_gate_ids,
    _is_doctrine_document,
)

TODAY = date(2026, 8, 7)
SCRIPT = Path(__file__).resolve().parents[1] / "rules_lint.py"
REAL_DOCTRINE = Path(__file__).resolve().parents[2] / "doctrine"


# ---------------------------------------------------------------------------
# Fixture construction
# ---------------------------------------------------------------------------

PRINCIPLES = dedent(
    """\
    # Kiln: Iron Principles

    ## Severity scale

    Three levels: `BLOCK`, `WARN`, `INFO`.

    ## P0. Kiln is a kiln

    Rejection is the measure.

    ## P3. No detector may gate publication

    Forbidden.

    ## P5. Core and packs are separate

    Packs live in `doctrine/lang/<code>.md`.
    """
)

WRITING_CORE = dedent(
    """\
    # 05. Writing Core

    ## §3. Draft scoring

    | ID         | What            | Threshold                                       | Sev   | By   |
    | ---------- | --------------- | ----------------------------------------------- | ----- | ---- |
    | **WRT-01** | brief complete  | 100 % complete                                  | BLOCK | code |
    | **WRT-02** | value source    | `≥ 0.50` [expert judgement, needs calibration]  | WARN  | code |

    ### Composite gate

    ```
    BLOCK  ⟸  any of: WRT-01, 02
    REWORK ⟸  ≥ 2 WARN rules triggered
    PASS   ⟸  everything else
    ```

    ## §6. The language pack contract

    See `00-principles.md` P5.
    """
)


def _pack(
    *,
    prescribed: list[str] | None = None,
    forbidden_extra: list[str] | None = None,
    severity_anaphora: str = "BLOCK",
    default_status_anaphora: str = "deterministic",
    next_review: str = "2026-11-05",
    declare_forbidden: bool = True,
    normalization: bool = True,
    items_key: str = "items",
    phrase_key: str = "phrase",
    rule_ids: bool = True,
    rule_id_locale: str = "TT",
    duplicate_rule_id: bool = False,
) -> str:
    """Build a language pack with the seven required sets, tweakable per test."""
    prescribed = prescribed if prescribed is not None else ["it is", "we tested"]
    forbidden_extra = forbidden_extra or []
    counter = {"n": 0}

    def block(name: str, phrases: list[str], sev: str, status: str, forbidden: bool = True) -> str:
        """One fenced set. Built line by line: interpolating into a dedent-ed block produces
        indentation that depends on the substituted values, which silently yields invalid YAML."""
        out = ["```yaml", f"{name}:"]
        if rule_ids:
            counter["n"] += 1
            nn = 1 if duplicate_rule_id else counter["n"]
            out.append(f"  rule_id: LANG-{rule_id_locale}-{nn:02d}")
        if declare_forbidden:
            out.append(f"  forbidden: {'true' if forbidden else 'false'}")
        out.append(f"  default_status: {status}")
        out.append("  updated_at: 2026-08-07")
        out.append(f"  next_review: {next_review}")
        out.append(f"  severity: {sev}")
        if phrases:
            out.append(f"  {items_key}:")
            for p in phrases:
                out.append(f'    - {{ {phrase_key}: "{p}", risk: low }}')
        else:
            out.append(f"  {items_key}: []")
        out.append("```")
        out.append("")
        return "\n".join(out)

    meta = ["```yaml", "lang:", "  code: tt", "  script: Latn", "  locales: [tt-TT]",
            "  updated_at: 2026-08-07", f"  next_review: {next_review}"]
    if normalization:
        meta += [
            "  normalization:",
            "    case: lower",
            "    unicode_form: NFC",
            "    collapse_whitespace: true",
            "    strip_trailing_ellipsis: true",
            "    strip_terminal_punctuation: true",
            "    tokenizer: unicode_words",
        ]
    meta += ["```", ""]

    parts = ["# Language pack: Test (`tt`)", "", "\n".join(meta)]
    parts.append(block("anaphora_openers", ["this"], severity_anaphora, default_status_anaphora))
    parts.append(block("hedge_phrases", ["it is worth noting"] + forbidden_extra, "WARN", "hypothesis"))
    parts.append(block("closing_formulas", ["in conclusion"], "WARN", "hypothesis"))
    parts.append(block("promo_lexicon", ["cutting-edge"], "WARN", "hypothesis"))
    parts.append(block("vague_attribution", ["studies show"], "WARN", "hypothesis"))
    parts.append(block("generational_stopwords", ["delve"], "WARN", "hypothesis"))
    parts.append(block("prescribed_phrases", prescribed, "INFO", "hypothesis", forbidden=False))
    return "\n".join(parts)


@pytest.fixture
def doctrine(tmp_path: Path) -> Path:
    """A minimal, clean doctrine tree."""
    root = tmp_path / "kiln"
    d = root / "doctrine"
    (d / "lang").mkdir(parents=True)
    (d / "00-principles.md").write_text(PRINCIPLES, encoding="utf-8")
    (d / "05-writing-core.md").write_text(WRITING_CORE, encoding="utf-8")
    (d / "lang" / "tt.md").write_text(_pack(), encoding="utf-8")
    return root


def lint(root: Path, today: date = TODAY) -> DoctrineLinter:
    linter = DoctrineLinter(root / "doctrine", root, today)
    linter.run_all()
    return linter


def checks_firing(linter: DoctrineLinter, severity: str | None = None) -> set[str]:
    return {
        v.check for v in linter.violations if severity is None or v.severity == severity
    }


def _by_check(linter: DoctrineLinter, check: str) -> list:
    """Violations from one check, in report order."""
    return [v for v in linter.violations if v.check == check]


# ---------------------------------------------------------------------------
# The clean baseline
# ---------------------------------------------------------------------------


def test_clean_doctrine_produces_no_errors(doctrine: Path) -> None:
    """The baseline fixture must be genuinely clean, or every other test proves nothing."""
    linter = lint(doctrine)
    errors = [v for v in linter.violations if v.severity == "error"]
    assert errors == [], "\n".join(f"{v.file}:{v.line} {v.check}: {v.message}" for v in errors)
    assert linter.exit_code() in (EXIT_CLEAN, EXIT_WARNINGS)


# ---------------------------------------------------------------------------
# Check 1 — the reason this script exists
# ---------------------------------------------------------------------------


def test_prescribed_phrase_that_is_also_forbidden_is_an_error(doctrine: Path) -> None:
    """The original defect: one phrase prescribed by one document and forbidden by another."""
    (doctrine / "doctrine" / "lang" / "tt.md").write_text(
        _pack(prescribed=["here's the thing"], forbidden_extra=["here's the thing"]),
        encoding="utf-8",
    )
    linter = lint(doctrine)
    assert "prescribed_forbidden_intersection" in checks_firing(linter, "error")


def test_intersection_respects_declared_normalization(doctrine: Path) -> None:
    """"Here's the thing…" and "here's the thing" are the same phrase under the pack's rules.

    A linter comparing raw strings would miss it, which is how the defect survived in the first
    place: the two documents spelled it differently.
    """
    (doctrine / "doctrine" / "lang" / "tt.md").write_text(
        _pack(prescribed=["Here's the thing…"], forbidden_extra=["here's the thing"]),
        encoding="utf-8",
    )
    linter = lint(doctrine)
    assert "prescribed_forbidden_intersection" in checks_firing(linter, "error")


def test_intersection_sees_pack_local_forbidden_sets(doctrine: Path) -> None:
    """A set beyond the required seven must still enter the union.

    A fixed list of five cannot see the Ukrainian russism set, and a pack could then prescribe a
    phrase its own set forbids while the build passed.
    """
    pack = _pack(prescribed=["згідно з"])
    pack += dedent(
        """
        ```yaml
        russisms_calques:
          forbidden: true
          default_status: hypothesis
          updated_at: 2026-08-07
          next_review: 2026-11-05
          severity: WARN
          items:
            - { phrase: "згідно з", risk: high, note: "calque" }
        ```
        """
    )
    (doctrine / "doctrine" / "lang" / "tt.md").write_text(pack, encoding="utf-8")
    linter = lint(doctrine)
    assert "prescribed_forbidden_intersection" in checks_firing(linter, "error")


def test_missing_normalization_block_is_an_error(doctrine: Path) -> None:
    """Without declared normalization the invariant is undefined, not merely untidy."""
    (doctrine / "doctrine" / "lang" / "tt.md").write_text(
        _pack(normalization=False), encoding="utf-8"
    )
    linter = lint(doctrine)
    assert "prescribed_forbidden_intersection" in checks_firing(linter, "error")


# ---------------------------------------------------------------------------
# Check 3 — duplicate and misplaced identifiers
# ---------------------------------------------------------------------------


def test_rule_defined_in_two_files_is_an_error(doctrine: Path) -> None:
    (doctrine / "doctrine" / "02-semantics.md").write_text(
        dedent(
            """\
            # 02. Semantics

            | ID         | What | Sev   |
            | ---------- | ---- | ----- |
            | **WRT-01** | copy | BLOCK |
            """
        ),
        encoding="utf-8",
    )
    linter = lint(doctrine)
    assert "duplicate_rule_id" in checks_firing(linter, "error")


def test_rule_defined_outside_its_owning_section_is_an_error(doctrine: Path) -> None:
    """A SEM rule declared in the writing file means one of the two files is lying about scope."""
    (doctrine / "doctrine" / "05-writing-core.md").write_text(
        WRITING_CORE
        + dedent(
            """
            | ID         | What | Sev   |
            | ---------- | ---- | ----- |
            | **SEM-01** | oops | BLOCK |
            """
        ),
        encoding="utf-8",
    )
    linter = lint(doctrine)
    errs = [v for v in linter.violations if v.check == "duplicate_rule_id" and v.severity == "error"]
    assert any("belongs to" in v.message for v in errs)


# ---------------------------------------------------------------------------
# Check 4 — the composite gate
# ---------------------------------------------------------------------------


def test_composite_gate_naming_a_missing_rule_is_an_error(doctrine: Path) -> None:
    """A typo in the gate does not fail loudly; it silently stops enforcing a rule."""
    (doctrine / "doctrine" / "05-writing-core.md").write_text(
        WRITING_CORE.replace("any of: WRT-01, 02", "any of: WRT-01, 02, 77"),
        encoding="utf-8",
    )
    linter = lint(doctrine)
    assert "composite_gate" in checks_firing(linter, "error")


def test_gate_expansion_ignores_parentheticals_and_counts() -> None:
    """`20 (when OCD=0)` and `≥ 2 WARN rules` must not mint WRT-0 and WRT-2."""
    body = dedent(
        """\
        BLOCK  ⟸  any of: WRT-01..03, 20 (when OCD=0), 21 (when EG<0.08)
        REWORK ⟸  ≥ 2 WARN rules triggered
        PASS   ⟸  everything else
        """
    )
    ids = {rid for rid, _ in _expand_gate_ids(body)}
    assert ids == {"WRT-01", "WRT-02", "WRT-03", "WRT-20", "WRT-21"}


def test_gate_expansion_reads_blockquoted_and_padded_ids() -> None:
    ids = {rid for rid, _ in _expand_gate_ids("BLOCK  ⟸  any of: MSR-05..07")}
    assert ids == {"MSR-05", "MSR-06", "MSR-07"}


# ---------------------------------------------------------------------------
# Check 5 — review dates
# ---------------------------------------------------------------------------


def test_overdue_pack_review_warns_but_does_not_block(doctrine: Path) -> None:
    """Stale vocabulary still catches yesterday's output; it merely under-detects today's."""
    (doctrine / "doctrine" / "lang" / "tt.md").write_text(
        _pack(next_review="2026-01-01"), encoding="utf-8"
    )
    linter = lint(doctrine)
    assert "review_dates" in checks_firing(linter, "warning")
    assert "review_dates" not in checks_firing(linter, "error")


def test_review_dates_are_deterministic_under_today_override(doctrine: Path) -> None:
    (doctrine / "doctrine" / "lang" / "tt.md").write_text(
        _pack(next_review="2026-09-01"), encoding="utf-8"
    )
    assert "review_dates" not in checks_firing(lint(doctrine, date(2026, 8, 7)), "warning")
    assert "review_dates" in checks_firing(lint(doctrine, date(2027, 1, 1)), "warning")


# ---------------------------------------------------------------------------
# Check 7 — doctrine and code drift apart
# ---------------------------------------------------------------------------


def test_rule_id_used_in_code_but_absent_from_doctrine_is_an_error(doctrine: Path) -> None:
    scripts = doctrine / "scripts"
    scripts.mkdir()
    (scripts / "thing.py").write_text('rule_id = "WRT-99"\n', encoding="utf-8")
    linter = lint(doctrine)
    assert "code_doctrine_ids" in checks_firing(linter, "error")


def test_section_number_used_as_a_rule_id_is_reported_verbatim(doctrine: Path) -> None:
    """`MSR-5.2` is a section number, not a rule. The report must say so, not truncate to MSR-5."""
    scripts = doctrine / "scripts"
    scripts.mkdir()
    (scripts / "thing.py").write_text('rule_id = "MSR-5.2"\n', encoding="utf-8")
    linter = lint(doctrine)
    msgs = [v.message for v in linter.violations if v.check == "code_doctrine_ids"]
    assert any("MSR-5.2" in m for m in msgs)


def test_rule_id_present_in_doctrine_passes(doctrine: Path) -> None:
    scripts = doctrine / "scripts"
    scripts.mkdir()
    (scripts / "thing.py").write_text('rule_id = "WRT-01"\n', encoding="utf-8")
    linter = lint(doctrine)
    assert "code_doctrine_ids" not in checks_firing(linter, "error")


# ---------------------------------------------------------------------------
# Check 8 — one threshold, one home
# ---------------------------------------------------------------------------


def test_same_threshold_with_two_values_in_two_files_is_an_error(doctrine: Path) -> None:
    (doctrine / "doctrine" / "06-review-lenses.md").write_text(
        "# 06\n\nA rule fires when `override_rate` ≥ 0.40 over enough samples.\n",
        encoding="utf-8",
    )
    (doctrine / "doctrine" / "11-self-learning.md").write_text(
        "# 11\n\nDeletion is considered when `override_rate` ≥ 0.55 over enough samples.\n",
        encoding="utf-8",
    )
    linter = lint(doctrine)
    assert "threshold_single_home" in checks_firing(linter, "error")


def test_same_threshold_restated_identically_is_only_a_warning(doctrine: Path) -> None:
    """A matching restatement is legal. It still drifts, so it is surfaced, not blocked."""
    (doctrine / "doctrine" / "06-review-lenses.md").write_text(
        "# 06\n\nA rule fires when `override_rate` ≥ 0.40 here.\n", encoding="utf-8"
    )
    (doctrine / "doctrine" / "11-self-learning.md").write_text(
        "# 11\n\nAnd `override_rate` ≥ 0.40 there.\n", encoding="utf-8"
    )
    linter = lint(doctrine)
    assert "threshold_single_home" in checks_firing(linter, "warning")
    assert "threshold_single_home" not in checks_firing(linter, "error")


# ---------------------------------------------------------------------------
# Check 9 — packs must not rebuild a detector and point it at the gate
# ---------------------------------------------------------------------------


def test_stylistic_pack_set_carrying_block_is_an_error(doctrine: Path) -> None:
    """Gating on a vocabulary hit is the failure P3 forbids, with our own detector."""
    (doctrine / "doctrine" / "lang" / "tt.md").write_text(
        _pack(severity_anaphora="BLOCK", default_status_anaphora="hypothesis"),
        encoding="utf-8",
    )
    linter = lint(doctrine)
    assert "pack_block_severity" in checks_firing(linter, "error")


def test_deterministic_pack_set_may_carry_block(doctrine: Path) -> None:
    """A letter absent from the alphabet is a fact, not a stylometric score."""
    linter = lint(doctrine)  # baseline pack: anaphora_openers is BLOCK + deterministic
    assert "pack_block_severity" not in checks_firing(linter, "error")


# ---------------------------------------------------------------------------
# Check 10 — pack structure
# ---------------------------------------------------------------------------


def test_set_without_forbidden_flag_is_an_error(doctrine: Path) -> None:
    """An undeclared set is invisible to the intersection invariant even though it parses."""
    (doctrine / "doctrine" / "lang" / "tt.md").write_text(
        _pack(declare_forbidden=False), encoding="utf-8"
    )
    linter = lint(doctrine)
    assert "pack_structure" in checks_firing(linter, "error")


def test_missing_required_set_is_an_error(doctrine: Path) -> None:
    pack = _pack()
    pack = pack.replace("closing_formulas:", "closing_formulae:")
    (doctrine / "doctrine" / "lang" / "tt.md").write_text(pack, encoding="utf-8")
    linter = lint(doctrine)
    msgs = [v.message for v in linter.violations if v.check == "pack_structure"]
    assert any("closing_formulas" in m and "missing" in m for m in msgs)


def test_entries_key_deviation_is_reported_not_skipped(doctrine: Path) -> None:
    """The parser must see a set written with the wrong key, then name the deviation.

    Silently skipping it would hide the set from the intersection invariant, which is the one
    thing this linter must never do.
    """
    (doctrine / "doctrine" / "lang" / "tt.md").write_text(
        _pack(items_key="entries", phrase_key="term"), encoding="utf-8"
    )
    linter = lint(doctrine)
    msgs = [v.message for v in linter.violations if v.check == "pack_structure"]
    assert any("`entries:`" in m for m in msgs)
    assert any("`term:`" in m for m in msgs)


def test_entries_key_deviation_still_checks_the_intersection(doctrine: Path) -> None:
    """A pack using the wrong key is still checked for the defect that matters."""
    (doctrine / "doctrine" / "lang" / "tt.md").write_text(
        _pack(
            items_key="entries",
            phrase_key="term",
            prescribed=["here's the thing"],
            forbidden_extra=["here's the thing"],
        ),
        encoding="utf-8",
    )
    linter = lint(doctrine)
    assert "prescribed_forbidden_intersection" in checks_firing(linter, "error")


def test_unknown_status_value_is_an_error(doctrine: Path) -> None:
    (doctrine / "doctrine" / "lang" / "tt.md").write_text(
        _pack(default_status_anaphora="guesswork"), encoding="utf-8"
    )
    linter = lint(doctrine)
    assert "pack_structure" in checks_firing(linter, "error")


# ---------------------------------------------------------------------------
# Check 11 — principle identifiers are reserved
# ---------------------------------------------------------------------------


def test_reference_to_a_nonexistent_principle_is_an_error(doctrine: Path) -> None:
    (doctrine / "doctrine" / "05-writing-core.md").write_text(
        WRITING_CORE + "\nThis follows from P42.\n", encoding="utf-8"
    )
    linter = lint(doctrine)
    assert "principle_reference" in checks_firing(linter, "error")


def test_intel_prefixed_identifier_is_not_a_principle_reference(doctrine: Path) -> None:
    """`EVIDENCE.md#e10-eeat-entities-schema P13` is a trust signal from a research report, not principle 13."""
    (doctrine / "doctrine" / "05-writing-core.md").write_text(
        WRITING_CORE + "\nSee `EVIDENCE.md#e10-eeat-entities-schema` P13 for the trust signal.\n", encoding="utf-8"
    )
    linter = lint(doctrine)
    assert "principle_reference" not in checks_firing(linter, "error")


# ---------------------------------------------------------------------------
# Check 12 — one severity ladder
# ---------------------------------------------------------------------------


def test_review_verdict_used_outside_the_review_file_is_an_error(doctrine: Path) -> None:
    (doctrine / "doctrine" / "11-self-learning.md").write_text(
        "# 11\n\n**LRN-09 (HIGH).** A disagreement without both rationales is discarded.\n",
        encoding="utf-8",
    )
    linter = lint(doctrine)
    assert "severity_vocabulary" in checks_firing(linter, "error")


def test_prose_word_high_is_not_a_severity(doctrine: Path) -> None:
    """"a HIGH degree of overlap" in prose is not a severity assignment."""
    (doctrine / "doctrine" / "05-writing-core.md").write_text(
        WRITING_CORE + "\nThis produces a HIGH degree of overlap between locales.\n",
        encoding="utf-8",
    )
    linter = lint(doctrine)
    assert "severity_vocabulary" not in checks_firing(linter, "error")


def test_file_declaring_its_own_scale_is_exempted_with_a_warning(doctrine: Path) -> None:
    """A register grading question urgency is a different axis, not a fourth rule ladder."""
    (doctrine / "doctrine" / "OPEN-QUESTIONS.md").write_text(
        dedent(
            """\
            # Open questions

            **Severity meanings.** `CRITICAL` — dated deadline. `HIGH` — silently wrong results.

            | Q | Severity |
            | - | -------- |
            | 1 | `HIGH`   |
            """
        ),
        encoding="utf-8",
    )
    linter = lint(doctrine)
    assert "severity_vocabulary" not in checks_firing(linter, "error")
    assert "severity_vocabulary" in checks_firing(linter, "warning")


# ---------------------------------------------------------------------------
# Check 13 — cross references
# ---------------------------------------------------------------------------


def test_reference_to_a_missing_doctrine_file_is_an_error(doctrine: Path) -> None:
    (doctrine / "doctrine" / "05-writing-core.md").write_text(
        WRITING_CORE + "\nSee `99-nonexistent.md` for details.\n", encoding="utf-8"
    )
    linter = lint(doctrine)
    assert "cross_reference" in checks_firing(linter, "error")


def test_runtime_artefact_names_are_not_cross_references(doctrine: Path) -> None:
    """`draft.md` is something the pipeline writes, not a document in this repository."""
    (doctrine / "doctrine" / "05-writing-core.md").write_text(
        WRITING_CORE + "\nStage 4 emits `draft.md` and stage 3 emits `outline.md`.\n",
        encoding="utf-8",
    )
    linter = lint(doctrine)
    assert "cross_reference" not in checks_firing(linter, "error")


def test_planned_language_pack_is_a_warning_not_an_error(doctrine: Path) -> None:
    (doctrine / "doctrine" / "lang" / "tt.md").write_text(
        _pack() + "\n`ru.md` is a separate pack; rules never cross.\n", encoding="utf-8"
    )
    linter = lint(doctrine)
    assert "cross_reference" not in checks_firing(linter, "error")
    assert "cross_reference" in checks_firing(linter, "warning")


def test_governance_docs_at_repo_root_resolve(doctrine: Path) -> None:
    (doctrine / "RULE-CHANGE.md").write_text("# Rule change template\n", encoding="utf-8")
    (doctrine / "doctrine" / "05-writing-core.md").write_text(
        WRITING_CORE + "\nAmend via `RULE-CHANGE.md`.\n", encoding="utf-8"
    )
    linter = lint(doctrine)
    assert "cross_reference" not in checks_firing(linter, "error")


def test_doctrine_document_recognition() -> None:
    assert _is_doctrine_document("05-writing-core.md")
    assert _is_doctrine_document("RULE-CHANGE.md")
    assert _is_doctrine_document("uk.md")
    assert _is_doctrine_document("_template.md")
    assert not _is_doctrine_document("draft.md")
    assert not _is_doctrine_document("onboarding-report.md")


# ---------------------------------------------------------------------------
# Malformed YAML
# ---------------------------------------------------------------------------


def test_unparseable_yaml_block_is_an_error(doctrine: Path) -> None:
    """Every check reading that block is skipped until it parses, so silence would be a lie."""
    (doctrine / "doctrine" / "lang" / "tt.md").write_text(
        _pack() + "\n```yaml\nbroken:\n  - [unclosed\n```\n", encoding="utf-8"
    )
    linter = lint(doctrine)
    assert "yaml_parses" in checks_firing(linter, "error")


# ---------------------------------------------------------------------------
# Report shape, exit codes, determinism
# ---------------------------------------------------------------------------


def test_report_is_deterministic(doctrine: Path) -> None:
    """Byte-identical output, or a change in the linter is indistinguishable from a change in
    the doctrine."""
    a = json.dumps(lint(doctrine).report(), sort_keys=True)
    b = json.dumps(lint(doctrine).report(), sort_keys=True)
    assert a == b


def test_exit_code_is_two_when_errors_present(doctrine: Path) -> None:
    (doctrine / "doctrine" / "05-writing-core.md").write_text(
        WRITING_CORE + "\nThis follows from P42.\n", encoding="utf-8"
    )
    assert lint(doctrine).exit_code() == EXIT_ERRORS


def test_warnings_alone_do_not_fail_the_build(doctrine: Path) -> None:
    """Warnings report and exit 0.

    An earlier revision exited 1 on warnings. That collided with the shared convention where 1
    means "the script could not complete", so a crash and a stale review date became
    indistinguishable to a caller, and it made the pipeline permanently red on a corpus that
    legitimately carries warnings. A permanently red pipeline stops being read.
    """
    (doctrine / "doctrine" / "lang" / "tt.md").write_text(
        _pack(next_review="2026-01-01"), encoding="utf-8"
    )
    linter = lint(doctrine)
    assert not any(v.severity == "error" for v in linter.violations)
    assert any(v.severity == "warning" for v in linter.violations), "fixture should warn"
    assert linter.exit_code() == 0


def test_report_contains_file_and_line_for_every_violation(doctrine: Path) -> None:
    """A linter whose message does not say where to look gets suppressed rather than fixed."""
    (doctrine / "doctrine" / "lang" / "tt.md").write_text(
        _pack(prescribed=["here's the thing"], forbidden_extra=["here's the thing"]),
        encoding="utf-8",
    )
    report = lint(doctrine).report()
    for bucket in ("errors", "warnings"):
        for v in report[bucket]:
            assert v["file"]
            assert isinstance(v["line"], int) and v["line"] >= 1
            assert v["message"] and v["remedy"]


def test_missing_doctrine_directory_raises(tmp_path: Path) -> None:
    with pytest.raises(rules_lint.KilnError):
        DoctrineLinter(tmp_path / "nope", tmp_path, TODAY)


# ---------------------------------------------------------------------------
# Smoke test against the real doctrine
# ---------------------------------------------------------------------------


@pytest.mark.skipif(not REAL_DOCTRINE.is_dir(), reason="real doctrine tree not present")
def test_smoke_against_real_doctrine() -> None:
    """Runs against the live doctrine.

    Asserts the linter completes and produces a well-formed report. It does **not** assert the
    doctrine is clean: the doctrine has real violations today, and a test demanding silence would
    create pressure to edit the doctrine until the linter passed. The linter reports; humans fix.
    """
    linter = DoctrineLinter(REAL_DOCTRINE, REAL_DOCTRINE.parent, TODAY)
    linter.run_all()
    report = linter.report()

    assert report["checked"]["doctrine_files"] >= 10
    assert report["checked"]["language_packs"] >= 2
    assert report["checked"]["rules_defined"] >= 100

    for bucket in ("errors", "warnings"):
        for v in report[bucket]:
            assert v["file"] and v["message"] and v["remedy"]
            assert isinstance(v["line"], int)

    counted = sum(
        c["errors"] + c["warnings"] for c in report["summary"]["by_check"].values()
    )
    assert counted == len(report["errors"]) + len(report["warnings"])


@pytest.mark.skipif(not REAL_DOCTRINE.is_dir(), reason="real doctrine tree not present")
def test_cli_runs_and_returns_documented_exit_code() -> None:
    """The CLI is what CI invokes; a linter that only works as a library is not a gate."""
    proc = subprocess.run(
        [
            sys.executable,
            str(SCRIPT),
            "--doctrine",
            str(REAL_DOCTRINE),
            "--root",
            str(REAL_DOCTRINE.parent),
            "--today",
            "2026-08-07",
        ],
        capture_output=True,
        text=True,
        encoding="utf-8",
    )
    assert proc.returncode in (EXIT_CLEAN, EXIT_WARNINGS, EXIT_ERRORS)
    payload = json.loads(proc.stdout)
    assert "errors" in payload and "warnings" in payload and "summary" in payload


# ---------------------------------------------------------------------------
# check 14: language pack rule identifiers
# ---------------------------------------------------------------------------


def test_pack_set_without_rule_id_is_an_error(doctrine: Path) -> None:
    """Findings are counted per rule. An identifier invented at runtime cannot be counted."""
    (doctrine / "doctrine" / "lang" / "tt.md").write_text(_pack(rule_ids=False), encoding="utf-8")
    v = _by_check(lint(doctrine), "pack_rule_ids")
    assert v, "a pack declaring no rule_id must be reported"
    assert all(x.severity == "error" for x in v)
    assert any("declares no `rule_id`" in x.message for x in v)


def test_pack_rule_id_locale_must_match_the_pack(doctrine: Path) -> None:
    """A pack copied from another language and edited keeps the donor's locale segment.

    That silently merges two languages' counters under one identifier, which is the failure the
    locale segment exists to prevent.
    """
    (doctrine / "doctrine" / "lang" / "tt.md").write_text(
        _pack(rule_id_locale="UK"), encoding="utf-8"
    )
    v = _by_check(lint(doctrine), "pack_rule_ids")
    assert v and all(x.severity == "error" for x in v)
    assert any("this pack's locale is TT" in x.message for x in v)


def test_duplicate_pack_rule_id_is_an_error(doctrine: Path) -> None:
    (doctrine / "doctrine" / "lang" / "tt.md").write_text(
        _pack(duplicate_rule_id=True), encoding="utf-8"
    )
    v = _by_check(lint(doctrine), "pack_rule_ids")
    assert v and any("already declared" in x.message for x in v)


def test_well_formed_pack_rule_ids_are_clean(doctrine: Path) -> None:
    (doctrine / "doctrine" / "lang" / "tt.md").write_text(_pack(), encoding="utf-8")
    assert not _by_check(lint(doctrine), "pack_rule_ids")


def test_pack_declared_rule_id_counts_as_a_definition(doctrine: Path) -> None:
    """A script emitting a pack's own identifier must not be reported as citing a missing rule.

    Without this, the honest-looking fix is to suppress the check, which is how a linter stops
    catching anything.
    """
    (doctrine / "doctrine" / "lang" / "tt.md").write_text(_pack(), encoding="utf-8")
    scripts = doctrine / "scripts"
    scripts.mkdir(exist_ok=True)
    (scripts / "emitter.py").write_text('rule_id = "LANG-TT-01"\n', encoding="utf-8")
    v = [x for x in _by_check(lint(doctrine), "code_doctrine_ids") if "LANG-TT-01" in x.message]
    assert not v, [x.message for x in v]


def test_undeclared_pack_rule_id_in_code_is_reported(doctrine: Path) -> None:
    (doctrine / "doctrine" / "lang" / "tt.md").write_text(_pack(), encoding="utf-8")
    scripts = doctrine / "scripts"
    scripts.mkdir(exist_ok=True)
    (scripts / "emitter.py").write_text('rule_id = "LANG-TT-99"\n', encoding="utf-8")
    v = [x for x in _by_check(lint(doctrine), "code_doctrine_ids") if "LANG-TT-99" in x.message]
    assert v and v[0].severity == "error"


# ---------------------------------------------------------------------------
# check 15: patterns that cannot match, and checks that do not exist
# ---------------------------------------------------------------------------


def _pack_with_entry(entry: str, doctrine: Path) -> None:
    """Write a valid pack whose anaphora set carries one extra hand-written entry."""
    text = _pack()
    marker = '    - { phrase: "this", risk: low }'
    assert marker in text, text[:400]
    (doctrine / "doctrine" / "lang" / "tt.md").write_text(
        text.replace(marker, marker + "\n" + entry, 1), encoding="utf-8"
    )


def test_impossible_adjacent_lookaheads_are_reported(doctrine: Path) -> None:
    """The recorded dead rule: two lookaheads demanding one character be in two scripts.

    It compiled, it reviewed cleanly, and its match set was empty for as long as it shipped.
    """
    _pack_with_entry(
        '    - { phrase: "homoglyph", risk: high, '
        "match: '\\b(?=\\p{Cyrillic})(?=\\p{Latin})\\S+\\b' }",
        doctrine,
    )
    v = _by_check(lint(doctrine), "pack_patterns")
    assert v and v[0].severity == "error"
    assert "can never match" in v[0].message


def test_unknown_named_check_is_reported(doctrine: Path) -> None:
    """A named check nothing implements must not pass silently: that is the dead rule again."""
    _pack_with_entry(
        '    - { phrase: "invented", risk: high, named_check: no_such_check }', doctrine
    )
    v = _by_check(lint(doctrine), "pack_patterns")
    assert v and v[0].severity == "error"
    assert "not implemented" in v[0].message


def test_known_named_check_is_accepted(doctrine: Path) -> None:
    _pack_with_entry(
        '    - { phrase: "homoglyph", risk: high, named_check: mixed_script_token }', doctrine
    )
    assert not _by_check(lint(doctrine), "pack_patterns")


def test_named_check_and_match_together_is_a_warning(doctrine: Path) -> None:
    _pack_with_entry(
        '    - { phrase: "both", risk: high, named_check: mixed_script_token, match: "x" }',
        doctrine,
    )
    v = _by_check(lint(doctrine), "pack_patterns")
    assert v and v[0].severity == "warning"
    assert "declares both `named_check` and `match`" in v[0].message
    assert "mutually exclusive" in v[0].remedy


def test_real_doctrine_packs_declare_valid_rule_ids() -> None:
    """Smoke test against the shipped packs, not a fixture."""
    root = Path(__file__).resolve().parents[2]
    linter = DoctrineLinter(root / "doctrine", root, date(2026, 8, 7))
    linter.run_all()
    bad = _by_check(linter, "pack_rule_ids") + _by_check(linter, "pack_patterns")
    assert not bad, [f"{x.file}:{x.line} {x.message}" for x in bad]


# ---------------------------------------------------------------------------
# Suppressions
# ---------------------------------------------------------------------------

# Assembled by concatenation rather than written literally. The linter scans `scripts/` including
# this file, so a literal, well-formed marker here would be collected as a real suppression of the
# real corpus and then reported stale forever.
MARK = "# kiln-lint: ignore"


def _scripts_dir(root: Path) -> Path:
    d = root / "scripts"
    d.mkdir(exist_ok=True)
    return d


def _reported_checks(linter: DoctrineLinter, severity: str) -> list[str]:
    """Checks visible in the report, i.e. after suppressions are applied."""
    return [v["check"] for v in linter.report()[severity + "s"]]


def test_suppression_silences_its_own_finding(doctrine: Path) -> None:
    body = 'rule_id = "WRT-99"  ' + MARK + " code_doctrine_ids -- deliberate fixture\n"
    (_scripts_dir(doctrine) / "thing.py").write_text(body, encoding="utf-8")
    linter = lint(doctrine)

    # The violation is still found; it is withheld from the report rather than never detected.
    assert "code_doctrine_ids" in checks_firing(linter, "error")
    assert "code_doctrine_ids" not in _reported_checks(linter, "error")

    s = linter.report()["summary"]["suppressions"]
    assert s == {"declared": 1, "applied": 1, "stale": 0, "findings_suppressed": 1}


def test_suppression_is_scoped_to_the_named_check(doctrine: Path) -> None:
    """Suppressing one check must not silence a different finding on the same line."""
    body = 'rule_id = "WRT-99"  ' + MARK + " yaml_parses -- wrong check on purpose\n"
    (_scripts_dir(doctrine) / "thing.py").write_text(body, encoding="utf-8")
    linter = lint(doctrine)
    assert "code_doctrine_ids" in _reported_checks(linter, "error")
    # And the suppression that matched nothing is itself surfaced.
    assert linter.report()["summary"]["suppressions"]["stale"] == 1


def test_suppression_does_not_leak_to_the_next_line(doctrine: Path) -> None:
    body = (
        'a = "WRT-98"  ' + MARK + " code_doctrine_ids -- first line only\n"
        'b = "WRT-97"\n'
    )
    (_scripts_dir(doctrine) / "thing.py").write_text(body, encoding="utf-8")
    linter = lint(doctrine)
    reported = [v for v in linter.report()["errors"] if v["check"] == "code_doctrine_ids"]
    assert len(reported) == 1
    assert reported[0]["line"] == 2
    assert "WRT-97" in reported[0]["message"]


def test_suppression_without_a_reason_is_an_error(doctrine: Path) -> None:
    body = 'rule_id = "WRT-99"  ' + MARK + " code_doctrine_ids\n"
    (_scripts_dir(doctrine) / "thing.py").write_text(body, encoding="utf-8")
    linter = lint(doctrine)
    msgs = [v["message"] for v in linter.report()["errors"] if v["check"] == "lint_suppression"]
    assert any("no reason" in m for m in msgs)
    # It also does not take effect, so the finding it aimed at still reports.
    assert "code_doctrine_ids" in _reported_checks(linter, "error")


def test_suppression_with_an_empty_reason_is_an_error(doctrine: Path) -> None:
    body = 'rule_id = "WRT-99"  ' + MARK + " code_doctrine_ids --   \n"
    (_scripts_dir(doctrine) / "thing.py").write_text(body, encoding="utf-8")
    linter = lint(doctrine)
    assert "lint_suppression" in _reported_checks(linter, "error")


def test_stale_suppression_warns(doctrine: Path) -> None:
    body = 'rule_id = "WRT-01"  ' + MARK + " code_doctrine_ids -- nothing to silence here\n"
    (_scripts_dir(doctrine) / "thing.py").write_text(body, encoding="utf-8")
    linter = lint(doctrine)
    msgs = [v["message"] for v in linter.report()["warnings"] if v["check"] == "lint_suppression"]
    assert any("stale" in m for m in msgs)
    assert linter.report()["summary"]["suppressions"]["stale"] == 1


def test_unknown_check_name_in_a_suppression_is_an_error(doctrine: Path) -> None:
    """A typo silences nothing while looking as though it does."""
    body = 'rule_id = "WRT-99"  ' + MARK + " code_doctrin_ids -- typo\n"
    (_scripts_dir(doctrine) / "thing.py").write_text(body, encoding="utf-8")
    linter = lint(doctrine)
    msgs = [v["message"] for v in linter.report()["errors"] if v["check"] == "lint_suppression"]
    assert any("not a check" in m for m in msgs)
    assert "code_doctrine_ids" in _reported_checks(linter, "error")


def test_the_suppression_auditor_cannot_be_suppressed(doctrine: Path) -> None:
    body = "x = 1  " + MARK + " lint_suppression -- trying to hide the auditor\n"
    (_scripts_dir(doctrine) / "thing.py").write_text(body, encoding="utf-8")
    linter = lint(doctrine)
    msgs = [v["message"] for v in linter.report()["errors"] if v["check"] == "lint_suppression"]
    assert any("cannot itself be suppressed" in m for m in msgs)


def test_suppressions_are_listed_in_the_report(doctrine: Path) -> None:
    """Counted and visible, or nobody ever prunes them."""
    body = 'rule_id = "WRT-99"  ' + MARK + " code_doctrine_ids -- documented exemption\n"
    (_scripts_dir(doctrine) / "thing.py").write_text(body, encoding="utf-8")
    rep = lint(doctrine).report()
    assert rep["suppressions"] == [{
        "file": "scripts/thing.py",
        "line": 1,
        "check": "code_doctrine_ids",
        "reason": "documented exemption",
        "used": 1,
    }]


def test_report_is_idempotent_across_calls(doctrine: Path) -> None:
    """`report()` and `exit_code()` both partition; usage counts must not accumulate."""
    body = 'rule_id = "WRT-99"  ' + MARK + " code_doctrine_ids -- fixture\n"
    (_scripts_dir(doctrine) / "thing.py").write_text(body, encoding="utf-8")
    linter = lint(doctrine)
    first = json.dumps(linter.report(), sort_keys=True)
    linter.exit_code()
    second = json.dumps(linter.report(), sort_keys=True)
    assert first == second
