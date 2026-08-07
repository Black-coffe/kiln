#!/usr/bin/env python3
"""Opportunity analyser over normalised Search Console rows.

Specification: `doctrine/08-measurement.md` §5 (algorithms), §6 (CTR curves), §11.2 (this script).
The doctrine is authoritative for thresholds, formulas and rule IDs; this file implements them.

This descends from a working `the audited system's analyzer` that read Search Console *exports* rather
than a site's own database. That property is the whole reason it transfers between projects
unchanged, so it is preserved here: no database, no CMS client, no site-specific path. Input is a
directory of JSON/JSONL files, output is one JSON document.

Cannibalization is deliberately absent. `cannibal_detect.py` is the canonical implementation and is
imported, never reimplemented. Two implementations of one calculation diverge the moment either is
touched, and the doctrine cites that exact failure (P8, and the two mutually exclusive rules found
in the owner's previous system).

INPUT CONTRACT
--------------
Rows are the normalised records `gsc_pull.py` writes under `.kiln/measurements/raw/<property>/`.
Each row is a JSON object; `.json` files may hold a list or `{"rows": [...]}`, `.jsonl` one per line.

    {
      "date": "2026-07-06",             # required, ISO
      "query": "кредит онлайн",          # "" when anonymized (MSR-10)
      "page": "https://site/uk/credits", # or "url"
      "clicks": 3,
      "impressions": 120,
      "position": 8.4,                   # API: already 1-based
      "sum_position": 888,               # BigQuery alternative: 0-based, needs +1 (§5.0)
      "locale": "uk",                    # optional; otherwise derived per §0.1
      "is_anonymized_query": false       # optional
    }

Repeated keys are expected and harmless: every aggregation groups before summing, which is what
MSR-09 requires of the BigQuery export.
"""

from __future__ import annotations

import datetime as dt
import importlib
import inspect
import json
import re
import statistics
import sys
from collections import defaultdict
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Callable, Iterable, Sequence
from urllib.parse import urlsplit

sys.path.insert(0, str(Path(__file__).resolve().parent))

from kiln_common import (  # noqa: E402
    EXIT_OK,
    Finding,
    GateFailure,
    KilnError,
    Thresholds,
    base_parser,
    dumps,
    load_thresholds,
    normalize_query,
    read_jsonl,
    run,
    sort_findings,
    stable_key,
    write_json,
)

# ---------------------------------------------------------------------------
# Doctrine defaults
# ---------------------------------------------------------------------------
# Passed in rather than parsed out of the markdown, per the shared module's design: the doctrine
# file is authoritative for humans, and six scripts parsing it would be six ways to misread it.
#
# Where §5 prints two columns, the value below is the one the doctrine selected and the alternative
# is recorded in PRACTICE_ALTERNATIVES. Both are reachable through `.kiln/thresholds.yml`; neither
# is reconciled here, because §14.1 and §14.2 leave that to calibration on project data.

DOCTRINE_DEFAULTS: dict[str, Any] = {
    # MSR-06 — the last days of any window are systematically under-reported.
    "measurement.trim_days": 4,
    # §5.2 striking distance. the reference pilot runs the low threshold as a recorded decision (§14.1): with
    # 4,075 URLs after 29 months of dormancy, the practice threshold of 1,000 impressions returns
    # nothing at all, and a detector that says nothing is indistinguishable from a healthy site.
    "striking.min_impressions": 20,
    "striking.position_min": 5.0,
    "striking.position_max": 20.0,
    "striking.max_ctr": None,  # practice sets 0.02; unset means "no CTR ceiling"
    "striking.result_cap": 50,
    # §5.3 CTR outliers
    "ctr_outliers.min_impressions": 50,
    "ctr_outliers.ratio": 0.5,
    "ctr_outliers.max_position": 10.0,
    # §5.4 decay
    "decay.min_prior_clicks": 50,
    "decay.drop": -0.25,
    "decay.cluster_margin": 0.15,
    "decay.min_cluster_pages": 3,
    # §5.5 rising
    "rising.min_clicks_now": 25,
    "rising.min_delta_clicks": 25,
    "rising.min_impressions": 30,
    # §5.6 query-page mismatch
    "mismatch.min_impressions": 30,
    # §5.8 lost queries. Below 100 prior impressions half the list is anonymization (MSR-07).
    "lost.min_prior_impressions": 100,
    "lost.drop": -0.80,
    # §5.10 coverage gaps
    "gaps.min_impressions": 30,
    "gaps.min_best_position": 20.0,
    # §5.9 seasonality
    "seasonality.min_history_weeks": 52,
    "seasonality.residual_drop": -0.30,
    "seasonality.min_impressions": 100,
    # MSR-04. A project with genuinely no brand (an internal tool, a fresh domain) can set this to
    # false and record that decision, rather than living permanently behind a gate it cannot pass.
    # Silence is not an option here: unsegmented growth metrics look identical to healthy ones.
    "segmentation.require_brand_tokens": True,
    # §6 / MSR-14
    "ctr.prior_curve": "first_page_sage",
    "ctr.aio_multiplier": 0.39,
    "ctr.provisional_below_w": 0.30,
    # §10 / MSR-21
    "mode.steady_state_after_days": 90,
}

PRACTICE_ALTERNATIVES: dict[str, Any] = {
    # Recorded so a human reading a finding can see what the other column said without opening the
    # doctrine. Set any of these in `.kiln/thresholds.yml` to switch; nothing here is applied.
    "striking.min_impressions": 1000,
    "striking.position_min": 4.0,
    "striking.position_max": 15.0,
    "striking.max_ctr": 0.02,
}

# §6 Curve A — clean SERP. [source: First Page Sage 2026 meta-analysis, via indexsy.com]
CTR_PRIOR_FIRST_PAGE_SAGE: dict[int, float] = {
    1: 0.264, 2: 0.121, 3: 0.067, 4: 0.048, 5: 0.034,
    6: 0.029, 7: 0.020, 8: 0.014, 9: 0.012, 10: 0.010,
}

# §6 — the curve from the owner's working code, kept because it differs materially at positions 2–5
# and §14.3 records that which one fits Ukrainian financial SERPs is unknown.
# [internal observation, unpublished: the audited system's analyzer]
CTR_PRIOR_WORKING: dict[int, float] = {
    1: 0.28, 2: 0.15, 3: 0.10, 4: 0.07, 5: 0.05,
    6: 0.04, 7: 0.03, 8: 0.025, 9: 0.02, 10: 0.018,
}

CTR_PRIORS: dict[str, dict[int, float]] = {
    "first_page_sage": CTR_PRIOR_FIRST_PAGE_SAGE,
    "working": CTR_PRIOR_WORKING,
}

TAIL_DECAY = 0.85  # "shrink ~15% per position past 10" [internal observation, unpublished]
TAIL_FLOOR = 0.003

DETECTOR_PREFIX = {
    "cannibalization": "CANNIBAL",
    "striking": "STRIKE",
    "ctr_outliers": "CTROUT",
    "decay": "DECAY",
    "rising": "RISING",
    "mismatch": "MISMATCH",
    "lost": "LOST",
    "gaps": "GAP",
    "seasonality": "SEASON",
    "segmentation": "SEGMENT",
}

ALL_DETECTORS = tuple(DETECTOR_PREFIX)


# ---------------------------------------------------------------------------
# Row model
# ---------------------------------------------------------------------------


@dataclass(slots=True)
class Row:
    """One normalised Search Console record."""

    date: dt.date
    query: str
    page: str
    clicks: int
    impressions: int
    position: float | None
    locale: str | None = None
    anonymized: bool = False

    @property
    def branded_key(self) -> str:
        return normalize_query(self.query)


