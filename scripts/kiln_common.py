"""Shared primitives for Kiln layer-2 scripts.

Every script in this directory imports from here. The point is not code reuse for its own sake:
three things must be identical across scripts or the learning loops read our own inconsistency as
a signal from the world.

1. Threshold resolution. A finding is meaningless without the thresholds that produced it and
   where they came from, because recalibration otherwise silently invalidates stored history.
2. Unicode text handling. `wc -w` does not split Cyrillic into words; on a live measurement it
   reported an English locale as six times larger than a Ukrainian one at parity, inverting the
   conclusion. Every count here operates on Unicode.
3. Deterministic output. Identical input must produce byte-identical output, ordering included,
   or a change in our implementation is indistinguishable from a change in the SERP.

Runtime: Python 3.11+. Standard library only, except PyYAML for threshold files.
"""

from __future__ import annotations

import argparse
import json
import os
import re
import sys
import unicodedata
from dataclasses import dataclass, field, asdict
from pathlib import Path
from typing import Any, Callable, Iterable, Iterator, Sequence

__all__ = [
    "EXIT_OK",
    "EXIT_ERROR",
    "EXIT_GATE_FAILED",
    "EXIT_SCRIPT_SPECIFIC",
    "Threshold",
    "Thresholds",
    "Finding",
    "KilnError",
    "GateFailure",
    "load_thresholds",
    "tokenize_words",
    "count_words",
    "split_sentences",
    "normalize_text",
    "normalize_query",
    "read_jsonl",
    "write_jsonl",
    "write_json",
    "dumps",
    "stable_key",
    "base_parser",
    "run",
]


# ---------------------------------------------------------------------------
# Exit codes
# ---------------------------------------------------------------------------
# Uniform across every layer-2 script. Hooks and CI branch on these, so a script that invents its
# own meaning for a code breaks the gate silently, which is the one failure mode gates must not have.

EXIT_OK = 0
"""Completed; no blocking condition found."""

EXIT_ERROR = 1
"""Could not complete: bad input, missing file, unreadable credentials. Says nothing about the site."""

EXIT_GATE_FAILED = 2
"""Completed and found a blocking condition. The work is valid; the answer is no."""

EXIT_SCRIPT_SPECIFIC = 3
"""Reserved for a meaning the owning doctrine section defines. Never reused for a generic error."""


class KilnError(Exception):
    """Operational failure. Maps to EXIT_ERROR."""


class GateFailure(Exception):
    """A blocking condition was found. Maps to EXIT_GATE_FAILED.

    Distinct from KilnError on purpose: "the script broke" and "the draft is not publishable" are
    different events, and conflating them lets a crash read as a pass.
    """

    def __init__(self, message: str, findings: Sequence["Finding"] = ()) -> None:
        super().__init__(message)
        self.findings = list(findings)


# ---------------------------------------------------------------------------
# Thresholds
# ---------------------------------------------------------------------------


@dataclass(frozen=True, slots=True)
class Threshold:
    """One threshold with its provenance.

    `source` is the honest part. `doctrine` means nobody has measured it on this project yet;
    `local` means it was calibrated from this project's own data. A finding produced under a
    doctrine default and one produced under a calibrated value are not comparable, and the
    difference has to survive into storage.
    """

    key: str
    value: Any
    source: str  # "doctrine" | "local" | "fallback"
    note: str = ""

    def as_record(self) -> dict[str, Any]:
        rec: dict[str, Any] = {"key": self.key, "value": self.value, "source": self.source}
        if self.note:
            rec["note"] = self.note
        return rec


