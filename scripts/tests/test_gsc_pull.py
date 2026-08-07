"""Tests for gsc_pull.

The four traps from `doctrine/08-measurement.md` all fail silently in production, so each one has a
test that fails loudly here: deduplication (MSR-09), the empty-string anonymised query (MSR-10),
`epoch_version` (MSR-11), and trailing-window trimming (MSR-06). Plus the position base conversion,
which is wrong by exactly one in a way that looks entirely plausible.

No credentials and no cloud libraries are required. Network paths run against recorded fixtures.
"""

from __future__ import annotations

import json
from pathlib import Path

import pytest

import gsc_pull as gp
from kiln_common import KilnError

pytest.importorskip("yaml", reason="PyYAML is required to read project.yml")


PROJECT_YML = """\
locales:
  - code: uk
    url_pattern: "/"
    lang_ruleset: uk
    is_primary: true
  - code: en
    url_pattern: "/en/"
    lang_ruleset: en
    is_primary: false
"""


@pytest.fixture()
def project(tmp_path: Path) -> Path:
    (tmp_path / ".kiln").mkdir()
    (tmp_path / ".kiln" / "project.yml").write_text(PROJECT_YML, encoding="utf-8")
    return tmp_path


def run_cli(argv: list[str]) -> int:
    """Invoke main through the real parser, so flag wiring is covered too."""
    return gp.main(gp._parser().parse_args(argv))


# ---------------------------------------------------------------------------
# MSR-09: rows are not deduplicated
# ---------------------------------------------------------------------------


def test_duplicate_keys_are_collapsed_before_aggregation():
    """A direct SUM over repeated keys inflates every figure downstream."""
    rows = [
        {"date": "2026-07-01", "query": "кредит", "page": "https://x.ua/a",
         "clicks": 2, "impressions": 100, "position": 3.0},
        {"date": "2026-07-01", "query": "кредит", "page": "https://x.ua/a",
         "clicks": 3, "impressions": 300, "position": 5.0},
    ]
    out = gp.aggregate_rows(rows)

    assert len(out) == 1
    assert out[0]["clicks"] == 5
    assert out[0]["impressions"] == 400
    # Impression-weighted, not the arithmetic mean of 3.0 and 5.0 (which would be 4.0).
    assert out[0]["position"] == pytest.approx(4.5)


def test_position_merge_is_impression_weighted_not_row_averaged():
    """MSR-12: a one-impression tail query must not weigh as much as a head term."""
    rows = [
        {"date": "2026-07-01", "query": "q", "page": "/a", "clicks": 0,
         "impressions": 1, "position": 90.0},
        {"date": "2026-07-01", "query": "q", "page": "/a", "clicks": 0,
         "impressions": 9999, "position": 2.0},
    ]
    position = gp.aggregate_rows(rows)[0]["position"]

    assert position < 3.0, "row-averaging would have produced 46.0"


def test_zero_impressions_yields_null_position_rather_than_dividing_by_zero():
    rows = [{"date": "2026-07-01", "query": "q", "page": "/a",
             "clicks": 0, "impressions": 0, "position": None}]
    assert gp.aggregate_rows(rows)[0]["position"] is None


def test_aggregation_output_is_deterministically_ordered():
    rows = [
        {"date": "2026-07-02", "query": "б", "page": "/b", "clicks": 1, "impressions": 1, "position": 1.0},
        {"date": "2026-07-01", "query": "а", "page": "/a", "clicks": 1, "impressions": 1, "position": 1.0},
        {"date": "2026-07-01", "query": "я", "page": "/c", "clicks": 1, "impressions": 1, "position": 1.0},
    ]
    first = [(r["date"], r["query"]) for r in gp.aggregate_rows(rows)]
    second = [(r["date"], r["query"]) for r in gp.aggregate_rows(list(reversed(rows)))]

    assert first == second
    assert first[0] == ("2026-07-01", "а")


# ---------------------------------------------------------------------------
# MSR-10: an anonymised query is an empty string, not NULL
# ---------------------------------------------------------------------------