@dataclass(slots=True)
class Agg:
    """Aggregate over a group of rows.

    Position is accumulated impression-weighted and CTR is recomputed from totals, never averaged
    across rows (MSR-12): a one-impression tail query must not carry the weight of a head term.
    """

    clicks: int = 0
    impressions: int = 0
    _position_weighted: float = 0.0
    _position_impressions: int = 0
    days: set[dt.date] = field(default_factory=set)

    def add(self, row: Row) -> None:
        self.clicks += row.clicks
        self.impressions += row.impressions
        self.days.add(row.date)
        if row.position is not None and row.impressions > 0:
            self._position_weighted += row.position * row.impressions
            self._position_impressions += row.impressions

    @property
    def ctr(self) -> float:
        return self.clicks / self.impressions if self.impressions else 0.0

    @property
    def position(self) -> float | None:
        if not self._position_impressions:
            return None
        return self._position_weighted / self._position_impressions


def aggregate(rows: Iterable[Row], key: Callable[[Row], Any]) -> dict[Any, Agg]:
    """Group then sum. This is the GROUP BY that MSR-09 makes mandatory."""
    out: dict[Any, Agg] = defaultdict(Agg)
    for row in rows:
        out[key(row)].add(row)
    return dict(out)


# ---------------------------------------------------------------------------
# Loading
# ---------------------------------------------------------------------------


def _coerce_row(rec: dict[str, Any], lineno: str) -> Row | None:
    """Parse one record. Returns None for rows carrying no impressions."""
    try:
        date = dt.date.fromisoformat(str(rec["date"])[:10])
    except (KeyError, ValueError) as exc:
        raise KilnError(f"{lineno}: row has no usable 'date': {exc}") from exc

    page = rec.get("page") or rec.get("url") or ""
    query = rec.get("query")
    if query is None:
        query = ""
    impressions = int(rec.get("impressions") or 0)
    clicks = int(rec.get("clicks") or 0)

    position = rec.get("position")
    if position is None and rec.get("sum_position") is not None and impressions:
        # BigQuery `sum_position` is 0-based; §5.0 requires the +1.
        position = float(rec["sum_position"]) / impressions + 1.0
    position = float(position) if position is not None else None

    anonymized = bool(rec.get("is_anonymized_query", False)) or query == ""

    if impressions <= 0:
        return None
    return Row(
        date=date,
        query=str(query),
        page=str(page),
        clicks=clicks,
        impressions=impressions,
        position=position,
        locale=rec.get("locale"),
        anonymized=anonymized,
    )


def load_rows(raw_dir: Path) -> tuple[list[Row], dict[str, Any]]:
    """Read every row file under `raw_dir`, plus `_manifest.json` if present."""
    raw_dir = Path(raw_dir)
    if not raw_dir.exists():
        raise KilnError(f"raw directory not found: {raw_dir}")

    manifest: dict[str, Any] = {}
    manifest_path = raw_dir / "_manifest.json"
    if manifest_path.exists():
        manifest = json.loads(manifest_path.read_text(encoding="utf-8"))

    rows: list[Row] = []
    # Sorted so that a malformed-input error names the same file on every run.
    files = sorted(
        [p for p in raw_dir.iterdir() if p.suffix in (".json", ".jsonl") and not p.name.startswith("_")],
        key=lambda p: p.name,
    )
    if not files:
        raise KilnError(f"no .json or .jsonl row files in {raw_dir}")

    for path in files:
        if path.suffix == ".jsonl":
            for i, rec in enumerate(read_jsonl(path), 1):
                row = _coerce_row(rec, f"{path.name}:{i}")
                if row is not None:
                    rows.append(row)
            continue
        payload = json.loads(path.read_text(encoding="utf-8"))
        if isinstance(payload, dict):
            payload = payload.get("rows", [])
        if not isinstance(payload, list):
            raise KilnError(f"{path}: expected a list of rows or an object with a 'rows' key")
        for i, rec in enumerate(payload, 1):
            row = _coerce_row(rec, f"{path.name}[{i}]")
            if row is not None:
                rows.append(row)

    if not rows:
        raise KilnError(f"{raw_dir} contains no rows with impressions")
    return rows, manifest


def load_config(path: Path | None) -> dict[str, Any]:
    """Read `.kiln/project.yml` (or a JSON equivalent). Absent is not an error."""
    if path is None or not Path(path).exists():
        return {}
    text = Path(path).read_text(encoding="utf-8")
    if Path(path).suffix in (".yml", ".yaml"):
        try:
            import yaml
        except ImportError as exc:  # pragma: no cover - environment problem
            raise KilnError("PyYAML is required to read project.yml") from exc
        return yaml.safe_load(text) or {}
    return json.loads(text)


# ---------------------------------------------------------------------------
# Locale — MSR-22, applied before any threshold
# ---------------------------------------------------------------------------


def _locale_rules(config: dict[str, Any]) -> list[tuple[str, str, str]]:
    """Extract (code, kind, pattern) rules from a project config, tolerating several shapes."""
    raw = config.get("locales") or config.get("locale") or []
    rules: list[tuple[str, str, str]] = []

    def _one(code: str, spec: Any) -> None:
        if isinstance(spec, str):
            rules.append((code, "prefix", spec))
            return
        if not isinstance(spec, dict):
            return
        for key, kind in (
            ("path_prefix", "prefix"), ("url_prefix", "prefix"), ("prefix", "prefix"),
            ("host", "host"), ("subdomain", "host"), ("domain", "host"),
            ("pattern", "regex"), ("regex", "regex"),
        ):
            if spec.get(key):
                rules.append((code, kind, str(spec[key])))
                return

    if isinstance(raw, dict):
        for code, spec in raw.items():
            _one(str(code), spec)
    elif isinstance(raw, list):
        for item in raw:
            if isinstance(item, str):
                rules.append((item, "declared", ""))
            elif isinstance(item, dict):
                code = item.get("code") or item.get("locale") or item.get("lang")
                if code:
                    _one(str(code), item)
    return rules


def resolve_locale(page: str, rules: Sequence[tuple[str, str, str]]) -> str | None:
    """Derive locale from the URL, per §0.1.

    Country is where the searcher was; locale is which page served them, and the two diverge
    constantly. So the `country` dimension is never consulted here.
    """
    if not page:
        return None
    parts = urlsplit(page)
    path = parts.path or "/"
    host = parts.netloc
    for code, kind, pattern in rules:
        if kind == "prefix":
            norm = "/" + pattern.strip("/") + "/"
            if path == norm.rstrip("/") or path.startswith(norm):
                return code
        elif kind == "host" and pattern and host.startswith(pattern):
            return code
        elif kind == "regex" and re.search(pattern, page):
            return code
    return None


def apply_locale(
    rows: list[Row], config: dict[str, Any], requested: str | None
) -> tuple[list[Row], str, list[str]]:
    """Assign and filter locale. Returns (rows, locale, notes).

    Refuses to guess. Mixing locales in one calculation produces an average that describes no
    market (MSR-22), so an unresolvable corpus is an error rather than a silent single bucket.
    """
    notes: list[str] = []
    rules = _locale_rules(config)
    declared = [code for code, _, _ in rules]

    for row in rows:
        if row.locale is None:
            row.locale = resolve_locale(row.page, rules)

    unresolved = [r for r in rows if r.locale is None]
    if unresolved and len(declared) == 1:
        # Single-locale site: everything belongs to it, and saying so is not a guess.
        for row in unresolved:
            row.locale = declared[0]
        notes.append(f"single declared locale '{declared[0]}' applied to all rows")
        unresolved = []

    if unresolved:
        sample = sorted({r.page for r in unresolved})[:3]
        raise KilnError(
            "MSR-22: locale could not be derived for "
            f"{len(unresolved)} rows, e.g. {sample}. Declare `locales` in project.yml with a "
            "path_prefix, host or pattern per locale, or emit `locale` from gsc_pull.py. "
            "Thresholds must never be applied across mixed locales."
        )

    present = sorted({r.locale for r in rows if r.locale})
    if requested:
        if requested not in present:
            raise KilnError(f"locale {requested!r} not present in the data; found {present}")
        rows = [r for r in rows if r.locale == requested]
        return rows, requested, notes
    if len(present) > 1:
        raise KilnError(
            f"data spans locales {present}; pass --locale to pick one. "
            "§0.1 permits one locale per run."
        )
    return rows, present[0], notes


