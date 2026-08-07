#!/usr/bin/env python3
"""The machine gate every draft passes before a human sees it.

Specification: `doctrine/05-writing-core.md` §3 (the rule table), §5 (the effort gate),
§6 (the language pack contract), §10 (this script's IO contract).

What this script is for: spending human review attention only on drafts that are worth it.
Human attention is the binding constraint on the whole system (P2), so a draft with a fabricated
claim or a dead link must never reach a reviewer.

Three things it deliberately does not do.

1. **It does not judge meaning.** Rules the specification marks as agent-evaluated emit
   `requires_agent` and are never silently converted into a number. Approximating "does this
   sentence answer the question" with a heuristic is how a gate starts lying.
2. **It does not let an unrun check pass.** `PASS` requires every BLOCK rule to have actually
   evaluated to `pass`. A BLOCK rule sitting at `requires_agent` or `requires_input` caps the
   verdict at `REWORK`. You cannot pass a gate you did not run.
3. **It does not block on style.** Language pack metrics are capped at `WARN` in code, not by
   trusting the pack to declare its own ceiling honestly (`00-principles.md`, severity scale).
   The single exception the doctrine grants is `status: deterministic` entries, which are facts
   about orthography rather than frequency claims.

Runtime: Python 3.11+, PyYAML. No network: link liveness is read from `http_status` captured in
the research packet at fetch time, not re-fetched here.

--------------------------------------------------------------------------------------------
KNOWN CONTRACT COLLISION, flagged rather than papered over
--------------------------------------------------------------------------------------------
`05-writing-core.md` §10 specifies exit codes `0 PASS · 1 REWORK · 2 BLOCK`. `kiln_common.py`
reserves `1` for an operational error. Both cannot hold. This script follows the doctrine, since
the specification is authoritative for exit behaviour, which means a crash and a REWORK verdict
both leave the shell with 1. They are distinguishable in practice: a REWORK writes a complete
score record to stdout or `--out`, an error writes nothing there and prints `error:` on stderr.
The clean fix is to move REWORK to exit 3, which is what `EXIT_SCRIPT_SPECIFIC` exists for. That
is a doctrine change and belongs in a RULE-CHANGE PR, not in a script comment.
"""

from __future__ import annotations

import hashlib
import math
import re
import statistics
import sys
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Callable, Iterable, Sequence

sys.path.insert(0, str(Path(__file__).resolve().parent))

from kiln_common import (  # noqa: E402
    EXIT_OK,
    KilnError,
    Thresholds,
    base_parser,
    count_words,
    dumps,
    load_thresholds,
    normalize_text,
    run,
    split_sentences,
    stable_key,
    tokenize_words,
    write_json,
)

# ---------------------------------------------------------------------------
# Exit codes, per the specification rather than the shared convention. See the module docstring.
# ---------------------------------------------------------------------------

EXIT_PASS = 0
EXIT_REWORK = 1
EXIT_BLOCK = 2

# ---------------------------------------------------------------------------
# Doctrine defaults
# ---------------------------------------------------------------------------
# Transcribed from `05-writing-core.md` §3. Every one of these is overridable from
# `.kiln/thresholds.yml`, and every finding records which layer answered, because a threshold
# recalibrated next quarter otherwise silently rewrites the meaning of findings stored today.

DOCTRINE_DEFAULTS: dict[str, Any] = {
    "wrt11.sourced_share_min": 0.85,
    "wrt11.sourced_share_min_ymyl": 1.00,
    "wrt12.primary_source_ratio_min": 0.50,
    "wrt13.link_liveness_min": 1.00,
    "wrt14.date_divergence_days_max": 90,
    "wrt15.volatile_source_age_days_max": 30,
    "wrt20.ocd_min": 2.0,
    "wrt21.entity_gain_warn": 0.15,
    "wrt21.entity_gain_block": 0.08,
    "wrt22.entity_coverage_min": 0.70,
    "wrt22.entity_coverage_max": 0.90,
    "wrt23.ngram_n": 8,
    "wrt23.ngram_overlap_max": 0.03,
    "wrt24.cannibalization_cos_max": 0.85,
    "wrt25.site_drift_max": 0.45,
    "wrt26.words_per_claim_max": 250,
    "wrt30.time_to_answer_words_max": 60,
    "wrt31.passage_self_sufficiency_min": 0.90,
    "wrt33.first_third_core_coverage_min": 0.60,
    "wrt34.long_document_words": 1200,
    "wrt34.structural_variety_min": 2,
    "wrt40.sentence_length_sd_min": 6.0,
    "wrt41.mid_length_share_max": 0.65,
    "wrt42.uniform_paragraph_share_max": 0.60,
    "wrt43.repeated_opener_share_max": 0.12,
    "wrt44.ttr_min": 0.38,
    "wrt44.ttr_window_words": 500,
    "wrt45.consecutive_lists_max": 2,
    "wrt46.rule_of_three_share_max": 0.50,
    "volume_expectation.tolerance": 0.40,
    # Below this length a per-1000-words rate is arithmetic noise: a single occurrence in a
    # 120-word draft scores 8.3 per 1000 and trips a threshold of 5. That converts a density rule
    # into the presence rule it exists to avoid, which the pack contract calls its single most
    # important safeguard. Short drafts report the number and raise nothing.
    "lang.density_min_words": 300,
}

# Provenance of each threshold, so a finding can say whether the number behind it was measured by
# somebody or guessed by somebody. Everything unlisted is expert judgement pending calibration.
THRESHOLD_PROVENANCE: dict[str, str] = {
    "wrt11.sourced_share_min": "source: EVIDENCE.md#e11-content-quality-signals",
    "wrt11.sourced_share_min_ymyl": "source: EVIDENCE.md#e11-content-quality-signals",
    "wrt13.link_liveness_min": "source: [internal observation, unpublished], owner mandate",
    "wrt14.date_divergence_days_max": "expert judgement, needs calibration; basis: semanticDate in the leak",
    "wrt25.site_drift_max": "expert judgement, needs calibration; basis: siteRadius",
    "wrt40.sentence_length_sd_min": "expert judgement, needs calibration; EVIDENCE.md#e03-ai-detection-and-humanization",
    "wrt20.ocd_min": "expert judgement, needs calibration; EVIDENCE.md#e11-content-quality-signals",
}

UNIQUE_VALUE_KINDS = frozenset(
    {
        "first_party_data",
        "own_measurement",
        "interview",
        "own_calculation",
        "primary_source_analysis",
        "original_media",
        "proprietary_tool",
    }
)

ARTIFACT_KINDS = frozenset(
    {"export", "measurement", "interview", "survey", "calculation", "primary_reading", "original_media"}
)

BRIEF_REQUIRED_FIELDS = (
    "topic_id",
    "locale",
    "surface_type",
    "target",
    "answer_intent",
    "audience",
    "unique_value_source",
    "entity_map",
    "mandated_proof_sources",
    "cannibalization_check",
    "forbidden",
    "reviewers",
)

# Rules the specification assigns to an agent, wholly or in part. A rule listed here can be failed
# by code when code sees a hard violation, but it can never be passed by code alone.
AGENT_RULES = frozenset({"WRT-05", "WRT-10", "WRT-11", "WRT-15", "WRT-30", "WRT-31"})

# The composite gate, `05-writing-core.md` §3. WRT-20 and WRT-21 block only at their lower bound,
# which the rule implementations encode themselves.
BLOCKING_RULES = frozenset(
    {
        "WRT-01", "WRT-02", "WRT-03", "WRT-04", "WRT-05",
        "WRT-10", "WRT-11", "WRT-13", "WRT-15", "WRT-16", "WRT-17",
        "WRT-20", "WRT-21", "WRT-23", "WRT-24",
        "WRT-32",
        "WRT-50", "WRT-51", "WRT-52", "WRT-53",
        "WRT-60", "WRT-61", "WRT-62",
    }
)

# Group F, `05-writing-core.md` §3. Language-independent, near-zero false positive rate.
TOOL_MARKERS: tuple[tuple[str, str], ...] = (
    ("contentReference", r"contentReference"),
    ("oai_citation", r"oai_citation"),
    ("turn_search", r"turn\d+search\d+"),
    ("attributableIndex", r"attributableIndex"),
    ("cite_marker", r"\[cite:\s*\d+\]"),
    ("span_marker", r"\[span_\d+\]\(start_span\)"),
    ("grok_card", r"grok_card"),
    ("ppl_file_upload", r"ppl-ai-file-upload"),
    ("attached_file", r"attached_file"),
    ("writing_fence", r":::writing"),
)

GENERATOR_UTM = (
    r"utm_source=chatgpt\.com",
    r"utm_source=openai",
    r"utm_source=perplexity",
)

# Zero-width and formatting characters that carry no meaning in prose and survive copy-paste.
# U+00A0 is deliberately absent: a non-breaking space is legitimate typography.
INVISIBLE_CHARS = {
    "​": "ZERO WIDTH SPACE",
    "‌": "ZERO WIDTH NON-JOINER",
    "‍": "ZERO WIDTH JOINER",
    "⁠": "WORD JOINER",
    "﻿": "ZERO WIDTH NO-BREAK SPACE",
    " ": "NARROW NO-BREAK SPACE",
    "­": "SOFT HYPHEN",
    "⁡": "FUNCTION APPLICATION",
}

# A word-count requirement, in the shapes it actually takes. `volume_expectation` is exempt by
# name: the doctrine permits a forecast and forbids a target, and the difference is the field it
# is written in, not the number itself (§4).
WORD_COUNT_PATTERNS: tuple[tuple[str, str], ...] = (
    ("numeric_word_requirement", r"\b\d{3,6}\s*[-–—+]?\s*(?:\d{3,6})?\s*(?:words?|word-count)\b"),
    ("minimum_words", r"\b(?:min(?:imum)?|at least|no fewer than)\b[^.\n]{0,30}\bwords?\b"),
    ("optimal_length", r"\b(?:optimal|ideal|target|sweet spot)\b[^.\n]{0,30}\b(?:length|words?)\b"),
    ("word_count_phrase", r"\bword count\b"),
    ("cyrillic_word_requirement", r"\b\d{3,6}\s*[-–—+]?\s*(?:\d{3,6})?\s*(?:слів|слов|знаків|символів)\b"),
    ("cyrillic_minimum", r"\b(?:мінімум|минимум|не менше|не менее)\b[^.\n]{0,30}\b(?:слів|слов|знаків)\b"),
)

