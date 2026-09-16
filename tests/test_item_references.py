"""Invented forward item-class references, separate from numeric aliasing."""
from copy import deepcopy
from dataclasses import replace
import json
from pathlib import Path

import pytest

from rulekit.data.project import load_project
from rulekit.generation import generate_candidate
from rulekit.generation.reviews import _reviewed_facts_match
from rulekit.kernel.engine import solve
from rulekit.kernel.item_references import project_item_reference
from rulekit.kernel.model import Predication, Provenance, Quantity, Relation
from rulekit.kernel.patterns import match_ask
from rulekit.kernel.reference_identity import ReferenceIdentity as Ref, scope_reference_store
from rulekit.server.api import _fact_json

ROOT = Path(__file__).resolve().parents[1]


@pytest.fixture(scope="module", params=("curated", "gsm8k"))
def project(request):
    return load_project(ROOT / "projects" / request.param)


def checked(project, text, expected, rule="arithmetic/anchored-relation"):
    result = solve(text, project.registry)
    assert match_ask(result.question, project.registry) is not None
    assert any(r.provenance.source == rule for r in result.store.by_kind(Relation))
    assert result.store.by_kind(Quantity)
    assert not any("unknown word" in str(gap) for gap in result.deficiencies())
    assert result.answer.committed == (expected is not None), result.answer
    assert result.answer.value == expected, result.answer
    return result


@pytest.mark.parametrize("verb,ask", (("has", "does {who} have"), ("sold", "did {who} sell")))
@pytest.mark.parametrize("comparison,value,expected,rule", (
    ("3 more", 8, 11, "arithmetic/anchored-relation"),
    ("twice as many", 8, 16, "arithmetic/times-as-many"),
    ("3 more", 0, 3, "arithmetic/anchored-relation"),
))
@pytest.mark.parametrize("inverse", (False, True))
def test_forward_class_has_inspectable_link(project, verb, ask, comparison, value, expected, rule, inverse):
    connector = "than" if comparison == "3 more" else "as"
    target, answer_actor = ("Bira", "Aven") if inverse else ("Aven", "Bira")
    stated, answer = (expected, value) if inverse else (value, expected)
    result = checked(project,
        f"Bira {verb} {comparison} red cards {connector} Aven. "
        f"{target} {verb} {stated} cards. How many red cards {ask.format(who=answer_actor)}?", answer, rule)
    literal = next(q for q in result.store.by_kind(Quantity) if q.item_reference)
    assert literal.measure_qualifier is None and literal.value == stated
    assert literal.item_reference.item == Ref("card", qualifiers=("red",))
    assert literal.item_reference.target == literal.provenance
    assert literal.item_reference.participant == literal.entity_ref
    assert all(p.sentence < literal.provenance.sentence for p in literal.item_reference.antecedents)
    viewed = project_item_reference(literal, result.store)
    assert viewed.measure_qualifier == "red" and literal.measure_qualifier is None
    assert viewed.provenance == literal.provenance
    serialized = _fact_json(literal)
    assert isinstance(serialized["fields"]["item_reference"], dict)
    json.dumps(serialized)


@pytest.mark.parametrize("verb,ask", (("has", "does Bira have"), ("sold", "did Bira sell")))
@pytest.mark.parametrize("comparison,connector,rule", (
    ("3 more", "than", "arithmetic/anchored-relation"),
    ("twice as many", "as", "arithmetic/times-as-many"),
))
def test_later_class_never_retargets_earlier_whole(project, verb, ask, comparison, connector, rule):
    result = checked(project, f"Aven {verb} 8 cards. Bira {verb} {comparison} red cards {connector} Aven. "
                     f"How many red cards {ask}?", None, rule)
    assert not any(q.item_reference for q in result.store.by_kind(Quantity))


