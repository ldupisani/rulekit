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
from .model import Membership, PartitionQuantity, Predication, Price, Quantity, Rate, Reading
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


def _purchase_total(
    store: FactStore,
    reg: Registry,
    entity: str,
    log: ArithmeticLog,
    exclude_item: str | None = None,
) -> float | None:
    """'3 toys at $10 each' priced purchases: Σ qty × unit price over every
    PURCHASE-verb quantity this entity holds. Any purchase whose item has
    no matching Price fact declines the WHOLE total rather than risk
    silently dropping a term (definitive-or-decline). A 'splits/shares the
    cost' predicate on the same buyer means the raw total isn't what they
    actually paid — the split factor is unbuilt, so decline rather than
    risk the pre-split number.

    `exclude_item` (opt-in, default None — every other caller is
    unaffected) omits one item's own purchase-verb quantities from the
    sum; the remaining-budget capacity path uses it to total the entity's
    OTHER priced purchases without double-counting the asked item."""
    buys = [
        q for q in store.by_kind(Quantity)
        if q.entity == entity
        and reg.word_in_category(q.verb, "purchase")
        and q.measure != exclude_item
    ]
    if not buys:
        return None
    if any(
        p.subject == entity and reg.word_in_category(p.verb, "divide")
        for p in store.by_kind(Predication)
    ):
        return None
    prices = {p.item: p for p in store.by_kind(Price)}
    parts: list[str] = []
    for q in buys:
        price = prices.get(q.measure)
        if price is None:
            return None
        parts.append(f"{q.value} * {price.value}")
    return evaluate(" + ".join(parts), {}, log, source="purchase-total")


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
    ask, query, _match = matched
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
            if total is not None:
                return Answer("number", total, f"Σ {ask_verb!r} events of {entity!r}/{singular!r}")
            # "how much did X pay/spend?" over priced purchases ("3 toys at
            # $10 each") is a DERIVED total, not a literal 'pay'/'spend'
            # event — gated to money asks over spend-family verbs only.
            is_currency_ask = singular == "currency" or reg.word_in_category(singular, "currency")
            if is_currency_ask and reg.word_in_category(ask_verb, "spend_verb"):
                total = _purchase_total(store, reg, entity, log)
                if total is not None:
                    return Answer(
                        "number", total, f"Σ price × qty over {entity!r}'s purchases"
                    )
            return Answer(
                "decline", None,
                f"no {ask_verb!r} events known for {entity!r}/{singular!r}",
            )
        total = _entity_total(store, reg, entity, singular, log)
        if total is None:
            return Answer(
                "decline", None,
                f"no quantity known for {entity!r} of {singular!r} (ask {ask.id})",
            )
        return Answer("number", total, f"fold over {entity!r}/{singular!r}")

    if consumer == "rate-span":
        # Re-landing step 4 (docs/negative-results.md): conversion spans
        # and rate x population are both live. The entity slot type is
        # the one remaining parked piece.
        entity = query["entity"]
        measure = reg.plural_to_singular.get(query["measure"], query["measure"])
        rates = [
            r for r in store.by_kind(Rate)
            if r.entity == entity
            and (
                r.measure == measure
                or (
                    measure in reg.category_parents
                    and reg.word_in_category(r.measure, measure)
                )
            )
        ]
        if len(rates) != 1:
            return Answer(
                "decline", None,
                f"{len(rates)} rates known for {entity!r}/{measure!r} — "
                "the span ask needs exactly one",
            )
        rate = rates[0]
        if "span_unit" in query:
            span_unit = reg.plural_to_singular.get(query["span_unit"], query["span_unit"])
            span_value = float(query["span_value"])
        else:
            # the ask named no span in the QUESTION ("how much does Rob
            # earn?") — a standalone quantity fact stated for the entity
            # in the rate's OWN per-unit ("Rob works 8 hours") stands in
            # for it, on the same unique-fact-or-decline discipline as
            # the bridge lookup below: exactly one such fact, else decline.
            spans = [
                q for q in store.by_kind(Quantity)
                if q.entity == entity and q.measure == rate.per
            ]
            if len(spans) != 1:
                return Answer(
                    "decline", None,
                    f"no unique {rate.per!r} span known for {entity!r} to "
                    "pair with the rate",
                )
            span_unit = rate.per
            span_value = spans[0].value
        if span_unit == rate.per:
            k = span_value
        else:
            # CHAINED RATES ("30 pages an hour" x "4 hours a day" x "3
            # days"): a SECOND Rate fact for the same entity, stated in the
            # text, bridges span_unit to the first rate's per-unit — e.g.
            # Rate(entity='machine', measure='hour', per='day', value=4)
            # bridges a 'day' span to the 'hour' the first rate is per.
            # A text-stated bridge takes priority over the generic
            # reg.conversions table (a day is 24 HOURS in general, but
            # THIS machine only runs 4 of them) — checked first, and only
            # a UNIQUE bridge is trusted; anything else falls through to
            # the untouched single-rate path below, byte-for-byte.
            bridges = [
                r2 for r2 in store.by_kind(Rate)
                if r2 is not rate
                and r2.entity == entity
                and r2.measure == rate.per
                and r2.per == span_unit
            ]
            if len(bridges) == 1:
                bridge = bridges[0]
                k = evaluate(
                    f"{span_value} * {bridge.value}", {}, log, source="rate-span-bridge"
                )
            elif (span_unit, rate.per) in reg.conversions:
                k = span_value * reg.conversions[(span_unit, rate.per)]
            else:
                return Answer(
                    "decline", None,
                    f"no conversion from {span_unit!r} to the rate's "
                    f"{rate.per!r} — cannot span",
                )
        # a PER-INDIVIDUAL rate ("a bird eats 7 berries a day") multiplies
        # by the population when every holder's total resolves
        holders = sorted(
            {q.entity for q in store.by_kind(Quantity) if q.measure == rate.entity}
        )
        if holders:
            pop_totals = [
                _entity_total(store, reg, h, rate.entity, log) for h in holders
            ]
            if any(t is None for t in pop_totals):
                return Answer(
                    "decline", None,
                    f"the rate is per-{rate.entity} but the population "
                    "does not resolve",
                )
            population = evaluate(
                " + ".join(str(t) for t in pop_totals), {}, log, source="rate-population"
            )
            total = evaluate(
                f"{rate.value} * {population} * {k}", {}, log, source="rate-span"
            )
            return Answer(
                "number", total,
                f"{rate.value}/{rate.per} × {population} {rate.entity} × "
                f"{k} {rate.per}",
            )
        total = evaluate(f"{rate.value} * {k}", {}, log, source="rate-span")
        return Answer(
            "number", total,
            f"{rate.value}/{rate.per} × {k} {rate.per} for {entity!r}",
        )

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
        ask_verb = query.get("verb", "have")
        state_ask = ask_verb in ("have", "be") or reg.word_in_category(ask_verb, "state")
        totals = []
        for entity in entities:
            t = (
                _entity_total(store, reg, entity, singular, log)
                if state_ask
                else _verb_total(store, entity, singular, ask_verb, log)
            )
            totals.append(t)
        if any(t is None for t in totals) and state_ask:
            # the ask's verb trails out of pattern reach ("did X, Y and Z
            # READ?") — when every quantity of the measure shares exactly ONE
            # event verb, that activity is what the question sums
            verbs = {
                q.verb for q in store.by_kind(Quantity) if q.measure == singular
            } - {"have", "be"}
            if len(verbs) == 1:
                (only_verb,) = verbs
                totals = [
                    _verb_total(store, entity, singular, only_verb, log)
                    for entity in entities
                ]
        if any(t is None for t in totals):
            missing = entities[totals.index(None)]
            return Answer("decline", None, f"{missing!r} has no resolvable total")
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

    if consumer == "partition-complement":
        # "N of them are ADJ" premises name a subset of a collection; the
        # ask ("how many X are ADJ" / "how many X are not ADJ") either
        # reads the named subset directly or takes its EXACT complement
        # (total minus that one subset — always correct regardless of how
        # many OTHER subsets the collection has, since it is the
        # complement of THIS attribute specifically, never an
        # exhaustive-enumeration assumption).
        item = reg.plural_to_singular.get(query["item"], query["item"])
        attribute = query["attribute"]
        negated = query.get("negated") == "true"
        parts = [
            p for p in store.by_kind(PartitionQuantity)
            if p.collection == item and p.attribute == attribute and p.polarity
        ]
        if len(parts) != 1:
            return Answer(
                "decline", None,
                f"{len(parts)} partition facts known for {item!r}/{attribute!r}",
            )
        part = parts[0]
        if not negated:
            return Answer(
                "number", part.value, f"{part.value} of {item!r} are {attribute!r}"
            )
        entities = sorted(
            {q.entity for q in store.by_kind(Quantity) if q.measure == item}
        )
        if len(entities) != 1:
            return Answer(
                "decline", None,
                f"{len(entities)} entities hold {item!r} — the partition "
                "total needs exactly one",
            )
        total = _entity_total(store, reg, entities[0], item, log)
        if total is None:
            return Answer(
                "decline", None, f"{entities[0]!r} has no resolvable total for {item!r}"
            )
        return Answer(
            "number",
            evaluate(f"{total} - {part.value}", {}, log, source="partition-complement"),
            f"{total} total {item!r} minus {part.value} {attribute!r}",
        )

    if consumer == "capacity":
        # "how many X can/could/... WHO buy/purchase/afford (with $B)?" —
        # budget ÷ unit price, floored (leftover money is never itself
        # part of the count). The verb/modal are structural glue only
        # (increment 14 split 'modal' from 'auxiliary' precisely so this
        # ask can claim the token factual asks now exclude); the SEMANTIC
        # gate is a Price fact for the asked item plus a UNIQUE explicit
        # budget — never a surface cue. The budget is either the ask's own
        # "with $B" tail or, absent that, the entity's single stated money
        # holding; anything else (zero, or more than one, of either) is a
        # genuine ambiguity and declines.
        entity = query["entity"]
        item = reg.plural_to_singular.get(query["item"], query["item"])
        prices = [p for p in store.by_kind(Price) if p.item == item]
        if len(prices) != 1:
            return Answer(
                "decline", None,
                f"{len(prices)} price facts known for {item!r} — a capacity "
                "ask needs exactly one",
            )
        price = prices[0]
        budget_raw = query.get("budget_value")
        if budget_raw is not None:
            budget = evaluate(str(budget_raw), {}, log, source="capacity-budget")
        else:
            holdings = [
                q for q in store.by_kind(Quantity)
                if q.entity == entity and q.is_state
                and (q.measure == "currency" or reg.word_in_category(q.measure, "currency"))
            ]
            if len(holdings) != 1:
                return Answer(
                    "decline", None,
                    f"{len(holdings)} money holdings known for {entity!r} — "
                    "no explicit budget stated and no unique holding to use",
                )
            budget = evaluate(
                str(holdings[0].value), {}, log, source="capacity-budget"
            )
        # a budget shared across SEVERAL priced purchases needs splitting —
        # this mechanism only ever does a single floor division, so any
        # OTHER priced item this entity also has a quantity of (bought,
        # wants, holds) makes the budget ambiguous UNLESS every one of
        # those other items is itself a fully-priced, unambiguous PURCHASE
        # (a genuine "buys X for $Y" the entity already made) — in that
        # one case the remaining budget after those purchases is exactly
        # computable, so subtract it instead of declining outright.
        all_priced_items = {p2.item for p2 in store.by_kind(Price)}
        other_priced = sorted(
            {
                q.measure
                for q in store.by_kind(Quantity)
                if q.entity == entity
                and q.measure != item
                and q.measure in all_priced_items
            }
        )
        if other_priced:
            # any other-priced item held via a NON-purchase verb ("wants"/
            # "has") is not spending at all — the remaining-budget
            # subtraction below only accounts for purchase-verb quantities,
            # so such an item stays a genuine ambiguity (increment 19's
            # original decline, unchanged).
            non_purchase_other = {
                q.measure
                for q in store.by_kind(Quantity)
                if q.entity == entity
                and q.measure in other_priced
                and not reg.word_in_category(q.verb, "purchase")
            }
            if non_purchase_other:
                return Answer(
                    "decline", None,
                    f"{entity!r} also has priced {other_priced} — the budget "
                    "would need splitting across items",
                )
            # _purchase_total already carries the increment-10 invariant
            # (any unpriced purchase, or a 'splits/shares the cost'
            # predicate on this entity, declines the WHOLE total) — reused
            # here unscoped by item, so it extends unchanged to this
            # subtraction path.
            other_total = _purchase_total(store, reg, entity, log, exclude_item=item)
            if other_total is None:
                return Answer(
                    "decline", None,
                    f"{entity!r} also has priced {other_priced} — the budget "
                    "would need splitting across items",
                )
            remaining = evaluate(
                f"{budget} - {other_total}", {}, log, source="capacity-remaining"
            )
            if remaining < 0:
                return Answer(
                    "decline", None,
                    f"{entity!r}'s other purchases ({other_total}) exceed the "
                    f"stated budget ({budget}) — remaining budget is negative",
                )
            budget = remaining
        count = evaluate(
            f"round({budget} / {price.value}, 6) // 1", {}, log, source="capacity"
        )
        return Answer(
            "number", count,
            f"floor({budget} / {price.value}) — budget ÷ unit price of {item!r}",
        )

    if consumer == "membership-verdict":
        member, collection = query["member"], query["collection"]
        singular = reg.plural_to_singular.get(collection, collection)
        for f in store.by_kind(Membership):
            if f.member == member and f.collection == singular:
                return Answer("verdict", "yes" if f.polarity else "no", "membership fact")
        return Answer("verdict", "undetermined", "no membership fact either way")

    return Answer("decline", None, f"ask {ask.id} names unknown consumer {consumer!r}")
