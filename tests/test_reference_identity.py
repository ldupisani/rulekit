"""Invented typed-reference tests; amounts never decide participant identity."""
from dataclasses import replace
import pytest

from rulekit.kernel.facts import FactStore
from rulekit.kernel.model import Quantity, Provenance, Unit, Word
from rulekit.kernel.reference_identity import (
    ReferenceIdentity as Ref, constrains, reference_from_unit,
    resolve_reference, scope_reference_store,
    distinct_references,
)


def test_constraints_intersect_and_missing_descriptors_do_not_match():
    a = Ref("box", Ref("teacher", Ref("aven")), "A", ("red", "small"))
    b = replace(a, label="B")
    c = replace(a, owner=Ref("teacher", Ref("bira")))
    assert resolve_reference(a, [a, b, c]) == a
    assert resolve_reference(Ref("box", owner=a.owner), [a, b, c]) is None
    assert resolve_reference(Ref("box", label="A"), [a, b, c]) is None
    assert resolve_reference(Ref("box"), [a]) == a
    assert not constrains(a, Ref("box"))
    assert Ref.from_dict(a.to_dict()) == a


def test_unresolved_rival_and_zero_uid_are_not_bare_evidence():
    unit = Unit(1, (Word("owned", 0),), {"lemma": "box", "senses": ["noun"],
                 "owner": "unresolved", "owner_ref_uid": 0})
    unknown = reference_from_unit(unit)
    known = Ref("box", label="A")
    assert not unknown.resolved
    assert resolve_reference(Ref("box"), [known, unknown]) is None


def test_ownership_traversal_is_bounded():
    raw = {"head": "box"}
    for _ in range(100):
        raw = {"head": "box", "owner": raw}
    assert not Ref.from_dict(raw).resolved


def test_equal_amounts_remain_distinct_and_scope_never_mutates_source():
    a, b = Ref("teacher", label="A"), Ref("teacher", label="B")
    store = FactStore()
    for sentence, ref in enumerate((a, b)):
        store.admit(Quantity(Provenance("invented", sentence), "teacher", "card", 8,
                             entity_ref=ref, label=ref.label))
    assert len(store.facts) == 2 and store.clean
    original = tuple(store.facts)
    view = scope_reference_store(store, a)
    assert view is not None and len(view.facts) == 1
    assert view.facts[0].entity_ref == a
    assert tuple(store.facts) == original
    assert scope_reference_store(store, Ref("teacher")) is None


def test_reference_uniqueness_precedes_measure_and_predicate_selection():
    a, b = Ref("teacher", label="A"), Ref("teacher", label="B")
    store = FactStore(facts=[
        Quantity(Provenance("invented", 0), "teacher", "card", 8, entity_ref=a),
        Quantity(Provenance("invented", 1), "teacher", "apple", 3, verb="buy", entity_ref=b),
    ])
    assert scope_reference_store(store, Ref("teacher")) is None
    assert scope_reference_store(store, a).facts[0].entity_ref == a


def test_distinctness_does_not_treat_missing_constraints_as_inequality():
    bare = Ref("box")
    owned = Ref("box", owner=Ref("aven"))
    assert not distinct_references(bare, owned)
    assert not distinct_references(Ref("box", qualifiers=("red",)),
                                   Ref("box", qualifiers=("red", "small")))
    assert distinct_references(owned, Ref("box", owner=Ref("bira")))
    assert not distinct_references(Ref("teacher", qualifiers=("tall",)),
                                   Ref("teacher", qualifiers=("small",)))
    assert not distinct_references(Ref("box", qualifiers=("red",)),
                                   Ref("box", qualifiers=("small",)))


def test_scoped_view_retains_other_heads_amount_free_rivals():
    owner = Ref("teacher", label="A")
    a, b = Ref("box", label="A"), Ref("box", label="B")
    store = FactStore(facts=[
        Quantity(Provenance("invented", 0), "teacher", "card", 8, entity_ref=owner),
        Quantity(Provenance("invented", 1), "box", "card", 3, entity_ref=a),
    ], references=(owner, a, b))
    view = scope_reference_store(store, owner)
    assert view is not None and b in view.references
    assert scope_reference_store(view, Ref("box")) is None


@pytest.mark.parametrize("malformed", ({"head": "box", "owner": {}},
    {"head": "box", "utterance_anchor": []},
    {"head": "box", "utterance_anchor": [True, 1]},
    {"head": "box", "utterance_anchor": [-1, 1]}))
def test_nested_and_local_anchor_metadata_is_validated(malformed):
    with pytest.raises(ValueError):
        Ref.from_dict(malformed)


