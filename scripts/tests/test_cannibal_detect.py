"""Tests for the canonical cannibalization detector.

The preprocessing tests matter more than they look. Every one of them corresponds to a documented
way Search Console data lies to you, and each failure mode produces plausible numbers rather than
an error, so nothing downstream would notice.
"""

from __future__ import annotations

import math
from datetime import date

import pytest

from cannibal_detect import (
    DOCTRINE_DEFAULTS,
    detect,
    flip_rate,
    preprocess,
)
from kiln_common import KilnError, Thresholds, dumps

QUERY = "кредит онлайн на картку"
BRAND = ["examplebrand"]


def thresholds(**overrides) -> Thresholds:
    """Doctrine defaults with a local override layer, as a project would have."""
    local = {"cannibalization.trim_days": 0, "cannibalization.detect_window_days": 365}
    local.update({f"cannibalization.{k}": v for k, v in overrides.items()})
    return Thresholds(DOCTRINE_DEFAULTS, local)


def r(
    url: str,
    day: str,
    *,
    query: str = QUERY,
    clicks: int = 5,
    impressions: int = 100,
    avg_pos: float = 3.0,
    locale: str | None = None,
) -> dict:
    """A normalised row in the BigQuery url-table convention: `sum_position` is a 0-based sum."""
    row = {
        "query": query,
        "url": url,
        "date": day,
        "clicks": clicks,
        "impressions": impressions,
        "sum_position": (avg_pos - 1.0) * impressions,
    }
    if locale is not None:
        row["locale"] = locale
    return row


def alternating_leader(a_clicks: int, b_clicks: int) -> list[dict]:
    """Four days on which the leading URL alternates every day: flip_rate 1.0.

    Clicks are loaded onto the first day of each URL so the totals are easy to reason about.
    """
    return [
        r("/a", "2026-08-01", clicks=a_clicks, avg_pos=2.0),
        r("/b", "2026-08-01", clicks=b_clicks, avg_pos=6.0),
        r("/a", "2026-08-02", clicks=0, avg_pos=7.0),
        r("/b", "2026-08-02", clicks=0, avg_pos=2.0),
        r("/a", "2026-08-03", clicks=0, avg_pos=2.0),
        r("/b", "2026-08-03", clicks=0, avg_pos=8.0),
        r("/a", "2026-08-04", clicks=0, avg_pos=9.0),
        r("/b", "2026-08-04", clicks=0, avg_pos=2.0),
    ]


def emb(cosine: float) -> dict[str, list[float]]:
    """Two unit vectors separated by exactly `cosine`."""
    return {"/a": [1.0, 0.0], "/b": [cosine, math.sqrt(max(0.0, 1.0 - cosine * cosine))]}


def candidates(findings):
    return [f for f in findings if f.severity == "WARN"]


def blocking(findings):
    return [f for f in findings if f.severity == "BLOCK"]


# ---------------------------------------------------------------------------
# Preprocessing
# ---------------------------------------------------------------------------


def test_anonymized_query_is_empty_string_not_null():
    """MSR-10. `query IS NOT NULL` does nothing; the anonymized marker is an empty string."""
    rows = [
        r("/a", "2026-08-01"),
        {**r("/b", "2026-08-01"), "query": ""},
        {**r("/c", "2026-08-01"), "query": "   "},
        {**r("/d", "2026-08-01"), "query": None},
    ]
    prepared, _ = preprocess(rows, thresholds(), None, BRAND)
    assert [p.url for p in prepared] == ["/a"]


def test_rows_are_deduplicated_before_aggregation():
    """MSR-09. Export rows are not deduplicated. Summing without collapsing first inflates clicks
    and impressions together, which keeps CTR plausible while every absolute number is wrong."""
    rows = [
        r("/a", "2026-08-01", clicks=5, impressions=100),
        r("/a", "2026-08-01", clicks=5, impressions=100),
    ]
    prepared, _ = preprocess(rows, thresholds(), None, BRAND)
    assert len(prepared) == 1
    assert prepared[0].clicks == 10
    assert prepared[0].impressions == 200


