"""Tests for `analyze.py`.

The fixture is one small Search Console corpus shaped so that every detector has something to find.
That matters more than it sounds: a detector silently returning nothing looks exactly like a healthy
site, so each test asserts a specific finding rather than a non-empty list.
"""

from __future__ import annotations

import datetime as dt
import json
import sys
import types
from pathlib import Path

import pytest

import analyze
from kiln_common import Finding, GateFailure, KilnError

# --------------------------------------------------------------------------------------------
# Fixture corpus
# --------------------------------------------------------------------------------------------
# max date 2026-08-07, trim 4 -> now = 2026-07-07..2026-08-03, prior = 2026-06-09..2026-07-06.

MAX_DATE = dt.date(2026, 8, 7)
NOW_DAY = dt.date(2026, 7, 15)
PRIOR_DAY = dt.date(2026, 6, 20)

_iso = NOW_DAY.isocalendar()
YEAR_AGO_DAY = dt.date.fromisocalendar(_iso.year - 1, _iso.week, 3)

UK = "https://uk.example.com"
EN = "https://en.example.com"


def _row(date, query, page, clicks, impressions, position):
    return {
        "date": date.isoformat(),
        "query": query,
        "page": page,
        "clicks": clicks,
        "impressions": impressions,
        "position": position,
    }


def build_rows() -> list[dict]:
    rows: list[dict] = []

    # --- now window ------------------------------------------------------------------
    # striking: good position, CTR far below the curve
    rows.append(_row(NOW_DAY, "striking query", f"{UK}/credits/striking", 2, 500, 6.0))
    # ctr outlier: position 3 sits below striking's 5.0 floor, so only §5.3 should fire
    rows.append(_row(NOW_DAY, "ctr outlier query", f"{UK}/credits/ctr", 1, 200, 3.0))
    # decay subject: 100 -> 20 clicks
    rows.append(_row(NOW_DAY, "decay query", f"{UK}/credits/decay", 20, 400, 8.0))
    # decay peers: flat, so the cluster median stays near zero and the subject's drop is excess
    for i in range(1, 4):
        rows.append(_row(NOW_DAY, f"peer query {i}", f"{UK}/credits/peer{i}", 60, 600, 7.0))
    # rising: absent from the prior window entirely
    rows.append(_row(NOW_DAY, "rising query", f"{UK}/credits/rising", 40, 500, 4.0))
    # coverage gap: demand confirmed, page does not reach
    rows.append(_row(NOW_DAY, "gap query", f"{UK}/credits/gap", 0, 200, 35.0))
    # intent mismatch: transactional query served by an informational page
    rows.append(_row(NOW_DAY, "mismatch query", f"{UK}/credits/guide", 5, 300, 9.0))
    # seasonality subject
    rows.append(_row(NOW_DAY, "season query", f"{UK}/credits/season", 5, 100, 10.0))
    # anonymized: an empty query, not NULL (MSR-10)
    rows.append(_row(NOW_DAY, "", f"{UK}/credits/striking", 0, 1000, 11.0))
    # branded: must never reach a growth metric (MSR-04)
    rows.append(_row(NOW_DAY, "example brand loan", f"{UK}/", 100, 800, 1.2))

    # --- prior window ----------------------------------------------------------------
    rows.append(_row(PRIOR_DAY, "decay query", f"{UK}/credits/decay", 100, 1200, 6.0))
    for i in range(1, 4):
        rows.append(_row(PRIOR_DAY, f"peer query {i}", f"{UK}/credits/peer{i}", 60, 600, 7.0))
    rows.append(_row(PRIOR_DAY, "lost query", f"{UK}/credits/lost", 10, 500, 12.0))
    rows.append(_row(PRIOR_DAY, "striking query", f"{UK}/credits/striking", 2, 480, 6.2))

    # --- a year ago, for the year-over-year comparison --------------------------------
    rows.append(_row(YEAR_AGO_DAY, "season query", f"{UK}/credits/season", 900, 20000, 3.0))

    # --- inside the trimmed tail, only to establish the max date ----------------------
    rows.append(_row(MAX_DATE, "anchor query", f"{UK}/credits/anchor", 1, 10, 9.0))

    # --- a second locale, which must not leak into any calculation --------------------
    rows.append(_row(NOW_DAY, "striking query", f"{EN}/credits/striking", 900, 99000, 1.1))
    rows.append(_row(PRIOR_DAY, "striking query", f"{EN}/credits/striking", 900, 99000, 1.1))

    return rows