WORD_COUNT_KEYS = frozenset(
    {"min_words", "max_words", "target_words", "word_count", "word_count_target", "length_target", "min_length"}
)

# PCRE-style Unicode property classes appear in the language packs. Python's `re` does not support
# them, so they are rewritten rather than left to raise at compile time. A pack pattern that still
# fails to compile becomes a visible pack defect, never a silent skip.
PCRE_CLASS_MAP: tuple[tuple[str, str], ...] = (
    (r"\p{Cyrillic}", r"[Ѐ-ӿԀ-ԯ]"),
    (r"\p{Latin}", r"[A-Za-zÀ-ɏ]"),
    (r"\p{Lu}", r"[A-ZА-ЯЄІЇҐ]"),
    (r"\p{Ll}", r"[a-zа-яєіїґ]"),
    (r"\p{L}", r"[^\W\d_]"),
    (r"\p{N}", r"\d"),
)


# ---------------------------------------------------------------------------
# Named checks
# ---------------------------------------------------------------------------
#
# Some deterministic facts are properties of a token or a document, not of a character stream.
# Writing one as a regex anyway yields a rule that compiles, reviews cleanly and can never fire.
#
# The recorded case, live in the Ukrainian pack until 2026-08-07:
#
#     \b(?=\p{Cyrillic})(?=\p{Latin})\S+\b
#
# Two lookaheads at one position require a SINGLE CHARACTER to belong to two scripts at once. The
# pattern is well formed and its match set is empty, so the homoglyph check reported success on
# every document for as long as it shipped. A pack entry that needs such a check declares
# `named_check: <name>`; an unrecognised name is a pack defect and never a silent skip.

#: Maximal runs of letters. Digits, underscores, hyphens and punctuation split tokens, which is what
#: keeps legitimate compounds ("PDF-файл", "IT-компанія") from reading as script mixing.
_LETTER_RUN_RE = re.compile(r"[^\W\d_]+", re.UNICODE)
_CYRILLIC_RE = re.compile(r"[Ѐ-ӿԀ-ԯⷠ-ⷿꙀ-ꚟ]")
_LATIN_RE = re.compile(r"[A-Za-zÀ-ɏ]")


def check_mixed_script_token(text: str) -> list[tuple[int, str]]:
    """Words whose letters span both Cyrillic and Latin: homoglyph substitution.

    Latin `a e o p c x i y` are visually identical to their Cyrillic counterparts. A substituted
    character breaks search, anchor matching and deduplication while the word looks correct to a
    reader, which is why this is `deterministic` and may block.

    Detection is per token because that is what the fact is about. Hyphenated compounds are split
    first: `PDF-файл` and `IT-компанія` are ordinary Ukrainian and must stay quiet.
    """
    hits: list[tuple[int, str]] = []
    for m in _LETTER_RUN_RE.finditer(text):
        token = m.group(0)
        if len(token) < 2:
            continue
        if _CYRILLIC_RE.search(token) and _LATIN_RE.search(token):
            hits.append((m.start(), token))
    return hits


#: Registry resolved by `named_check:` in a language pack. A name absent from this table is a pack
#: defect reported through WRT-06, because a check that cannot run has to say so.
NAMED_CHECKS: dict[str, Callable[[str], list[tuple[int, str]]]] = {
    "mixed_script_token": check_mixed_script_token,
}


# ---------------------------------------------------------------------------
# Result model
# ---------------------------------------------------------------------------


@dataclass(slots=True)
class RuleResult:
    """One rule's verdict, in the shape `05-writing-core.md` §10 specifies for `score.json`.

    `status` is one of:
      pass            evaluated and satisfied
      fail            evaluated and violated
      requires_agent  the specification assigns this judgement to an agent; code did not decide
      requires_input  an input this rule needs was not supplied
      not_applicable  the rule does not apply to this draft, with a reason

    Only `pass` counts as passing. The other four are all "unknown", and a BLOCK rule sitting at
    unknown caps the verdict at REWORK.
    """

    id: str
    severity: str
    status: str
    computed_by: str
    value: Any = None
    threshold: Any = None
    evidence: list[str] = field(default_factory=list)
    thresholds_used: list[dict[str, Any]] = field(default_factory=list)
    reason: str = ""

    def as_record(self) -> dict[str, Any]:
        rec: dict[str, Any] = {
            "id": self.id,
            "severity": self.severity,
            "status": self.status,
            "computed_by": self.computed_by,
            "evidence": self.evidence[:10],
            "thresholds_used": self.thresholds_used,
        }
        if self.value is not None:
            rec["value"] = self.value
        if self.threshold is not None:
            rec["threshold"] = self.threshold
        if self.reason:
            rec["reason"] = self.reason
        return rec


@dataclass(slots=True)
class ScoreResult:
    verdict: str
    rules: list[RuleResult]
    blocked_by: list[str]
    unresolved: list[str]
    warnings_triggered: list[str]
    pack: dict[str, Any]
    stats: dict[str, Any]
    iteration: int = 1
    writer_model: str | None = None
    judge_model: str | None = None

    def as_record(self) -> dict[str, Any]:
        return {
            "verdict": self.verdict,
            "iteration": self.iteration,
            "writer_model": self.writer_model,
            "judge_model": self.judge_model,
            "blocked_by": sorted(self.blocked_by),
            "unresolved": sorted(self.unresolved),
            "warnings_triggered": sorted(self.warnings_triggered),
            "pack": self.pack,
            "stats": self.stats,
            "rules": [r.as_record() for r in sorted(self.rules, key=lambda r: stable_key(r.id))],
        }


# ---------------------------------------------------------------------------
# Language pack
# ---------------------------------------------------------------------------


@dataclass(slots=True)
class PackEntry:
    set_key: str
    term: str
    pattern: str
    match_mode: str
    risk: str | None
    status: str
    compiled: re.Pattern[str] | None
    compile_error: str = ""
    #: Name of a check resolved in code rather than by pattern. Mutually exclusive with `pattern`.
    named_check: str = ""
    #: Per-entry severity. Only ever a downgrade from the set ceiling; see `cap_pack_severity`.
    severity: str | None = None

    @property
    def is_deterministic(self) -> bool:
        return self.status == "deterministic"

    @property
    def runnable(self) -> bool:
        return self.compiled is not None or self.named_check in NAMED_CHECKS


@dataclass(slots=True)
class PackSet:
    key: str
    forbidden: bool
    declared_severity: str | None
    density_threshold: float | None
    applies_to: str
    never_inside: tuple[str, ...]
    entries: list[PackEntry]
    default_status: str | None = None
    #: `LANG-<LOCALE>-<NN>`, declared by the pack. Findings are counted per rule in
    #: `.kiln/rules-stats.json`, and an identifier invented here at runtime could not be counted:
    #: nothing outside this process would know it exists.
    rule_id: str = ""


@dataclass(slots=True)
class LanguagePack:
    code: str
    path: Path
    sets: dict[str, PackSet]
    defects: list[str]
    sha256: str

    def get(self, key: str) -> PackSet | None:
        return self.sets.get(key)


_YAML_FENCE = re.compile(r"^```ya?ml\s*$(.*?)^```\s*$", re.MULTILINE | re.DOTALL)


def _translate_pcre(pattern: str) -> str:
    """Rewrite PCRE Unicode property classes into Python-compatible equivalents.

    The packs are written for humans and use `\\p{L}` and `\\p{Cyrillic}`, which Python's `re`
    rejects outright. Rewriting is preferable to demanding pack authors learn Python's dialect,
    and the alternative — letting the compile fail — would silently drop a rule.
    """
    for pcre, py in PCRE_CLASS_MAP:
        pattern = pattern.replace(pcre, py)
    return pattern


def _compile_pack_pattern(pattern: str) -> tuple[re.Pattern[str] | None, str]:
    try:
        return re.compile(_translate_pcre(pattern), re.IGNORECASE | re.MULTILINE | re.UNICODE), ""
    except re.error as exc:
        return None, str(exc)


def _normalise_applies_to(raw: Any) -> str:
    """Map the pack's free-text scope descriptions onto the three scopes code can honour."""
    text = str(raw or "").strip().lower()
    if not text:
        return "document"
    if "first sentence" in text and "section" in text:
        return "section_first_sentence"
    if text == "section_first_sentence":
        return "section_first_sentence"
    if "final" in text and "%" in text:
        return "document_tail"
    if "heading" in text and "final" in text:
        return "document_tail"
    return "document"


