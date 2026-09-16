"""Complete known-word quantity/ask paths in both user-facing registries."""
from pathlib import Path
from dataclasses import replace

import pytest

from rulekit.data.project import load_project
from rulekit.kernel.engine import solve
from rulekit.kernel.model import Quantity, Relation, Predication
from rulekit.kernel.patterns import match_ask

ROOT = Path(__file__).resolve().parents[1]


@pytest.fixture(scope="module", params=("curated", "gsm8k"))
def registry(request):
    return load_project(ROOT / "projects" / request.param).registry


def checked(text, registry, expected):
    result = solve(text, registry)
    matched = match_ask(result.question, registry)
    assert matched is not None, result.answer
    assert matched[1].get("evidence_entity_reference") is not None
    assert result.store.by_kind(Quantity), result.answer
    assert not any("unknown word" in str(gap) for gap in result.deficiencies())
    assert result.answer.value == expected, result.answer
    assert result.answer.committed == (expected is not None)
    return result


@pytest.mark.parametrize("reverse", (False, True))
@pytest.mark.parametrize("second", (3, 8))
@pytest.mark.parametrize("descriptor,other", (
    ("the teacher A", "the teacher B"),
    ("the tall teacher", "the small teacher"),
    ("Aven's teacher", "Bira's teacher"),
    ("the red box", "the blue box"),
    ("Aven's teacher's box", "Bira's teacher's box"),
))
def test_explicit_identity_and_ambiguous_bare(registry, reverse, second, descriptor, other):
    premises = [f"{descriptor} has 8 cards.", f"{other} has {second} cards."]
    if reverse:
        premises.reverse()
    prefix = " ".join(premises)
    result = checked(prefix + f" How many cards does {descriptor} have?", registry, 8)
    quantities = result.store.by_kind(Quantity)
    assert len({q.entity_ref for q in quantities}) == 2
    assert all(q.entity_ref.described for q in quantities)
    head = "box" if "box" in descriptor else "teacher"
    checked(prefix + f" How many cards does the {head} have?", registry, None)


@pytest.mark.parametrize("tail,expected", (
    ("How many cards did the teacher A buy?", 8),
    ("How many cards did the teacher buy?", None),
))
@pytest.mark.parametrize("rival", (
    "The teacher B bought 3 cards.",
    "The teacher B has 3 apples.",
    "The teacher B bought cards.",
))
def test_event_and_non_numeric_rivals(registry, tail, expected, rival):
    checked("The teacher A bought 8 cards. " + rival + " " + tail, registry, expected)


def test_repeat_events_preserve_occurrences(registry):
    result = checked("The teacher A bought 8 cards. The teacher A bought 8 cards. "
                     "How many cards did the teacher A buy?", registry, 16)
    assert {q.occurrence for q in result.store.by_kind(Quantity)} == {0, 1}


@pytest.mark.parametrize("target", ("the teacher", "the teacher A"))
def test_unique_bare_neighbor(registry, target):
    checked(f"The teacher A has 8 cards. How many cards does {target} have?", registry, 8)


@pytest.mark.parametrize("owner", ("her", "his", "their", "my", "your"))
def test_consistent_unnamed_owner_is_local_not_an_invented_person(registry, owner):
    result = checked(f"{owner.title()} child is 10 years old. How old is {owner} child?",
                     registry, 10)
    assert match_ask(result.question, registry)[0].id == "ask/how-old-is-possessed"
    quantity = result.store.by_kind(Quantity)[0]
    reference = quantity.entity_ref
    assert quantity.owner == owner
    assert reference.owner.head == owner and reference.owner.utterance_anchor is not None
    assert reference.resolved
    assert not any(ob.met for reading in result.premises for unit in reading.units
                   if unit.sense() == "pronoun" for ob in unit.obligations()
                   if ob.need == "refers")


@pytest.mark.parametrize("tail,ask_id", (
    ("How old is his child?", "ask/how-old-is-possessed"),
    ("How old is Aven's child?", "ask/how-old-is-explicitly-possessed"),
    ("Aven has 1 apple. How old is her child?", "ask/how-old-is-possessed"),
))
def test_unnamed_owner_does_not_supply_different_or_introduced_owner(registry, tail, ask_id):
    result = checked("Her child is 10 years old. " + tail, registry, None)
    assert match_ask(result.question, registry)[0].id == ask_id