def test_empty_string_query_is_flagged_anonymised_and_kept():
    """Dropping these rows makes the totals disagree with the console for no visible reason."""
    records = [
        {"data_date": "2026-07-01", "query": "", "url": "https://x.ua/a",
         "clicks": 0, "impressions": 500, "sum_position": 1000.0},
        {"data_date": "2026-07-01", "query": "кредит", "url": "https://x.ua/a",
         "clicks": 5, "impressions": 100, "sum_position": 200.0},
    ]
    rows = gp.rows_from_bq_records(records)

    assert rows[0]["is_anonymized_query"] is True
    assert rows[1]["is_anonymized_query"] is False
    assert len(rows) == 2, "anonymised rows are kept, not filtered"


def test_anonymised_share_is_impression_weighted_and_reported():
    rows = [
        {"query": "", "is_anonymized_query": True, "impressions": 300, "clicks": 0, "locale": "uk"},
        {"query": "кредит", "is_anonymized_query": False, "impressions": 700, "clicks": 5, "locale": "uk"},
    ]
    manifest = gp.build_manifest(
        property_url="sc-domain:x.ua", source="bigquery", pulled_at="2026-08-07T00:00:00Z",
        requested=("2026-07-01", "2026-07-31"), effective=("2026-07-01", "2026-07-31"),
        trim_days=4, trimmed=False, rows=rows, dimensions=("date", "query", "page"),
        epoch_versions={}, epoch_changed=[], truncated=False,
        quota_used={}, date_granularity="date", unmapped_locale_rows=0, schema_probe=None,
    )

    assert manifest["anonymized_share"] == pytest.approx(0.3)
    assert manifest["anonymized_rows"] == 1


def test_is_anonymized_query_column_is_honoured_when_present():
    records = [{"data_date": "2026-07-01", "query": "x", "url": "/a", "clicks": 0,
                "impressions": 10, "sum_position": 10.0, "is_anonymized_query": True}]
    assert gp.rows_from_bq_records(records)[0]["is_anonymized_query"] is True


# ---------------------------------------------------------------------------
# Position base conversion
# ---------------------------------------------------------------------------


def test_bigquery_sum_position_is_zero_based_and_gains_one():
    """`sum_position / impressions + 1`. Omitting the +1 shifts every threshold by one."""
    records = [{"data_date": "2026-07-01", "query": "q", "url": "/a",
                "clicks": 1, "impressions": 340, "sum_position": 1234.0}]
    assert gp.rows_from_bq_records(records)[0]["position"] == pytest.approx(4.6294, abs=1e-4)


def test_bigquery_site_table_uses_sum_top_position_and_carries_no_url():
    """The site table cannot detect cannibalization; it has no url, and that must be visible."""
    records = [{"data_date": "2026-07-01", "query": "q", "clicks": 1,
                "impressions": 100, "sum_position": 0.0}]
    row = gp.rows_from_bq_records(records, table="site")

    assert row[0]["position"] == pytest.approx(1.0), "a 0-based sum of 0 is position 1"
    assert row[0]["page"] is None


def test_api_position_is_already_one_based_and_is_not_adjusted():
    payload = {"rows": [{"keys": ["2026-07-01", "кредит", "https://x.ua/a"],
                         "clicks": 5, "impressions": 100, "position": 4.6294}]}
    rows = gp.rows_from_api_response(payload, ("date", "query", "page"))

    assert rows[0]["position"] == pytest.approx(4.6294)


def test_api_response_key_count_mismatch_is_an_error_not_a_silent_shift():
    payload = {"rows": [{"keys": ["2026-07-01"], "clicks": 1, "impressions": 1, "position": 1.0}]}
    with pytest.raises(KilnError, match="does not match the request"):
        gp.rows_from_api_response(payload, ("date", "query", "page"))


# ---------------------------------------------------------------------------
# MSR-06: trailing window trimming
# ---------------------------------------------------------------------------


def test_trailing_provisional_days_are_trimmed():
    import datetime as dt

    start, end, trimmed = gp.effective_window("2026-07-01", "2026-08-07", 4, dt.date(2026, 8, 7))

    assert (start, end, trimmed) == ("2026-07-01", "2026-08-03", True)