def parse_language_pack(path: Path) -> LanguagePack:
    """Read the fenced YAML blocks out of `doctrine/lang/<code>.md`.

    A pack is a markdown document with machine-readable islands, deliberately: the prose around
    each set carries the reasoning, and separating them into two files is how the reasoning stops
    being read. Blocks that are not set declarations, such as the entry-schema example, are
    skipped rather than misparsed.
    """
    if not path.exists():
        raise KilnError(
            f"language pack not found: {path}. The locale declared in the brief has no pack. "
            f"Falling back to another language is forbidden (P5): a pack encodes one language's "
            f"vocabulary and syntax, and applying it to another damages correct text."
        )
    try:
        import yaml
    except ImportError as exc:  # pragma: no cover - environment problem
        raise KilnError("PyYAML is required to read language packs") from exc

    raw = path.read_text(encoding="utf-8")
    sha = hashlib.sha256(raw.encode("utf-8")).hexdigest()
    defects: list[str] = []
    sets: dict[str, PackSet] = {}

    for block in _YAML_FENCE.findall(raw):
        try:
            loaded = yaml.safe_load(block)
        except yaml.YAMLError as exc:
            defects.append(f"unparseable YAML block: {exc}")
            continue
        if not isinstance(loaded, dict):
            continue  # entry-schema examples and metadata fragments parse as lists or scalars
        for key, body in loaded.items():
            if not isinstance(body, dict):
                continue
            raw_entries = body.get("items")
            if raw_entries is None and "entries" in body:
                # A pack that renamed the contract key still parses and still looks complete, but
                # every consumer reading `items` receives nothing. Read it, and say so: the whole
                # class of defect is that it produces no error and no output.
                raw_entries = body.get("entries")
                defects.append(
                    f"set {key!r} lists its entries under `entries:`; the contract names the key "
                    f"`items:` (05-writing-core.md §6). Read anyway, but a consumer following the "
                    f"contract sees an empty set."
                )
            if raw_entries is None:
                continue  # not a set declaration
            if key in sets:
                defects.append(f"set {key!r} declared more than once; the later declaration wins")
            sets[key] = _build_set(key, body, raw_entries, defects)

    if not sets:
        raise KilnError(f"{path}: no language pack sets found. The pack is unusable.")

    for required in (
        "anaphora_openers",
        "hedge_phrases",
        "closing_formulas",
        "promo_lexicon",
        "vague_attribution",
        "generational_stopwords",
        "prescribed_phrases",
    ):
        if required not in sets:
            defects.append(f"required set {required!r} is missing (05-writing-core.md §6)")

    # A set claiming BLOCK while holding statistical entries is a contract violation, and it is the
    # violation that matters most: it is a language pack trying to hold a publication gate. The
    # entries are capped at scoring time regardless, but the pack must also be told it is wrong,
    # or the defect stays invisible until someone reads the file.
    for key in sorted(sets):
        pack_set = sets[key]
        if (pack_set.declared_severity or "").upper() != "BLOCK":
            continue
        offenders = sorted({e.term for e in pack_set.entries if not e.is_deterministic})
        if offenders:
            defects.append(
                f"set {key!r} declares BLOCK but holds {len(offenders)} non-deterministic "
                f"entr{'y' if len(offenders) == 1 else 'ies'} ({', '.join(offenders[:3])}"
                f"{', …' if len(offenders) > 3 else ''}). Only status: deterministic may block "
                f"(00-principles.md severity scale). Those entries were capped at WARN."
            )

    return LanguagePack(code=path.stem, path=path, sets=sets, defects=defects, sha256=sha)


def _build_set(key: str, body: dict[str, Any], raw_entries: Any, defects: list[str]) -> PackSet:
    if "forbidden" not in body:
        defects.append(f"set {key!r} does not declare `forbidden: true|false` (§6 contract)")
    declared = body.get("severity_ceiling", body.get("severity"))
    density = body.get("density_threshold_per_1000", body.get("density_warn_per_1000"))
    default_status = body.get("default_status")

    rule_id = str(body.get("rule_id") or "")
    if not rule_id:
        defects.append(
            f"set {key!r} declares no `rule_id` (§6 contract). Findings from it cannot be counted "
            f"in .kiln/rules-stats.json, so P8 has nothing to retire the rule on."
        )

    entries: list[PackEntry] = []
    for raw_entry in raw_entries if isinstance(raw_entries, list) else []:
        if not isinstance(raw_entry, dict):
            continue
        named = str(raw_entry.get("named_check") or "")
        pattern = raw_entry.get("match") or raw_entry.get("pattern") or raw_entry.get("phrase")
        term = str(raw_entry.get("phrase") or raw_entry.get("term") or pattern or named or "")
        status = raw_entry.get("status") or default_status
        if not status:
            defects.append(f"{key}: entry {term!r} resolves no status (§6 contract)")
            status = "hypothesis"
        severity = raw_entry.get("severity")

        compiled: re.Pattern[str] | None = None
        err = ""
        if named:
            if pattern and raw_entry.get("match"):
                defects.append(
                    f"{key}: entry {term!r} declares both `named_check` and `match`; they are "
                    f"mutually exclusive. The named check was used."
                )
            if named not in NAMED_CHECKS:
                # The point of the mechanism is that a check which cannot run says so. Skipping an
                # unknown name quietly would reproduce the dead-rule failure this replaced.
                defects.append(
                    f"{key}: entry {term!r} names an unknown check {named!r}. Known checks: "
                    f"{', '.join(sorted(NAMED_CHECKS))}. The entry did not run."
                )
        else:
            if not pattern:
                defects.append(f"{key}: entry {term!r} has neither a match pattern nor a named_check")
                continue
            compiled, err = _compile_pack_pattern(str(pattern))
            if err:
                defects.append(f"{key}: entry {term!r} has an uncompilable pattern and was skipped: {err}")

        entries.append(
            PackEntry(
                set_key=key,
                term=term,
                pattern="" if named else str(pattern),
                match_mode=str(raw_entry.get("match_mode") or ("named" if named else "phrase")),
                risk=raw_entry.get("risk"),
                status=str(status),
                compiled=compiled,
                compile_error=err,
                named_check=named,
                severity=str(severity).upper() if severity else None,
            )
        )

    return PackSet(
        key=key,
        forbidden=bool(body.get("forbidden", True)),
        declared_severity=str(declared) if declared else None,
        density_threshold=float(density) if isinstance(density, (int, float)) else None,
        applies_to=_normalise_applies_to(body.get("applies_to")),
        never_inside=tuple(body.get("never_applies_inside") or ()),
        entries=entries,
        default_status=str(default_status) if default_status else None,
        rule_id=rule_id,
    )


def cap_pack_severity(pack_set: PackSet, entry: PackEntry) -> str:
    """Enforce the WARN ceiling on language pack findings, in code.

    `00-principles.md` states that a language pack may not hold a publication gate, and grants one
    exception for `deterministic` entries: a letter that does not exist in the alphabet is a fact,
    not a stylometric score. The ceiling is applied here rather than read from the pack, because a
    pack that declares its own severity honestly today is not a guarantee about the pack somebody
    contributes next month.
    """
    declared = (pack_set.declared_severity or "WARN").upper()
    if declared == "BLOCK" and entry.is_deterministic:
        ceiling = "BLOCK"
    elif declared == "BLOCK":
        ceiling = "WARN"
    else:
        ceiling = declared if declared in {"WARN", "INFO"} else "WARN"

    # An entry may lower its own severity below the set ceiling, never raise it. A set that
    # collects orthographic facts can still hold one entry that is merely a typographic
    # preference, and the alternative is prose saying "WARN, not BLOCK" beside a field the
    # machine reads as BLOCK. Prose that disagrees with the field is prose nothing enforces.
    order = {"INFO": 0, "WARN": 1, "BLOCK": 2}
    if entry.severity in order and order[entry.severity] < order[ceiling]:
        return entry.severity
    return ceiling


# ---------------------------------------------------------------------------
# Draft parsing
# ---------------------------------------------------------------------------


@dataclass(slots=True)
class Section:
    heading: str
    level: int
    body: str
    start_word: int


@dataclass(slots=True)
class Draft:
    raw: str
    text: str  # prose only: code fences, tables and blockquotes removed
    sections: list[Section]
    paragraphs: list[str]
    sentences: list[str]
    headings: list[tuple[int, str]]
    lists: list[list[str]]
    has_table: bool
    is_html: bool
    protected_spans: list[tuple[int, int]]

    @property
    def words(self) -> int:
        return count_words(self.text)


_FENCE_RE = re.compile(r"```.*?```", re.DOTALL)
_INLINE_CODE_RE = re.compile(r"`[^`\n]+`")
_HTML_TAG_RE = re.compile(r"<[^>]+>")
_HEADING_RE = re.compile(r"^(#{1,6})\s+(.*?)\s*$", re.MULTILINE)
_LIST_ITEM_RE = re.compile(r"^\s*(?:[-*+]|\d+[.)])\s+(.*)$")
_TABLE_ROW_RE = re.compile(r"^\s*\|.*\|\s*$", re.MULTILINE)
_BLOCKQUOTE_RE = re.compile(r"^\s*>.*$", re.MULTILINE)
_QUOTED_SPAN_RE = re.compile(r"«[^»]{2,}»|„[^“”]{2,}[“”]|\"[^\"\n]{2,}\"|“[^”]{2,}”")


def parse_draft(raw: str, filename: str = "") -> Draft:
    """Split a draft into the units the rules operate on.

    Everything downstream measures prose, so code fences, tables and blockquotes come out first.
    A table counts toward structural variety (WRT-34) but its cells are not sentences, and letting
    them through inflates sentence-length variance in a way that looks like healthy rhythm.
    """
    is_html = filename.lower().endswith((".html", ".htm")) or bool(re.search(r"<(p|div|article|h[1-6])\b", raw, re.I))
    text = raw

    protected: list[tuple[int, int]] = []
    for match in _FENCE_RE.finditer(raw):
        protected.append(match.span())
    for match in _INLINE_CODE_RE.finditer(raw):
        protected.append(match.span())
    for match in _BLOCKQUOTE_RE.finditer(raw):
        protected.append(match.span())
    for match in _QUOTED_SPAN_RE.finditer(raw):
        protected.append(match.span())

    has_table = bool(_TABLE_ROW_RE.search(raw))

    prose = _FENCE_RE.sub("\n", text)
    prose = _TABLE_ROW_RE.sub("", prose)
    prose = _BLOCKQUOTE_RE.sub("", prose)
    if is_html:
        prose = _HTML_TAG_RE.sub(" ", prose)
    prose = normalize_text(prose)

    headings = [(len(m.group(1)), m.group(2).strip()) for m in _HEADING_RE.finditer(raw)]

    sections: list[Section] = []
    cursor = 0
    matches = list(_HEADING_RE.finditer(raw))
    if matches and matches[0].start() > 0:
        lead = raw[: matches[0].start()]
        sections.append(Section("", 0, lead, 0))
        cursor = count_words(lead)
    for i, m in enumerate(matches):
        end = matches[i + 1].start() if i + 1 < len(matches) else len(raw)
        body = raw[m.end() : end]
        sections.append(Section(m.group(2).strip(), len(m.group(1)), body, cursor))
        cursor += count_words(body)
    if not sections:
        sections.append(Section("", 0, raw, 0))

    paragraphs = [p.strip() for p in re.split(r"\n\s*\n", prose) if p.strip()]

    lists: list[list[str]] = []
    current: list[str] = []
    for line in raw.splitlines():
        item = _LIST_ITEM_RE.match(line)
        if item:
            current.append(item.group(1).strip())
        elif current:
            lists.append(current)
            current = []
    if current:
        lists.append(current)

    prose_no_lists = "\n".join(l for l in prose.splitlines() if not _LIST_ITEM_RE.match(l))
    sentences = split_sentences(prose_no_lists)

    return Draft(
        raw=raw,
        text=prose,
        sections=sections,
        paragraphs=paragraphs,
        sentences=sentences,
        headings=headings,
        lists=lists,
        has_table=has_table,
        is_html=is_html,
        protected_spans=sorted(protected),
    )