def test_overlapping_qualifiers_are_not_proof_of_distinct_participants(registry):
    result = checked("The tall teacher has 8 cards. "
                     "The small teacher has 3 more cards than the tall teacher. "
                     "How many cards does the small teacher have?", registry, None)
    assert not result.store.by_kind(Relation)


@pytest.mark.parametrize("question", (
    "How many cards does Bira's teacher's box have?",
    "How many cards are in Bira's teacher's box?",
))
def test_missing_nested_owner(registry, question):
    result = checked("Aven's teacher's box has 8 cards. " + question, registry, None)
    reference = result.store.by_kind(Quantity)[0].entity_ref
    assert reference.owner.owner.head == "aven"


def test_owner_label_intersection(registry):
    checked("Aven's teacher A has 8 cards. Aven's teacher B has 3 cards. "
            "Bira's teacher A has 5 cards. How many cards does Aven's teacher A have?",
            registry, 8)


def test_owner_label_and_qualifier_intersection(registry):
    result = checked("Aven's red box A has 8 cards. Aven's blue box A has 3 cards. "
                     "Bira's red box A has 5 cards. How many cards does Aven's red box A have?",
                     registry, 8)
    refs = {q.entity_ref for q in result.store.by_kind(Quantity)}
    assert len(refs) == 3 and all(ref.owner and ref.label and ref.qualifiers for ref in refs)


def test_identical_state_is_idempotent_but_conflict_is_not(registry):
    checked("The teacher A has 8 cards. The teacher A has 8 cards. "
            "How many cards does the teacher A have?", registry, 8)
    result = solve("The teacher A has 8 cards. The teacher A has 9 cards. "
                   "How many cards does the teacher A have?", registry)
    assert not result.answer.committed and result.store.collisions
    assert match_ask(result.question, registry) is not None


@pytest.mark.parametrize("order", ((0, 1, 2), (0, 2, 1), (2, 0, 1)))
@pytest.mark.parametrize("rows,question,expected", (
    (("The teacher A has 8 cards.", "The teacher A has 8 cards.",
      "The teacher B has 3 cards."), "How many cards does the teacher A have?", 8),
    (("Aven has 8 red cards.", "Aven has 8 red cards.", "Aven has 3 blue cards."),
     "How many cards does Aven have?", 11),
))
def test_agreement_survives_later_actor_or_measure_rekey(registry, order, rows, question, expected):
    result = checked(" ".join(rows[i] for i in order) + " " + question, registry, expected)
    assert result.store.agreement_ambiguities


def test_later_conflict_does_not_account_for_deduped_state(registry):
    result = solve("The teacher A has 8 cards. The teacher A has 8 cards. "
                   "The teacher B has 3 cards. The teacher A has 9 cards. "
                   "How many cards does the teacher A have?", registry)
    assert result.store.collisions and not result.answer.committed
    assert match_ask(result.question, registry) is not None
    assert all(q.entity_ref.label != "a" for q in result.store.by_kind(Quantity))


@pytest.mark.parametrize("qualifier", ("", "large "))
def test_counted_container_class_retains_its_existing_aggregate(registry, qualifier):
    result = checked(f"There are 7 {qualifier}boxes. Each {qualifier}box has 4 cards. "
                     "How many cards are in the boxes?", registry, 28)
    assert "counted" in result.answer.reason


@pytest.mark.parametrize("rival", ("The small box has apples.", "The small box has 3 apples."))
def test_counted_container_class_does_not_erase_other_measure_rival(registry, rival):
    checked("There are 7 large boxes. Each large box has 4 cards. " + rival
            + " How many cards are in the boxes?", registry, None)


def test_owned_place_fallback_resolves_the_full_holder(registry):
    checked("Aven has 7 cards. How many cards does Aven have in his box?", registry, 7)
    checked("The teacher A has 7 cards. The teacher B has 3 cards. "
            "How many cards does the teacher A have in his box?", registry, 7)
    checked("Aven's teacher has 7 cards. Bira's teacher has 3 cards. "
            "How many cards does Aven's teacher have in her box?", registry, 7)


