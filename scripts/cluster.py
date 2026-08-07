#!/usr/bin/env python3
"""Centroid clustering over the query edge graph.

Specification: `doctrine/02-semantics.md` §3 (algorithm), §4 (storage), §13.3 (contract).

This script reads an edge graph and writes a cluster run. It makes no network calls and fetches
no SERPs. That is the point of the edge graph: re-clustering at a different threshold, or after
adding two thousand queries, costs nothing but CPU, and any heuristic aimed at saving SERP calls
would be optimising the wrong side of a $0.0006 line item.

Four doctrinal constraints shape everything below.

**SEM-11: centroid, not graph.** Connected components produce chaining drift, where A links to B,
B links to C, A and C share nothing, and all three land in one cluster. Every member here is
compared against the head, never against a neighbour, so the drift cannot form. The cost is that
the result depends on traversal order, which is why the order is fixed and total.

**SEM-09: SERP overlap decides.** `embed_sim` is carried into the output for reporting and is
never consulted when deciding membership. Embeddings cannot see that «ягуар тварина» and
«ягуар авто» are different intents; the SERP can.

**SEM-10: the threshold is a project parameter.** Over-merging is the dominant failure of every
tool in this class, and it is worse in tools with a fixed threshold. The default lives here; the
operative value lives in `.kiln/thresholds.yml`.

**SEM-18: one locale per run.** The uniqueness key of a query is (text_norm, geo, device, lang).
Clusters never span locales, because a cluster built across two markets describes neither.

One deliberate deviation from the example in §13.3, flagged rather than hidden: `run_id` there is
a wall-clock timestamp. A timestamp makes the output differ on every run, which destroys the
byte-identical guarantee the README requires and, with it, the ability to tell a SERP change from
an implementation change. `run_id` is therefore derived from a hash of the inputs and parameters
unless one is supplied explicitly.
"""

from __future__ import annotations

import argparse
import hashlib
import sys
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Iterable, Sequence

sys.path.insert(0, str(Path(__file__).resolve().parent))

from kiln_common import (  # noqa: E402
    EXIT_OK,
    Finding,
    KilnError,
    Thresholds,
    base_parser,
    dumps,
    emit,
    load_thresholds,
    read_jsonl,
    run,
    sort_findings,
    write_json,
)

# ---------------------------------------------------------------------------
# Doctrine defaults
# ---------------------------------------------------------------------------
# Starting values only. §14.1 resolves the apparent tension with P10: the doctrine supplies a
# default and the obligation to calibrate it; `.kiln/thresholds.yml` overrides it; promoting a
# calibrated value back into the doctrine requires its own PR.

DOCTRINE_DEFAULTS: dict[str, Any] = {
    # §3.2: 3 is loose, 4 is the working default, 5+ for competitive niches.
    "semantics.cluster.overlap_threshold": 4,
    # §3.2: comparing against the top 7 instead of the top 10 tightens the criterion without
    # touching the numeric threshold.
    "semantics.cluster.serp_depth": 10,
    # SEM-13: query drift between active runs above this share raises an alert.
    "semantics.cluster.drift_alert_ratio": 0.10,
    # SEM-23: automatic merging above this size requires human confirmation.
    "semantics.cluster.manual_confirm_size": 20,
}

METHOD = "centroid"

# Cognitive intent values, normalised. The doctrine (§5.1) names three; `intent.py` is not written
# yet, so both the long and short spellings are accepted rather than failing on a suffix.
_INTENT_SUFFIX = "-seeking"


# ---------------------------------------------------------------------------
# Input records
# ---------------------------------------------------------------------------


@dataclass(frozen=True, slots=True)
class Query:
    """One row of `queries.norm.jsonl`, plus whatever priority and intent were joined in."""

    id: str
    text: str
    text_norm: str
    lang: str
    geo: str
    device: str
    is_verified: bool
    volume: float | None = None
    priority: float | None = None
    intent_commercial: str | None = None
    intent_cognitive: str | None = None

    @property
    def scope_key(self) -> str:
        """The clustering scope: lang, geo and device together.

        Device belongs here and is easy to forget. Mobile and desktop SERPs differ, so a cluster
        mixing them is built on two different rankings and means nothing on either.
        """
        return f"{self.lang}-{self.geo}-{self.device}"

    @property
    def sort_priority(self) -> float:
        """Missing priority sorts last rather than arbitrarily.

        A query whose expected yield was never computed must not become a cluster head ahead of one
        whose yield is known and high: the head decides which page gets written.
        """
        return float(self.priority) if self.priority is not None else 0.0

    @property
    def sort_volume(self) -> float:
        return float(self.volume) if self.volume is not None else 0.0