@pytest.mark.parametrize("field,expected", (
    ({}, "red"), ({"measure_qualifier": None}, "red"),
    ({"measure_qualifier": ""}, ""), ({"measure_qualifier": "blue"}, "blue"),
    ({"measure_qualifier": "{other.qualifier}"}, "blue"),
))
def test_declared_measure_modifier_inheritance_preserves_explicit_yaml(field, expected):
    from rulekit.kernel.patterns import _build_fact
    item = Unit(1, (Word("cards", 0),), {"lemma": "card", "qualifier": "red"})
    other = Unit(2, (Word("cards", 1),), {"lemma": "card", "qualifier": "blue"})
    fact = _build_fact({"subject": "aven", "standard": "bira", "measure": "{item}", **field},
                       "relation", {"item": item, "other": other}, None,
                       Provenance("invented", 0), None, "invented")
    assert fact.measure_qualifier == expected
    assert fact.standard_qualifier is None  # undeclared fields do not inherit


@pytest.mark.parametrize("source", ("card", "{item.lemma}", "{item} suffix", None))
def test_modifier_inheritance_requires_one_direct_slot(source):
    from rulekit.kernel.patterns import _build_fact
    item = Unit(1, (Word("cards", 0),), {"lemma": "card", "qualifier": "red"})
    fact = _build_fact({"subject": "aven", "standard": "bira", "measure": source},
                       "relation", {"item": item}, None, Provenance("invented", 0), None, "invented")
    assert fact.measure_qualifier is None


def test_unqualified_direct_slot_does_not_invent_modifier():
    from rulekit.kernel.patterns import _build_fact
    item = Unit(1, (Word("cards", 0),), {"lemma": "card"})
    fact = _build_fact({"subject": "aven", "standard": "bira", "measure": "{item}"},
                       "relation", {"item": item}, None, Provenance("invented", 0), None, "invented")
    assert fact.measure_qualifier is None


@pytest.mark.parametrize("metadata", ({}, [], {"head": "aven", "owner": {}}))
def test_malformed_unit_owner_never_falls_back_to_flat_owner(metadata):
    unit = Unit(1, (Word("owned", 0),), {"lemma": "box", "senses": ["noun"],
                 "owner": "aven", "owner_reference": metadata})
    reference = reference_from_unit(unit)
    assert reference.head == "box" and not reference.resolved
    assert reference.owner is not None and not reference.owner.resolved


def test_local_owner_is_not_a_named_entity_or_another_passage_anchor():
    anchored = Ref("owner", utterance_anchor=(0, 1))
    assert Ref.from_dict(anchored.to_dict()) == anchored
    assert not constrains(anchored, Ref("owner"))
    assert not constrains(anchored, Ref("owner", utterance_anchor=(2, 1)))


def test_deictic_binding_key_is_not_the_display_projection():
    owned = Ref("box", owner=Ref("red"))
    qualified = Ref("box", qualifiers=("red",))
    assert owned.display() == qualified.display()
    assert owned.binding_key() != qualified.binding_key()
    assert Ref("aven").binding_key() == "aven"


def test_synth_forwarding_preserves_exact_input_reference_without_parsing():
    ref = Ref("box", owner=Ref("teacher", owner=Ref("aven")), label="A")
    store = FactStore(facts=[Quantity(Provenance("invented", 0), ref.display(),
                                     "bag", 2, entity_ref=ref)])
    derived = Quantity(Provenance("synth/invented", -1), ref.display(), "card", 8)
    store.admit(derived)
    assert store.by_kind(Quantity)[-1].entity_ref == ref


def test_synth_forwarding_cannot_select_between_colliding_displays():
    a, b = Ref("box", owner=Ref("red")), Ref("box", qualifiers=("red",))
    assert a.display() == b.display()
    store = FactStore(facts=[
        Quantity(Provenance("invented", i), ref.display(), "bag", value, entity_ref=ref)
        for i, (ref, value) in enumerate(((a, 2), (b, 3)))
    ])
    store.admit(Quantity(Provenance("synth/invented", -1), a.display(), "card", 8))
    assert not store.by_kind(Quantity)[-1].entity_ref.resolved
    assert scope_reference_store(store, a) is None


def test_rekey_cannot_reassign_an_unrelated_agreement():
    from rulekit.kernel.facts import AgreementAmbiguity
    from rulekit.kernel.guards import _fact_values_by_sentence
    ref = Ref("teacher", label="A")
    fact = Quantity(Provenance("invented", 0), "teacher", "card", 8, entity_ref=ref)
    stale = AgreementAmbiguity(fact.key(), 9, fact.provenance, Provenance("invented", 1))
    store = FactStore(facts=[fact], agreement_ambiguities=[stale])
    rekeyed = store._compatibility_rekey(fact, entity=ref.display())
    store.facts = [rekeyed]
    assert store.agreement_ambiguities == [stale]
    assert 1 not in _fact_values_by_sentence(store)