def test_conflicting_labeled_comparison_keeps_both_activated_sides(registry):
    result = checked("The teacher A has 8 cards. The teacher B has 3 cards. "
                     "The teacher A has 3 more cards than the teacher B. "
                     "How many cards does the teacher A have?", registry, None)
    assert len(result.store.by_kind(Quantity)) == 2
    assert result.store.by_kind(Relation)
    assert "contradicted-relation" in result.answer.reason


@pytest.mark.parametrize("premise,ask,expected", (
    ("The teacher A has 8 cards. The teacher B has 3 more cards than the teacher A.",
     "How many cards does the teacher B have?", 11),
    ("The teacher B has 11 cards. The teacher B has 3 more cards than the teacher A.",
     "How many cards does the teacher A have?", 8),
    ("The tall teacher A has 8 cards. The small teacher B has 3 more cards than the tall teacher A.",
     "How many cards does the small teacher B have?", 11),
    ("Aven's teacher has 8 cards. Bira's teacher has 3 more cards than Aven's teacher.",
     "How many cards does Bira's teacher have?", 11),
    ("The teacher A has 8 cards. The teacher C has 3 more cards than the teacher B.",
     "How many cards does the teacher C have?", None),
    ("The teacher A has 8 cards. The teacher B has 3 cards. Cato has 2 more cards than the teacher.",
     "How many cards does Cato have?", None),
    ("The teacher A bought 8 red cards. The teacher B bought 20 blue cards. "
     "The teacher bought 5 more green cards than red cards.",
     "How many cards did the teacher buy?", None),
))
def test_relation_identity_paths(registry, premise, ask, expected):
    result = checked(premise + " " + ask, registry, expected)
    relations = result.store.by_kind(Relation)
    assert relations and all(r.subject_ref and r.standard_ref for r in relations)
    assert any(r.provenance.source == "arithmetic/anchored-relation" for r in relations)


@pytest.mark.parametrize("verb,past", (("buy", "bought"), ("sell", "sold")))
@pytest.mark.parametrize("inverse", (False, True))
def test_event_relation_forward_and_inverse(registry, verb, past, inverse):
    anchor = f"The teacher B {past} 11 cards." if inverse else f"The teacher A {past} 8 cards."
    target, value = ("A", 8) if inverse else ("B", 11)
    result = checked(anchor + f" The teacher B {past} 3 more cards than the teacher A. "
                     f"How many cards did the teacher {target} {verb}?", registry, value)
    assert len(result.store.by_kind(Quantity)) == 2
    assert {q.verb for q in result.store.by_kind(Quantity)} == {verb}


@pytest.mark.parametrize("reverse", (False, True))
def test_event_relation_cannot_borrow_other_predicate(registry, reverse):
    premises = ["The teacher A sold 8 cards.",
                "The teacher B bought 3 more cards than the teacher A."]
    if reverse:
        premises.reverse()
    result = checked(" ".join(premises) + " How many cards did the teacher B buy?",
                     registry, None)
    assert result.store.by_kind(Relation)
    assert not any(q.verb == "buy" for q in result.store.by_kind(Quantity))


@pytest.mark.parametrize("verb,past", (("buy", "bought"), ("sell", "sold")))
@pytest.mark.parametrize("inverse", (False, True))
@pytest.mark.parametrize("amounts,standard,offset,expected", (
    ((8,), 5, 3, 8),
    ((8,), 3, 3, None),
    ((8, 4), 9, 3, 12),
    ((6, 6), 9, 3, 12),
    ((8, 4), 5, 3, None),
    ((0,), 0, 0, 0),
    ((0,), 0, 3, None),
))
def test_event_comparison_validates_complete_totals(
    registry, verb, past, inverse, amounts, standard, offset, expected
):
    quantities = " ".join(f"The teacher A {past} {n} cards." for n in amounts)
    quantities += f" The teacher B {past} {standard} cards."
    subject, direction, anchor = ("B", "fewer", "A") if inverse else ("A", "more", "B")
    result = checked(
        quantities + f" The teacher {subject} {past} {offset} {direction} cards than the teacher {anchor}."
        + f" How many cards did the teacher A {verb}?", registry, expected
    )
    assert match_ask(result.question, registry)[0].id == "ask/how-many-entity-common-noun"
    relations = result.store.by_kind(Relation)
    assert len(relations) == 1 and relations[0].provenance.source == "arithmetic/anchored-relation"
    assert relations[0].verb == verb
    facts = result.store.by_kind(Quantity)
    assert len(facts) == len(amounts) + 1
    assert all(q.verb == verb for q in facts)
    assert sorted(q.value for q in facts if q.entity_ref.label == "A") == sorted(amounts)
    if expected is None:
        assert "contradicted-relation" in result.answer.reason


