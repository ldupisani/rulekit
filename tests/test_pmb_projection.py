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
from rulekit.kernel.model import SemanticGraphEdge, SemanticGraphNode


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


def test_pmb_indefinite_common_agent_projects_complete_graph() -> None:
    text = "A zephyrstone buzzes."
    project = load_project(Path("projects/pmb"))
    result = solve(text, project.registry, tracing=False)
    graph = project_result(
        result, text, project.registry, allow_legacy_bridge=False
    )
    assert graph.node_keys() == {
        ("x1", "entity"),
        ("x2", "event"),
    }
    assert graph.edge_keys() == {
        ("type", "x1", "", "zephyrstone"),
        ("event", "x2", "", "buzz"),
        ("role", "x2", "x1", "agent"),
    }
    assert {edge.evidence_source for edge in graph.edges} == {
        "semantic/intransitive-indefinite-common-agent"
    }


@pytest.mark.parametrize(
    "text",
    [
        "The zephyrstone buzzes.",
        "Zephyrstones buzzes.",
        "Neris buzzes.",
        "Someone buzzes.",
        "Zephyrstone buzzes.",
        "A zephyrstone might buzzes.",
        "A zephyrstone is buzzes.",
        "A zephyrstone does not buzzes.",
        "A zephyrstone buzzes loudly.",
        "A zephyrstone buzzes near Neris.",
        "A zephyrstone buzzes a bell.",
        "A zephyrstone buzzes and smiles.",
    ],
)
def test_pmb_indefinite_common_agent_rejects_neighbouring_shapes(
    text: str,
) -> None:
    project = load_project(Path("projects/pmb"))
    result = solve(text, project.registry, tracing=False)
    assert project_result(
        result, text, project.registry, allow_legacy_bridge=False
    ).empty


def test_pmb_indefinite_common_agent_membership_is_dormant_in_cogs() -> None:
    text = "A zephyrstone buzzes."
    project = load_project(Path("projects/cogs"))
    result = solve(text, project.registry, tracing=False)
    assert project_result(result, text, project.registry).empty


@pytest.mark.parametrize(
    ("text", "gender"),
    [
        ("Neris smiled.", "male"),
        ("Alice sneezed.", "female"),
    ],
)
def test_pmb_typed_name_simple_past_agent_projects_complete_graph(
    text: str,
    gender: str,
) -> None:
    project = load_project(Path("projects/pmb"))
    result = solve(text, project.registry, tracing=False)
    graph = project_result(
        result, text, project.registry, allow_legacy_bridge=False
    )
    name = text.split()[0].casefold()
    event = text.split()[1].removesuffix(".")
    event = project.registry.verb_lemmas[event]
    assert graph.node_keys() == {
        (f"const:{name}", "entity"),
        ("x0", "entity"),
        ("x1", "event"),
    }
    assert graph.edge_keys() == {
        ("type", f"const:{name}", "", gender),
        ("type", "x0", "", "time"),
        ("event", "x1", "", event),
        ("role", "x1", f"const:{name}", "agent"),
    }
    expected_source = f"semantic/intransitive-{gender}-name-simple-past-agent"
    assert {edge.evidence_source for edge in graph.edges} == {expected_source}


@pytest.mark.parametrize(
    "text",
    [
        "He smiled.",
        "Everybody smiled.",
        "A zephyrstone smiled.",
        "The zephyrstone smiled.",
        "Neris danced.",
        "Neris smiles.",
        "Neris was smiling.",
        "Neris might smile.",
        "Neris did not smile.",
        "Neris smiled loudly.",
        "Neris smiled near Alice.",
        "Neris smiled a smile.",
        "Neris smiled and sneezed.",
        "Did Neris smile?",
        "Alice said Neris smiled.",
        "Orin smiled.",
        "Neris laughed.",
    ],
)
def test_pmb_typed_name_simple_past_agent_rules_reject_neighbours(
    text: str,
) -> None:
    project = load_project(Path("projects/pmb"))
    result = solve(text, project.registry, tracing=False)
    facts = (
        list(result.store.by_kind(SemanticGraphNode))
        + list(result.store.by_kind(SemanticGraphEdge))
    )
    assert not any(
        fact.provenance.source
        in {
            "semantic/intransitive-male-name-simple-past-agent",
            "semantic/intransitive-female-name-simple-past-agent",
        }
        for fact in facts
    )