class Thresholds:
    """Resolved threshold set: local calibration layered over doctrine defaults.

    Access is recorded. `used()` returns only the thresholds a given run actually read, so a
    finding carries the thresholds that produced it rather than every threshold in the file.
    """

    def __init__(
        self,
        doctrine: dict[str, Any] | None = None,
        local: dict[str, Any] | None = None,
    ) -> None:
        self._doctrine = dict(doctrine or {})
        self._local = dict(local or {})
        self._used: dict[str, Threshold] = {}
        self._notes: dict[str, str] = {}

    def get(self, key: str, fallback: Any = None, note: str = "") -> Any:
        """Read a threshold, recording which layer answered.

        A missing key with no fallback is an error, not a zero. A silent default is how a gate
        stops gating.
        """
        note = note or self._notes.get(key, "")
        if key in self._local:
            th = Threshold(key, self._local[key], "local", note)
        elif key in self._doctrine:
            th = Threshold(key, self._doctrine[key], "doctrine", note)
        elif fallback is not None:
            th = Threshold(key, fallback, "fallback", note or "not present in any threshold file")
        else:
            raise KilnError(
                f"threshold {key!r} is not defined in .kiln/thresholds.yml or the doctrine defaults, "
                f"and no fallback was supplied"
            )
        self._used[key] = th
        return th.value

    def used(self) -> list[dict[str, Any]]:
        """Thresholds read so far, ordered by key for deterministic output."""
        return [self._used[k].as_record() for k in sorted(self._used)]

    def is_calibrated(self, key: str) -> bool:
        return key in self._local

    def reset_usage(self) -> None:
        self._used.clear()

    def override(self, key: str, value: Any, note: str = "") -> None:
        """Override a threshold for this run, e.g. from a command-line flag.

        The override lands in the local layer, so `used()` reports it as `local` and the note
        travels into every finding it produced. That is the whole point: a run with a
        hand-supplied threshold must not be indistinguishable from a calibrated one when someone
        reads the findings back six months later.

        Callers reached into the private layer before this existed, which worked and silently
        dropped the provenance.
        """
        self._local[key] = value
        self._used.pop(key, None)
        if note:
            self._notes[key] = note

    def note_for(self, key: str) -> str:
        return self._notes.get(key, "")


def load_thresholds(
    project_root: Path | str,
    doctrine_defaults: dict[str, Any] | None = None,
    local_path: Path | str | None = None,
) -> Thresholds:
    """Load `.kiln/thresholds.yml` over the doctrine defaults the caller supplies.

    Doctrine defaults are passed in by the script rather than parsed out of markdown. The doctrine
    file is authoritative for humans; duplicating a parser for it in six scripts would create six
    ways to misread it.
    """
    root = Path(project_root)
    path = Path(local_path) if local_path else root / ".kiln" / "thresholds.yml"
    local: dict[str, Any] = {}
    if path.exists():
        try:
            import yaml  # imported lazily so scripts needing no thresholds file have no dependency
        except ImportError as exc:  # pragma: no cover - environment problem, not logic
            raise KilnError("PyYAML is required to read .kiln/thresholds.yml") from exc
        loaded = yaml.safe_load(path.read_text(encoding="utf-8")) or {}
        if not isinstance(loaded, dict):
            raise KilnError(f"{path} must contain a mapping at the top level")
        local = _flatten(loaded)
    return Thresholds(doctrine_defaults, local)


def _flatten(d: dict[str, Any], prefix: str = "") -> dict[str, Any]:
    """Flatten nested threshold mappings to dotted keys.

    `thresholds.yml` is written nested for humans and read flat by scripts.
    """
    out: dict[str, Any] = {}
    for k, v in d.items():
        key = f"{prefix}.{k}" if prefix else str(k)
        if isinstance(v, dict) and not _is_value_mapping(v):
            out.update(_flatten(v, key))
        else:
            out[key] = v["value"] if _is_value_mapping(v) else v
    return out


def _is_value_mapping(v: Any) -> bool:
    """A mapping carrying its own provenance, e.g. {value: 3, calibrated_on: '2026-09-01'}."""
    return isinstance(v, dict) and "value" in v


# ---------------------------------------------------------------------------
# Findings
# ---------------------------------------------------------------------------


@dataclass(slots=True)
class Finding:
    """One machine-produced observation, in the shape every Kiln script emits.

    `thresholds_used` is not optional. Thresholds are recalibrated over time, and a stored finding
    without them cannot be re-read later: nobody can tell whether it fired because the site changed
    or because the number did.
    """

    rule_id: str
    severity: str  # BLOCK | WARN | INFO
    subject: str  # URL, slug, query, cluster id: whatever the rule is about
    message: str
    evidence: dict[str, Any] = field(default_factory=dict)
    thresholds_used: list[dict[str, Any]] = field(default_factory=list)
    locale: str | None = None

    VALID_SEVERITIES = ("BLOCK", "WARN", "INFO")

    def __post_init__(self) -> None:
        if self.severity not in self.VALID_SEVERITIES:
            raise KilnError(
                f"severity {self.severity!r} is not one of {self.VALID_SEVERITIES}. "
                f"The doctrine defines three levels and no synonyms."
            )

    @property
    def blocking(self) -> bool:
        return self.severity == "BLOCK"

    def as_record(self) -> dict[str, Any]:
        rec = asdict(self)
        if self.locale is None:
            rec.pop("locale")
        return rec