@pytest.mark.parametrize("extra", (
    "The teacher C sold 90 cards.",
    "The teacher B bought 90 cards.",
    "The teacher B sold 90 apples.",
))
def test_event_comparison_does_not_mix_rivals_predicates_or_measures(registry, extra):
    result = checked("The teacher A sold 8 cards. The teacher B sold 5 cards. " + extra
                     + " The teacher A sold 3 more cards than the teacher B."
                     + " How many cards did the teacher A sell?", registry, 8)
    assert result.store.by_kind(Relation)[0].provenance.source == "arithmetic/anchored-relation"
    assert any(q.value == 90 for q in result.store.by_kind(Quantity))


@pytest.mark.parametrize("inverse", (False, True))
@pytest.mark.parametrize("qualified_relation", (False, True))
def test_event_relation_unique_qualified_item_projection(registry, inverse, qualified_relation):
    anchor = "Bira sold 11 red cards." if inverse else "Aven sold 8 red cards."
    target, value = ("Aven", 8) if inverse else ("Bira", 11)
    modifier = "red " if qualified_relation else ""
    result = checked(anchor + f" Bira sold 3 more {modifier}cards than Aven."
                     + f" How many cards did {target} sell?", registry, value)
    relation = result.store.by_kind(Relation)[0]
    assert relation.provenance.source == "arithmetic/anchored-relation"
    assert (relation.measure_qualifier or None) == ("red" if qualified_relation else None)
    assert {q.measure_qualifier for q in result.store.by_kind(Quantity)} == (
        {"red"} if qualified_relation else {"red", None})


@pytest.mark.parametrize("anchor,extra,expected", (
    ("red", "", 11),
    ("blue", "", None),
    ("red", "Aven sold 90 blue apples.", 11),
    ("red", "Aven sold 10 blue cards.", 11),
))
def test_event_relation_explicit_item_constraint_selects_only_its_variant(registry, anchor, extra, expected):
    result = checked(f"Aven sold 8 {anchor} cards. Bira sold 11 red cards. {extra}"
                     " Bira sold 3 more red cards than Aven."
                     " How many red cards did Bira sell?", registry, expected)
    assert result.store.by_kind(Relation)[0].provenance.source == "arithmetic/anchored-relation"
    assert len(result.store.by_kind(Quantity)) == (3 if extra else 2)
    if expected is None:
        assert "contradicted-relation" in result.answer.reason


def test_event_relation_missing_item_modifier_cannot_alias_competing_variants(registry):
    result = checked("Aven sold 8 cards. Aven sold 10 blue cards. Bira sold 11 red cards."
                     " Bira sold 3 more red cards than Aven."
                     " How many red cards did Bira sell?", registry, None)
    assert result.store.by_kind(Relation)[0].provenance.source == "arithmetic/anchored-relation"
    assert {q.measure_qualifier for q in result.store.by_kind(Quantity)} == {None, "blue", "red"}
    assert "contradicted-relation" in result.answer.reason


@pytest.mark.parametrize("asked", ("A", "B"))
@pytest.mark.parametrize("determiner", ("", "some "))
def test_event_comparison_cannot_certify_unknown_additional_amount(registry, asked, determiner):
    result = checked(f"The teacher A sold 8 cards. The teacher A sold {determiner}cards."
                     " The teacher B sold 5 cards. The teacher A sold 3 more cards than the teacher B."
                     f" How many cards did the teacher {asked} sell?", registry, None)
    assert result.store.by_kind(Relation)[0].provenance.source == "arithmetic/anchored-relation"
    assert any(p.polarity and p.subject_ref.label == "A" and p.dobj == "card"
               and p.verb == "sell" and p.dobj_unquantified == bool(determiner)
               for p in result.store.by_kind(Predication))


