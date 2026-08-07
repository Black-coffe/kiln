#!/usr/bin/env python3
"""Lint the Kiln doctrine against its own invariants.

This is the only script in layer 2 that audits the doctrine rather than the site. It exists
because of a paid-for failure: in the owner's previous system two canonical documents coexisted
where one prescribed a phrase (`lp-copywriting-rules §13.11`) that another forbade
(`ai-content-stop-rules §1.5`, `§3.5`). A writer could satisfy neither, the review verdict became
a lottery, and nobody noticed for months because nobody was checking. Check 1 below is the direct
descendant of that incident.

The specification is `doctrine/05-writing-core.md` §10, which lists eleven checks. Two more come
from the severity scale in `00-principles.md`. Where this file and the doctrine disagree, the
doctrine wins and this file is the bug.

Exit codes:

    0  clean, or warnings only
    2  errors present, the doctrine does not build

Warnings deliberately do not fail the build. An earlier revision returned 1 on warnings, which
collided with the shared convention where 1 means "the script could not complete" — a crash and a
style note became indistinguishable to any caller. It also made the pipeline permanently red on a
corpus that legitimately carries warnings, and a permanently red pipeline stops being read, which
costs more than the warnings were worth. Errors still fail; warnings still appear in the report.
Resolved 2026-08-07 and recorded in `05-writing-core.md` §10.

Usage:
    python rules_lint.py --doctrine ../doctrine
    python rules_lint.py --doctrine ../doctrine --root .. --format text
"""

from __future__ import annotations

import re
import sys
import unicodedata
from dataclasses import dataclass
from datetime import date, datetime
from pathlib import Path
from typing import Any, Iterable, Iterator, Sequence

sys.path.insert(0, str(Path(__file__).resolve().parent))

from kiln_common import (  # noqa: E402
    EXIT_OK,
    KilnError,
    base_parser,
    dumps,
    normalize_text,
    run,
    write_json,
)

# ---------------------------------------------------------------------------
# Exit codes for this script, per doctrine 05 §10
# ---------------------------------------------------------------------------

EXIT_CLEAN = 0
EXIT_WARNINGS = 0  # retained for callers; warnings no longer fail the build
EXIT_ERRORS = 2


# ---------------------------------------------------------------------------
# Constants drawn from the doctrine
# ---------------------------------------------------------------------------

#: Rule ID prefixes. One prefix per doctrine section; the section that owns the prefix is the only
#: file allowed to define IDs carrying it. Adding a section means adding its prefix here, and the
#: unknown-prefix check below will say so out loud rather than silently ignoring the new rules.
RULE_PREFIX_OWNER: dict[str, str] = {
    "ONB": "01-onboarding-grill.md",
    "SEM": "02-semantics.md",
    "CMP": "03-competitors.md",
    "TRD": "04-trends-and-plan.md",
    "WRT": "05-writing-core.md",
    "REV": "06-review-lenses.md",
    "LNK": "07-linking.md",
    "MSR": "08-measurement.md",
    "GEO": "09-geo.md",
    "SAF": "10-safety-gates.md",
    "LRN": "11-self-learning.md",
}

#: The three-level scale from `00-principles.md`. There is no fourth level and no synonyms.
DOCTRINE_SEVERITIES = ("BLOCK", "WARN", "INFO")

#: The human review scale, declared as an explicit exception in `06-review-lenses.md` with a
#: mapping table onto the doctrine scale. It is legal in that file and nowhere else.
REVIEW_VERDICTS = ("BLOCKER", "HIGH", "NOTE")
REVIEW_SCALE_FILE = "06-review-lenses.md"

#: Words that look like a severity but are not one. Catching these is the point of the check: a
#: fourth ladder appearing anywhere means two files have started grading differently.
FORBIDDEN_SEVERITY_WORDS = ("CRITICAL", "FATAL", "SEVERE", "MAJOR", "MINOR", "TRIVIAL")

#: The seven required language pack set keys, from `05-writing-core.md` §6.
REQUIRED_PACK_SETS = (
    "anaphora_openers",
    "hedge_phrases",
    "closing_formulas",
    "promo_lexicon",
    "vague_attribution",
    "generational_stopwords",
    "prescribed_phrases",
)

#: Entry status values, from `05-writing-core.md` §6. Only `deterministic` may carry BLOCK.
PACK_STATUSES = ("hypothesis", "observed", "calibrated", "deterministic")

PROVENANCE_RE = re.compile(
    r"\[\s*(source\s*:|expert judgement|expert judgment|owner decision|method\s*:)",
    re.IGNORECASE,
)

#: A rule identifier. The optional `.N` tail is not a legal rule ID; it is matched deliberately so
#: that a section number used as a rule ID (`MSR-5.2`) is reported as the thing it actually is,
#: rather than silently truncated to a plausible-looking `MSR-5`.
RULE_RE = re.compile(
    r"\b(?P<prefix>[A-Z]{3})-(?P<num>R?\d{1,3}(?:\.\d{1,2})?[a-z]?)\b"
)

PRINCIPLE_RE = re.compile(r"(?<![\w/.-])P(?P<num>\d{1,2})\b")

#: A language pack rule identifier. Four-letter prefix, so `RULE_RE` (which requires exactly three)
#: never sees these and the two namespaces cannot collide.
PACK_RULE_ID_RE = re.compile(r"\bLANG-(?P<locale>[A-Z]{2,3})-(?P<num>\d{2,3})\b")

#: Named checks a pack may reference in place of a pattern, resolved in code by `draft_score.py`.
#: Kept as a literal list rather than imported, so linting the doctrine does not require the
#: scorer to be importable. A name added there and not here is reported, which is the safe
#: direction: the alternative is a pack naming a check nothing implements.
KNOWN_NAMED_CHECKS = ("mixed_script_token",)

#: Two adjacent lookaheads at one position demand a single character satisfy both classes. This is
#: the shape of the homoglyph rule that shipped dead in the Ukrainian pack: well formed, reviewed,
#: and with an empty match set. It is the one dead-pattern shape cheap enough to detect statically.
IMPOSSIBLE_LOOKAHEAD_RE = re.compile(r"\(\?=(?![^)]*\|)[^)]{1,40}\)\s*\(\?=")

#: A numeric threshold stated against a named identifier, e.g. `override_rate ≥ 0.40`.
#: This is the shape check 8 hunts: the same name carrying two different numbers in two files.
NAMED_THRESHOLD_RE = re.compile(
    r"`(?P<name>[a-z][a-z0-9_]{2,}(?:\.[a-z0-9_]+)*)`"
    r"\s*(?P<op>[=≥≤<>]|&gt;=|&lt;=|>=|<=)\s*"
    r"(?P<value>-?\d+(?:\.\d+)?)\s*(?P<pct>%?)"
)


# ---------------------------------------------------------------------------
# Violations
# ---------------------------------------------------------------------------


@dataclass(frozen=True, slots=True)
class Violation:
    """One lint finding.

    `remedy` is not decoration. A linter whose message does not say what to do about it gets
    suppressed rather than fixed, and a suppressed doctrine linter is worse than none: it reports
    green on a corpus nobody is checking.
    """

    check: str
    severity: str  # "error" | "warning"
    file: str
    line: int
    message: str
    remedy: str

    def as_record(self) -> dict[str, Any]:
        return {
            "check": self.check,
            "file": self.file,
            "line": self.line,
            "message": self.message,
            "remedy": self.remedy,
        }

    def sort_key(self) -> tuple:
        return (0 if self.severity == "error" else 1, self.file, self.line, self.check, self.message)


# ---------------------------------------------------------------------------
# Suppressions
# ---------------------------------------------------------------------------

#: Every check this linter can emit. A suppression naming anything else is a typo, and a typo'd
#: suppression is the worst of both worlds: it silences nothing and looks like it does.
KNOWN_CHECKS = frozenset({
    "code_doctrine_ids",
    "composite_gate",
    "cross_reference",
    "duplicate_rule_id",
    "pack_block_severity",
    "pack_patterns",
    "pack_rule_ids",
    "pack_structure",
    "prescribed_forbidden_intersection",
    "principle_reference",
    "review_dates",
    "rule_metadata",
    "severity_vocabulary",
    "threshold_provenance",
    "threshold_single_home",
    "yaml_parses",
})

#: The check under which the linter reports problems with suppressions themselves. Deliberately
#: absent from KNOWN_CHECKS: a suppression that could silence the suppression auditor would let one
#: malformed line hide every other malformed line.
SUPPRESSION_CHECK = "lint_suppression"

