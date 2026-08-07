#!/usr/bin/env python3
"""Canonical cannibalization detector.

Owning doctrine: `doctrine/07-linking.md` §6 (decision tree), with the detection thresholds and
Search Console preprocessing rules from `doctrine/08-measurement.md` §5.1 and MSR-04/06/09/10/12/22.

`analyze.py` imports `detect()` from here rather than recomputing. There is exactly one
implementation of this calculation on purpose: two implementations of the same detector diverge,
and the medium learning loop reads the divergence as a change in the world.

What this script does NOT do: decide anything. Consolidation, redirects and deletion are
irreversible actions against an existing corpus and belong to a human (`LNK-18`, P11). The output
is a proposal with its evidence attached and its unresolved gates named.
"""

from __future__ import annotations

import json
import math
from collections import defaultdict
from dataclasses import dataclass
from datetime import date, datetime, timedelta
from pathlib import Path
from typing import Any, Iterable, Sequence

from kiln_common import (
    EXIT_OK,
    Finding,
    KilnError,
    Thresholds,
    base_parser,
    dumps,
    emit,
    load_thresholds,
    normalize_query,
    read_jsonl,
    run,
    sort_findings,
    stable_key,
    write_json,
)

__all__ = ["detect", "DOCTRINE_DEFAULTS", "preprocess", "flip_rate", "PreparedRow"]


# ---------------------------------------------------------------------------
# Doctrine defaults
# ---------------------------------------------------------------------------
# Passed to Thresholds so a project's .kiln/thresholds.yml can override any of them, and so every
# finding records which layer answered. Provenance for each value is in the doctrine tables; the
# short note travels with the finding.

DOCTRINE_DEFAULTS: dict[str, Any] = {
    # 08-measurement §5.1. The working default from the owner's the audited system's analyzer is 2;
    # published practice uses 3. The doctrine keeps both and the project picks.
    "cannibalization.min_urls": 2,
    "cannibalization.min_clicks_second_url": 3,
    "cannibalization.min_impressions_per_pair": 10,
    "cannibalization.flip_rate": 0.30,
    "cannibalization.cosine_merge": 0.90,
    "cannibalization.detect_window_days": 28,
    "cannibalization.trim_days": 4,  # MSR-06
    # NOT sourced from the doctrine. "One page is clearly stronger" appears in the tree with no
    # number attached. This is the weakest threshold in the file and is flagged as such in every
    # finding it touches.
    "cannibalization.leader_dominance": 0.80,
}

_THRESHOLD_NOTES = {
    "cannibalization.min_urls": "source: [internal observation, unpublished] the audited system's analyzer (2) vs EVIDENCE.md#e04-search-console practice (3)",
    "cannibalization.min_clicks_second_url": "source: JC Chouinard; n8n templates",
    "cannibalization.min_impressions_per_pair": "source: [internal observation, unpublished] the audited system's analyzer",
    "cannibalization.flip_rate": "expert judgement, needs calibration",
    "cannibalization.cosine_merge": "source: EVIDENCE.md#e04-search-console; validate on a sample",
    "cannibalization.trim_days": "MSR-06, recent days are systematically under-reported",
    "cannibalization.leader_dominance": "NOT IN DOCTRINE: invented to make 'clearly stronger' computable",
}


# ---------------------------------------------------------------------------
# Input rows
# ---------------------------------------------------------------------------


@dataclass(frozen=True, slots=True)
class PreparedRow:
    """One (query, url, date) observation after preprocessing.

    `position_sum` is always stored in the summed 0-based BigQuery convention, whatever the source
    used, so downstream aggregation has exactly one formula to apply.
    """

    query: str
    url: str
    day: date
    clicks: int
    impressions: int
    position_sum: float
    locale: str | None


_REQUIRED = ("clicks", "impressions")


def _pick(row: dict[str, Any], *names: str) -> Any:
    for n in names:
        if n in row and row[n] is not None:
            return row[n]
    return None