@dataclass(slots=True)
class Member:
    query_id: str
    is_head: bool
    membership_score: float
    serp_overlap: int | None
    embed_sim: float | None = None

    def as_record(self) -> dict[str, Any]:
        rec: dict[str, Any] = {
            "query_id": self.query_id,
            "is_head": self.is_head,
            "membership_score": self.membership_score,
        }
        # Reported, never consulted. Present so a human can see why the overlap landed where it did.
        if self.serp_overlap is not None:
            rec["serp_overlap"] = self.serp_overlap
        if self.embed_sim is not None:
            rec["embed_sim"] = self.embed_sim
        return rec


@dataclass(slots=True)
class Cluster:
    id: str
    head_query_id: str
    label: str
    members: list[Member]
    intent_commercial: str | None = None
    intent_cognitive: str | None = None
    pillar_id: str | None = None
    pillar_source: str | None = None
    needs_human_confirmation: bool = False

    @property
    def size(self) -> int:
        return len(self.members)

    @property
    def member_ids(self) -> list[str]:
        return [m.query_id for m in self.members]

    def as_record(self) -> dict[str, Any]:
        return {
            "id": self.id,
            "head_query_id": self.head_query_id,
            "label": self.label,
            "size": self.size,
            "intent_commercial": self.intent_commercial,
            "intent_cognitive": self.intent_cognitive,
            "pillar_id": self.pillar_id,
            "pillar_source": self.pillar_source,
            # A flag rather than a warning message. SEM-23 requires human confirmation for large
            # automatic merges; downstream honours a field in the data, not a line of prose it has
            # to parse out of a findings list.
            "needs_human_confirmation": self.needs_human_confirmation,
            "members": [m.as_record() for m in self.members],
        }


# ---------------------------------------------------------------------------
# Loading
# ---------------------------------------------------------------------------


def _require(rec: dict[str, Any], field_name: str, path: Path, lineno: int | None = None) -> Any:
    if field_name not in rec or rec[field_name] in (None, ""):
        where = f"{path}" if lineno is None else f"{path}:{lineno}"
        raise KilnError(f"{where}: record is missing required field {field_name!r}: {rec!r}")
    return rec[field_name]


def load_queries(
    queries_path: Path,
    priorities_path: Path | None = None,
    intents_path: Path | None = None,
) -> list[Query]:
    """Load the normalised core, joining priority and intent where available.

    Intent is not in the §13.3 input list, but §3.2 defines two over-merging indicators in terms of
    it and §4.1 puts `intent_commercial` and `intent_cognitive` on the cluster. It is accepted from
    the query records themselves (the `queries` table in §4.1 carries the columns) or from a
    separate `intents.jsonl` produced by `intent.py`, whichever is present.
    """
    priorities: dict[str, float] = {}
    if priorities_path is not None:
        for rec in read_jsonl(priorities_path):
            qid = _require(rec, "query_id", priorities_path)
            if "priority" in rec and rec["priority"] is not None:
                priorities[str(qid)] = float(rec["priority"])

    intents: dict[str, tuple[str | None, str | None]] = {}
    if intents_path is not None:
        for rec in read_jsonl(intents_path):
            qid = str(_require(rec, "query_id", intents_path))
            intents[qid] = (
                _norm_intent(rec.get("intent_commercial")),
                _norm_intent(rec.get("intent_cognitive")),
            )

    out: list[Query] = []
    seen: set[str] = set()
    for lineno, rec in enumerate(read_jsonl(queries_path), 1):
        qid = str(_require(rec, "id", queries_path, lineno))
        if qid in seen:
            raise KilnError(f"{queries_path}:{lineno}: duplicate query id {qid!r}")
        seen.add(qid)
        joined_commercial, joined_cognitive = intents.get(qid, (None, None))
        out.append(
            Query(
                id=qid,
                text=str(rec.get("text", rec.get("text_norm", ""))),
                text_norm=str(_require(rec, "text_norm", queries_path, lineno)),
                lang=str(_require(rec, "lang", queries_path, lineno)),
                geo=str(_require(rec, "geo", queries_path, lineno)),
                device=str(rec.get("device", "desktop")),
                # SEM-07 defaults to the safe reading: absent means unverified, not verified.
                is_verified=bool(rec.get("is_verified", False)),
                volume=rec.get("volume"),
                priority=priorities.get(qid, rec.get("priority")),
                intent_commercial=joined_commercial or _norm_intent(rec.get("intent_commercial")),
                intent_cognitive=joined_cognitive or _norm_intent(rec.get("intent_cognitive")),
            )
        )
    if not out:
        raise KilnError(f"{queries_path}: no query records found")
    return out


