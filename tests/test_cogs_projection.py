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


def _abstract_role_topology(graph: ProjectionGraph) -> set[tuple]:
    event_labels = {
        edge.source: edge.label
        for edge in graph.edges
        if edge.kind == "event"
    }
    type_labels = {
        edge.source: edge.label
        for edge in graph.edges
        if edge.kind == "type"
    }

    def abstract(ref: str) -> tuple[str, str]:
        if ref in event_labels:
            return ("event", event_labels[ref])
        if ref in type_labels:
            return ("entity", type_labels[ref])
        if ref.startswith("const:"):
            return ("constant", ref.removeprefix("const:"))
        return ("", "")

    return {
        (edge.kind, abstract(edge.source), abstract(edge.target), edge.label)
        for edge in graph.edges
    }


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


def test_active_definite_common_subject_projects_a_complete_graph(
    cogs_project,
) -> None:
    text = "The zephyrstone appreciated a zephyrstone."
    result = solve(text, cogs_project.registry, tracing=False)
    got = project_result(result, text, cogs_project.registry)
    expected = parse_cogs_logical_form(
        "* zephyrstone(x_1); appreciate.agent(x_2,x_1) "
        "AND appreciate.theme(x_2,x_4) AND zephyrstone(x_4)"
    )
    assert got.node_keys() == expected.node_keys()
    assert got.edge_keys() == expected.edge_keys()
    assert ("definite", "x1", "", "") in got.edge_keys()
    assert ("definite", "x4", "", "") not in got.edge_keys()
    assert {("x1", "entity"), ("x4", "entity")} <= got.node_keys()

    nodes = list(result.store.by_kind(SemanticGraphNode))
    edges = list(result.store.by_kind(SemanticGraphEdge))
    assert len(nodes) == 3
    assert len(edges) == 6
    assert {fact.provenance.source for fact in nodes + edges} == {
        "semantic/active-definite-agent-indefinite-theme"
    }


@pytest.mark.parametrize(
    "text",
    [
        "A zephyrstone appreciated a zephyrstone.",
        "Neris appreciated a zephyrstone.",
        "The zephyrstones appreciated a zephyrstone.",
        "The zephyrstone appreciated the zephyrstone.",
        "The zephyrstone appreciated Neris.",
        "The zephyrstone gave Mira a zephyrstone.",
        "The zephyrstone appreciated a zephyrstone beside a table.",
        "The zephyrstone hoped that Neris smiled.",
        "The zephyrstone did not appreciate a zephyrstone.",
        "The zephyrstone appreciated a zephyrstone and a cloud.",
        "The zephyrstone appreciated a zephyrstone",
    ],
)
def test_active_definite_common_subject_declines_shape_neighbours(
    cogs_project,
    text: str,
) -> None:
    result = solve(text, cogs_project.registry, tracing=False)
    assert "semantic/active-definite-agent-indefinite-theme" not in {
        fact.provenance.source
        for fact in (
            list(result.store.by_kind(SemanticGraphNode))
            + list(result.store.by_kind(SemanticGraphEdge))
        )
    }


def test_active_indefinite_common_subject_projects_a_complete_graph(
    cogs_project,
) -> None:
    text = "A zephyrstone appreciated a zephyrstone."
    result = solve(text, cogs_project.registry, tracing=False)
    got = project_result(result, text, cogs_project.registry)
    expected = parse_cogs_logical_form(
        "zephyrstone(x_1) AND appreciate.agent(x_2,x_1) "
        "AND appreciate.theme(x_2,x_4) AND zephyrstone(x_4)"
    )
    assert got.node_keys() == expected.node_keys()
    assert got.edge_keys() == expected.edge_keys()
    assert not any(edge.kind == "definite" for edge in got.edges)
    assert {("x1", "entity"), ("x4", "entity")} <= got.node_keys()

    nodes = list(result.store.by_kind(SemanticGraphNode))
    edges = list(result.store.by_kind(SemanticGraphEdge))
    assert len(nodes) == 3
    assert len(edges) == 5
    assert {fact.provenance.source for fact in nodes + edges} == {
        "semantic/active-indefinite-agent-indefinite-theme"
    }