#: `# kiln-lint: ignore <check> -- <reason>`
#: The check name is constrained to lowercase identifiers so that documentation writing
#: `ignore <check>` with a literal placeholder is not mistaken for a real suppression.
SUPPRESSION_RE = re.compile(
    r"#\s*kiln-lint:\s*ignore\s+([a-z_][a-z0-9_]*)\s*(?:(--)\s*(.*?))?\s*$"
)


@dataclass(slots=True)
class Suppression:
    """One line-scoped, reasoned suppression.

    Three properties are load-bearing, and a suppression mechanism without them becomes the place
    real findings go to die:

    - It names exactly one check. A blanket ignore hides the finding nobody predicted.
    - It carries a reason. Six months later the reason is the only thing distinguishing a
      deliberate exemption from a defect someone silenced on a Friday.
    - It is counted and audited. A suppression whose finding no longer occurs is stale, and stale
      suppressions accumulate until a clean report means nothing.
    """

    file: str
    line: int
    check: str
    reason: str
    used: int = 0

    def as_record(self) -> dict[str, Any]:
        return {
            "file": self.file,
            "line": self.line,
            "check": self.check,
            "reason": self.reason,
            "used": self.used,
        }


# ---------------------------------------------------------------------------
# Document model
# ---------------------------------------------------------------------------


@dataclass(slots=True)
class YamlBlock:
    """A fenced YAML block with the line it started on, so violations can point at it."""

    start_line: int
    text: str
    data: Any
    error: str | None = None


class DoctrineFile:
    """A parsed markdown doctrine file.

    Parsing is deliberately structural: identifiers, tables, fenced blocks. Nothing here reads
    prose semantics. A linter that tries to understand meaning produces confident nonsense, and
    the doctrine already has humans for judgement.
    """

    def __init__(self, path: Path, root: Path) -> None:
        self.path = path
        self.rel = path.relative_to(root).as_posix() if path.is_relative_to(root) else path.name
        self.name = path.name
        try:
            self.text = path.read_text(encoding="utf-8")
        except OSError as exc:
            raise KilnError(f"cannot read {path}: {exc}") from exc
        self.lines = self.text.splitlines()
        self.yaml_blocks: list[YamlBlock] = []
        self._parse_fences()

    def _parse_fences(self) -> None:
        """Collect fenced YAML blocks. Non-YAML fences are skipped rather than guessed at.

        `05-writing-core.md` carries `jsonc` fences with comments that are not valid JSON either;
        they are documentation of a schema, not data, and parsing them would only invent errors.
        """
        import yaml

        in_fence = False
        lang = ""
        start = 0
        buf: list[str] = []
        for i, line in enumerate(self.lines, 1):
            stripped = line.strip()
            if not in_fence and stripped.startswith("```"):
                in_fence = True
                lang = stripped[3:].strip().lower()
                start = i
                buf = []
                continue
            if in_fence and stripped == "```":
                in_fence = False
                if lang in ("yaml", "yml"):
                    body = "\n".join(buf)
                    try:
                        data = yaml.safe_load(body)
                        self.yaml_blocks.append(YamlBlock(start, body, data))
                    except yaml.YAMLError as exc:
                        self.yaml_blocks.append(
                            YamlBlock(start, body, None, error=str(exc).splitlines()[0])
                        )
                continue
            if in_fence:
                buf.append(line)

    def in_fence(self, lineno: int) -> bool:
        """Whether a 1-based line sits inside any fenced block.

        Used to avoid reading code samples as doctrine statements.
        """
        fences = [i for i, ln in enumerate(self.lines, 1) if ln.strip().startswith("```")]
        return sum(1 for f in fences if f < lineno) % 2 == 1


# ---------------------------------------------------------------------------
# Rule identifier extraction
# ---------------------------------------------------------------------------

#: Every convention the doctrine files actually use to declare a rule. They differ per file
#: because they were written in parallel; rather than forcing one style retroactively, the linter
#: recognises all of them and the styles are documented here.
#:
#: Each pattern is applied after stripping any leading blockquote marker. Several sections declare
#: their headline rules inside a blockquote for emphasis ("> **MSR-22 (BLOCK).**"), and treating
#: those as mere mentions makes the rule look undefined everywhere it is cited.
_DEFINITION_PATTERNS = (
    # | **WRT-01** | ... |     and     | `REV-01` | ... |
    re.compile(r"^\s*\|\s*(?:\*\*)?`?(?P<id>[A-Z]{3}-R?\d{1,3}[a-z]?)`?(?:\*\*)?\s*\|"),
    # **Rule `LNK-01` (BLOCK, code).**
    re.compile(r"^\s*\*\*Rule\s+`?(?P<id>[A-Z]{3}-R?\d{1,3}[a-z]?)`?"),
    # **LRN-01 (BLOCK).**   /   **WRT-R1. The researcher must not write prose.**
    re.compile(r"^\s*\*\*`?(?P<id>[A-Z]{3}-R?\d{1,3}[a-z]?)`?[\s.(·]"),
    # **`GEO-01 · BLOCK · Main content must be present in raw HTML.**
    re.compile(r"^\s*\*\*`(?P<id>[A-Z]{3}-R?\d{1,3}[a-z]?)\s*·"),
    # ### WRT-01 — heading form
    re.compile(r"^\s*#{2,6}\s+`?(?P<id>[A-Z]{3}-R?\d{1,3}[a-z]?)`?[\s.—:-]"),
)

#: Leading blockquote markers, stripped before definition matching.
_BLOCKQUOTE_RE = re.compile(r"^\s*(?:>\s?)+")

#: A line naming a span of rules ("`REV-01`…`REV-12`") mentions two IDs but defines neither.
_RANGE_MARKERS = ("…", "...", "..")


@dataclass(slots=True)
class RuleOccurrence:
    rule_id: str
    file: str
    line: int
    is_definition: bool


def extract_rule_occurrences(doc: DoctrineFile) -> list[RuleOccurrence]:
    """Find every rule ID in a file and decide which occurrences are definitions."""
    out: list[RuleOccurrence] = []
    for lineno, line in enumerate(doc.lines, 1):
        ids_here = {m.group(0) for m in RULE_RE.finditer(line)}
        if not ids_here:
            continue
        defined = _definitions_on_line(line)
        for rid in sorted(ids_here):
            out.append(RuleOccurrence(rid, doc.rel, lineno, rid in defined))
    return out


def _definitions_on_line(line: str) -> set[str]:
    """IDs this line declares, as opposed to merely mentions."""
    if any(marker in line for marker in _RANGE_MARKERS):
        # A range heading names endpoints without defining them. Treating "`REV-01`…`REV-12`" as
        # two definitions would mask the absence of the ten rules in between.
        return set()
    stripped = _BLOCKQUOTE_RE.sub("", line)
    found: set[str] = set()
    for pat in _DEFINITION_PATTERNS:
        m = pat.match(stripped)
        if m:
            found.add(m.group("id"))
    return found


# ---------------------------------------------------------------------------
# Language pack model
# ---------------------------------------------------------------------------


@dataclass(slots=True)
class PackSet:
    name: str
    forbidden: bool | None
    severity: str | None
    default_status: str | None
    items: list[dict[str, Any]]
    updated_at: Any
    next_review: Any
    line: int
    #: The key the pack actually used for its item list, and for each item's phrase. The contract
    #: says `items` and `phrase`; a pack using `entries` and `term` still parses here, and the
    #: deviation is reported rather than silently tolerated. Skipping such a set would hide it
    #: from the intersection invariant, which is the one thing this linter must never do.
    items_key: str = "items"
    phrase_key: str = "phrase"
    #: `LANG-<LOCALE>-<NN>` declared by the set. Pack findings are counted per rule in
    #: `.kiln/rules-stats.json`; an identifier a script invents at runtime cannot be counted,
    #: because nothing outside that script knows it exists.
    rule_id: str = ""