def test_pmb_typed_name_rules_are_dormant_in_cogs() -> None:
    text = "Neris smiled."
    project = load_project(Path("projects/cogs"))
    result = solve(text, project.registry, tracing=False)
    graph = project_result(result, text, project.registry)
    assert ("event", "x1", "", "smile") in graph.edge_keys()
    assert not any(
        edge.kind == "type" and edge.label in {"male", "female", "time"}
        for edge in graph.edges
    )


@pytest.mark.parametrize(
    ("text", "subject_ref", "subject_type", "source"),
    [
        (
            "Neris reserved a zephyrstone.",
            "const:neris",
            "male",
            "semantic/transitive-male-name-simple-past-indefinite-theme",
        ),
        (
            "He reserved a zephyrstone.",
            "x0",
            "male",
            "semantic/transitive-male-pronoun-simple-past-indefinite-theme",
        ),
        (
            "She reserved a zephyrstone.",
            "x0",
            "female",
            "semantic/transitive-female-pronoun-simple-past-indefinite-theme",
        ),
        (
            "We reserved a zephyrstone.",
            "x0",
            "person",
            "semantic/transitive-person-pronoun-simple-past-indefinite-theme",
        ),
    ],
)
def test_pmb_typed_subject_past_transitive_projects_complete_graph(
    text: str,
    subject_ref: str,
    subject_type: str,
    source: str,
) -> None:
    project = load_project(Path("projects/pmb"))
    result = solve(text, project.registry, tracing=False)
    graph = project_result(
        result, text, project.registry, allow_legacy_bridge=False
    )
    assert graph.node_keys() == {
        (subject_ref, "entity"),
        ("x1", "event"),
        ("x3", "entity"),
        ("x99", "entity"),
    }
    assert graph.edge_keys() == {
        ("type", subject_ref, "", subject_type),
        ("event", "x1", "", "reserve"),
        ("type", "x3", "", "zephyrstone"),
        ("type", "x99", "", "time"),
        ("role", "x1", subject_ref, "agent"),
        ("role", "x1", "x3", "theme"),
    }
    assert {edge.evidence_source for edge in graph.edges} == {source}


@pytest.mark.parametrize(
    "text",
    [
        "A zephyrstone reserved a chair.",
        "Everybody reserved a chair.",
        "Orin reserved a chair.",
        "Neris reserved the chair.",
        "Neris reserved chairs.",
        "Neris reserved Alice.",
        "Neris reserved a wooden chair.",
        "Neris danced a chair.",
        "Neris reserves a chair.",
        "Neris was reserving a chair.",
        "Neris might reserve a chair.",
        "Neris did not reserve a chair.",
        "Neris reserved a chair for Alice.",
        "Neris reserved a chair quickly.",
        "Neris reserved a chair and smiled.",
        "Did Neris reserve a chair?",
        "Alice said Neris reserved a chair.",
    ],
)
def test_pmb_typed_subject_past_transitive_rejects_neighbours(
    text: str,
) -> None:
    project = load_project(Path("projects/pmb"))
    result = solve(text, project.registry, tracing=False)
    facts = (
        list(result.store.by_kind(SemanticGraphNode))
        + list(result.store.by_kind(SemanticGraphEdge))
    )
    assert not any(
        fact.provenance.source.startswith("semantic/transitive-")
        and fact.provenance.source.endswith("-simple-past-indefinite-theme")
        for fact in facts
    )


def test_pmb_past_transitive_categories_are_dormant_in_cogs() -> None:
    text = "Neris reserved a zephyrstone."
    project = load_project(Path("projects/cogs"))
    result = solve(text, project.registry, tracing=False)
    facts = (
        list(result.store.by_kind(SemanticGraphNode))
        + list(result.store.by_kind(SemanticGraphEdge))
    )
    assert not any(
        fact.provenance.source.startswith("semantic/transitive-")
        and fact.provenance.source.endswith("-simple-past-indefinite-theme")
        for fact in facts
    )
