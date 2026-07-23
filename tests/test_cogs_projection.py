"""Synthetic contracts for the COGS projection harness.

No COGS sentence is copied here.  The logical forms use invented predicates
and names so the evaluator is pinned without tuning a reader to benchmark
items.
"""

from __future__ import annotations

import importlib.util
import sys
from pathlib import Path

import pytest

from rulekit.data.project import load_project
from rulekit.harness.projection import (
    ProjectionEdge,
    ProjectionGraph,
    ProjectionNode,
    classify_projection_graph,
    parse_cogs_logical_form,
)
from rulekit.harness.snapshot import diff


def test_cogs_adapter_normalizes_conjunct_order_and_spacing() -> None:
    first = parse_cogs_logical_form(
        "* lantern ( x _ 1 ) ; polish . agent ( x _ 2 , Mira ) "
        "AND polish . theme ( x _ 2 , x _ 1 )"
    )
    second = parse_cogs_logical_form(
        "polish.theme(x_2,x_1) AND polish.agent(x_2,Mira) ; "
        "* lantern(x_1)"
    )
    assert first.node_keys() == second.node_keys()
    assert first.edge_keys() == second.edge_keys()
    assert ("definite", "x1", "", "") in first.edge_keys()
    assert ("role", "x2", "const:mira", "agent") in first.edge_keys()


def test_cogs_adapter_represents_modifiers_and_complements() -> None:
    graph = parse_cogs_logical_form(
        "wonder . agent ( x _ 1 , Lio ) "
        "AND wonder . ccomp ( x _ 1 , x _ 4 ) "
        "AND vessel ( x _ 3 ) "
        "AND drift . theme ( x _ 4 , x _ 3 ) "
        "AND vessel . nmod . near ( x _ 3 , x _ 7 ) "
        "AND beacon ( x _ 7 )"
    )
    assert ("complement", "x1", "x4", "ccomp") in graph.edge_keys()
    assert ("modifier", "x3", "x7", "near") in graph.edge_keys()
    assert ("role", "x4", "x3", "theme") in graph.edge_keys()


def test_cogs_adapter_alpha_normalizes_primitive_lambdas() -> None:
    left = parse_cogs_logical_form(
        "LAMBDA a . LAMBDA b . LAMBDA e . "
        "glimmer . agent ( e , b ) AND glimmer . theme ( e , a )"
    )
    right = parse_cogs_logical_form(
        "LAMBDA z . LAMBDA y . LAMBDA q . "
        "glimmer . theme ( q , z ) AND glimmer . agent ( q , y )"
    )
    assert left.node_keys() == right.node_keys()
    assert left.edge_keys() == right.edge_keys()


def test_cogs_adapter_handles_noun_and_name_primitives() -> None:
    noun = parse_cogs_logical_form("LAMBDA r . zephyr ( r )")
    name = parse_cogs_logical_form("Neris")
    assert noun.edge_keys() == frozenset({
        ("type", "bound:0", "", "zephyr"),
    })
    assert name.node_keys() == frozenset({("const:neris", "entity")})


def test_projection_construction_taxonomy_is_graph_structural() -> None:
    graph = parse_cogs_logical_form(
        "carry . agent ( x _ 1 , Neris ) "
        "AND carry . theme ( x _ 1 , x _ 3 ) "
        "AND carry . recipient ( x _ 1 , x _ 5 ) "
        "AND parcel ( x _ 3 ) AND pilot ( x _ 5 )"
    )
    assert classify_projection_graph(graph) == "ditransitive"


def _snapshot(outcome: str, got_label: str = "") -> dict:
    got = ProjectionGraph(
        nodes=(ProjectionNode("x1", "entity"),) if got_label else (),
        edges=(
            ProjectionEdge("type", "x1", label=got_label),
        ) if got_label else (),
    )
    return {
        "kind": "projection",
        "schema": "rulekit/projection-graph@1",
        "fingerprint": "synthetic",
        "items": {
            "invented": {
                "outcome": outcome,
                "got": got.to_json(),
            }
        },
    }


def test_projection_diff_rejects_safe_to_incorrect() -> None:
    delta = diff(_snapshot("declined"), _snapshot("incorrect", "wrong"))
    assert delta.safe_to_incorrect == ["invented"]
    assert not delta.ship


def test_projection_diff_credits_new_exact_graph() -> None:
    delta = diff(_snapshot("partial", "glow"), _snapshot("exact", "glow"))
    assert delta.exact == ["invented"]
    assert delta.ship


def _builder():
    path = Path("projects/cogs/build_corpus.py")
    spec = importlib.util.spec_from_file_location("cogs_build_corpus", path)
    module = importlib.util.module_from_spec(spec)
    assert spec.loader is not None
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module


def test_cogs_train_partition_is_stable_and_has_both_sides() -> None:
    builder = _builder()
    examples = {
        builder.train_bucket(f"Synthetic projection sentence {index}.")
        for index in range(200)
    }
    assert examples == {"dev-train", "dev-holdout"}
    assert builder.train_bucket("A synthetic sentence.") == builder.train_bucket(
        "A synthetic sentence."
    )


def test_cogs_project_declares_protected_external_slices() -> None:
    project = load_project(Path("projects/cogs"))
    assert project.doc.projection is not None
    assert project.projection_slice_inspectable("dev-train")
    assert project.projection_slice_inspectable("calibration")
    assert not project.projection_slice_inspectable("test")
    assert not project.projection_slice_inspectable("generalization")


@pytest.mark.skipif(
    not Path("projects/cogs/data/cogs_dev_train.parquet").exists(),
    reason="COGS corpus not materialized",
)
def test_materialized_cogs_firewall_and_gold_adapter() -> None:
    project = load_project(Path("projects/cogs"))
    train = project.projection_items("dev-train")
    holdout = project.projection_items("dev-holdout")
    calibration = project.projection_items("calibration")
    assert len(train) + len(holdout) == 24_155
    assert len(calibration) == 3_000
    assert {item.id for item in train}.isdisjoint(
        {item.id for item in holdout}
    )
    assert all(item.gold.nodes or item.gold.edges for item in train + holdout)
