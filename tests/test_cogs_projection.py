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
    semantic_sources = {
        fact.provenance.source
        for fact in (
            list(result.store.by_kind(SemanticGraphNode))
            + list(result.store.by_kind(SemanticGraphEdge))
        )
    }
    assert "semantic/active-name-indefinite-theme" not in semantic_sources


def test_new_event_vocabulary_does_not_buy_a_definite_neighbour(
    cogs_project,
) -> None:
    text = "Neris admired the cloud."
    result = solve(text, cogs_project.registry, tracing=False)
    assert project_result(result, text, cogs_project.registry).empty


@pytest.mark.parametrize("preposition", ["beside", "in", "on"])
def test_active_theme_nominal_modifier_projects_complete_attachment(
    cogs_project,
    preposition: str,
) -> None:
    text = f"Neris admired a zephyrstone {preposition} a zephyrstone."
    result = solve(text, cogs_project.registry, tracing=False)
    got = project_result(result, text, cogs_project.registry)
    expected = parse_cogs_logical_form(
        "admire.agent(x_1,Neris) AND admire.theme(x_1,x_3) "
        f"AND zephyrstone(x_3) "
        f"AND zephyrstone.nmod.{preposition}(x_3,x_6) "
        "AND zephyrstone(x_6)"
    )
    assert got.node_keys() == expected.node_keys()
    assert got.edge_keys() == expected.edge_keys()
    assert ("modifier", "x3", "x6", preposition) in got.edge_keys()

    nodes = list(result.store.by_kind(SemanticGraphNode))
    edges = list(result.store.by_kind(SemanticGraphEdge))
    assert len(nodes) == 4
    assert len(edges) == 6
    assert {fact.provenance.source for fact in nodes + edges} == {
        "semantic/active-name-indefinite-theme-indefinite-modifier"
    }
    assert {
        (fact.span_start, fact.span_end) for fact in nodes
    } == {("0", "0"), ("1", "1"), ("3", "3"), ("6", "6")}
    modifier = next(fact for fact in edges if fact.kind == "modifier")
    assert (modifier.source, modifier.target, modifier.label) == (
        "entity:3",
        "entity:6",
        preposition,
    )
    assert (modifier.span_start, modifier.span_end) == ("3", "6")