# ---------------------------------------------------------------------------
# Branded segmentation — MSR-04
# ---------------------------------------------------------------------------


def load_brand_tokens(spec: str | None, config: dict[str, Any]) -> list[str]:
    """Load brand tokens from `path`, `path:key`, or the already-loaded project config."""
    tokens: Any = None
    if spec:
        path_part, _, key = str(spec).partition(":")
        path = Path(path_part)
        if not path.exists():
            raise KilnError(f"brand token file not found: {path}")
        data = load_config(path)
        tokens = data.get(key) if key else data
    if tokens is None:
        tokens = config.get("brand_tokens")
    if tokens is None:
        return []
    if isinstance(tokens, str):
        tokens = [tokens]
    return sorted({normalize_query(str(t)) for t in tokens if str(t).strip()})


def is_branded(query: str, tokens: Sequence[str]) -> bool:
    if not tokens:
        return False
    norm = normalize_query(query)
    return any(tok in norm for tok in tokens)


# ---------------------------------------------------------------------------
# CTR curves — §6
# ---------------------------------------------------------------------------


@dataclass(slots=True)
class CtrCurve:
    """Expected CTR by position for one SERP profile.

    `provisional` is the honest flag. MSR-14 forbids absolute traffic forecasts from a public
    curve because studies disagree by 19–39.8% at position one; a curve that is still mostly prior
    can rank tasks against each other and nothing more.
    """

    table: dict[int, float]
    source: str
    profile: str
    min_w: float
    provisional_below: float

    @property
    def provisional(self) -> bool:
        return self.min_w < self.provisional_below

    def expected(self, position: float | None) -> float:
        if position is None:
            return 0.0
        pos = max(1, int(round(position)))
        if pos in self.table:
            return self.table[pos]
        anchor = self.table.get(max(self.table), TAIL_FLOOR)
        steps = pos - max(self.table)
        return max(TAIL_FLOOR, anchor * (TAIL_DECAY ** steps))


def build_ctr_curve(thresholds: Thresholds, locale: str, profile: str = "clean") -> CtrCurve:
    """Calibrated curve when `ctr_calibrate.py` has produced one, otherwise the public prior."""
    calibrated: dict[int, float] = {}
    ws: list[float] = []
    for pos in range(1, 11):
        ctr_key = f"ctr_curves.{locale}.{profile}.{pos}.ctr"
        if thresholds.is_calibrated(ctr_key):
            calibrated[pos] = float(thresholds.get(ctr_key))
            w_key = f"ctr_curves.{locale}.{profile}.{pos}.w"
            ws.append(float(thresholds.get(w_key)) if thresholds.is_calibrated(w_key) else 0.0)

    provisional_below = float(thresholds.get("ctr.provisional_below_w"))
    if calibrated:
        return CtrCurve(
            table=calibrated,
            source="calibrated",
            profile=profile,
            min_w=min(ws) if ws else 0.0,
            provisional_below=provisional_below,
        )

    prior_name = str(thresholds.get("ctr.prior_curve"))
    if prior_name not in CTR_PRIORS:
        raise KilnError(f"unknown ctr.prior_curve {prior_name!r}; known: {sorted(CTR_PRIORS)}")
    table = dict(CTR_PRIORS[prior_name])
    if profile == "aio":
        multiplier = float(thresholds.get("ctr.aio_multiplier"))
        table = {k: v * multiplier for k, v in table.items()}
    return CtrCurve(
        table=table,
        source=f"prior:{prior_name}",
        profile=profile,
        min_w=0.0,
        provisional_below=provisional_below,
    )


def load_serp_profiles(path: Path | None) -> dict[str, str]:
    """Map normalised query -> "clean" | "aio". GSC exposes no such field (§6 step 4)."""
    if path is None or not Path(path).exists():
        return {}
    data = load_config(Path(path))
    if isinstance(data, dict) and "queries" in data:
        data = data["queries"]
    out: dict[str, str] = {}
    for query, value in (data or {}).items():
        if isinstance(value, dict):
            has_aio = bool(value.get("ai_overview") or value.get("aio"))
            profile = "aio" if has_aio else str(value.get("profile", "clean"))
        else:
            profile = "aio" if value in (True, "aio", "ai_overview") else "clean"
        out[normalize_query(str(query))] = "aio" if profile == "aio" else "clean"
    return out


# ---------------------------------------------------------------------------
# Windows — MSR-06
# ---------------------------------------------------------------------------


@dataclass(slots=True)
class Windows:
    now: tuple[dt.date, dt.date]
    prior: tuple[dt.date, dt.date]
    trimmed_days: int
    max_date: dt.date

    def as_record(self) -> dict[str, Any]:
        return {
            "now": [self.now[0].isoformat(), self.now[1].isoformat()],
            "prior": [self.prior[0].isoformat(), self.prior[1].isoformat()],
            "trimmed_days": self.trimmed_days,
        }


def build_windows(rows: Sequence[Row], window: int, compare_window: int, trim_days: int) -> Windows:
    """Two equal-length comparable windows, with the unreliable tail removed.

    Windows are inclusive and exactly `window` days long. Equal length matters: decay compares
    click totals directly, so a 29-day window against a 28-day one manufactures a 3.6% drop out of
    arithmetic alone.
    """
    max_date = max(r.date for r in rows)
    now_end = max_date - dt.timedelta(days=trim_days)
    now_start = now_end - dt.timedelta(days=window - 1)
    prior_end = now_start - dt.timedelta(days=1)
    prior_start = prior_end - dt.timedelta(days=compare_window - 1)
    return Windows((now_start, now_end), (prior_start, prior_end), trim_days, max_date)


def in_window(row: Row, span: tuple[dt.date, dt.date]) -> bool:
    return span[0] <= row.date <= span[1]


# ---------------------------------------------------------------------------
# Grouping helpers
# ---------------------------------------------------------------------------


def url_group(url: str, corpus: dict[str, dict[str, Any]] | None = None) -> str:
    """Cluster for a URL: from the corpus when available, else the first path segment.

    The fallback is a proxy, and findings that rely on it say so, because "we grouped by folder"
    and "we grouped by topic cluster" support different conclusions.
    """
    if corpus:
        entry = corpus.get(url) or corpus.get(urlsplit(url).path)
        if entry:
            cluster = entry.get("cluster") or entry.get("cluster_id")
            if cluster:
                return str(cluster)
    parts = [p for p in urlsplit(url).path.split("/") if p]
    return parts[0] if parts else "(root)"


def load_corpus(path: Path | None) -> dict[str, dict[str, Any]]:
    """`.kiln/corpus.json` keyed by URL. Absent is not an error; it narrows what can be computed."""
    if path is None or not Path(path).exists():
        return {}
    data = load_config(Path(path))
    if isinstance(data, dict) and "pages" in data:
        data = data["pages"]
    if isinstance(data, list):
        return {str(e.get("url") or e.get("page")): e for e in data if e.get("url") or e.get("page")}
    return {str(k): v for k, v in (data or {}).items() if isinstance(v, dict)}


# ---------------------------------------------------------------------------
# Detectors
# ---------------------------------------------------------------------------
# Each reads its thresholds first, snapshots provenance, then produces findings. Reading a
# threshold lazily inside the loop would leave the first findings claiming they used fewer
# thresholds than they did.


def _snapshot(thresholds: Thresholds) -> list[dict[str, Any]]:
    return thresholds.used()


def _finding(
    rule_id: str,
    severity: str,
    subject: str,
    message: str,
    detector: str,
    metrics: dict[str, Any],
    thresholds_used: list[dict[str, Any]],
    locale: str,
    *,
    action: str | None = None,
    tier: str = "automatic",
    extra: dict[str, Any] | None = None,
) -> Finding:
    evidence: dict[str, Any] = {"detector": detector, "metrics": metrics, "tier": tier}
    if action:
        evidence["suggested_action"] = action
    if extra:
        evidence.update(extra)
    return Finding(
        rule_id=rule_id,
        severity=severity,
        subject=subject,
        message=message,
        evidence=evidence,
        thresholds_used=thresholds_used,
        locale=locale,
    )