def test_trailing_days_are_trimmed_relative_to_the_newest_day_present():
    """MSR-06. The tail is trimmed against the data, not the wall clock, so a stale export and a
    fresh one remain comparable."""
    rows = [r("/a", f"2026-08-{d:02d}") for d in range(1, 9)]
    prepared, _ = preprocess(rows, thresholds(trim_days=4), None, BRAND)
    days = sorted({p.day for p in prepared})
    assert days[-1] == date(2026, 8, 4)
    assert date(2026, 8, 5) not in days


def test_branded_queries_are_excluded():
    """MSR-04. Holding several positions for your own brand is correct behaviour, not
    cannibalization."""
    rows = [
        r("/a", "2026-08-01", query="examplebrand кредит"),
        r("/b", "2026-08-01", query=QUERY),
    ]
    prepared, _ = preprocess(rows, thresholds(), None, BRAND)
    assert [p.url for p in prepared] == ["/b"]


def test_missing_brand_tokens_is_a_blocking_finding():
    """Without the brand list the sample still contains queries where several positions are
    legitimate, so every candidate downstream is suspect."""
    _, findings = preprocess([r("/a", "2026-08-01")], thresholds(), None, ())
    assert [f.rule_id for f in blocking(findings)] == ["MSR-04"]


def test_position_is_converted_to_the_summed_zero_based_convention():
    """The API reports a 1-based per-row average; BigQuery reports a 0-based sum. Both must land in
    one convention before aggregation."""
    bq = [r("/a", "2026-08-01", impressions=100, avg_pos=4.0)]
    api = [{
        "query": QUERY, "url": "/a", "date": "2026-08-01",
        "clicks": 5, "impressions": 100, "position": 4.0,
    }]
    p_bq, _ = preprocess(bq, thresholds(), None, BRAND)
    p_api, _ = preprocess(api, thresholds(), None, BRAND)
    assert p_bq[0].position_sum == pytest.approx(p_api[0].position_sum)
    assert p_bq[0].position_sum / p_bq[0].impressions + 1 == pytest.approx(4.0)


def test_mixing_position_conventions_raises():
    """Blending a 0-based sum with a 1-based average produces a number that looks right and is not.
    Refusing is the only safe answer."""
    rows = [
        r("/a", "2026-08-01"),
        {"query": QUERY, "url": "/b", "date": "2026-08-01",
         "clicks": 5, "impressions": 100, "position": 4.0},
    ]
    with pytest.raises(KilnError, match="position conventions"):
        preprocess(rows, thresholds(), None, BRAND)


def test_row_without_any_position_field_raises():
    rows = [{"query": QUERY, "url": "/a", "date": "2026-08-01", "clicks": 5, "impressions": 100}]
    with pytest.raises(KilnError, match="position basis"):
        preprocess(rows, thresholds(), None, BRAND)


# ---------------------------------------------------------------------------
# Locale
# ---------------------------------------------------------------------------


def test_locale_filter_keeps_only_the_requested_locale():
    """MSR-22. The same URL path under two locales is two distinct pages."""
    rows = [
        r("/a", "2026-08-01", locale="uk"),
        r("/a", "2026-08-01", locale="ru"),
    ]
    prepared, _ = preprocess(rows, thresholds(), "uk", BRAND)
    assert len(prepared) == 1
    assert prepared[0].locale == "uk"


def test_mixed_locales_without_a_locale_argument_blocks():
    rows = [r("/a", "2026-08-01", locale="uk"), r("/b", "2026-08-01", locale="ru")]
    _, findings = preprocess(rows, thresholds(), None, BRAND)
    ids = [f.rule_id for f in blocking(findings)]
    assert "MSR-22" in ids


def test_findings_carry_the_locale_they_were_computed_in():
    rows = [{**src, "locale": "uk"} for src in alternating_leader(20, 10)]
    findings = detect(rows, thresholds(), "uk", brand_tokens=BRAND, embeddings=emb(0.95))
    assert candidates(findings)
    assert all(f.locale == "uk" for f in candidates(findings))


# ---------------------------------------------------------------------------
# Flip rate
# ---------------------------------------------------------------------------