class LanguagePack:
    """A parsed `doctrine/lang/<code>.md`.

    Sets are read from every fenced YAML block, so a pack-local set declared anywhere in the file
    is visible. That is the whole point of check 1: a fixed list of five set names cannot see the
    Ukrainian russism set, and a pack could then prescribe a phrase its own set forbids while the
    build passed.
    """

    def __init__(self, doc: DoctrineFile) -> None:
        self.doc = doc
        self.code = doc.path.stem
        self.meta: dict[str, Any] = {}
        self.sets: dict[str, PackSet] = {}
        self._collect()

    def _collect(self) -> None:
        for block in self.doc.yaml_blocks:
            if not isinstance(block.data, dict):
                continue
            for key, value in block.data.items():
                if key == "lang" and isinstance(value, dict):
                    self.meta = value
                    continue
                if not isinstance(value, dict):
                    continue
                # The contract says `items`. A pack that wrote `entries` is still a phrase set and
                # must still be checked; `punctuation` and `form_metrics` carry `rules` / `metrics`
                # and are genuinely not phrase sets, so they are skipped.
                items_key = next((k for k in ("items", "entries") if k in value), None)
                if items_key is None:
                    continue
                items = value.get(items_key) or []
                if not isinstance(items, list):
                    items = []
                items = [i for i in items if isinstance(i, dict)]
                phrase_key = "phrase"
                if items and "phrase" not in items[0] and "term" in items[0]:
                    phrase_key = "term"
                self.sets[key] = PackSet(
                    name=key,
                    forbidden=value.get("forbidden"),
                    severity=value.get("severity"),
                    default_status=value.get("default_status"),
                    items=items,
                    updated_at=value.get("updated_at"),
                    next_review=value.get("next_review"),
                    line=self._line_of(key, block.start_line),
                    items_key=items_key,
                    phrase_key=phrase_key,
                    rule_id=str(value.get("rule_id") or ""),
                )

    def _line_of(self, key: str, block_start: int) -> int:
        """Best-effort line number of a top-level key inside its block."""
        pat = re.compile(rf"^{re.escape(key)}\s*:")
        for offset, line in enumerate(self.doc.lines[block_start:], block_start + 1):
            if pat.match(line):
                return offset
        return block_start

    def normalizer(self) -> "PhraseNormalizer":
        return PhraseNormalizer(self.meta.get("normalization") or {})


class PhraseNormalizer:
    """Applies the pack's declared normalization.

    The intersection invariant is undefined without this: whether "Here's the thing…" and
    "here's the thing" are the same phrase is a decision the pack makes, and the linter must use
    the pack's decision rather than its own.
    """

    def __init__(self, spec: dict[str, Any]) -> None:
        self.case = str(spec.get("case", "lower")).lower()
        self.unicode_form = str(spec.get("unicode_form", "NFC")).upper()
        self.collapse_whitespace = bool(spec.get("collapse_whitespace", True))
        self.strip_trailing_ellipsis = bool(spec.get("strip_trailing_ellipsis", True))
        self.strip_terminal_punctuation = bool(spec.get("strip_terminal_punctuation", True))
        self.declared = bool(spec)

    def __call__(self, phrase: str) -> str:
        s = unicodedata.normalize(self.unicode_form, str(phrase))
        if self.collapse_whitespace:
            s = " ".join(normalize_text(s).split())
        if self.strip_trailing_ellipsis:
            s = re.sub(r"(\.\.\.|…)\s*$", "", s)
        if self.strip_terminal_punctuation:
            s = re.sub(r"[.,;:!?]+\s*$", "", s)
        if self.case == "lower":
            s = s.casefold()
        return s.strip()


# ---------------------------------------------------------------------------
# The linter
# ---------------------------------------------------------------------------