def _norm_intent(value: Any) -> str | None:
    """Normalise an intent label so `knowledge` and `knowledge-seeking` compare equal."""
    if value in (None, ""):
        return None
    text = str(value).strip().casefold()
    if text.endswith(_INTENT_SUFFIX):
        text = text[: -len(_INTENT_SUFFIX)]
    return text or None


def load_edges(edges_path: Path) -> tuple[dict[str, dict[str, int]], dict[str, dict[str, float]], int]:
    """Load the edge graph into adjacency form.

    Returns (overlap, embed_sim, edge_count). Edges are stored once with `a < b`; both directions
    are materialised here because the clustering asks "what does this head reach", which is
    symmetric.
    """
    overlap: dict[str, dict[str, int]] = {}
    embed: dict[str, dict[str, float]] = {}
    count = 0
    for lineno, rec in enumerate(read_jsonl(edges_path), 1):
        a = str(_require(rec, "a", edges_path, lineno))
        b = str(_require(rec, "b", edges_path, lineno))
        if a == b:
            raise KilnError(f"{edges_path}:{lineno}: self-edge on {a!r}")
        if "serp_overlap" not in rec:
            raise KilnError(f"{edges_path}:{lineno}: edge is missing 'serp_overlap'")
        ov = int(rec["serp_overlap"])
        overlap.setdefault(a, {})[b] = ov
        overlap.setdefault(b, {})[a] = ov
        sim = rec.get("embed_sim")
        if sim is not None:
            embed.setdefault(a, {})[b] = float(sim)
            embed.setdefault(b, {})[a] = float(sim)
        count += 1
    return overlap, embed, count


def load_pillars(pillars_path: Path | None) -> dict[str, tuple[str | None, str | None]]:
    """Optional map of query id to (pillar_id, pillar_source).

    A cluster inherits the pillar of its head. Neither `declared` nor `inferred` groupings are
    derivable from this script's inputs, so absence means "not established" and is written as null
    on both fields. §9.3 is explicit that this is not the same as certified independence.
    """
    if pillars_path is None:
        return {}
    out: dict[str, tuple[str | None, str | None]] = {}
    for rec in read_jsonl(pillars_path):
        qid = str(_require(rec, "query_id", pillars_path))
        source = rec.get("pillar_source")
        if source not in (None, "declared", "inferred"):
            raise KilnError(
                f"{pillars_path}: pillar_source must be 'declared' or 'inferred', got {source!r}"
            )
        out[qid] = (rec.get("pillar_id"), source)
    return out


# ---------------------------------------------------------------------------
# Locale scoping (SEM-18)
# ---------------------------------------------------------------------------


def scope_queries(queries: Sequence[Query], locale: str | None) -> tuple[list[Query], int, str]:
    """Restrict the run to a single locale, returning (kept, excluded_count, scope_key).

    Two behaviours on purpose. Without `--locale` a mixed file is rejected outright, because
    silently clustering whichever locale happened to appear first would produce a plausible,
    wrong core. With `--locale` the file is filtered and the number of excluded records is
    reported, so the drop is visible in the output rather than invisible in the code.
    """
    scopes = sorted({q.scope_key for q in queries})
    if locale is None:
        if len(scopes) > 1:
            raise KilnError(
                "SEM-18: input mixes locales "
                + ", ".join(scopes)
                + ". Clusters never span locales. Pass --locale <lang-geo-device> to select one."
            )
        return list(queries), 0, scopes[0]

    kept = [q for q in queries if q.scope_key == locale]
    if not kept:
        raise KilnError(
            f"--locale {locale!r} matches no records. Locales present: " + ", ".join(scopes)
        )
    return kept, len(queries) - len(kept), locale


# ---------------------------------------------------------------------------
# The algorithm (pure)
# ---------------------------------------------------------------------------