def detect_striking(
    rows_now: Sequence[Row],
    thresholds: Thresholds,
    curve_for: Callable[[str], CtrCurve],
    locale: str,
) -> list[Finding]:
    """§5.2 — ranked by opportunity, not by impressions.

    Ranking by impressions floats head terms we already win to the top of the queue; the point of
    the score is the gap between what the position should earn and what it does.
    """
    thresholds.reset_usage()
    min_impr = int(thresholds.get("striking.min_impressions"))
    pos_min = float(thresholds.get("striking.position_min"))
    pos_max = float(thresholds.get("striking.position_max"))
    max_ctr = thresholds.get("striking.max_ctr")
    cap = int(thresholds.get("striking.result_cap"))
    used = _snapshot(thresholds)

    grouped = aggregate(rows_now, lambda r: (r.query, r.page))
    scored: list[tuple[float, tuple[str, str], Agg, CtrCurve]] = []
    for (query, page), agg in grouped.items():
        if agg.impressions < min_impr or agg.position is None:
            continue
        if not (pos_min <= agg.position <= pos_max):
            continue
        if max_ctr is not None and agg.ctr >= float(max_ctr):
            continue
        curve = curve_for(query)
        gap = curve.expected(agg.position) - agg.ctr
        if gap <= 0:
            continue
        scored.append((agg.impressions * gap, (query, page), agg, curve))

    scored.sort(key=lambda item: (-item[0], stable_key(item[1][0], item[1][1])))

    findings: list[Finding] = []
    for score, (query, page), agg, curve in scored[:cap]:
        action = "rewrite_title_and_meta" if agg.position <= 7 else "strengthen_content_and_links"
        findings.append(
            _finding(
                rule_id="MSR-23",
                severity="WARN",
                subject=f"{query} → {page}",
                message=(
                    f"position {agg.position:.1f} earns {agg.ctr:.3f} CTR against "
                    f"{curve.expected(agg.position):.3f} expected"
                ),
                detector="striking",
                metrics={
                    "query": query,
                    "page": page,
                    "impressions": agg.impressions,
                    "clicks": agg.clicks,
                    "position": round(agg.position, 2),
                    "ctr_actual": round(agg.ctr, 5),
                    "ctr_expected": round(curve.expected(agg.position), 5),
                    "opportunity_score": round(score, 2),
                    "serp_profile": curve.profile,
                    "ctr_curve_source": curve.source,
                    "provisional": curve.provisional,
                },
                thresholds_used=used,
                locale=locale,
                action=action,
                tier="semi_automatic",
            )
        )
    return findings


def detect_ctr_outliers(
    rows_now: Sequence[Row],
    thresholds: Thresholds,
    curve_for: Callable[[str], CtrCurve],
    locale: str,
) -> list[Finding]:
    """§5.3 — relative under-performance only.

    The comment travelling with this threshold in the original source is worth keeping: the curve
    flags relative under-performance and is not ground truth.
    """
    thresholds.reset_usage()
    min_impr = int(thresholds.get("ctr_outliers.min_impressions"))
    ratio = float(thresholds.get("ctr_outliers.ratio"))
    max_pos = float(thresholds.get("ctr_outliers.max_position"))
    used = _snapshot(thresholds)

    grouped = aggregate(rows_now, lambda r: (r.query, r.page))
    findings: list[Finding] = []
    for (query, page), agg in sorted(grouped.items(), key=lambda kv: stable_key(*kv[0])):
        if agg.impressions < min_impr or agg.position is None or agg.position > max_pos:
            continue
        curve = curve_for(query)
        expected = curve.expected(agg.position)
        if expected <= 0 or agg.ctr >= ratio * expected:
            continue
        findings.append(
            _finding(
                rule_id="MSR-24",
                severity="WARN",
                subject=f"{query} → {page}",
                message=(
                    f"CTR {agg.ctr:.3f} is below {ratio:g}× the {expected:.3f} expected at "
                    f"position {agg.position:.1f}"
                ),
                detector="ctr_outliers",
                metrics={
                    "query": query,
                    "page": page,
                    "impressions": agg.impressions,
                    "clicks": agg.clicks,
                    "position": round(agg.position, 2),
                    "ctr_actual": round(agg.ctr, 5),
                    "ctr_expected": round(expected, 5),
                    "shortfall_ratio": round(agg.ctr / expected, 3) if expected else None,
                    "serp_profile": curve.profile,
                    "provisional": curve.provisional,
                },
                thresholds_used=used,
                locale=locale,
                action="rewrite_title_and_meta",
                tier="semi_automatic",
            )
        )
    return findings


def detect_decay(
    rows_now: Sequence[Row],
    rows_prior: Sequence[Row],
    thresholds: Thresholds,
    locale: str,
    corpus: dict[str, dict[str, Any]] | None = None,
) -> list[Finding]:
    """§5.4 — with the cluster differencing that keeps it from being pure noise.

    A page that fell while its whole cluster fell has not decayed; demand or the SERP moved, and
    the remedy is different. Only the excess over the cluster median is treated as decay.
    """
    thresholds.reset_usage()
    min_prior = int(thresholds.get("decay.min_prior_clicks"))
    drop = float(thresholds.get("decay.drop"))
    margin = float(thresholds.get("decay.cluster_margin"))
    min_cluster = int(thresholds.get("decay.min_cluster_pages"))
    used = _snapshot(thresholds)

    now = aggregate(rows_now, lambda r: r.page)
    prior = aggregate(rows_prior, lambda r: r.page)

    changes: dict[str, float] = {}
    for page, prior_agg in prior.items():
        if prior_agg.clicks <= 0:
            continue
        now_clicks = now[page].clicks if page in now else 0
        changes[page] = (now_clicks - prior_agg.clicks) / prior_agg.clicks

    by_cluster: dict[str, list[float]] = defaultdict(list)
    for page, change in changes.items():
        by_cluster[url_group(page, corpus)].append(change)
    cluster_median = {c: statistics.median(v) for c, v in by_cluster.items()}
    grouping = "corpus_cluster" if corpus else "url_path_segment"

    findings: list[Finding] = []
    for page in sorted(changes):
        prior_agg = prior[page]
        if prior_agg.clicks < min_prior:
            continue
        change = changes[page]
        if change > drop:
            continue

        cluster = url_group(page, corpus)
        peers = by_cluster[cluster]
        median = cluster_median[cluster]
        differenced = len(peers) >= min_cluster
        excess = change - median
        if differenced and excess > -margin:
            continue  # the cluster moved together: demand or SERP, not this page

        now_clicks = now[page].clicks if page in now else 0
        findings.append(
            _finding(
                rule_id="MSR-25",
                severity="WARN",
                subject=page,
                message=(
                    f"clicks fell {change:+.0%} ({prior_agg.clicks} → {now_clicks}); "
                    + (
                        f"cluster median {median:+.0%}, excess {excess:+.0%}"
                        if differenced
                        else f"cluster has {len(peers)} pages, too few to difference against"
                    )
                ),
                detector="decay",
                metrics={
                    "page": page,
                    "clicks_prior": prior_agg.clicks,
                    "clicks_now": now_clicks,
                    "relative_change": round(change, 4),
                    "cluster": cluster,
                    "cluster_median_change": round(median, 4),
                    "excess_over_cluster": round(excess, 4),
                    "cluster_differencing": "applied" if differenced else "insufficient_pages",
                    "cluster_grouping": grouping,
                },
                thresholds_used=used,
                locale=locale,
                action="refresh_or_consolidate",
                tier="semi_automatic",
                extra={
                    "note": (
                        "re-measuring sooner than 4 weeks after a fix is forbidden as a basis for "
                        "further action; reindexing takes 4-12 weeks (§5.4)"
                    )
                },
            )
        )
    return findings


