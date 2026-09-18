"""Invented analogues: same-holder signed comparisons over named item classes."""

import pytest

from rulekit.data.project import load_project
from rulekit.generation import generate_candidate
from rulekit.kernel.engine import analyze, solve
from rulekit.kernel.model import CollectionAttribute, Predication, Quantity, Relation

RULE = "arithmetic/qualified-item-comparison-pair"


@pytest.fixture(scope="module")
def project():
    return load_project("projects/curated")


def story(verb="bought", item="cards", modifiers=("flower", "truck", "rose"), split=False):
    first, second, third = modifiers
    join = f". Cato {verb}" if split else ", and"
    return (f"Cato {verb} 14 {first} {item}. Cato {verb} 6 more {second} {item} "
            f"than {first} {item}{join} 8 fewer {third} {item} than {second} {item}. ")


@pytest.mark.parametrize("verb,ask", [("bought", "did Cato buy"), ("sold", "did Cato sell"),
                                      ("has", "does Cato have")])
@pytest.mark.parametrize("item,modifiers", [("cards", ("flower", "truck", "rose")),
                                          ("stamps", ("snowflake", "truck", "rose")),
                                          ("balls", ("red", "blue", "green"))])
@pytest.mark.parametrize("split", [False, True])
def test_subtype_chain_uses_exact_standard(project, verb, ask, item, modifiers, split):
    result = solve(story(verb, item, modifiers, split) + f"How many {item} {ask} in all?",
                   project.registry)
    assert result.value == 46, result.answer
    quantities = result.store.by_kind(Quantity)
    assert {q.measure_qualifier: q.value for q in quantities} == dict(zip(modifiers, (14, 20, 12)))
    relations = result.store.by_kind(Relation)
    assert len(relations) == 2
    assert [(r.measure_qualifier, r.standard_qualifier, r.offset) for r in relations] == [
        (modifiers[1], modifiers[0], 6), (modifiers[2], modifiers[1], -8)]
    if not split:
        assert all(r.provenance.source == RULE for r in relations)


def test_descriptions_preserved_without_made_up_quantities(project):
    description = ("Some of the cards had a rose pattern, some had a flower pattern, "
                   "and some had a tree pattern. ")
    result = solve("Cato bought cards at the post office. " + description
                   + story(item="cards", modifiers=("rose", "flower", "tree"))
                   + "How many cards did Cato buy in all?", project.registry)
    assert result.value == 46, result.answer
    assert {(f.collection, f.attribute, f.qualifier, f.quantifier)
            for f in result.store.by_kind(CollectionAttribute)} == {
        ("card", "pattern", modifier, "some") for modifier in ("rose", "flower", "tree")}
    assert not any(f.provenance.sentence == 1 for kind in (Quantity, Predication)
                   for f in result.store.by_kind(kind))


@pytest.mark.parametrize("attribute", ["design", "pattern"])
@pytest.mark.parametrize("tail,count", [("", 1), (", and some had a tree {attribute}", 2),
                                       (", some had a truck {attribute}, and some had a tree {attribute}", 3)])
def test_nominal_description_templates(project, attribute, tail, count):
    result = solve("Some of the cards had a flower " + attribute
                   + tail.format(attribute=attribute) + ".", project.registry)
    assert len(result.store.by_kind(CollectionAttribute)) == count
    assert not result.store.by_kind(Quantity)
    assert not result.store.by_kind(Predication)


@pytest.mark.parametrize("prefix", [
    "Some of the cards had a tree design. ",
    "Some of the cards had a tree design. Dena bought 5 tree cards. ",
    "Some of the cards had a tree design. Cato sold 5 tree cards. ",
    "Some of the cards had a tree design. Cato bought 0 tree cards. ",
    "Some of the cards had a flower design. Some of the cards had a truck pattern. ",
])
def test_unknown_or_overlapping_described_subset_cannot_disappear(project, prefix):
    result = solve(prefix + story() + "How many cards did Cato buy in all?", project.registry)
    assert not result.answer.committed, result.answer