@pytest.mark.parametrize(
    "text",
    [
        "The zephyrstone appreciated a zephyrstone.",
        "Neris appreciated a zephyrstone.",
        "Zephyrstones appreciated a zephyrstone.",
        "A zephyrstone appreciated the zephyrstone.",
        "A zephyrstone appreciated Neris.",
        "A zephyrstone gave Mira a zephyrstone.",
        "A zephyrstone appreciated a zephyrstone beside a table.",
        "A zephyrstone hoped that Neris smiled.",
        "A zephyrstone did not appreciate a zephyrstone.",
        "A zephyrstone appreciated a zephyrstone and a cloud.",
        "A zephyrstone appreciated a zephyrstone",
    ],
)
def test_active_indefinite_common_subject_declines_shape_neighbours(
    cogs_project,
    text: str,
) -> None:
    result = solve(text, cogs_project.registry, tracing=False)
    assert "semantic/active-indefinite-agent-indefinite-theme" not in {
        fact.provenance.source
        for fact in (
            list(result.store.by_kind(SemanticGraphNode))
            + list(result.store.by_kind(SemanticGraphEdge))
        )
    }


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


@pytest.mark.parametrize("depth", [1, 2, 3, 4])
def test_nominal_modifier_chain_uses_one_rule_at_multiple_depths(
    cogs_project,
    depth: int,
) -> None:
    prepositions = ["beside", "on", "in", "beside"]
    text = "Neris admired a zephyrstone"
    logical_form = [
        "admire.agent(x_1,Neris)",
        "admire.theme(x_1,x_3)",
        "zephyrstone(x_3)",
    ]
    source = 3
    for index, preposition in enumerate(prepositions[:depth]):
        target = 6 + index * 3
        text += f" {preposition} a zephyrstone"
        logical_form.extend([
            f"zephyrstone.nmod.{preposition}(x_{source},x_{target})",
            f"zephyrstone(x_{target})",
        ])
        source = target
    text += "."

    result = solve(text, cogs_project.registry, tracing=False)
    got = project_result(result, text, cogs_project.registry)
    expected = parse_cogs_logical_form(" AND ".join(logical_form))
    assert got.node_keys() == expected.node_keys()
    assert got.edge_keys() == expected.edge_keys()
    assert len([edge for edge in got.edges if edge.kind == "modifier"]) == depth
    assert result.document is not None
    assert result.document.rounds == 1


def test_recursive_modifier_links_retain_local_attachment_provenance(
    cogs_project,
) -> None:
    text = (
        "Neris admired a zephyrstone beside a zephyrstone "
        "on a zephyrstone in a zephyrstone beside a zephyrstone."
    )
    result = solve(text, cogs_project.registry, tracing=False)
    modifiers = [
        fact
        for fact in result.store.by_kind(SemanticGraphEdge)
        if fact.kind == "modifier"
    ]
    assert len(modifiers) == 4
    assert {fact.provenance.source for fact in modifiers} == {
        "semantic/nominal-modifier-chain-link"
    }
    assert {
        (fact.source, fact.target, fact.label) for fact in modifiers
    } == {
        ("entity:3", "entity:6", "beside"),
        ("entity:6", "entity:9", "on"),
        ("entity:9", "entity:12", "in"),
        ("entity:12", "entity:15", "beside"),
    }
    assert {
        (fact.span_start, fact.span_end) for fact in modifiers
    } == {("3", "6"), ("6", "9"), ("9", "12"), ("12", "15")}


