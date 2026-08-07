#!/usr/bin/env python3
"""Pull Search Console data and normalise it to one row shape.

Specification: `doctrine/08-measurement.md` §11.1. That file is authoritative for field names,
quotas and formulas; this module implements it.

The only script in layer 2 with network access. Everything downstream reads its output and never
talks to Google, which is what keeps the rest of the layer deterministic and testable offline.

Three sources, one output shape:

  --source api        Search Analytics API. `position` arrives 1-based, per row.
  --source bigquery   Bulk export tables. `sum_position` is 0-based and rows are NOT deduplicated.
  --source csv        A manual export. A project without API access still has to work on day one.

Four traps, all of which fail silently, and all of which are closed here:

  MSR-09  BigQuery rows carry repeated keys. Aggregating without collapsing them first inflates
          every figure in the system.
  MSR-10  An anonymised query is an empty string, never NULL. `WHERE query IS NOT NULL` filters
          nothing, and the rows it fails to exclude are invisible in the totals.
  MSR-11  `epoch_version` incrementing means Google rewrote history. Recomputing silently destroys
          any later ability to explain why a conclusion changed.
  MSR-06  The trailing 3-4 days are systematically under-reported. Comparing untrimmed windows
          manufactures decay on every single run.

Read-only scope, always. The working system this descends from carries "no write scopes ever" and
that constraint travels with it.
"""

from __future__ import annotations

import csv
import datetime as dt
import json
import os
import re
import sys
from collections import defaultdict
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Iterable, Sequence

from kiln_common import (
    EXIT_OK,
    EXIT_SCRIPT_SPECIFIC,
    KilnError,
    base_parser,
    dumps,
    run,
    stable_key,
    write_json,
    write_jsonl,
)

__all__ = [
    "LocaleRule",
    "NormalRow",
    "load_locales",
    "locale_for_url",
    "aggregate_rows",
    "assign_locales",
    "rows_from_api_response",
    "rows_from_bq_records",
    "rows_from_csv",
    "effective_window",
    "build_manifest",
    "BQ_URL_IMPRESSION_SQL",
    "BQ_SITE_IMPRESSION_SQL",
    "BQ_EXPORT_LOG_SQL",
    "BQ_SCHEMA_PROBE_SQL",
]


# ---------------------------------------------------------------------------
# Doctrine defaults
# ---------------------------------------------------------------------------
# Passed to Thresholds by the caller rather than parsed out of markdown: the doctrine file is
# authoritative for humans, and six scripts parsing it would produce six ways to misread it.

DOCTRINE_DEFAULTS: dict[str, Any] = {
    # MSR-06. Practice, not a Google guarantee, hence a threshold rather than a constant.
    "measurement.trim_days": 4,
    # Search Analytics API hard ceiling. 1-25,000; paginated via startRow.
    "measurement.api_row_limit": 25_000,
    # Our own stop, so a runaway pull cannot burn the per-site quota. MSR-05 in spirit.
    "measurement.api_max_rows": 1_000_000,
}

READONLY_SCOPE = "https://www.googleapis.com/auth/webmasters.readonly"

DEFAULT_DIMENSIONS = ("date", "query", "page")

# Search Console keeps 16 months and hourly data for 8 days. Pulling outside those windows returns
# empty results that read exactly like "our traffic vanished".
RETENTION_MONTHS = 16
HOURLY_RETENTION_DAYS = 8


# ---------------------------------------------------------------------------
# BigQuery statements
# ---------------------------------------------------------------------------
# The GROUP BY is not an optimisation. Without it the numbers are wrong and nothing says so.

BQ_URL_IMPRESSION_SQL = """
SELECT
  data_date,
  query,
  url,
  device,
  country,
  SUM(clicks)       AS clicks,
  SUM(impressions)  AS impressions,
  SUM(sum_position) AS sum_position
FROM `{project}.searchconsole.searchdata_url_impression`
WHERE data_date BETWEEN @start AND @end
GROUP BY data_date, query, url, device, country
""".strip()

BQ_SITE_IMPRESSION_SQL = """
SELECT
  data_date,
  query,
  device,
  country,
  SUM(clicks)           AS clicks,
  SUM(impressions)      AS impressions,
  SUM(sum_top_position) AS sum_position
FROM `{project}.searchconsole.searchdata_site_impression`
WHERE data_date BETWEEN @start AND @end
GROUP BY data_date, query, device, country
""".strip()

BQ_EXPORT_LOG_SQL = """
SELECT data_date, MAX(epoch_version) AS epoch_version
FROM `{project}.searchconsole.ExportLog`
WHERE agenda = 'SEARCHDATA' AND data_date BETWEEN @start AND @end
GROUP BY data_date
""".strip()