def test_historical_window_is_not_trimmed():
    """Trimming is relative to today; clipping a settled window would discard good data."""
    import datetime as dt

    assert gp.effective_window("2026-01-01", "2026-01-31", 4, dt.date(2026, 8, 7)) == (
        "2026-01-01", "2026-01-31", False,
    )


def test_a_window_entirely_inside_the_provisional_zone_is_refused():
    import datetime as dt

    with pytest.raises(KilnError, match="provisional zone"):
        gp.effective_window("2026-08-05", "2026-08-07", 4, dt.date(2026, 8, 7))


def test_reversed_window_is_rejected():
    import datetime as dt

    with pytest.raises(KilnError, match="is after"):
        gp.effective_window("2026-08-07", "2026-07-01", 4, dt.date(2026, 8, 7))


# ---------------------------------------------------------------------------
# Locale resolution (MSR-22)
# ---------------------------------------------------------------------------


def test_locale_matches_the_most_specific_url_pattern(project: Path):
    rules = gp.load_locales(project)

    assert gp.locale_for_url("https://example.com/en/loans", rules) == "en"
    assert gp.locale_for_url("https://example.com/kredyty", rules) == "uk"


def test_unmapped_url_returns_none_rather_than_defaulting_to_primary():
    """Filing an unmapped URL under the primary locale corrupts the segmentation MSR-22 protects."""
    rules = [gp.LocaleRule("en", "/en/"), gp.LocaleRule("de", "/de/")]

    assert gp.locale_for_url("https://x.com/fr/page", rules) is None


def test_subdomain_and_cctld_patterns_are_supported():
    rules = [gp.LocaleRule("en", "en.example.com"), gp.LocaleRule("uk", "example.com.ua")]

    assert gp.locale_for_url("https://en.example.com/a", rules) == "en"
    assert gp.locale_for_url("https://www.example.com.ua/a", rules) == "uk"


def test_missing_project_yml_is_an_error(tmp_path: Path):
    with pytest.raises(KilnError, match="ONB-24"):
        gp.load_locales(tmp_path)


def test_project_yml_without_locales_is_an_error(tmp_path: Path):
    (tmp_path / ".kiln").mkdir()
    (tmp_path / ".kiln" / "project.yml").write_text("mode: full\n", encoding="utf-8")

    with pytest.raises(KilnError, match="declares no `locales`"):
        gp.load_locales(tmp_path)


# ---------------------------------------------------------------------------
# CSV source, end to end
# ---------------------------------------------------------------------------

CSV_WITH_DATES = """\
Date,Query,Page,Clicks,Impressions,CTR,Position
2026-07-01,кредит онлайн на картку,https://example.com/kredyty/online,12,340,3.53%,4.63
2026-07-01,кредит онлайн на картку,https://example.com/kredyty/online,3,60,5.00%,4.00
2026-07-01,,https://example.com/kredyty/online,0,500,0.00%,18.20
2026-07-01,loan calculator,https://example.com/en/loans,7,120,5.83%,6.10
"""


def test_csv_end_to_end_writes_rows_and_manifest(project: Path, capsys):
    csv_path = project / "export.csv"
    csv_path.write_text(CSV_WITH_DATES, encoding="utf-8")

    code = run_cli([
        "--project-root", str(project), "--property", "sc-domain:example.com",
        "--start", "2026-07-01", "--end", "2026-07-31", "--source", "csv",
        "--csv-file", str(csv_path), "--today", "2026-08-07",
        "--pulled-at", "2026-08-07T00:00:00Z",
    ])
    capsys.readouterr()

    assert code == 0
    out_dir = project / ".kiln" / "measurements" / "raw" / "sc-domain_example.com"
    rows = [json.loads(line) for line in (out_dir / "2026-07-01.jsonl").read_text(encoding="utf-8").splitlines()]

    # Four input rows, two of which share a key, so three survive aggregation.
    assert len(rows) == 3
    merged = next(r for r in rows if r["query"] == "кредит онлайн на картку")
    assert merged["clicks"] == 15
    assert merged["impressions"] == 400
    assert merged["locale"] == "uk"

    anonymised = next(r for r in rows if r["query"] == "")
    assert anonymised["is_anonymized_query"] is True

    english = next(r for r in rows if r["query"] == "loan calculator")
    assert english["locale"] == "en"

    manifest = json.loads((out_dir / "_manifest.json").read_text(encoding="utf-8"))
    assert manifest["source"] == "csv"
    assert manifest["row_count"] == 3
    assert manifest["date_granularity"] == "date"
    assert manifest["unmapped_locale_rows"] == 0
    assert manifest["locales_seen"] == {"en": 1, "uk": 2}


