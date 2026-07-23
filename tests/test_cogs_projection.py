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
    project_result,
)
from rulekit.harness.snapshot import diff
from rulekit.kernel.engine import solve
from rulekit.kernel.model import SemanticGraphEdge, SemanticGraphNode


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


@pytest.fixture(scope="module")
def cogs_project():
    return load_project(Path("projects/cogs"))


def test_active_named_indefinite_transitive_projects_a_complete_graph(
    cogs_project,
) -> None:
    text = "Neris admired a cloud."
    result = solve(text, cogs_project.registry, tracing=False)
    got = project_result(result, text, cogs_project.registry)
    expected = parse_cogs_logical_form(
        "admire.agent(x_1,Neris) AND admire.theme(x_1,x_3) "
        "AND cloud(x_3)"
    )
    assert got.node_keys() == expected.node_keys()
    assert got.edge_keys() == expected.edge_keys()

    nodes = list(result.store.by_kind(SemanticGraphNode))
    edges = list(result.store.by_kind(SemanticGraphEdge))
    assert len(nodes) == 3
    assert len(edges) == 4
    assert {fact.provenance.source for fact in nodes + edges} == {
        "semantic/active-name-indefinite-theme"
    }
    assert {
        (fact.span_start, fact.span_end) for fact in nodes
    } == {("0", "0"), ("1", "1"), ("3", "3")}


@pytest.mark.parametrize(
    "text",
    [
        "Neris admired the cloud.",
        "A pilot admired a cloud.",
        "A cloud was admired by Neris.",
        "Neris admired a cloud near Mira.",
        "Neris admired a cloud and a bell.",
        "Neris missed a cloud.",
        "Neris admired a rose.",
    ],
)
def test_active_transitive_rule_declines_negative_neighbours(
    cogs_project,
    text: str,
) -> None:
    result = solve(text, cogs_project.registry, tracing=False)
    assert list(result.store.by_kind(SemanticGraphNode)) == []
    assert list(result.store.by_kind(SemanticGraphEdge)) == []


def test_new_event_vocabulary_does_not_buy_a_definite_neighbour(
    cogs_project,
) -> None:
    text = "Neris admired the cloud."
    result = solve(text, cogs_project.registry, tracing=False)
    assert project_result(result, text, cogs_project.registry).empty


def test_named_intransitive_agent_projects_a_complete_graph(
    cogs_project,
) -> None:
    text = "Neris smiled."
    result = solve(text, cogs_project.registry, tracing=False)
    got = project_result(result, text, cogs_project.registry)
    expected = parse_cogs_logical_form(
        "smile.agent(x_1,Neris)"
    )
    assert got.node_keys() == expected.node_keys()
    assert got.edge_keys() == expected.edge_keys()

    nodes = list(result.store.by_kind(SemanticGraphNode))
    edges = list(result.store.by_kind(SemanticGraphEdge))
    assert len(nodes) == 2
    assert len(edges) == 2
    assert {fact.provenance.source for fact in nodes + edges} == {
        "semantic/intransitive-name-agent"
    }
    assert {
        (fact.span_start, fact.span_end) for fact in nodes
    } == {("0", "0"), ("1", "1")}


@pytest.mark.parametrize(
    "text",
    [
        "Neris collapsed.",
        "A pilot smiled.",
        "The pilot smiled.",
        "Neris smiled a cloud.",
        "Neris smiled near Mira.",
        "Neris smiled and laughed.",
        "Neris cooked.",
        "Neris called.",
    ],
)
def test_named_intransitive_agent_declines_role_and_shape_neighbours(
    cogs_project,
    text: str,
) -> None:
    result = solve(text, cogs_project.registry, tracing=False)
    semantic_sources = {
        fact.provenance.source
        for fact in (
            list(result.store.by_kind(SemanticGraphNode))
            + list(result.store.by_kind(SemanticGraphEdge))
        )
    }
    assert "semantic/intransitive-name-agent" not in semantic_sources


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