# MSR-16. One minute of work, resolves a documented contradiction between the official schema
# reference and practitioner reports about an `is_ai_overview` column.
BQ_SCHEMA_PROBE_SQL = """
SELECT column_name
FROM `{project}.searchconsole.INFORMATION_SCHEMA.COLUMNS`
WHERE table_name = 'searchdata_url_impression' AND column_name LIKE 'is_%'
ORDER BY column_name
""".strip()


# ---------------------------------------------------------------------------
# Locale resolution
# ---------------------------------------------------------------------------


@dataclass(frozen=True, slots=True)
class LocaleRule:
    """One entry from `project.yml:locales`.

    `url_pattern` is how the locale shows up in a URL: a path prefix (`/en/`), a subdomain
    (`en.example.com`) or a ccTLD (`example.co.uk`). Matching is by URL and never by the `country`
    dimension: country is where the searcher was, locale is which page served them, and the two
    diverge constantly (§0.1).
    """

    code: str
    url_pattern: str
    is_primary: bool = False

    @property
    def is_path(self) -> bool:
        return self.url_pattern.startswith("/")

    @property
    def specificity(self) -> int:
        """Longer patterns win. `/` is the catch-all and must lose to everything."""
        return len(self.url_pattern.rstrip("/"))


def load_locales(project_root: Path | str, project_yml: Path | str | None = None) -> list[LocaleRule]:
    """Read the declared locale set. An undeclared locale set is an error, not an empty list.

    ONB-24 makes the locale set mandatory at onboarding, and MSR-22 forbids applying any threshold
    across mixed locales. A script that quietly proceeds with no locales would violate both while
    appearing to work.
    """
    path = Path(project_yml) if project_yml else Path(project_root) / ".kiln" / "project.yml"
    if not path.exists():
        raise KilnError(
            f"{path} not found. The locale set is declared at onboarding (ONB-24) and every row "
            f"must carry a locale before any threshold applies (MSR-22)."
        )
    try:
        import yaml
    except ImportError as exc:  # pragma: no cover - environment problem, not logic
        raise KilnError("PyYAML is required to read .kiln/project.yml") from exc

    doc = yaml.safe_load(path.read_text(encoding="utf-8")) or {}
    raw = doc.get("locales")
    if not raw:
        raise KilnError(f"{path} declares no `locales`. See ONB-24; onboarding cannot be skipped.")

    rules = [
        LocaleRule(
            code=str(item["code"]),
            url_pattern=str(item.get("url_pattern", "/")),
            is_primary=bool(item.get("is_primary", False)),
        )
        for item in raw
    ]
    # Most specific first, so `/en/` is tested before the `/` catch-all.
    return sorted(rules, key=lambda r: (-r.specificity, r.code))


def locale_for_url(url: str, rules: Sequence[LocaleRule]) -> str | None:
    """Map a URL to a declared locale, or None when nothing matches.

    None is deliberately not coerced to the primary locale. An unmapped URL means the declared
    locale set is incomplete, and silently filing those rows under the primary locale would corrupt
    exactly the segmentation MSR-22 exists to protect.
    """
    if not url:
        return None
    host, path = _split_url(url)
    for rule in rules:
        if rule.is_path:
            if path.startswith(rule.url_pattern) or path == rule.url_pattern.rstrip("/"):
                return rule.code
        elif host == rule.url_pattern.casefold() or host.endswith("." + rule.url_pattern.casefold()):
            return rule.code
    return None


def _split_url(url: str) -> tuple[str, str]:
    """Host and path from a URL, tolerating the bare paths a CSV export sometimes carries."""
    m = re.match(r"^[a-z][a-z0-9+.\-]*://([^/?#]*)([^?#]*)", url, re.IGNORECASE)
    if m:
        return m.group(1).casefold(), m.group(2) or "/"
    return "", url if url.startswith("/") else "/" + url


def assign_locales(
    rows: Iterable[dict[str, Any]], rules: Sequence[LocaleRule]
) -> tuple[list[dict[str, Any]], int]:
    """Attach `locale` to every row. Returns the rows and the count that could not be mapped."""
    out: list[dict[str, Any]] = []
    unmapped = 0
    for row in rows:
        code = locale_for_url(row.get("page") or "", rules)
        if code is None:
            unmapped += 1
        row["locale"] = code
        out.append(row)
    return out, unmapped


# ---------------------------------------------------------------------------
# The normalised row
# ---------------------------------------------------------------------------