def sort_queries(queries: Iterable[Query]) -> list[Query]:
    """SEM-11 ordering: expected yield, then volume, then text, then id.

    Descending on yield and volume, ascending on text. The `text_norm` tiebreak is what the
    doctrine requires and the reason is worth restating: without a total order, two runs over
    identical data can differ, and then there is no way to tell SERP drift from implementation
    drift. `id` is appended as a final tiebreak; within a locale `text_norm` is unique by the
    model's uniqueness key, so it never fires on well-formed input and costs nothing when the
    input is not well formed.
    """
    return sorted(
        queries,
        key=lambda q: (-q.sort_priority, -q.sort_volume, q.text_norm, q.id),
    )


def cluster_queries(
    queries: Sequence[Query],
    overlap: dict[str, dict[str, int]],
    embed: dict[str, dict[str, float]],
    threshold: int,
    serp_depth: int,
) -> list[Cluster]:
    """Centroid clustering. Pure: no IO, no clock, no randomness.

    Take the highest-ranked unassigned query as the head, attach everything that clears the
    threshold **against the head**, repeat on the remainder. Comparison is always head-to-candidate
    and never candidate-to-candidate, which is precisely what stops A and C joining through B.
    """
    ordered = sort_queries(queries)
    order_index = {q.id: i for i, q in enumerate(ordered)}
    by_id = {q.id: q for q in ordered}

    assigned: set[str] = set()
    clusters: list[Cluster] = []

    for head in ordered:
        if head.id in assigned:
            continue
        assigned.add(head.id)

        members = [Member(query_id=head.id, is_head=True, membership_score=1.0, serp_overlap=None)]

        # Walk the head's neighbours in the same global order the heads were chosen in. Iterating
        # the adjacency rather than the whole core keeps this linear in the head's degree, and
        # sorting by the global index keeps it deterministic.
        neighbours = overlap.get(head.id, {})
        for cand_id in sorted(neighbours, key=lambda i: (order_index.get(i, len(ordered)), i)):
            if cand_id in assigned or cand_id not in by_id:
                continue
            ov = neighbours[cand_id]
            # SEM-09: this comparison, and only this comparison, decides membership.
            if ov < threshold:
                continue
            assigned.add(cand_id)
            members.append(
                Member(
                    query_id=cand_id,
                    is_head=False,
                    membership_score=_membership_score(ov, serp_depth),
                    serp_overlap=ov,
                    embed_sim=embed.get(head.id, {}).get(cand_id),
                )
            )

        members.sort(key=lambda m: (not m.is_head, -m.membership_score, m.query_id))
        clusters.append(
            Cluster(
                id="",  # assigned below, once the count is known
                head_query_id=head.id,
                label=head.text or head.text_norm,
                members=members,
                # The head determines which page gets written, so the head's intent is the
                # cluster's intent. Disagreement among members is an over-merging signal, not a
                # reason to average.
                intent_commercial=head.intent_commercial,
                intent_cognitive=head.intent_cognitive,
            )
        )

    width = max(3, len(str(len(clusters))))
    for i, c in enumerate(clusters, 1):
        c.id = f"c-{i:0{width}d}"
    return clusters


def _membership_score(overlap: int, serp_depth: int) -> float:
    """§13.3: membership_score = serp_overlap / serp_depth.

    Rounded to four places so the JSON is stable across platforms, and clamped because an overlap
    exceeding the depth means the edge and the depth disagree, which should not silently produce a
    score above 1.
    """
    if serp_depth <= 0:
        raise KilnError(f"serp_depth must be positive, got {serp_depth}")
    return round(min(overlap / serp_depth, 1.0), 4)


# ---------------------------------------------------------------------------
# Over-merging indicators (§3.2)
# ---------------------------------------------------------------------------
# Of the four indicators the doctrine lists, two are computable from this script's inputs. The
# other two are not, and pretending otherwise would be worse than omitting them: "the head does not
# answer most of the cluster's queries" needs a human reading, and "the page picks up impressions
# for half the cluster" needs GSC data 4 to 8 weeks after publication. Both belong to
# `08-measurement.md`.