@pytest.mark.parametrize("period", ("March", "April"))
def test_event_comparison_does_not_equate_period_subtotals_with_unscoped_totals(registry, period):
    result = checked("The teacher A sold 8 cards in March."
                     f" The teacher B sold 5 cards in {period}."
                     " The teacher A sold 3 more cards than the teacher B."
                     " How many cards did the teacher A sell?", registry, None)
    assert result.store.by_kind(Relation)[0].provenance.source == "arithmetic/anchored-relation"
    assert {q.time for q in result.store.by_kind(Quantity)} == {"march", period.lower()}


@pytest.mark.parametrize("alteration", ("same-compatible", "same-incompatible", "offset", "perspective"))
def test_event_comparison_declared_identity_and_time_boundaries(registry, alteration):
    # Start from a complete parsed path, then exercise typed relation metadata
    # that the grammar deliberately does not infer from a self-comparison.
    from rulekit.kernel.answer import Answer
    from rulekit.kernel.evaluate import ArithmeticLog
    from rulekit.kernel.facts import FactStore
    from rulekit.kernel.guards import check

    result = checked("The teacher A sold 8 cards. The teacher B sold 5 cards."
                     " The teacher A sold 3 more cards than the teacher B."
                     " How many cards did the teacher A sell?", registry, 8)
    relation = result.store.by_kind(Relation)[0]
    if alteration.startswith("same-"):
        relation = replace(relation, standard_ref=relation.subject_ref, standard_label="A",
                           offset=0 if alteration == "same-compatible" else 3)
    elif alteration == "offset":
        relation = replace(relation, subject_offset=1, standard_offset=1)
    else:
        relation = replace(relation, provenance=replace(relation.provenance,
                                                       temporal_perspective="future"))
    store = FactStore(facts=[*result.store.by_kind(Quantity), relation],
                      references=result.store.references)
    veto = check([], {}, ArithmeticLog(), registry, Answer("number", 8, "probe"), store)
    if alteration == "same-compatible":
        assert veto is None
    else:
        assert veto is not None and veto.guard == "contradicted-relation"


@pytest.mark.parametrize("comparison,rule", (
    ("3 more than", "arithmetic/anchored-relation-elided"),
    ("twice as many as", "arithmetic/times-as-many-elided"),
))
@pytest.mark.parametrize("amount,extra,expected", (
    (6, "", 6),
    (8, "", None),
    (6, "The teacher A sold cards.", None),
    (6, "The teacher A sold some cards.", None),
    (6, "The teacher B sold 4 apples.", None),
    (6, "The teacher C sold 4 apples.", 6),
    (6, "The teacher A sold 4 apples.", 6),
))
def test_elided_event_comparison_uses_one_shared_measure_resolution(
    registry, comparison, rule, amount, extra, expected
):
    result = checked(f"The teacher A sold {amount} cards. The teacher B sold 3 cards. {extra}"
                     f" The teacher A sold {comparison} the teacher B."
                     " How many cards did the teacher A sell?", registry, expected)
    assert match_ask(result.question, registry)[0].id == "ask/how-many-entity-common-noun"
    relations = result.store.by_kind(Relation)
    assert len(relations) == 1 and relations[0].provenance.source == rule
    assert relations[0].measure is None  # recovery does not rewrite the reading
    assert {q.entity_ref.label for q in result.store.by_kind(Quantity)} >= {"A", "B"}
    if expected is None:
        assert "contradicted-relation" in result.answer.reason or "no 'sell' events" in result.answer.reason


def test_elided_measure_saturation_uses_the_same_full_standard_identity(registry):
    result = checked("The teacher B sold 3 cards. The teacher C sold 4 apples."
                     " The teacher A sold 3 more than the teacher B."
                     " How many cards did the teacher A sell?", registry, 6)
    assert result.store.by_kind(Relation)[0].provenance.source == "arithmetic/anchored-relation-elided"
    derived = [q for q in result.store.by_kind(Quantity) if q.entity_ref.label == "A"]
    assert len(derived) == 1 and derived[0].measure == "card" and derived[0].value == 6