class NormalRow(dict):
    """Documentation of the output shape. Rows travel as plain dicts for cheap JSONL round-tripping.

    Fields:
      date                  ISO date, or None for a CSV export covering a whole window
      hour                  0-23 when --hourly, else absent
      query                 raw query text; "" means anonymised, which is a value and not a gap
      is_anonymized_query   explicit boolean so downstream never has to re-derive MSR-10
      page                  full URL when the page dimension was requested, else None
      locale                resolved from the URL against project.yml, never from `country`
      device, country       as reported
      clicks, impressions   integers, summed across duplicate keys
      position              **1-based average**, already converted from BigQuery's 0-based sums.
                            Re-aggregating requires weighting by impressions (MSR-12); averaging
                            these values directly gives a one-impression tail query the same weight
                            as a head term.
    """


AGG_KEYS = ("date", "hour", "query", "page", "device", "country")


def aggregate_rows(rows: Iterable[dict[str, Any]]) -> list[dict[str, Any]]:
    """Collapse duplicate keys, then aggregate. MSR-09.

    Applied to every source, not only BigQuery. It is a no-op on already-unique data and it is the
    difference between correct and quietly inflated figures when a source repeats keys, which the
    export does by design and a concatenated CSV does by accident.

    Position is merged impression-weighted (MSR-12): `Σ(pos × imp) / Σ imp`.
    """
    buckets: dict[tuple, dict[str, Any]] = {}
    for row in rows:
        key = tuple(row.get(k) for k in AGG_KEYS)
        acc = buckets.get(key)
        if acc is None:
            acc = {k: row.get(k) for k in AGG_KEYS}
            acc["clicks"] = 0
            acc["impressions"] = 0
            acc["_pos_weighted"] = 0.0
            acc["is_anonymized_query"] = row.get("is_anonymized_query", row.get("query") == "")
            buckets[key] = acc
        imp = int(row.get("impressions") or 0)
        acc["clicks"] += int(row.get("clicks") or 0)
        acc["impressions"] += imp
        pos = row.get("position")
        if pos is not None and imp:
            acc["_pos_weighted"] += float(pos) * imp

    out: list[dict[str, Any]] = []
    for acc in buckets.values():
        imp = acc["impressions"]
        acc["position"] = round(acc.pop("_pos_weighted") / imp, 4) if imp else None
        out.append({k: v for k, v in acc.items() if not (k == "hour" and v is None)})
    return sorted(out, key=lambda r: stable_key(*(r.get(k) for k in AGG_KEYS)))


# ---------------------------------------------------------------------------
# Source: Search Analytics API
# ---------------------------------------------------------------------------


def rows_from_api_response(
    payload: dict[str, Any], dimensions: Sequence[str]
) -> list[dict[str, Any]]:
    """Transform one API response page into normalised rows. Pure; no network.

    `position` from this API is already 1-based and needs no adjustment (§5.0). The adjustment
    belongs to the BigQuery path alone, and applying it here would shift every downstream threshold
    by exactly one in a way that looks entirely plausible.
    """
    out: list[dict[str, Any]] = []
    for entry in payload.get("rows", []):
        keys = entry.get("keys", [])
        if len(keys) != len(dimensions):
            raise KilnError(
                f"API row has {len(keys)} keys for {len(dimensions)} requested dimensions; "
                f"the response does not match the request"
            )
        row: dict[str, Any] = dict(zip(dimensions, keys))
        query = row.get("query")
        out.append(
            {
                "date": row.get("date"),
                "hour": _parse_hour(row.get("hour")),
                "query": query,
                "is_anonymized_query": query == "" if query is not None else False,
                "page": row.get("page"),
                "device": row.get("device"),
                "country": row.get("country"),
                "clicks": int(entry.get("clicks") or 0),
                "impressions": int(entry.get("impressions") or 0),
                "position": entry.get("position"),
            }
        )
    return out


def _parse_hour(value: Any) -> int | None:
    """The hour dimension arrives as an ISO timestamp, not an integer."""
    if value in (None, ""):
        return None
    if isinstance(value, int):
        return value
    m = re.search(r"T(\d{2}):", str(value))
    return int(m.group(1)) if m else None