class DoctrineLinter:
    def __init__(self, doctrine_dir: Path, root: Path, today: date) -> None:
        if not doctrine_dir.is_dir():
            raise KilnError(f"doctrine directory not found: {doctrine_dir}")
        self.doctrine_dir = doctrine_dir
        self.root = root
        self.today = today
        self.violations: list[Violation] = []

        self.files: list[DoctrineFile] = [
            DoctrineFile(p, root)
            for p in sorted(doctrine_dir.glob("*.md"), key=lambda p: p.name)
        ]
        self.lang_files: list[DoctrineFile] = [
            DoctrineFile(p, root)
            for p in sorted((doctrine_dir / "lang").glob("*.md"), key=lambda p: p.name)
        ] if (doctrine_dir / "lang").is_dir() else []
        self.packs: list[LanguagePack] = [
            LanguagePack(f) for f in self.lang_files if f.name != "_template.md"
        ]
        self.template: DoctrineFile | None = next(
            (f for f in self.lang_files if f.name == "_template.md"), None
        )

        self.occurrences: list[RuleOccurrence] = []
        for f in self.files + self.lang_files:
            self.occurrences.extend(extract_rule_occurrences(f))

        self.suppressions: list[Suppression] = []

    # -- suppressions ----------------------------------------------------

    #: Directories outside `doctrine/` that checks read, and therefore that suppressions can cover.
    CODE_DIRS = ("skills", "agents", "hooks", "scripts")
    CODE_EXTS = frozenset({".md", ".py", ".sh", ".json", ".yml", ".yaml", ".txt"})

    def _scanned_files(self) -> Iterator[tuple[str, Path]]:
        """Every file a check can produce a finding against, as (relative path, path).

        Suppressions are collected from exactly this set. Scanning a narrower set would make a
        suppression silently inert; scanning a wider one would report stale suppressions in files
        no check ever looks at.
        """
        seen: set[Path] = set()
        for f in self.files + self.lang_files:
            p = Path(f.path) if not isinstance(f.path, Path) else f.path
            if p not in seen:
                seen.add(p)
                yield p.relative_to(self.root).as_posix(), p
        for d in (self.root / d for d in self.CODE_DIRS):
            if not d.is_dir():
                continue
            for p in sorted(d.rglob("*")):
                if p.is_file() and p.suffix.lower() in self.CODE_EXTS and p not in seen:
                    seen.add(p)
                    yield p.relative_to(self.root).as_posix(), p

    def collect_suppressions(self) -> None:
        """Read `# kiln-lint: ignore <check> -- <reason>` markers.

        Malformed markers are reported rather than ignored. A suppression that does not parse is
        indistinguishable from a comment, so the finding it was meant to cover reappears and the
        author concludes the mechanism is broken instead of that their line was.
        """
        for rel, path in self._scanned_files():
            try:
                text = path.read_text(encoding="utf-8")
            except (OSError, UnicodeDecodeError):
                continue
            for lineno, line in enumerate(text.splitlines(), 1):
                m = SUPPRESSION_RE.search(line)
                if not m:
                    continue
                check, dashes, reason = m.group(1), m.group(2), (m.group(3) or "").strip()
                if dashes is None or not reason:
                    self.error(
                        SUPPRESSION_CHECK, rel, lineno,
                        f"suppression of {check!r} carries no reason",
                        "write `-- <why>`; an unexplained suppression cannot be reviewed later",
                    )
                    continue
                if check == SUPPRESSION_CHECK:
                    self.error(
                        SUPPRESSION_CHECK, rel, lineno,
                        "the suppression auditor cannot itself be suppressed",
                        "remove the marker; one malformed line must not be able to hide the rest",
                    )
                    continue
                if check not in KNOWN_CHECKS:
                    self.error(
                        SUPPRESSION_CHECK, rel, lineno,
                        f"{check!r} is not a check this linter emits",
                        "fix the check name; a typo silences nothing while appearing to",
                    )
                    continue
                self.suppressions.append(Suppression(rel, lineno, check, reason))

    def _partition(self) -> tuple[list[Violation], list[Violation]]:
        """Split violations into reported and suppressed, marking each suppression as used."""
        for s in self.suppressions:
            s.used = 0  # idempotent: report() and exit_code() both partition
        index: dict[tuple[str, int, str], Suppression] = {
            (s.file, s.line, s.check): s for s in self.suppressions
        }
        reported: list[Violation] = []
        suppressed: list[Violation] = []
        for v in self.violations:
            s = index.get((v.file, v.line, v.check))
            if s is None:
                reported.append(v)
            else:
                s.used += 1
                suppressed.append(v)
        for s in self.suppressions:
            if s.used == 0:
                reported.append(Violation(
                    SUPPRESSION_CHECK, "warning", s.file, s.line,
                    f"suppression of {s.check!r} matched nothing and is stale",
                    "remove it; suppressions nobody prunes are how a clean report stops meaning anything",
                ))
        return reported, suppressed

    # -- reporting -------------------------------------------------------

    def error(self, check: str, file: str, line: int, message: str, remedy: str) -> None:
        self.violations.append(Violation(check, "error", file, line, message, remedy))

    def warn(self, check: str, file: str, line: int, message: str, remedy: str) -> None:
        self.violations.append(Violation(check, "warning", file, line, message, remedy))

    # -- entry point -----------------------------------------------------

    def run_all(self) -> None:
        self.collect_suppressions()
        self.check_yaml_parses()
        self.check_prescribed_forbidden_intersection()  # 1
        self.check_rule_metadata()  # 2
        self.check_duplicate_ids()  # 3
        self.check_composite_gate()  # 4
        self.check_review_dates()  # 5
        self.check_threshold_provenance()  # 6
        self.check_code_doctrine_ids()  # 7
        self.check_threshold_single_home()  # 8
        self.check_pack_block_severity()  # 9
        self.check_pack_structure()  # 10
        self.check_principle_references()  # 11
        self.check_severity_vocabulary()  # 12
        self.check_cross_references()  # 13
        self.check_pack_rule_ids()  # 14
        self.check_pack_patterns()  # 15

    # -- check 0: the YAML itself ----------------------------------------

    def check_yaml_parses(self) -> None:
        """A doctrine YAML block that does not parse takes every downstream check with it."""
        for f in self.files + self.lang_files:
            for block in f.yaml_blocks:
                if block.error:
                    self.error(
                        "yaml_parses",
                        f.rel,
                        block.start_line,
                        f"fenced YAML block does not parse: {block.error}",
                        "fix the YAML; every check that reads this block is skipped until it parses",
                    )

    # -- check 1: the reason this script exists --------------------------

    def check_prescribed_forbidden_intersection(self) -> None:
        """`prescribed_phrases ∩ (⋃ every set where forbidden: true) = ∅`.

        The union is computed over all forbidden sets present in the pack, pack-local ones
        included. A fixed list of five cannot see the Ukrainian russism set, which would let a
        pack prescribe a phrase its own set forbids and reintroduce the original defect one level
        deeper.
        """
        for pack in self.packs:
            norm = pack.normalizer()
            if not norm.declared:
                self.error(
                    "prescribed_forbidden_intersection",
                    pack.doc.rel,
                    1,
                    "pack declares no `normalization` block, so the intersection invariant is undefined",
                    "add the `normalization` block from `lang/_template.md` §1",
                )
            prescribed = pack.sets.get("prescribed_phrases")
            if prescribed is None:
                continue  # absence is reported by check 10

            prescribed_map: dict[str, str] = {}
            for item in prescribed.items:
                phrase = item.get(prescribed.phrase_key)
                if phrase is None:
                    continue
                prescribed_map[norm(phrase)] = str(phrase)

            for name, s in sorted(pack.sets.items()):
                if name == "prescribed_phrases" or s.forbidden is not True:
                    continue
                for item in s.items:
                    phrase = item.get(s.phrase_key)
                    if phrase is None:
                        continue
                    key = norm(phrase)
                    if key in prescribed_map:
                        self.error(
                            "prescribed_forbidden_intersection",
                            pack.doc.rel,
                            s.line,
                            f"phrase {prescribed_map[key]!r} is prescribed and also forbidden "
                            f"by set `{name}` (normalized form: {key!r})",
                            "remove it from one side; a writer cannot satisfy both and the "
                            "review verdict becomes a lottery (05-writing-core.md §9.2-2)",
                        )

    # -- check 2 ---------------------------------------------------------

    def check_rule_metadata(self) -> None:
        """Every rule definition states a severity, and any threshold it states is sourced.

        Scope note, stated openly: this check reads the *definition line* only. The doctrine files
        use five different declaration conventions, and a definition whose severity sits three
        paragraphs below its heading cannot be verified structurally. Rules defined in table rows
        are checked strictly; rules defined in prose are checked for a severity token on the same
        line and nothing more.
        """
        for f in self.files:
            for lineno, line in enumerate(f.lines, 1):
                defined = _definitions_on_line(line)
                if not defined:
                    continue
                is_table_row = line.lstrip().startswith("|")
                has_sev = any(s in line for s in DOCTRINE_SEVERITIES) or (
                    f.name == REVIEW_SCALE_FILE and any(v in line for v in REVIEW_VERDICTS)
                )
                for rid in sorted(defined):
                    if not has_sev:
                        # Table rows carry their severity in a column; prose definitions carry it
                        # in the parenthetical. Neither is optional.
                        self.warn(
                            "rule_metadata",
                            f.rel,
                            lineno,
                            f"{rid} is defined without a severity on the definition line",
                            f"state one of {', '.join(DOCTRINE_SEVERITIES)} where the rule is declared",
                        )
                    if is_table_row and self._states_number(line) and not PROVENANCE_RE.search(line):
                        self.warn(
                            "rule_metadata",
                            f.rel,
                            lineno,
                            f"{rid} states a numeric threshold with no provenance marker",
                            "append `[source: ...]` or `[expert judgement, needs calibration]`; "
                            "an unmarked number is the failure this doctrine was built to prevent",
                        )

    @staticmethod
    def _states_number(line: str) -> bool:
        """A threshold-shaped number, not an ID fragment or a section reference."""
        cleaned = RULE_RE.sub(" ", line)
        cleaned = re.sub(r"§\s*\d+(\.\d+)*", " ", cleaned)
        cleaned = re.sub(r"\bEVIDENCE\.md#\S+", " ", cleaned)
        return bool(re.search(r"[=≥≤<>]\s*-?\d|(?<![\w.])-?\d+(\.\d+)?\s*%", cleaned))

    # -- check 3 ---------------------------------------------------------

    def check_duplicate_ids(self) -> None:
        """No ID is defined twice, and no ID is defined outside the section that owns its prefix."""
        by_id: dict[str, list[RuleOccurrence]] = {}
        for occ in self.occurrences:
            if occ.is_definition:
                by_id.setdefault(occ.rule_id, []).append(occ)

        for rid, occs in sorted(by_id.items()):
            files = sorted({o.file for o in occs})
            if len(files) > 1:
                first = min(occs, key=lambda o: (o.file, o.line))
                self.error(
                    "duplicate_rule_id",
                    first.file,
                    first.line,
                    f"{rid} is defined in more than one file: {', '.join(files)}",
                    "one rule, one home; delete the copy or give it its own ID",
                )
            elif len(occs) > 1:
                dupes = ", ".join(f"line {o.line}" for o in sorted(occs, key=lambda o: o.line))
                self.warn(
                    "duplicate_rule_id",
                    occs[0].file,
                    min(o.line for o in occs),
                    f"{rid} appears to be defined more than once in the same file ({dupes})",
                    "keep one definition; a summary table should reference the rule, not redeclare it",
                )

            prefix = rid.split("-", 1)[0]
            owner = RULE_PREFIX_OWNER.get(prefix)
            if owner is None:
                self.warn(
                    "duplicate_rule_id",
                    occs[0].file,
                    occs[0].line,
                    f"{rid} uses prefix {prefix!r}, which no doctrine section claims",
                    "register the prefix in rules_lint.py RULE_PREFIX_OWNER, or fix the ID",
                )
            else:
                for o in occs:
                    if Path(o.file).name != owner:
                        self.error(
                            "duplicate_rule_id",
                            o.file,
                            o.line,
                            f"{rid} is defined in {Path(o.file).name}, but prefix {prefix} "
                            f"belongs to {owner}",
                            "move the definition to its owning section, or reference it instead",
                        )

    # -- check 4 ---------------------------------------------------------

    def check_composite_gate(self) -> None:
        """Every rule named in the composite gate exists.

        The gate is the list of rules that stop a publication. A typo here does not fail loudly;
        it silently removes a rule from the gate, which is the worst available failure mode.
        """
        defined = {o.rule_id for o in self.occurrences if o.is_definition}
        for f in self.files:
            for block_start, body in self._gate_blocks(f):
                for rid, offset in _expand_gate_ids(body):
                    if rid not in defined:
                        self.error(
                            "composite_gate",
                            f.rel,
                            block_start + offset,
                            f"composite gate names {rid}, which is not defined anywhere",
                            "fix the identifier or define the rule; a gate naming a "
                            "non-existent rule silently stops enforcing it",
                        )

    def _gate_blocks(self, f: DoctrineFile) -> Iterator[tuple[int, str]]:
        """Fenced blocks that read as a composite gate."""
        in_fence = False
        start = 0
        buf: list[str] = []
        for i, line in enumerate(f.lines, 1):
            s = line.strip()
            if not in_fence and s.startswith("```"):
                in_fence, start, buf = True, i, []
                continue
            if in_fence and s == "```":
                in_fence = False
                body = "\n".join(buf)
                if re.search(r"^\s*(BLOCK|REWORK|PASS)\s*⟸", body, re.MULTILINE):
                    yield start, body
                continue
            if in_fence:
                buf.append(line)

    # -- check 5 ---------------------------------------------------------

    def check_review_dates(self) -> None:
        """`next_review` is not in the past.

        Stop-vocabulary is tied to model generations and goes stale within months. An overdue pack
        is a warning on every run rather than an error, because stale rules still catch most of
        what they caught yesterday; they simply under-detect the current generation.
        """
        for pack in self.packs:
            for name, s in sorted(pack.sets.items()):
                for field_name, value in (("updated_at", s.updated_at), ("next_review", s.next_review)):
                    if value is None:
                        self.error(
                            "review_dates",
                            pack.doc.rel,
                            s.line,
                            f"set `{name}` does not declare `{field_name}`",
                            "every set carries `updated_at` and `next_review` "
                            "(05-writing-core.md §6)",
                        )
                due = _as_date(s.next_review)
                if due is not None and due < self.today:
                    self.warn(
                        "review_dates",
                        pack.doc.rel,
                        s.line,
                        f"set `{name}` review was due {due.isoformat()}, "
                        f"{(self.today - due).days} days ago",
                        "re-derive the set against the current model generation and move "
                        "`next_review` forward; treat its findings as suspect until then",
                    )
            meta_due = _as_date(pack.meta.get("next_review"))
            if meta_due is not None and meta_due < self.today:
                self.warn(
                    "review_dates",
                    pack.doc.rel,
                    1,
                    f"pack review was due {meta_due.isoformat()}",
                    "review the pack and move `lang.next_review` forward",
                )

    # -- check 6 ---------------------------------------------------------

    def check_threshold_provenance(self) -> None:
        """Numeric thresholds inside rule tables carry a provenance marker.

        Scope, stated rather than implied: this reads table rows only. Applying it to every number
        in prose would flag dates, section numbers and evidence figures, and a check with that
        false-positive rate gets switched off within a week.
        """
        for f in self.files:
            for lineno, line in enumerate(f.lines, 1):
                if not line.lstrip().startswith("|"):
                    continue
                if not RULE_RE.search(line):
                    continue
                if _definitions_on_line(line):
                    continue  # already covered by check 2, do not double-report
                if self._states_number(line) and not PROVENANCE_RE.search(line):
                    self.warn(
                        "threshold_provenance",
                        f.rel,
                        lineno,
                        "table row states a numeric threshold with no provenance marker",
                        "add `[source: ...]` or `[expert judgement, needs calibration]`",
                    )

        for pack in self.packs:
            for name, s in sorted(pack.sets.items()):
                block = self._pack_block_text(pack, s)
                if block is None:
                    continue
                for m in re.finditer(r"density_warn_per_1000\s*:\s*(-?\d+(\.\d+)?)", block):
                    tail = block[m.end(): m.end() + 120]
                    if not PROVENANCE_RE.search(tail):
                        self.warn(
                            "threshold_provenance",
                            pack.doc.rel,
                            s.line,
                            f"set `{name}` states `density_warn_per_1000: {m.group(1)}` "
                            f"with no provenance marker",
                            "append `# [source: ...]` or `# [expert judgement, needs calibration]`",
                        )

    @staticmethod
    def _pack_block_text(pack: LanguagePack, s: PackSet) -> str | None:
        for block in pack.doc.yaml_blocks:
            if isinstance(block.data, dict) and s.name in block.data:
                return block.text
        return None

    # -- check 7 ---------------------------------------------------------

    def check_code_doctrine_ids(self) -> None:
        """Rule IDs used outside the doctrine resolve to a definition inside it.

        This is the check that catches the drift which made the owner's admin guide contradict its
        own stop-list: code and prose citing rules that no longer exist, or never did.

        The reverse direction ("every code-executed rule is referenced in scripts/") is
        deliberately not enforced. Layer 2 is largely unwritten; enforcing it today would emit
        several hundred warnings and train everyone to ignore this report. It belongs in the
        revision where the scripts exist.
        """
        defined = {o.rule_id for o in self.occurrences if o.is_definition}
        # A language pack set declaring `rule_id:` defines that identifier as surely as a doctrine
        # table row does. Without this, a script emitting a pack's own declared ID would be
        # reported as citing a rule that does not exist, and the honest fix would look like
        # suppressing the check.
        defined |= {s.rule_id for pack in self.packs for s in pack.sets.values() if s.rule_id}
        scan_dirs = [self.root / d for d in ("skills", "agents", "hooks", "scripts")]
        exts = {".md", ".py", ".sh", ".json", ".yml", ".yaml", ".txt"}
        for d in scan_dirs:
            if not d.is_dir():
                continue
            for p in sorted(d.rglob("*")):
                if not p.is_file() or p.suffix.lower() not in exts:
                    continue
                if p.name in ("rules_lint.py", "test_rules_lint.py"):
                    # Both name identifiers only in examples and constructed fixtures. The test
                    # file must contain deliberately invalid IDs — `WRT-99`, `MSR-5.2`, an
                    # undeclared `LANG-TT-99` — because they are what the detection is tested
                    # against. Reporting them is eleven permanent errors nobody can fix, and a
                    # report carrying permanent errors is one people learn to skim.
                    continue
                try:
                    text = p.read_text(encoding="utf-8")
                except (OSError, UnicodeDecodeError):
                    continue
                rel = p.relative_to(self.root).as_posix()
                for lineno, line in enumerate(text.splitlines(), 1):
                    for m in PACK_RULE_ID_RE.finditer(line):
                        rid = m.group(0)
                        if rid not in defined:
                            self.error(
                                "code_doctrine_ids",
                                rel,
                                lineno,
                                f"{rid} is referenced here but no language pack declares it",
                                "declare it as `rule_id:` on the owning set, or fix the identifier",
                            )
                    for m in RULE_RE.finditer(line):
                        rid = m.group(0)
                        if rid.split("-", 1)[0] not in RULE_PREFIX_OWNER:
                            continue
                        if rid not in defined:
                            self.error(
                                "code_doctrine_ids",
                                rel,
                                lineno,
                                f"{rid} is referenced here but defined nowhere in the doctrine",
                                "fix the identifier, or add the rule to its owning section",
                            )

    # -- check 8 ---------------------------------------------------------

    def check_threshold_single_home(self) -> None:
        """One threshold key, one value.

        The known instance: `06-review-lenses.md` and `11-self-learning.md` came to hold the same
        four counters. A number copied into two files drifts apart silently, and then two parts of
        the system enforce different rules while both cite the doctrine.

        The heuristic is a named identifier in backticks carrying a comparator and a number. It
        will not catch a threshold stated in prose, and it says so rather than implying coverage
        it does not have.
        """
        seen: dict[str, list[tuple[str, int, str]]] = {}
        for f in self.files:
            for lineno, line in enumerate(f.lines, 1):
                if f.in_fence(lineno):
                    continue
                for m in NAMED_THRESHOLD_RE.finditer(line):
                    name = m.group("name")
                    value = m.group("value") + m.group("pct")
                    seen.setdefault(name, []).append((f.rel, lineno, value))

        for name, occs in sorted(seen.items()):
            files = {o[0] for o in occs}
            values = {o[2] for o in occs}
            if len(files) > 1 and len(values) > 1:
                where = "; ".join(f"{fl}:{ln} = {v}" for fl, ln, v in sorted(occs))
                first = sorted(occs)[0]
                self.error(
                    "threshold_single_home",
                    first[0],
                    first[1],
                    f"threshold `{name}` is stated with different values in different files: {where}",
                    "give the key one canonical home; elsewhere reference the section "
                    "rather than restating the number",
                )
            elif len(files) > 1:
                first = sorted(occs)[0]
                self.warn(
                    "threshold_single_home",
                    first[0],
                    first[1],
                    f"threshold `{name}` is restated in {len(files)} files with the same value "
                    f"({sorted(values)[0]})",
                    "a matching restatement is legal but drifts; prefer a reference to the "
                    "canonical section",
                )

    # -- check 9 ---------------------------------------------------------

    def check_pack_block_severity(self) -> None:
        """Only `deterministic` entries may carry BLOCK inside a language pack.

        This is the doctrine defending itself against its own author. Gating publication on a
        stylometric score is exactly the failure P3 forbids; a language pack that blocks on a
        vocabulary hit has rebuilt a detector in-house and pointed it at the gate.
        """
        for pack in self.packs:
            for name, s in sorted(pack.sets.items()):
                if s.severity != "BLOCK":
                    continue
                if s.default_status == "deterministic":
                    non_det = [
                        i.get("phrase")
                        for i in s.items
                        if i.get("status") is not None and i.get("status") != "deterministic"
                    ]
                    if non_det:
                        self.error(
                            "pack_block_severity",
                            pack.doc.rel,
                            s.line,
                            f"set `{name}` carries BLOCK, but these entries override the "
                            f"deterministic default: {', '.join(str(p) for p in non_det[:5])}",
                            "an entry that is a statistical claim cannot block; move it to a "
                            "WARN set or justify it as deterministic",
                        )
                    continue
                self.error(
                    "pack_block_severity",
                    pack.doc.rel,
                    s.line,
                    f"set `{name}` carries severity BLOCK without `default_status: deterministic`",
                    "cap stylistic sets at WARN (00-principles.md, severity scale); only facts "
                    "about the writing system may block",
                )

    # -- check 10 --------------------------------------------------------

    def check_pack_structure(self) -> None:
        """Required keys present, every set declares `forbidden`, every entry resolves a status."""
        for pack in self.packs:
            for key in REQUIRED_PACK_SETS:
                if key not in pack.sets:
                    self.error(
                        "pack_structure",
                        pack.doc.rel,
                        1,
                        f"required set `{key}` is missing",
                        "all seven required sets must be present (05-writing-core.md §6)",
                    )
            for name, s in sorted(pack.sets.items()):
                if s.forbidden is None:
                    self.error(
                        "pack_structure",
                        pack.doc.rel,
                        s.line,
                        f"set `{name}` does not declare `forbidden: true|false`",
                        "declare it; the intersection invariant is computed over every set "
                        "carrying `forbidden: true`, and an undeclared set is invisible to it",
                    )
                if s.default_status is not None and s.default_status not in PACK_STATUSES:
                    self.error(
                        "pack_structure",
                        pack.doc.rel,
                        s.line,
                        f"set `{name}` declares default_status {s.default_status!r}, "
                        f"which is not one of {', '.join(PACK_STATUSES)}",
                        "use a declared status value, or amend the contract by PR",
                    )
                if s.items_key != "items":
                    self.error(
                        "pack_structure",
                        pack.doc.rel,
                        s.line,
                        f"set `{name}` lists its entries under `{s.items_key}:`, but the contract "
                        f"names the key `items:`",
                        "rename the key; every consumer of the pack reads `items`, and a set "
                        "under another name is invisible to them even though it parses",
                    )
                if s.items and s.phrase_key != "phrase":
                    self.error(
                        "pack_structure",
                        pack.doc.rel,
                        s.line,
                        f"entries in `{name}` carry `{s.phrase_key}:` where the contract "
                        f"names the field `phrase:`",
                        "rename the field (05-writing-core.md §6, lang/_template.md §2)",
                    )
                for item in s.items:
                    phrase = item.get(s.phrase_key)
                    if phrase is None:
                        self.error(
                            "pack_structure",
                            pack.doc.rel,
                            s.line,
                            f"set `{name}` holds an entry with no `{s.phrase_key}`",
                            "every entry carries `phrase` and `risk`",
                        )
                        continue
                    status = item.get("status", s.default_status)
                    if status is None:
                        self.error(
                            "pack_structure",
                            pack.doc.rel,
                            s.line,
                            f"entry {phrase!r} in `{name}` resolves no status",
                            "set it on the entry or give the set a `default_status`",
                        )
                    elif status not in PACK_STATUSES:
                        self.error(
                            "pack_structure",
                            pack.doc.rel,
                            s.line,
                            f"entry {phrase!r} in `{name}` has status {status!r}, "
                            f"not one of {', '.join(PACK_STATUSES)}",
                            "use a declared status value",
                        )
                    if item.get("risk") in ("critical", "high") and not item.get("note"):
                        self.warn(
                            "pack_structure",
                            pack.doc.rel,
                            s.line,
                            f"entry {phrase!r} in `{name}` is risk={item.get('risk')} with no note",
                            "say why it is a signal, not merely why you dislike it "
                            "(lang/_template.md §8)",
                        )

        if self.template is not None:
            body = self.template.text
            for key in REQUIRED_PACK_SETS:
                if key not in body:
                    self.warn(
                        "pack_structure",
                        self.template.rel,
                        1,
                        f"template does not mention required set `{key}`",
                        "the template is what new packs are copied from; a key missing here "
                        "propagates into every future pack",
                    )

    # -- check 11 --------------------------------------------------------

    def check_principle_references(self) -> None:
        """A bare `P<number>` resolves to a principle in `00-principles.md`.

        Research reports use the same `P<number>` shape for unrelated objects: `EVIDENCE.md#e10-eeat-entities-schema` numbers
        its trust signals P1..P18. An unqualified P13 in a doctrine file is therefore ambiguous
        until it is either resolved here or prefixed with its source.
        """
        principles = self._defined_principles()
        if not principles:
            self.error(
                "principle_reference",
                "doctrine/00-principles.md",
                1,
                "no principles could be parsed from 00-principles.md",
                "principles are declared as `## P<n>. <title>`; the linter reads that form",
            )
            return
        for f in self.files + self.lang_files:
            if f.name == "00-principles.md":
                continue
            for lineno, line in enumerate(f.lines, 1):
                if f.in_fence(lineno):
                    continue
                for m in PRINCIPLE_RE.finditer(line):
                    before = line[max(0, m.start() - 60): m.start()]
                    # A P-number carried by a citation belongs to the cited source, not to our
                    # principles: an EVIDENCE.md citation followed by P13 is that report's trust signal 13.
                    if re.search(r"(EVIDENCE\.md#\S*|\[internal observation, unpublished\])[`\s]*$", before):
                        continue  # correctly prefixed with its source
                    num = int(m.group("num"))
                    if num not in principles:
                        self.error(
                            "principle_reference",
                            f.rel,
                            lineno,
                            f"P{num} does not exist in 00-principles.md",
                            "if this identifier comes from an intel report, prefix it with its "
                            "source (`EVIDENCE.md#e10-eeat-entities-schema P13`); otherwise fix the number",
                        )

    def _defined_principles(self) -> set[int]:
        for f in self.files:
            if f.name != "00-principles.md":
                continue
            return {
                int(m.group(1))
                for line in f.lines
                if (m := re.match(r"^#{2,3}\s+P(\d{1,2})\b", line))
            }
        return set()

    # -- check 12 --------------------------------------------------------

    def check_severity_vocabulary(self) -> None:
        """Exactly three severity words, plus one declared exception.

        `06-review-lenses.md` declares a separate human verdict scale with an explicit mapping
        table onto the doctrine scale. That exception is honoured. A fourth ladder anywhere else
        means two parts of the system have quietly started grading differently.
        """
        review_declares_mapping = any(
            f.name == REVIEW_SCALE_FILE
            and all(v in f.text for v in REVIEW_VERDICTS)
            and "Doctrine severity" in f.text
            for f in self.files
        )
        if not review_declares_mapping and any(f.name == REVIEW_SCALE_FILE for f in self.files):
            self.error(
                "severity_vocabulary",
                f"doctrine/{REVIEW_SCALE_FILE}",
                1,
                "the review file uses a separate verdict scale without a declared mapping table",
                "declare the mapping onto BLOCK/WARN/INFO, or convert to the doctrine scale",
            )

        # A register that grades something other than rules may declare its own axis. The open
        # questions file ranks question urgency, not rule enforcement; flagging it as a fourth
        # severity ladder would be wrong. It is noted once and then exempted.
        own_scale_files: set[str] = set()
        for f in self.files:
            if re.search(r"^\*\*Severity meanings\.\*\*", f.text, re.MULTILINE):
                own_scale_files.add(f.name)
                self.warn(
                    "severity_vocabulary",
                    f.rel,
                    1,
                    "this file declares its own severity vocabulary, separate from the "
                    "doctrine scale",
                    "legal for a register that grades something other than rules; make sure "
                    "no rule is graded on it",
                )

        for f in self.files + self.lang_files:
            if f.name in (REVIEW_SCALE_FILE, *own_scale_files):
                continue
            for lineno, line in enumerate(f.lines, 1):
                for word in REVIEW_VERDICTS:
                    if not re.search(rf"\b{word}\b", line):
                        continue
                    if not _severity_shaped(line):
                        continue  # the English word "high" in prose is not a severity assignment
                    if re.search(rf"`?{word}`?\s*(→|->|maps to)", line):
                        continue  # a line explaining the mapping is not a use of the scale
                    if re.search(
                        r"must not appear|no synonyms|is a review-scale|forbidden|not one of",
                        line,
                        re.IGNORECASE,
                    ):
                        continue  # a line prohibiting the word is not a use of it
                    self.error(
                        "severity_vocabulary",
                        f.rel,
                        lineno,
                        f"{word!r} is a review-scale verdict and is used outside "
                        f"{REVIEW_SCALE_FILE}",
                        f"use one of {', '.join(DOCTRINE_SEVERITIES)}; the review scale is "
                        f"declared only for human verdicts in {REVIEW_SCALE_FILE}",
                    )
                for word in FORBIDDEN_SEVERITY_WORDS:
                    if re.search(rf"(?<![\w`]){word}(?![\w`])", line) and _severity_shaped(line):
                        self.warn(
                            "severity_vocabulary",
                            f.rel,
                            lineno,
                            f"{word!r} appears in a severity position; the doctrine defines "
                            f"three levels and no synonyms",
                            f"use one of {', '.join(DOCTRINE_SEVERITIES)}",
                        )

    # -- check 13 --------------------------------------------------------

    def check_cross_references(self) -> None:
        """File and section references resolve.

        A reference to a section that has been renumbered is not cosmetic. These files cite each
        other for thresholds and procedures, and a stale pointer sends a reader to the wrong
        number with full confidence.
        """
        known_files = {f.name for f in self.files} | {
            f"lang/{f.name}" for f in self.lang_files
        }
        # Governance documents live at the repository root rather than inside doctrine/.
        known_files |= {p.name for p in self.root.glob("*.md")}
        sections: dict[str, set[str]] = {}
        for f in self.files + self.lang_files:
            sections[f.name] = _section_ids(f)

        file_ref = re.compile(
            r"`(?P<path>(?:doctrine/)?(?:lang/)?(?P<base>[0-9A-Za-z_-]+\.md))`"
            r"(?:\s*(?P<sec>§\s*[\d.]+(?:-\d+)?))?"
        )
        for f in self.files + self.lang_files:
            for lineno, line in enumerate(f.lines, 1):
                for m in file_ref.finditer(line):
                    base = m.group("base")
                    if not _is_doctrine_document(base):
                        # `draft.md`, `outline.md`, `onboarding-report.md` and friends are runtime
                        # artefacts the pipeline produces, not documents in this repository.
                        # Demanding they exist would report the doctrine as broken for naming
                        # its own outputs.
                        continue
                    # A reference inside lang/ is relative to lang/ unless it says otherwise.
                    lang_names = {lf.name for lf in self.lang_files}
                    resolved = (
                        base in known_files
                        or f"lang/{base}" in known_files
                        or (f.path.parent.name == "lang" and base in lang_names)
                    )
                    if not resolved:
                        # A language pack that does not exist yet is a plan, not a broken link:
                        # packs are added one locale at a time and the doctrine names the next
                        # one deliberately.
                        planned_pack = bool(re.fullmatch(r"[a-z]{2,3}\.md", base))
                        report = self.warn if planned_pack else self.error
                        report(
                            "cross_reference",
                            f.rel,
                            lineno,
                            f"reference to `{m.group('path')}`, which does not exist"
                            + (" yet" if planned_pack else ""),
                            "add the pack before relying on the reference"
                            if planned_pack
                            else "fix the path; doctrine files reference each other for "
                            "thresholds and procedures",
                        )
                        continue
                    sec = m.group("sec")
                    if not sec:
                        continue
                    target = base
                    num = sec.replace("§", "").strip()
                    known = sections.get(target, set())
                    if known and num not in known and num.split("-")[0] not in known:
                        self.warn(
                            "cross_reference",
                            f.rel,
                            lineno,
                            f"reference to {target} §{num}, which has no matching section heading",
                            "renumbering happened during authoring; re-point the reference",
                        )

    # -- check 14 --------------------------------------------------------

    def check_pack_rule_ids(self) -> None:
        """Every language pack set declares a well-formed, unique `LANG-<LOCALE>-<NN>` identifier.

        Findings from a pack are counted per rule in `.kiln/rules-stats.json`, and those counters
        are what P8 uses to decide which rules survive. An identifier synthesised at runtime from a
        set key cannot be counted: nothing outside the process that invented it knows the
        identifier exists, so the rule accumulates no history and can never be retired on evidence.

        The locale segment must match the pack's own code. A pack copied from another language and
        edited is the normal way packs are born, and a stale locale segment in the copy silently
        merges two languages' counters into one.
        """
        seen: dict[str, tuple[str, int]] = {}
        for pack in self.packs:
            if pack.doc.path.stem == "_template":
                continue  # the template declares placeholder IDs on purpose
            expected_locale = str(pack.meta.get("code") or pack.code).upper()
            for name, s in sorted(pack.sets.items()):
                if not s.rule_id:
                    self.error(
                        "pack_rule_ids",
                        pack.doc.rel,
                        s.line,
                        f"set `{name}` declares no `rule_id`",
                        f"add `rule_id: LANG-{expected_locale}-NN`; without it the set's findings "
                        f"cannot be counted per rule and P8 has nothing to act on",
                    )
                    continue
                m = PACK_RULE_ID_RE.fullmatch(s.rule_id)
                if not m:
                    self.error(
                        "pack_rule_ids",
                        pack.doc.rel,
                        s.line,
                        f"set `{name}` declares rule_id {s.rule_id!r}, which is not of the form "
                        f"LANG-<LOCALE>-<NN>",
                        "uppercase locale segment, zero-padded number",
                    )
                    continue
                if m.group("locale") != expected_locale:
                    self.error(
                        "pack_rule_ids",
                        pack.doc.rel,
                        s.line,
                        f"set `{name}` declares rule_id {s.rule_id!r}, but this pack's locale is "
                        f"{expected_locale}",
                        "a stale locale segment merges two languages' counters into one",
                    )
                    continue
                prior = seen.get(s.rule_id)
                if prior:
                    self.error(
                        "pack_rule_ids",
                        pack.doc.rel,
                        s.line,
                        f"rule_id {s.rule_id!r} is already declared at {prior[0]}:{prior[1]}",
                        "identifiers are unique and immutable; a changed rule takes a new one",
                    )
                    continue
                seen[s.rule_id] = (pack.doc.rel, s.line)

    # -- check 15 --------------------------------------------------------

    def check_pack_patterns(self) -> None:
        """Pack entries do not carry patterns that cannot match, or checks that do not exist.

        A rule that compiles and can never fire is worse than a missing rule. A missing rule is
        visible; a dead one reports success forever, and nobody investigates a check that never
        complains. This is not hypothetical: `\\b(?=\\p{Cyrillic})(?=\\p{Latin})\\S+\\b` shipped in
        the Ukrainian pack as the homoglyph guard. Two lookaheads at one position require a single
        character to belong to two scripts, so its match set was empty for as long as it existed.

        Only the statically decidable cases are checked. General emptiness of a regular language is
        not something to attempt here, and a linter that pretends otherwise is its own dead rule.
        """
        for pack in self.packs:
            for name, s in sorted(pack.sets.items()):
                for item in s.items:
                    label = str(item.get(s.phrase_key) or item.get("named_check") or "?")
                    named = item.get("named_check")
                    pattern = item.get("match") or item.get("pattern")

                    if named:
                        if str(named) not in KNOWN_NAMED_CHECKS:
                            self.error(
                                "pack_patterns",
                                pack.doc.rel,
                                s.line,
                                f"`{name}` entry {label!r} names check {named!r}, which is not "
                                f"implemented. Known: {', '.join(KNOWN_NAMED_CHECKS)}",
                                "implement it in draft_score.py NAMED_CHECKS and register it here, "
                                "or remove the entry; an unresolved name means the entry never runs",
                            )
                        if item.get("match"):
                            self.warn(
                                "pack_patterns",
                                pack.doc.rel,
                                s.line,
                                f"`{name}` entry {label!r} declares both `named_check` and `match`",
                                "they are mutually exclusive; delete the one that is not intended",
                            )
                        continue

                    if not pattern:
                        continue
                    if IMPOSSIBLE_LOOKAHEAD_RE.search(str(pattern)):
                        self.error(
                            "pack_patterns",
                            pack.doc.rel,
                            s.line,
                            f"`{name}` entry {label!r} has adjacent lookaheads at one position "
                            f"({str(pattern)[:60]!r}); a single character cannot satisfy both, so "
                            f"the pattern can never match",
                            "express it as a `named_check` if the fact is a property of a token "
                            "rather than of a character",
                        )

    # -- output ----------------------------------------------------------

    def report(self) -> dict[str, Any]:
        reported, suppressed = self._partition()
        ordered = sorted(reported, key=Violation.sort_key)
        errors = [v.as_record() for v in ordered if v.severity == "error"]
        warnings = [v.as_record() for v in ordered if v.severity == "warning"]
        by_check: dict[str, dict[str, int]] = {}
        for v in ordered:
            slot = by_check.setdefault(v.check, {"errors": 0, "warnings": 0})
            slot["errors" if v.severity == "error" else "warnings"] += 1
        return {
            "checked": {
                "doctrine_files": len(self.files),
                "language_packs": len(self.packs),
                "rules_defined": len({o.rule_id for o in self.occurrences if o.is_definition}),
            },
            "summary": {
                "errors": len(errors),
                "warnings": len(warnings),
                "by_check": {k: by_check[k] for k in sorted(by_check)},
                # Surfaced in the summary on purpose. A suppression count that only appears in a
                # detail section is a count nobody reads, and unreviewed suppressions are how a
                # green report drifts away from a healthy corpus.
                "suppressions": {
                    "declared": len(self.suppressions),
                    "applied": sum(1 for s in self.suppressions if s.used),
                    "stale": sum(1 for s in self.suppressions if not s.used),
                    "findings_suppressed": len(suppressed),
                },
            },
            "errors": errors,
            "warnings": warnings,
            "suppressions": [
                s.as_record() for s in sorted(self.suppressions, key=lambda x: (x.file, x.line, x.check))
            ],
        }

    def exit_code(self) -> int:
        reported, _ = self._partition()
        if any(v.severity == "error" for v in reported):
            return EXIT_ERRORS
        # Warnings report and do not fail. See the module docstring: an exit code on warnings
        # collides with "the script could not complete" and turns the pipeline permanently red.
        return EXIT_CLEAN


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