def _in_protected_span(pos: int, spans: Sequence[tuple[int, int]]) -> bool:
    return any(start <= pos < end for start, end in spans)


# ---------------------------------------------------------------------------
# Scoring helpers
# ---------------------------------------------------------------------------


class Scorer:
    """Accumulates rule results while tracking which thresholds each rule actually read."""

    def __init__(self, thresholds: Thresholds) -> None:
        self.thresholds = thresholds
        self.results: list[RuleResult] = []

    def threshold(self, key: str) -> Any:
        return self.thresholds.get(key, note=THRESHOLD_PROVENANCE.get(key, "expert judgement, needs calibration"))

    def begin(self) -> None:
        self.thresholds.reset_usage()

    def record(
        self,
        rule_id: str,
        severity: str,
        status: str,
        computed_by: str = "code",
        value: Any = None,
        threshold: Any = None,
        evidence: Iterable[str] = (),
        reason: str = "",
    ) -> RuleResult:
        result = RuleResult(
            id=rule_id,
            severity=severity,
            status=status,
            computed_by=computed_by,
            value=value,
            threshold=threshold,
            evidence=list(evidence),
            thresholds_used=self.thresholds.used(),
            reason=reason,
        )
        self.results.append(result)
        self.thresholds.reset_usage()
        return result


def _entity_tokens(entity: str) -> tuple[str, ...]:
    return tuple(tokenize_words(entity))


def _entity_present(entity_tokens: tuple[str, ...], doc_tokens: Sequence[str]) -> bool:
    """Sequence match over Unicode tokens.

    Deliberately not a regex with `\\b`: word boundaries are not reliable for Cyrillic, and the
    Ukrainian pack forbids that construction outright. Matching token sequences sidesteps the
    problem entirely and behaves identically in every script.
    """
    n = len(entity_tokens)
    if n == 0:
        return False
    for i in range(len(doc_tokens) - n + 1):
        if tuple(doc_tokens[i : i + n]) == entity_tokens:
            return True
    return False


def _ngrams(tokens: Sequence[str], n: int) -> set[tuple[str, ...]]:
    if len(tokens) < n:
        return set()
    return {tuple(tokens[i : i + n]) for i in range(len(tokens) - n + 1)}


def _parse_date(value: Any) -> tuple[int, int, int] | None:
    if not value:
        return None
    text = str(value)[:10]
    m = re.match(r"^(\d{4})-(\d{2})-(\d{2})$", text)
    if not m:
        return None
    return int(m.group(1)), int(m.group(2)), int(m.group(3))


def _days_between(a: tuple[int, int, int], b: tuple[int, int, int]) -> int:
    """Whole days between two calendar dates, without importing a clock.

    Layer 2 scripts must be deterministic, so nothing here reads the current time. Every date
    comparison is between two dates supplied in the inputs.
    """
    import datetime

    return abs((datetime.date(*a) - datetime.date(*b)).days)


def _iter_strings(obj: Any, path: str = "") -> Iterable[tuple[str, str]]:
    if isinstance(obj, str):
        yield path, obj
    elif isinstance(obj, dict):
        for k, v in obj.items():
            yield from _iter_strings(v, f"{path}.{k}" if path else str(k))
    elif isinstance(obj, (list, tuple)):
        for i, v in enumerate(obj):
            yield from _iter_strings(v, f"{path}[{i}]")


def _checksum_doi(doi: str) -> bool:
    """A DOI has no checksum; validity here means structural validity of the prefix and suffix."""
    return bool(re.match(r"^10\.\d{4,9}/\S+$", doi.strip()))


def _checksum_isbn(isbn: str) -> bool:
    digits = re.sub(r"[^0-9Xx]", "", isbn)
    if len(digits) == 10:
        total = sum((10 - i) * (10 if c in "Xx" else int(c)) for i, c in enumerate(digits))
        return total % 11 == 0
    if len(digits) == 13:
        total = sum((1 if i % 2 == 0 else 3) * int(c) for i, c in enumerate(digits))
        return total % 10 == 0
    return False


# ---------------------------------------------------------------------------
# Rule groups
# ---------------------------------------------------------------------------


def score_group_a(sc: Scorer, brief: dict[str, Any], artifacts_dir: Path | None) -> None:
    """Input and intent. Everything here is cheap and everything here blocks."""
    missing = [f for f in BRIEF_REQUIRED_FIELDS if brief.get(f) in (None, "", [], {})]
    sc.record(
        "WRT-01",
        "BLOCK",
        "fail" if missing else "pass",
        value=len(BRIEF_REQUIRED_FIELDS) - len(missing),
        threshold=len(BRIEF_REQUIRED_FIELDS),
        evidence=[f"missing required brief field: {f}" for f in sorted(missing)],
    )

    uvs = brief.get("unique_value_source")
    uvs_problems: list[str] = []
    if not isinstance(uvs, dict):
        uvs_problems.append("unique_value_source is absent or not a mapping")
    else:
        kind = uvs.get("kind")
        if kind not in UNIQUE_VALUE_KINDS:
            uvs_problems.append(f"kind {kind!r} is not one of {sorted(UNIQUE_VALUE_KINDS)}")
        if not str(uvs.get("description") or "").strip():
            uvs_problems.append("description is empty")
    sc.record("WRT-02", "BLOCK", "fail" if uvs_problems else "pass", evidence=uvs_problems)

    # WRT-03: the effort gate (§5). Code verifies attachment and integrity, never authenticity.
    artifact_id = (uvs or {}).get("artifact_id") if isinstance(uvs, dict) else None
    if not artifact_id:
        sc.record("WRT-03", "BLOCK", "fail", evidence=["unique_value_source carries no artifact_id (§5.1)"])
    elif artifacts_dir is None:
        sc.record("WRT-03", "BLOCK", "requires_input", reason="artifacts directory not supplied")
    else:
        problems = _validate_artifact(artifacts_dir, str(artifact_id))
        sc.record("WRT-03", "BLOCK", "fail" if problems else "pass", value=str(artifact_id), evidence=problems)

    # WRT-04: no word-count requirement anywhere in the brief. `volume_expectation` is exempt.
    hits: list[str] = []
    for key in brief:
        if key in WORD_COUNT_KEYS:
            hits.append(f"brief declares a length target field: {key}")
    for path, value in _iter_strings(brief):
        if path.split(".")[0] == "volume_expectation":
            continue
        for name, pattern in WORD_COUNT_PATTERNS:
            m = re.search(pattern, value, re.IGNORECASE)
            if m:
                hits.append(f"{path}: {name}: {m.group(0)!r}")
    sc.record(
        "WRT-04",
        "BLOCK",
        "fail" if hits else "pass",
        value=len(hits),
        threshold=0,
        evidence=hits,
        reason="" if hits else "no length requirement found; volume_expectation is exempt as a forecast (§4)",
    )

    sc.record(
        "WRT-05",
        "BLOCK",
        "requires_agent",
        computed_by="agent",
        reason="taboo violation is a binary judgement for the agent (§7); code cannot decide it",
    )


def _validate_artifact(artifacts_dir: Path, artifact_id: str) -> list[str]:
    """Check the artefact manifest: existence, hash, human authorship, referenced files (§5.3)."""
    problems: list[str] = []
    candidates = [artifacts_dir / artifact_id / "manifest.yml", artifacts_dir / f"{artifact_id}.yml"]
    manifest_path = next((p for p in candidates if p.exists()), None)
    if manifest_path is None:
        return [f"no manifest for artifact {artifact_id!r} under {artifacts_dir}"]
    try:
        import yaml

        manifest = yaml.safe_load(manifest_path.read_text(encoding="utf-8")) or {}
    except Exception as exc:  # noqa: BLE001 - a malformed manifest is a finding, not a crash
        return [f"{manifest_path}: unreadable manifest: {exc}"]
    if not isinstance(manifest, dict):
        return [f"{manifest_path}: manifest is not a mapping"]

    if manifest.get("kind") not in ARTIFACT_KINDS:
        problems.append(f"artifact kind {manifest.get('kind')!r} is not one of {sorted(ARTIFACT_KINDS)}")
    created_by = str(manifest.get("created_by") or "")
    if not created_by or created_by.lower().startswith("agent"):
        problems.append("created_by must name a human; an agent cannot originate first-party material (§5.3)")
    if not str(manifest.get("method") or "").strip():
        problems.append("method is empty: how the material was obtained must be stated")

    files = manifest.get("files") or []
    hashes = manifest.get("sha256") or []
    if isinstance(hashes, str):
        hashes = [hashes]
    if not files:
        problems.append("manifest lists no files")
    for i, rel in enumerate(files):
        target = (manifest_path.parent / str(rel)).resolve() if not Path(str(rel)).is_absolute() else Path(str(rel))
        if not target.exists():
            alt = (artifacts_dir.parent.parent / str(rel)).resolve()
            target = alt if alt.exists() else target
        if not target.exists():
            problems.append(f"artifact file missing: {rel}")
            continue
        if i < len(hashes):
            actual = hashlib.sha256(target.read_bytes()).hexdigest()
            if actual != str(hashes[i]).strip().lower():
                problems.append(f"sha256 mismatch for {rel}: manifest says {hashes[i]}, file is {actual}")
    return problems