def _parse_day(value: Any) -> date:
    if isinstance(value, date) and not isinstance(value, datetime):
        return value
    if isinstance(value, datetime):
        return value.date()
    if isinstance(value, str):
        try:
            return date.fromisoformat(value[:10])
        except ValueError as exc:
            raise KilnError(f"unparseable date {value!r}; expected ISO YYYY-MM-DD") from exc
    raise KilnError(f"missing or unparseable date in row: {value!r}")


def _normalize_position(row: dict[str, Any], impressions: int) -> tuple[float, str]:
    """Return (summed 0-based position, basis name).

    Three formulas exist and the doctrine spells all three out because mixing them is a silent
    error that produces plausible numbers:

      BigQuery url table:  avg = SUM(sum_position) / SUM(impressions) + 1   (0-based, summed)
      BigQuery site table: avg = SUM(sum_top_position) / SUM(impressions) + 1
      Search Console API:  avg = SUM(position * impressions) / SUM(impressions)  (1-based, per-row average)

    We convert everything into the first convention on the way in. An API row carrying a 1-based
    average becomes `(position - 1) * impressions`, which restores the summed 0-based value the
    aggregation expects.
    """
    sum_position = _pick(row, "sum_position", "sum_top_position")
    if sum_position is not None:
        return float(sum_position), "sum_position"
    position = _pick(row, "position", "avg_position")
    if position is not None:
        return (float(position) - 1.0) * impressions, "position"
    raise KilnError(
        "row carries neither `sum_position` nor `position`; the position basis cannot be inferred "
        "and guessing it silently corrupts every average"
    )


def _is_brand(query: str, brand_tokens: Sequence[str]) -> bool:
    """MSR-04. A site legitimately holds several positions for its own brand, so branded queries
    are not cannibalization and must leave the sample before any detector runs."""
    if not brand_tokens:
        return False
    q = normalize_query(query)
    return any(tok and tok in q for tok in brand_tokens)


