"""Identity enrichment may replay old evidence, never rewrite its judgment."""
from copy import deepcopy

import pytest

from rulekit.generation.reviews import _reviewed_facts_match
from rulekit.kernel.reference_identity import ReferenceIdentity as Ref


def fact(value=8, label=None):
    return {"type": "Quantity", "source": "invented", "sentence": 0,
            "fields": {"entity": "teacher", "measure": "card", "verb": "have",
                       "value": value, **({"label": label} if label else {})}}


def test_only_declared_reference_enrichment_is_additive():
    old = fact()
    enriched = deepcopy(old)
    enriched["fields"]["entity_ref"] = Ref("teacher").to_dict()
    assert _reviewed_facts_match([enriched], [old])
    assert not _reviewed_facts_match([old], [enriched])
    unrelated = deepcopy(enriched)
    unrelated["fields"]["extra_evidence"] = True
    assert not _reviewed_facts_match([unrelated], [old])
    unrelated["fields"].pop("extra_evidence")
    unrelated["fields"]["value"] = 9
    assert not _reviewed_facts_match([unrelated], [old])


@pytest.mark.parametrize("change", (
    {"head": "other"}, {"resolved": "true"}, {"owner": []}, {"owner": {}},
    {"utterance_anchor": [False, 0]},
    {"qualifiers": [8]}, {"surprise": True},
))
def test_malformed_or_incompatible_reference_metadata_fails_closed(change):
    old, current = fact(), fact()
    current["fields"]["entity_ref"] = {**Ref("teacher").to_dict(), **change}
    assert not _reviewed_facts_match([current], [old])


def test_recorded_identity_must_remain_exact():
    old = fact(label="A")
    old["fields"]["entity_ref"] = Ref("teacher", label="A").to_dict()
    changed = deepcopy(old)
    changed["fields"]["entity_ref"]["owner"] = Ref("aven").to_dict()
    assert not _reviewed_facts_match([changed], [old])


@pytest.mark.parametrize("reference", (
    Ref("teacher", resolved=False),
    Ref("teacher", owner=Ref("aven", resolved=False), resolved=False),
    Ref("teacher", owner=Ref("aven", owner=Ref("bira", resolved=False),
                              resolved=False), resolved=False),
))
def test_well_formed_unresolved_enrichment_fails_closed(reference):
    old, current = fact(), fact()
    current["fields"]["entity_ref"] = reference.to_dict()
    assert Ref.from_dict(reference.to_dict()).to_dict() == reference.to_dict()
    assert not _reviewed_facts_match([current], [old])


@pytest.mark.parametrize("head", ("", " ", "\t\n"))
@pytest.mark.parametrize("depth", (0, 1, 3))
def test_blank_reference_heads_fail_closed_at_every_owner_depth(head, depth):
    reference = Ref(head)
    for _ in range(depth):
        reference = Ref("teacher", owner=reference)
    old, current = fact(), fact()
    current["fields"]["entity_ref"] = reference.to_dict()
    with pytest.raises(ValueError, match="malformed reference identity"):
        Ref.from_dict(reference.to_dict())
    assert not _reviewed_facts_match([current], [old])


def test_deep_resolved_owner_enrichment_remains_valid():
    reference = Ref("teacher", owner=Ref("aven", owner=Ref("bira", owner=Ref("cato"))))
    old, current = fact(), fact()
    current["fields"]["entity_ref"] = reference.to_dict()
    assert Ref.from_dict(reference.to_dict()) == reference
    assert _reviewed_facts_match([current], [old])


@pytest.mark.parametrize("fields,reference", (
    ({"owner": "aven"}, Ref("teacher", owner=Ref("bira"))),
    ({"label": "A"}, Ref("teacher", label="B")),
    ({"qualifier": "tall"}, Ref("teacher", qualifiers=("small",))),
))
def test_added_identity_cannot_contradict_recorded_flat_descriptors(fields, reference):
    old = fact()
    old["fields"].update(fields)
    current = deepcopy(old)
    current["fields"]["entity_ref"] = reference.to_dict()
    assert not _reviewed_facts_match([current], [old])


@pytest.mark.parametrize("reference", (
    Ref("teacher", owner=Ref("aven", owner=Ref("bira")), label="A", qualifiers=("tall", "small")),
    Ref("teacher", owner=Ref("aven", utterance_anchor=(0, 1)), label="A", qualifiers=("tall",)),
))
def test_nested_or_local_owner_enrichment_preserves_recorded_constraints(reference):
    old = fact(label="A")
    old["fields"].update(owner="aven", qualifier="tall")
    current = deepcopy(old)
    current["fields"]["entity_ref"] = reference.to_dict()
    assert _reviewed_facts_match([current], [old])


def test_elided_nullable_measure_does_not_require_invented_review_data():
    old = {"type": "Relation", "source": "invented", "sentence": 0,
           "fields": {"subject": "aven", "standard": "bira", "factor": 2}}
    current = deepcopy(old)
    current["fields"].update(subject_ref=Ref("aven").to_dict(),
                             standard_ref=Ref("bira").to_dict())
    assert _reviewed_facts_match([current], [old])


def test_missing_nonnullable_field_cannot_be_reconstructed_as_null():
    old = fact()
    old["fields"].pop("value")
    current = deepcopy(old)
    current["fields"]["entity_ref"] = Ref("teacher").to_dict()
    assert not _reviewed_facts_match([current], [old])


def test_new_item_qualifier_is_not_reference_only_review_enrichment():
    old = {"type": "Relation", "source": "invented", "sentence": 0,
           "fields": {"subject": "aven", "standard": "bira", "measure": "card", "factor": 2}}
    current = deepcopy(old)
    current["fields"].update(measure_qualifier="red", subject_ref=Ref("aven").to_dict(),
                             standard_ref=Ref("bira").to_dict())
    assert not _reviewed_facts_match([current], [old])


def test_fact_multiset_is_one_to_one_and_order_independent():
    bare = fact()
    a, b = fact(), fact()
    a["fields"]["entity_ref"] = Ref("teacher", label="A").to_dict()
    b["fields"]["entity_ref"] = Ref("teacher", label="B").to_dict()
    assert _reviewed_facts_match([a, b], [bare, a])
    assert _reviewed_facts_match([b, a], [a, bare])
    assert not _reviewed_facts_match([b, a], [a, a])
    assert not _reviewed_facts_match([a], [bare, a])
    assert not _reviewed_facts_match([a, a], [bare])
    for key in ("type", "source", "sentence"):
        changed = deepcopy(a)
        changed[key] = "changed"
        assert not _reviewed_facts_match([changed], [a])