def test_csv_cyrillic_survives_the_round_trip_unescaped(project: Path, capsys):
    """Escaped Cyrillic makes a pull request diff unreadable, and these files are reviewed by humans."""
    csv_path = project / "export.csv"
    csv_path.write_text(CSV_WITH_DATES, encoding="utf-8")
    run_cli([
        "--project-root", str(project), "--property", "sc-domain:example.com",
        "--start", "2026-07-01", "--end", "2026-07-31", "--source", "csv",
        "--csv-file", str(csv_path), "--today", "2026-08-07", "--pulled-at", "2026-08-07T00:00:00Z",
    ])
    capsys.readouterr()

    raw = (project / ".kiln" / "measurements" / "raw" / "sc-domain_example.com" / "2026-07-01.jsonl").read_text(encoding="utf-8")
    assert "кредит онлайн на картку" in raw
    assert "\\u043a" not in raw


def test_csv_without_a_date_column_declares_window_granularity(project: Path, capsys):
    """Decay and year-over-year are undefined without dates, and must be able to refuse to run."""
    csv_path = project / "queries.csv"
    csv_path.write_text("Query,Clicks,Impressions,Position\nкредит,5,100,4.2\n", encoding="utf-8")

    run_cli([
        "--project-root", str(project), "--property", "sc-domain:example.com",
        "--start", "2026-07-01", "--end", "2026-07-31", "--source", "csv",
        "--csv-file", str(csv_path), "--today", "2026-08-07", "--pulled-at", "2026-08-07T00:00:00Z",
    ])
    out = json.loads(capsys.readouterr().out)

    assert out["manifest"]["date_granularity"] == "window"
    # No page column means no locale can be resolved, and the manifest says so instead of guessing.
    assert out["manifest"]["unmapped_locale_rows"] == 1
    assert out["manifest"]["usable"] is False


def test_csv_with_semicolons_and_localised_headers_is_read(project: Path):
    csv_path = project / "ru.csv"
    csv_path.write_text(
        "Дата;Запрос;Страница;Клики;Показы;Позиция\n"
        "2026-07-01;кредит;https://example.com/kredyty;10;200;3,5\n",
        encoding="utf-8",
    )
    rows, has_date = gp.rows_from_csv(csv_path)

    assert has_date is True
    assert rows[0]["clicks"] == 10
    assert rows[0]["position"] == pytest.approx(3.5), "a decimal comma is not a thousands separator"


def test_csv_with_no_recognised_columns_names_the_headers_it_saw(project: Path):
    csv_path = project / "junk.csv"
    csv_path.write_text("alpha,beta\n1,2\n", encoding="utf-8")

    with pytest.raises(KilnError, match="no query or page column recognised"):
        gp.rows_from_csv(csv_path)


def test_csv_non_numeric_metric_names_the_line(project: Path):
    csv_path = project / "bad.csv"
    csv_path.write_text("Query,Clicks,Impressions\nкредит,many,100\n", encoding="utf-8")

    with pytest.raises(KilnError, match=r"bad\.csv:2: clicks is not numeric"):
        gp.rows_from_csv(csv_path)