def detect_over_merging(
    clusters: Sequence[Cluster],
    by_id: dict[str, Query],
    locale: str,
    threshold_records: list[dict[str, Any]],
) -> list[Finding]:
    findings: list[Finding] = []
    for c in clusters:
        commercial = {
            by_id[m.query_id].intent_commercial
            for m in c.members
            if by_id[m.query_id].intent_commercial
        }
        cognitive = {
            by_id[m.query_id].intent_cognitive
            for m in c.members
            if by_id[m.query_id].intent_cognitive
        }

        # §3.2, first indicator: informational and transactional in one cluster.
        if {"informational", "transactional"} <= commercial:
            findings.append(
                Finding(
                    rule_id="SEM-10",
                    severity="WARN",
                    subject=c.id,
                    message=(
                        "over-merging indicator: the cluster mixes informational and transactional "
                        "intent. Grounds for raising the overlap threshold."
                    ),
                    evidence={
                        "label": c.label,
                        "size": c.size,
                        "commercial_intents": sorted(commercial),
                    },
                    thresholds_used=threshold_records,
                    locale=locale,
                )
            )

        # §3.2, fourth indicator: knowledge and output-seeking together.
        if {"knowledge", "output"} <= cognitive:
            findings.append(
                Finding(
                    rule_id="SEM-10",
                    severity="WARN",
                    subject=c.id,
                    message=(
                        "over-merging indicator: the cluster spans the knowledge and output-seeking "
                        "cognitive axes. Grounds for raising the overlap threshold."
                    ),
                    evidence={
                        "label": c.label,
                        "size": c.size,
                        "cognitive_intents": sorted(cognitive),
                    },
                    thresholds_used=threshold_records,
                    locale=locale,
                )
            )
    return findings


def flag_large_clusters(
    clusters: Sequence[Cluster],
    limit: int,
    locale: str,
    threshold_records: list[dict[str, Any]],
) -> list[Finding]:
    """SEM-23: an automatic merge above the size limit needs human confirmation.

    Sets the flag on the cluster as well as emitting the finding. The cost of an over-merging error
    grows with cluster size, and on a large corpus the clusters are large.
    """
    findings: list[Finding] = []
    for c in clusters:
        if c.size > limit:
            c.needs_human_confirmation = True
            findings.append(
                Finding(
                    rule_id="SEM-23",
                    severity="WARN",
                    subject=c.id,
                    message=(
                        f"cluster of {c.size} queries exceeds the automatic-merge limit of {limit} "
                        f"and requires human confirmation before the run is activated."
                    ),
                    evidence={"label": c.label, "size": c.size, "head_query_id": c.head_query_id},
                    thresholds_used=threshold_records,
                    locale=locale,
                )
            )
    return findings


def report_pillar_groups(clusters: Sequence[Cluster], locale: str) -> list[Finding]:
    """SEM-25: clusters sharing a pillar are not independent.

    This script does not assign measurement arms or linking waves, so it cannot violate SEM-25. It
    can make the constraint visible to whatever does, which is the whole reason `pillar_id` is on
    the cluster.
    """
    groups: dict[str, list[str]] = {}
    for c in clusters:
        if c.pillar_id:
            groups.setdefault(str(c.pillar_id), []).append(c.id)
    findings: list[Finding] = []
    for pillar_id in sorted(groups):
        ids = sorted(groups[pillar_id])
        if len(ids) < 2:
            continue
        findings.append(
            Finding(
                rule_id="SEM-25",
                severity="INFO",
                subject=pillar_id,
                message=(
                    f"{len(ids)} clusters share pillar {pillar_id!r} and are not statistically "
                    f"independent. They must not be split across arms of one comparison or across "
                    f"concurrently measured linking waves."
                ),
                evidence={"cluster_ids": ids},
                locale=locale,
            )
        )
    return findings


# ---------------------------------------------------------------------------
# Drift between runs (SEM-13)
# ---------------------------------------------------------------------------


def _mate_map(run: dict[str, Any]) -> dict[str, frozenset[str]]:
    """query id -> the set of its cluster-mates, excluding itself.

    Membership is compared through cluster-mates rather than through cluster ids because ids are
    positional and heads change. If a new high-yield query arrives and becomes the head of an
    otherwise untouched cluster, nothing about that cluster's membership has drifted, and a
    head-based or id-based comparison would report that it had.
    """
    out: dict[str, frozenset[str]] = {}
    for c in run.get("clusters", []):
        ids = [str(m["query_id"]) for m in c.get("members", [])]
        members = set(ids)
        for qid in ids:
            out[qid] = frozenset(members - {qid})
    return out


def _cluster_of(run: dict[str, Any]) -> dict[str, str]:
    return {
        str(m["query_id"]): str(c["id"])
        for c in run.get("clusters", [])
        for m in c.get("members", [])
    }