@pytest.mark.parametrize("verb,ask", (("has", "does Bira have"), ("sold", "did Bira sell")))
@pytest.mark.parametrize("reverse", (False, True))
def test_rival_classes_never_choose_by_recency(project, verb, ask, reverse):
    classes = [f"Bira {verb} 3 more red cards than Aven.",
               f"Cato {verb} 2 more blue cards than Aven."]
    if reverse:
        classes.reverse()
    result = checked(project, " ".join(classes) + f" Aven {verb} 8 cards. How many red cards {ask}?", None)
    assert len(result.store.by_kind(Relation)) == 2
    assert not any(q.item_reference for q in result.store.by_kind(Quantity))


@pytest.mark.parametrize("prefix", (
    "Cato sold 4 blue cards.", "Aven bought 4 blue cards.", "Aven sold 4 blue apples.",
    "Cato sold 3 more blue cards than Dena.", "Bira bought 3 more blue cards than Aven.",
))
def test_unrelated_context_does_not_choose_or_block(project, prefix):
    result = checked(project, prefix + " Bira sold 3 more red cards than Aven. "
                     "Aven sold 8 cards. How many red cards did Bira sell?", 11)
    assert sum(q.item_reference is not None for q in result.store.by_kind(Quantity)) == 1


@pytest.mark.parametrize("modifier,expected", (("red ", 11), ("blue ", None)))
def test_explicit_modifier_remains_authoritative(project, modifier, expected):
    result = checked(project, "Bira sold 3 more red cards than Aven. "
                     f"Aven sold 8 {modifier}cards. How many red cards did Bira sell?", expected)
    assert not any(q.item_reference for q in result.store.by_kind(Quantity))


@pytest.mark.parametrize("prefix", ("Aven sold cards.", "Aven sold some cards.", "Aven sold blue cards."))
def test_unquantified_prior_activity_blocks_reference(project, prefix):
    result = checked(project, "Bira sold 3 more red cards than Aven. " + prefix +
                     " Aven sold 8 cards. How many red cards did Bira sell?", None)
    assert any(p.subject == "aven" and p.dobj == "card" for p in result.store.by_kind(Predication))
    assert not any(q.item_reference for q in result.store.by_kind(Quantity))


@pytest.mark.parametrize("verb,ask,expected", (("has", "does Bira have", 7), ("sold", "did Bira sell", 11)))
def test_repeated_states_and_events_keep_their_own_arithmetic(project, verb, ask, expected):
    result = checked(project, f"Bira {verb} 3 more red cards than Aven. "
                     f"Aven {verb} 4 cards. Aven {verb} 4 cards. How many red cards {ask}?", expected)
    assert any(q.item_reference for q in result.store.by_kind(Quantity))


@pytest.mark.parametrize("tail", (
    "Cato sold 8 cards.", "Aven bought 8 cards.", "Aven sold 8 apples.",
    "Aven sold 8 cards yesterday.", "Aven will sell 8 cards.",
    "Aven sold 8 cards in total.", "Aven sold 8 cards altogether.",
))
def test_wrong_participant_predicate_scope_or_time_never_links(project, tail):
    result = checked(project, "Bira sold 3 more red cards than Aven. " + tail +
                     " How many red cards did Bira sell?", None)
    assert not any(q.item_reference for q in result.store.by_kind(Quantity))


@pytest.mark.parametrize("first", (
    "Bira sold 3 more red cards than Aven yesterday.",
))
def test_non_actual_or_explicit_time_source_never_links(project, first):
    result = checked(project, first + " Aven sold 8 cards. How many red cards did Bira sell?", None)
    assert not any(q.item_reference for q in result.store.by_kind(Quantity))


def linked_example(project):
    result = checked(project, "Bira sold 3 more red cards than Aven. Aven sold 8 cards. "
                     "How many red cards did Bira sell?", 11)
    quantity = next(q for q in result.store.by_kind(Quantity) if q.item_reference)
    return result.store, quantity