#: Documents this repository owns, as opposed to artefacts the pipeline produces at runtime.
#: Doctrine sections are `NN-name.md`; governance documents are SHOUTING-CASE; language packs are
#: short codes under `lang/`.
_DOCTRINE_DOC_RE = re.compile(r"^(?:\d{2}-[a-z0-9-]+|[A-Z][A-Z-]+|_template|[a-z]{2,3})\.md$")


def _is_doctrine_document(name: str) -> bool:
    return bool(_DOCTRINE_DOC_RE.match(name))


def _severity_shaped(line: str) -> bool:
    """Whether a line looks like it is assigning a severity rather than using an English word.

    "a critical failure" in prose is not a severity assignment; "| CRITICAL |" in a table is.
    """
    return bool(
        re.search(r"\|\s*`?[A-Z]{4,8}`?\s*\|", line)
        or re.search(r"severity\s*[:=]", line, re.IGNORECASE)
        or re.search(r"`[A-Z]{4,8}`", line)
        # "**LRN-09 (HIGH).**" — a severity in the parenthetical of a rule declaration, which is
        # how three of the doctrine sections declare theirs.
        or re.search(r"[A-Z]{3}-R?\d{1,3}[a-z]?\s*\(\s*[A-Z]{4,8}\s*\)", line)
    )