def score_group_b(sc: Scorer, draft: Draft, brief: dict[str, Any], packet: dict[str, Any]) -> None:
    """Claim provenance. This is P1 made executable."""
    claims: list[dict[str, Any]] = [c for c in packet.get("claims", []) if isinstance(c, dict)]
    ymyl = bool(brief.get("ymyl")) or str(brief.get("surface_type", "")).lower() in {"ymyl"}

    cited_ids = set(re.findall(r"\[\[claim:([A-Za-z0-9_\-]+)\]\]|\{claim:([A-Za-z0-9_\-]+)\}", draft.raw))
    used_claim_ids = {a or b for a, b in cited_ids} if cited_ids else set()
    if not used_claim_ids:
        used_claim_ids = set(re.findall(r"\bclaim:([A-Za-z0-9_\-]+)", draft.raw))

    known_ids = {str(c.get("id")) for c in claims if c.get("id")}
    dangling = sorted(used_claim_ids - known_ids)
    sc.record(
        "WRT-10",
        "BLOCK",
        "fail" if dangling else "requires_agent",
        computed_by="code + agent",
        value=len(used_claim_ids),
        evidence=[f"draft cites unknown claim id: {cid}" for cid in dangling],
        reason=""
        if dangling
        else "markup is consistent; whether an unbound factual claim remains is the agent's question (§7)",
    )

    factual = [c for c in claims if c.get("kind") in {"fact", "figure", "quote", "definition"}]
    sourced = [c for c in factual if str(c.get("source_url") or "").strip()]
    share = len(sourced) / len(factual) if factual else None
    minimum = sc.threshold("wrt11.sourced_share_min_ymyl" if ymyl else "wrt11.sourced_share_min")
    if share is None:
        sc.record("WRT-11", "BLOCK", "requires_input", computed_by="code + agent", reason="packet holds no factual claims")
    elif share + 1e-9 < minimum:
        sc.record(
            "WRT-11",
            "BLOCK",
            "fail",
            computed_by="code + agent",
            value=round(share, 4),
            threshold=minimum,
            evidence=[f"claim {c.get('id')} has no source_url" for c in factual if c not in sourced][:10],
        )
    else:
        sc.record(
            "WRT-11",
            "BLOCK",
            "requires_agent",
            computed_by="code + agent",
            value=round(share, 4),
            threshold=minimum,
            reason="every claim the packet marks factual carries a source; which sentences are factual is the agent's question",
        )

    all_sources = [c for c in claims if c.get("source_url")]
    primary = [c for c in all_sources if str(c.get("source_tier", "")).lower() == "primary"]
    psr = len(primary) / len(all_sources) if all_sources else None
    psr_min = sc.threshold("wrt12.primary_source_ratio_min")
    sc.record(
        "WRT-12",
        "WARN",
        "requires_input" if psr is None else ("fail" if psr + 1e-9 < psr_min else "pass"),
        value=None if psr is None else round(psr, 4),
        threshold=psr_min,
        reason="no sourced claims in the packet" if psr is None else "",
    )

    statuses = [c.get("http_status") for c in all_sources]
    checked = [s for s in statuses if isinstance(s, int)]
    dead = [c for c in all_sources if isinstance(c.get("http_status"), int) and not 200 <= c["http_status"] < 300]
    liveness = (len(checked) - len(dead)) / len(checked) if checked else None
    live_min = sc.threshold("wrt13.link_liveness_min")
    if liveness is None:
        sc.record("WRT-13", "BLOCK", "requires_input", reason="no http_status recorded in the packet")
    else:
        unchecked = len(all_sources) - len(checked)
        sc.record(
            "WRT-13",
            "BLOCK",
            "fail" if (dead or unchecked) else "pass",
            value=round(liveness, 4),
            threshold=live_min,
            evidence=[f"claim {c.get('id')}: HTTP {c.get('http_status')} for {c.get('source_url')}" for c in dead][:10]
            + ([f"{unchecked} source(s) carry no http_status"] if unchecked else []),
        )

    byline = _parse_date(brief.get("byline_date") or packet.get("created_at"))
    semantic_dates = [d for d in (_parse_date(c.get("source_published_at")) for c in claims) if d]
    max_div = sc.threshold("wrt14.date_divergence_days_max")
    if byline and semantic_dates:
        newest = max(semantic_dates)
        divergence = _days_between(byline, newest)
        sc.record(
            "WRT-14",
            "WARN",
            "fail" if divergence > max_div else "pass",
            value=divergence,
            threshold=max_div,
            evidence=[f"byline {byline} against newest source {newest}"],
        )
    else:
        sc.record("WRT-14", "WARN", "requires_input", reason="byline date or source dates missing")

    volatile = [c for c in claims if c.get("volatile") is True]
    age_max = sc.threshold("wrt15.volatile_source_age_days_max")
    stale: list[str] = []
    fetched = _parse_date(packet.get("created_at"))
    for c in volatile:
        published = _parse_date(c.get("source_published_at"))
        if published and fetched:
            age = _days_between(fetched, published)
            if age > age_max:
                stale.append(f"claim {c.get('id')}: source is {age} days old, limit is {age_max}")
    sc.record(
        "WRT-15",
        "BLOCK",
        "fail" if stale else "requires_agent",
        computed_by="code + agent",
        threshold=age_max,
        evidence=stale,
        reason="" if stale else "which values can change within a month is the agent's question (§7)",
    )

    mandated = {str(x) for x in (brief.get("mandated_proof_sources") or [])}
    missing_mandated = sorted(mandated - used_claim_ids) if mandated else []
    sc.record(
        "WRT-16",
        "BLOCK",
        "fail" if missing_mandated else "pass",
        value=len(mandated - set(missing_mandated)),
        threshold=len(mandated),
        evidence=[f"mandated claim not cited in the draft: {cid}" for cid in missing_mandated],
    )

    bad_ids: list[str] = []
    for m in re.finditer(r"\b10\.\d{4,9}/\S+", draft.text):
        if not _checksum_doi(m.group(0)):
            bad_ids.append(f"malformed DOI: {m.group(0)}")
    for m in re.finditer(r"\bISBN[:\s]*([0-9][0-9\-\s]{8,20}[0-9Xx])", draft.text, re.IGNORECASE):
        if not _checksum_isbn(m.group(1)):
            bad_ids.append(f"ISBN fails checksum: {m.group(1).strip()}")
    sc.record("WRT-17", "BLOCK", "fail" if bad_ids else "pass", value=len(bad_ids), threshold=0, evidence=bad_ids)


