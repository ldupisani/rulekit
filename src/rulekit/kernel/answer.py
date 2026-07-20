"""Question answering: the few generic consumers over the saturated store.

These are the shared machinery difg's playbook says must stay few, central
and heavily tested (loosening them per-rule was a documented regression
source). Question SHAPES are data (asks in rule packs); consumers are code.

The epistemic square: yes / no / undetermined / conflict — a verdict is a
statement about what the text determines, never a guess.
"""

from __future__ import annotations

from dataclasses import dataclass

from ..data.registry import Registry
from . import deixis
from .evaluate import ArithmeticLog
from .facts import FactStore
from .model import Reading
from .patterns import match_ask


# The value kinds VALUE-ACCOUNTING holds a reading responsible for (guards.py
# imports this; it is the single definition so the two cannot drift). An
# ordinal/tuple is an index or a structure, never an operative quantity, so it is
# absent by design.
#
# A consumer taking guards.py's `_WHOLE_LIST_CONSUMERS` exemption inherits the
# duty this tuple describes — ALL of it. Reading it from here, rather than
# re-listing the kinds, is deliberate: the `physics` consumer originally
# re-implemented only the `count` third and silently ignored a stated
# multiplier/fraction ("travels HALF of 60 meters in 4 seconds" committed 15.0,
# true 7.5). Two copies of a contract drift; one does not.
_ACCOUNTED_VALUE_KINDS = ("count", "multiplier", "fraction")


@dataclass
class Answer:
    kind: str  # "number" | "verdict" | "decline"
    value: float | str | None
    reason: str

    @property
    def committed(self) -> bool:
        # A verdict COMMITS only when it takes a side. 'undetermined' is the
        # epistemic square's "I don't know" and must never count as a
        # commitment — the day it does, every honest decline becomes a
        # scoreable wrong (HANDOFF, Frontier 2). The judge half of this
        # contract lives in harness/bench.py (_judge_typed / _judge): a
        # committed verdict at a non-verdict gold now scores WRONG there, in
        # the same increment that widened this — the two halves drift apart
        # or land together.
        return self.kind == "number" or (
            self.kind == "verdict" and self.value in ("yes", "no")
        )


def _question_reference_time(question: Reading, reg: Registry, match) -> list:
    """The moment the QUESTION asks about — the ask's origo on the TIME dimension.

    docs/deixis.md §4 proved this field's absence is a confident-wrong factory: with
    no way to name a point in time, a matched ask will happily answer a March question
    with the January amount, and nothing anywhere compares them. This is the field that
    lets the ask say WHEN.

    A reference time is a `timeperiod` noun GOVERNED BY A PREPOSITION ("in March", "on
    Monday") that the ask's own slots did not take. Both tests are structural, and both
    are load-bearing:

      - the PREPOSITION test keeps a measure out. "How many MONTHS are there?" — `month`
        is what is being COUNTED, not when. A bare timeperiod noun is subject matter; a
        prepositional one is an adjunct.
      - the CONSUMED test keeps the ask's own bound slots out, for the same reason: a
        slot the ask read is what the question is ABOUT, never where it is asked FROM.

    Returns the candidate Referents (TIME-dimension), for `deixis.resolve` to arbitrate.
    A question naming two times is ambiguous and must decline — time arbitration (which
    of two moments is nearer) needs an ORDER, and there is none (deixis.md §1.3).
    """
    taken = set(match.consumed) | {
        u.uid
        for v in match.slots.values()
        for u in (v if isinstance(v, tuple) else (v,))  # span slots bind runs
    }
    out = []
    for i, unit in enumerate(question.units):
        if unit.uid in taken:
            continue
        if unit.sense() != "noun" or "value" in unit.features:
            continue
        lemma = unit.features.get("lemma", unit.features.get("fold", ""))
        if not reg.word_in_category(lemma, "timeperiod"):
            continue
        prev = question.units[i - 1] if i > 0 else None
        if prev is None or prev.sense() != "preposition":
            continue
        out.append(
            deixis.Referent(
                dimension=deixis.TIME,
                key=unit.features.get("fold", ""),
                payload=unit,
                sentence=question.sentence_index,
                span=unit.span,
            )
        )
    return out


def answer(
    question: Reading,
    store: FactStore,
    reg: Registry,
    log: ArithmeticLog,
    premises: list[Reading] | None = None,
) -> Answer:
    if not store.clean:
        c = store.collisions[0]
        return Answer(
            "decline", None,
            f"conflict: {c.a_source} and {c.b_source} disagree about {c.key} "
            f"({c.a_value} vs {c.b_value})",
        )

    matched = match_ask(question, reg)
    if matched is None:
        return Answer("decline", None, "no ask shape recognizes this question")
    ask, query, _match = matched
    consumer = query.get("consumer")

    # EXTRACTED CONSUMERS FIRST (kernel/consumers/). Consulted before the
    # if-chain below so an extracted consumer is unreachable from the chain and
    # the two can never silently diverge — a leftover branch would otherwise sit
    # there shadowed and rot. Imported lazily: `consumers` needs `Answer` from
    # this module, and a module-level import either way is a cycle.
    from .consumers import CONSUMERS, TIME_SCOPED, ConsumerContext

    def _dispatch(scoped_store):
        handler = CONSUMERS.get(consumer)
        if handler is None:
            return None
        return handler(ConsumerContext(
            query=query, question=question, store=scoped_store, reg=reg,
            log=log, match=_match, ask=ask, premises=tuple(premises or ()),
        ))

    # Phase 1: consumers that lived ABOVE the temporal origo. They never saw the
    # time-filtered store, so dispatching here is exactly what they had.
    if consumer not in TIME_SCOPED:
        early = _dispatch(store)
        if early is not None:
            return early

    # ------------------------------------------------------------------
    # THE TEMPORAL ORIGO (docs/deixis.md phase 2).
    #
    # Applied ONCE, here, before any consumer runs — not bolted onto individual ask
    # shapes. The moment a question asks about is a property of the QUESTION, not of
    # whichever ask happened to match it, so a per-ask `{slot: when}` would be exactly
    # the per-problem parsing the constitution forbids. One scan; every consumer, every
    # ask shape, for free.
    #
    # The scope rule: a fact stamped with a DIFFERENT moment is not evidence about this
    # one and is dropped. An UNTIMED fact (time=None) is kept — it asserts nothing about
    # when, so it is not contrary evidence, and dropping it would lose the base state
    # that a timed event modifies ("Sam has 10 apples. In March he ate 3.").
    # ------------------------------------------------------------------
    time_candidates = _question_reference_time(question, reg, _match)
    if time_candidates:
        origo = deixis.resolve(
            time_candidates,
            deixis.Origo(sentence=question.sentence_index),
            deixis.constant,
            dimension=deixis.TIME,
            journal=log.journal,
            source="ask/reference-time",
        )
        if origo is None:
            # Two moments named, and no way to choose: arbitrating between times needs
            # an ORDER, and `time` is an opaque label with none (deixis.md §1.3).
            # Declining is the only honest move.
            return Answer(
                "decline", None,
                "the question names more than one time, and time arbitration is unbuilt",
            )
        reference_time = origo.key
        store = FactStore(facts=[
            f for f in store.facts
            if getattr(f, "time", None) in (None, reference_time)
        ])

    # Phase 2: consumers that lived BELOW the origo. `store` is now the
    # time-filtered copy, which is the state those consumers have always been
    # written against.
    if consumer in TIME_SCOPED:
        late = _dispatch(store)
        if late is not None:
            return late

    return Answer("decline", None, f"ask {ask.id} names unknown consumer {consumer!r}")
