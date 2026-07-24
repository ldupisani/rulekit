"""Synthetic contracts for the PMB SBN adapter and licensed builder."""

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
    _align_projection_refs,
    parse_pmb_sbn,
    project_result,
)
from rulekit.kernel.engine import solve


def _load_builder():
    path = Path("projects/pmb/build_corpus.py").resolve()
    spec = importlib.util.spec_from_file_location("pmb_build_corpus", path)
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module


def test_pmb_adapter_resolves_roles_by_synset_offset() -> None:
    graph = parse_pmb_sbn(
        "navigator.n.01 shimmer.v.01 Agent -1 Theme +1 "
        "artifact.n.01 transfer.v.01 Agent -3 Theme -1 Recipient +1 "
        "curator.n.01",
        document_id="synthetic/p0001",
    )
    assert ("event", "p1", "", "shimmer") in graph.edge_keys()
    assert ("role", "p1", "p0", "agent") in graph.edge_keys()
    assert ("role", "p1", "p2", "theme") in graph.edge_keys()
    assert ("role", "p3", "p4", "recipient") in graph.edge_keys()
    assert all(
        edge.evidence_source.startswith("pmb:synthetic/p0001:")
        for edge in graph.edges
    )


def test_pmb_adapter_normalizes_named_entities_and_adjectival_types() -> None:
    graph = parse_pmb_sbn(
        'person.n.01 Name "Neris Vale" gleam.v.01 Agent -1 '
        "relic.n.01 radiant.a.01 AttributeOf -1"
    )
    assert ("const:neris vale", "entity") in graph.node_keys()
    assert ("type", "const:neris vale", "", "person") in graph.edge_keys()
    assert ("role", "p1", "const:neris vale", "agent") in graph.edge_keys()
    assert ("type", "p2", "", "radiant") in graph.edge_keys()


def test_pmb_adapter_ignores_unsupported_roles_and_operators() -> None:
    graph = parse_pmb_sbn(
        "device.n.01 time.n.08 EQU now rotate.v.01 Theme -2 "
        "Time -1 Manner +1 swiftly.r.01"
    )
    assert ("role", "p2", "p0", "theme") in graph.edge_keys()
    assert not any(
        edge.kind == "role" and edge.label in {"time", "manner"}
        for edge in graph.edges
    )


def test_pmb_adapter_treats_escaping_offsets_as_constants() -> None:
    graph = parse_pmb_sbn("glow.v.01 Agent +4 object.n.01")
    assert not any(edge.kind == "role" for edge in graph.edges)


def test_pmb_adapter_leaves_unclosed_name_uncollapsed() -> None:
    graph = parse_pmb_sbn('person.n.01 Name "Neris glow.v.01 Agent -1')
    assert ("p0", "entity") in graph.node_keys()
    assert not any(node.ref.startswith("const:") for node in graph.nodes)


def test_pmb_alignment_treats_local_variable_names_as_nonsemantic() -> None:
    expected = parse_pmb_sbn(
        'person.n.01 Name "Neris" polish.v.01 Agent -1 '
        "artifact.n.01 polish.v.01 Theme -1"
    )
    got = ProjectionGraph(
        nodes=(
            ProjectionNode("const:neris", "entity"),
            ProjectionNode("x1", "event"),
            ProjectionNode("x2", "entity"),
        ),
        edges=(
            ProjectionEdge("event", "x1", label="polish"),
            ProjectionEdge("role", "x1", "const:neris", "agent"),
            ProjectionEdge("type", "x2", label="artifact"),
        ),
    )
    aligned = _align_projection_refs(got, expected)
    assert not aligned.node_keys() - expected.node_keys()
    assert not aligned.edge_keys() - expected.edge_keys()


def test_pmb_builder_parses_strict_four_line_records() -> None:
    builder = _load_builder()
    records = builder.parse_split(
        "p01/d0001\nSynthetic sentence.\n"
        "object.n.01 glow.v.01 Theme -1\n\n"
    )
    assert [(record.item_id, record.text) for record in records] == [
        ("p01/d0001", "Synthetic sentence."),
    ]
    with pytest.raises(ValueError, match="four-line"):
        builder.parse_split("p01/d0001\nSynthetic sentence.\n")


def test_pmb_project_declares_protected_test() -> None:
    project = load_project(Path("projects/pmb"))
    assert project.doc.projection is not None
    assert project.doc.projection.adapter == "pmb"
    assert not project.doc.projection.legacy_bridge
    assert all(not item.legacy_bridge for item in project.projection_items("train"))
    assert project.projection_slice_inspectable("train")
    assert project.projection_slice_inspectable("development")
    assert not project.projection_slice_inspectable("test")


@pytest.mark.parametrize(
    "text",
    [
        "Somebody giggled.",
        "Nobody snoozed.",
        "Everybody smirked.",
        "Someone sneezed.",
    ],
)
def test_indefinite_pronouns_are_not_promoted_to_sentence_initial_names(
    text: str,
) -> None:
    project = load_project(Path("projects/pmb"))
    result = solve(text, project.registry, tracing=False)
    assert project_result(
        result, text, project.registry, allow_legacy_bridge=False
    ).empty


@pytest.mark.parametrize(
    "text",
    [
        "Neris saw a zephyrstone.",
        "Neris danced.",
    ],
)
def test_pmb_role_quarantine_declines_disputed_verb_roles(text: str) -> None:
    project = load_project(Path("projects/pmb"))
    result = solve(text, project.registry, tracing=False)
    assert project_result(
        result, text, project.registry, allow_legacy_bridge=False
    ).empty


@pytest.mark.parametrize(
    "text",
    [
        "Neris saw a zephyrstone.",
        "Neris danced.",
    ],
)
def test_pmb_role_quarantine_does_not_change_cogs_projection(text: str) -> None:
    project = load_project(Path("projects/cogs"))
    result = solve(text, project.registry, tracing=False)
    assert not project_result(result, text, project.registry).empty