@pytest.fixture
def project(tmp_path: Path) -> Path:
    """A complete project tree: raw rows, project.yml, corpus and intent maps."""
    raw = tmp_path / "raw"
    raw.mkdir()
    with (raw / "rows.jsonl").open("w", encoding="utf-8", newline="\n") as fh:
        for row in build_rows():
            fh.write(json.dumps(row, ensure_ascii=False, sort_keys=True) + "\n")

    kiln = tmp_path / ".kiln"
    kiln.mkdir()
    (kiln / "project.yml").write_text(
        "locales:\n"
        "  uk:\n"
        '    host: "uk."\n'
        "  en:\n"
        '    host: "en."\n'
        "brand_tokens:\n"
        "  - example brand\n",
        encoding="utf-8",
    )

    (tmp_path / "corpus.json").write_text(
        json.dumps(
            {
                f"{UK}/credits/guide": {
                    "cluster": "credits",
                    "expected_intent": "informational",
                    "published_at": "2026-07-10",
                }
            }
        ),
        encoding="utf-8",
    )
    (tmp_path / "intents.json").write_text(
        json.dumps({"mismatch query": "transactional"}), encoding="utf-8"
    )
    return tmp_path


def make_args(project: Path, *extra: str):
    argv = [
        "--project-root", str(project),
        "--raw", str(project / "raw"),
        "--locale", "uk",
        "--corpus", str(project / "corpus.json"),
        "--intents", str(project / "intents.json"),
        "--out", str(project / "out.json"),
        "--now", "2026-08-07T06:00:00+00:00",
        *extra,
    ]
    return analyze.build_parser().parse_args(argv)


def run_analyze(project: Path, *extra: str) -> dict:
    args = make_args(project, *extra)
    analyze.main(args)
    return json.loads((project / "out.json").read_text(encoding="utf-8"))


def findings_of(report: dict, detector: str) -> list[dict]:
    return [f for f in report["findings"] if f["type"] == detector]


# --------------------------------------------------------------------------------------------
# Stub for the canonical cannibalization implementation
# --------------------------------------------------------------------------------------------


@pytest.fixture
def stub_cannibal(monkeypatch):
    """Stand in for `cannibal_detect.py`, recording exactly what it was handed."""
    calls: list[dict] = []
    module = types.ModuleType("cannibal_detect")
    # The real module declares its own thresholds; the stub does too, so the merge path is
    # exercised rather than only the happy case where the callee needs nothing.
    module.DOCTRINE_DEFAULTS = {"cannibalization.flip_rate": 0.30}

    def detect(rows, thresholds, locale=None, **kwargs):
        calls.append({"rows": rows, "thresholds": thresholds, "locale": locale, **kwargs})
        return [
            Finding(
                rule_id="LNK-25",
                severity="WARN",
                subject="кредит онлайн на картку",
                message="3 competing URLs, flip_rate 0.41",
                evidence={
                    "detector": "cannibalization",
                    "metrics": {"flip_rate": 0.41},
                    "tier": "manual",
                    "suggested_action": "merge_301",
                },
                thresholds_used=[
                    {"key": "cannibal.flip_rate", "value": 0.3, "source": "doctrine"}
                ],
                locale=locale,
            )
        ]

    module.detect = detect
    monkeypatch.setitem(sys.modules, "cannibal_detect", module)
    return calls


@pytest.fixture
def no_cannibal(monkeypatch):
    """Make `cannibal_detect` unimportable, as it is before that script is written."""
    monkeypatch.setitem(sys.modules, "cannibal_detect", None)


# --------------------------------------------------------------------------------------------
# Detectors
# --------------------------------------------------------------------------------------------