def preprocess(
    rows: Iterable[dict[str, Any]],
    thresholds: Thresholds,
    locale: str | None,
    brand_tokens: Sequence[str] = (),
    *,
    today: date | None = None,
) -> tuple[list[PreparedRow], list[Finding]]:
    """Apply every mandatory preprocessing step, in order, before any detection.

    Skipping any one of these produces confident wrong answers, which is worse than no answer:

      MSR-22  locale segmentation, before anything else
      MSR-10  an anonymized query is an empty string, not NULL
      MSR-06  the last 3-4 days are always trimmed
      MSR-04  non-branded slice only
      MSR-09  GROUP BY before aggregation; export rows are not deduplicated

    Returns the prepared rows and any findings about the validity of the sample itself.
    """
    findings: list[Finding] = []
    trim_days = int(thresholds.get("cannibalization.trim_days",
                                   note=_THRESHOLD_NOTES["cannibalization.trim_days"]))
    window_days = int(thresholds.get("cannibalization.detect_window_days"))

    staged: list[PreparedRow] = []
    seen_locales: set[str] = set()
    bases: set[str] = set()
    anonymized = 0
    branded = 0
    total = 0

    for row in rows:
        total += 1
        if not isinstance(row, dict):
            raise KilnError(f"expected an object per row, got {type(row).__name__}")

        row_locale = _pick(row, "locale", "country_locale")
        if row_locale:
            seen_locales.add(str(row_locale))
        # MSR-22: a row from another locale is a different page's data. Drop it rather than blend it.
        if locale is not None and row_locale is not None and str(row_locale) != locale:
            continue

        query = _pick(row, "query", "keys_query")
        # MSR-10. `query is not None` does nothing here: the anonymized marker is "".
        if query is None or str(query).strip() == "":
            anonymized += 1
            continue

        url = _pick(row, "url", "page")
        if not url:
            raise KilnError("row carries neither `url` nor `page`")

        for key in _REQUIRED:
            if key not in row:
                raise KilnError(f"row is missing required field {key!r}")

        impressions = int(row["impressions"])
        if impressions <= 0:
            continue

        if _is_brand(str(query), brand_tokens):
            branded += 1
            continue

        pos_sum, basis = _normalize_position(row, impressions)
        bases.add(basis)

        staged.append(
            PreparedRow(
                query=normalize_query(str(query)),
                url=str(url),
                day=_parse_day(_pick(row, "date", "data_date", "day")),
                clicks=int(row["clicks"]),
                impressions=impressions,
                position_sum=pos_sum,
                locale=str(row_locale) if row_locale else None,
            )
        )

    # Mixing an API export with a BigQuery export means mixing two position conventions in one
    # aggregation. The result looks like a number and is not one.
    if len(bases) > 1:
        raise KilnError(
            f"rows mix position conventions ({sorted(bases)}); "
            f"`sum_position` is a 0-based sum and `position` is a 1-based per-row average. "
            f"Split the input by source and run once per source."
        )

    # MSR-22 as a blocking finding: unsegmented multi-locale input is not a smaller problem than a
    # wrong threshold, it invalidates every number downstream.
    if locale is None and len(seen_locales) > 1:
        findings.append(
            Finding(
                rule_id="MSR-22",
                severity="BLOCK",
                subject="<input>",
                message=(
                    f"input spans {len(seen_locales)} locales ({', '.join(sorted(seen_locales))}) "
                    f"and no --locale was given; detection must run once per locale"
                ),
                evidence={"locales": sorted(seen_locales)},
                thresholds_used=[],
            )
        )

    # MSR-04 as a blocking finding: without the brand list the sample still contains queries where
    # holding several positions is correct behaviour, and every candidate is suspect.
    if not brand_tokens:
        findings.append(
            Finding(
                rule_id="MSR-04",
                severity="BLOCK",
                subject="<input>",
                message=(
                    "no brand tokens supplied; the non-branded slice could not be taken and "
                    "branded queries will surface as false cannibalization"
                ),
                evidence={"rows_examined": total},
                thresholds_used=[],
                locale=locale,
            )
        )

    if not staged:
        return [], findings

    # MSR-06: trim the provisional tail relative to the newest day actually present, not to the
    # wall clock. A stale export would otherwise lose nothing while a fresh one loses four days,
    # and the two runs would not be comparable.
    anchor = today or max(r.day for r in staged)
    cutoff_end = anchor - timedelta(days=trim_days)
    cutoff_start = cutoff_end - timedelta(days=window_days)
    kept = [r for r in staged if cutoff_start < r.day <= cutoff_end]

    # MSR-09: collapse duplicates by (query, url, day). Export rows are not deduplicated, and
    # summing them without collapsing first inflates impressions and clicks together, which keeps
    # CTR plausible while making every absolute number wrong.
    merged: dict[tuple[str, str, date], PreparedRow] = {}
    for r in kept:
        key = (r.query, r.url, r.day)
        prev = merged.get(key)
        if prev is None:
            merged[key] = r
        else:
            merged[key] = PreparedRow(
                query=r.query,
                url=r.url,
                day=r.day,
                clicks=prev.clicks + r.clicks,
                impressions=prev.impressions + r.impressions,
                position_sum=prev.position_sum + r.position_sum,
                locale=prev.locale or r.locale,
            )

    out = sorted(merged.values(), key=lambda r: stable_key(r.query, r.url, r.day.isoformat()))
    return out, findings


# ---------------------------------------------------------------------------
# Flip rate
# ---------------------------------------------------------------------------