def sort_findings(findings: Iterable[Finding]) -> list[Finding]:
    """Total order: severity first, then rule, subject, message.

    The message tiebreak looks redundant and is not. Two findings from one rule about one subject
    do occur, and without it their order depends on dict iteration, which breaks byte-identical
    output.
    """
    rank = {"BLOCK": 0, "WARN": 1, "INFO": 2}
    return sorted(
        findings,
        key=lambda f: (rank[f.severity], f.rule_id, f.subject, f.message),
    )


# ---------------------------------------------------------------------------
# Unicode-aware text
# ---------------------------------------------------------------------------

# Letters, digits and marks, allowing an internal apostrophe or hyphen. The apostrophe matters:
# a naive \w+ splits Ukrainian «п'ять» into two tokens, and every density metric computed on top
# of that is wrong in a way that looks plausible.
_WORD_RE = re.compile(
    r"[^\W\d_]+(?:[’'ʼ\-][^\W\d_]+)*|\d+(?:[.,]\d+)*",
    re.UNICODE,
)

# Sentence terminators including the ones absent from ASCII.
_SENT_SPLIT_RE = re.compile(r"(?<=[.!?…。！？])[\s ]+(?=[^\s])", re.UNICODE)

# Abbreviations that end in a period without ending a sentence. Deliberately short and Latin- and
# Cyrillic-covering; the full problem is unsolvable without a language model and this layer is
# supposed to be deterministic.
_ABBREV = frozenset(
    {
        "e.g", "i.e", "etc", "vs", "mr", "mrs", "ms", "dr", "prof", "inc", "ltd", "co", "fig", "no",
        "напр", "т.д", "т.п", "тис", "млн", "млрд", "грн", "вул", "проф", "др", "рис", "ст",
    }
)


def normalize_text(text: str) -> str:
    """NFC-normalise and collapse whitespace, preserving paragraph breaks.

    NFC matters for Cyrillic: the same visible word can arrive composed or decomposed, and two
    spellings of one word inflate every count that treats them as distinct.
    """
    text = unicodedata.normalize("NFC", text)
    text = text.replace(" ", " ").replace("​", "")
    text = re.sub(r"[ \t]+", " ", text)
    text = re.sub(r"\n{3,}", "\n\n", text)
    return text.strip()


def tokenize_words(text: str) -> list[str]:
    """Unicode word tokens, casefolded. Works for Latin and Cyrillic alike."""
    return [m.group(0).casefold() for m in _WORD_RE.finditer(normalize_text(text))]


def count_words(text: str) -> int:
    """Word count. The only sanctioned way to measure length anywhere in Kiln."""
    return len(tokenize_words(text))


def split_sentences(text: str) -> list[str]:
    """Split into sentences, tolerating common abbreviations.

    Imperfect by design and deterministic, which is the trade the doctrine asks for: sentence-length
    variance is a WARN-level signal, never a gate, so a rare bad split costs nothing that matters.
    """
    text = normalize_text(text)
    if not text:
        return []
    raw = _SENT_SPLIT_RE.split(text)
    out: list[str] = []
    buf = ""
    for part in raw:
        candidate = f"{buf} {part}".strip() if buf else part
        last = candidate.rstrip()
        tail = last.rsplit(" ", 1)[-1].rstrip(".").casefold() if last else ""
        if tail in _ABBREV:
            buf = candidate
            continue
        out.append(candidate.strip())
        buf = ""
    if buf:
        out.append(buf.strip())
    return [s for s in out if s]


def normalize_query(query: str) -> str:
    """Canonical form of a search query for deduplication and joins.

    Casefold, NFC, collapse whitespace. Deliberately does not lemmatise: lemmatisation is
    language-specific, lives in the language pack, and applying a half-measure here would make the
    anchor invariant report clean while guaranteeing nothing for inflected languages.
    """
    return " ".join(normalize_text(query).casefold().split())


# ---------------------------------------------------------------------------
# Deterministic IO
# ---------------------------------------------------------------------------