@pytest.mark.parametrize("change", (
    {"item": None}, {"item": {}}, {"participant": "aven"}, {"target": {}},
    {"antecedents": None}, {"antecedents": ({},)},
    {"item": Ref("card", qualifiers=("blue",))}, {"participant": Ref("cato")},
    {"predicate": "buy"}, {"antecedents": ()},
    {"item": Ref("card", qualifiers=(None,))},
    {"target": Provenance("invented", [])},
    {"antecedents": (Provenance("invented", []),)},
))
def test_malformed_or_forged_link_fails_closed(project, change):
    store, quantity = linked_example(project)
    changed = replace(quantity, item_reference=replace(quantity.item_reference, **change))
    store.facts[store.facts.index(quantity)] = changed
    assert not project_item_reference(changed, store).entity_ref.resolved


@pytest.mark.parametrize("change", ("source_removed", "target_removed", "rival_added", "eligibility_removed", "assumption", "future"))
def test_current_antecedent_inventory_and_reader_eligibility_required(project, change):
    store, quantity = linked_example(project)
    view = deepcopy(store)
    relation = view.by_kind(Relation)[0]
    if change == "source_removed":
        view.facts.remove(relation)
    elif change == "target_removed":
        view.facts.remove(quantity)
    elif change == "rival_added":
        view.facts.append(replace(relation, measure_qualifier="blue"))
    elif change == "eligibility_removed":
        view.item_reference_clauses = frozenset()
    else:
        changed = replace(relation.provenance, **({"assumption": True} if change == "assumption"
                                               else {"temporal_perspective": "future"}))
        view.facts[view.facts.index(relation)] = replace(relation, provenance=changed)
    assert not project_item_reference(quantity, view).entity_ref.resolved


def test_scoped_view_retains_original_proof_and_review_is_not_auto_enriched(project):
    store, quantity = linked_example(project)
    view = scope_reference_store(store, quantity.entity_ref)
    assert view.item_reference_clauses == store.item_reference_clauses
    assert quantity.item_reference is not None and quantity.measure_qualifier is None
    current = _fact_json(quantity)
    old = deepcopy(current)
    del old["fields"]["item_reference"]
    assert _reviewed_facts_match([current], [current])
    assert not _reviewed_facts_match([current], [old])


def test_strict_generated_comparison_and_qualified_boundary_round_trip(project):
    candidate = generate_candidate(project, rule_id="arithmetic/anchored-relation", seed=17,
        max_attempts=2,
        locked_bindings={"who": "Bira", "verb": "sold", "n": "3", "dir": "more",
                         "item": "cards", "std": "Aven"}, generation_mode="strict",
        structural_target="optional:5:omitted")
    assert candidate.target_status == "matched"
    assert "arithmetic/anchored-relation" in {match.rule_id for match in candidate.actual_matches}
    # The native plural slot generates atomic nouns. Exercise its strict
    # output unchanged, then an explicitly authored modifier boundary; do not
    # pretend the generator itself already composes this qualified filler.
    checked(project, candidate.sentence + " Aven sold 8 cards. How many cards did Bira sell?", 11)
    assert candidate.sentence.count("cards") == 1
    qualified = candidate.sentence.replace("cards", "red cards")
    result = checked(project, qualified + " Aven sold 8 cards. How many red cards did Bira sell?", 11)
    assert any(q.item_reference for q in result.store.by_kind(Quantity))
    json.dumps([_fact_json(fact) for fact in result.store.facts])


@pytest.mark.parametrize("actor,anchor,ask,expected", (
    ("the teacher A", "the teacher A", "the teacher B", 11),
    ("the teacher A", "the teacher C", "the teacher B", None),
    ("Aven's teacher", "Aven's teacher", "Bira's teacher", 11),
    ("Aven's teacher", "Cato's teacher", "Bira's teacher", None),
))
def test_item_class_requires_full_participant_identity(project, actor, anchor, ask, expected):
    result = checked(project, f"{ask} has 3 more red cards than {actor}. "
                     f"{anchor} has 8 cards. How many cards does {ask} have?", expected)
    assert any(q.item_reference for q in result.store.by_kind(Quantity)) == (expected is not None)