def test_striking_distance_ranks_by_opportunity_not_impressions(project, stub_cannibal):
    report = run_analyze(project)
    hits = findings_of(report, "striking")
    subjects = [f["subject"] for f in hits]
    assert "striking query → https://uk.example.com/credits/striking" in subjects

    hit = next(f for f in hits if f["subject"].startswith("striking query"))
    metrics = hit["metrics"]
    assert metrics["impressions"] == 500
    assert metrics["position"] == pytest.approx(6.0)
    assert metrics["ctr_actual"] == pytest.approx(2 / 500)
    # First Page Sage prior at position 6
    assert metrics["ctr_expected"] == pytest.approx(0.029)
    assert metrics["opportunity_score"] == pytest.approx(500 * (0.029 - 0.004), rel=1e-6)
    # Position 3 is below the 5.0 floor, so the CTR outlier must not appear here.
    assert not any(f["subject"].startswith("ctr outlier") for f in hits)


def test_ctr_outlier_fires_on_relative_underperformance(project, stub_cannibal):
    report = run_analyze(project)
    hits = findings_of(report, "ctr_outliers")
    subjects = [f["subject"] for f in hits]
    assert "ctr outlier query → https://uk.example.com/credits/ctr" in subjects
    hit = next(f for f in hits if f["subject"].startswith("ctr outlier"))
    # 0.005 actual against 0.5 x 0.067 expected
    assert hit["metrics"]["ctr_actual"] < 0.5 * hit["metrics"]["ctr_expected"]


def test_decay_requires_excess_over_the_cluster(project, stub_cannibal):
    report = run_analyze(project)
    hits = findings_of(report, "decay")
    subjects = [f["subject"] for f in hits]
    assert f"{UK}/credits/decay" in subjects
    hit = next(f for f in hits if f["subject"].endswith("/credits/decay"))
    assert hit["metrics"]["clicks_prior"] == 100
    assert hit["metrics"]["clicks_now"] == 20
    assert hit["metrics"]["cluster_differencing"] == "applied"
    assert hit["metrics"]["excess_over_cluster"] < -0.15
    # The flat peers moved with the cluster and must not be reported as decay.
    assert not any("peer" in s for s in subjects)


def test_decay_ignores_a_page_that_fell_with_its_cluster(project, stub_cannibal, tmp_path):
    """A whole cluster sliding is demand or the SERP moving, and needs a different remedy."""
    from kiln_common import Thresholds

    rows_now = [
        analyze.Row(NOW_DAY, "q", f"{UK}/c/{i}", clicks=20, impressions=100, position=5.0)
        for i in range(4)
    ]
    rows_prior = [
        analyze.Row(PRIOR_DAY, "q", f"{UK}/c/{i}", clicks=100, impressions=500, position=5.0)
        for i in range(4)
    ]
    thresholds = Thresholds(analyze.DOCTRINE_DEFAULTS, {})
    hits = analyze.detect_decay(rows_now, rows_prior, thresholds, "uk", {})
    assert hits == []


def test_rising_and_lost_and_gaps(project, stub_cannibal):
    report = run_analyze(project)

    rising = findings_of(report, "rising")
    assert "rising query" in [f["subject"] for f in rising]
    hit = next(f for f in rising if f["subject"] == "rising query")
    assert hit["metrics"]["clicks_prior"] is None  # absent from the prior window

    lost = findings_of(report, "lost")
    assert "lost query" in [f["subject"] for f in lost]
    assert next(f for f in lost if f["subject"] == "lost query")["metrics"]["impressions_now"] == 0

    gaps = findings_of(report, "gaps")
    assert "gap query" in [f["subject"] for f in gaps]
    assert next(f for f in gaps if f["subject"] == "gap query")["metrics"]["best_position"] == 35.0


def test_lost_ignores_queries_below_the_anonymization_floor(project, stub_cannibal):
    """Below 100 prior impressions half the list would be privacy-cutoff artefacts (MSR-07)."""
    from kiln_common import Thresholds

    rows_prior = [analyze.Row(PRIOR_DAY, "tiny", f"{UK}/x", 1, 40, 20.0)]
    thresholds = Thresholds(analyze.DOCTRINE_DEFAULTS, {})
    assert analyze.detect_lost([], rows_prior, thresholds, "uk") == []