@pytest.mark.parametrize(
    "text",
    [
        "Neris admired a zephyrstone beside the zephyrstone on a zephyrstone.",
        "Neris admired a zephyrstone near a zephyrstone on a zephyrstone.",
        "Neris admired a zephyrstone beside Mira on a zephyrstone.",
        "Neris admired a zephyrstone beside a zephyrstone and a zephyrstone.",
        "Neris did not admire a zephyrstone beside a zephyrstone.",
        "A zephyrstone was admired beside a zephyrstone by Neris.",
        "Neris missed a zephyrstone beside a zephyrstone.",
        "Neris hoped that Mira admired a zephyrstone beside a zephyrstone.",
    ],
)
def test_modifier_chain_root_declines_unlicensed_neighbours(
    cogs_project,
    text: str,
) -> None:
    result = solve(text, cogs_project.registry, tracing=False)
    sources = {
        fact.provenance.source
        for fact in (
            list(result.store.by_kind(SemanticGraphNode))
            + list(result.store.by_kind(SemanticGraphEdge))
        )
    }
    assert "semantic/active-name-indefinite-theme-modifier-chain-root" not in (
        sources
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


def test_subject_control_xcomp_projects_explicit_shared_agent(
    cogs_project,
) -> None:
    text = "Neris hoped to smirk."
    result = solve(text, cogs_project.registry, tracing=False)
    got = project_result(result, text, cogs_project.registry)
    expected = parse_cogs_logical_form(
        "hope.agent(x_1,Neris) AND hope.xcomp(x_1,x_3) "
        "AND smirk.agent(x_3,Neris)"
    )
    assert got.node_keys() == expected.node_keys()
    assert got.edge_keys() == expected.edge_keys()
    assert ("complement", "x1", "x3", "xcomp") in got.edge_keys()

    nodes = list(result.store.by_kind(SemanticGraphNode))
    edges = list(result.store.by_kind(SemanticGraphEdge))
    assert len(nodes) == 3
    assert len(edges) == 5
    assert {fact.provenance.source for fact in nodes + edges} == {
        "semantic/xcomp-name-agent-shared-agent"
    }
    agent_edges = [fact for fact in edges if fact.kind == "role"]
    assert {
        (edge.source, edge.target, edge.label) for edge in agent_edges
    } == {
        ("event:1", "name:neris", "agent"),
        ("event:3", "name:neris", "agent"),
    }
    complement = next(fact for fact in edges if fact.kind == "complement")
    assert (complement.source, complement.target, complement.label) == (
        "event:1",
        "event:3",
        "xcomp",
    )
    assert (complement.span_start, complement.span_end) == ("1", "3")


@pytest.mark.parametrize(
    "text",
    [
        "Neris hoped Mira smirked.",
        "Neris hoped that Mira smirked.",
        "A pilot hoped to smirk.",
        "The pilot hoped to smirk.",
        "Neris hoped smirk.",
        "Neris hoped to redden.",
        "Neris hoped to admire a zephyrstone.",
        "Neris persuaded Mira to smirk.",
        "Neris hoped to smirk and sneeze.",
        "Neris did not hope to smirk.",
        "Neris hoped to want to smirk.",
        "Neris hoped to smirk beside Mira.",
        "Neris expected Mira to smirk.",
        "Neris planned to nap.",
        "Neris tried to call Mira.",
    ],
)
def test_subject_control_xcomp_declines_neighbouring_control_shapes(
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
    assert "semantic/xcomp-name-agent-shared-agent" not in semantic_sources


@pytest.mark.parametrize("ccomp_depth", [1, 2, 3])
def test_nested_complement_chain_uses_local_rules_at_multiple_depths(
    cogs_project,
    ccomp_depth: int,
) -> None:
    names = ["Neris", "Mira", "Lio", "Tavi"]
    text_parts = [names[0], "hoped"]
    logical_form = []
    event_positions = [1 + 3 * index for index in range(ccomp_depth + 1)]
    for index in range(ccomp_depth):
        text_parts.extend(["that", names[index + 1], "hoped"])
        logical_form.extend([
            f"hope.agent(x_{event_positions[index]},{names[index]})",
            (
                f"hope.ccomp(x_{event_positions[index]},"
                f"x_{event_positions[index + 1]})"
            ),
        ])
    # Replace the final repeated ccomp matrix with the terminal xcomp matrix.
    text_parts[-1] = "wanted"
    controller = names[ccomp_depth]
    terminal_event = event_positions[-1]
    infinitive_event = terminal_event + 2
    text_parts.extend(["to", "smirk"])
    logical_form.extend([
        f"want.agent(x_{terminal_event},{controller})",
        f"want.xcomp(x_{terminal_event},x_{infinitive_event})",
        f"smirk.agent(x_{infinitive_event},{controller})",
    ])
    text = " ".join(text_parts) + "."

    result = solve(text, cogs_project.registry, tracing=False)
    got = project_result(result, text, cogs_project.registry)
    expected = parse_cogs_logical_form(" AND ".join(logical_form))
    assert got.node_keys() == expected.node_keys()
    assert got.edge_keys() == expected.edge_keys()
    assert len([edge for edge in got.edges if edge.kind == "complement"]) == (
        ccomp_depth + 1
    )
    assert result.document is not None
    assert result.document.rounds == 1


def test_nested_complement_edges_retain_local_direction_and_provenance(
    cogs_project,
) -> None:
    text = (
        "Neris hoped that Mira hoped that Lio hoped "
        "that Tavi wanted to smirk."
    )
    result = solve(text, cogs_project.registry, tracing=False)
    complements = [
        fact
        for fact in result.store.by_kind(SemanticGraphEdge)
        if fact.kind == "complement"
    ]
    assert {
        (fact.source, fact.target, fact.label) for fact in complements
    } == {
        ("event:1", "event:4", "ccomp"),
        ("event:4", "event:7", "ccomp"),
        ("event:7", "event:10", "ccomp"),
        ("event:10", "event:12", "xcomp"),
    }
    assert {
        fact.provenance.source for fact in complements if fact.label == "ccomp"
    } == {"semantic/z-complement-chain-ccomp-link"}
    assert {
        fact.provenance.source for fact in complements if fact.label == "xcomp"
    } == {"semantic/z-complement-chain-xcomp-terminal"}


@pytest.mark.parametrize(
    "text",
    [
        "Neris hoped Mira wanted to smirk.",
        "A pilot hoped that Mira wanted to smirk.",
        "Neris hoped that a pilot wanted to smirk.",
        "Neris hoped that the pilot wanted to smirk.",
        "Neris said that Mira wanted to smirk.",
        "Neris did not hope that Mira wanted to smirk.",
    ],
)
def test_nested_ccomp_link_declines_unlicensed_outer_neighbours(
    cogs_project,
    text: str,
) -> None:
    result = solve(text, cogs_project.registry, tracing=False)
    sources = {
        fact.provenance.source
        for fact in (
            list(result.store.by_kind(SemanticGraphNode))
            + list(result.store.by_kind(SemanticGraphEdge))
        )
    }
    assert "semantic/z-complement-chain-ccomp-link" not in sources


@pytest.mark.parametrize(
    "text",
    [
        "Neris hoped that Mira wanted smirk.",
        "Neris hoped that Mira wanted to redden.",
        "Neris hoped that Mira persuaded Lio to smirk.",
        "Neris hoped that Mira wanted to nap.",
    ],
)
def test_nested_xcomp_terminal_declines_unlicensed_control_neighbours(
    cogs_project,
    text: str,
) -> None:
    result = solve(text, cogs_project.registry, tracing=False)
    sources = {
        fact.provenance.source
        for fact in (
            list(result.store.by_kind(SemanticGraphNode))
            + list(result.store.by_kind(SemanticGraphEdge))
        )
    }
    assert "semantic/z-complement-chain-xcomp-terminal" not in sources


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


def test_active_and_passive_surfaces_share_one_role_topology(
    cogs_project,
) -> None:
    active_text = "Neris appreciated a zephyrstone."
    passive_text = "A zephyrstone was appreciated by Neris."
    active = project_result(
        solve(active_text, cogs_project.registry, tracing=False),
        active_text,
        cogs_project.registry,
    )
    passive = project_result(
        solve(passive_text, cogs_project.registry, tracing=False),
        passive_text,
        cogs_project.registry,
    )
    assert _abstract_role_topology(active) == _abstract_role_topology(passive)


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


def test_proper_direct_object_remains_theme_not_recipient(
    cogs_project,
) -> None:
    text = "Neris gave Mira."
    result = solve(text, cogs_project.registry, tracing=False)
    got = project_result(result, text, cogs_project.registry)
    expected = parse_cogs_logical_form(
        "give.agent(x_1,Neris) AND give.theme(x_1,Mira)"
    )
    assert got.node_keys() == expected.node_keys()
    assert got.edge_keys() == expected.edge_keys()
    assert not any(
        edge.kind == "role" and edge.label == "recipient"
        for edge in got.edges
    )


@pytest.mark.parametrize(
    "text",
    [
        "Neris gave Mira a zephyrstone.",
        "Neris sold Mira a zephyrstone.",
        "Neris passed Mira a zephyrstone.",
        "Neris gave Mira to Lio.",
    ],
)
def test_postverbal_proper_name_does_not_license_recipient_by_position(
    cogs_project,
    text: str,
) -> None:
    result = solve(text, cogs_project.registry, tracing=False)
    got = project_result(result, text, cogs_project.registry)
    assert not any(
        edge.kind == "role" and edge.label == "recipient"
        for edge in got.edges
    )
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