def diff_runs(
    prev: dict[str, Any],
    curr: dict[str, Any],
    alert_ratio: float,
    locale: str,
    threshold_records: list[dict[str, Any]],
) -> tuple[dict[str, Any], list[Finding]]:
    """Compare two cluster runs. Pure.

    Reports the queries whose membership changed, the clusters that split or merged, and the drift
    ratio per cluster against SEM-13. Queries added or removed between runs are reported separately
    and excluded from the ratio: a query that did not exist last time has not drifted.
    """
    prev_mates, curr_mates = _mate_map(prev), _mate_map(curr)
    prev_cluster, curr_cluster = _cluster_of(prev), _cluster_of(curr)

    prev_ids, curr_ids = set(prev_mates), set(curr_mates)
    common = prev_ids & curr_ids

    changed: list[dict[str, Any]] = []
    for qid in sorted(common):
        before = prev_mates[qid] & common
        after = curr_mates[qid] & common
        if before != after:
            changed.append(
                {
                    "query_id": qid,
                    "prev_cluster_id": prev_cluster.get(qid),
                    "curr_cluster_id": curr_cluster.get(qid),
                    "left": sorted(before - after),
                    "joined": sorted(after - before),
                }
            )

    changed_ids = {c["query_id"] for c in changed}

    # Per-cluster drift, computed on the previous run's clusters: the question SEM-13 asks is how
    # much a cluster we already had has moved.
    per_cluster: list[dict[str, Any]] = []
    findings: list[Finding] = []
    for c in prev.get("clusters", []):
        cid = str(c["id"])
        members = [str(m["query_id"]) for m in c.get("members", [])]
        comparable = [q for q in members if q in common]
        if not comparable:
            continue
        moved = [q for q in comparable if q in changed_ids]
        ratio = round(len(moved) / len(comparable), 4)
        landed = sorted({curr_cluster[q] for q in comparable if q in curr_cluster})
        entry = {
            "prev_cluster_id": cid,
            "label": c.get("label"),
            "comparable_queries": len(comparable),
            "moved_queries": len(moved),
            "drift_ratio": ratio,
            "landed_in": landed,
        }
        per_cluster.append(entry)
        if ratio > alert_ratio:
            findings.append(
                Finding(
                    rule_id="SEM-13",
                    severity="WARN",
                    subject=cid,
                    message=(
                        f"{ratio:.0%} of this cluster's queries changed membership between runs, "
                        f"above the alert threshold of {alert_ratio:.0%}. This is an early signal "
                        f"that the SERP has moved; it arrives before rankings drop."
                    ),
                    evidence=entry,
                    thresholds_used=threshold_records,
                    locale=locale,
                )
            )

    splits = [
        {"prev_cluster_id": e["prev_cluster_id"], "landed_in": e["landed_in"]}
        for e in per_cluster
        if len(e["landed_in"]) > 1
    ]

    origins: dict[str, set[str]] = {}
    for qid in sorted(common):
        origins.setdefault(curr_cluster[qid], set()).add(prev_cluster[qid])
    merges = [
        {"curr_cluster_id": cid, "came_from": sorted(origins[cid])}
        for cid in sorted(origins)
        if len(origins[cid]) > 1
    ]

    overall = round(len(changed_ids) / len(common), 4) if common else 0.0

    drift = {
        "prev_run_id": prev.get("run_id"),
        "curr_run_id": curr.get("run_id"),
        "locale": locale,
        "summary": {
            "queries_compared": len(common),
            "queries_changed": len(changed_ids),
            "overall_drift_ratio": overall,
            "queries_added": len(curr_ids - prev_ids),
            "queries_removed": len(prev_ids - curr_ids),
            "clusters_split": len(splits),
            "clusters_merged": len(merges),
        },
        "changed": changed,
        "added": sorted(curr_ids - prev_ids),
        "removed": sorted(prev_ids - curr_ids),
        "splits": splits,
        "merges": merges,
        "per_cluster": per_cluster,
    }
    return drift, findings


# ---------------------------------------------------------------------------
# Assembly
# ---------------------------------------------------------------------------


def _resolve(
    th: Thresholds, key: str, cli_value: Any, fallback: Any
) -> tuple[Any, dict[str, Any]]:
    """Resolve one parameter, recording where the value came from.

    An explicit command-line value wins over the calibrated file, which wins over the doctrine
    default. The provenance travels into the output because a finding produced under a doctrine
    guess and one produced under a calibrated number are not comparable.
    """
    if cli_value is not None:
        return cli_value, {"key": key, "value": cli_value, "source": "cli"}
    value = th.get(key, fallback)
    record = next(r for r in th.used() if r["key"] == key)
    return value, record