def test_csv_run_is_byte_identical_when_repeated(project: Path, capsys):
    csv_path = project / "export.csv"
    csv_path.write_text(CSV_WITH_DATES, encoding="utf-8")
    argv = [
        "--project-root", str(project), "--property", "sc-domain:example.com",
        "--start", "2026-07-01", "--end", "2026-07-31", "--source", "csv",
        "--csv-file", str(csv_path), "--today", "2026-08-07", "--pulled-at", "2026-08-07T00:00:00Z",
    ]
    out_file = project / ".kiln" / "measurements" / "raw" / "sc-domain_example.com" / "2026-07-01.jsonl"

    run_cli(argv)
    capsys.readouterr()
    first = out_file.read_bytes()
    run_cli(argv)
    capsys.readouterr()

    assert out_file.read_bytes() == first


def test_dry_run_writes_nothing(project: Path, capsys):
    csv_path = project / "export.csv"
    csv_path.write_text(CSV_WITH_DATES, encoding="utf-8")

    run_cli([
        "--project-root", str(project), "--property", "sc-domain:example.com",
        "--start", "2026-07-01", "--end", "2026-07-31", "--source", "csv",
        "--csv-file", str(csv_path), "--today", "2026-08-07",
        "--pulled-at", "2026-08-07T00:00:00Z", "--dry-run",
    ])
    capsys.readouterr()

    assert not (project / ".kiln" / "measurements" / "raw").exists()


def test_repull_replaces_the_range_rather_than_upserting_rows(project: Path, capsys):
    """Row-level upsert leaves behind rows Google has since removed, indistinguishable from real ones."""
    out_dir = project / ".kiln" / "measurements" / "raw" / "sc-domain_example.com"
    out_dir.mkdir(parents=True)
    (out_dir / "2026-07-01.jsonl").write_text('{"query": "stale"}\n', encoding="utf-8")

    csv_path = project / "export.csv"
    csv_path.write_text(CSV_WITH_DATES, encoding="utf-8")
    run_cli([
        "--project-root", str(project), "--property", "sc-domain:example.com",
        "--start", "2026-07-01", "--end", "2026-07-31", "--source", "csv",
        "--csv-file", str(csv_path), "--today", "2026-08-07", "--pulled-at", "2026-08-07T00:00:00Z",
    ])
    capsys.readouterr()

    assert "stale" not in (out_dir / "2026-07-01.jsonl").read_text(encoding="utf-8")


# ---------------------------------------------------------------------------
# API source against a recorded fixture
# ---------------------------------------------------------------------------


class _Exec:
    def __init__(self, payload: dict) -> None:
        self._payload = payload

    def execute(self) -> dict:
        return self._payload


class _SearchAnalytics:
    def __init__(self, pages: list[dict], calls: list[dict]) -> None:
        self._pages, self._calls = pages, calls

    def query(self, siteUrl: str, body: dict) -> _Exec:  # noqa: N803 - vendor signature
        self._calls.append(body)
        index = body["startRow"] // body["rowLimit"]
        return _Exec(self._pages[index] if index < len(self._pages) else {"rows": []})


class FakeService:
    """Stands in for the Google client. No credentials, no network."""

    def __init__(self, pages: list[dict]) -> None:
        self._pages = pages
        self.calls: list[dict] = []

    def searchanalytics(self) -> _SearchAnalytics:
        return _SearchAnalytics(self._pages, self.calls)


def _page(n: int, offset: int = 0) -> dict:
    return {"rows": [
        {"keys": ["2026-07-01", f"запит {i + offset}", "https://example.com/a"],
         "clicks": 1, "impressions": 10, "position": 5.0}
        for i in range(n)
    ]}


def test_api_pagination_stops_on_a_short_page():
    service = FakeService([_page(2), _page(1, offset=2)])
    rows, requests, truncated = gp.fetch_api(
        service, "sc-domain:example.com", "2026-07-01", "2026-07-31",
        ("date", "query", "page"), "web", "final", row_limit=2, max_rows=1000,
    )

    assert len(rows) == 3
    assert requests == 2
    assert truncated is False
    assert service.calls[1]["startRow"] == 2


