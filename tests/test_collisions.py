"""Conflict adjudication: disagreement declines, agreement dedupes,
subsumption lets the strictly-narrower rule win."""

from rulekit.kernel.facts import FactStore
from rulekit.kernel.model import Provenance, Quantity


def _q(value, source="a", entity="tom", measure="apple"):
    return Quantity(
        provenance=Provenance(source=source, sentence=0),
        entity=entity, measure=measure, value=value,
    )


def test_agreement_dedupes():
    store = FactStore()
    assert store.admit(_q(3, "rule-a"))
    assert store.admit(_q(3, "rule-b"))
    assert len(store.facts) == 1
    assert store.clean


def test_disagreement_quarantines_both():
    store = FactStore()
    store.admit(_q(3, "rule-a"))
    assert not store.admit(_q(4, "rule-b"))
    assert len(store.facts) == 0  # neither survives — no ordering can mask this
    assert len(store.collisions) == 1
    c = store.collisions[0]
    assert {c.a_source, c.b_source} == {"rule-a", "rule-b"}
    assert not store.clean


def test_collision_declines_the_answer(registry):
    """End-to-end: a store with a collision must decline, whatever else holds."""
    from rulekit.kernel.answer import answer
    from rulekit.kernel.engine import analyze
    from rulekit.kernel.evaluate import ArithmeticLog

    store = FactStore()
    store.admit(_q(3, "rule-a"))
    store.admit(_q(4, "rule-b"))
    question = analyze("How many apples does Tom have?", registry)
    a = answer(question, store, registry, ArithmeticLog())
    assert a.kind == "decline"
    assert "disagree" in a.reason