def fetch_api(
    service: Any,
    property_url: str,
    start: str,
    end: str,
    dimensions: Sequence[str],
    search_type: str,
    data_state: str,
    row_limit: int,
    max_rows: int,
) -> tuple[list[dict[str, Any]], int, bool]:
    """Page through Search Analytics. Returns rows, request count and whether output was truncated.

    `service` is injected so the transform can be exercised against recorded fixtures. Quota is
    counted here rather than inferred from errors: the "quota exceeded" message is identical for
    every quota type and cannot tell you which one you hit (MSR-05).
    """
    rows: list[dict[str, Any]] = []
    start_row = 0
    requests = 0
    truncated = False

    while True:
        body = {
            "startDate": start,
            "endDate": end,
            "dimensions": list(dimensions),
            "type": search_type,
            "dataState": data_state,
            "rowLimit": row_limit,
            "startRow": start_row,
        }
        payload = service.searchanalytics().query(siteUrl=property_url, body=body).execute()
        requests += 1
        page = rows_from_api_response(payload, dimensions)
        rows.extend(page)

        if len(page) < row_limit:
            break
        start_row += row_limit
        if len(rows) >= max_rows:
            truncated = True
            break

    return rows, requests, truncated


def _api_service(credentials_path: Path) -> Any:  # pragma: no cover - requires cloud libraries
    """Build a read-only Search Console client. Imported lazily so the CSV path needs nothing."""
    try:
        from google.oauth2 import service_account
        from googleapiclient.discovery import build
    except ImportError as exc:
        raise KilnError(
            "google-api-python-client and google-auth are required for --source api. "
            "The csv source needs no cloud libraries."
        ) from exc

    if not credentials_path.exists():
        raise KilnError(f"credentials file not found: {credentials_path}")
    creds = service_account.Credentials.from_service_account_file(
        str(credentials_path), scopes=[READONLY_SCOPE]
    )
    return build("searchconsole", "v1", credentials=creds, cache_discovery=False)


# ---------------------------------------------------------------------------
# Source: BigQuery bulk export
# ---------------------------------------------------------------------------


def rows_from_bq_records(
    records: Iterable[dict[str, Any]], table: str = "url"
) -> list[dict[str, Any]]:
    """Transform grouped BigQuery records into normalised rows. Pure; no network.

    `sum_position` and `sum_top_position` are **0-based**, hence the `+ 1`:

        url table:   position = sum_position     / impressions + 1
        site table:  position = sum_top_position / impressions + 1

    The records must already be grouped (MSR-09); the SQL constants in this module do that. Passing
    raw rows here produces plausible, inflated numbers.
    """
    out: list[dict[str, Any]] = []
    for rec in records:
        impressions = int(rec.get("impressions") or 0)
        sum_pos = rec.get("sum_position")
        position = (float(sum_pos) / impressions + 1.0) if (impressions and sum_pos is not None) else None
        query = rec.get("query")
        # MSR-10: the empty string is the anonymisation marker. `is_anonymized_query` is read when
        # present, but the empty string decides, because the boolean column is not guaranteed.
        anonymised = bool(rec.get("is_anonymized_query")) or query == ""
        out.append(
            {
                "date": _iso_date(rec.get("data_date")),
                "hour": rec.get("hour"),
                "query": query,
                "is_anonymized_query": anonymised,
                "page": rec.get("url") if table == "url" else None,
                "device": rec.get("device"),
                "country": rec.get("country"),
                "clicks": int(rec.get("clicks") or 0),
                "impressions": impressions,
                "position": round(position, 4) if position is not None else None,
            }
        )
    return out


def _iso_date(value: Any) -> str | None:
    if value is None:
        return None
    if isinstance(value, (dt.date, dt.datetime)):
        return value.strftime("%Y-%m-%d")
    return str(value)[:10]


def fetch_bigquery(
    client: Any, gcp_project: str, start: str, end: str, table: str
) -> tuple[list[dict[str, Any]], int]:
    """Run the grouped export query. Returns rows and the request count."""
    sql = (BQ_URL_IMPRESSION_SQL if table == "url" else BQ_SITE_IMPRESSION_SQL).format(
        project=gcp_project
    )
    records = _bq_query(client, sql, start, end)
    return rows_from_bq_records(records, table=table), 1


def fetch_epoch_versions(client: Any, gcp_project: str, start: str, end: str) -> dict[str, int]:
    """Read `ExportLog.epoch_version` per date. MSR-11.

    The only programmatic signal that Google recomputed history and that cached aggregates are now
    describing a past that no longer exists.
    """
    sql = BQ_EXPORT_LOG_SQL.format(project=gcp_project)
    return {
        _iso_date(r.get("data_date")) or "": int(r.get("epoch_version") or 0)
        for r in _bq_query(client, sql, start, end)
    }