def test_api_truncation_is_reported_not_hidden():
    """A silently truncated pull looks exactly like a site that lost half its queries."""
    service = FakeService([_page(2), _page(2, offset=2), _page(2, offset=4)])
    rows, _, truncated = gp.fetch_api(
        service, "sc-domain:example.com", "2026-07-01", "2026-07-31",
        ("date", "query", "page"), "web", "final", row_limit=2, max_rows=3,
    )

    assert truncated is True
    assert len(rows) == 4


def test_truncated_pull_is_marked_unusable_in_the_manifest():
    manifest = gp.build_manifest(
        property_url="sc-domain:example.com", source="api", pulled_at="2026-08-07T00:00:00Z",
        requested=("2026-07-01", "2026-07-31"), effective=("2026-07-01", "2026-07-31"),
        trim_days=4, trimmed=False, rows=[], dimensions=("date",),
        epoch_versions={}, epoch_changed=[], truncated=True,
        quota_used={"search_analytics_queries": 3}, date_granularity="date",
        unmapped_locale_rows=0, schema_probe=None,
    )

    assert manifest["truncated"] is True
    assert manifest["usable"] is False


def test_api_quota_is_counted_by_us_not_parsed_from_errors():
    """MSR-05: the quota-exceeded message is identical for every quota type."""
    service = FakeService([_page(2), _page(2, offset=2), _page(1, offset=4)])
    _, requests, _ = gp.fetch_api(
        service, "sc-domain:example.com", "2026-07-01", "2026-07-31",
        ("date", "query", "page"), "web", "final", row_limit=2, max_rows=1000,
    )

    assert requests == 3


def test_hourly_dimension_parses_the_timestamp_form():
    payload = {"rows": [{"keys": ["2026-07-01", "2026-07-01T14:00:00-07:00", "/a"],
                         "clicks": 1, "impressions": 5, "position": 2.0}]}
    rows = gp.rows_from_api_response(payload, ("date", "hour", "page"))

    assert rows[0]["hour"] == 14


# ---------------------------------------------------------------------------
# BigQuery source against a recorded fixture
# ---------------------------------------------------------------------------


class FakeBQ:
    """Matches a SQL fragment to a recorded result set. No credentials, no network."""

    def __init__(self, results: dict[str, list[dict]]) -> None:
        self._results = results
        self.statements: list[str] = []

    def query(self, sql: str, params: object = None) -> object:
        self.statements.append(sql)
        for fragment, rows in self._results.items():
            if fragment in sql:
                return iter(rows)
        return iter([])


def test_bigquery_sql_groups_before_aggregating():
    """MSR-09 is enforced in the statement itself, not left to the caller to remember."""
    assert "GROUP BY" in gp.BQ_URL_IMPRESSION_SQL
    assert "GROUP BY" in gp.BQ_SITE_IMPRESSION_SQL
    assert "data_date BETWEEN @start AND @end" in gp.BQ_URL_IMPRESSION_SQL, "partition pruning"


def test_bigquery_fetch_converts_position_and_counts_one_job():
    client = FakeBQ({"searchdata_url_impression": [
        {"data_date": "2026-07-01", "query": "кредит", "url": "https://example.com/a",
         "device": "MOBILE", "country": "ukr", "clicks": 4,
         "impressions": 340, "sum_position": 1234.0},
    ]})
    rows, jobs = gp.fetch_bigquery(client, "proj", "2026-07-01", "2026-07-31", "url")

    assert jobs == 1
    assert rows[0]["position"] == pytest.approx(4.6294, abs=1e-4)


def test_epoch_versions_are_read_per_date():
    client = FakeBQ({"ExportLog": [
        {"data_date": "2026-07-01", "epoch_version": 3},
        {"data_date": "2026-07-02", "epoch_version": 4},
    ]})

    assert gp.fetch_epoch_versions(client, "proj", "2026-07-01", "2026-07-31") == {
        "2026-07-01": 3, "2026-07-02": 4,
    }


