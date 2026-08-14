"""Question answering: the few generic consumers over the saturated store.

These are the shared machinery difg's playbook says must stay few, central
and heavily tested (loosening them per-rule was a documented regression
source). Question SHAPES are data (asks in rule packs); consumers are code.

The epistemic square: yes / no / undetermined / conflict — a verdict is a
statement about what the text determines, never a guess.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import TYPE_CHECKING

from ..data.registry import Registry
from . import deixis
from .evaluate import ArithmeticLog
from .facts import FactStore
from .model import Reading
from .patterns import match_ask
from .temporal import perspectives_match

if TYPE_CHECKING:  # pragma: no cover - types only
    from .model import Fact


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


@dataclass(frozen=True)
class SemanticNode:
    """One typed proposition in an answer proof.

    This is deliberately smaller than a Fact: a query or intermediate
    conclusion need not be materialized in the FactStore. Exact textual facts
    remain untouched; the proof records the semantic projection that used
    them.
    """

    kind: str
    fields: tuple[tuple[str, str | float | bool], ...]


@dataclass(frozen=True)
class ProofStep:
    """A named inference over evidence facts."""

    rule: str
    conclusion: SemanticNode
    evidence: tuple["Fact", ...] = ()
    detail: str = ""


@dataclass(frozen=True)
class AnswerProof:
    """Structured proof metadata for the designer and API."""

    query: SemanticNode
    steps: tuple[ProofStep, ...] = ()


@dataclass(frozen=True)
class ClarificationOption:
    """One normalized interpretation the caller may explicitly confirm."""

    id: str
    label: str
    description: str
    query: SemanticNode


@dataclass(frozen=True)
class ClarificationRequest:
    """A paused answer whose surface has more than one supported reading."""

    prompt: str
    options: tuple[ClarificationOption, ...]
    selected: str | None = None


@dataclass
class Answer:
    kind: str  # "number" | "series" | "witnesses" | "verdict" | "decline"
    # A series is an ordered, JSON-native list of labelled records. Keeping
    # the entity and measure beside every value means a multi-answer result
    # can never lose its identity through a positional list such as [25, 20].
    value: float | str | list[dict[str, str | float]] | None
    reason: str
    proof: AnswerProof | None = None
    clarification: ClarificationRequest | None = None

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
        return self.kind in ("number", "series", "witnesses") or (
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


def _temporal_evidence_store(
    query: dict, store: FactStore, reg: Registry
) -> FactStore:
    """Scope an opted-in temporal ask to evidence from its perspective.

    The ask names the semantic measure category to scope. That keeps this
    mechanism reusable: age asks currently declare ``age_measure``; another
    pack can opt a different family into the same contract without a new
    consumer branch. Untimed evidence in the scoped category is excluded—an
    unknown perspective cannot prove a present, past, or future state.
    """

    required = query.get("evidence_temporal_perspective")
    measure_category = query.get("evidence_measure_category")
    if required is None or not measure_category:
        return store
    scoped = []
    for fact in store.facts:
        measure = getattr(fact, "measure", None)
        base_measure = (
            measure.split("[", 1)[0]
            if isinstance(measure, str)
            else measure
        )
        if (
            base_measure is None
            or not reg.word_in_category(base_measure, measure_category)
        ):
            scoped.append(fact)
            continue
        if perspectives_match(
            required, fact.provenance.temporal_perspective, reg
        ):
            scoped.append(fact)
    return FactStore(facts=scoped)


def answer(
    question: Reading,
    store: FactStore,
    reg: Registry,
    log: ArithmeticLog,
    premises: list[Reading] | None = None,
    interpretation: str | None = None,
    reference_year: int | None = None,
) -> Answer:
    from .model import LocationConstraintViolation

    violations = store.by_kind(LocationConstraintViolation)
    if violations:
        violation = violations[0]
        return Answer(
            "decline",
            None,
            "location constraint conflict: "
            f"{violation.entity!r} has a terminating event at "
            f"{violation.place!r}, where termination is impossible",
        )
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

    clarification = None
    raw_choices = query.get("__interpretations__")
    if raw_choices is not None:
        def semantic_value(value: str) -> str | bool:
            if value == "true":
                return True
            if value == "false":
                return False
            return value

        def semantic_query(choice) -> SemanticNode:
            return SemanticNode(
                choice["kind"],
                tuple(
                    (key, semantic_value(value))
                    for key, value in choice["query"].items()
                    if key != "consumer"
                ),
            )

        options = tuple(
            ClarificationOption(
                choice["id"],
                choice["label"],
                choice["description"],
                semantic_query(choice),
            )
            for choice in raw_choices
        )
        selected = next(
            (choice for choice in raw_choices if choice["id"] == interpretation),
            None,
        )
        clarification = ClarificationRequest(
            query["__clarification__"],
            options,
            selected=interpretation if selected is not None else None,
        )
        if interpretation is None:
            return Answer(
                "decline",
                None,
                "the question has multiple supported interpretations",
                clarification=clarification,
            )
        if selected is None:
            return Answer(
                "decline",
                None,
                f"unknown interpretation {interpretation!r}; clarification is still required",
                clarification=clarification,
            )
        query = dict(selected["query"])

    consumer = query.get("consumer")

    store = _temporal_evidence_store(query, store, reg)

    def finish(result: Answer) -> Answer:
        if clarification is not None:
            result.clarification = clarification
        return result

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
            reference_year=reference_year,
        ))

    # Phase 1: consumers that lived ABOVE the temporal origo. They never saw the
    # time-filtered store, so dispatching here is exactly what they had.
    if consumer not in TIME_SCOPED:
        early = _dispatch(store)
        if early is not None:
            return finish(early)

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
            return finish(Answer(
                "decline", None,
                "the question names more than one time, and time arbitration is unbuilt",
            ))
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
            return finish(late)

    return finish(
        Answer("decline", None, f"ask {ask.id} names unknown consumer {consumer!r}")
    )