def test_flip_rate_over_a_multi_day_fixture():
    """flip_rate = days the leading URL changed / (days with impressions - 1)."""
    prepared, _ = preprocess(alternating_leader(20, 10), thresholds(), None, BRAND)
    rate, flips, days = flip_rate(prepared)
    assert days == 4
    assert flips == 3
    assert rate == pytest.approx(1.0)


def test_stable_leader_yields_zero_flip_rate():
    rows = [
        r("/a", f"2026-08-0{d}", clicks=10, avg_pos=2.0) for d in range(1, 5)
    ] + [
        r("/b", f"2026-08-0{d}", clicks=2, avg_pos=8.0) for d in range(1, 5)
    ]
    prepared, _ = preprocess(rows, thresholds(), None, BRAND)
    rate, flips, days = flip_rate(prepared)
    assert days == 4
    assert flips == 0
    assert rate == 0.0


def test_single_day_cannot_produce_a_flip_rate():
    """One day gives a zero denominator. Reporting 0.0 rather than dividing is the honest answer,
    and the day count travels with it so nobody reads it as stability."""
    prepared, _ = preprocess([r("/a", "2026-08-01"), r("/b", "2026-08-01")], thresholds(), None, BRAND)
    rate, flips, days = flip_rate(prepared)
    assert (rate, flips, days) == (0.0, 0, 1)


def test_stable_leader_is_reported_as_coexistence_not_cannibalization():
    """A candidate without a high flip rate is ordinary coexistence. Merging those pages would
    destroy two working pages."""
    rows = [
        r("/a", f"2026-08-0{d}", clicks=10, avg_pos=2.0) for d in range(1, 5)
    ] + [
        r("/b", f"2026-08-0{d}", clicks=3, avg_pos=8.0) for d in range(1, 5)
    ]
    findings = detect(rows, thresholds(), None, brand_tokens=BRAND, embeddings=emb(0.99))
    assert not candidates(findings)
    info = [f for f in findings if f.severity == "INFO"]
    assert len(info) == 1
    assert info[0].evidence["outcome"] == "coexistence"


# ---------------------------------------------------------------------------
# Decision tree
# ---------------------------------------------------------------------------


def test_branch_differentiate_when_texts_are_distinct():
    findings = detect(alternating_leader(20, 10), thresholds(), None,
                      brand_tokens=BRAND, embeddings=emb(0.50))
    (f,) = candidates(findings)
    assert f.evidence["proposed_branch"] == "DIFFERENTIATE"
    assert f.evidence["blocked_on"] == []
    assert f.evidence["provisional"] is False


def test_branch_redirect_when_one_page_clearly_dominates():
    findings = detect(alternating_leader(100, 5), thresholds(), None,
                      brand_tokens=BRAND, embeddings=emb(0.97))
    (f,) = candidates(findings)
    assert f.evidence["proposed_branch"] == "REDIRECT_301"
    assert f.evidence["blocked_on"] == ["weaker_page_has_unique_value"]
    assert f.evidence["provisional"] is True


def test_branch_consolidate_when_both_pages_carry_clicks():
    findings = detect(alternating_leader(20, 15), thresholds(), None,
                      brand_tokens=BRAND, embeddings=emb(0.97))
    (f,) = candidates(findings)
    assert f.evidence["proposed_branch"] == "CONSOLIDATE"
    assert f.evidence["provisional"] is True


def test_branch_undetermined_without_embeddings():
    """No embeddings means the merge-or-differentiate split cannot be evaluated. Saying so beats
    proposing a branch that was never computed."""
    findings = detect(alternating_leader(20, 10), thresholds(), None, brand_tokens=BRAND)
    (f,) = candidates(findings)
    assert f.evidence["proposed_branch"] is None
    assert "cosine_similarity" in f.evidence["blocked_on"]
    assert f.evidence["cosine_similarity"] is None


def test_intent_gate_is_always_null():
    """The root of the tree is a semantic judgement. A similarity number is evidence toward it, not
    a substitute for it, and the script must never fill it in."""
    for cos in (0.50, 0.97):
        findings = detect(alternating_leader(20, 10), thresholds(), None,
                          brand_tokens=BRAND, embeddings=emb(cos))
        (f,) = candidates(findings)
        assert f.evidence["gates"]["same_intent"] is None
        assert f.evidence["gates"]["weaker_page_has_unique_value"] is None