def dumps(obj: Any, *, indent: int | None = 2) -> str:
    """JSON with sorted keys and real Unicode.

    `ensure_ascii=False` is not cosmetic: escaped Cyrillic makes diffs unreadable, and these files
    are reviewed in pull requests by humans.
    """
    return json.dumps(obj, ensure_ascii=False, sort_keys=True, indent=indent)


def write_json(path: Path | str, obj: Any, *, indent: int | None = 2) -> None:
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(dumps(obj, indent=indent) + "\n", encoding="utf-8", newline="\n")


def read_jsonl(path: Path | str) -> Iterator[dict[str, Any]]:
    """Stream a JSONL file. Blank lines are skipped; a malformed line names itself."""
    path = Path(path)
    if not path.exists():
        raise KilnError(f"input file not found: {path}")
    with path.open("r", encoding="utf-8") as fh:
        for lineno, line in enumerate(fh, 1):
            line = line.strip()
            if not line:
                continue
            try:
                yield json.loads(line)
            except json.JSONDecodeError as exc:
                raise KilnError(f"{path}:{lineno}: malformed JSON: {exc}") from exc


def write_jsonl(path: Path | str, rows: Iterable[Any]) -> int:
    """Write JSONL, one compact object per line. Returns the row count."""
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    n = 0
    with path.open("w", encoding="utf-8", newline="\n") as fh:
        for row in rows:
            fh.write(json.dumps(row, ensure_ascii=False, sort_keys=True) + "\n")
            n += 1
    return n


def stable_key(*parts: Any) -> tuple:
    """Sort key that never raises on mixed or missing values.

    `None` sorts before everything; numbers before strings. Real data has holes, and a sort that
    crashes on one missing field loses a whole run.
    """
    out: list[tuple[int, Any]] = []
    for p in parts:
        if p is None:
            out.append((0, ""))
        elif isinstance(p, bool):
            out.append((1, int(p)))
        elif isinstance(p, (int, float)):
            out.append((1, p))
        else:
            out.append((2, str(p)))
    return tuple(out)


# ---------------------------------------------------------------------------
# CLI
# ---------------------------------------------------------------------------


def base_parser(description: str) -> argparse.ArgumentParser:
    """Argument parser carrying the flags every script accepts.

    `--observe` exists because every threshold in doctrine 0.1.0 is uncalibrated. A gate that
    blocks on a guessed number teaches people to bypass gates, so a project runs in observe mode
    until it has enough of its own data to earn the block.
    """
    p = argparse.ArgumentParser(description=description)
    p.add_argument("--project-root", type=Path, default=Path("."),
                   help="repository root containing .kiln/")
    p.add_argument("--thresholds", type=Path, default=None,
                   help="override path to thresholds.yml")
    p.add_argument("--locale", default=None,
                   help="locale to operate on; required by scripts whose findings are locale-scoped")
    p.add_argument("--out", type=Path, default=None,
                   help="output path; stdout when omitted")
    p.add_argument("--observe", action="store_true",
                   help="downgrade BLOCK findings to WARN and always exit 0")
    return p


def run(main: Callable[[argparse.Namespace], int], parser: argparse.ArgumentParser) -> None:
    """Entry point wrapper: uniform error handling and exit codes.

    Scripts raise; they do not call sys.exit. That keeps them importable, which is how
    `analyze.py` reuses `cannibal_detect.py` instead of reimplementing it and drifting from it.
    """
    args = parser.parse_args()
    try:
        code = main(args)
    except GateFailure as exc:
        if getattr(args, "observe", False):
            print(f"[observe] gate would have failed: {exc}", file=sys.stderr)
            sys.exit(EXIT_OK)
        print(f"gate failed: {exc}", file=sys.stderr)
        sys.exit(EXIT_GATE_FAILED)
    except KilnError as exc:
        print(f"error: {exc}", file=sys.stderr)
        sys.exit(EXIT_ERROR)
    except BrokenPipeError:  # pragma: no cover - shell plumbing
        os._exit(EXIT_OK)
    sys.exit(code if code is not None else EXIT_OK)


def emit(args: argparse.Namespace, payload: Any) -> None:
    """Write the result to --out or stdout, deterministically."""
    if getattr(args, "out", None):
        write_json(args.out, payload)
    else:
        sys.stdout.write(dumps(payload) + "\n")