def flip_rate(rows: Sequence[PreparedRow]) -> tuple[float, int, int]:
    """Share of days on which the leading URL for a query changed.

        flip_rate = (days the leading URL changed) / (days with impressions - 1)

    This is the honest signal in the whole detector. Two URLs appearing for one query is ordinary;
    Google being unable to settle on one of them is not. A candidate without a high flip rate is
    usually coexistence, and treating it as cannibalization means merging two pages that were both
    working.

    "Leading" is defined here as the best average position on that day, with impressions and then
    URL as tiebreaks. The doctrine does not specify the tiebreak; position is used because it is
    what the SERP actually ordered, and the remaining tiebreaks exist so the result is deterministic.

    Returns (flip_rate, flips, days_with_impressions).
    """
    by_day: dict[date, list[PreparedRow]] = defaultdict(list)
    for r in rows:
        by_day[r.day].append(r)

    leaders: list[tuple[date, str]] = []
    for day in sorted(by_day):
        same_day = by_day[day]
        leader = min(
            same_day,
            key=lambda r: stable_key(
                r.position_sum / r.impressions if r.impressions else float("inf"),
                -r.impressions,
                r.url,
            ),
        )
        leaders.append((day, leader.url))

    days = len(leaders)
    if days < 2:
        return 0.0, 0, days
    flips = sum(1 for i in range(1, days) if leaders[i][1] != leaders[i - 1][1])
    return flips / (days - 1), flips, days


# ---------------------------------------------------------------------------
# Cosine
# ---------------------------------------------------------------------------


def _cosine(a: Sequence[float], b: Sequence[float]) -> float:
    if len(a) != len(b):
        raise KilnError(f"embedding dimensions differ: {len(a)} vs {len(b)}")
    dot = sum(x * y for x, y in zip(a, b))
    na = math.sqrt(sum(x * x for x in a))
    nb = math.sqrt(sum(y * y for y in b))
    if na == 0.0 or nb == 0.0:
        raise KilnError("zero-magnitude embedding; cannot compute cosine similarity")
    return dot / (na * nb)


# ---------------------------------------------------------------------------
# Detection
# ---------------------------------------------------------------------------


@dataclass(slots=True)
class _Pair:
    url: str
    clicks: int
    impressions: int
    avg_position: float