def test_epoch_version_increment_is_detected_against_the_previous_manifest(project: Path):
    """MSR-11: silent recomputation destroys the ability to explain why a conclusion changed."""
    out_dir = project / ".kiln" / "measurements" / "raw" / "sc-domain_example.com"
    out_dir.mkdir(parents=True)
    (out_dir / "_manifest.json").write_text(
        json.dumps({"epoch_versions": {"2026-07-01": 3, "2026-07-02": 4}}), encoding="utf-8"
    )

    previous = gp.read_previous_epochs(out_dir)
    current = {"2026-07-01": 4, "2026-07-02": 4}
    changed = [d for d, v in current.items() if v > previous.get(d, v)]

    assert changed == ["2026-07-01"]


def test_manifest_with_a_rewritten_epoch_is_not_usable():
    manifest = gp.build_manifest(
        property_url="p", source="bigquery", pulled_at="2026-08-07T00:00:00Z",
        requested=("2026-07-01", "2026-07-31"), effective=("2026-07-01", "2026-07-31"),
        trim_days=4, trimmed=False, rows=[], dimensions=("date",),
        epoch_versions={"2026-07-01": 4}, epoch_changed=["2026-07-01"],
        truncated=False, quota_used={}, date_granularity="date",
        unmapped_locale_rows=0, schema_probe=None,
    )

    assert manifest["usable"] is False


def test_read_previous_epochs_on_a_fresh_project_is_empty(tmp_path: Path):
    assert gp.read_previous_epochs(tmp_path) == {}


def test_schema_probe_lists_is_columns(project: Path):
    """MSR-16: settles whether is_ai_overview exists on this property."""
    client = FakeBQ({"INFORMATION_SCHEMA": [
        {"column_name": "is_amp_top_stories"}, {"column_name": "is_anonymized_query"},
    ]})

    assert gp.probe_is_columns(client, "proj") == ["is_amp_top_stories", "is_anonymized_query"]


# ---------------------------------------------------------------------------
# Filesystem and guardrails
# ---------------------------------------------------------------------------


def test_property_slug_is_windows_safe():
    """`sc-domain:example.com` carries a colon, which is not a legal path character on Windows."""
    assert gp.property_slug("sc-domain:example.com") == "sc-domain_example.com"
    assert gp.property_slug("https://example.com/") == "https_example.com"


def test_hourly_pull_outside_the_eight_day_window_is_refused(project: Path):
    with pytest.raises(KilnError, match="8 days"):
        run_cli([
            "--project-root", str(project), "--property", "sc-domain:example.com",
            "--start", "2026-07-01", "--end", "2026-07-31", "--source", "csv",
            "--csv-file", str(project / "x.csv"), "--hourly", "--today", "2026-08-07",
        ])


def test_csv_source_without_a_file_is_an_error(project: Path):
    with pytest.raises(KilnError, match="requires --csv-file"):
        run_cli([
            "--project-root", str(project), "--property", "sc-domain:example.com",
            "--start", "2026-07-01", "--end", "2026-07-31", "--source", "csv",
            "--today", "2026-08-07",
        ])


def test_bigquery_without_a_gcp_project_is_an_error(project: Path):
    with pytest.raises(KilnError, match="requires --gcp-project"):
        run_cli([
            "--project-root", str(project), "--property", "sc-domain:example.com",
            "--start", "2026-07-01", "--end", "2026-07-31", "--source", "bigquery",
            "--today", "2026-08-07",
        ])


def test_credentials_are_read_from_the_environment_never_the_command_line(monkeypatch):
    monkeypatch.delenv("CLAUDE_PLUGIN_OPTION_GSC_CREDENTIALS", raising=False)
    monkeypatch.delenv("GOOGLE_APPLICATION_CREDENTIALS", raising=False)
    with pytest.raises(KilnError, match="no credentials"):
        gp._credentials_from_env()

    monkeypatch.setenv("CLAUDE_PLUGIN_OPTION_GSC_CREDENTIALS", "/tmp/sa.json")
    assert gp._credentials_from_env() == "/tmp/sa.json"


def test_readonly_scope_is_the_only_scope_requested():
    """"No write scopes ever" travels verbatim from the system this descends from."""
    assert gp.READONLY_SCOPE.endswith("webmasters.readonly")