def probe_is_columns(client: Any, gcp_project: str) -> list[str]:
    """List `is_*` columns on the url table. MSR-16.

    Settles whether `is_ai_overview` exists on this property. The official schema reference does not
    name it while practitioner reports do, and the conservative position is that it is absent until
    this query says otherwise.
    """
    sql = BQ_SCHEMA_PROBE_SQL.format(project=gcp_project)
    return sorted(str(r["column_name"]) for r in _bq_query(client, sql, None, None))


def _bq_query(client: Any, sql: str, start: str | None, end: str | None) -> list[dict[str, Any]]:
    """Execute a parameterised query. `client` is injected so tests use a fake."""
    params = None
    if start and end:
        try:  # pragma: no cover - requires cloud libraries
            from google.cloud import bigquery

            params = [
                bigquery.ScalarQueryParameter("start", "DATE", start),
                bigquery.ScalarQueryParameter("end", "DATE", end),
            ]
        except ImportError:
            params = [("start", start), ("end", end)]
    job = client.query(sql, params) if params is not None else client.query(sql)
    return [dict(row) for row in job]


def _bq_client(credentials_path: Path, gcp_project: str) -> Any:  # pragma: no cover
    """Build a BigQuery client. Imported lazily so the CSV path needs nothing installed."""
    try:
        from google.cloud import bigquery
        from google.oauth2 import service_account
    except ImportError as exc:
        raise KilnError(
            "google-cloud-bigquery and google-auth are required for --source bigquery"
        ) from exc

    if not credentials_path.exists():
        raise KilnError(f"credentials file not found: {credentials_path}")
    creds = service_account.Credentials.from_service_account_file(str(credentials_path))
    raw = bigquery.Client(project=gcp_project, credentials=creds)

    class _Wrapper:
        """Adapts the vendor client to the two-argument shape `_bq_query` expects."""

        def query(self, sql: str, params: Any = None) -> Any:
            cfg = bigquery.QueryJobConfig(query_parameters=params) if params else None
            return raw.query(sql, job_config=cfg).result()

    return _Wrapper()


# ---------------------------------------------------------------------------
# Source: manual CSV export
# ---------------------------------------------------------------------------

# The interface export ships localised headers. Only the shapes we have actually seen are mapped;
# an unrecognised header is reported rather than guessed at, because a silently dropped column here
# becomes a missing metric three scripts downstream.
_CSV_HEADERS: dict[str, str] = {
    "query": "query", "queries": "query", "top queries": "query",
    "запрос": "query", "запит": "query", "поисковый запрос": "query",
    "page": "page", "pages": "page", "top pages": "page", "landing page": "page",
    "страница": "page", "сторінка": "page",
    "date": "date", "дата": "date",
    "country": "country", "страна": "country", "країна": "country",
    "device": "device", "устройство": "device", "пристрій": "device",
    "clicks": "clicks", "клики": "clicks", "кліки": "clicks",
    "impressions": "impressions", "показы": "impressions", "покази": "impressions",
    "ctr": "ctr",
    "position": "position", "average position": "position",
    "позиция": "position", "позиція": "position",
}


def rows_from_csv(
    path: Path | str, default_date: str | None = None
) -> tuple[list[dict[str, Any]], bool]:
    """Read a manual export. Returns rows and whether the file carried a date column.

    A UI export usually summarises a whole window with no date column. In that case rows get
    `date = None` and the manifest records `date_granularity: "window"`, because decay, rising and
    year-over-year detectors are undefined without dates and must refuse to run rather than compute
    something meaningless.

    CTR is read but never stored: it is recomputed downstream from clicks and impressions (MSR-12).
    """
    path = Path(path)
    if not path.exists():
        raise KilnError(f"CSV export not found: {path}")

    text = path.read_text(encoding="utf-8-sig")
    sample = text[:4096]
    try:
        dialect: Any = csv.Sniffer().sniff(sample, delimiters=",;\t")
    except csv.Error:
        dialect = csv.excel

    reader = csv.DictReader(text.splitlines(), dialect=dialect)
    if not reader.fieldnames:
        raise KilnError(f"{path}: no header row")

    mapping = {name: _CSV_HEADERS.get(name.strip().casefold()) for name in reader.fieldnames}
    if not any(v in ("query", "page") for v in mapping.values()):
        raise KilnError(
            f"{path}: no query or page column recognised. Headers seen: {reader.fieldnames}"
        )
    has_date = "date" in mapping.values()

    out: list[dict[str, Any]] = []
    for lineno, raw in enumerate(reader, 2):
        rec = {
            field: (raw.get(name) or "").strip()
            for name, field in mapping.items()
            if field is not None
        }
        query = rec.get("query")
        out.append(
            {
                "date": rec.get("date") or default_date,
                "hour": None,
                "query": query,
                # MSR-10. An export renders the anonymised bucket as an empty cell, so the empty
                # string keeps its meaning here exactly as it does in BigQuery.
                "is_anonymized_query": query == "" if query is not None else False,
                "page": rec.get("page"),
                "device": rec.get("device") or None,
                "country": rec.get("country") or None,
                "clicks": _csv_int(rec.get("clicks"), path, lineno, "clicks"),
                "impressions": _csv_int(rec.get("impressions"), path, lineno, "impressions"),
                "position": _csv_float(rec.get("position"), path, lineno, "position"),
            }
        )
    return out, has_date