def detect(
    rows: Iterable[dict[str, Any]],
    thresholds: Thresholds,
    locale: str | None = None,
    *,
    brand_tokens: Sequence[str] = (),
    embeddings: dict[str, Sequence[float]] | None = None,
    today: date | None = None,
) -> list[Finding]:
    """Detect cannibalization candidates from normalised Search Console rows.

    Pure: no file IO, no network, no printing. The CLI wrapper below does the IO, which is what
    lets `analyze.py` import this function instead of shelling out to it.

    The positional signature `(rows, thresholds, locale)` is the contract other scripts call.
    `brand_tokens`, `embeddings` and `today` are keyword-only with defaults so that contract holds.
    """
    prepared, findings = preprocess(rows, thresholds, locale, brand_tokens, today=today)
    if not prepared:
        return sort_findings(findings)

    min_urls = int(thresholds.get("cannibalization.min_urls",
                                  note=_THRESHOLD_NOTES["cannibalization.min_urls"]))
    min_clicks_second = int(thresholds.get("cannibalization.min_clicks_second_url",
                                           note=_THRESHOLD_NOTES["cannibalization.min_clicks_second_url"]))
    min_impressions = int(thresholds.get("cannibalization.min_impressions_per_pair",
                                         note=_THRESHOLD_NOTES["cannibalization.min_impressions_per_pair"]))
    flip_threshold = float(thresholds.get("cannibalization.flip_rate",
                                          note=_THRESHOLD_NOTES["cannibalization.flip_rate"]))
    cosine_merge = float(thresholds.get("cannibalization.cosine_merge",
                                        note=_THRESHOLD_NOTES["cannibalization.cosine_merge"]))
    dominance_threshold = float(thresholds.get("cannibalization.leader_dominance",
                                               note=_THRESHOLD_NOTES["cannibalization.leader_dominance"]))
    thresholds_snapshot = thresholds.used()

    by_query: dict[str, list[PreparedRow]] = defaultdict(list)
    for r in prepared:
        by_query[r.query].append(r)

    for query in sorted(by_query):
        rows_q = by_query[query]

        # Aggregate to (query, url) across the window. MSR-12: position is impression-weighted and
        # 0-based, so the +1 is applied once, here, and never again downstream.
        agg: dict[str, _Pair] = {}
        for r in rows_q:
            p = agg.get(r.url)
            if p is None:
                agg[r.url] = _Pair(r.url, r.clicks, r.impressions, r.position_sum)
            else:
                p.clicks += r.clicks
                p.impressions += r.impressions
                p.avg_position += r.position_sum
        for p in agg.values():
            p.avg_position = (p.avg_position / p.impressions) + 1.0 if p.impressions else float("nan")

        competing = [p for p in agg.values() if p.impressions >= min_impressions]
        if len(competing) < min_urls:
            continue

        ranked = sorted(competing, key=lambda p: stable_key(-p.clicks, -p.impressions, p.url))
        leader, runner_up = ranked[0], ranked[1]

        if runner_up.clicks < min_clicks_second:
            continue

        rate, flips, days = flip_rate([r for r in rows_q if r.url in {p.url for p in competing}])

        cosine: float | None = None
        if embeddings is not None:
            va, vb = embeddings.get(leader.url), embeddings.get(runner_up.url)
            if va is not None and vb is not None:
                cosine = round(_cosine(va, vb), 6)

        total_top_clicks = leader.clicks + runner_up.clicks
        dominance = leader.clicks / total_top_clicks if total_top_clicks else None

        evidence: dict[str, Any] = {
            "query": query,
            "competing_urls": len(competing),
            "urls": [
                {
                    "url": p.url,
                    "clicks": p.clicks,
                    "impressions": p.impressions,
                    "avg_position": round(p.avg_position, 2),
                }
                for p in ranked
            ],
            "flip_rate": round(rate, 4),
            "flips": flips,
            "days_with_impressions": days,
            "leader_dominance": round(dominance, 4) if dominance is not None else None,
            "cosine_similarity": cosine,
            "window_days_observed": days,
        }

        # Below the flip threshold this is coexistence, not competition. Recorded at INFO so the
        # first run on a project can collect the real distribution: every threshold here is
        # uncalibrated, and thrown-away observations cannot calibrate anything later.
        if rate < flip_threshold:
            findings.append(
                Finding(
                    rule_id="LNK-26",
                    severity="INFO",
                    subject=query,
                    message=(
                        f"{len(competing)} URLs share this query but the leader is stable "
                        f"(flip_rate {rate:.2f} < {flip_threshold:.2f}): coexistence, not cannibalization"
                    ),
                    evidence={**evidence, "outcome": "coexistence"},
                    thresholds_used=thresholds_snapshot,
                    locale=locale,
                )
            )
            continue

        decision = _decide(cosine, dominance, cosine_merge, dominance_threshold)
        findings.append(
            Finding(
                # LNK-25 reports the candidate; LNK-18 governs who may execute the branch it
                # proposes. Emitting LNK-18 here would claim a BLOCK severity this finding does
                # not carry: nothing is blocked until a human moves to redirect or consolidate.
                rule_id="LNK-25",
                severity="WARN",
                subject=query,
                message=(
                    f"{len(competing)} URLs compete for this query with an unstable leader "
                    f"(flip_rate {rate:.2f}); proposed: {decision['proposed_branch'] or 'undetermined'}"
                ),
                evidence={**evidence, **decision},
                thresholds_used=thresholds_snapshot,
                locale=locale,
            )
        )

    return sort_findings(findings)