def detect_rising(
    rows_now: Sequence[Row],
    rows_prior: Sequence[Row],
    thresholds: Thresholds,
    locale: str,
) -> list[Finding]:
    """§5.5 — it is cheaper to win where momentum already exists."""
    thresholds.reset_usage()
    min_clicks = int(thresholds.get("rising.min_clicks_now"))
    min_delta = int(thresholds.get("rising.min_delta_clicks"))
    min_impr = int(thresholds.get("rising.min_impressions"))
    used = _snapshot(thresholds)

    findings: list[Finding] = []
    for scope, key in (("query", lambda r: r.query), ("page", lambda r: r.page)):
        now = aggregate(rows_now, key)
        prior = aggregate(rows_prior, key)
        for subject in sorted(now):
            agg = now[subject]
            if not subject or agg.clicks < min_clicks or agg.impressions < min_impr:
                continue
            prior_clicks = prior[subject].clicks if subject in prior else None
            if prior_clicks is not None and agg.clicks - prior_clicks < min_delta:
                continue
            findings.append(
                _finding(
                    rule_id="MSR-26",
                    severity="INFO",
                    subject=subject,
                    message=(
                        f"{scope} rising: {prior_clicks if prior_clicks is not None else 'no prior'}"
                        f" → {agg.clicks} clicks"
                    ),
                    detector="rising",
                    metrics={
                        "scope": scope,
                        "clicks_now": agg.clicks,
                        "clicks_prior": prior_clicks,
                        "impressions_now": agg.impressions,
                        "position_now": round(agg.position, 2) if agg.position else None,
                    },
                    thresholds_used=used,
                    locale=locale,
                    action="reinforce_internal_links_and_expand",
                    tier="semi_automatic",
                )
            )
    return findings


def detect_lost(
    rows_now: Sequence[Row],
    rows_prior: Sequence[Row],
    thresholds: Thresholds,
    locale: str,
) -> list[Finding]:
    """§5.8 — the high prior threshold is deliberate.

    Below 100 prior impressions, half the list is queries that merely fell under the privacy
    cutoff (MSR-07), and a detector reporting anonymization as a loss trains people to ignore it.
    """
    thresholds.reset_usage()
    min_prior = int(thresholds.get("lost.min_prior_impressions"))
    drop = float(thresholds.get("lost.drop"))
    used = _snapshot(thresholds)

    now = aggregate(rows_now, lambda r: r.query)
    prior = aggregate(rows_prior, lambda r: r.query)

    findings: list[Finding] = []
    for query in sorted(prior):
        if not query:
            continue  # anonymized (MSR-10)
        prior_impr = prior[query].impressions
        if prior_impr < min_prior:
            continue
        now_impr = now[query].impressions if query in now else 0
        change = (now_impr - prior_impr) / prior_impr
        if now_impr != 0 and change > drop:
            continue
        findings.append(
            _finding(
                rule_id="MSR-28",
                severity="WARN",
                subject=query,
                message=f"impressions fell {change:+.0%} ({prior_impr} → {now_impr})",
                detector="lost",
                metrics={
                    "query": query,
                    "impressions_prior": prior_impr,
                    "impressions_now": now_impr,
                    "relative_change": round(change, 4),
                },
                thresholds_used=used,
                locale=locale,
                action="inspect_index_status_and_serp",
                tier="manual",
                extra={
                    "note": (
                        "URL Inspection is capped at 2,000/day per site (MSR-05); inspect only "
                        "flagged URLs"
                    )
                },
            )
        )
    return findings


def detect_gaps(rows_now: Sequence[Row], thresholds: Thresholds, locale: str) -> list[Finding]:
    """§5.10 — demand confirmed, the page does not reach. Rework queue, not a new article."""
    thresholds.reset_usage()
    min_impr = int(thresholds.get("gaps.min_impressions"))
    min_pos = float(thresholds.get("gaps.min_best_position"))
    used = _snapshot(thresholds)

    per_pair = aggregate(rows_now, lambda r: (r.query, r.page))
    best: dict[str, tuple[float, str]] = {}
    totals: dict[str, int] = defaultdict(int)
    for (query, page), agg in per_pair.items():
        totals[query] += agg.impressions
        if agg.position is None:
            continue
        if query not in best or agg.position < best[query][0]:
            best[query] = (agg.position, page)

    findings: list[Finding] = []
    for query in sorted(best):
        position, page = best[query]
        impressions = totals[query]
        if not query or impressions < min_impr or position <= min_pos:
            continue
        findings.append(
            _finding(
                rule_id="MSR-31",
                severity="INFO",
                subject=query,
                message=f"{impressions} impressions but best position {position:.1f}",
                detector="gaps",
                metrics={
                    "query": query,
                    "impressions": impressions,
                    "best_position": round(position, 2),
                    "best_page": page,
                },
                thresholds_used=used,
                locale=locale,
                action="rework_existing_page",
                tier="semi_automatic",
            )
        )
    return findings


def detect_mismatch(
    rows_now: Sequence[Row],
    thresholds: Thresholds,
    locale: str,
    intents: dict[str, str],
    expected_by_page: dict[str, str],
) -> list[Finding]:
    """§5.6 — needs the intent classification and page types from `02-semantics.md`."""
    thresholds.reset_usage()
    min_impr = int(thresholds.get("mismatch.min_impressions"))
    used = _snapshot(thresholds)

    per_pair = aggregate(rows_now, lambda r: (r.query, r.page))
    top_page: dict[str, tuple[int, str]] = {}
    for (query, page), agg in per_pair.items():
        current = top_page.get(query)
        if current is None or agg.impressions > current[0]:
            top_page[query] = (agg.impressions, page)

    findings: list[Finding] = []
    for query in sorted(top_page):
        impressions, page = top_page[query]
        if not query or impressions < min_impr:
            continue
        query_intent = intents.get(normalize_query(query))
        page_intent = expected_by_page.get(page) or expected_by_page.get(urlsplit(page).path)
        if not query_intent or not page_intent or query_intent == page_intent:
            continue
        findings.append(
            _finding(
                rule_id="MSR-27",
                severity="WARN",
                subject=f"{query} → {page}",
                message=f"query intent {query_intent!r} against page intent {page_intent!r}",
                detector="mismatch",
                metrics={
                    "query": query,
                    "page": page,
                    "impressions": impressions,
                    "query_intent": query_intent,
                    "page_intent": page_intent,
                },
                thresholds_used=used,
                locale=locale,
                action="rework_page_intent_or_create_missing_page",
                tier="manual",
            )
        )
    return findings


def detect_seasonality(
    rows_all: Sequence[Row],
    windows: Windows,
    thresholds: Thresholds,
    locale: str,
) -> list[Finding]:
    """§5.9 — year over year by ISO week.

    Without YoY every seasonal dip reads as decay. When history is too short to compare, that fact
    is itself the finding: it is the operational argument for MSR-08, and silence would hide it.
    """
    thresholds.reset_usage()
    min_weeks = int(thresholds.get("seasonality.min_history_weeks"))
    residual_drop = float(thresholds.get("seasonality.residual_drop"))
    min_impr = int(thresholds.get("seasonality.min_impressions"))
    used = _snapshot(thresholds)

    by_week: dict[tuple[int, int], Agg] = defaultdict(Agg)
    for row in rows_all:
        iso = row.date.isocalendar()
        by_week[(iso.year, iso.week)].add(row)

    if not by_week:
        return []

    span_days = (max(r.date for r in rows_all) - min(r.date for r in rows_all)).days
    if span_days < min_weeks * 7:
        return [
            _finding(
                # MSR-30, not MSR-29: this reports that the comparison could not be made, and its
                # action is to enable the export. Sharing an ID with the result would make
                # "no history" indistinguishable from "no seasonality" in the rule counters.
                rule_id="MSR-30",
                severity="INFO",
                subject="(corpus)",
                message=(
                    f"history spans {span_days} days; {min_weeks} weeks are needed for a "
                    "year-over-year comparison, so seasonal dips cannot be told from decay"
                ),
                detector="seasonality",
                metrics={
                    "history_days": span_days,
                    "required_days": min_weeks * 7,
                    "status": "insufficient_history",
                },
                thresholds_used=used,
                locale=locale,
                action="enable_bigquery_export",
                tier="manual",
                extra={
                    "note": (
                        "the export has no backfill (MSR-08); every day of delay is lost "
                        "permanently"
                    )
                },
            )
        ]

    findings: list[Finding] = []
    now_weeks = sorted(
        {(d.isocalendar().year, d.isocalendar().week)
         for d in _dates_in(windows.now)}
    )
    for year, week in now_weeks:
        current = by_week.get((year, week))
        previous = by_week.get((year - 1, week))
        if current is None or previous is None:
            continue
        if previous.impressions < min_impr:
            continue
        change = (current.impressions - previous.impressions) / previous.impressions
        if change > residual_drop:
            continue
        findings.append(
            _finding(
                rule_id="MSR-29",
                severity="INFO",
                subject=f"{year}-W{week:02d}",
                message=(
                    f"impressions {change:+.0%} year over year "
                    f"({previous.impressions} → {current.impressions})"
                ),
                detector="seasonality",
                metrics={
                    "iso_year": year,
                    "iso_week": week,
                    "impressions_now": current.impressions,
                    "impressions_year_ago": previous.impressions,
                    "yoy_change": round(change, 4),
                },
                thresholds_used=used,
                locale=locale,
                tier="automatic",
            )
        )
    return findings