def _csv_int(value: str | None, path: Path, lineno: int, field: str) -> int:
    if value in (None, ""):
        return 0
    cleaned = re.sub(r"[\s ,]", "", str(value))
    try:
        return int(float(cleaned))
    except ValueError as exc:
        raise KilnError(f"{path}:{lineno}: {field} is not numeric: {value!r}") from exc


def _csv_float(value: str | None, path: Path, lineno: int, field: str) -> float | None:
    if value in (None, ""):
        return None
    cleaned = re.sub(r"[\s ]", "", str(value)).replace(",", ".")
    try:
        return float(cleaned)
    except ValueError as exc:
        raise KilnError(f"{path}:{lineno}: {field} is not numeric: {value!r}") from exc


# ---------------------------------------------------------------------------
# Window, manifest, output
# ---------------------------------------------------------------------------


def effective_window(start: str, end: str, trim_days: int, today: dt.date) -> tuple[str, str, bool]:
    """Apply MSR-06. Returns the effective window and whether anything was trimmed.

    Trimming is relative to today, not to the requested end: a historical window is already final
    and clipping it would silently discard good data.
    """
    try:
        start_d = dt.date.fromisoformat(start)
        end_d = dt.date.fromisoformat(end)
    except ValueError as exc:
        raise KilnError(f"dates must be YYYY-MM-DD: {exc}") from exc
    if start_d > end_d:
        raise KilnError(f"--start {start} is after --end {end}")

    cutoff = today - dt.timedelta(days=trim_days)
    if end_d <= cutoff:
        return start, end, False
    if start_d > cutoff:
        raise KilnError(
            f"the whole window {start}..{end} sits inside the {trim_days}-day provisional zone "
            f"(MSR-06). Nothing here is final; pull a window ending on or before {cutoff}."
        )
    return start, cutoff.isoformat(), True


def build_manifest(
    *,
    property_url: str,
    source: str,
    pulled_at: str,
    requested: tuple[str, str],
    effective: tuple[str, str],
    trim_days: int,
    trimmed: bool,
    rows: Sequence[dict[str, Any]],
    dimensions: Sequence[str],
    epoch_versions: dict[str, int],
    epoch_changed: list[str],
    truncated: bool,
    quota_used: dict[str, int],
    date_granularity: str,
    unmapped_locale_rows: int,
    schema_probe: list[str] | None,
) -> dict[str, Any]:
    """Assemble `_manifest.json` per §11.1.

    A downstream script must be able to decide from the manifest alone whether the data is usable,
    without re-reading a hundred thousand rows.
    """
    total_impressions = sum(int(r.get("impressions") or 0) for r in rows)
    anon_impressions = sum(
        int(r.get("impressions") or 0) for r in rows if r.get("is_anonymized_query")
    )
    anon_rows = sum(1 for r in rows if r.get("is_anonymized_query"))
    locales_seen: dict[str, int] = defaultdict(int)
    for r in rows:
        locales_seen[str(r.get("locale"))] += 1

    manifest: dict[str, Any] = {
        "property": property_url,
        "source": source,
        "pulled_at": pulled_at,
        "window": {"start": effective[0], "end": effective[1]},
        "requested_window": {"start": requested[0], "end": requested[1]},
        "trimmed_days": trim_days,
        # MSR-06 made explicit: the trailing window was excluded because it is provisional, not
        # because it was empty.
        "provisional_days_excluded": trimmed,
        "dimensions": list(dimensions),
        "date_granularity": date_granularity,
        "row_count": len(rows),
        # MSR-07. Reported on its own line, never folded into another number: the query slice does
        # not reconcile with the property total, and the gap reaches tens of percent on the tail.
        "anonymized_share": round(anon_impressions / total_impressions, 4) if total_impressions else 0.0,
        "anonymized_rows": anon_rows,
        "total_impressions": total_impressions,
        "truncated": truncated,
        "epoch_versions": dict(sorted(epoch_versions.items())),
        "epoch_version_changed": sorted(epoch_changed),
        "quota_used": quota_used,
        "locales_seen": dict(sorted(locales_seen.items())),
        "unmapped_locale_rows": unmapped_locale_rows,
        "usable": not truncated and unmapped_locale_rows == 0 and not epoch_changed,
    }
    if schema_probe is not None:
        manifest["schema_probe"] = {"searchdata_url_impression_is_columns": schema_probe}
    return manifest