def _section_ids(f: DoctrineFile) -> set[str]:
    """Section numbers a file declares, in the several forms the doctrine uses."""
    out: set[str] = set()
    for line in f.lines:
        m = re.match(r"^#{2,6}\s+§?\s*(\d+(?:\.\d+)*)", line)
        if m:
            out.add(m.group(1))
            continue
        m = re.match(r"^#{2,6}\s+.*?§\s*(\d+(?:\.\d+)*)", line)
        if m:
            out.add(m.group(1))
    return out


def _as_date(value: Any) -> date | None:
    """Coerce a YAML date-ish value, tolerating the template's YYYY-MM-DD placeholder."""
    if isinstance(value, date) and not isinstance(value, datetime):
        return value
    if isinstance(value, datetime):
        return value.date()
    if isinstance(value, str):
        try:
            return datetime.strptime(value.strip(), "%Y-%m-%d").date()
        except ValueError:
            return None
    return None


def _expand_gate_ids(body: str) -> list[tuple[str, int]]:
    """Expand a composite gate expression into concrete IDs with their line offsets.

    The gate is written for humans: `WRT-01..05, 10, 11, 20 (when OCD=0), 50..53`. Bare numbers
    inherit the last prefix, and `..` denotes an inclusive range.
    """
    out: list[tuple[str, int]] = []
    prefix: str | None = None
    for offset, raw in enumerate(body.splitlines()):
        # Only the BLOCK clause enumerates rules. The REWORK and PASS clauses state counts
        # ("≥ 2 WARN rules triggered"), and reading those as identifiers mints a phantom rule.
        if re.match(r"^\s*(REWORK|PASS)\b", raw):
            prefix = None
            continue
        # Parenthetical conditions carry their own numbers ("20 (when OCD=0)", "21 (when EG<0.08)").
        # Left in, they mint phantom rules like WRT-0 and WRT-08 and bury the real gate errors.
        line = re.sub(r"\([^)]*\)", " ", raw)
        line = re.sub(r"\d+\.\d+", " ", line)
        for token in re.finditer(
            r"(?:(?P<prefix>[A-Z]{3})-)?(?P<a>R?\d{1,3})(?:\s*\.\.\s*(?P<b>\d{1,3}))?",
            line,
        ):
            if token.group("prefix"):
                prefix = token.group("prefix")
            if prefix is None:
                continue
            a_raw = token.group("a")
            if a_raw.startswith("R"):
                out.append((f"{prefix}-{a_raw}", offset))
                continue
            width = len(a_raw)
            a = int(a_raw)
            b = int(token.group("b")) if token.group("b") else a
            if b < a or b - a > 60:
                continue  # not a rule range; almost certainly a year or a percentage
            for n in range(a, b + 1):
                out.append((f"{prefix}-{n:0{width}d}", offset))
    return out


