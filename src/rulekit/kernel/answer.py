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
from .model import (
    Goal,
    GroupTotal,
    Membership,
    PartitionQuantity,
    Predication,
    Price,
    Quantity,
    Rate,
    Reading,
)
from .patterns import match_ask


@dataclass
class Answer:
    kind: str  # "number" | "verdict" | "decline"
    value: float | str | None
    reason: str

    @property
    def committed(self) -> bool:
        return self.kind == "number"


def _resolve_measure_against(measure: str, candidates: set[str], reg: Registry) -> str | None:
    """Resolve a measure word against a CANDIDATE set of in-play measures.

    - a word matching a candidate resolves to itself ('pounds' in a pounds
      problem — never collapsed onto some canonical currency);
    - a CATEGORY name ('currency' in a bare how-much ask) or a category
      member with no candidate of its own ('money') resolves to the UNIQUE
      candidate measure of that category — one currency in play uses it,
      mixed currencies are genuinely ambiguous and return None (decline).
      ONLY categories marked `interchangeable` in the packs resolve this
      way: currency denominations stand in for each other; sibling count
      nouns never do (a 'cats' ask must not answer from 'dog' facts — a
      real confident-wrong: "20 pets. 8 of them are dogs. How many cats?"
      answered 8 via the unique in-store 'animal' member);
    - anything else passes through unresolved (the singular form, unchanged).
    """
    singular = reg.plural_to_singular.get(measure, measure)
    if singular in candidates:
        return singular
    categories = (
        [singular] if singular in reg.category_parents
        else list(reg.word_categories.get(singular, ()))
    )
    categories = [c for c in categories if c in reg.interchangeable_categories]
    if not categories:
        return singular
    present = sorted(
        m for m in candidates
        if any(reg.word_in_category(m, c) for c in categories)
    )
    if len(present) == 1:
        return present[0]
    if present:
        return None  # mixed measures of the category — ambiguous
    return singular


def _resolve_measure(measure: str, store: FactStore, reg: Registry) -> str | None:
    """Resolve the ask's measure word against the FACTS (see
    `_resolve_measure_against` for the category-fallback rules)."""
    in_store = {q.measure for q in store.by_kind(Quantity)}
    return _resolve_measure_against(measure, in_store, reg)


def _check_req_unit(
    req_unit: str | None, singular: str, store: FactStore, reg: Registry
) -> bool:
    """Decline-safety for a parenthetical unit qualifier ("how much money,
    in dollars, ...", mining candidate unit-parenthetical-asks): the
    ask-bound unit must resolve to the SAME concrete measure the ask's own
    `measure` already resolved to (`singular`). Reuses
    `_resolve_measure_against` unchanged — a generic currency word
    ("money"/"pounds" standing in for whatever denomination is in play)
    still resolves via the existing interchangeable-category fallback, but
    a specific unit from a DIFFERENT, non-interchangeable category (asked
    dollars, facts in quarters — `currency` and `coin` are distinct
    categories in this pack) fails to resolve to `singular` and declines
    rather than silently answering in the wrong unit. `req_unit` absent
    (no parenthetical in the question) is always a pass-through."""
    if req_unit is None:
        return True
    in_store = {q.measure for q in store.by_kind(Quantity)}
    return _resolve_measure_against(req_unit, in_store, reg) == singular


def _measure_substance_guard(
    store: FactStore, measure: str, substance: str, entities: list[str] | None = None,
) -> Answer | None:
    """Decline-safety for a partitive-tail ask (mining candidate
    partitive-measure-ask-slot: "how many KILOGRAMS OF MEAT are left" /
    "... are there" / "... does WHO have"). The ask's `item` slot only ever
    binds the bare MEASURE noun ('kilogram') — the ASKED substance ('meat')
    names nothing any fact is keyed on, so a naive fold would silently sum
    every substance sharing that measure noun across the document, exactly
    the sibling-borrow wrong `_resolve_measure_against`'s own docstring
    warns about for non-interchangeable categories ("How many cats?"
    answered from 'dog' facts): a 'rice' quantity answering a 'meat'
    question.

    `measure_qualifier` (learn.py's `_measure_substance`, a fallback source
    for the SAME field `_qualifier`/`measure_qualifier` already use for
    adjective-qualified measures — mining candidate qualified-measure-keys)
    carries the STATED substance on every Quantity fact whose counted noun
    came from a partitive 'MEASURE of SUBSTANCE' phrase. Scanning the
    candidate facts (optionally scoped to `entities`, for a single-entity
    ask) for DISTINCT non-null `measure_qualifier` values:
    - more than one distinct substance attested -> the text names two+
      substances under this measure and the ask cannot tell which the fold
      already summed -> decline;
    - exactly one attested and it does not match the ASKED substance ->
      zero facts exist about the asked substance -> decline;
    - zero attested (the overwhelming case: no partitive tail anywhere, or
      every mention agrees with what was asked) -> None, proceed exactly as
      the bare (non-partitive) ask always has.

    Every EXISTING (non-partitive) ask never binds `measure_substance` in
    its query, so this function is never even called for them — a pure
    opt-in addition, zero change to any currently-shipped consumer path."""
    candidates = [
        q for q in store.by_kind(Quantity)
        if q.measure == measure and (entities is None or q.entity in entities)
    ]
    qualifiers = {q.measure_qualifier for q in candidates if q.measure_qualifier}
    if len(qualifiers) > 1:
        return Answer(
            "decline", None,
            f"measure {measure!r} names more than one substance in the "
            f"facts {sorted(qualifiers)!r} — asked for {substance!r}",
        )
    if len(qualifiers) == 1 and substance not in qualifiers:
        return Answer(
            "decline", None,
            f"no {substance!r} facts known for measure {measure!r}",
        )
    return None


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