@pytest.mark.parametrize(
    "text",
    [
        "A zephyrstone beside a chair admired a zephyrstone.",
        "Neris admired the zephyrstone beside a chair.",
        "Neris admired a zephyrstone beside the chair.",
        "Neris admired a zephyrstone beside Mira.",
        "Neris admired a zephyrstone near a chair.",
        "Neris admired a zephyrstone beside chair.",
        "Neris admired a zephyrstone beside a chair on a table.",
        "Neris admired a zephyrstone beside a chair and a table.",
        "A zephyrstone was admired by Neris beside a chair.",
        "Neris did not admire a zephyrstone beside a chair.",
        "Neris said that Mira admired a zephyrstone beside a chair.",
        "Neris missed a zephyrstone beside a chair.",
        "Neris admired a zephyrstone beside a log.",
    ],
)
def test_active_theme_nominal_modifier_declines_attachment_neighbours(
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
    assert (
        "semantic/active-name-indefinite-theme-indefinite-modifier"
        not in semantic_sources
    )


def test_named_agent_ccomp_projects_two_events_and_direction(
    cogs_project,
) -> None:
    text = "Neris hoped that Mira smiled."
    result = solve(text, cogs_project.registry, tracing=False)
    got = project_result(result, text, cogs_project.registry)
    expected = parse_cogs_logical_form(
        "hope.agent(x_1,Neris) AND hope.ccomp(x_1,x_4) "
        "AND smile.agent(x_4,Mira)"
    )
    assert got.node_keys() == expected.node_keys()
    assert got.edge_keys() == expected.edge_keys()
    assert ("complement", "x1", "x4", "ccomp") in got.edge_keys()
    assert ("complement", "x4", "x1", "ccomp") not in got.edge_keys()

    nodes = list(result.store.by_kind(SemanticGraphNode))
    edges = list(result.store.by_kind(SemanticGraphEdge))
    assert len(nodes) == 4
    assert len(edges) == 5
    assert {fact.provenance.source for fact in nodes + edges} == {
        "semantic/ccomp-name-agent-name-agent"
    }
    complement = next(fact for fact in edges if fact.kind == "complement")
    assert (complement.source, complement.target, complement.label) == (
        "event:1",
        "event:4",
        "ccomp",
    )
    assert (complement.span_start, complement.span_end) == ("1", "4")


def test_named_agent_ccomp_preserves_shared_name_and_distinct_events(
    cogs_project,
) -> None:
    text = "Neris hoped that Neris smiled."
    result = solve(text, cogs_project.registry, tracing=False)
    got = project_result(result, text, cogs_project.registry)
    expected = parse_cogs_logical_form(
        "hope.agent(x_1,Neris) AND hope.ccomp(x_1,x_4) "
        "AND smile.agent(x_4,Neris)"
    )
    assert got.node_keys() == expected.node_keys()
    assert got.edge_keys() == expected.edge_keys()
    assert len([node for node in got.nodes if node.kind == "entity"]) == 1
    assert len([node for node in got.nodes if node.kind == "event"]) == 2


@pytest.mark.parametrize(
    "text",
    [
        "Neris hoped Mira smiled.",
        "A pilot hoped that Mira smiled.",
        "Neris hoped that a pilot smiled.",
        "Neris hoped that the pilot smiled.",
        "Neris hoped that Mira reddened.",
        "Neris hoped that Mira admired a zephyrstone.",
        "Neris hoped that a zephyrstone was admired by Mira.",
        "Neris hoped to smile.",
        "Neris hoped that Mira smiled and laughed.",
        "Neris did not hope that Mira smiled.",
        "Neris hoped that Mira hoped that Lio smiled.",
        "Neris told Mira that Lio smiled.",
        "Neris said that Mira smiled.",
        "Neris hoped that Mira cooked.",
    ],
)
def test_named_agent_ccomp_declines_neighbouring_complement_shapes(
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
    assert "semantic/ccomp-name-agent-name-agent" not in semantic_sources


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


def test_named_intransitive_theme_projects_a_complete_graph(
    cogs_project,
) -> None:
    text = "Neris reddened."
    result = solve(text, cogs_project.registry, tracing=False)
    got = project_result(result, text, cogs_project.registry)
    expected = parse_cogs_logical_form(
        "redden.theme(x_1,Neris)"
    )
    assert got.node_keys() == expected.node_keys()
    assert got.edge_keys() == expected.edge_keys()
    assert ("role", "x1", "const:neris", "theme") in got.edge_keys()
    assert ("role", "x1", "const:neris", "agent") not in got.edge_keys()

    nodes = list(result.store.by_kind(SemanticGraphNode))
    edges = list(result.store.by_kind(SemanticGraphEdge))
    assert len(nodes) == 2
    assert len(edges) == 2
    assert {fact.provenance.source for fact in nodes + edges} == {
        "semantic/intransitive-name-theme"
    }


@pytest.mark.parametrize(
    "text",
    [
        "Neris smiled.",
        "A pilot reddened.",
        "The pilot reddened.",
        "Neris reddened a cloud.",
        "Neris reddened near Mira.",
        "Neris reddened and collapsed.",
        "Neris broke.",
        "Neris doubled.",
        "Neris was reddened.",
    ],
)
def test_named_intransitive_theme_declines_role_and_shape_neighbours(
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
    assert "semantic/intransitive-name-theme" not in semantic_sources


def test_indefinite_agentless_passive_projects_a_complete_graph(
    cogs_project,
) -> None:
    text = "A zephyrstone was appreciated."
    result = solve(text, cogs_project.registry, tracing=False)
    got = project_result(result, text, cogs_project.registry)
    expected = parse_cogs_logical_form(
        "zephyrstone(x_1) AND appreciate.theme(x_3,x_1)"
    )
    assert got.node_keys() == expected.node_keys()
    assert got.edge_keys() == expected.edge_keys()
    assert ("role", "x3", "x1", "theme") in got.edge_keys()
    assert not any(
        edge[0] == "role" and edge[3] == "agent"
        for edge in got.edge_keys()
    )

    nodes = list(result.store.by_kind(SemanticGraphNode))
    edges = list(result.store.by_kind(SemanticGraphEdge))
    assert len(nodes) == 2
    assert len(edges) == 3
    assert {fact.provenance.source for fact in nodes + edges} == {
        "semantic/passive-indefinite-theme-agent-omitted"
    }
    assert {
        (fact.span_start, fact.span_end) for fact in nodes
    } == {("1", "1"), ("3", "3")}


@pytest.mark.parametrize(
    "text",
    [
        "The zephyrstone was appreciated.",
        "Neris was appreciated.",
        "A zephyrstone was appreciated by Neris.",
        "Neris appreciated a zephyrstone.",
        "A zephyrstone appreciated.",
        "Zephyrstones were appreciated.",
        "A zephyrstone was appreciated near Neris.",
        "A zephyrstone was appreciated and admired.",
        "A zephyrstone was not appreciated.",
        "A zephyrstone was cooked.",
        "A zephyrstone was frozen.",
        "A zephyrstone is appreciated.",
        "Neris said that a zephyrstone was appreciated.",
    ],
)
def test_indefinite_agentless_passive_declines_shape_and_lemma_neighbours(
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
    assert (
        "semantic/passive-indefinite-theme-agent-omitted"
        not in semantic_sources
    )


def test_indefinite_passive_with_named_agent_projects_a_complete_graph(
    cogs_project,
) -> None:
    text = "A zephyrstone was appreciated by Neris."
    result = solve(text, cogs_project.registry, tracing=False)
    got = project_result(result, text, cogs_project.registry)
    expected = parse_cogs_logical_form(
        "zephyrstone(x_1) AND appreciate.theme(x_3,x_1) "
        "AND appreciate.agent(x_3,Neris)"
    )
    assert got.node_keys() == expected.node_keys()
    assert got.edge_keys() == expected.edge_keys()
    assert ("role", "x3", "x1", "theme") in got.edge_keys()
    assert ("role", "x3", "const:neris", "agent") in got.edge_keys()

    nodes = list(result.store.by_kind(SemanticGraphNode))
    edges = list(result.store.by_kind(SemanticGraphEdge))
    assert len(nodes) == 3
    assert len(edges) == 4
    assert {fact.provenance.source for fact in nodes + edges} == {
        "semantic/passive-indefinite-theme-name-agent"
    }
    assert {
        (fact.span_start, fact.span_end) for fact in nodes
    } == {("1", "1"), ("3", "3"), ("5", "5")}


def test_expressed_agent_passive_leaves_agentless_minimal_pair_unchanged(
    cogs_project,
) -> None:
    text = "A zephyrstone was appreciated."
    result = solve(text, cogs_project.registry, tracing=False)
    semantic_sources = {
        fact.provenance.source
        for fact in (
            list(result.store.by_kind(SemanticGraphNode))
            + list(result.store.by_kind(SemanticGraphEdge))
        )
    }
    assert semantic_sources == {
        "semantic/passive-indefinite-theme-agent-omitted"
    }


@pytest.mark.parametrize(
    "text",
    [
        "A zephyrstone was appreciated by a pilot.",
        "A zephyrstone was appreciated by the Neris.",
        "The zephyrstone was appreciated by Neris.",
        "Neris was appreciated by Mira.",
        "Neris appreciated a zephyrstone.",
        "Zephyrstones were appreciated by Neris.",
        "A zephyrstone was cooked by Neris.",
        "A zephyrstone was frozen by Neris.",
        "A zephyrstone is appreciated by Neris.",
        "A zephyrstone was appreciated to Mira by Neris.",
        "A zephyrstone was appreciated by Neris near Mira.",
        "A zephyrstone was appreciated by Neris and Mira.",
        "A zephyrstone was not appreciated by Neris.",
        "Mira said that a zephyrstone was appreciated by Neris.",
    ],
)
def test_named_agent_passive_declines_shape_and_lemma_neighbours(
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
    assert (
        "semantic/passive-indefinite-theme-name-agent"
        not in semantic_sources
    )


def test_prepositional_dative_projects_a_complete_graph(
    cogs_project,
) -> None:
    text = "Neris gave a zephyrstone to Mira."
    result = solve(text, cogs_project.registry, tracing=False)
    got = project_result(result, text, cogs_project.registry)
    expected = parse_cogs_logical_form(
        "give.agent(x_1,Neris) AND give.theme(x_1,x_3) "
        "AND zephyrstone(x_3) AND give.recipient(x_1,Mira)"
    )
    assert got.node_keys() == expected.node_keys()
    assert got.edge_keys() == expected.edge_keys()
    assert ("role", "x1", "const:neris", "agent") in got.edge_keys()
    assert ("role", "x1", "x3", "theme") in got.edge_keys()
    assert ("role", "x1", "const:mira", "recipient") in got.edge_keys()

    nodes = list(result.store.by_kind(SemanticGraphNode))
    edges = list(result.store.by_kind(SemanticGraphEdge))
    assert len(nodes) == 4
    assert len(edges) == 5
    assert {fact.provenance.source for fact in nodes + edges} == {
        "semantic/ditransitive-name-indefinite-theme-to-name"
    }
    assert {
        (fact.span_start, fact.span_end) for fact in nodes
    } == {("0", "0"), ("1", "1"), ("3", "3"), ("5", "5")}


@pytest.mark.parametrize(
    "text",
    [
        "Neris gave Mira a zephyrstone.",
        "Neris gave a zephyrstone.",
        "Neris gave a zephyrstone to a pilot.",
        "Neris gave a zephyrstone to the pilot.",
        "A pilot gave a zephyrstone to Mira.",
        "Neris gave the zephyrstone to Mira.",
        "Neris gave Mira to Lio.",
        "A zephyrstone was given to Mira by Neris.",
        "Neris gave a zephyrstone near Mira to Lio.",
        "Neris gave a zephyrstone to Mira near Lio.",
        "Neris gave a zephyrstone to Mira and Lio.",
        "Neris did not give a zephyrstone to Mira.",
        "Lio said that Neris gave a zephyrstone to Mira.",
        "Neris lended a zephyrstone to Mira.",
    ],
)
def test_prepositional_dative_declines_alternation_and_shape_neighbours(
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
    assert (
        "semantic/ditransitive-name-indefinite-theme-to-name"
        not in semantic_sources
    )


def test_definite_agentless_passive_projects_a_complete_graph(
    cogs_project,
) -> None:
    text = "The zephyrstone was appreciated."
    result = solve(text, cogs_project.registry, tracing=False)
    got = project_result(result, text, cogs_project.registry)
    expected = parse_cogs_logical_form(
        "* zephyrstone(x_1); appreciate.theme(x_3,x_1)"
    )
    assert got.node_keys() == expected.node_keys()
    assert got.edge_keys() == expected.edge_keys()
    assert ("definite", "x1", "", "") in got.edge_keys()
    assert ("role", "x3", "x1", "theme") in got.edge_keys()
    assert not any(
        edge[0] == "role" and edge[3] == "agent"
        for edge in got.edge_keys()
    )

    nodes = list(result.store.by_kind(SemanticGraphNode))
    edges = list(result.store.by_kind(SemanticGraphEdge))
    assert len(nodes) == 2
    assert len(edges) == 4
    assert {fact.provenance.source for fact in nodes + edges} == {
        "semantic/passive-definite-theme-agent-omitted"
    }
    definite = next(edge for edge in edges if edge.kind == "definite")
    assert (definite.span_start, definite.span_end) == ("0", "1")


def test_definite_passive_leaves_indefinite_minimal_pair_unchanged(
    cogs_project,
) -> None:
    text = "A zephyrstone was appreciated."
    result = solve(text, cogs_project.registry, tracing=False)
    semantic_sources = {
        fact.provenance.source
        for fact in (
            list(result.store.by_kind(SemanticGraphNode))
            + list(result.store.by_kind(SemanticGraphEdge))
        )
    }
    assert semantic_sources == {
        "semantic/passive-indefinite-theme-agent-omitted"
    }


@pytest.mark.parametrize(
    "text",
    [
        "Neris was appreciated.",
        "Zephyrstones were appreciated.",
        "The zephyrstone was appreciated by Neris.",
        "The zephyrstone was given to Mira.",
        "The bright zephyrstone was appreciated.",
        "The zephyrstone beacon was appreciated.",
        "The zephyrstone was appreciated near Mira.",
        "The zephyrstone was appreciated and admired.",
        "The zephyrstone was not appreciated.",
        "The zephyrstone is appreciated.",
        "Neris appreciated the zephyrstone.",
        "Mira said that the zephyrstone was appreciated.",
        "The zephyrstone was cooked.",
        "The zephyrstone was frozen.",
    ],
)
def test_definite_passive_declines_identity_and_shape_neighbours(
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
    assert (
        "semantic/passive-definite-theme-agent-omitted"
        not in semantic_sources
    )


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