def property_slug(property_url: str) -> str:
    """Filesystem-safe directory name.

    `sc-domain:example.com` contains a colon, which is not a legal path character on Windows, and
    the pilot runs on Windows.
    """
    return re.sub(r"[^A-Za-z0-9._-]+", "_", property_url).strip("_")


def write_output(
    out_dir: Path, rows: Sequence[dict[str, Any]], manifest: dict[str, Any], dry_run: bool
) -> dict[str, int]:
    """Write per-date JSONL plus the manifest, replacing the pulled range wholesale.

    Idempotency is delete-by-date-range then insert, per §11.1. Row-level upsert would leave rows
    behind that Google has since removed, and a stale row is indistinguishable from a real one.
    """
    by_date: dict[str, list[dict[str, Any]]] = defaultdict(list)
    for row in rows:
        by_date[str(row.get("date") or "undated")].append(row)

    if dry_run:
        return {d: len(v) for d, v in sorted(by_date.items())}

    out_dir.mkdir(parents=True, exist_ok=True)
    start, end = manifest["window"]["start"], manifest["window"]["end"]
    for existing in out_dir.glob("*.jsonl"):
        stem = existing.stem
        if stem == "undated" or start <= stem <= end:
            existing.unlink()

    written: dict[str, int] = {}
    for date, group in sorted(by_date.items()):
        written[date] = write_jsonl(out_dir / f"{date}.jsonl", group)
    write_json(out_dir / "_manifest.json", manifest)
    return written


def read_previous_epochs(out_dir: Path) -> dict[str, int]:
    """Epoch versions from the last manifest, for detecting a rewrite of history."""
    path = out_dir / "_manifest.json"
    if not path.exists():
        return {}
    try:
        return dict(json.loads(path.read_text(encoding="utf-8")).get("epoch_versions", {}))
    except json.JSONDecodeError as exc:
        raise KilnError(f"{path} is not valid JSON: {exc}") from exc


# ---------------------------------------------------------------------------
# CLI
# ---------------------------------------------------------------------------


def _parser():
    p = base_parser(__doc__.splitlines()[0])
    p.add_argument("--property", required=True,
                   help="sc-domain:example.com or https://example.com/")
    p.add_argument("--start", required=True, help="YYYY-MM-DD")
    p.add_argument("--end", required=True, help="YYYY-MM-DD")
    p.add_argument("--source", choices=("api", "bigquery", "csv"), default="api")
    p.add_argument("--credentials", type=Path, default=None,
                   help="path to the service account JSON; the path is not itself a secret")
    p.add_argument("--gcp-project", default=None, help="GCP project holding the searchconsole dataset")
    p.add_argument("--bq-table", choices=("url", "site"), default="url",
                   help="url is the working table; site cannot detect cannibalization")
    p.add_argument("--csv-file", type=Path, default=None, help="manual export for --source csv")
    p.add_argument("--dimensions", default=",".join(DEFAULT_DIMENSIONS))
    p.add_argument("--type", dest="search_type", default="web")
    p.add_argument("--hourly", action="store_true", help="dataState=hourly_all; lives 8 days")
    p.add_argument("--trim-days", type=int, default=None, help="override MSR-06 trimming")
    p.add_argument("--max-rows", type=int, default=None)
    p.add_argument("--check-schema", action="store_true",
                   help="probe is_* columns on the url table (MSR-16)")
    p.add_argument("--dry-run", action="store_true")
    p.add_argument("--pulled-at", default=None,
                   help="freeze the manifest timestamp; required for byte-identical test output")
    p.add_argument("--today", default=None, help="override today's date for trimming")
    p.add_argument("--project-yml", type=Path, default=None)
    return p