def test_no_finding_names_a_branch_as_a_decision():
    """`LNK-18`: the script proposes, a human decides. Nothing in the output may read as an
    instruction already carried out."""
    findings = detect(alternating_leader(100, 5), thresholds(), None,
                      brand_tokens=BRAND, embeddings=emb(0.97))
    (f,) = candidates(findings)
    assert "proposed_branch" in f.evidence
    assert "decision" not in f.evidence
    assert f.severity == "WARN"


# ---------------------------------------------------------------------------
# Candidate thresholds
# ---------------------------------------------------------------------------


def test_runner_up_below_the_click_floor_is_not_a_candidate():
    findings = detect(alternating_leader(50, 1), thresholds(), None,
                      brand_tokens=BRAND, embeddings=emb(0.97))
    assert not candidates(findings)


def test_url_below_the_impression_floor_does_not_count_as_competition():
    rows = alternating_leader(20, 10)
    rows = [{**row, "impressions": 2} if row["url"] == "/b" else row for row in rows]
    findings = detect(rows, thresholds(), None, brand_tokens=BRAND, embeddings=emb(0.97))
    assert not candidates(findings)


def test_strict_min_urls_requires_a_third_competing_url():
    findings = detect(alternating_leader(20, 10), thresholds(min_urls=3), None,
                      brand_tokens=BRAND, embeddings=emb(0.97))
    assert not candidates(findings)


# ---------------------------------------------------------------------------
# Provenance and determinism
# ---------------------------------------------------------------------------


def test_every_finding_carries_the_thresholds_that_produced_it():
    """A stored finding without its thresholds cannot be re-read after a recalibration: nobody can
    tell whether it fired because the site changed or because the number did."""
    findings = detect(alternating_leader(20, 10), thresholds(), None,
                      brand_tokens=BRAND, embeddings=emb(0.97))
    (f,) = candidates(findings)
    keys = {t["key"] for t in f.thresholds_used}
    assert "cannibalization.flip_rate" in keys
    assert "cannibalization.cosine_merge" in keys
    assert all("source" in t for t in f.thresholds_used)


def test_locally_overridden_thresholds_are_marked_local():
    findings = detect(alternating_leader(20, 10), thresholds(flip_rate=0.10), None,
                      brand_tokens=BRAND, embeddings=emb(0.97))
    (f,) = candidates(findings)
    by_key = {t["key"]: t for t in f.thresholds_used}
    assert by_key["cannibalization.flip_rate"]["source"] == "local"
    assert by_key["cannibalization.cosine_merge"]["source"] == "doctrine"


def test_the_invented_dominance_threshold_declares_itself():
    """It is the only threshold here with no doctrine backing, and the finding says so rather than
    letting it accumulate unearned authority."""
    findings = detect(alternating_leader(100, 5), thresholds(), None,
                      brand_tokens=BRAND, embeddings=emb(0.97))
    (f,) = candidates(findings)
    note = next(t["note"] for t in f.thresholds_used
                if t["key"] == "cannibalization.leader_dominance")
    assert "NOT IN DOCTRINE" in note


def test_output_is_byte_identical_across_runs():
    """Without this, a change in our implementation is indistinguishable from a change in the SERP,
    and the medium learning loop reads exactly that difference."""
    rows = alternating_leader(20, 10) + [
        r("/c", "2026-08-01", query="інший запит", clicks=9, avg_pos=3.0),
        r("/d", "2026-08-01", query="інший запит", clicks=8, avg_pos=4.0),
        r("/c", "2026-08-02", query="інший запит", clicks=1, avg_pos=9.0),
        r("/d", "2026-08-02", query="інший запит", clicks=1, avg_pos=2.0),
    ]
    first = detect(rows, thresholds(), None, brand_tokens=BRAND, embeddings=emb(0.97))
    second = detect(list(reversed(rows)), thresholds(), None, brand_tokens=BRAND, embeddings=emb(0.97))
    assert dumps([f.as_record() for f in first]) == dumps([f.as_record() for f in second])