def test_labeled_relation_chain_keeps_each_actor(registry):
    result = checked("The teacher A bought 8 cards. "
                     "The teacher B bought 3 more cards than the teacher A. "
                     "The teacher C bought twice as many cards as the teacher B. "
                     "How many cards did the teacher C buy?", registry, 22)
    assert len({q.entity_ref for q in result.store.by_kind(Quantity)}) == 3


@pytest.mark.parametrize("verb,past", (("have", "has"), ("buy", "bought")))
def test_stated_amount_cannot_hide_ambiguous_comparison(registry, verb, past):
    checked(f"The teacher A {past} 8 cards. The teacher B {past} 3 cards. "
            f"Cato {past} 2 more cards than the teacher. Cato {past} 10 cards. "
            f"How many cards does Cato {verb}?", registry, None)


@pytest.mark.parametrize("comparison,rule", (
    ("3 more than", "arithmetic/anchored-relation-elided"),
    ("twice as many as", "arithmetic/times-as-many-elided"),
    ("3 more cards than", "arithmetic/anchored-relation"),
    ("twice as many cards as", "arithmetic/times-as-many"),
))
@pytest.mark.parametrize("amount,extra,expected", (
    (6, "", 6), (8, "", None),
    (6, "The teacher A has 6 cards.", 6),
    (6, "The teacher C has 4 apples.", 6),
    (6, "The teacher A has 4 apples.", 6),
))
@pytest.mark.parametrize("reverse", (False, True))
def test_state_comparison_snapshots_explicit_or_elided(
    registry, comparison, rule, amount, extra, expected, reverse
):
    rows = [f"The teacher A has {amount} cards.", "The teacher B has 3 cards.",
            f"The teacher A has {comparison} the teacher B."]
    if reverse:
        rows.reverse()
    result = checked(" ".join(rows) + " " + extra
                     + " How many cards does the teacher A have?", registry, expected)
    assert match_ask(result.question, registry)[0].id == "ask/how-many-entity-common-noun"
    assert result.store.by_kind(Relation)[0].provenance.source == rule
    assert {q.entity_ref.label for q in result.store.by_kind(Quantity)} >= {"A", "B"}
    if expected is None:
        assert "contradicted-relation" in result.answer.reason


@pytest.mark.parametrize("comparison,rule", (
    ("3 more than", "arithmetic/anchored-relation-elided"),
    ("twice as many as", "arithmetic/times-as-many-elided"),
))
def test_state_elided_measure_cannot_choose_between_standard_items(registry, comparison, rule):
    result = checked("The teacher A has 6 cards. The teacher B has 3 cards."
                     " The teacher B has 4 apples."
                     f" The teacher A has {comparison} the teacher B."
                     " How many cards does the teacher A have?", registry, None)
    assert result.store.by_kind(Relation)[0].provenance.source == rule
    assert "contradicted-relation" in result.answer.reason


@pytest.mark.parametrize("inverse", (False, True))
@pytest.mark.parametrize("comparison,rule,subject,standard", (
    ("3 more red cards than", "arithmetic/anchored-relation", 11, 8),
    ("twice as many red cards as", "arithmetic/times-as-many", 16, 8),
))
@pytest.mark.parametrize("modifier", ("red ", "blue ", ""))
@pytest.mark.parametrize("verb,finite", (("have", "has"), ("sell", "sold")))
def test_qualified_relation_anchors_preserve_item_constraints(
    registry, inverse, comparison, rule, subject, standard, modifier, verb, finite
):
    name, value = ("Bira", subject) if inverse else ("Aven", standard)
    target, answer = ("Aven", standard) if inverse else ("Bira", subject)
    result = checked(f"{name} {finite} {value} {modifier}cards. Bira {finite} {comparison} Aven."
                     f" How many red cards does {target} {verb}?", registry,
                     answer if modifier == "red " else None)
    assert result.store.by_kind(Relation)[0].provenance.source == rule
    derived = [q for q in result.store.by_kind(Quantity) if q.provenance.source.startswith("synth/")]
    assert all(q.measure_qualifier == "red" for q in derived)
    assert bool(derived) == (modifier == "red ")