def _run_id(params: dict[str, Any], queries: Sequence[Query], overlap: dict[str, dict[str, int]]) -> str:
    """Content-derived run identifier.

    A wall-clock id would make two runs over identical data differ, which is exactly the difference
    the medium learning loop is trying to read. Hashing the inputs means an unchanged core and an
    unchanged graph produce the same id, and any change to either produces a new one.
    """
    h = hashlib.sha256()
    h.update(dumps(params, indent=None).encode("utf-8"))
    for q in sorted(queries, key=lambda x: x.id):
        h.update(f"\x1f{q.id}\x1f{q.text_norm}\x1f{q.is_verified}".encode("utf-8"))
    for a in sorted(overlap):
        for b in sorted(overlap[a]):
            h.update(f"\x1e{a}\x1e{b}\x1e{overlap[a][b]}".encode("utf-8"))
    return f"run-{h.hexdigest()[:12]}"


def build_run(args: argparse.Namespace) -> tuple[dict[str, Any], dict[str, Any] | None]:
    th = load_thresholds(args.project_root, DOCTRINE_DEFAULTS, args.thresholds)

    threshold, th_rec = _resolve(
        th, "semantics.cluster.overlap_threshold", args.threshold, DOCTRINE_DEFAULTS["semantics.cluster.overlap_threshold"]
    )
    serp_depth, depth_rec = _resolve(
        th, "semantics.cluster.serp_depth", args.serp_depth, DOCTRINE_DEFAULTS["semantics.cluster.serp_depth"]
    )
    confirm_size, confirm_rec = _resolve(
        th, "semantics.cluster.manual_confirm_size", None, DOCTRINE_DEFAULTS["semantics.cluster.manual_confirm_size"]
    )
    alert_ratio, alert_rec = _resolve(
        th, "semantics.cluster.drift_alert_ratio", None, DOCTRINE_DEFAULTS["semantics.cluster.drift_alert_ratio"]
    )

    if int(threshold) > int(serp_depth):
        raise KilnError(
            f"overlap threshold {threshold} exceeds serp_depth {serp_depth}: no pair can ever clear it"
        )

    all_queries = load_queries(args.queries, args.priorities, args.intents)
    scoped, excluded_locale, locale = scope_queries(all_queries, args.locale)

    # SEM-07: a hypothesis sits in the store; it does not enter the clusters of a run. Reported
    # rather than dropped quietly, because a silently shrinking core is indistinguishable from a
    # working one.
    verified = [q for q in scoped if q.is_verified]
    excluded_unverified = len(scoped) - len(verified)
    if not verified:
        raise KilnError(
            "SEM-07: every query in scope is unverified, so there is nothing to cluster. "
            "Verify queries against a SERP or GSC before clustering."
        )

    overlap, embed, edge_count = load_edges(args.edges)
    pillars = load_pillars(args.pillars)

    clusters = cluster_queries(verified, overlap, embed, int(threshold), int(serp_depth))
    for c in clusters:
        pillar_id, pillar_source = pillars.get(c.head_query_id, (None, None))
        c.pillar_id = pillar_id
        c.pillar_source = pillar_source

    by_id = {q.id: q for q in verified}
    param_records = [th_rec, depth_rec]
    findings: list[Finding] = []
    findings += detect_over_merging(clusters, by_id, locale, param_records)
    findings += flag_large_clusters(clusters, int(confirm_size), locale, [confirm_rec])
    findings += report_pillar_groups(clusters, locale)

    if excluded_unverified:
        findings.append(
            Finding(
                rule_id="SEM-07",
                severity="INFO",
                subject=locale,
                message=(
                    f"{excluded_unverified} unverified queries were excluded from the run. They "
                    f"remain hypotheses until a SERP or GSC confirms them."
                ),
                evidence={"excluded": excluded_unverified, "clustered": len(verified)},
                locale=locale,
            )
        )

    singletons = sum(1 for c in clusters if c.size == 1)
    if singletons:
        findings.append(
            Finding(
                rule_id="SEM-11",
                severity="INFO",
                subject=locale,
                message=(
                    f"{singletons} of {len(clusters)} clusters are singletons: no other query in "
                    f"the core shares enough of their SERP at the current threshold."
                ),
                evidence={"singletons": singletons, "clusters": len(clusters)},
                thresholds_used=[th_rec],
                locale=locale,
            )
        )

    params = {
        "threshold": int(threshold),
        "serp_depth": int(serp_depth),
        # Recorded for provenance only. Pre-filtering happens in `edges.py`; this script never
        # sees the pairs that were discarded there.
        "prefilter": args.prefilter,
    }
    run_id = args.run_id or _run_id(params, verified, overlap)

    lang, geo, device = locale.split("-", 2) if locale.count("-") >= 2 else (locale, "", "")

    payload: dict[str, Any] = {
        "run_id": run_id,
        "method": METHOD,
        # Activation is a deliberate act, not a side effect of clustering. SEM-23 exists precisely
        # so a large automatic merge is confirmed by a human before it becomes the active core.
        "is_active": bool(args.activate),
        "locale": {"key": locale, "lang": lang, "geo": geo, "device": device},
        "params": params,
        "params_provenance": sorted(param_records, key=lambda r: r["key"]),
        "inputs": {
            "queries_total": len(all_queries),
            "queries_in_scope": len(scoped),
            "queries_clustered": len(verified),
            "queries_excluded_unverified": excluded_unverified,
            "queries_excluded_other_locale": excluded_locale,
            "edges": edge_count,
        },
        "clusters": [c.as_record() for c in clusters],
    }
    if args.created_at:
        payload["created_at"] = args.created_at

    drift: dict[str, Any] | None = None
    if args.diff_against:
        prev = _read_json(args.diff_against)
        drift, drift_findings = diff_runs(prev, payload, float(alert_ratio), locale, [alert_rec])
        findings += drift_findings

    payload["findings"] = [f.as_record() for f in sort_findings(findings)]
    return payload, drift