def _decide(
    cosine: float | None,
    dominance: float | None,
    cosine_merge: float,
    dominance_threshold: float,
) -> dict[str, Any]:
    """Walk the §6.2 tree as far as computation honestly reaches, and stop there.

    The root of the tree is "do the pages serve the same intent, not merely the same query". That
    is a semantic judgement and it stays `null` for an agent to fill, exactly as `link_suggest.py`
    leaves its semantic gates null. Cosine similarity is evidence toward it, not a substitute for
    it: two pages can be textually near-identical and serve different intents, and two pages can
    read very differently while competing for exactly the same job.

    `blocked_on` names what is missing. A proposal with a non-empty `blocked_on` is provisional and
    must not be executed on, which is enforced socially by `LNK-18` (human only) rather than here.
    """
    gates: dict[str, Any] = {
        # Semantic. Agent fills.
        "same_intent": None,
        # Semantic, and partly not in Search Console at all: "the weaker page adds nothing new" and
        # "both hold external links" cannot be derived from query data under any threshold.
        "weaker_page_has_unique_value": None,
    }

    if cosine is None:
        return {
            "gates": gates,
            "proposed_branch": None,
            "blocked_on": ["same_intent", "cosine_similarity"],
            "provisional": True,
            "governing_rules": ["LNK-18"],
            "rationale": "no embeddings supplied; the merge-or-differentiate split cannot be evaluated",
        }

    if cosine < cosine_merge:
        # Doctrine §6.2: below the merge threshold the pages are genuinely distinct and are treated
        # by differentiation. This branch is reversible, which is why it can be proposed with more
        # confidence than the other two.
        return {
            "gates": gates,
            "proposed_branch": "DIFFERENTIATE",
            "blocked_on": [],
            "provisional": False,
            # Reversible, so LNK-18 (human-only execution) does not gate it; LNK-19 states the
            # preference for this branch over a redirect.
            "governing_rules": ["LNK-19"],
            "rationale": (
                f"cosine {cosine:.3f} < {cosine_merge:.2f}: distinct texts. Separate the target "
                f"queries, titles and angle; lock the competing anchor phrases to one owner each. "
                f"Reversible, and preferred over a 301 wherever the weaker page carries any unique "
                f"value (LNK-19)."
            ),
        }

    if dominance is not None and dominance >= dominance_threshold:
        return {
            "gates": gates,
            "proposed_branch": "REDIRECT_301",
            "blocked_on": ["weaker_page_has_unique_value"],
            "provisional": True,
            "governing_rules": ["LNK-18", "LNK-19", "LNK-01"],
            "rationale": (
                f"cosine {cosine:.3f} >= {cosine_merge:.2f} and the leader takes "
                f"{dominance:.0%} of the clicks across the top two URLs. If the weaker page adds "
                f"nothing new, 301 it onto the leader and rewrite every internal link to the final "
                f"URL, never to the redirect (LNK-01). Irreversible: human only (LNK-18, P11). "
                f"The dominance threshold is not from the doctrine."
            ),
        }

    return {
        "gates": gates,
        "proposed_branch": "CONSOLIDATE",
        "blocked_on": ["weaker_page_has_unique_value"],
        "provisional": True,
        "governing_rules": ["LNK-18", "LNK-01"],
        "rationale": (
            f"cosine {cosine:.3f} >= {cosine_merge:.2f} and clicks are split "
            f"{dominance:.0%}/{1 - dominance:.0%} across the top two URLs, so neither page is "
            f"clearly redundant. Consolidate into one document, 301 the rest, migrate the unique "
            f"blocks and rebuild the anchor profile. Irreversible: human only (LNK-18, P11)."
            if dominance is not None
            else f"cosine {cosine:.3f} >= {cosine_merge:.2f}; click distribution unavailable."
        ),
    }


# ---------------------------------------------------------------------------
# CLI
# ---------------------------------------------------------------------------