def score_group_c(
    sc: Scorer,
    draft: Draft,
    brief: dict[str, Any],
    packet: dict[str, Any],
    top_docs: dict[str, str],
    corpus: dict[str, Any] | None,
) -> None:
    """Gain and originality. This is the group that separates Kiln from a similarity optimizer."""
    claims = [c for c in packet.get("claims", []) if isinstance(c, dict)]
    words = draft.words
    first_party = [c for c in claims if str(c.get("provenance", "")).lower() == "first_party" and c.get("artifact_id")]
    ocd = (len(first_party) / (words / 1000)) if words else 0.0
    ocd_min = sc.threshold("wrt20.ocd_min")
    if not first_party:
        sc.record(
            "WRT-20",
            "BLOCK",
            "fail",
            value=0.0,
            threshold=ocd_min,
            evidence=["no first_party claim carries an artifact_id; OCD is 0, which blocks (§5.1)"],
        )
    else:
        sc.record(
            "WRT-20",
            "WARN",
            "fail" if ocd + 1e-9 < ocd_min else "pass",
            value=round(ocd, 3),
            threshold=ocd_min,
            evidence=[f"{len(first_party)} first-party claims over {words} words"],
        )

    entity_map = brief.get("entity_map") or packet.get("entity_map") or {}
    top_corpus = [d for d in packet.get("top_corpus", []) if isinstance(d, dict)]
    known_entities = sorted(
        {
            str(e)
            for key in ("core", "ours", "absent_ok")
            for e in (entity_map.get(key) or [])
            if str(e).strip()
        }
    )
    top_entity_sets = [{str(e) for e in (d.get("entities") or [])} for d in top_corpus]
    top_entities = set().union(*top_entity_sets) if top_entity_sets else set()

    if top_entity_sets:
        need = len(top_entity_sets) / 2
        core_entities = sorted({e for e in top_entities if sum(e in s for s in top_entity_sets) >= need})
    else:
        core_entities = sorted({str(e) for e in (entity_map.get("core") or [])})

    doc_tokens = tokenize_words(draft.text)
    universe = sorted(set(known_entities) | top_entities | set(core_entities))
    present = [e for e in universe if _entity_present(_entity_tokens(e), doc_tokens)]

    eg_warn = sc.threshold("wrt21.entity_gain_warn")
    eg_block = sc.threshold("wrt21.entity_gain_block")
    if not present:
        sc.record("WRT-21", "BLOCK", "requires_input", reason="no known entity occurs in the draft; entity map may be empty")
    else:
        gain = len([e for e in present if e not in top_entities]) / len(present)
        if gain + 1e-9 < eg_block:
            sc.record("WRT-21", "BLOCK", "fail", value=round(gain, 4), threshold=eg_block,
                      evidence=["entity gain below the blocking floor: the draft adds almost nothing the top does not have"])
        elif gain + 1e-9 < eg_warn:
            sc.record("WRT-21", "WARN", "fail", value=round(gain, 4), threshold=eg_warn)
        else:
            sc.record("WRT-21", "WARN", "pass", value=round(gain, 4), threshold=eg_warn)

    ec_min = sc.threshold("wrt22.entity_coverage_min")
    ec_max = sc.threshold("wrt22.entity_coverage_max")
    if not core_entities:
        sc.record("WRT-22", "WARN", "requires_input", reason="no core entities available from the packet")
        coverage = None
    else:
        covered = [e for e in core_entities if e in present]
        coverage = len(covered) / len(core_entities)
        if coverage + 1e-9 < ec_min:
            sc.record("WRT-22", "WARN", "fail", value=round(coverage, 4), threshold=ec_min,
                      evidence=[f"core entity absent: {e}" for e in core_entities if e not in present][:10],
                      reason="topic is under-covered")
        elif coverage - 1e-9 > ec_max:
            sc.record("WRT-22", "WARN", "fail", value=round(coverage, 4), threshold=ec_max,
                      reason="over-optimization: coverage this high means the top has been paraphrased (§3, P13)")
        else:
            sc.record("WRT-22", "WARN", "pass", value=round(coverage, 4), threshold=[ec_min, ec_max])

    n = int(sc.threshold("wrt23.ngram_n"))
    ngo_max = sc.threshold("wrt23.ngram_overlap_max")
    if not top_docs:
        sc.record("WRT-23", "BLOCK", "requires_input", reason="no top-N corpus supplied (--top)")
    else:
        draft_grams = _ngrams(doc_tokens, n)
        if not draft_grams:
            sc.record("WRT-23", "BLOCK", "not_applicable", reason=f"draft is shorter than {n} words")
        else:
            per_doc: list[tuple[float, str, list[str]]] = []
            for name in sorted(top_docs):
                other = _ngrams(tokenize_words(top_docs[name]), n)
                shared = draft_grams & other
                per_doc.append(
                    (len(shared) / len(draft_grams), name, [" ".join(g) for g in sorted(shared)[:3]])
                )
            worst = max(per_doc, key=lambda x: (x[0], x[1]))
            sc.record(
                "WRT-23",
                "BLOCK",
                "fail" if worst[0] - 1e-9 > ngo_max else "pass",
                value=round(worst[0], 4),
                threshold=ngo_max,
                evidence=[f"highest overlap against {worst[1]}"] + [f"shared {n}-gram: {s}" for s in worst[2]],
                reason="sibling locales of the same project must be excluded from the comparison corpus (§11-4)",
            )

    cann = brief.get("cannibalization_check") or {}
    cos_max = sc.threshold("wrt24.cannibalization_cos_max")
    max_cos = cann.get("max_cosine") if isinstance(cann, dict) else None
    if not isinstance(max_cos, (int, float)):
        sc.record("WRT-24", "BLOCK", "fail",
                  evidence=["brief carries no cannibalization_check.max_cosine; the stage-2 check did not run (§3)"])
    else:
        decision = str(cann.get("decision") or "")
        failing = max_cos - 1e-9 > cos_max
        sc.record(
            "WRT-24",
            "BLOCK",
            "fail" if failing else "pass",
            value=round(float(max_cos), 4),
            threshold=cos_max,
            evidence=[f"nearest existing page: {cann.get('nearest_url')}", f"stage-2 decision: {decision}"],
            reason="above this the correct outcome is extend_existing, not a new page" if failing else "",
        )

    drift_max = sc.threshold("wrt25.site_drift_max")
    drift = (corpus or {}).get("draft_centroid_distance")
    if isinstance(drift, (int, float)):
        sc.record("WRT-25", "WARN", "fail" if drift - 1e-9 > drift_max else "pass",
                  value=round(float(drift), 4), threshold=drift_max)
    else:
        sc.record("WRT-25", "WARN", "requires_input",
                  reason="corpus centroid distance not supplied; needs embeddings computed outside this script")

    total_claims = len(claims)
    wpc_max = sc.threshold("wrt26.words_per_claim_max")
    if total_claims:
        wpc = words / total_claims
        sc.record("WRT-26", "WARN", "fail" if wpc - 1e-9 > wpc_max else "pass",
                  value=round(wpc, 1), threshold=wpc_max,
                  evidence=[f"{words} words carrying {total_claims} claims"])
    else:
        sc.record("WRT-26", "WARN", "requires_input", reason="packet holds no claims")


def score_group_d(sc: Scorer, draft: Draft, packet: dict[str, Any], pack: LanguagePack, core_present: Sequence[str],
                  core_entities: Sequence[str]) -> None:
    """Structure and extractability."""
    sc.record("WRT-30", "WARN", "requires_agent", computed_by="code + agent",
              threshold=sc.threshold("wrt30.time_to_answer_words_max"),
              reason="which sentence answers the intent is the agent's binary question (§7)")
    sc.record("WRT-31", "WARN", "requires_agent", computed_by="agent",
              threshold=sc.threshold("wrt31.passage_self_sufficiency_min"),
              reason="paragraph comprehensibility without context is judged by the agent, one paragraph at a time")

    # WRT-32. The severity is BLOCK because the core doctrine says so, not because the pack claims
    # authority to block. The pack supplies the word list; the rule belongs to the core.
    anaphora = pack.get("anaphora_openers")
    hits: list[str] = []
    if anaphora is None:
        sc.record("WRT-32", "BLOCK", "requires_input", reason="language pack declares no anaphora_openers set")
    else:
        for section in draft.sections:
            if not section.heading:
                continue
            first = next((s for s in split_sentences(section.body) if s.strip()), "")
            if not first:
                continue
            for entry in anaphora.entries:
                if entry.compiled and entry.compiled.search(first):
                    hits.append(f"section {section.heading!r} opens with {entry.term!r}: {first[:90]}")
                    break
        sc.record("WRT-32", "BLOCK", "fail" if hits else "pass", computed_by="code + lang pack",
                  value=len(hits), threshold=0, evidence=hits)

    first_third_min = sc.threshold("wrt33.first_third_core_coverage_min")
    if core_entities:
        cut = max(1, int(len(tokenize_words(draft.text)) * 0.30))
        head_tokens = tokenize_words(draft.text)[:cut]
        in_head = [e for e in core_entities if _entity_present(_entity_tokens(e), head_tokens)]
        share = len(in_head) / len(core_entities)
        sc.record("WRT-33", "WARN", "fail" if share + 1e-9 < first_third_min else "pass",
                  value=round(share, 4), threshold=first_third_min)
    else:
        sc.record("WRT-33", "WARN", "requires_input", reason="no core entities available")

    long_doc = sc.threshold("wrt34.long_document_words")
    variety_min = int(sc.threshold("wrt34.structural_variety_min"))
    block_types: list[str] = []
    if draft.has_table:
        block_types.append("table")
    if any(re.match(r"^\s*\d+[.)]\s+", item) for group in draft.lists for item in [group[0]] if group):
        block_types.append("numbered_procedure")
    if re.search(r"\$\$|\\\[|^\s*\|\s*[-=+*/]\s*\|", draft.raw, re.MULTILINE) or re.search(
        r"\b\d+\s*[×x*/]\s*\d+\s*=\s*\d+", draft.raw
    ):
        block_types.append("calculation")
    if re.search(r"!\[[^\]]*\]\([^)]+\)|<img\b|```mermaid", draft.raw):
        block_types.append("original_media")
    if draft.words <= long_doc:
        sc.record("WRT-34", "WARN", "not_applicable", value=len(block_types),
                  reason=f"document is {draft.words} words; the rule applies above {long_doc}")
    else:
        sc.record("WRT-34", "WARN", "fail" if len(block_types) < variety_min else "pass",
                  value=len(block_types), threshold=variety_min, evidence=sorted(block_types))

    skips: list[str] = []
    previous = 0
    for level, title in draft.headings:
        if previous and level > previous + 1:
            skips.append(f"H{previous} to H{level} at {title!r}")
        previous = level
    sc.record("WRT-35", "WARN", "fail" if skips else "pass", value=len(skips), threshold=0, evidence=skips)


def score_group_e(sc: Scorer, draft: Draft) -> None:
    """Form statistics. Secondary diagnostics, never a gate (§11-2).

    Every rule here is WARN by construction. If a habit of tuning drafts to hit these numbers ever
    appears, the metrics have become the optimization target P3 forbids and must be withdrawn
    rather than defended.
    """
    lengths = [count_words(s) for s in draft.sentences]
    sd_min = sc.threshold("wrt40.sentence_length_sd_min")
    if len(lengths) >= 3:
        sd = statistics.pstdev(lengths)
        sc.record("WRT-40", "WARN", "fail" if sd + 1e-9 < sd_min else "pass", value=round(sd, 2), threshold=sd_min)
    else:
        sc.record("WRT-40", "WARN", "requires_input", reason="fewer than three sentences")

    mid_max = sc.threshold("wrt41.mid_length_share_max")
    if lengths:
        share = sum(1 for n in lengths if 12 <= n <= 22) / len(lengths)
        sc.record("WRT-41", "WARN", "fail" if share - 1e-9 > mid_max else "pass", value=round(share, 4), threshold=mid_max)
    else:
        sc.record("WRT-41", "WARN", "requires_input", reason="no sentences")

    uni_max = sc.threshold("wrt42.uniform_paragraph_share_max")
    para_sentences = [len(split_sentences(p)) for p in draft.paragraphs]
    if len(para_sentences) >= 3:
        mode = statistics.mode(para_sentences)
        share = sum(1 for n in para_sentences if abs(n - mode) <= 1) / len(para_sentences)
        sc.record("WRT-42", "WARN", "fail" if share - 1e-9 > uni_max else "pass", value=round(share, 4), threshold=uni_max)
    else:
        sc.record("WRT-42", "WARN", "requires_input", reason="fewer than three paragraphs")

    rep_max = sc.threshold("wrt43.repeated_opener_share_max")
    openers = [" ".join(tokenize_words(s)[:2]) for s in draft.sentences if count_words(s) >= 2]
    if len(openers) >= 5:
        counts: dict[str, int] = {}
        for o in openers:
            counts[o] = counts.get(o, 0) + 1
        repeated = sum(c for c in counts.values() if c > 1)
        share = repeated / len(openers)
        worst = sorted(counts.items(), key=lambda kv: (-kv[1], kv[0]))[:3]
        sc.record("WRT-43", "WARN", "fail" if share - 1e-9 > rep_max else "pass", value=round(share, 4),
                  threshold=rep_max, evidence=[f"{o!r} opens {c} sentences" for o, c in worst if c > 1])
    else:
        sc.record("WRT-43", "WARN", "requires_input", reason="fewer than five sentences")

    ttr_min = sc.threshold("wrt44.ttr_min")
    window = int(sc.threshold("wrt44.ttr_window_words"))
    tokens = tokenize_words(draft.text)
    if tokens:
        chunks = [tokens[i : i + window] for i in range(0, len(tokens), window)] or [tokens]
        ratios = [len(set(c)) / len(c) for c in chunks if len(c) >= min(window, 50)] or [len(set(tokens)) / len(tokens)]
        worst_ttr = min(ratios)
        sc.record("WRT-44", "WARN", "fail" if worst_ttr + 1e-9 < ttr_min else "pass",
                  value=round(worst_ttr, 4), threshold=ttr_min,
                  evidence=[f"{len(ratios)} window(s) of {window} words; mean {round(sum(ratios)/len(ratios), 4)}"])
    else:
        sc.record("WRT-44", "WARN", "requires_input", reason="draft has no words")

    cons_max = int(sc.threshold("wrt45.consecutive_lists_max"))
    longest_run, run = 0, 0
    prev_was_list = False
    for line in draft.raw.splitlines():
        is_item = bool(_LIST_ITEM_RE.match(line))
        if is_item and not prev_was_list:
            run += 1
            longest_run = max(longest_run, run)
        elif line.strip() and not is_item:
            run = 0
        prev_was_list = is_item
    sc.record("WRT-45", "WARN", "fail" if longest_run > cons_max else "pass", value=longest_run, threshold=cons_max)

    three_max = sc.threshold("wrt46.rule_of_three_share_max")
    if draft.lists:
        share = sum(1 for g in draft.lists if len(g) == 3) / len(draft.lists)
        sc.record("WRT-46", "WARN", "fail" if share - 1e-9 > three_max else "pass",
                  value=round(share, 4), threshold=three_max,
                  evidence=[f"{sum(1 for g in draft.lists if len(g) == 3)} of {len(draft.lists)} lists have exactly three items"])
    else:
        sc.record("WRT-46", "WARN", "not_applicable", reason="draft contains no lists")