def _dates_in(span: tuple[dt.date, dt.date]) -> list[dt.date]:
    days = (span[1] - span[0]).days
    return [span[0] + dt.timedelta(days=i) for i in range(days + 1)]


def check_segmentation(
    brand_tokens: Sequence[str], thresholds: Thresholds, locale: str
) -> list[Finding]:
    """MSR-04 — growth metrics are computed on the non-branded segment only.

    With no brand token list there is no segmentation, so the rule cannot be honoured. That is a
    BLOCK in the doctrine, and reporting it as a gentle note would be exactly the failure mode the
    severity ladder exists to prevent. `--observe` is the sanctioned way through during onboarding.
    """
    thresholds.reset_usage()
    required = bool(thresholds.get("segmentation.require_brand_tokens"))
    used = _snapshot(thresholds)
    if brand_tokens:
        return []
    return [
        _finding(
            rule_id="MSR-04",
            severity="BLOCK" if required else "INFO",
            subject="(project)",
            message=(
                "no brand tokens configured, so growth metrics cannot be restricted to the "
                "non-branded segment; branded growth is a marketing result and masks a content "
                "failure"
                + ("" if required else " (waived: segmentation.require_brand_tokens is false)")
            ),
            detector="segmentation",
            metrics={"brand_tokens": 0, "required": required},
            thresholds_used=used,
            locale=locale,
            action="declare_brand_tokens_in_project_yml",
            tier="manual",
        )
    ]


# ---------------------------------------------------------------------------
# Cannibalization — imported, never reimplemented
# ---------------------------------------------------------------------------


def run_cannibalization(
    rows: Sequence[Row],
    *,
    project_root: Path,
    thresholds_path: Path | None,
    locale: str,
    brand_tokens: Sequence[str],
    today: dt.date,
) -> tuple[list[Finding] | None, str | None]:
    """Delegate to the canonical implementation in `cannibal_detect.py`.

    Contract: it receives locale-filtered, non-branded rows as plain dicts spanning the full
    available history, and applies its own 28-day detection and 90-day decision windows (§5.1).

    Two details are load-bearing and were both found by running this against the real module
    rather than a stub:

    * **Each script owns its own doctrine defaults.** A `Thresholds` built from this file's
      defaults has none of `cannibalization.*`, so the callee's first threshold read raises. The
      callee's declared defaults are therefore merged in and the object rebuilt, which keeps each
      script authoritative for its own numbers instead of forcing one global table.
    * **`today` is pinned to the data, not the wall clock.** The callee trims and windows relative
      to `today`; left at its default the same export would analyse differently tomorrow, which
      breaks both determinism and any comparison between runs.

    Unavailability is reported, never swallowed: LI-7 is a leading indicator, and a missing
    detector that reads as "no cannibalization found" is worse than an obvious hole.
    """
    try:
        module = importlib.import_module("cannibal_detect")
    except ImportError as exc:
        return None, f"cannibal_detect.py not importable: {exc}"

    detect = getattr(module, "detect", None)
    if detect is None or not callable(detect):
        return None, "cannibal_detect.py provides no callable detect()"

    merged = dict(getattr(module, "DOCTRINE_DEFAULTS", {}))
    merged.update(DOCTRINE_DEFAULTS)
    callee_thresholds = load_thresholds(project_root, merged, thresholds_path)

    payload = [
        {
            "date": r.date.isoformat(),
            "query": r.query,
            "page": r.page,
            "clicks": r.clicks,
            "impressions": r.impressions,
            "position": r.position,
            "locale": r.locale,
        }
        for r in rows
    ]

    # Only the positional `(rows, thresholds, locale)` part is contractual, so the optional
    # keywords are offered by inspection rather than by catching TypeError, which would swallow a
    # genuine type bug raised inside the callee.
    params = inspect.signature(detect).parameters
    takes_kwargs = any(p.kind is inspect.Parameter.VAR_KEYWORD for p in params.values())
    extra: dict[str, Any] = {}
    if takes_kwargs or "brand_tokens" in params:
        extra["brand_tokens"] = tuple(brand_tokens)
    if takes_kwargs or "today" in params:
        extra["today"] = today

    try:
        result = list(detect(payload, callee_thresholds, locale=locale, **extra))
    except KilnError as exc:
        # A broken sibling must not take the other seven detectors down with it, but it must be
        # impossible to mistake for a clean result.
        return None, f"cannibal_detect.detect() failed: {exc}"

    for finding in result:
        finding.evidence.setdefault("detector", "cannibalization")
    return result, None


# ---------------------------------------------------------------------------
# Leading indicators — MSR-01
# ---------------------------------------------------------------------------