def test_empty_input_produces_no_candidates():
    findings = detect([], thresholds(), None, brand_tokens=BRAND)
    assert not candidates(findings)


# ---------------------------------------------------------------------------
# Rule identifier integrity
#
# These exist because the first version of this script emitted `MSR-5.2`, `LNK-18` and friends:  # kiln-lint: ignore code_doctrine_ids -- names the malformed IDs this suite exists to reject; a mention, not a citation
# section numbers and governance rules pressed into service as detector identifiers. A finding
# whose `rule_id` resolves to nothing cannot be joined to the per-rule counters in
# `.kiln/rules-stats.json`, cannot be tied to a reviewer override, and therefore never reaches the
# fast learning loop. The defect is invisible at runtime, so it has to fail here.
# ---------------------------------------------------------------------------

import re as _re
from pathlib import Path as _Path

_DOCTRINE = _Path(__file__).resolve().parents[2] / "doctrine"
_SCRIPT = _Path(__file__).resolve().parents[1] / "cannibal_detect.py"


def doctrine_rule_ids(filename: str, prefix: str) -> set[str]:
    """Every rule ID *defined* in a doctrine file.

    The doctrine defines rules in three shapes and a linter that knows only one of them reports
    false violations, which is how linters get switched off:
      1. `### MSR-07 · Title`              (section headers)
      2. `**Rule `LNK-16` (BLOCK, code).**` (inline statements)
      3. `| `LNK-07` | Statement | WARN |`  (limit and summary tables)
    """
    text = (_DOCTRINE / filename).read_text(encoding="utf-8")
    ids: set[str] = set()
    ids |= set(_re.findall(rf"^#{{2,4}} ({prefix}-\d+)\s*·", text, _re.M))
    ids |= set(_re.findall(rf"^\*\*Rule `({prefix}-\d+)`", text, _re.M))
    ids |= set(_re.findall(rf"^\|\s*`({prefix}-\d+)`\s*\|", text, _re.M))
    return ids


def emitted_rule_ids(path: _Path) -> set[str]:
    return set(_re.findall(r'rule_id="([A-Z]+-[\w.]+)"', path.read_text(encoding="utf-8")))


def test_every_emitted_rule_id_is_well_formed():
    """`PREFIX-NN`, never a section number. `MSR-5.2` is the shape this forbids."""  # kiln-lint: ignore code_doctrine_ids -- docstring quoting the forbidden shape
    for rule_id in emitted_rule_ids(_SCRIPT):
        assert _re.fullmatch(r"[A-Z]{3}-\d{2}", rule_id), (
            f"{rule_id!r} is not a rule identifier. Section numbers such as 'MSR-5.2' are not "  # kiln-lint: ignore code_doctrine_ids -- failure message quoting the forbidden shape
            f"rule IDs and resolve to nothing in the doctrine."
        )


def test_every_emitted_rule_id_exists_in_the_doctrine():
    known = doctrine_rule_ids("07-linking.md", "LNK") | doctrine_rule_ids("08-measurement.md", "MSR")
    unresolved = emitted_rule_ids(_SCRIPT) - known
    assert not unresolved, (
        f"emitted but undefined in the doctrine: {sorted(unresolved)}. Either the detector is "
        f"citing the wrong rule, or the rule needs minting via RULE-CHANGE.md."
    )


def test_detection_does_not_borrow_the_human_execution_rule():
    """`LNK-18` is BLOCK/human; this script is WARN/code and executes nothing.

    Emitting LNK-18 from here would claim a severity the finding does not carry and would make the
    counters read as though a blocking gate had fired on every candidate.
    """
    assert "LNK-18" not in emitted_rule_ids(_SCRIPT)
    findings = detect(alternating_leader(100, 5), thresholds(), None,
                      brand_tokens=BRAND, embeddings=emb(0.97))
    (f,) = candidates(findings)
    assert f.rule_id == "LNK-25"
    # The governing rules stay machine-readable rather than only appearing in the prose rationale.
    assert "LNK-18" in f.evidence["governing_rules"]