def _read_json(path: Path) -> dict[str, Any]:
    import json

    p = Path(path)
    if not p.exists():
        raise KilnError(f"input file not found: {p}")
    try:
        return json.loads(p.read_text(encoding="utf-8"))
    except json.JSONDecodeError as exc:
        raise KilnError(f"{p}: malformed JSON: {exc}") from exc


# ---------------------------------------------------------------------------
# CLI
# ---------------------------------------------------------------------------


def build_parser() -> argparse.ArgumentParser:
    p = base_parser("Centroid clustering over the query edge graph (doctrine/02-semantics.md §13.3)")
    p.add_argument("--queries", type=Path, required=True, help="queries.norm.jsonl")
    p.add_argument("--edges", type=Path, required=True, help="edges.jsonl")
    p.add_argument("--priorities", type=Path, default=None,
                   help="priorities.jsonl; without it, ordering falls back to volume then text")
    p.add_argument("--intents", type=Path, default=None,
                   help="intents.jsonl; enables the over-merging indicators that depend on intent")
    p.add_argument("--pillars", type=Path, default=None,
                   help="JSONL mapping query_id to pillar_id and pillar_source")
    p.add_argument("--threshold", type=int, default=None,
                   help="shared URLs required to join a cluster; overrides thresholds.yml")
    p.add_argument("--serp-depth", type=int, default=None,
                   help="SERP depth the edges were computed over; denominator of membership_score")
    p.add_argument("--prefilter", type=float, default=None,
                   help="embedding pre-filter used by edges.py; recorded for provenance only")
    p.add_argument("--diff-against", type=Path, default=None,
                   help="previous clusters.json; emits the drift report for SEM-13")
    p.add_argument("--drift-out", type=Path, default=None,
                   help="where to write the drift report; defaults beside --out")
    p.add_argument("--run-id", default=None,
                   help="explicit run id; derived from a hash of the inputs when omitted")
    p.add_argument("--created-at", default=None,
                   help="optional ISO timestamp; omitted by default to keep output deterministic")
    p.add_argument("--activate", action="store_true",
                   help="mark this run active; withheld by default so SEM-23 confirmation can precede it")
    return p


def main(args: argparse.Namespace) -> int:
    payload, drift = build_run(args)

    if drift is not None:
        if args.drift_out:
            write_json(args.drift_out, drift)
        elif args.out:
            write_json(Path(args.out).parent / "cluster_drift.json", drift)
        else:
            emit(args, {"run": payload, "drift": drift})
            return EXIT_OK

    emit(args, payload)
    return EXIT_OK


if __name__ == "__main__":
    run(main, build_parser())