def test_known_subset_can_be_asked_without_completing_other_subsets(project):
    result = solve("Some of the cards had a flower design, and some had a tree design. "
                   "Cato bought 14 flower cards. How many flower cards did Cato buy?", project.registry)
    assert result.value == 14, result.answer


@pytest.mark.parametrize("anchor", ["", "Dena bought 14 flower cards. ",
                                    "Cato sold 14 flower cards. ", "Cato bought 14 tree cards. ",
                                    "Cato bought 1 flower card. "])
def test_missing_incompatible_or_negative_anchor_declines(project, anchor):
    comparison = story().split(". ", 1)[1]
    result = solve(anchor + comparison + "How many cards did Cato buy in all?", project.registry)
    assert not result.answer.committed, result.answer


@pytest.mark.parametrize("extra", ["Cato bought 50 truck cards. ", "Cato bought 4 cards. "])
def test_contradiction_or_unclassified_event_cannot_supply_anchor(project, extra):
    result = solve(story() + extra + "How many cards did Cato buy in all?", project.registry)
    assert not result.answer.committed, result.answer


def test_repeated_events_sum_only_within_the_named_standard(project):
    text = story().replace("Cato bought 14 flower cards. ",
                           "Cato bought 5 flower cards. Cato bought 9 flower cards. ")
    result = solve(text + "How many cards did Cato buy in all?", project.registry)
    assert result.value == 46, result.answer


@pytest.mark.parametrize("replacement", ["flower cards", "truck apples", "cards", "Dena's truck cards"])
def test_pair_requires_distinct_compatible_unowned_item_classes(project, replacement):
    text = story().replace("6 more truck cards", "6 more " + replacement)
    result = solve(text + "How many cards did Cato buy in all?", project.registry)
    assert not any(r.provenance.source == RULE for r in result.store.by_kind(Relation))
    assert not result.answer.committed


@pytest.mark.parametrize("holder", ["Dena's teacher", "the tall teacher", "teacher B"])
def test_pair_does_not_drop_scoped_holder_identity(project, holder):
    text = story().replace("Cato bought 6", holder + " bought 6")
    result = solve(text + "How many cards did Cato buy in all?", project.registry)
    assert not any(r.provenance.source == RULE for r in result.store.by_kind(Relation))


def test_noun_homograph_keeps_its_noun_identity(project):
    reading = analyze("Cato bought 8 rose cards.", project.registry)
    card = next(u for u in reading.units if u.features.get("lemma") == "card")
    assert card.features["qualifier"] == "rose"
    reading = analyze("The rose is red.", project.registry)
    assert any(u.features.get("lemma") == "rose" and u.sense() == "noun" for u in reading.units)
    reading = analyze("The price rose.", project.registry)
    assert any(u.features.get("lemma") == "rise" and u.sense() == "verb" for u in reading.units)


def test_pair_is_available_to_generation(project):
    candidate = generate_candidate(project, rule_id=RULE, seed=17)
    assert candidate.target_status == "matched"


@pytest.mark.parametrize("suffix", ["nominal-attribute", "two-nominal-attributes", "three-nominal-attributes"])
def test_description_rules_generate(project, suffix):
    candidate = generate_candidate(project, rule_id="arithmetic/collection-" + suffix, seed=17)
    assert candidate.target_status == "matched"


def test_compound_preserves_owner_before_class_gate(project):
    reading = analyze("Cato bought Dena's truck cards.", project.registry)
    card = next(u for u in reading.units if u.features.get("lemma") == "card")
    assert card.features["qualifier"] == "truck"
    assert card.features["owner"] == "dena"


def test_class_slot_allows_modifier_but_not_owner_or_label(project):
    from rulekit.data.schemas import MatchToken
    from rulekit.kernel.model import Unit
    from rulekit.kernel.patterns import _slot_ok

    slot = MatchToken(slot="item", type="qualified", class_only=True)
    features = {"senses": ["noun"], "lemma": "card", "qualifier": "red"}
    assert _slot_ok(Unit(0, (), features), slot, project.registry)
    for field in ("owner", "label"):
        assert not _slot_ok(Unit(0, (), {**features, field: "A"}), slot, project.registry)
