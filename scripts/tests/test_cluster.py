"""Tests for cluster.py.

The load-bearing test in this file is `test_centroid_does_not_chain`. Everything else verifies
behaviour; that one verifies the reason the algorithm was chosen at all. If it ever starts passing
for the wrong reason, the doctrine's case for centroid over graph clustering has quietly evaporated.
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any, Sequence

import pytest

import cluster as mod
from kiln_common import KilnError, dumps


# ---------------------------------------------------------------------------
# Fixture helpers
# ---------------------------------------------------------------------------


def _write_jsonl(path: Path, rows: Sequence[dict[str, Any]]) -> Path:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8", newline="\n") as fh:
        for row in rows:
            fh.write(json.dumps(row, ensure_ascii=False, sort_keys=True) + "\n")
    return path


def q(
    qid: str,
    text: str,
    *,
    priority: float | None = None,
    volume: float | None = None,
    lang: str = "uk",
    geo: str = "UA",
    device: str = "desktop",
    is_verified: bool = True,
    commercial: str | None = None,
    cognitive: str | None = None,
) -> dict[str, Any]:
    rec: dict[str, Any] = {
        "id": qid,
        "text": text,
        "text_norm": text.casefold(),
        "lang": lang,
        "geo": geo,
        "device": device,
        "is_verified": is_verified,
    }
    if priority is not None:
        rec["priority"] = priority
    if volume is not None:
        rec["volume"] = volume
    if commercial is not None:
        rec["intent_commercial"] = commercial
    if cognitive is not None:
        rec["intent_cognitive"] = cognitive
    return rec


def e(a: str, b: str, overlap: int, embed_sim: float | None = None) -> dict[str, Any]:
    rec: dict[str, Any] = {"a": a, "b": b, "serp_overlap": overlap, "computed_at": "2026-08-07"}
    if embed_sim is not None:
        rec["embed_sim"] = embed_sim
    return rec


def make_args(
    tmp_path: Path,
    queries: Sequence[dict[str, Any]],
    edges: Sequence[dict[str, Any]],
    *,
    extra: Sequence[str] = (),
) -> Any:
    qp = _write_jsonl(tmp_path / "queries.norm.jsonl", queries)
    ep = _write_jsonl(tmp_path / "edges.jsonl", edges)
    argv = [
        "--project-root", str(tmp_path),
        "--queries", str(qp),
        "--edges", str(ep),
        *extra,
    ]
    return mod.build_parser().parse_args(argv)


def clusters_as_sets(payload: dict[str, Any]) -> list[set[str]]:
    return [{m["query_id"] for m in c["members"]} for c in payload["clusters"]]


def findings_for(payload: dict[str, Any], rule_id: str) -> list[dict[str, Any]]:
    return [f for f in payload["findings"] if f["rule_id"] == rule_id]


# The working fixture. Overlaps are chosen so that the 3-versus-4 threshold boundary is visible:
# q1-q3 sits at exactly 3, so it survives a loose threshold and fails the default one.
BASE_QUERIES = [
    q("q1", "кредитна картка порівняння", priority=100, volume=1000),
    q("q2", "найкраща кредитна картка 2026", priority=80, volume=800),
    q("q3", "як обрати кредитну картку", priority=60, volume=600),
    q("q4", "ягуар тварина", priority=40, volume=400),
    q("q5", "ягуар авто", priority=20, volume=200),
]

BASE_EDGES = [
    e("q1", "q2", 6, 0.81),
    e("q1", "q3", 3, 0.74),
    e("q2", "q3", 7, 0.88),
    # The two jaguars. High lexical and embedding similarity, one shared URL: the SERP knows they
    # are different things and nothing else does.
    e("q4", "q5", 1, 0.93),
]


# ---------------------------------------------------------------------------
# Core algorithm
# ---------------------------------------------------------------------------


def test_known_graph_has_the_expected_answer(tmp_path: Path) -> None:
    args = make_args(tmp_path, BASE_QUERIES, BASE_EDGES, extra=["--threshold", "3"])
    payload, drift = mod.build_run(args)

    assert drift is None
    assert clusters_as_sets(payload) == [{"q1", "q2", "q3"}, {"q4"}, {"q5"}]

    head = payload["clusters"][0]
    assert head["head_query_id"] == "q1"
    assert head["label"] == "кредитна картка порівняння"
    assert head["members"][0] == {"is_head": True, "membership_score": 1.0, "query_id": "q1"}
    assert payload["method"] == "centroid"
    assert payload["is_active"] is False


def test_centroid_does_not_chain(tmp_path: Path) -> None:
    """A links to B, B links to C, A and C share nothing.

    Graph clustering puts all three together and calls it a topic. Centroid clustering compares
    every candidate against the head, so C never reaches A. This is the entire argument of §3.3,
    and it is the one property that must not regress.
    """
    queries = [
        q("qa", "alpha", priority=100),
        q("qb", "bravo", priority=50),
        q("qc", "charlie", priority=10),
    ]
    edges = [e("qa", "qb", 5), e("qb", "qc", 5)]  # note: no qa-qc edge

    args = make_args(tmp_path, queries, edges, extra=["--threshold", "4"])
    payload, _ = mod.build_run(args)

    sets = clusters_as_sets(payload)
    assert sets == [{"qa", "qb"}, {"qc"}]
    assert not any({"qa", "qc"} <= s for s in sets), "qa and qc chained through qb"


def test_embedding_similarity_never_decides_membership(tmp_path: Path) -> None:
    """SEM-09: the SERP decides. A near-perfect embedding match with one shared URL stays apart."""
    args = make_args(tmp_path, BASE_QUERIES, BASE_EDGES, extra=["--threshold", "4"])
    payload, _ = mod.build_run(args)

    sets = clusters_as_sets(payload)
    assert {"q4", "q5"} not in sets
    assert {"q4"} in sets and {"q5"} in sets


def test_threshold_sensitivity_splits_what_a_looser_one_merges(tmp_path: Path) -> None:
    loose, _ = mod.build_run(make_args(tmp_path / "a", BASE_QUERIES, BASE_EDGES, extra=["--threshold", "3"]))
    strict, _ = mod.build_run(make_args(tmp_path / "b", BASE_QUERIES, BASE_EDGES, extra=["--threshold", "4"]))

    assert clusters_as_sets(loose) == [{"q1", "q2", "q3"}, {"q4"}, {"q5"}]
    assert clusters_as_sets(strict) == [{"q1", "q2"}, {"q3"}, {"q4"}, {"q5"}]
    assert loose["params"]["threshold"] == 3
    assert strict["params"]["threshold"] == 4


def test_membership_score_is_overlap_over_depth(tmp_path: Path) -> None:
    args = make_args(tmp_path, BASE_QUERIES, BASE_EDGES, extra=["--threshold", "3", "--serp-depth", "10"])
    payload, _ = mod.build_run(args)

    scores = {m["query_id"]: m["membership_score"] for m in payload["clusters"][0]["members"]}
    assert scores == {"q1": 1.0, "q2": 0.6, "q3": 0.3}


def test_default_threshold_comes_from_the_doctrine(tmp_path: Path) -> None:
    args = make_args(tmp_path, BASE_QUERIES, BASE_EDGES)
    payload, _ = mod.build_run(args)

    assert payload["params"]["threshold"] == 4
    provenance = {r["key"]: r["source"] for r in payload["params_provenance"]}
    assert provenance["semantics.cluster.overlap_threshold"] == "doctrine"


def test_local_calibration_overrides_the_doctrine(tmp_path: Path) -> None:
    pytest.importorskip("yaml")
    kiln = tmp_path / ".kiln"
    kiln.mkdir(parents=True, exist_ok=True)
    (kiln / "thresholds.yml").write_text(
        "semantics:\n  cluster:\n    overlap_threshold:\n      value: 3\n"
        "      calibrated_on: '2026-11-01'\n",
        encoding="utf-8",
    )

    args = make_args(tmp_path, BASE_QUERIES, BASE_EDGES)
    payload, _ = mod.build_run(args)

    assert payload["params"]["threshold"] == 3
    provenance = {r["key"]: r["source"] for r in payload["params_provenance"]}
    assert provenance["semantics.cluster.overlap_threshold"] == "local"


def test_threshold_above_serp_depth_is_rejected(tmp_path: Path) -> None:
    args = make_args(tmp_path, BASE_QUERIES, BASE_EDGES, extra=["--threshold", "11", "--serp-depth", "10"])
    with pytest.raises(KilnError, match="exceeds serp_depth"):
        mod.build_run(args)


# ---------------------------------------------------------------------------
# Determinism
# ---------------------------------------------------------------------------


def test_two_runs_over_identical_input_are_byte_identical(tmp_path: Path) -> None:
    first, _ = mod.build_run(make_args(tmp_path / "one", BASE_QUERIES, BASE_EDGES))
    second, _ = mod.build_run(make_args(tmp_path / "two", BASE_QUERIES, BASE_EDGES))
    assert dumps(first) == dumps(second)


def test_input_order_does_not_change_the_result(tmp_path: Path) -> None:
    """The sort is total, so shuffling the input file cannot move a query between clusters."""
    shuffled = list(reversed(BASE_QUERIES))
    normal, _ = mod.build_run(make_args(tmp_path / "n", BASE_QUERIES, BASE_EDGES))
    reordered, _ = mod.build_run(make_args(tmp_path / "r", shuffled, list(reversed(BASE_EDGES))))
    assert dumps(normal) == dumps(reordered)


def test_run_id_changes_when_the_graph_changes(tmp_path: Path) -> None:
    before, _ = mod.build_run(make_args(tmp_path / "before", BASE_QUERIES, BASE_EDGES))
    moved_edges = [e("q1", "q2", 9), *BASE_EDGES[1:]]
    after, _ = mod.build_run(make_args(tmp_path / "after", BASE_QUERIES, moved_edges))
    assert before["run_id"] != after["run_id"]


def test_created_at_is_absent_unless_requested(tmp_path: Path) -> None:
    payload, _ = mod.build_run(make_args(tmp_path / "a", BASE_QUERIES, BASE_EDGES))
    assert "created_at" not in payload

    stamped, _ = mod.build_run(
        make_args(tmp_path / "b", BASE_QUERIES, BASE_EDGES, extra=["--created-at", "2026-08-07T10:00:00Z"])
    )
    assert stamped["created_at"] == "2026-08-07T10:00:00Z"


# ---------------------------------------------------------------------------
# Locale (SEM-18)
# ---------------------------------------------------------------------------


def test_mixed_locales_are_rejected_without_an_explicit_locale(tmp_path: Path) -> None:
    queries = [
        q("q1", "кредитна картка", priority=100),
        q("q2", "кредитная карта", priority=90, lang="ru"),
    ]
    args = make_args(tmp_path, queries, [e("q1", "q2", 8)])
    with pytest.raises(KilnError, match="SEM-18"):
        mod.build_run(args)


def test_explicit_locale_filters_and_reports_the_exclusions(tmp_path: Path) -> None:
    queries = [
        q("q1", "кредитна картка", priority=100),
        q("q2", "кредитная карта", priority=90, lang="ru"),
    ]
    args = make_args(tmp_path, queries, [e("q1", "q2", 8)], extra=["--locale", "uk-UA-desktop"])
    payload, _ = mod.build_run(args)

    assert payload["locale"]["key"] == "uk-UA-desktop"
    assert payload["inputs"]["queries_excluded_other_locale"] == 1
    assert clusters_as_sets(payload) == [{"q1"}]


def test_device_is_part_of_the_locale(tmp_path: Path) -> None:
    """Mobile and desktop SERPs differ, so a cluster spanning them rests on two rankings."""
    queries = [
        q("q1", "кредитна картка", priority=100),
        q("q2", "кредитна картка", priority=90, device="mobile"),
    ]
    args = make_args(tmp_path, queries, [e("q1", "q2", 9)])
    with pytest.raises(KilnError, match="SEM-18"):
        mod.build_run(args)


def test_unknown_locale_names_the_available_ones(tmp_path: Path) -> None:
    args = make_args(tmp_path, BASE_QUERIES, BASE_EDGES, extra=["--locale", "pl-PL-desktop"])
    with pytest.raises(KilnError, match="uk-UA-desktop"):
        mod.build_run(args)


# ---------------------------------------------------------------------------
# SEM-07: unverified queries
# ---------------------------------------------------------------------------


def test_unverified_queries_are_excluded_and_reported(tmp_path: Path) -> None:
    queries = [
        q("q1", "кредитна картка порівняння", priority=100),
        q("q2", "найкраща кредитна картка", priority=80),
        q("q3", "вигаданий запит", priority=70, is_verified=False),
    ]
    edges = [e("q1", "q2", 6), e("q1", "q3", 9)]

    args = make_args(tmp_path, queries, edges)
    payload, _ = mod.build_run(args)

    assert clusters_as_sets(payload) == [{"q1", "q2"}]
    assert payload["inputs"]["queries_excluded_unverified"] == 1
    assert len(findings_for(payload, "SEM-07")) == 1


def test_a_missing_verification_flag_counts_as_unverified(tmp_path: Path) -> None:
    """Absent means hypothesis. The safe reading is the only defensible default under P1."""
    rec = q("q1", "запит", priority=10)
    rec.pop("is_verified")
    args = make_args(tmp_path, [rec], [])
    with pytest.raises(KilnError, match="SEM-07"):
        mod.build_run(args)


# ---------------------------------------------------------------------------
# Over-merging indicators (§3.2)
# ---------------------------------------------------------------------------


def test_mixed_commercial_intent_raises_an_over_merging_warning(tmp_path: Path) -> None:
    queries = [
        q("q1", "кредитна картка порівняння", priority=100, commercial="informational"),
        q("q2", "оформити кредитну картку", priority=80, commercial="transactional"),
    ]
    args = make_args(tmp_path, queries, [e("q1", "q2", 8)])
    payload, _ = mod.build_run(args)

    warnings = findings_for(payload, "SEM-10")
    assert len(warnings) == 1
    assert warnings[0]["severity"] == "WARN"
    assert warnings[0]["evidence"]["commercial_intents"] == ["informational", "transactional"]
    assert warnings[0]["thresholds_used"], "a finding without its thresholds cannot be re-read later"


def test_mixed_cognitive_axis_raises_an_over_merging_warning(tmp_path: Path) -> None:
    queries = [
        q("q1", "що таке кредитна картка", priority=100, cognitive="knowledge-seeking"),
        q("q2", "калькулятор кредитної картки", priority=80, cognitive="output-seeking"),
    ]
    args = make_args(tmp_path, queries, [e("q1", "q2", 8)])
    payload, _ = mod.build_run(args)

    warnings = findings_for(payload, "SEM-10")
    assert len(warnings) == 1
    assert warnings[0]["evidence"]["cognitive_intents"] == ["knowledge", "output"]


def test_intent_can_arrive_from_a_separate_intents_file(tmp_path: Path) -> None:
    queries = [
        q("q1", "кредитна картка порівняння", priority=100),
        q("q2", "оформити кредитну картку", priority=80),
    ]
    intents = _write_jsonl(
        tmp_path / "intents.jsonl",
        [
            {"query_id": "q1", "intent_commercial": "informational", "intent_cognitive": "knowledge"},
            {"query_id": "q2", "intent_commercial": "transactional", "intent_cognitive": "guidance"},
        ],
    )
    args = make_args(tmp_path, queries, [e("q1", "q2", 8)], extra=["--intents", str(intents)])
    payload, _ = mod.build_run(args)

    assert len(findings_for(payload, "SEM-10")) == 1
    assert payload["clusters"][0]["intent_commercial"] == "informational"  # the head's


def test_a_homogeneous_cluster_raises_nothing(tmp_path: Path) -> None:
    queries = [
        q("q1", "кредитна картка порівняння", priority=100, commercial="commercial", cognitive="guidance"),
        q("q2", "найкраща кредитна картка", priority=80, commercial="commercial", cognitive="guidance"),
    ]
    args = make_args(tmp_path, queries, [e("q1", "q2", 8)])
    payload, _ = mod.build_run(args)
    assert findings_for(payload, "SEM-10") == []


# ---------------------------------------------------------------------------
# SEM-23 and SEM-25
# ---------------------------------------------------------------------------


def test_large_clusters_are_flagged_for_human_confirmation(tmp_path: Path) -> None:
    queries = [q("q0", "head", priority=100)]
    edges = []
    for i in range(1, 25):
        queries.append(q(f"q{i}", f"member {i:02d}", priority=100 - i))
        edges.append(e("q0", f"q{i}", 8))

    args = make_args(tmp_path, queries, edges)
    payload, _ = mod.build_run(args)

    assert payload["clusters"][0]["size"] == 25
    assert payload["clusters"][0]["needs_human_confirmation"] is True
    sem23 = findings_for(payload, "SEM-23")
    assert len(sem23) == 1 and sem23[0]["severity"] == "WARN"


def test_small_clusters_are_not_flagged(tmp_path: Path) -> None:
    payload, _ = mod.build_run(make_args(tmp_path, BASE_QUERIES, BASE_EDGES))
    assert findings_for(payload, "SEM-23") == []
    assert all(c["needs_human_confirmation"] is False for c in payload["clusters"])


def test_clusters_sharing_a_pillar_are_reported_as_dependent(tmp_path: Path) -> None:
    pillars = _write_jsonl(
        tmp_path / "pillars.jsonl",
        [
            {"query_id": "q1", "pillar_id": "p-cards", "pillar_source": "declared"},
            {"query_id": "q4", "pillar_id": "p-cards", "pillar_source": "declared"},
        ],
    )
    args = make_args(tmp_path, BASE_QUERIES, BASE_EDGES, extra=["--pillars", str(pillars)])
    payload, _ = mod.build_run(args)

    sem25 = findings_for(payload, "SEM-25")
    assert len(sem25) == 1
    # At the default threshold of 4 the q4 cluster is third: q1+q2, then q3 alone, then q4.
    assert sem25[0]["subject"] == "p-cards"
    assert sem25[0]["evidence"]["cluster_ids"] == ["c-001", "c-003"]


def test_a_cluster_without_a_pillar_records_null_rather_than_independence(tmp_path: Path) -> None:
    payload, _ = mod.build_run(make_args(tmp_path, BASE_QUERIES, BASE_EDGES))
    assert payload["clusters"][0]["pillar_id"] is None
    assert payload["clusters"][0]["pillar_source"] is None
    assert findings_for(payload, "SEM-25") == []


def test_an_invalid_pillar_source_is_rejected(tmp_path: Path) -> None:
    pillars = _write_jsonl(
        tmp_path / "pillars.jsonl", [{"query_id": "q1", "pillar_id": "p", "pillar_source": "guessed"}]
    )
    args = make_args(tmp_path, BASE_QUERIES, BASE_EDGES, extra=["--pillars", str(pillars)])
    with pytest.raises(KilnError, match="declared"):
        mod.build_run(args)


# ---------------------------------------------------------------------------
# Drift (SEM-13)
# ---------------------------------------------------------------------------


def test_diff_against_reports_a_known_move(tmp_path: Path) -> None:
    loose, _ = mod.build_run(make_args(tmp_path / "prev", BASE_QUERIES, BASE_EDGES, extra=["--threshold", "3"]))
    prev_path = tmp_path / "prev_run.json"
    prev_path.write_text(dumps(loose), encoding="utf-8")

    args = make_args(
        tmp_path / "curr",
        BASE_QUERIES,
        BASE_EDGES,
        extra=["--threshold", "4", "--diff-against", str(prev_path)],
    )
    payload, drift = mod.build_run(args)

    assert drift is not None
    assert drift["summary"]["queries_compared"] == 5
    # q3 left the cluster; q1 and q2 lost it as a mate. Three of five queries changed company.
    assert drift["summary"]["queries_changed"] == 3
    assert drift["summary"]["overall_drift_ratio"] == 0.6
    assert drift["summary"]["clusters_split"] == 1
    assert drift["summary"]["clusters_merged"] == 0

    moved = {c["query_id"] for c in drift["changed"]}
    assert moved == {"q1", "q2", "q3"}

    sem13 = findings_for(payload, "SEM-13")
    assert len(sem13) == 1
    assert sem13[0]["evidence"]["prev_cluster_id"] == "c-001"
    assert sem13[0]["evidence"]["drift_ratio"] == 1.0


def test_an_unchanged_rebuild_reports_no_drift(tmp_path: Path) -> None:
    first, _ = mod.build_run(make_args(tmp_path / "prev", BASE_QUERIES, BASE_EDGES))
    prev_path = tmp_path / "prev_run.json"
    prev_path.write_text(dumps(first), encoding="utf-8")

    args = make_args(tmp_path / "curr", BASE_QUERIES, BASE_EDGES, extra=["--diff-against", str(prev_path)])
    payload, drift = mod.build_run(args)

    assert drift["summary"]["queries_changed"] == 0
    assert drift["summary"]["overall_drift_ratio"] == 0.0
    assert findings_for(payload, "SEM-13") == []


def test_a_new_query_is_reported_as_added_not_as_drift(tmp_path: Path) -> None:
    """A query that did not exist last time has not moved. Counting it as drift would make every
    core expansion look like a SERP shift."""
    first, _ = mod.build_run(make_args(tmp_path / "prev", BASE_QUERIES, BASE_EDGES))
    prev_path = tmp_path / "prev_run.json"
    prev_path.write_text(dumps(first), encoding="utf-8")

    grown = [*BASE_QUERIES, q("q6", "нова тема", priority=5)]
    args = make_args(tmp_path / "curr", grown, BASE_EDGES, extra=["--diff-against", str(prev_path)])
    payload, drift = mod.build_run(args)

    assert drift["added"] == ["q6"]
    assert drift["summary"]["queries_changed"] == 0
    assert findings_for(payload, "SEM-13") == []


def test_a_head_change_alone_is_not_drift(tmp_path: Path) -> None:
    """Membership is compared through cluster-mates, not through cluster ids or heads.

    Raising q2 above q1 makes q2 the head of the same pair. Nothing about who is grouped with whom
    has changed, and an id-based comparison would wrongly report that it had.
    """
    queries = [q("q1", "alpha", priority=100), q("q2", "bravo", priority=80)]
    edges = [e("q1", "q2", 8)]
    first, _ = mod.build_run(make_args(tmp_path / "prev", queries, edges))
    prev_path = tmp_path / "prev_run.json"
    prev_path.write_text(dumps(first), encoding="utf-8")

    reordered = [q("q1", "alpha", priority=80), q("q2", "bravo", priority=100)]
    args = make_args(tmp_path / "curr", reordered, edges, extra=["--diff-against", str(prev_path)])
    payload, drift = mod.build_run(args)

    assert first["clusters"][0]["head_query_id"] == "q1"
    assert payload["clusters"][0]["head_query_id"] == "q2"
    assert drift["summary"]["queries_changed"] == 0


# ---------------------------------------------------------------------------
# Input validation
# ---------------------------------------------------------------------------


def test_duplicate_query_ids_are_rejected(tmp_path: Path) -> None:
    args = make_args(tmp_path, [q("q1", "a", priority=1), q("q1", "b", priority=2)], [])
    with pytest.raises(KilnError, match="duplicate query id"):
        mod.build_run(args)


def test_a_missing_required_field_names_itself(tmp_path: Path) -> None:
    broken = q("q1", "a", priority=1)
    broken.pop("lang")
    args = make_args(tmp_path, [broken], [])
    with pytest.raises(KilnError, match="lang"):
        mod.build_run(args)


def test_a_self_edge_is_rejected(tmp_path: Path) -> None:
    args = make_args(tmp_path, BASE_QUERIES, [e("q1", "q1", 9)])
    with pytest.raises(KilnError, match="self-edge"):
        mod.build_run(args)


def test_edges_referencing_absent_queries_are_ignored(tmp_path: Path) -> None:
    """The edge graph is rebuilt from a cache and may outlive a query that was dropped upstream."""
    args = make_args(tmp_path, BASE_QUERIES, [*BASE_EDGES, e("q1", "q999", 9)])
    payload, _ = mod.build_run(args)
    assert all("q999" not in s for s in clusters_as_sets(payload))