def main(args) -> int:
    from kiln_common import load_thresholds

    th = load_thresholds(args.project_root, DOCTRINE_DEFAULTS, args.thresholds)
    trim_days = args.trim_days if args.trim_days is not None else int(th.get("measurement.trim_days"))
    row_limit = int(th.get("measurement.api_row_limit"))
    max_rows = args.max_rows or int(th.get("measurement.api_max_rows"))

    today = dt.date.fromisoformat(args.today) if args.today else dt.datetime.now(dt.UTC).date()
    pulled_at = args.pulled_at or dt.datetime.now(dt.UTC).strftime("%Y-%m-%dT%H:%M:%SZ")

    dimensions = tuple(d.strip() for d in args.dimensions.split(",") if d.strip())
    if args.hourly and "hour" not in dimensions:
        dimensions = dimensions + ("hour",)
    if args.hourly and (today - dt.date.fromisoformat(args.start)).days > HOURLY_RETENTION_DAYS:
        raise KilnError(
            f"hourly data lives {HOURLY_RETENTION_DAYS} days and then disappears permanently. "
            f"--start {args.start} is already outside it; archive daily instead of on demand."
        )

    start, end, trimmed = effective_window(args.start, args.end, trim_days, today)
    out_dir = Path(args.project_root) / ".kiln" / "measurements" / "raw" / property_slug(args.property)

    quota = {"search_analytics_queries": 0, "url_inspection": 0, "bigquery_jobs": 0}
    epoch_versions: dict[str, int] = {}
    epoch_changed: list[str] = []
    schema_probe: list[str] | None = None
    truncated = False
    date_granularity = "hour" if args.hourly else "date"

    if args.source == "csv":
        if not args.csv_file:
            raise KilnError("--source csv requires --csv-file")
        raw_rows, has_date = rows_from_csv(args.csv_file, default_date=None)
        if not has_date:
            # Honest, and load-bearing: decay, rising and year-over-year detectors are undefined
            # without dates, and must refuse rather than compute something meaningless.
            date_granularity = "window"

    elif args.source == "api":
        creds = args.credentials or _credentials_from_env()
        service = _api_service(Path(creds))
        raw_rows, requests, truncated = fetch_api(
            service, args.property, start, end, dimensions, args.search_type,
            "hourly_all" if args.hourly else "final", row_limit, max_rows,
        )
        quota["search_analytics_queries"] = requests

    else:
        if not args.gcp_project:
            raise KilnError("--source bigquery requires --gcp-project")
        creds = args.credentials or _credentials_from_env()
        client = _bq_client(Path(creds), args.gcp_project)
        raw_rows, jobs = fetch_bigquery(client, args.gcp_project, start, end, args.bq_table)
        epoch_versions = fetch_epoch_versions(client, args.gcp_project, start, end)
        quota["bigquery_jobs"] = jobs + 1
        if args.check_schema:
            schema_probe = probe_is_columns(client, args.gcp_project)
            quota["bigquery_jobs"] += 1
        previous = read_previous_epochs(out_dir)
        epoch_changed = [d for d, v in epoch_versions.items() if v > previous.get(d, v)]

    rows = aggregate_rows(raw_rows)
    rows, unmapped = assign_locales(rows, load_locales(args.project_root, args.project_yml))

    manifest = build_manifest(
        property_url=args.property, source=args.source, pulled_at=pulled_at,
        requested=(args.start, args.end), effective=(start, end),
        trim_days=trim_days, trimmed=trimmed, rows=rows, dimensions=dimensions,
        epoch_versions=epoch_versions, epoch_changed=epoch_changed, truncated=truncated,
        quota_used=quota, date_granularity=date_granularity,
        unmapped_locale_rows=unmapped, schema_probe=schema_probe,
    )
    written = write_output(out_dir, rows, manifest, args.dry_run)

    if args.out:
        write_json(args.out, {"manifest": manifest, "files": written})
    else:
        print(dumps({"manifest": manifest, "files": written}))

    if unmapped:
        print(
            f"warning: {unmapped} rows matched no declared locale. MSR-22 forbids applying "
            f"thresholds across mixed locales; extend project.yml:locales.",
            file=sys.stderr,
        )
    if epoch_changed:
        # MSR-11. The pull itself is fine; what is not fine is every aggregate computed before it.
        print(
            f"epoch_version incremented for {', '.join(epoch_changed)}: Google recomputed history. "
            f"Conclusions drawn on the previous version require re-verification. "
            f"Silent recomputation is forbidden.",
            file=sys.stderr,
        )
        return EXIT_SCRIPT_SPECIFIC
    return EXIT_OK


def _credentials_from_env() -> str:
    """Credentials arrive through the environment, never on the command line."""
    for var in ("CLAUDE_PLUGIN_OPTION_GSC_CREDENTIALS", "GOOGLE_APPLICATION_CREDENTIALS"):
        value = os.environ.get(var)
        if value:
            return value
    raise KilnError(
        "no credentials. Pass --credentials <path> or set CLAUDE_PLUGIN_OPTION_GSC_CREDENTIALS."
    )


if __name__ == "__main__":
    run(main, _parser())