def leading_indicators(
    rows_all: Sequence[Row],
    rows_now: Sequence[Row],
    rows_prior: Sequence[Row],
    windows: Windows,
    corpus: dict[str, dict[str, Any]],
    cannibal_findings: Sequence[Finding] | None,
    imported: dict[str, Any],
) -> tuple[dict[str, Any], dict[str, str]]:
    """The eight indicators. All eight keys are always present (MSR-01).

    What cannot be computed is `null` with a stated reason rather than an invented number: the set
    is fixed for a quarter, so a key that appears and disappears makes windows incomparable.
    """
    li: dict[str, Any] = {}
    unavailable: dict[str, str] = {}

    first_impression: dict[str, dt.date] = {}
    for row in rows_all:
        prev = first_impression.get(row.page)
        if prev is None or row.date < prev:
            first_impression[row.page] = row.date

    # LI-1, LI-2 need publication dates, which live in the corpus.
    published: list[tuple[str, dt.date]] = []
    for url, entry in corpus.items():
        raw = entry.get("published_at") or entry.get("first_published")
        if not raw:
            continue
        try:
            published.append((url, dt.date.fromisoformat(str(raw)[:10])))
        except ValueError:
            continue

    if published:
        in_scope = [(u, d) for u, d in published if windows.now[0] <= d <= windows.now[1]]
        if in_scope:
            indexed = sum(1 for u, _ in in_scope if u in first_impression)
            li["LI-1_indexation_rate"] = round(indexed / len(in_scope), 4)
        else:
            li["LI-1_indexation_rate"] = None
            unavailable["LI-1_indexation_rate"] = "no pages published inside the window"
        lags = [
            (first_impression[u] - d).days
            for u, d in published
            if u in first_impression and first_impression[u] >= d
        ]
        li["LI-2_days_to_first_impression_median"] = (
            int(statistics.median(lags)) if lags else None
        )
        if not lags:
            unavailable["LI-2_days_to_first_impression_median"] = "no page has both a publication date and an impression"
    else:
        li["LI-1_indexation_rate"] = None
        li["LI-2_days_to_first_impression_median"] = None
        unavailable["LI-1_indexation_rate"] = "corpus.json absent or carries no publication dates"
        unavailable["LI-2_days_to_first_impression_median"] = unavailable["LI-1_indexation_rate"]

    # LI-3 impression-weighted position shift.
    now_q = aggregate(rows_now, lambda r: r.query)
    prior_q = aggregate(rows_prior, lambda r: r.query)
    shared = [q for q in now_q if q and q in prior_q]
    weight = sum(now_q[q].impressions for q in shared)
    if weight:
        shift = sum(
            (now_q[q].position - prior_q[q].position) * now_q[q].impressions
            for q in shared
            if now_q[q].position is not None and prior_q[q].position is not None
        )
        li["LI-3_position_shift_weighted"] = round(shift / weight, 3)
    else:
        li["LI-3_position_shift_weighted"] = None
        unavailable["LI-3_position_shift_weighted"] = "no query appears in both windows"

    # LI-4 share of queries in the visible band, overall and per cluster.
    per_pair = aggregate(rows_now, lambda r: (r.query, r.page))
    best_pos: dict[str, float] = {}
    query_cluster: dict[str, str] = {}
    for (query, page), agg in per_pair.items():
        if not query or agg.position is None:
            continue
        if query not in best_pos or agg.position < best_pos[query]:
            best_pos[query] = agg.position
            query_cluster[query] = url_group(page, corpus)
    if best_pos:
        visible = sum(1 for p in best_pos.values() if p <= 20)
        li["LI-4_visible_query_share"] = round(visible / len(best_pos), 4)
        by_cluster: dict[str, list[float]] = defaultdict(list)
        for query, pos in best_pos.items():
            by_cluster[query_cluster[query]].append(pos)
        li["LI-4_visible_query_share_by_cluster"] = {
            cluster: round(sum(1 for p in positions if p <= 20) / len(positions), 4)
            for cluster, positions in sorted(by_cluster.items())
        }
    else:
        li["LI-4_visible_query_share"] = None
        unavailable["LI-4_visible_query_share"] = "no query carries a position in the window"

    # LI-5 belongs to 09-geo; GSC cannot produce it (MSR-15).
    li["LI-5_ai_citation_rate"] = imported.get("ai_citation_rate")
    if li["LI-5_ai_citation_rate"] is None:
        unavailable["LI-5_ai_citation_rate"] = "computed in 09-geo; pass --geo to import it (MSR-15)"

    li["LI-6_defects_closed"] = imported.get("defects_closed")
    if li["LI-6_defects_closed"] is None:
        unavailable["LI-6_defects_closed"] = "pass --defects with the onboarding defect register"

    if cannibal_findings is None:
        li["LI-7_cannibalized_queries"] = None
        unavailable["LI-7_cannibalized_queries"] = "cannibal_detect.py unavailable"
    else:
        li["LI-7_cannibalized_queries"] = len({f.subject for f in cannibal_findings})

    rejection = imported.get("rejection")
    li["LI-8_rejection"] = rejection
    if rejection is None:
        unavailable["LI-8_rejection"] = (
            "pass --rejection with the draft gate log; this is Kiln's primary measure (MSR-02)"
        )

    return li, unavailable


# ---------------------------------------------------------------------------
# Output
# ---------------------------------------------------------------------------


def to_record(finding: Finding, seq: int) -> dict[str, Any]:
    """Render a Finding in the output schema §11.2 defines."""
    evidence = dict(finding.evidence)
    detector = evidence.pop("detector", "unknown")
    metrics = evidence.pop("metrics", {})
    tier = evidence.pop("tier", "automatic")
    action = evidence.pop("suggested_action", None)
    record: dict[str, Any] = {
        "id": f"{DETECTOR_PREFIX.get(detector, detector.upper())}-{seq:04d}",
        "type": detector,
        "rule_id": finding.rule_id,
        "severity": finding.severity,
        "subject": finding.subject,
        "message": finding.message,
        "metrics": metrics,
        "thresholds_used": finding.thresholds_used,
        "tier": tier,
        "state": "new",
    }
    if finding.locale:
        record["locale"] = finding.locale
    if action:
        record["suggested_action"] = action
    if evidence:
        record["evidence"] = evidence
    return record


def summarise(findings: Sequence[Finding]) -> dict[str, Any]:
    """Counts by detector and by severity, so the report needs no second pass over findings."""
    by_detector: dict[str, int] = defaultdict(int)
    by_severity: dict[str, int] = defaultdict(int)
    by_detector_severity: dict[str, dict[str, int]] = defaultdict(lambda: defaultdict(int))
    for finding in findings:
        detector = finding.evidence.get("detector", "unknown")
        by_detector[detector] += 1
        by_severity[finding.severity] += 1
        by_detector_severity[detector][finding.severity] += 1
    return {
        "total": len(findings),
        "by_severity": {k: by_severity[k] for k in sorted(by_severity)},
        "by_detector": {k: by_detector[k] for k in sorted(by_detector)},
        "by_detector_severity": {
            detector: {sev: counts[sev] for sev in sorted(counts)}
            for detector, counts in sorted(by_detector_severity.items())
        },
    }


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------


def build_parser():
    parser = base_parser(__doc__.split("\n", 1)[0])
    parser.add_argument("--raw", type=Path, required=True,
                        help="directory of normalised rows from gsc_pull.py")
    parser.add_argument("--window", type=int, default=28)
    parser.add_argument("--compare-window", type=int, default=28)
    parser.add_argument("--project-config", type=Path, default=None,
                        help="path to project.yml; defaults to <project-root>/.kiln/project.yml")
    parser.add_argument("--brand-tokens", default=None,
                        help="path, or path:key, holding the brand token list")
    parser.add_argument("--serp-profiles", type=Path, default=None,
                        help="query -> clean|aio map; GSC exposes no such field")
    parser.add_argument("--corpus", type=Path, default=None,
                        help="corpus.json: clusters, publication dates, page intents")
    parser.add_argument("--intents", type=Path, default=None,
                        help="query -> intent map from 02-semantics")
    parser.add_argument("--geo", type=Path, default=None, help="LI-5 input from 09-geo")
    parser.add_argument("--defects", type=Path, default=None, help="LI-6 defect register")
    parser.add_argument("--rejection", type=Path, default=None, help="LI-8 draft gate log")
    parser.add_argument("--detectors", default=",".join(ALL_DETECTORS),
                        help=f"comma-separated subset of: {','.join(ALL_DETECTORS)}")
    parser.add_argument("--mode", choices=("auto", "cold_start", "steady_state"), default="auto")
    parser.add_argument("--now", default=None,
                        help="ISO timestamp for generated_at; set it to make output reproducible")
    parser.add_argument("--dry-run", action="store_true", help="print, write nothing")
    return parser


