"""Same-value fact agreement is visible without changing fact admission.

Synthetic only: the event identifies two distinct provenances that collapse
to one fact, while identical re-admission remains trace-noise-free.
"""

import json

from rulekit.kernel.answer import Answer
from rulekit.kernel.engine import Result
from rulekit.kernel.facts import FactStore
from rulekit.kernel.model import Provenance, Quantity


def _quantity(source: str) -> Quantity:
    return Quantity(
        provenance=Provenance(source=source, sentence=0),
        entity="mira",
        measure="token",
        value=7,
    )


def test_separate_agreeing_derivations_emit_one_trace_event() -> None:
    store = FactStore()

    assert store.admit(_quantity("reader/a"))
    assert store.admit(_quantity("reader/b"))
    assert store.admit(_quantity("reader/b"))

    assert len(store.facts) == 1
    assert len(store.agreement_ambiguities) == 1
    event = store.agreement_ambiguities[0].to_trace_event()
    assert event["kind"] == "agreement-ambiguity"
    assert event["key"] == ["quantity", "mira", "token", "have", None, None]
    assert {event["retained"]["source"], event["deduped"]["source"]} == {
        "reader/a",
        "reader/b",
    }
    trace = Result(Answer("decline", None, "synthetic"), store=store).trace()
    assert event in trace
    json.dumps(trace)


def test_identical_provenance_is_not_an_ambiguous_derivation() -> None:
    store = FactStore()

    store.admit(_quantity("reader/a"))
    store.admit(_quantity("reader/a"))

    assert not store.agreement_ambiguities