def test_mismatch_uses_the_intent_map(project, stub_cannibal):
    report = run_analyze(project)
    hits = findings_of(report, "mismatch")
    assert hits, "mismatch should fire with both an intent map and page intents present"
    assert hits[0]["metrics"]["query_intent"] == "transactional"
    assert hits[0]["metrics"]["page_intent"] == "informational"


def test_mismatch_reports_itself_inactive_rather_than_silent(project, stub_cannibal):
    """A detector that cannot run must say so; silence reads as 'nothing found'."""
    args = make_args(project)
    args.intents = None
    analyze.main(args)
    report = json.loads((project / "out.json").read_text(encoding="utf-8"))
    assert report["detectors"]["mismatch"]["status"] == "unavailable"
    assert any("mismatch detector inactive" in w for w in report["warnings"])


def test_seasonality_compares_year_over_year(project, stub_cannibal):
    report = run_analyze(project)
    hits = findings_of(report, "seasonality")
    assert hits, "a year of history is present, so a YoY comparison must be attempted"
    hit = hits[0]
    assert hit["metrics"]["impressions_year_ago"] == 20000
    assert hit["metrics"]["yoy_change"] < -0.30


def test_seasonality_reports_insufficient_history_as_a_finding(project, stub_cannibal):
    """The absence of a year of data is the operational argument for MSR-08, not a silent skip."""
    from kiln_common import Thresholds

    rows = [analyze.Row(NOW_DAY, "q", f"{UK}/x", 1, 100, 5.0)]
    windows = analyze.build_windows(rows, 28, 28, 4)
    thresholds = Thresholds(analyze.DOCTRINE_DEFAULTS, {})
    hits = analyze.detect_seasonality(rows, windows, thresholds, "uk")
    assert len(hits) == 1
    assert hits[0].evidence["metrics"]["status"] == "insufficient_history"
    assert hits[0].thresholds_used, "even the no-data finding records its thresholds"


# --------------------------------------------------------------------------------------------
# Cannibalization arrives through the import
# --------------------------------------------------------------------------------------------


def test_cannibalization_is_delegated_not_reimplemented(project, stub_cannibal):
    report = run_analyze(project)

    assert len(stub_cannibal) == 1, "cannibal_detect.detect() must be called exactly once"
    call = stub_cannibal[0]
    assert call["locale"] == "uk"
    assert all(isinstance(r, dict) for r in call["rows"]), "rows cross the boundary as plain dicts"
    # Branded rows are filtered by the caller; locale filtering happens before the call.
    assert all(r["locale"] == "uk" for r in call["rows"])
    assert not any("example brand" in r["query"] for r in call["rows"])
    # Full history, so the callee can apply its own 28/90-day windows per §5.1.
    assert {r["date"] for r in call["rows"]} >= {NOW_DAY.isoformat(), YEAR_AGO_DAY.isoformat()}

    hits = findings_of(report, "cannibalization")
    assert [f["rule_id"] for f in hits] == ["LNK-25"]
    assert report["leading_indicators"]["LI-7_cannibalized_queries"] == 1


def test_callee_defaults_are_merged_and_today_is_pinned_to_the_data(project, stub_cannibal):
    """The cross-script threshold contract, and the reason it exists.

    A `Thresholds` built from this file's defaults carries no `cannibalization.*` key, so the
    callee's first read would raise. And left to its own default the callee would trim relative to
    the wall clock, making the same export analyse differently tomorrow.
    """
    run_analyze(project)
    call = stub_cannibal[0]
    assert call["today"] == MAX_DATE
    assert call["brand_tokens"] == ("example brand",)
    assert call["thresholds"].get("cannibalization.flip_rate") == 0.30


def test_real_cannibal_detect_satisfies_the_contract(project):
    """Integration, no stub: the unit tests passed while the on-disk contract was broken."""
    pytest.importorskip("cannibal_detect")
    report = run_analyze(project)
    assert report["detectors"]["cannibalization"]["status"] == "ran"
    assert isinstance(report["leading_indicators"]["LI-7_cannibalized_queries"], int)
    for finding in findings_of(report, "cannibalization"):
        assert finding["thresholds_used"], "the callee must attach its own provenance"