def _revenue_total(
    store: FactStore, reg: Registry, entity: str, log: ArithmeticLog
) -> float | None:
    """'sells 5 cakes at $3 each' priced sales: Σ qty × unit price over
    every SELL-verb quantity this entity holds — the sell-side mirror of
    _purchase_total (increment 10's discipline, unchanged): any sold item
    with no matching Price fact declines the WHOLE total rather than risk
    dropping a term (definitive-or-decline).

    A Rate fact for the same entity means a wage-earnings reading (rate ×
    worked span, increment 21's ask/earn-span/rate-span consumer) is ALSO
    live for this 'make'/'earn' verb — that's a genuine ambiguity between
    two different sources of money for the same person, so this declines
    rather than silently picking the sale-revenue interpretation."""
    sales = [
        q for q in store.by_kind(Quantity)
        if q.entity == entity and reg.word_in_category(q.verb, "sell")
    ]
    if not sales:
        return None
    if any(r.entity == entity for r in store.by_kind(Rate)):
        return None
    prices = {p.item: p for p in store.by_kind(Price)}
    parts: list[str] = []
    for q in sales:
        price = prices.get(q.measure)
        if price is None:
            return None
        parts.append(f"{q.value} * {price.value}")
    return evaluate(" + ".join(parts), {}, log, source="revenue-total")


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
    if state and events:
        earliest_event = min(q.provenance.sentence for q in events)
        if any(q.provenance.sentence > earliest_event for q in state):
            # A state Quantity narrated AFTER a prior event for the same
            # entity/measure is structurally ambiguous: it may be an
            # independent additional holding (sum, the anchor-then-event
            # order below already handles) OR a RESTATEMENT of the
            # running post-event total ("Kendall finds 6 dimes. She now
            # has 6 dimes." is 6, not 12 — the state isn't a second
            # holding). Nothing in the fold distinguishes the two
            # readings, so decline rather than risk a confident double-
            # count; a state that precedes every event (the anchor
            # narrative order) is unaffected.
            return None
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


def _superordinate_total(
    store: FactStore, reg: Registry, entity: str, measure: str, log: ArithmeticLog,
    verb: str | None = None,
) -> float | None:
    """Superordinate totality asks over same-holder subtype comparatives
    (mining candidate subtype-total-asks): "Sandro has six times as many
    daughters as sons... how many children does he have?" — the asked
    measure ('child') carries no fact of its own, but every measure this
    entity actually holds is a pack-DECLARED subtype of it (packs/core-
    english/categories/core.yaml + packs/difg-mined/categories/
    semantic.yaml: `reg.category_members[measure]` — the superordinate
    WORD doubles as its own category name, mirroring 'currency's
    structural role — resolved generically, never a hardcoded word list in
    Python, constitution rule 1).

    Fires ONLY when EVERY measure the entity holds is a declared member of
    the asked measure's category AND at least two distinct subtypes are
    held — so a partition ('Tom has 20 pets, 8 of them are dogs') never
    double-counts: 'pet' already carries its own fact and this consumer is
    only ever reached (from the `single-entity` branch) once that direct
    lookup has already come back empty. A single incidental subtype
    mention alone (only one declared member ever held) is not "every
    subtype", so it stays declined rather than risk answering a bare
    restatement as if it were the whole superordinate total.

    `verb` (opt-in, default None — the STATE-ask caller is unaffected):
    when given (an EVENT ask, e.g. "how many total toys does he BUY"),
    scopes both which measures count as "held" and how each subtype is
    summed to THAT VERB alone, mirroring `_verb_total`'s own verb-scoping
    discipline — reusing the state/event `_entity_total` fold here would
    silently pull in an unrelated verb's facts for the same measure. Either
    way this never re-implements the underlying fold: state asks reuse
    `_entity_total`, event asks reuse `_verb_total`, so an ambiguous
    subtype (mixed times, unsigned event) declines the WHOLE total,
    definitive-or-decline exactly like `_purchase_total`/`_revenue_total`."""
    if measure not in reg.superordinate_categories:
        # NOT merely "measure has declared members" — 'animal'/'pet' also
        # have members (a different, deliberately PARTIAL list, for
        # unrelated decline-safety regression coverage) and reading them
        # here would silently sum only the CAPTURED subset while an
        # uncaptured subtype phrase in the text (e.g. an unresolved
        # relation) drops out unaccounted — a genuine confident-wrong the
        # dev-train gate caught. Only a category the pack explicitly marks
        # `superordinate: true` (data/schemas.py CategoryDef) is eligible.
        return None
    members = set(reg.category_members.get(measure, ()))
    if not members:
        return None
    if verb is None:
        held_measures = {q.measure for q in store.by_kind(Quantity) if q.entity == entity}
    else:
        held_measures = {
            q.measure for q in store.by_kind(Quantity)
            if q.entity == entity and q.verb == verb
        }
    if not held_measures or not held_measures <= members:
        return None
    if len(held_measures) < 2:
        return None
    parts: list[str] = []
    for m in sorted(held_measures):
        subtotal = (
            _entity_total(store, reg, entity, m, log) if verb is None
            else _verb_total(store, entity, m, verb, log)
        )
        if subtotal is None:
            return None
        parts.append(str(subtotal))
    return evaluate(" + ".join(parts), {}, log, source="superordinate-total")