def test_earlier_bare_event_remains_unknown_subset_contribution(project):
    result = checked(project, "Aven sold 4 cards. Bira sold 3 more red cards than Aven. "
                     "Aven sold 4 cards. How many red cards did Bira sell?", None)
    stated = [q for q in result.store.by_kind(Quantity) if q.entity == "aven"]
    assert not stated[0].item_reference and stated[1].item_reference


def test_ask_only_class_does_not_supply_reference(project):
    result = checked(project, "Bira sold 3 more cards than Aven. Aven sold 8 cards. "
                     "How many red cards did Bira sell?", None)
    assert not any(q.item_reference for q in result.store.by_kind(Quantity))


def test_same_holder_item_role_is_not_a_comparison_participant(project):
    result = solve("Aven has 8 blue cards. Aven has 3 more red cards than blue cards. "
                   "Aven has 8 cards. How many red cards does Aven have?", project.registry)
    assert match_ask(result.question, project.registry) is not None
    assert any(r.standard_qualifier == "blue" for r in result.store.by_kind(Relation))
    assert not any(q.item_reference for q in result.store.by_kind(Quantity))


def test_future_comparison_is_not_an_activated_boundary(project):
    result = solve("Bira will sell 3 more red cards than Aven. Aven sold 8 cards. "
                   "How many red cards did Bira sell?", project.registry)
    assert match_ask(result.question, project.registry) is not None
    assert not result.store.by_kind(Relation)
    assert not result.answer.committed
    assert not any(q.item_reference for q in result.store.by_kind(Quantity))


def test_conditional_quantity_cannot_supply_actual_item_link(project):
    result = checked(project, "Bira sold 3 more red cards than Aven. "
        "If Aven sold 8 cards, how many red cards did Bira sell?", None)
    assert any(q.provenance.assumption for q in result.store.by_kind(Quantity))
    assert not any(q.item_reference for q in result.store.by_kind(Quantity))


@pytest.mark.parametrize("verb,ask", (("has", "does Aven have"), ("sold", "did Aven sell")))
@pytest.mark.parametrize("modifier,expected", (("", None), ("red ", 8), ("blue ", None)))
def test_direct_ask_item_constraint_is_not_self_justifying(project, verb, ask, modifier, expected):
    result = solve(f"Aven {verb} 8 {modifier}cards. How many red cards {ask}?", project.registry)
    assert match_ask(result.question, project.registry) is not None
    assert result.store.by_kind(Quantity)
    assert result.answer.committed == (expected is not None)
    assert result.answer.value == expected


@pytest.mark.parametrize("extra,expected", (
    ("Aven sold 4 cards.", None), ("Aven sold cards.", None),
    ("Aven sold 4 red cards.", 12), ("Aven sold 4 blue cards.", 8),
))
def test_qualified_asks_preserve_extra_event_and_sibling_boundaries(project, extra, expected):
    result = solve("Aven sold 8 red cards. " + extra +
                   " How many red cards did Aven sell?", project.registry)
    assert match_ask(result.question, project.registry) is not None
    assert result.store.by_kind(Quantity)
    assert result.answer.committed == (expected is not None)
    assert result.answer.value == expected