def test_no_local_cannibalization_implementation_exists():
    """Guards against someone quietly adding a second implementation of one calculation."""
    source = Path(analyze.__file__).read_text(encoding="utf-8")
    assert "def detect_cannibal" not in source
    assert "flip_rate =" not in source, "flip_rate is computed in cannibal_detect.py only"
    assert "importlib.import_module(\"cannibal_detect\")" in source


def test_missing_cannibal_module_is_reported_not_swallowed(project, no_cannibal):
    report = run_analyze(project)
    assert report["detectors"]["cannibalization"]["status"] == "unavailable"
    assert findings_of(report, "cannibalization") == []
    assert report["leading_indicators"]["LI-7_cannibalized_queries"] is None
    assert any("cannibalization detector unavailable" in w for w in report["warnings"])


# --------------------------------------------------------------------------------------------
# Provenance, locale, determinism
# --------------------------------------------------------------------------------------------


def test_every_finding_records_the_thresholds_that_produced_it(project, stub_cannibal):
    report = run_analyze(project)
    assert report["findings"], "the fixture must produce findings for this test to mean anything"
    for finding in report["findings"]:
        used = finding["thresholds_used"]
        assert used, f"{finding['id']} carries no threshold provenance"
        for entry in used:
            assert set(entry) >= {"key", "value", "source"}
            assert entry["source"] in ("doctrine", "local", "fallback")


def test_threshold_provenance_switches_to_local_when_calibrated(project, stub_cannibal):
    (project / ".kiln" / "thresholds.yml").write_text(
        "striking:\n  min_impressions: 400\n", encoding="utf-8"
    )
    report = run_analyze(project)
    striking = findings_of(report, "striking")
    entry = next(
        e for e in striking[0]["thresholds_used"] if e["key"] == "striking.min_impressions"
    )
    assert entry == {"key": "striking.min_impressions", "value": 400, "source": "local"}
    # 200 impressions now sits below the raised floor.
    assert not any(f["subject"].startswith("ctr outlier") for f in striking)


def test_locales_are_separated_before_any_threshold(project, stub_cannibal):
    report = run_analyze(project)
    assert report["locale"] == "uk"
    for finding in report["findings"]:
        assert "en.example.com" not in finding["subject"]

    # The English row carries 99,000 impressions on the same query. If locales leaked, the
    # striking metrics would be dominated by it.
    striking = next(
        f for f in findings_of(report, "striking") if f["subject"].startswith("striking query")
    )
    assert striking["metrics"]["impressions"] == 500

    for call_rows in (r for c in stub_cannibal for r in c["rows"]):
        assert "en.example.com" not in call_rows["page"]


def test_mixed_locales_without_a_choice_is_an_error(project, stub_cannibal):
    args = make_args(project)
    args.locale = None
    with pytest.raises(KilnError, match="pass --locale"):
        analyze.main(args)


def test_unresolvable_locale_refuses_to_guess(tmp_path, stub_cannibal):
    raw = tmp_path / "raw"
    raw.mkdir()
    (raw / "rows.jsonl").write_text(
        json.dumps(_row(NOW_DAY, "q", "https://other.test/a", 1, 100, 5.0)) + "\n",
        encoding="utf-8",
    )
    (tmp_path / ".kiln").mkdir()
    (tmp_path / ".kiln" / "project.yml").write_text(
        'locales:\n  uk:\n    host: "uk."\n  en:\n    host: "en."\n', encoding="utf-8"
    )
    args = analyze.build_parser().parse_args(
        ["--project-root", str(tmp_path), "--raw", str(raw), "--out", str(tmp_path / "o.json")]
    )
    with pytest.raises(KilnError, match="MSR-22"):
        analyze.main(args)


def test_two_runs_are_byte_identical(project, stub_cannibal):
    run_analyze(project)
    first = (project / "out.json").read_bytes()
    (project / "out.json").unlink()
    run_analyze(project)
    second = (project / "out.json").read_bytes()
    assert first == second


# --------------------------------------------------------------------------------------------
# Segmentation gate and observe mode
# --------------------------------------------------------------------------------------------