def _combined_holder_totals(
    store: FactStore, reg: Registry, query: dict, log: ArithmeticLog,
    *, exclude_entity: str | None = None,
) -> tuple[list[str], list[float]] | Answer:
    """The 'combined' consumer's holder enumeration, factored out so the
    'average' consumer (mining candidate average-asks) can reuse it
    UNCHANGED: resolve the measure, enumerate every entity that holds it
    (>=2 or decline — a combined/average ask asserts plurality), fold each
    holder's total (state-anchored or event-summed per the ask's verb),
    and retry with the sole in-play event verb when the ask's own verb
    resolves no totals. Returns either (entities, totals) or a decline
    Answer — never partial results.

    A named-pair ask (ask/how-many-combined-named, ask/how-much-combined-
    named — mining candidate named-pair-combined) binds `a`/`b` directly
    instead of leaving them unbound: sum EXACTLY those two named holders,
    never the enumerate-all-holders fallback below, so a third unnamed
    holder mentioned elsewhere in the passage can never silently inflate
    the sum. The pronoun path ('they'/'we', ask/how-many-combined/ask/
    how-much-combined, and the 'average' consumer that reuses this
    helper) is unchanged.

    `exclude_entity` (mining candidate entityless-total-recut, opt-in,
    default None — every existing caller above is UNCHANGED): the ask's
    `resolves` block may name a single entity (pack data, e.g.
    `exclude_entity: world` on ask/how-many-there-combined) that must be
    dropped from the enumerated holders before the >=2-holders-or-decline
    check below — this function never hardcodes which entity that is.
    ask/how-many-there-combined's own comment in packs/arithmetic/rules/
    core.yaml explains why: a bare `world` scene-holder (arithmetic/
    existential-premise-bare's unlocated "There are N X" fact) is a
    scene-level restatement, not an independent holding, and summing it
    alongside a real named entity is a confident-wrong."""
    measure = query["measure"]
    singular = _resolve_measure(measure, store, reg)
    if singular is None:
        return Answer("decline", None,
                      f"measure {measure!r} is ambiguous across the facts")
    measure_substance = query.get("measure_substance")
    if measure_substance:
        guard = _measure_substance_guard(store, singular, measure_substance)
        if guard is not None:
            return guard
    a, b = query.get("a"), query.get("b")
    if a is not None and b is not None:
        entities = [a, b]
    else:
        entities = sorted(
            {q.entity for q in store.by_kind(Quantity) if q.measure == singular}
        )
        if exclude_entity is not None:
            entities = [e for e in entities if e != exclude_entity]
        if len(entities) < 2:
            # "how many do THEY have ALTOGETHER" asserts plurality — a
            # one-entity sum usually means a mangled parse (the permissive
            # scan's Σ-over-one artifact), and declining costs no real
            # coverage
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
    return entities, totals


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
        # a possessive-qualified subject ("Kennedy's house") resolves bare
        # ("house") the same as any other entity UNLESS a same-key VALUE
        # conflict forced facts.py to re-key it to "house[kennedy]". Two
        # asked-for lookups when `entity_owner` is bound (absent for every
        # ask that never matches a `possessed` slot — a no-op there):
        # the exact qualified key first (the conflict-split case), then
        # the bare key SCOPED to owner-compatible facts only — excluding
        # any Quantity whose OWN owner names a DIFFERENT possessor, so
        # "Kennedy's house has 5 rooms" can never answer a question about
        # Benedict's house just because the bare lemma never collided.
        owner = query.get("entity_owner")
        # increment 34's mirror of `owner`: an attribute-qualified subject
        # ("the coconut tree") resolves bare ("tree") the same way UNLESS a
        # same-key VALUE conflict forced facts.py to re-key it to
        # "tree[coconut]" — same two-lookup, owner-scoped-fallback shape,
        # gated on `qualifier` instead. An ask binds at most one of
        # `entity_owner`/`entity_qualifier` (each comes from a distinct ask
        # id), so the two never compete for the same query.
        qualifier = query.get("entity_qualifier")
        singular = _resolve_measure(measure, store, reg)
        if singular is None:
            return Answer("decline", None,
                          f"measure {measure!r} is ambiguous across the facts")
        req_unit = query.get("req_unit")
        if not _check_req_unit(req_unit, singular, store, reg):
            return Answer(
                "decline", None,
                f"asked unit {req_unit!r} does not match resolved measure {singular!r}",
            )
        measure_substance = query.get("measure_substance")
        if measure_substance:
            guard = _measure_substance_guard(
                store, singular, measure_substance, entities=[entity]
            )
            if guard is not None:
                return guard
        owner_store = store
        if owner:
            owner_store = FactStore(facts=[
                q for q in store.by_kind(Quantity) if q.owner is None or q.owner == owner
            ])
        qualifier_store = store
        if qualifier:
            qualifier_store = FactStore(facts=[
                q for q in store.by_kind(Quantity)
                if q.qualifier is None or q.qualifier == qualifier
            ])
        ask_verb = query.get("verb", "have")
        is_state_ask = ask_verb in ("have", "be") or reg.word_in_category(ask_verb, "state")
        if not is_state_ask:
            # An EVENT ask ("how many apples did Mary EAT?") sums only that
            # verb's own event quantities — a holdings fold answering an
            # eat-question with a buy-total is a category error (the
            # question's verb is part of the query, difg playbook lesson).
            total = (
                _verb_total(store, f"{entity}[{owner}]", singular, ask_verb, log)
                if owner else None
            )
            if total is None and qualifier:
                total = _verb_total(store, f"{entity}[{qualifier}]", singular, ask_verb, log)
            if total is None:
                scoped = owner_store if owner else qualifier_store
                total = _verb_total(scoped, entity, singular, ask_verb, log)
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
            # "how much money does WHO make/earn?" over priced sales ("5
            # cakes at $3 each") is likewise a DERIVED total — gated to the
            # narrow wage_verb category (packs/difg-mined/categories/wage.yaml)
            # so an unrelated 'how much did Mary buy' never reaches here;
            # sell-side mirror of the spend_verb branch above (increment
            # 10's purchase-total, sales-revenue-asks candidate).
            if is_currency_ask and reg.word_in_category(ask_verb, "wage_verb"):
                total = _revenue_total(store, reg, entity, log)
                if total is not None:
                    return Answer(
                        "number", total, f"Σ price × qty over {entity!r}'s sales"
                    )
            # superordinate-totality fallback (mining candidate subtype-
            # total-asks), verb-scoped sibling of the state-ask fallback
            # below: "James buys twice as many toy soldiers as toy cars...
            # how many total toys does he buy?" — see `_superordinate_
            # total`'s own docstring for the guard.
            total = _superordinate_total(store, reg, entity, singular, log, verb=ask_verb)
            if total is not None:
                return Answer(
                    "number", total, f"Σ {ask_verb!r} subtype events of {entity!r}/{singular!r}"
                )
            return Answer(
                "decline", None,
                f"no {ask_verb!r} events known for {entity!r}/{singular!r}",
            )
        total = _entity_total(store, reg, f"{entity}[{owner}]", singular, log) if owner else None
        if total is None and qualifier:
            total = _entity_total(store, reg, f"{entity}[{qualifier}]", singular, log)
        if total is None:
            scoped = owner_store if owner else qualifier_store
            total = _entity_total(scoped, reg, entity, singular, log)
        fallback_entity = query.get("place_fallback_entity")
        if total is None and fallback_entity:
            # decline-safe fallback (mining candidate complement-labeled-
            # subsets), bound ONLY by ask/how-many-in-place — the HANDOFF
            # opt-in-parameter discipline for widening a shared consumer
            # (mirrors the pre-existing `exclude_entity: world` precedent
            # on ask/how-many-there-combined: the fallback entity is pack
            # DATA carried through the query, never a hardcoded "world"
            # string literal in this Python consumer). The named PLACE
            # holds NO facts of the asked measure at all (e.g. a bare
            # existential collection scene-held on `world`, introduced by
            # a leading place PP that never actually bound to the named
            # place). Answer from `fallback_entity` ONLY when it is the
            # SOLE holder of the measure anywhere in the document — never
            # merely "some other single holder exists" (that would risk a
            # confident wrong whenever an unrelated entity happens to be
            # the only other holder, e.g. "Tom's STORE has 20 candies...
            # how many are in the BOX?"). Every OTHER single-entity ask (a
            # NAMED individual like "how many toys does Tom have") never
            # binds this query field, so it can only ever CONVERT a
            # decline into a commit for the in-place ask, never move an
            # already-committed answer or reach for an unrelated entity.
            holders = {q.entity for q in store.by_kind(Quantity) if q.measure == singular}
            if holders == {fallback_entity}:
                total = _entity_total(store, reg, fallback_entity, singular, log)
        if total is None:
            # superordinate-totality fallback (mining candidate subtype-
            # total-asks): the asked measure has ZERO facts of its own but
            # every measure this entity holds is a pack-declared subtype of
            # it — see `_superordinate_total`'s own docstring for the guard.
            total = _superordinate_total(store, reg, entity, singular, log)
        if total is None:
            return Answer(
                "decline", None,
                f"no quantity known for {entity!r} of {singular!r} (ask {ask.id})",
            )
        return Answer("number", total, f"fold over {entity!r}/{singular!r}")

    if consumer == "single-entity-elided-measure":
        # mining candidate elided-measure-entity-asks: the question has NO
        # item/measure noun at all ("How many does Tom have?", "How many
        # did Tom make?") — unlike `single-entity` above, which always
        # binds `measure` from an `item` slot. The measure is supplied as
        # the UNIQUE measure for which the asked entity holds ANY fact —
        # the same unique-pool-in-play discipline `unique-entity` above
        # uses (there the entity is elided and the measure given; here
        # it's the mirror image). More than one measure in play for the
        # entity is genuinely ambiguous ("Tom has 5 marbles and 3
        # pencils. How many does Tom have?") and must decline, never guess
        # document-level.
        entity = query["entity"]
        candidates = sorted(
            {q.measure for q in store.by_kind(Quantity) if q.entity == entity}
        )
        if len(candidates) != 1:
            return Answer(
                "decline", None,
                f"{entity!r} holds {len(candidates)} measures — an "
                "elided-measure ask needs exactly one",
            )
        measure = candidates[0]
        ask_verb = query.get("verb", "have")
        is_state_ask = ask_verb in ("have", "be") or reg.word_in_category(ask_verb, "state")
        if not is_state_ask:
            # mirrors the single-entity event branch, minus the
            # owner/qualifier and derived-total (spend/wage) paths — this
            # ask never binds a possessive/qualified subject or a
            # currency-category measure (there is no `item` slot to carry
            # one), so none of that machinery applies here.
            total = _verb_total(store, entity, measure, ask_verb, log)
            if total is not None:
                return Answer(
                    "number", total, f"Σ {ask_verb!r} events of {entity!r}/{measure!r}"
                )
            return Answer(
                "decline", None,
                f"no {ask_verb!r} events known for {entity!r}/{measure!r}",
            )
        total = _entity_total(store, reg, entity, measure, log)
        if total is None:
            return Answer(
                "decline", None,
                f"no quantity known for {entity!r} of {measure!r} (ask {ask.id})",
            )
        return Answer("number", total, f"fold over {entity!r}/{measure!r}")

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
        if rate.numerator is not None and rate.denominator is not None:
            # a COMPOUND rate ("8 pages in 20 minutes") — multiply through
            # the raw stated numerator/denominator directly so value-
            # accounting (guards.py) credits the text's own two numbers as
            # read; using the derived `value` quotient here would leave
            # them unaccounted (see Rate's docstring).
            total = evaluate(
                f"{rate.numerator} * {k} / {rate.denominator}", {}, log,
                source="rate-span",
            )
        else:
            total = evaluate(f"{rate.value} * {k}", {}, log, source="rate-span")
        return Answer(
            "number", total,
            f"{rate.value}/{rate.per} × {k} {rate.per} for {entity!r}",
        )

    if consumer == "rate-span-inverse":
        # the INVERSE of 'rate-span' above ('how long does it take WHO to
        # VERB N ITEM?' / 'how many TIMEUNIT does it take...?'): an ASKED
        # amount divided by a known Rate, rather than a known span
        # multiplied by one. A distinct, additive branch — the forward
        # 'rate-span' block above is untouched byte-for-byte.
        entity = query["entity"]
        measure = reg.plural_to_singular.get(query["item"], query["item"])
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
                "the inverse span ask needs exactly one",
            )
        rate = rates[0]
        # a per-individual rate ("a bird eats 7 berries a day") entangles a
        # population the simple division below does not attempt — decline
        # rather than risk a wrong, mirroring the forward branch's own
        # per-individual detection (holders of rate.entity as a measure).
        holders = {q.entity for q in store.by_kind(Quantity) if q.measure == rate.entity}
        if holders:
            return Answer(
                "decline", None,
                f"the rate is per-{rate.entity} — the inverse span ask does "
                "not attempt a population division",
            )
        if "item_value" in query:
            item_value = float(query["item_value"])
        else:
            # mining candidate duration-rate-item-asks (TOTALITY ITEM): the
            # ask named no numeral at all ("all of the windows") — the
            # asked count instead resolves from the entity's own UNIQUELY
            # stated Quantity of this measure, elsewhere in the text
            # (the increment-10/16 whole-total-decline discipline: zero or
            # ambiguous totals both decline, never a partial/guessed sum).
            # `q.owner == entity` (not just `q.entity == entity`): "David's
            # house has 64 windows" states the total on the POSSESSED noun
            # ('house'), owner-tagged 'david' (condense.py merge-possessive,
            # Quantity.owner — the SAME declared field the single-entity
            # consumer's own `entity_owner` fallback already reads), so a
            # totality stated through what the asked entity OWNS resolves
            # exactly as one stated directly on the entity would.
            totals = [
                q for q in store.by_kind(Quantity)
                if q.measure == measure and (q.entity == entity or q.owner == entity)
            ]
            if len(totals) != 1:
                return Answer(
                    "decline", None,
                    f"{len(totals)} {measure!r} quantities known for "
                    f"{entity!r} — the totality item needs exactly one",
                )
            item_value = totals[0].value
        if rate.numerator is not None and rate.denominator is not None:
            # a COMPOUND rate ("8 pages in 20 minutes") — invert through
            # the raw stated numerator/denominator directly (same
            # numerator/denominator-not-`value` discipline as the forward
            # consumer's compound branch, Rate's docstring) so value-
            # accounting credits the text's own two numbers as read.
            span = evaluate(
                f"{item_value} * {rate.denominator} / {rate.numerator}", {}, log,
                source="rate-span-inverse",
            )
        else:
            span = evaluate(
                f"{item_value} / {rate.value}", {}, log, source="rate-span-inverse"
            )
        span_unit = rate.per
        if "span_unit" in query:
            asked_unit = reg.plural_to_singular.get(query["span_unit"], query["span_unit"])
            if asked_unit != rate.per:
                # mining candidate duration-rate-item-asks (ASKED-UNIT
                # CONVERSION): the asked time unit differs from the
                # committing rate's own per-unit — apply the SAME static
                # `reg.conversions` table the forward rate-span consumer
                # already applies above, in the REVERSE direction (the
                # computed span is stated in the rate's per-unit; convert
                # it INTO the asked unit). An absent/ambiguous conversion
                # still declines exactly as before this widening.
                if (rate.per, asked_unit) not in reg.conversions:
                    return Answer(
                        "decline", None,
                        f"no conversion from the rate's {rate.per!r} to "
                        f"asked time unit {asked_unit!r} — cannot invert",
                    )
                span = evaluate(
                    f"{span} * {reg.conversions[(rate.per, asked_unit)]}", {}, log,
                    source="rate-span-inverse",
                )
                span_unit = asked_unit
        return Answer(
            "number", span,
            f"{item_value} {measure} ÷ {rate.value}/{rate.per} for {entity!r}"
            + (f" -> {span_unit}" if span_unit != rate.per else ""),
        )

    if consumer == "unique-entity":
        # an ENTITY-LESS ask ("how many balloons are left?") resolves iff
        # exactly one entity holds the measure — definitive-or-decline
        measure = query["measure"]
        singular = _resolve_measure(measure, store, reg)
        if singular is None:
            return Answer("decline", None,
                          f"measure {measure!r} is ambiguous across the facts")
        measure_substance = query.get("measure_substance")
        if measure_substance:
            guard = _measure_substance_guard(store, singular, measure_substance)
            if guard is not None:
                return guard
        entities = sorted(
            {q.entity for q in store.by_kind(Quantity) if q.measure == singular}
        )
        if len(entities) != 1:
            return Answer(
                "decline", None,
                f"{len(entities)} entities hold {singular!r} — an entity-less "
                "ask needs exactly one",
            )
        if any(gt.measure == singular for gt in store.by_kind(GroupTotal)):
            # mining candidate distributive-each-totals (the precision fix):
            # a GroupTotal for this SAME measure means the lone entity's own
            # Quantity is a PER-CONTAINER rate ("each row has 20 chairs"),
            # not the group's whole — saturate.py's
            # synth/distributive-container-total (or a stated "N X
            # altogether" premise) already says so. Folding the single
            # entity's raw value here would be exactly the confident wrong
            # that GroupTotal exists to prevent ("20 chairs in each row"
            # read as the total 20 instead of composing with the row count
            # for 800) — decline rather than guess which one the ask means.
            return Answer(
                "decline", None,
                f"{singular!r} has both a lone holder and a group total — "
                "an entity-less ask cannot tell which one is meant",
            )
        total = _entity_total(store, reg, entities[0], singular, log)
        if total is None:
            return Answer("decline", None, f"{entities[0]!r} has no resolvable total")
        return Answer("number", total, f"unique-entity fold over {entities[0]!r}/{singular!r}")

    if consumer == "combined":
        # `exclude_entity` (mining candidate entityless-total-recut): bound
        # ONLY by ask/how-many-there-combined (`exclude_entity: world` in
        # its own resolves block) — see `_combined_holder_totals`'s
        # docstring for why that ask alone needs an entity dropped.
        holders = _combined_holder_totals(
            store, reg, query, log,
            exclude_entity=query.get("exclude_entity"),
        )
        if isinstance(holders, Answer):
            return holders
        entities, totals = holders
        combined = evaluate(" + ".join(str(t) for t in totals), {}, log, source="combined")
        return Answer("number", combined, f"Σ over {entities}")

    if consumer == "combined-elided-measure":
        # mining candidate plural-np-totality-asks: the named-pair sibling
        # of `single-entity-elided-measure` above — "how many do Tom and
        # Jerry have combined?" has NO item slot at all. Mirrors that
        # branch's unique-measure-in-play discipline, but BILATERAL: the
        # elided measure is the ONE measure BOTH named holders share (set
        # intersection of what each holds), never guessed when zero or
        # more than one measure is common to both. Once resolved, this
        # reuses `_combined_holder_totals` exactly as ask/how-many-
        # combined-named does — a/b bound, so it sums exactly those two,
        # never the enumerate-all-holders fallback.
        a, b = query["a"], query["b"]
        cand_a = {q.measure for q in store.by_kind(Quantity) if q.entity == a}
        cand_b = {q.measure for q in store.by_kind(Quantity) if q.entity == b}
        common = sorted(cand_a & cand_b)
        if len(common) != 1:
            return Answer(
                "decline", None,
                f"{a!r} and {b!r} share {len(common)} measures — an "
                "elided-measure combined ask needs exactly one",
            )
        holders = _combined_holder_totals(store, reg, dict(query, measure=common[0]), log)
        if isinstance(holders, Answer):
            return holders
        entities, totals = holders
        combined = evaluate(" + ".join(str(t) for t in totals), {}, log, source="combined")
        return Answer("number", combined, f"Σ over {entities}")

    if consumer == "average":
        # "what is/was the average number/amount of ITEM (that) they VERB?"
        # (mining candidate average-asks): the SAME holder enumeration the
        # 'combined' consumer uses (Σ over every holder of the resolved
        # measure, >=2-holders-or-decline, same state/event-verb fallback),
        # divided by the holder count. No new fact kind, no new decline
        # surface beyond what 'combined' already has.
        holders = _combined_holder_totals(store, reg, query, log)
        if isinstance(holders, Answer):
            return holders
        entities, totals = holders
        combined = evaluate(" + ".join(str(t) for t in totals), {}, log, source="combined")
        average = evaluate(
            f"({combined}) / {len(entities)}", {}, log, source="average"
        )
        return Answer("number", average, f"({combined}) ÷ {len(entities)} over {entities}")

    if consumer == "difference":
        measure = query["measure"]
        singular = _resolve_measure(measure, store, reg)
        if singular is None:
            return Answer("decline", None,
                          f"measure {measure!r} is ambiguous across the facts")
        a, b = query.get("a"), query.get("b")
        if a is None or b is None:
            # ask/what-is-the-difference-pronoun names no pair ("...ITEM
            # they have?") — mirrors the 'combined' consumer's holder
            # enumeration, but a difference is inherently BINARY: decline
            # unless EXACTLY two entities hold the measure (the established
            # exactly-one/exactly-two-or-decline discipline).
            entities = sorted(
                {q.entity for q in store.by_kind(Quantity) if q.measure == singular}
            )
            if len(entities) != 2:
                return Answer(
                    "decline", None,
                    f"a pronoun difference ask needs exactly two holders of "
                    f"{singular!r}; found {entities}",
                )
            a, b = entities
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

    if consumer == "item-cost":
        # "how much do/does/did ITEM cost" — the item-subject cost ask
        # (mining candidate item-cost-asks). The unique Price fact for the
        # asked item, times its unique purchased/held Quantity, gives the
        # TOTAL cost ("Tom buys 3 shirts at $5 each. How much do the shirts
        # cost?" -> 15); with no such Quantity in play the bare unit price
        # itself answers ("A jacket costs $50. How much does the jacket
        # cost?" -> 50). Either more than one Price fact for the item (two
        # competing prices in the text) or more than one Quantity fact
        # (which holding does the question mean?) is a genuine ambiguity —
        # decline rather than guess, the increment 19/30 discipline.
        item = reg.plural_to_singular.get(query["item"], query["item"])
        prices = [p for p in store.by_kind(Price) if p.item == item]
        if len(prices) != 1:
            return Answer(
                "decline", None,
                f"{len(prices)} price facts known for {item!r} — an "
                "item-cost ask needs exactly one",
            )
        price = prices[0]
        quantities = [q for q in store.by_kind(Quantity) if q.measure == item]
        if not quantities:
            bare = evaluate(str(price.value), {}, log, source="item-cost")
            return Answer(
                "number", bare, f"bare unit price of {item!r}"
            )
        if len(quantities) > 1:
            return Answer(
                "decline", None,
                f"{len(quantities)} quantities of {item!r} known — an "
                "item-cost ask needs exactly one to total",
            )
        qty = quantities[0]
        total = evaluate(
            f"{qty.value} * {price.value}", {}, log, source="item-cost"
        )
        return Answer(
            "number", total,
            f"{qty.value} * {price.value} — qty x unit price of {item!r}",
        )

    if consumer == "cost-of-quantity":
        # "how much did WHO pay/spend for/on N ITEM" (mining candidate
        # priced-quantity-cost-asks): unlike item-cost, the QUESTION itself
        # states the quantity (never an existing Quantity fact) — commit N
        # (the question's own count) times the item's UNIQUE per-unit Price
        # fact, the increment 19 exactly-one-Price discipline.
        item = reg.plural_to_singular.get(query["item"], query["item"])
        qty = evaluate(str(query["qty_value"]), {}, log, source="cost-of-quantity-qty")
        prices = [p for p in store.by_kind(Price) if p.item == item]
        if len(prices) != 1:
            return Answer(
                "decline", None,
                f"{len(prices)} price facts known for {item!r} — a "
                "cost-of-quantity ask needs exactly one",
            )
        price = prices[0]
        entity = query["entity"]
        # increment 10's invariant, reused verbatim: a buyer who
        # splits/shares the cost with someone else means the raw qty *
        # price is not necessarily what they themselves paid.
        if any(
            p.subject == entity and reg.word_in_category(p.verb, "divide")
            for p in store.by_kind(Predication)
        ):
            return Answer(
                "decline", None,
                f"{entity!r} has a cost-splitting predicate — the raw "
                "total is not necessarily what they paid",
            )
        # the SAME buyer already holding/having bought this item elsewhere
        # in the text is a genuine ambiguity between two possible
        # quantities (the premise's own and the question's stated one) —
        # decline rather than silently prefer the question's count.
        if any(
            q.entity == entity and q.measure == item for q in store.by_kind(Quantity)
        ):
            return Answer(
                "decline", None,
                f"{entity!r} already has a quantity of {item!r} known — "
                "ambiguous against the question's own count",
            )
        total = evaluate(f"{qty} * {price.value}", {}, log, source="cost-of-quantity")
        return Answer(
            "number", total,
            f"{qty} * {price.value} — question qty x unit price of {item!r}",
        )

    if consumer == "money-left":
        # "how much money does WHO have left" — the entity's general money
        # total (_entity_total: the SAME state-anchor + signed-event fold
        # the bare 'how much money does WHO have' ask already uses, so
        # "spends $14 on oranges" / "receives $50" / "saves $27 in March"
        # events it already signs by category polarity fold in exactly as
        # they would for that ask) minus its priced purchases
        # (_purchase_total, UNCHANGED — the increment-10 invariant travels
        # with it: any unpriced purchase or a 'splits/shares the cost'
        # predicate on this entity declines the WHOLE total rather than
        # risk a silently dropped term). The subtraction is safe from
        # double-counting: a priced purchase ("buys a toy for $8") never
        # emits a currency-measured Quantity at all (learn.py emits an
        # ITEM-measured Quantity plus a separate Price fact), so it is
        # invisible to _entity_total's currency fold and only ever
        # appears once, here.
        entity = query["entity"]
        measure = query.get("measure", "currency")
        singular = _resolve_measure(measure, store, reg)
        if singular is None:
            return Answer("decline", None,
                          f"measure {measure!r} is ambiguous across the facts")
        req_unit = query.get("req_unit")
        if not _check_req_unit(req_unit, singular, store, reg):
            return Answer(
                "decline", None,
                f"asked unit {req_unit!r} does not match resolved measure {singular!r}",
            )
        base = _entity_total(store, reg, entity, singular, log)
        if base is None:
            return Answer(
                "decline", None, f"no resolvable {singular!r} total for {entity!r}"
            )
        buys_exist = any(
            q.entity == entity and reg.word_in_category(q.verb, "purchase")
            for q in store.by_kind(Quantity)
        )
        spend = _purchase_total(store, reg, entity, log)
        if spend is None:
            if buys_exist:
                return Answer(
                    "decline", None,
                    f"{entity!r}'s purchases don't all resolve to a safe "
                    "total (unpriced item or a cost-split predicate)",
                )
            spend = 0.0
        remaining = evaluate(f"{base} - {spend}", {}, log, source="money-left")
        if remaining < 0:
            return Answer(
                "decline", None,
                f"{entity!r}'s purchases ({spend}) exceed the money total "
                f"({base}) — remaining money is negative",
            )
        return Answer(
            "number", remaining,
            f"{base} (money fold) minus {spend} spent on priced purchases",
        )

    if consumer == "change":
        # "how much change does/did/will WHO get/receive/take (back)"
        # (mining candidate change-asks): the buyer's stated TENDER minus
        # its priced purchases (_purchase_total, UNCHANGED — the
        # increment-10 invariant travels with it unscoped: any unpriced
        # purchase or a cost-splitting predicate on this entity declines
        # the whole total). A tender is the general SVO fold's own plain
        # currency Quantity EVENT for a tender_verb-category verb (pay/
        # give) — no new fact kind, no learn.py change needed (see
        # packs/difg-mined/categories/semantic.yaml's tender_verb
        # docstring). Both 'pay' and 'give' are already 'lose'-tagged,
        # signed event Quantities that already participate in the
        # general money fold elsewhere unchanged — this consumer is the
        # only thing that additionally reads one as a TENDER.
        #
        # UNLIKE money-left, a change ask presupposes a purchase actually
        # happened, so "no priced purchase found" here is a structural
        # extraction gap, never evidence of zero spend (a family visiting
        # an amusement park and paying per-person ticket prices the fold
        # can't multiply out — a real dev-train shape — is exactly this
        # gap) — this consumer DECLINES rather than defaulting spend to 0
        # whenever _purchase_total has nothing to offer, for any reason.
        entity = query["entity"]
        tenders = [
            q for q in store.by_kind(Quantity)
            if q.entity == entity
            and not q.is_state
            and reg.word_in_category(q.verb, "tender_verb")
            and reg.word_in_category(q.measure, "currency")
        ]
        if len(tenders) != 1:
            return Answer(
                "decline", None,
                f"{len(tenders)} tender facts known for {entity!r} — a "
                "change ask needs exactly one stated payment amount",
            )
        tender = tenders[0]
        # A discount/tip predicate on the SAME buyer (packs/difg-mined/
        # categories/semantic.yaml's `discount` category — 'coupon'/
        # 'discount'/'tip') means the raw priced-purchase total isn't
        # necessarily the final amount owed: the increment-10 'splits the
        # cost' unconsumed-predicate discipline, generalized from one
        # specific verb (divide) to a dobj CATEGORY, since a tip/discount
        # is stated as a noun object ("gave a tip", "used a coupon"), not
        # a verb. _purchase_total has no way to see this — decline rather
        # than risk a confident-wrong change amount.
        if any(
            p.subject == entity and p.dobj is not None
            and reg.word_in_category(p.dobj, "discount")
            for p in store.by_kind(Predication)
        ):
            return Answer(
                "decline", None,
                f"{entity!r} has a discount/tip predicate — the raw "
                "purchase total is not necessarily the final amount owed",
            )
        spend = _purchase_total(store, reg, entity, log)
        if spend is None:
            return Answer(
                "decline", None,
                f"no resolvable priced-purchase total for {entity!r} — a "
                "change ask needs at least one priced purchase to subtract",
            )
        change = evaluate(f"{tender.value} - {spend}", {}, log, source="change")
        if change < 0:
            return Answer(
                "decline", None,
                f"{entity!r}'s purchases ({spend}) exceed the tendered "
                f"amount ({tender.value}) — change would be negative",
            )
        return Answer(
            "number", change,
            f"{tender.value} (tender) minus {spend} spent on priced purchases",
        )

    if consumer == "deficit":
        # "how many more X does WHO need" — goal minus the entity's single
        # CURRENT holding (a stated STATE quantity, never the general event
        # fold: the desire verb's own spurious event Quantity, and the
        # target-verb's, both sit in the store unsignable/signed by
        # whatever the generic SVO scan gave them — reading the entity's
        # raw stated holding directly sidesteps that noise rather than
        # risking it). Commits only when EXACTLY one Goal fact and exactly
        # one current holding resolve; anything else is a genuine ambiguity.
        entity, measure = query["entity"], query["measure"]
        singular = _resolve_measure(measure, store, reg)
        if singular is None:
            return Answer("decline", None,
                          f"measure {measure!r} is ambiguous across the facts")
        goals = [
            g for g in store.by_kind(Goal)
            if g.entity == entity and g.measure == singular
        ]
        if len(goals) != 1:
            return Answer(
                "decline", None,
                f"{len(goals)} goal facts known for {entity!r}/{singular!r} — "
                "a deficit ask needs exactly one",
            )
        holdings = [
            q for q in store.by_kind(Quantity)
            if q.entity == entity and q.measure == singular and q.is_state
        ]
        if len(holdings) != 1:
            return Answer(
                "decline", None,
                f"{len(holdings)} current holdings known for {entity!r}/"
                f"{singular!r} — the deficit needs exactly one",
            )
        goal, holding = goals[0], holdings[0]
        deficit = evaluate(
            f"{goal.value} - {holding.value}", {}, log, source="deficit"
        )
        if deficit < 0:
            return Answer(
                "decline", None,
                f"goal {goal.value} is already met by current holding "
                f"{holding.value} for {entity!r}/{singular!r} — not a deficit",
            )
        return Answer(
            "number", deficit,
            f"{goal.value} goal - {holding.value} current {singular!r}",
        )

    if consumer == "membership-verdict":
        member, collection = query["member"], query["collection"]
        singular = reg.plural_to_singular.get(collection, collection)
        for f in store.by_kind(Membership):
            if f.member == member and f.collection == singular:
                return Answer("verdict", "yes" if f.polarity else "no", "membership fact")
        return Answer("verdict", "undetermined", "no membership fact either way")

    return Answer("decline", None, f"ask {ask.id} names unknown consumer {consumer!r}")