def score_group_f(sc: Scorer, draft: Draft) -> None:
    """Machine traces. Language-independent, near-zero false positives, all blocking."""
    found: list[str] = []
    for name, pattern in TOOL_MARKERS:
        for m in re.finditer(pattern, draft.raw):
            found.append(f"{name}: {m.group(0)!r} at offset {m.start()}")
    sc.record("WRT-50", "BLOCK", "fail" if found else "pass", value=len(found), threshold=0, evidence=found)

    utm: list[str] = []
    for pattern in GENERATOR_UTM:
        for m in re.finditer(pattern, draft.raw, re.IGNORECASE):
            utm.append(f"{m.group(0)!r} at offset {m.start()}")
    sc.record("WRT-51", "BLOCK", "fail" if utm else "pass", value=len(utm), threshold=0, evidence=utm)

    invisible: list[str] = []
    for ch, name in INVISIBLE_CHARS.items():
        count = draft.raw.count(ch)
        if count:
            invisible.append(f"{name} (U+{ord(ch):04X}) occurs {count} time(s)")
    sc.record("WRT-52", "BLOCK", "fail" if invisible else "pass", value=len(invisible), threshold=0,
              evidence=sorted(invisible))

    leaks: list[str] = []
    if draft.is_html:
        for name, pattern in (
            ("bold", r"\*\*[^*\n]{2,}\*\*"),
            ("heading", r"^#{1,6}\s+\S"),
            ("link", r"\[[^\]]+\]\([^)]+\)"),
            ("fence", r"```"),
        ):
            m = re.search(pattern, draft.raw, re.MULTILINE)
            if m:
                leaks.append(f"markdown {name} syntax in an HTML draft: {m.group(0)[:60]!r}")
    sc.record("WRT-53", "BLOCK", "fail" if leaks else "pass", value=len(leaks), threshold=0, evidence=leaks,
              reason="" if draft.is_html else "draft is markdown; no target-format mismatch detectable here")


def score_group_g(sc: Scorer, brief: dict[str, Any], reviews: dict[str, Any] | None,
                  writer_model: str | None, judge_model: str | None, pace: dict[str, Any] | None) -> None:
    """Process gates. These belong to the publication stage; at draft stage their inputs are absent."""
    required_lenses = {str(x) for x in (brief.get("reviewers") or [])}
    if reviews is None:
        sc.record("WRT-60", "BLOCK", "requires_input",
                  reason="no review log supplied; this gate is enforced at publication, not at draft scoring")
    else:
        logged = {str(k) for k, v in (reviews.get("lenses") or {}).items() if v}
        missing = sorted(required_lenses - logged)
        sc.record("WRT-60", "BLOCK", "fail" if missing else "pass",
                  evidence=[f"no review log entry for lens: {lens}" for lens in missing])

    if not writer_model or not judge_model:
        sc.record("WRT-61", "BLOCK", "requires_input", reason="writer and judge model identifiers not both supplied")
    else:
        same = _model_family(writer_model) == _model_family(judge_model)
        sc.record("WRT-61", "BLOCK", "fail" if same else "pass",
                  value=f"{writer_model} / {judge_model}",
                  evidence=[f"both resolve to family {_model_family(writer_model)!r}"] if same else [],
                  reason="a model does not see its own blind spots (WRT-R4)" if same else "")

    if pace is None:
        sc.record("WRT-62", "BLOCK", "requires_input", reason="publishing pace state not supplied")
    else:
        used, cap = pace.get("published_in_window"), pace.get("cap")
        if not isinstance(used, int) or not isinstance(cap, int):
            sc.record("WRT-62", "BLOCK", "requires_input", reason="pace state incomplete")
        else:
            sc.record("WRT-62", "BLOCK", "fail" if used >= cap else "pass", value=used, threshold=cap,
                      reason="pace is verification capacity, not production capacity (P2)")


def _model_family(identifier: str) -> str:
    """Reduce a model identifier to its family.

    Coarse on purpose. WRT-R4 asks whether the judge shares the writer's blind spots, and two
    checkpoints of one family share them whatever the version suffix says.
    """
    ident = identifier.strip().lower()
    for family in ("claude", "gpt", "gemini", "llama", "mistral", "qwen", "deepseek", "grok", "command"):
        if family in ident:
            return family
    return ident.split("-")[0] or ident


def score_language_pack(sc: Scorer, draft: Draft, pack: LanguagePack) -> None:
    """Findings from the locale's language pack, with the WARN ceiling applied in code.

    Density entries are judged by frequency and never by presence. That distinction is the pack
    contract's main safeguard: banning an ordinary word by presence bans ordinary language, and
    the Ukrainian pack calls this out as the single most important rule in the file.
    """
    words = max(draft.words, 1)
    density_min_words = int(sc.threshold("lang.density_min_words"))
    density_meaningful = words >= density_min_words
    for key in sorted(pack.sets):
        pack_set = pack.sets[key]
        if key == "prescribed_phrases" or not pack_set.forbidden:
            continue

        spans = draft.protected_spans if pack_set.never_inside else []
        if pack_set.never_inside and not spans:
            # UK-04: if span detection is unavailable the rules do not run at all. Here spans are
            # always detectable, but an empty result on a document with no quotations is normal.
            spans = []

        scope_text = _scope_text(draft, pack_set.applies_to)
        hits: list[str] = []
        density_reports: list[str] = []
        blocked = False

        for entry in sorted(pack_set.entries, key=lambda e: stable_key(e.set_key, e.term)):
            if not entry.runnable:
                continue  # already reported as a pack defect through WRT-06
            if entry.named_check:
                found = NAMED_CHECKS[entry.named_check](scope_text)
            else:
                assert entry.compiled is not None
                found = [(m.start(), m.group(0)) for m in entry.compiled.finditer(scope_text)]
            matches = [(start, txt) for start, txt in found if not _in_protected_span(start, spans)]
            if not matches:
                continue
            if entry.match_mode == "density":
                per_1000 = len(matches) * 1000 / words
                if pack_set.density_threshold is None:
                    density_reports.append(f"{entry.term!r}: {round(per_1000, 2)} per 1000 words (no threshold set)")
                elif not density_meaningful:
                    density_reports.append(
                        f"{entry.term!r}: {len(matches)} occurrence(s) in {words} words "
                        f"({round(per_1000, 2)} per 1000); below {density_min_words} words a rate is not evidence"
                    )
                elif per_1000 - 1e-9 > pack_set.density_threshold:
                    hits.append(f"{entry.term!r}: {round(per_1000, 2)} per 1000 words exceeds {pack_set.density_threshold}")
            else:
                hits.append(f"{entry.term!r} ({entry.match_mode}) matched {len(matches)} time(s): {matches[0][1][:60]!r}")
                if cap_pack_severity(pack_set, entry) == "BLOCK":
                    blocked = True

        rule_id = pack_set.rule_id or f"LANG-{pack.code.upper()}-{key}"
        severity = "BLOCK" if blocked else ((pack_set.declared_severity or "WARN").upper() if not hits else "WARN")
        if severity == "BLOCK" and not blocked:
            severity = "WARN"
        if not hits and density_reports:
            sc.record(rule_id, "INFO", "not_applicable", computed_by="code + lang pack",
                      evidence=density_reports,
                      reason="density measured but no threshold calibrated for this locale; reported, not warned")
        else:
            sc.record(rule_id, severity if severity in {"BLOCK", "WARN", "INFO"} else "WARN",
                      "fail" if hits else "pass", computed_by="code + lang pack",
                      value=len(hits), threshold=0, evidence=hits + density_reports)