def test_missing_brand_tokens_blocks_and_writes_the_report_first(project, stub_cannibal):
    (project / ".kiln" / "project.yml").write_text(
        'locales:\n  uk:\n    host: "uk."\n  en:\n    host: "en."\n', encoding="utf-8"
    )
    args = make_args(project)
    with pytest.raises(GateFailure, match="MSR-04"):
        analyze.main(args)
    # The output must exist even when the gate fails; a blocked run still has to be inspectable.
    report = json.loads((project / "out.json").read_text(encoding="utf-8"))
    assert findings_of(report, "segmentation")[0]["severity"] == "BLOCK"


def test_observe_downgrades_rather_than_hides(project, stub_cannibal):
    (project / ".kiln" / "project.yml").write_text(
        'locales:\n  uk:\n    host: "uk."\n  en:\n    host: "en."\n', encoding="utf-8"
    )
    report = run_analyze(project, "--observe")
    segmentation = findings_of(report, "segmentation")[0]
    assert segmentation["severity"] == "WARN"
    assert segmentation["evidence"]["observed_downgrade_from"] == "BLOCK"


def test_branded_traffic_is_reported_but_excluded(project, stub_cannibal):
    report = run_analyze(project)
    assert report["segment"] == "non_brand"
    assert report["branded_segment"]["clicks"] == 100
    assert report["branded_segment"]["impressions"] == 800
    for finding in report["findings"]:
        assert "example brand" not in finding["subject"]


# --------------------------------------------------------------------------------------------
# Windows, aggregation, indicators
# --------------------------------------------------------------------------------------------


def test_windows_are_equal_length_and_trimmed(project, stub_cannibal):
    report = run_analyze(project)
    now_start, now_end = (dt.date.fromisoformat(d) for d in report["window"]["now"])
    prior_start, prior_end = (dt.date.fromisoformat(d) for d in report["window"]["prior"])
    assert now_end == MAX_DATE - dt.timedelta(days=4)  # MSR-06
    assert (now_end - now_start).days == (prior_end - prior_start).days == 27
    assert prior_end == now_start - dt.timedelta(days=1)


def test_position_is_impression_weighted_and_ctr_recomputed():
    """MSR-12: a one-impression tail query must not weigh as much as a head term."""
    agg = analyze.Agg()
    agg.add(analyze.Row(NOW_DAY, "q", "/a", clicks=1, impressions=1, position=100.0))
    agg.add(analyze.Row(NOW_DAY, "q", "/a", clicks=9, impressions=999, position=1.0))
    assert agg.position == pytest.approx((100.0 * 1 + 1.0 * 999) / 1000)
    assert agg.ctr == pytest.approx(10 / 1000)


def test_repeated_keys_are_grouped_before_summing():
    """MSR-09: export rows are not deduplicated, so aggregation must group first."""
    rows = [analyze.Row(NOW_DAY, "q", "/a", 1, 10, 5.0) for _ in range(3)]
    grouped = analyze.aggregate(rows, lambda r: (r.query, r.page))
    assert len(grouped) == 1
    assert grouped[("q", "/a")].impressions == 30


def test_bigquery_sum_position_is_converted_to_one_based():
    """§5.0: `sum_position` is 0-based and needs the +1."""
    row = analyze._coerce_row(
        {"date": "2026-07-15", "query": "q", "page": "/a", "impressions": 100, "sum_position": 400},
        "t",
    )
    assert row.position == pytest.approx(5.0)


def test_all_eight_leading_indicators_are_always_present(project, stub_cannibal):
    report = run_analyze(project)
    li = report["leading_indicators"]
    for n in range(1, 9):
        assert any(k.startswith(f"LI-{n}_") for k in li), f"LI-{n} missing"
    # What cannot be computed is null with a stated reason, never an invented number.
    assert li["LI-5_ai_citation_rate"] is None
    assert "MSR-15" in report["leading_indicators_unavailable"]["LI-5_ai_citation_rate"]
    assert li["LI-1_indexation_rate"] == 1.0  # /credits/guide published in window and indexed
    assert li["LI-2_days_to_first_impression_median"] == 5