def _load_rows(path: Path) -> list[dict[str, Any]]:
    """Accept JSONL, a bare JSON array, or an object wrapping one under `rows`/`data`."""
    if path.suffix.lower() in {".jsonl", ".ndjson"}:
        return list(read_jsonl(path))
    if not path.exists():
        raise KilnError(f"input file not found: {path}")
    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
    except json.JSONDecodeError as exc:
        raise KilnError(f"{path}: malformed JSON: {exc}") from exc
    if isinstance(payload, list):
        return payload
    if isinstance(payload, dict):
        for key in ("rows", "data", "records"):
            if isinstance(payload.get(key), list):
                return payload[key]
    raise KilnError(f"{path}: expected a JSON array or an object carrying `rows`")


def _load_embeddings(path: Path | None) -> dict[str, Sequence[float]] | None:
    """Load `{url: vector}` from JSON, or from an .npz archive when numpy is present.

    numpy stays optional. A project with no embeddings still gets detection and flip rates; it
    simply does not get the merge-or-differentiate split, and the output says so rather than
    quietly proposing a branch it could not evaluate.
    """
    if path is None:
        return None
    if not path.exists():
        raise KilnError(f"embeddings file not found: {path}")
    if path.suffix.lower() == ".npz":
        try:
            import numpy as np
        except ImportError as exc:
            raise KilnError(
                "reading .npz embeddings requires numpy; supply a JSON {url: vector} map instead"
            ) from exc
        with np.load(path, allow_pickle=False) as archive:
            return {str(k): archive[k].tolist() for k in archive.files}
    payload = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(payload, dict):
        raise KilnError(f"{path}: expected an object mapping URL to vector")
    return {str(k): list(v) for k, v in payload.items()}


def _load_brand_tokens(path: Path | None) -> list[str]:
    """One token per line; blank lines and `#` comments ignored."""
    if path is None:
        return []
    if not path.exists():
        raise KilnError(f"brand tokens file not found: {path}")
    tokens: list[str] = []
    for line in path.read_text(encoding="utf-8").splitlines():
        line = line.strip()
        if line and not line.startswith("#"):
            tokens.append(normalize_query(line))
    return tokens


def main(args) -> int:
    thresholds = load_thresholds(args.project_root, DOCTRINE_DEFAULTS, args.thresholds)
    rows = _load_rows(args.gsc)
    embeddings = _load_embeddings(args.embeddings)
    brand_tokens = _load_brand_tokens(args.brand_tokens)

    if args.window is not None:
        # An explicit --window overrides the configured detection window for this run only.
        thresholds._local["cannibalization.detect_window_days"] = int(args.window)

    findings = detect(
        rows,
        thresholds,
        args.locale,
        brand_tokens=brand_tokens,
        embeddings=embeddings,
    )

    candidates = [f for f in findings if f.severity == "WARN"]
    blocking = [f for f in findings if f.blocking]

    payload = {
        "generated_by": "cannibal_detect.py",
        "locale": args.locale,
        "counts": {
            "candidates": len(candidates),
            "coexistence": sum(1 for f in findings if f.severity == "INFO"),
            "blocking": len(blocking),
        },
        "findings": [f.as_record() for f in findings],
    }
    emit(args, payload)

    # A blocking finding here means the sample itself is invalid, not that the site is broken.
    # Exiting non-zero is the difference between a gate and a report.
    if blocking and not args.observe:
        from kiln_common import EXIT_GATE_FAILED

        return EXIT_GATE_FAILED
    return EXIT_OK


if __name__ == "__main__":
    parser = base_parser("Detect cannibalization candidates from Search Console data")
    parser.add_argument("--gsc", type=Path, required=True,
                        help="normalised Search Console rows (JSON or JSONL) from gsc_pull.py")
    parser.add_argument("--embeddings", type=Path, default=None,
                        help="{url: vector} JSON, or .npz when numpy is available")
    parser.add_argument("--brand-tokens", type=Path, default=None,
                        help="one brand token per line; required for the non-branded slice (MSR-04)")
    parser.add_argument("--window", type=int, default=None,
                        help="detection window in days, overriding thresholds for this run")
    run(main, parser)