def _scope_text(draft: Draft, applies_to: str) -> str:
    if applies_to == "section_first_sentence":
        firsts = []
        for section in draft.sections:
            first = next((s for s in split_sentences(section.body) if s.strip()), "")
            if first:
                firsts.append(first)
        return "\n".join(firsts)
    if applies_to == "document_tail":
        # Sliced on lines rather than tokens: closing-formula patterns are anchored to the start of
        # a line, and a token-based cut would land mid-sentence and stop them matching.
        lines = draft.text.splitlines()
        if not lines:
            return draft.text
        return "\n".join(lines[int(len(lines) * 0.85) :])
    return draft.text


# ---------------------------------------------------------------------------
# Orchestration
# ---------------------------------------------------------------------------


def score(
    draft_text: str,
    brief: dict[str, Any],
    packet: dict[str, Any],
    pack: LanguagePack,
    thresholds: Thresholds,
    *,
    draft_filename: str = "draft.md",
    top_docs: dict[str, str] | None = None,
    corpus: dict[str, Any] | None = None,
    artifacts_dir: Path | None = None,
    reviews: dict[str, Any] | None = None,
    pace: dict[str, Any] | None = None,
    writer_model: str | None = None,
    judge_model: str | None = None,
    iteration: int = 1,
    observe: bool = False,
) -> ScoreResult:
    """Pure scoring. No IO, so the whole gate is testable without a filesystem."""
    draft = parse_draft(draft_text, draft_filename)
    sc = Scorer(thresholds)

    score_group_a(sc, brief, artifacts_dir)
    score_group_b(sc, draft, brief, packet)

    entity_map = brief.get("entity_map") or packet.get("entity_map") or {}
    top_corpus = [d for d in packet.get("top_corpus", []) if isinstance(d, dict)]
    top_entity_sets = [{str(e) for e in (d.get("entities") or [])} for d in top_corpus]
    if top_entity_sets:
        need = len(top_entity_sets) / 2
        core_entities = sorted({e for s in top_entity_sets for e in s if sum(e in t for t in top_entity_sets) >= need})
    else:
        core_entities = sorted({str(e) for e in (entity_map.get("core") or [])})
    doc_tokens = tokenize_words(draft.text)
    core_present = [e for e in core_entities if _entity_present(_entity_tokens(e), doc_tokens)]

    score_group_c(sc, draft, brief, packet, top_docs or {}, corpus)
    score_group_d(sc, draft, packet, pack, core_present, core_entities)
    score_group_e(sc, draft)
    score_group_f(sc, draft)
    score_group_g(sc, brief, reviews, writer_model, judge_model, pace)
    score_language_pack(sc, draft, pack)

    # WRT-06. A malformed pack fails silently: it parses, it looks complete, and every consumer
    # reading the contract receives nothing. Only the loader can tell "no matches" from "no rules
    # were read", so the finding has to originate here. WARN rather than BLOCK because the defect
    # is ours, not the draft's, and blocking the draft punishes the wrong artefact.
    if pack.defects:
        sc.record("WRT-06", "WARN", "fail", computed_by="code",
                  value=len(pack.defects), threshold=0, evidence=sorted(pack.defects),
                  reason="language pack contract defect (05-writing-core.md §6)")
    else:
        sc.record("WRT-06", "WARN", "pass", computed_by="code", value=0, threshold=0,
                  evidence=[f"pack {pack.path.name} loaded {sum(len(s.entries) for s in pack.sets.values())} "
                            f"entries across {len(pack.sets)} sets"])

    results = sc.results
    if observe:
        for r in results:
            if r.severity == "BLOCK":
                r.severity = "WARN"
                r.reason = (r.reason + " | " if r.reason else "") + "downgraded by --observe"

    blocked_by = sorted({r.id for r in results if r.severity == "BLOCK" and r.status == "fail"})
    unresolved = sorted({r.id for r in results if r.id in BLOCKING_RULES and r.status not in {"pass", "not_applicable"}
                         and r.status != "fail"})
    warnings = sorted({r.id for r in results if r.severity == "WARN" and r.status == "fail"})

    if blocked_by and not observe:
        verdict = "BLOCK"
    elif unresolved or len(warnings) >= 2:
        verdict = "REWORK"
    else:
        verdict = "PASS"

    stats = {
        "words": draft.words,
        "sentences": len(draft.sentences),
        "paragraphs": len(draft.paragraphs),
        "sections": len([s for s in draft.sections if s.heading]),
        "lists": len(draft.lists),
        "claims": len([c for c in packet.get("claims", []) if isinstance(c, dict)]),
        "observe_mode": observe,
    }

    return ScoreResult(
        verdict=verdict,
        rules=results,
        blocked_by=blocked_by,
        unresolved=unresolved,
        warnings_triggered=warnings,
        pack={"code": pack.code, "path": str(pack.path), "sha256": pack.sha256, "defects": len(pack.defects)},
        stats=stats,
        iteration=iteration,
        writer_model=writer_model,
        judge_model=judge_model,
    )


# ---------------------------------------------------------------------------
# CLI
# ---------------------------------------------------------------------------


def _load_yaml(path: Path) -> dict[str, Any]:
    try:
        import yaml
    except ImportError as exc:  # pragma: no cover
        raise KilnError("PyYAML is required") from exc
    if not path.exists():
        raise KilnError(f"file not found: {path}")
    loaded = yaml.safe_load(path.read_text(encoding="utf-8")) or {}
    if not isinstance(loaded, dict):
        raise KilnError(f"{path}: expected a mapping at the top level")
    return loaded


def _load_json(path: Path) -> dict[str, Any]:
    import json

    if not path.exists():
        raise KilnError(f"file not found: {path}")
    loaded = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(loaded, dict):
        raise KilnError(f"{path}: expected a JSON object")
    return loaded


def _load_top_corpus(directory: Path | None) -> dict[str, str]:
    if directory is None:
        return {}
    if not directory.is_dir():
        raise KilnError(f"--top must be a directory of top-N snapshots: {directory}")
    docs: dict[str, str] = {}
    for path in sorted(directory.iterdir()):
        if path.suffix.lower() not in {".txt", ".md", ".html", ".htm"}:
            continue
        raw = path.read_text(encoding="utf-8", errors="replace")
        if path.suffix.lower() in {".html", ".htm"}:
            raw = _HTML_TAG_RE.sub(" ", _FENCE_RE.sub(" ", raw))
        docs[path.name] = raw
    return docs


def resolve_pack_path(brief: dict[str, Any], doctrine_dir: Path, explicit: Path | None) -> Path:
    """Pick the language pack from the brief's locale. Never from the doctrine's own language."""
    if explicit:
        return explicit
    locale = str(brief.get("locale") or "").strip()
    if not locale:
        raise KilnError("brief declares no locale, so no language pack can be selected (05 §0)")
    code = locale.split("-")[0].lower()
    return doctrine_dir / "lang" / f"{code}.md"


def main(args) -> int:
    if getattr(args, "target_words", None):
        raise KilnError(
            "a target word count was supplied. WRT-04 forbids it: Google lists writing to a word "
            "count among the signals of search-engine-first content. Use volume_expectation in the "
            "brief as a forecast instead (05-writing-core.md §4)."
        )

    brief = _load_yaml(args.brief)
    packet = _load_json(args.packet)
    draft_path = Path(args.draft)
    if not draft_path.exists():
        raise KilnError(f"draft not found: {draft_path}")
    draft_text = draft_path.read_text(encoding="utf-8")

    doctrine_dir = Path(args.doctrine) if args.doctrine else Path(__file__).resolve().parent.parent / "doctrine"
    pack = parse_language_pack(resolve_pack_path(brief, doctrine_dir, args.lang))

    thresholds = load_thresholds(args.project_root, DOCTRINE_DEFAULTS, args.thresholds)
    corpus = _load_json(args.corpus) if args.corpus else None
    reviews = _load_json(args.reviews) if args.reviews else None
    pace = _load_json(args.pace) if args.pace else None
    artifacts = Path(args.artifacts) if args.artifacts else Path(args.project_root) / ".kiln" / "artifacts"

    result = score(
        draft_text,
        brief,
        packet,
        pack,
        thresholds,
        draft_filename=draft_path.name,
        top_docs=_load_top_corpus(args.top),
        corpus=corpus,
        artifacts_dir=artifacts if artifacts.exists() else None,
        reviews=reviews,
        pace=pace,
        writer_model=args.writer_model,
        judge_model=args.judge_model,
        iteration=int(args.iteration),
        observe=bool(args.observe),
    )

    payload = result.as_record()
    if args.out:
        write_json(args.out, payload)
    else:
        sys.stdout.write(dumps(payload) + "\n")

    if args.observe:
        return EXIT_OK
    return {"PASS": EXIT_PASS, "REWORK": EXIT_REWORK, "BLOCK": EXIT_BLOCK}[result.verdict]


def build_parser():
    p = base_parser(__doc__.split("\n")[0])
    p.add_argument("--draft", type=Path, required=True, help="markdown or html of the draft")
    p.add_argument("--brief", type=Path, required=True, help="brief.yml")
    p.add_argument("--packet", type=Path, required=True, help="research_packet.json")
    p.add_argument("--corpus", type=Path, default=None, help=".kiln/corpus.json, for WRT-25")
    p.add_argument("--top", type=Path, default=None, help="directory of top-N snapshots, for WRT-23")
    p.add_argument("--lang", type=Path, default=None, help="explicit language pack; normally resolved from the locale")
    p.add_argument("--doctrine", type=Path, default=None, help="doctrine directory, for language pack resolution")
    p.add_argument("--artifacts", type=Path, default=None, help=".kiln/artifacts, for WRT-03")
    p.add_argument("--reviews", type=Path, default=None, help="review log, for WRT-60")
    p.add_argument("--pace", type=Path, default=None, help="publishing pace state, for WRT-62")
    p.add_argument("--writer-model", default=None, help="model identifier that produced the draft")
    p.add_argument("--judge-model", default=None, help="model identifier that will judge it")
    p.add_argument("--iteration", default=1, help="scoring round for this draft")
    return p


if __name__ == "__main__":  # pragma: no cover
    run(main, build_parser())
