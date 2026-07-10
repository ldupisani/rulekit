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


def _sign(verb: str, reg: Registry, strict: bool = False) -> int | None:
    """The verb's accumulation direction from its polarity category. In
    strict mode an UNTAGGED verb returns None — defaulting 'put half in
    savings' to +1 is how a deposit inflates a balance. Sign facts are
    DATA (acquire/lose members); code never defaults them silently."""
    for tag in reg.word_categories.get(verb, ()):
        chain = reg.cat_ancestors(tag)
        for cat in chain:
            if cat in reg.category_polarity:
                return reg.category_polarity[cat]
    return None if strict else 1


def _verb_total(
    store: FactStore, entity: str, measure: str, verb: str, log: ArithmeticLog
) -> float | None:
    """Σ of an entity's quantities UNDER ONE VERB — the activity total
    ("how many did X sell"). Derived relation facts carry the verb too, so
    they participate; the by-verb resolution block prevents an event and
    its own re-derivation from both existing."""
    matching = [
        q for q in store.by_kind(Quantity)
        if q.entity == entity and q.measure == measure and q.verb == verb
    ]
    if not matching:
        return None
    if len({q.time for q in matching}) > 1:
        return None
    return evaluate(
        " + ".join(str(q.value) for q in matching), {}, log, source="verb-fold"
    )


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
    if any(_sign(q.verb, reg, strict=True) is None for q in events):
        return None  # an event with UNKNOWN polarity cannot be signed — decline
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
            total = _verb_total(store, entity, singular, ask_verb, log)
            if total is None:
                return Answer(
                    "decline", None,
                    f"no {ask_verb!r} events known for {entity!r}/{singular!r}",
                )
            return Answer("number", total, f"Σ {ask_verb!r} events of {entity!r}/{singular!r}")
        total = _entity_total(store, reg, entity, singular, log)
        if total is None:
            return Answer(
                "decline", None,
                f"no quantity known for {entity!r} of {singular!r} (ask {ask.id})",
            )
        return Answer("number", total, f"fold over {entity!r}/{singular!r}")

    if consumer == "unique-entity":
        # an ENTITY-LESS ask ("how many balloons are left?") resolves iff
        # exactly one entity holds the measure — definitive-or-decline
        measure = query["measure"]
        singular = _resolve_measure(measure, store, reg)
        if singular is None:
            return Answer("decline", None,
                          f"measure {measure!r} is ambiguous across the facts")
        entities = sorted(
            {q.entity for q in store.by_kind(Quantity) if q.measure == singular}
        )
        if len(entities) != 1:
            return Answer(
                "decline", None,
                f"{len(entities)} entities hold {singular!r} — an entity-less "
                "ask needs exactly one",
            )
        total = _entity_total(store, reg, entities[0], singular, log)
        if total is None:
            return Answer("decline", None, f"{entities[0]!r} has no resolvable total")
        return Answer("number", total, f"unique-entity fold over {entities[0]!r}/{singular!r}")

    if consumer == "combined":
        measure = query["measure"]
        singular = _resolve_measure(measure, store, reg)
        if singular is None:
            return Answer("decline", None,
                          f"measure {measure!r} is ambiguous across the facts")
        entities = sorted(
            {q.entity for q in store.by_kind(Quantity) if q.measure == singular}
        )
        if len(entities) < 2:
            # "how many do THEY have ALTOGETHER" asserts plurality — a
            # one-entity sum usually means a mangled parse (the permissive
            # scan's Σ-over-one artifact), and declining costs no real coverage
            return Answer(
                "decline", None,
                f"a combined ask needs at least two holders of {singular!r}; "
                f"found {entities}",
            )
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
        ask_verb = query.get("verb", "have")
        if ask_verb in ("have", "be") or reg.word_in_category(ask_verb, "state"):
            ta = _entity_total(store, reg, a, singular, log)
            tb = _entity_total(store, reg, b, singular, log)
        else:
            # "how many more did Quincy SELL than Jake" — activity totals,
            # never the signed holdings fold (selling is not owning)
            ta = _verb_total(store, a, singular, ask_verb, log)
            tb = _verb_total(store, b, singular, ask_verb, log)
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
