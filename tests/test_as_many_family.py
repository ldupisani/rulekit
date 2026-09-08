"""One comparison grammar supports two explicit endpoint layouts."""

from dataclasses import replace

import pytest

from rulekit.data.project import load_project
from rulekit.generation import generate_candidate
from rulekit.kernel.engine import solve
from rulekit.kernel.facts import FactStore
from rulekit.kernel.model import Provenance, Quantity, Relation


FORMS = [
    ("as-many", "as many", 40),
    ("times-as-many", "twice as many", 80),
    ("fraction-as-many", "half as many", 20),
    ("affine-times-as-many", "3 fewer than twice as many", 77),
    ("affine-fraction-as-many", "3 fewer than half as many", 17),
]


def rule_id(form, layout):
    if layout == "holders":
        return "arithmetic/" + form
    if form == "affine-fraction-as-many":
        return "arithmetic/affine-fraction-qualified-measures"
    return "arithmetic/" + form + "-qualified-measures"


@pytest.fixture(scope="module")
def project():
    return load_project("projects/curated")


@pytest.mark.parametrize("form,phrase,expected", FORMS)
@pytest.mark.parametrize("layout", ["holders", "items"])
@pytest.mark.parametrize("addition", ["", "also "])
def test_comparison_matrix_preserves_endpoints(project, form, phrase, expected, layout, addition):
    if layout == "holders":
        text = (f"Dena has 40 balls. Cato {addition}has {phrase} balls as Dena. "
                "How many balls does Cato have?")
    else:
        text = (f"Cato has 40 red balls. He {addition}has {phrase} blue balls as red balls. "
                "How many balls does Cato have?")
    result = solve(text, project.registry)
    assert result.answer.committed, result.answer.reason
    assert result.value == expected + (40 if layout == "items" else 0)
    relation, = result.store.by_kind(Relation)
    assert relation.provenance.source == rule_id(form, layout)
    if layout == "holders":
        assert (relation.subject, relation.standard, relation.measure) == ("cato", "dena", "ball")
        assert relation.measure_qualifier is relation.standard_qualifier is None
    else:
        assert (relation.subject, relation.standard, relation.measure) == ("cato", "ball", "ball")
        assert (relation.measure_qualifier, relation.standard_qualifier) == ("blue", "red")


@pytest.mark.parametrize("form,phrase,_", FORMS)
@pytest.mark.parametrize("standard", ["blue balls", "red coats", "Dena's red balls", "20 red balls"])
def test_item_layout_never_borrows_an_incompatible_endpoint(project, form, phrase, _, standard):
    result = solve(f"Cato has {phrase} blue balls as {standard}.", project.registry)
    assert not any(r.provenance.source == rule_id(form, "items") for r in result.store.by_kind(Relation))


@pytest.mark.parametrize("form,phrase,_", FORMS)
def test_unresolved_type_prevents_a_partial_total(project, form, phrase, _):
    result = solve(
        f"Cato has 40 green balls. Cato has {phrase} blue balls as red balls. "
        "How many balls does Cato have?", project.registry,
    )
    assert not result.answer.committed


@pytest.mark.parametrize("form,phrase,_", FORMS)
@pytest.mark.parametrize("holder", ["Dena's teacher", "the tall teacher", "teacher B"])
def test_item_layout_cannot_drop_holder_scope(project, form, phrase, _, holder):
    result = solve(f"{holder} has {phrase} blue balls as red balls.", project.registry)
    assert not any(r.provenance.source == rule_id(form, "items") for r in result.store.by_kind(Relation))


@pytest.mark.parametrize("form,_,expected", FORMS)
@pytest.mark.parametrize("layout", ["holders", "items"])
def test_compiled_variants_generate_and_link_to_editable_sources(project, form, _, expected, layout):
    target = rule_id(form, layout)
    candidate = generate_candidate(project, rule_id=target, seed=17)
    assert candidate.target_status == "matched"
    assert target in {m.rule_id for m in candidate.actual_matches}
    rule = next(r for r in project.registry.rules if r.id == target)
    source = project.source_index
    ref = source.rules[target]
    lines = ref.path.read_text().splitlines()
    assert target in lines[ref.line - 1]
    for index in range(len(rule.match["sentence"])):
        token_ref = source.rule_tokens[(target, index)]
        assert token_ref.line > 1
        assert "parameter:" not in lines[token_ref.line - 1]


def test_equal_qualified_holdings_are_not_deduplicated():
    store = FactStore()
    red = Quantity(provenance=Provenance("invented", 0), entity="cato", measure="ball",
                   value=12, verb="have", measure_qualifier="red")
    for color in ["red", "blue", "green"]:
        assert store.admit(replace(red, measure_qualifier=color))
    facts = store.by_kind(Quantity)
    assert len(facts) == 3
    assert {f.measure for f in facts} == {"ball[red]", "ball[blue]", "ball[green]"}
    # Repeating the same subtype still deduplicates; it is not a new count.
    store.admit(red)
    assert len(store.by_kind(Quantity)) == 3
    assert store.clean


def test_unqualified_total_is_not_an_additional_equal_subtype():
    result = solve(
        "Cato has 12 balls. Cato has 12 red balls. How many balls does Cato have?",
        load_project("projects/curated").registry,
    )
    # Complete-accounting may decline the redundant text; it must never sum
    # the whole and its subtype as two separate groups.
    assert result.value in (None, 12)
    assert len(result.store.by_kind(Quantity)) == 1