def _format_text(report: dict[str, Any]) -> str:
    lines: list[str] = []
    chk = report["checked"]
    lines.append(
        f"Checked {chk['doctrine_files']} doctrine files, {chk['language_packs']} language packs, "
        f"{chk['rules_defined']} rule definitions."
    )
    for bucket, label in (("errors", "ERROR"), ("warnings", "WARN ")):
        for v in report[bucket]:
            lines.append(f"{label} {v['file']}:{v['line']}  [{v['check']}]")
            lines.append(f"      {v['message']}")
            lines.append(f"      -> {v['remedy']}")
    s = report["summary"]
    lines.append("")
    lines.append(f"{s['errors']} error(s), {s['warnings']} warning(s).")
    for check, counts in s["by_check"].items():
        lines.append(f"  {check}: {counts['errors']} error(s), {counts['warnings']} warning(s)")
    return "\n".join(lines)


# ---------------------------------------------------------------------------
# Entry point
# ---------------------------------------------------------------------------


def main(args) -> int:
    doctrine_dir: Path = args.doctrine or (args.project_root / "doctrine")
    root: Path = args.root or doctrine_dir.parent
    today = _as_date(args.today) if args.today else date.today()
    if today is None:
        raise KilnError(f"--today must be YYYY-MM-DD, got {args.today!r}")

    linter = DoctrineLinter(doctrine_dir.resolve(), root.resolve(), today)
    linter.run_all()
    report = linter.report()

    if args.format == "text":
        text = _format_text(report)
        if args.out:
            Path(args.out).write_text(text + "\n", encoding="utf-8", newline="\n")
        else:
            sys.stdout.write(text + "\n")
    else:
        if args.out:
            write_json(args.out, report)
        else:
            sys.stdout.write(dumps(report) + "\n")

    return linter.exit_code()


def build_parser():
    p = base_parser("Lint the Kiln doctrine against its own invariants.")
    p.add_argument("--doctrine", type=Path, default=None,
                   help="path to the doctrine/ directory (default: <project-root>/doctrine)")
    p.add_argument("--root", type=Path, default=None,
                   help="repository root to scan for rule references (default: doctrine's parent)")
    p.add_argument("--today", default=None,
                   help="override today's date as YYYY-MM-DD; makes review-date checks deterministic")
    p.add_argument("--format", choices=("json", "text"), default="json",
                   help="output format")
    return p


if __name__ == "__main__":
    run(main, build_parser())