@pytest.mark.parametrize("verb,ask", (("has", "does Bira have"), ("sold", "did Bira sell")))
@pytest.mark.parametrize("comparison,explicit,rule,explicit_rule,expected", (
    ("3 more than", "3 more cards than", "arithmetic/anchored-relation-elided", "arithmetic/anchored-relation", 11),
    ("twice as many as", "twice as many cards as", "arithmetic/times-as-many-elided", "arithmetic/times-as-many", 16),
))
def test_omitted_item_retains_its_unique_qualifier_but_explicit_whole_does_not(
    project, verb, ask, comparison, explicit, rule, explicit_rule, expected
):
    prefix = f"Aven {verb} 8 red cards. "
    result = checked(project, prefix + f"Bira {verb} {comparison} Aven. How many red cards {ask}?", expected, rule)
    assert result.store.by_kind(Relation)[0].measure is None  # original omission is retained
    derived = [q for q in result.store.by_kind(Quantity) if q.entity == "bira"]
    assert derived and all(q.measure_qualifier == "red" for q in derived)
    bare = checked(project, prefix + f"Bira {verb} {explicit} Aven. How many red cards {ask}?", None, explicit_rule)
    assert all(q.measure_qualifier is None for q in bare.store.by_kind(Quantity) if q.entity == "bira")
    checked(project, prefix + f"Bira {verb} {explicit} Aven. How many cards {ask}?", expected, explicit_rule)


@pytest.mark.parametrize("verb,ask", (("has", "does Bira have"), ("sold", "did Bira sell")))
@pytest.mark.parametrize("qualifier,amount,expected", (("red", 11, 11), ("red", 12, None), ("blue", 11, None)))
def test_elided_item_validation_shares_the_retained_qualifier(project, verb, ask, qualifier, amount, expected):
    checked(project, f"Aven {verb} 8 red cards. Bira {verb} {amount} {qualifier} cards. "
                     f"Bira {verb} 3 more than Aven. How many {qualifier} cards {ask}?", expected,
            "arithmetic/anchored-relation-elided")


def test_elided_event_with_multiple_modifiers_preserves_whole_not_a_chosen_class(project):
    prefix = "Aven sold 8 red cards. Aven sold 4 blue cards. Bira sold 3 more than Aven. "
    result = checked(project, prefix + "How many cards did Bira sell?", 15, "arithmetic/anchored-relation-elided")
    assert all(q.measure_qualifier is None for q in result.store.by_kind(Quantity) if q.entity == "bira")
    checked(project, prefix + "How many red cards did Bira sell?", None, "arithmetic/anchored-relation-elided")


@pytest.mark.parametrize("reverse", (False, True))
def test_elided_event_counts_bare_scope_as_a_rival_to_a_modifier(project, reverse):
    rows = ["Aven sold 8 red cards.", "Aven sold 4 cards."]
    if reverse:
        rows.reverse()
    prefix = " ".join(rows) + " Bira sold 3 more than Aven. "
    result = checked(project, prefix + "How many cards did Bira sell?", 15,
                     "arithmetic/anchored-relation-elided")
    assert all(q.measure_qualifier is None for q in result.store.by_kind(Quantity) if q.entity == "bira")
    checked(project, prefix + "How many red cards did Bira sell?", None,
            "arithmetic/anchored-relation-elided")


@pytest.mark.parametrize("comparison,expected,rule", (
    ("3 more than", 11, "arithmetic/anchored-relation-elided"),
    ("twice as many as", 16, "arithmetic/times-as-many-elided"),
))
@pytest.mark.parametrize("first,second,first_ref,second_ref", (
    ("Aven's teacher", "Bira's teacher", Ref("teacher", owner=Ref("aven")), Ref("teacher", owner=Ref("bira"))),
    ("the teacher A", "the teacher B", Ref("teacher", label="A"), Ref("teacher", label="B")),
))
def test_described_elided_standard_is_a_holder_not_an_item(
    project, comparison, expected, rule, first, second, first_ref, second_ref
):
    result = checked(project, f"{first} has 8 red cards. "
        f"{second} has {comparison} {first}. "
        f"How many cards does {second} have?", expected, rule)
    assert {(q.entity_ref, q.measure, q.measure_qualifier, q.value)
            for q in result.store.by_kind(Quantity)} == {
        (first_ref, "card", "red", 8),
        (second_ref, "card", "red", expected),
    }
    assert len(result.store.by_kind(Quantity)) == 2