@pytest.mark.parametrize("order", ((0, 1, 2, 3), (3, 2, 1, 0), (0, 3, 1, 2)))
@pytest.mark.parametrize("comparison,rule,correct", (
    ("3 more red cards than", "arithmetic/anchored-relation", 11),
    ("twice as many red cards as", "arithmetic/times-as-many", 16),
))
@pytest.mark.parametrize("contradiction", (False, True))
def test_state_qualified_restatements_cannot_be_replaced_by_inverse_projection(
    registry, order, comparison, rule, correct, contradiction
):
    amount = correct + 1 if contradiction else correct
    rows = ["Aven has 8 red cards.", "Aven has 10 blue cards.",
            f"Bira has {amount} red cards.", f"Bira has {comparison} Aven."]
    result = checked(" ".join(rows[i] for i in order)
                     + " Aven has 90 blue apples. How many red cards does Bira have?",
                     registry, None if contradiction else correct)
    assert result.store.by_kind(Relation)[0].provenance.source == rule
    assert not any(q.provenance.source.startswith("synth/") for q in result.store.by_kind(Quantity))
    assert {q.measure_qualifier for q in result.store.by_kind(Quantity)} == {"red", "blue"}
    if contradiction:
        assert "contradicted-relation" in result.answer.reason


@pytest.mark.parametrize("comparison,rule", (
    ("0 more than", "arithmetic/anchored-relation-elided"),
    ("twice as many as", "arithmetic/times-as-many-elided"),
))
def test_zero_state_comparison_is_not_missing_evidence(registry, comparison, rule):
    result = checked("The teacher A has 0 cards. The teacher B has 0 cards."
                     f" The teacher A has {comparison} the teacher B."
                     " How many cards does the teacher A have?", registry, 0)
    assert result.store.by_kind(Relation)[0].provenance.source == rule


@pytest.mark.parametrize("comparison,rule", (
    ("3 more than", "arithmetic/anchored-relation-elided"),
    ("twice as many as", "arithmetic/times-as-many-elided"),
))
@pytest.mark.parametrize("standard", (3, 4))
def test_elided_state_inverse_restatement_checks_both_known_anchors(registry, comparison, rule, standard):
    result = checked(f"The teacher B has {standard} cards. The teacher A has 6 cards."
                     f" The teacher A has {comparison} the teacher B."
                     " How many cards does the teacher B have?", registry, 3 if standard == 3 else None)
    assert result.store.by_kind(Relation)[0].provenance.source == rule


@pytest.mark.parametrize("qualified_relation", (False, True))
def test_whole_state_and_explicit_part_are_not_added_or_identified(registry, qualified_relation):
    from rulekit.kernel.evaluate import ArithmeticLog
    from rulekit.kernel.facts import FactStore
    from rulekit.kernel.totals import _relation_item_evidence, _entity_total

    # Direct whole-plus-part prose still uses the existing collision guard;
    # this tests the projection contract when a typed part has its own key.
    result = checked("Aven has 20 cards. Bira has 3 more cards than Aven."
                     " How many cards does Bira have?", registry, 23)
    whole = next(q for q in result.store.by_kind(Quantity) if q.entity_ref.head == "aven")
    part = replace(whole, measure="card[red]", measure_qualifier="red", value=8)
    relation = replace(result.store.by_kind(Relation)[0],
                       measure_qualifier="red" if qualified_relation else None)
    store = FactStore(facts=[whole, part], references=result.store.references)
    evidence, _, measure = _relation_item_evidence(
        store, relation, relation.standard_ref, "card", registry, ArithmeticLog())
    assert _entity_total(evidence, registry, "aven", measure, ArithmeticLog()) == (
        8 if qualified_relation else 20)