def main(args) -> int:
    requested = [d.strip() for d in str(args.detectors).split(",") if d.strip()]
    unknown = [d for d in requested if d not in ALL_DETECTORS]
    if unknown:
        raise KilnError(f"unknown detectors {unknown}; known: {list(ALL_DETECTORS)}")

    project_root = Path(args.project_root)
    config_path = args.project_config or (project_root / ".kiln" / "project.yml")
    config = load_config(config_path)
    thresholds = load_thresholds(project_root, DOCTRINE_DEFAULTS, args.thresholds)

    rows, manifest = load_rows(args.raw)
    rows, locale, locale_notes = apply_locale(rows, config, args.locale)

    warnings: list[str] = list(locale_notes)

    trim_days = int(thresholds.get("measurement.trim_days"))
    windows = build_windows(rows, args.window, args.compare_window, trim_days)

    # MSR-07: the query slice never reconciles with the property total. Say so on its own line
    # rather than letting somebody compute a share from it.
    anonymized_impressions = sum(r.impressions for r in rows if r.anonymized)
    total_impressions = sum(r.impressions for r in rows)
    anonymized_share = anonymized_impressions / total_impressions if total_impressions else 0.0
    warnings.append(
        f"anonymized_share={anonymized_share:.2f} - query sums do not reconcile with the property "
        f"total (MSR-07); never compute a query's share of total traffic from this slice"
    )

    # MSR-11: an epoch_version bump means Google rewrote history. Never recompute silently.
    epochs = manifest.get("epoch_versions") or {}
    if epochs:
        warnings.append(
            f"epoch_versions present for {len(epochs)} dates (MSR-11); conclusions drawn on an "
            "earlier version require re-verification"
        )

    brand_tokens = load_brand_tokens(args.brand_tokens, config)
    non_branded = [r for r in rows if r.query and not is_branded(r.query, brand_tokens)]
    branded = [r for r in rows if r.query and is_branded(r.query, brand_tokens)]

    rows_now = [r for r in non_branded if in_window(r, windows.now)]
    rows_prior = [r for r in non_branded if in_window(r, windows.prior)]
    if not rows_now:
        raise KilnError(
            f"no non-branded rows inside {windows.now[0]}..{windows.now[1]} after trimming "
            f"{trim_days} days (MSR-06)"
        )

    history_days = (windows.max_date - min(r.date for r in rows)).days
    if args.mode == "auto":
        steady_after = int(thresholds.get("mode.steady_state_after_days"))
        mode = "steady_state" if history_days >= steady_after else "cold_start"
    else:
        mode = args.mode
    if mode == "cold_start":
        warnings.append(
            "mode=cold_start (MSR-21): conclusions are labelled as such, thresholds sit at the "
            "bottom of their range and the cohort monitor is inactive"
        )

    profiles = load_serp_profiles(args.serp_profiles)
    curves = {p: build_ctr_curve(thresholds, locale, p) for p in ("clean", "aio")}

    def curve_for(query: str) -> CtrCurve:
        return curves[profiles.get(normalize_query(query), "clean")]

    if any(c.provisional for c in curves.values()):
        warnings.append(
            "CTR curve is still mostly prior (MSR-14): potential estimates are provisional and "
            "absolute traffic forecasts from them are forbidden"
        )
    if not profiles:
        warnings.append(
            "no SERP profile map supplied: every query is scored on the clean curve, which "
            "overstates the opportunity on queries carrying an AI Overview (§5.2)"
        )

    corpus = load_corpus(args.corpus)
    intents_raw = load_config(args.intents) if args.intents else {}
    intents = {
        normalize_query(str(k)): str(v.get("intent") if isinstance(v, dict) else v)
        for k, v in (intents_raw.get("queries", intents_raw) or {}).items()
    }
    expected_by_page = {
        url: str(entry.get("expected_intent") or entry.get("intent"))
        for url, entry in corpus.items()
        if entry.get("expected_intent") or entry.get("intent")
    }

    imported: dict[str, Any] = {}
    if args.geo:
        geo = load_config(args.geo)
        imported["ai_citation_rate"] = geo.get("citation_rate", geo.get("LI-5_ai_citation_rate"))
    if args.defects:
        defects = load_config(args.defects)
        imported["defects_closed"] = defects.get("closed")
    if args.rejection:
        imported["rejection"] = load_config(args.rejection)

    findings: list[Finding] = []
    status: dict[str, dict[str, Any]] = {}
    cannibal_findings: list[Finding] | None = None

    def note(detector: str, state: str, reason: str | None = None, count: int = 0) -> None:
        entry: dict[str, Any] = {"status": state, "findings": count}
        if reason:
            entry["reason"] = reason
        status[detector] = entry

    for detector in ALL_DETECTORS:
        if detector not in requested:
            note(detector, "not_requested")
            continue

        if detector == "cannibalization":
            result, reason = run_cannibalization(
                non_branded,
                project_root=project_root,
                thresholds_path=args.thresholds,
                locale=locale,
                brand_tokens=brand_tokens,
                today=windows.max_date,
            )
            if result is None:
                note(detector, "unavailable", reason)
                warnings.append(
                    f"cannibalization detector unavailable ({reason}); LI-7 cannot be computed "
                    "and this is a hole, not a clean result"
                )
            else:
                cannibal_findings = result
                findings.extend(result)
                note(detector, "ran", count=len(result))
            continue

        if detector == "mismatch" and (not intents or not expected_by_page):
            missing = "intent map" if not intents else "page intents in corpus.json"
            note(detector, "unavailable", f"no {missing}")
            warnings.append(f"mismatch detector inactive: no {missing} (§5.6)")
            continue

        produced: list[Finding]
        if detector == "striking":
            produced = detect_striking(rows_now, thresholds, curve_for, locale)
        elif detector == "ctr_outliers":
            produced = detect_ctr_outliers(rows_now, thresholds, curve_for, locale)
        elif detector == "decay":
            produced = detect_decay(rows_now, rows_prior, thresholds, locale, corpus)
        elif detector == "rising":
            produced = detect_rising(rows_now, rows_prior, thresholds, locale)
        elif detector == "lost":
            produced = detect_lost(rows_now, rows_prior, thresholds, locale)
        elif detector == "gaps":
            produced = detect_gaps(rows_now, thresholds, locale)
        elif detector == "mismatch":
            produced = detect_mismatch(rows_now, thresholds, locale, intents, expected_by_page)
        elif detector == "seasonality":
            produced = detect_seasonality(non_branded, windows, thresholds, locale)
        elif detector == "segmentation":
            produced = check_segmentation(brand_tokens, thresholds, locale)
        else:  # pragma: no cover - guarded by the unknown-detector check above
            raise KilnError(f"detector {detector!r} has no implementation")
        findings.extend(produced)
        note(detector, "ran", count=len(produced))

    findings = sort_findings(findings)

    blocking = [f for f in findings if f.blocking]
    if args.observe and blocking:
        # The documented meaning of --observe: downgrade, do not hide. Every threshold in doctrine
        # 0.1.0 is uncalibrated, and a gate blocking on a guessed number teaches people to bypass
        # gates.
        for finding in blocking:
            finding.severity = "WARN"
            finding.evidence["observed_downgrade_from"] = "BLOCK"
        findings = sort_findings(findings)

    li, li_unavailable = leading_indicators(
        rows, rows_now, rows_prior, windows, corpus, cannibal_findings, imported
    )

    branded_agg = Agg()
    for row in branded:
        branded_agg.add(row)

    payload: dict[str, Any] = {
        "generated_at": args.now or dt.datetime.now(dt.timezone.utc).isoformat(timespec="seconds"),
        "window": windows.as_record(),
        "mode": mode,
        "locale": locale,
        "segment": "non_brand",
        "history_days": history_days,
        "leading_indicators": li,
        "leading_indicators_unavailable": li_unavailable,
        "branded_segment": {
            "tokens": len(brand_tokens),
            "clicks": branded_agg.clicks,
            "impressions": branded_agg.impressions,
            "note": "reported separately; excluded from every growth metric (MSR-04)",
        },
        "ctr_curves": {
            profile: {
                "source": curve.source,
                "min_w": curve.min_w,
                "provisional": curve.provisional,
            }
            for profile, curve in sorted(curves.items())
        },
        "detectors": {k: status[k] for k in sorted(status)},
        "summary": summarise(findings),
        "findings": [to_record(f, i) for i, f in enumerate(findings, 1)],
        "warnings": warnings,
        "practice_alternatives": PRACTICE_ALTERNATIVES,
    }

    text = dumps(payload)
    if args.dry_run:
        sys.stdout.write(text + "\n")
    elif str(args.out) == "-":
        sys.stdout.write(text + "\n")
    else:
        out = args.out or (
            project_root / ".kiln" / "measurements" / "findings" / f"{windows.now[1].isoformat()}.json"
        )
        write_json(out, payload)

    still_blocking = [f for f in findings if f.blocking]
    if still_blocking:
        raise GateFailure(
            f"{len(still_blocking)} blocking finding(s): "
            + ", ".join(sorted({f.rule_id for f in still_blocking})),
            still_blocking,
        )
    return EXIT_OK


if __name__ == "__main__":
    run(main, build_parser())
