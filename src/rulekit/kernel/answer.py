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
from .evaluate import ArithmeticLog, evaluate
from .facts import FactStore
from .model import Membership, Quantity, Reading
from .patterns import match_ask


@dataclass
class Answer:
    kind: str  # "number" | "verdict" | "decline"
    value: float | str | None
    reason: str

    @property
    def committed(self) -> bool:
        return self.kind == "number"


def _resolve_measure(measure: str, store: FactStore, reg: Registry) -> str | None:
    """Resolve the ask's measure word against the FACTS.

    - a word with its own facts resolves to itself ('pounds' in a pounds
      problem — never collapsed onto some canonical currency);
    - a CATEGORY name ('currency' in a bare how-much ask) or a category
      member with no facts of its own ('money') resolves to the UNIQUE
      in-store measure of that category — one currency in play uses it,
      mixed currencies are genuinely ambiguous and return None (decline);
    - anything else passes through to the normal not-known decline.
    """
    singular = reg.plural_to_singular.get(measure, measure)
    in_store = {q.measure for q in store.by_kind(Quantity)}
    if singular in in_store:
        return singular
    categories = (
        [singular] if singular in reg.category_parents
        else list(reg.word_categories.get(singular, ()))
    )
    if not categories:
        return singular
    present = sorted(
        m for m in in_store
        if any(reg.word_in_category(m, c) for c in categories)
    )
    if len(present) == 1:
        return present[0]
    if present:
        return None  # mixed measures of the category — ambiguous
    return singular


def _sign(verb: str, reg: Registry) -> int:
    for tag in reg.word_categories.get(verb, ()):
        chain = reg.cat_ancestors(tag)
        for cat in chain:
            if cat in reg.category_polarity:
                return reg.category_polarity[cat]
    return 1


def _entity_total(
    store: FactStore, reg: Registry, entity: str, measure: str, log: ArithmeticLog
) -> float | None:
    """The single-entity fold: state quantities anchor, event quantities
    accumulate signed by the verb's category polarity."""
    state: list[Quantity] = []
    events: list[Quantity] = []
    for q in store.by_kind(Quantity):
        if q.entity != entity or q.measure != measure:
            continue
        (state if q.is_state else events).append(q)
    if not state and not events:
        return None
    if len({q.time for q in state + events}) > 1:
        return None  # facts from DIFFERENT times — time arithmetic is unbuilt
    total = 0.0
    parts: list[str] = []
    for q in state:
        parts.append(str(q.value))
    for q in events:
        parts.append(f"{'+' if _sign(q.verb, reg) > 0 else '-'} {q.value}")
    if state:
        expr = " + ".join(str(q.value) for q in state)
        if events:
            expr += " " + " ".join(
                f"{'+' if _sign(q.verb, reg) > 0 else '-'} {q.value}" for q in events
            )
    else:
        expr = " ".join(
            f"{'+' if _sign(q.verb, reg) > 0 else '-'} {q.value}" for q in events
        ).lstrip("+ ")
        if expr.startswith("- "):
            expr = "0 " + " ".join(
                f"{'+' if _sign(q.verb, reg) > 0 else '-'} {q.value}" for q in events
            )
    return evaluate(expr, {}, log, source="fold")


def answer(
    question: Reading,
    store: FactStore,
    reg: Registry,
    log: ArithmeticLog,
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
    ask, query = matched
    consumer = query.get("consumer")

    if consumer == "single-entity":
        entity, measure = query["entity"], query["measure"]
        singular = _resolve_measure(measure, store, reg)
        if singular is None:
            return Answer("decline", None,
                          f"measure {measure!r} is ambiguous across the facts")
        ask_verb = query.get("verb", "have")
        is_state_ask = ask_verb in ("have", "be") or reg.word_in_category(ask_verb, "state")
        if not is_state_ask:
            # An EVENT ask ("how many apples did Mary EAT?") sums only that
            # verb's own event quantities — a holdings fold answering an
            # eat-question with a buy-total is a category error (the
            # question's verb is part of the query, difg playbook lesson).
            events = [
                q for q in store.by_kind(Quantity)
                if q.entity == entity and q.measure == singular
                and q.verb == ask_verb and not q.is_state
            ]
            if not events:
                return Answer(
                    "decline", None,
                    f"no {ask_verb!r} events known for {entity!r}/{singular!r}",
                )
            if len({q.time for q in events}) > 1:
                return Answer(
                    "decline", None,
                    f"{ask_verb!r} events span different times — time "
                    "arithmetic is unbuilt",
                )
            total = evaluate(
                " + ".join(str(q.value) for q in events), {}, log, source="event-fold"
            )
            return Answer("number", total, f"Σ {ask_verb!r} events of {entity!r}/{singular!r}")
        total = _entity_total(store, reg, entity, singular, log)
        if total is None:
            return Answer(
                "decline", None,
                f"no quantity known for {entity!r} of {singular!r} (ask {ask.id})",
            )
        return Answer("number", total, f"fold over {entity!r}/{singular!r}")

    if consumer == "combined":
        measure = query["measure"]
        singular = _resolve_measure(measure, store, reg)
        if singular is None:
            return Answer("decline", None,
                          f"measure {measure!r} is ambiguous across the facts")
        entities = sorted(
            {q.entity for q in store.by_kind(Quantity) if q.measure == singular}
        )
        if not entities:
            return Answer("decline", None, f"no quantities of {singular!r} known")
        totals = []
        for entity in entities:
            t = _entity_total(store, reg, entity, singular, log)
            if t is None:
                return Answer("decline", None, f"{entity!r} has no resolvable total")
            totals.append(t)
        combined = evaluate(" + ".join(str(t) for t in totals), {}, log, source="combined")
        return Answer("number", combined, f"Σ over {entities}")

    if consumer == "difference":
        a, b, measure = query["a"], query["b"], query["measure"]
        singular = _resolve_measure(measure, store, reg)
        if singular is None:
            return Answer("decline", None,
                          f"measure {measure!r} is ambiguous across the facts")
        ta = _entity_total(store, reg, a, singular, log)
        tb = _entity_total(store, reg, b, singular, log)
        if ta is None or tb is None:
            return Answer("decline", None, f"missing a total for {a!r} or {b!r}")
        return Answer(
            "number",
            evaluate(f"abs({ta} - {tb})", {}, log, source="difference"),
            f"|{a} - {b}| of {singular!r}",
        )

    if consumer == "membership-verdict":
        member, collection = query["member"], query["collection"]
        singular = reg.plural_to_singular.get(collection, collection)
        for f in store.by_kind(Membership):
            if f.member == member and f.collection == singular:
                return Answer("verdict", "yes" if f.polarity else "no", "membership fact")
        return Answer("verdict", "undetermined", "no membership fact either way")

    return Answer("decline", None, f"ask {ask.id} names unknown consumer {consumer!r}")