@pytest.mark.parametrize("target", (11, 12))
@pytest.mark.parametrize("derived_first", (False, True))
def test_legacy_derived_bare_projection_cannot_outrank_stated_qualified_snapshot(
    registry, target, derived_first
):
    from rulekit.kernel.answer import Answer
    from rulekit.kernel.evaluate import ArithmeticLog
    from rulekit.kernel.facts import FactStore
    from rulekit.kernel.guards import check

    result = checked("Aven has 8 red cards. Aven has 10 blue cards. Bira has 11 red cards."
                     " Bira has 3 more red cards than Aven. How many red cards does Bira have?",
                     registry, 11)
    quantities = [replace(q, value=target) if q.entity_ref.head == "bira" else q
                  for q in result.store.by_kind(Quantity)]
    direct = next(q for q in quantities if q.entity_ref.head == "aven" and q.measure_qualifier == "red")
    legacy = replace(direct, measure="card", measure_qualifier=None, value=target - 3,
                     provenance=replace(direct.provenance, source="synth/invented-projection"))
    facts = ([legacy] + quantities) if derived_first else (quantities + [legacy])
    store = FactStore(facts=facts + result.store.by_kind(Relation), references=result.store.references)
    veto = check([], {}, ArithmeticLog(), registry, Answer("number", target, "probe"), store)
    assert (veto is None) == (target == 11)
    if veto is not None:
        assert veto.guard == "contradicted-relation"


@pytest.mark.parametrize("verb,finite", (("have", "has"), ("sell", "sold")))
def test_legacy_derived_qualified_alias_remains_unique(registry, verb, finite):
    from rulekit.kernel.evaluate import ArithmeticLog
    from rulekit.kernel.facts import FactStore
    from rulekit.kernel.totals import _relation_item_evidence, _entity_total, _verb_total

    result = checked(f"Aven {finite} 8 red cards. Bira {finite} 3 more red cards than Aven."
                     f" How many red cards does Bira {verb}?", registry, 11)
    rel = result.store.by_kind(Relation)[0]
    facts = [replace(q, measure_qualifier=None) if q.provenance.source.startswith("synth/") else q
             for q in result.store.by_kind(Quantity)]
    store = FactStore(facts=facts + [rel], references=result.store.references)
    evidence, _, measure = _relation_item_evidence(store, rel, rel.subject_ref, "card", registry, ArithmeticLog())
    assert (_entity_total(evidence, registry, "bira", measure, ArithmeticLog()) if verb == "have"
            else _verb_total(evidence, "bira", measure, verb, ArithmeticLog())) == 11


@pytest.mark.parametrize("verb,finite", (("have", "has"), ("sell", "sold")))
def test_unqualified_derivation_chain_cannot_invent_item_modifier(registry, verb, finite):
    result = checked(f"Cato {finite} 5 cards. Bira {finite} 3 more cards than Cato."
                     f" Aven {finite} 3 more red cards than Bira."
                     f" How many red cards does Aven {verb}?", registry, None)
    assert len(result.store.by_kind(Relation)) == 2
    assert all(r.provenance.source == "arithmetic/anchored-relation" for r in result.store.by_kind(Relation))
    assert any(q.entity_ref.head == "bira" and q.value == 8 for q in result.store.by_kind(Quantity))
    assert not any(q.entity_ref.head == "aven" for q in result.store.by_kind(Quantity))


@pytest.mark.parametrize("extra,expected", (
    ("Aven sold 2 cards.", None),
    ("Aven sold 2 blue cards.", 11),
    ("Aven sold 2 blue apples.", 11),
    ("Aven sold 2 red cards.", None),
))
def test_qualified_event_comparison_accounts_for_unknown_subset_contribution(registry, extra, expected):
    result = checked("Aven sold 4 red cards. Aven sold 4 red cards."
                     f" {extra} Bira sold 11 red cards. Bira sold 3 more red cards than Aven."
                     " How many red cards did Bira sell?", registry, expected)
    assert result.store.by_kind(Relation)[0].provenance.source == "arithmetic/anchored-relation"
    assert len(result.store.by_kind(Quantity)) == 4
    if expected is None:
        assert "contradicted-relation" in result.answer.reason


def test_repeated_qualified_events_are_additive_comparison_anchors(registry):
    result = checked("Aven sold 4 red cards. Aven sold 4 red cards."
                     " Bira sold 3 more red cards than Aven."
                     " How many red cards did Bira sell?", registry, 11)
    assert result.store.by_kind(Relation)[0].provenance.source == "arithmetic/anchored-relation"
    assert len(result.store.by_kind(Quantity)) == 3