def test_summary_counts_match_the_findings(project, stub_cannibal):
    report = run_analyze(project)
    summary = report["summary"]
    assert summary["total"] == len(report["findings"])
    assert sum(summary["by_severity"].values()) == summary["total"]
    assert sum(summary["by_detector"].values()) == summary["total"]
    for detector, count in summary["by_detector"].items():
        assert count == len(findings_of(report, detector))


def test_anonymization_gap_is_stated_on_its_own_line(project, stub_cannibal):
    report = run_analyze(project)
    assert any("anonymized_share" in w and "MSR-07" in w for w in report["warnings"])


def test_unknown_detector_is_rejected(project, stub_cannibal):
    args = make_args(project, "--detectors", "striking,teleport")
    with pytest.raises(KilnError, match="unknown detectors"):
        analyze.main(args)


# ---------------------------------------------------------------------------
# Rule identifier integrity
#
# The first version of this script emitted `MSR-5.2`, `MSR-5.3` and so on: section numbers used as  # kiln-lint: ignore code_doctrine_ids -- names the malformed IDs this suite exists to reject; a mention, not a citation
# rule identifiers. Nothing failed at runtime. The findings simply could never be joined to
# `.kiln/rules-stats.json`, to a reviewer override, or to anything else that would let a detector
# be improved. That is why this is a test and not a linter warning.
# ---------------------------------------------------------------------------

import re as _re
from pathlib import Path as _Path

_DOCTRINE = _Path(__file__).resolve().parents[2] / "doctrine"
_SCRIPT = _Path(__file__).resolve().parents[1] / "analyze.py"


def _doctrine_rule_ids(filename: str, prefix: str) -> set[str]:
    """Rule IDs defined in a doctrine file, across all three definition shapes it uses."""
    text = (_DOCTRINE / filename).read_text(encoding="utf-8")
    ids: set[str] = set()
    ids |= set(_re.findall(rf"^#{{2,4}} ({prefix}-\d+)\s*·", text, _re.M))
    ids |= set(_re.findall(rf"^\*\*Rule `({prefix}-\d+)`", text, _re.M))
    ids |= set(_re.findall(rf"^\|\s*`({prefix}-\d+)`\s*\|", text, _re.M))
    return ids


def _emitted_rule_ids() -> set[str]:
    return set(_re.findall(r'rule_id="([A-Z]+-[\w.]+)"', _SCRIPT.read_text(encoding="utf-8")))


def test_every_emitted_rule_id_is_well_formed():
    for rule_id in _emitted_rule_ids():
        assert _re.fullmatch(r"[A-Z]{3}-\d{2}", rule_id), (
            f"{rule_id!r} is not a rule identifier. Section numbers such as 'MSR-5.2' resolve to "  # kiln-lint: ignore code_doctrine_ids -- failure message quoting the forbidden shape
            f"nothing in the doctrine."
        )


def test_every_emitted_rule_id_exists_in_the_doctrine():
    known = _doctrine_rule_ids("08-measurement.md", "MSR") | _doctrine_rule_ids("07-linking.md", "LNK")
    unresolved = _emitted_rule_ids() - known
    assert not unresolved, (
        f"emitted but undefined in the doctrine: {sorted(unresolved)}. Either the detector cites "
        f"the wrong rule, or the rule needs minting via RULE-CHANGE.md."
    )


def test_each_detector_names_exactly_one_rule():
    """One detector, one ID, and no ID shared across detectors.

    Seasonality is the case that forced this: it reported both a year-over-year result and a
    "there is not enough history to compare" state under one ID, which makes 'no seasonality' and
    'no data' indistinguishable in the counters. They are now MSR-29 and MSR-30.
    """
    source = _SCRIPT.read_text(encoding="utf-8")
    pairs = _re.findall(r'rule_id="([A-Z]{3}-\d{2})".*?detector="(\w+)"', source, _re.S)
    by_rule: dict[str, set[str]] = {}
    for rule_id, detector in pairs:
        by_rule.setdefault(rule_id, set()).add(detector)
    shared = {r: d for r, d in by_rule.items() if len(d) > 1}
    assert not shared, f"rule IDs claimed by more than one detector: {shared}"
