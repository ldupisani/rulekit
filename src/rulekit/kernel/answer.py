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
from .evaluate import ArithmeticLog, evaluate
from .facts import FactStore
from .model import (
    Discount,
    Goal,
    GroupTotal,
    Membership,
    PartitionQuantity,
    PercentChange,
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


def _resolve_measure_against(
    measure: str, candidates: set[str], reg: Registry, journal=None
) -> str | None:
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
    # THE WEAKEST ORIGO OF ALL THE SITES: no sentence, no span, no entity — an empty
    # Origo(), because "which measure does this ask mean?" is asked from nowhere at all.
    # Note the site is TRI-STATE, and only this branch is a deictic resolution: zero
    # candidates PASSES THROUGH unchanged (a soft non-decline), while two-or-more is a
    # hard decline. Constant metric => byte-identical to the `len(present) == 1` it
    # replaces.
    winner = deixis.resolve(
        [deixis.Referent(dimension=deixis.DISCOURSE, key=m) for m in present],
        deixis.Origo(),
        deixis.constant,
        dimension=deixis.DISCOURSE,
        journal=journal,
        source="answer/resolve-measure",
    )
    if winner is not None:
        return winner.key
    if present:
        return None  # mixed measures of the category — ambiguous
    return singular


def _resolve_measure(
    measure: str, store: FactStore, reg: Registry, journal=None
) -> str | None:
    """Resolve the ask's measure word against the FACTS (see
    `_resolve_measure_against` for the category-fallback rules)."""
    in_store = {q.measure for q in store.by_kind(Quantity)}
    return _resolve_measure_against(measure, in_store, reg, journal=journal)


def _resolve_dimension_measure(
    measure: str, store: FactStore, reg: Registry, journal=None
) -> str | None:
    """mining candidate dimension-aggregate-asks: resolve a DIMENSION word
    ('height'/'weight'/'age'/'distance'/'balance'/'earnings'/'cost' — an
    aggregate ask's measure named by WHAT is measured, not by the unit) or
    a unit-family CATEGORY NAME BOUND DIRECTLY ('time_measure', the way
    ask/how-long-is-total-dimension binds its `measure` field — mirrors
    `currency`'s own `measure: currency` precedent one level up) against
    the FACTS, by declared FAMILY membership (packs/core-english/
    categories/core.yaml's `length_measure`/`mass_measure`/`time_measure`/
    `currency_measure`, each `dimension: true`) — UNIQUE-OR-DECLINE exactly
    like `_resolve_measure_against`'s own currency-category discipline:
    zero or >=2 distinct family members present among the in-store
    measures is unresolvable and returns None, never a guess.

    Deliberately a SEPARATE function from `_resolve_measure`/
    `_resolve_measure_against`, consulting a SEPARATE registry set
    (`reg.dimension_categories`, never `interchangeable_categories`) —
    called ONLY from `_combined_holder_totals` when the ask opts in via
    `dimension_measure: true` (the new imperative-headed / dimension-
    adjective totality asks). Every OTHER consumer (single-entity,
    unique-entity, difference, ...) keeps calling `_resolve_measure`
    unchanged, so a question that happens to bind 'height'/'weight' as a
    measure through any OTHER, PRE-EXISTING ask id is completely
    unaffected (the shared-function blast-radius HANDOFF invariant)."""
    in_store = {q.measure for q in store.by_kind(Quantity)}
    if measure in reg.dimension_categories:
        families = [measure]
    else:
        singular = reg.plural_to_singular.get(measure, measure)
        families = [
            c for c in reg.word_categories.get(singular, ())
            if c in reg.dimension_categories
        ]
    if not families:
        return None
    # Another site docs/deixis.md's inventory of fifteen missed: the same degenerate
    # rule again, over a DIFFERENT registry set (dimension_categories, never
    # interchangeable_categories). Same empty Origo() — a dimension ask asks from
    # nowhere too. Unlike _resolve_measure_against this one is BINARY, not tri-state:
    # zero candidates declines rather than passing through.
    winner = deixis.resolve(
        [
            deixis.Referent(dimension=deixis.DISCOURSE, key=m)
            for m in sorted(
                m for m in in_store
                if any(reg.word_in_category(m, f) for f in families)
            )
        ],
        deixis.Origo(),
        deixis.constant,
        dimension=deixis.DISCOURSE,
        journal=journal,
        source="answer/resolve-dimension-measure",
    )
    # zero or ambiguous family members in the facts — never guess
    return winner.key if winner is not None else None


def _check_req_unit(
    req_unit: str | None, singular: str, store: FactStore, reg: Registry, journal=None
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
    return _resolve_measure_against(req_unit, in_store, reg, journal=journal) == singular


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
    taken = set(match.consumed) | {u.uid for u in match.slots.values()}
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


def _verb_total(
    store: FactStore, entity: str, measure: str, verb: str, log: ArithmeticLog
) -> float | None:
    """Σ of an entity's quantities UNDER ONE VERB — the activity total
    ("how many did X sell"). Derived relation facts carry the verb too, so
    they participate; the by-verb resolution block prevents an event and
    its own re-derivation from both existing."""
    scoped = [
        q for q in store.by_kind(Quantity)
        if q.entity == entity and q.measure == measure
    ]
    matching = [q for q in scoped if q.verb == verb]
    if not matching:
        return None
    # THE CROSS-VERB TIME HOLE (docs/deixis.md §4's confident-wrong).
    #
    # This check used to run over `matching` — i.e. AFTER the verb filter — so it could
    # only ever see time-mixing WITHIN one verb. Cross-verb evidence was structurally
    # invisible to it:
    #
    #   "In January Benny adds $19 ... By the end of March he has $46.
    #    How many dollars did he add in March?"
    #
    #   matching = [add $19 @january]        <- the only 'add' fact
    #   the $46 @march state is verb='have', so it was FILTERED OUT BEFORE THIS LINE
    #   len({'january'}) == 1                <- no refusal
    #   => COMMITS 19. Gold is 8.
    #
    # Widening the set to every fact about this entity/measure makes the document's
    # timestamping visible: a document that speaks about MORE THAN ONE MOMENT cannot be
    # folded under a single verb without knowing WHICH moment is asked about. Until the
    # ask can say (see `reference_time`), the honest answer is to decline.
    #
    # Strictly a precision move: it can only turn a commit into a decline.
    if len({q.time for q in scoped}) > 1:
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
    OTHER priced purchases without double-counting the asked item.

    DISCOUNT (mining candidate discounted-purchase-totals): at most ONE
    in-play Discount fact (model.Discount, USE-gated for value accounting)
    is applied to the raw Σ price × qty total before it commits — a
    'total'-scoped discount multiplies the whole sum once (percent) or
    subtracts a flat amount once; a 'per_unit'-scoped discount (a flat
    amount stated "EACH") is multiplied by the summed purchased quantity
    first. TWO OR MORE stated discounts is a compounding scenario this
    consumer does not model (out of scope — see Discount's own docstring);
    facts.py's ordinary same-key collision already quarantines a second,
    differently-valued Discount, so `store.quarantined` is checked too —
    otherwise the ambiguity would silently vanish and this would commit
    the pre-discount total as though it were final, exactly the
    confident-wrong the whole USE-gating discipline exists to prevent."""
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
    base_expr = " + ".join(parts)
    if any(isinstance(f, Discount) for f in store.quarantined):
        return None  # two or more stated discounts — ambiguous, decline
    discounts = store.by_kind(Discount)
    if len(discounts) > 1:
        return None
    if not discounts:
        return evaluate(base_expr, {}, log, source="purchase-total")
    discount = discounts[0]
    if discount.scope == "total":
        expr = (
            f"({base_expr}) * (1 - {discount.value})" if discount.percent
            else f"({base_expr}) - {discount.value}"
        )
    elif discount.scope == "per_unit" and not discount.percent:
        qty_expr = " + ".join(str(q.value) for q in buys)
        expr = f"({base_expr}) - ({qty_expr}) * {discount.value}"
    else:
        return None  # an unmodeled scope/percent combination — decline
    return evaluate(expr, {}, log, source="purchase-total")


def _unit_price_from_total(
    store: FactStore, reg: Registry, item: str, log: ArithmeticLog
) -> tuple[str, float, float] | None:
    """'Katerina purchases 3 pots and 4 pans. Each pot costs $20. The total
    cost of Katerina's items is $100. What is the cost of 2 pans?' (mining
    candidate unit-price-from-total, re-cut of the batch-47 review kill): a
    stated GRAND TOTAL for one buyer's whole purchase, minus every OTHER
    line item's already-priced cost (`_purchase_total`, UNCHANGED —
    exclude_item, the increment-19 remaining-budget discipline, reused
    verbatim), leaves the asked item's own total spend; dividing by its
    stated purchased COUNT recovers its per-unit price.

    The buyer is resolved STRUCTURALLY, never via a `who` slot (neither ask
    surface names one): exactly one entity may hold a purchase-verb
    Quantity of `item` — the same single-holder discipline
    ask/how-much-item-cost's item-cost consumer already applies. The grand
    total is read from an entity-OWNED currency Quantity (condense.py's
    merge-possessive: "TOM's items" -> owner='tom' on the copular "the
    total cost ... is $X" fold) — deliberately narrower than GroupTotal's
    unowned sum-across-the-passage reading, so this never fires on a
    total that belongs to a DIFFERENT buyer or to no buyer at all.

    Declines (never guesses) unless: (i) exactly one purchase-verb
    Quantity of `item` exists for that buyer, (ii) exactly one owned
    currency total exists for the SAME buyer, (iii) every OTHER
    purchase-verb item that buyer holds is fully priced (or there are
    none) — `_purchase_total`'s own definitive-or-decline invariant
    (increment 10) travels here unscoped, and (iv) the residual spend on
    `item` is non-negative. Returns (entity, unit_price, count) so a
    caller can multiply by its own asked quantity (1 for a bare "how much
    does each ITEM cost", or the question's own stated N)."""
    holders = [
        q for q in store.by_kind(Quantity)
        if q.measure == item and reg.word_in_category(q.verb, "purchase")
    ]
    if len(holders) != 1:
        return None
    holder = holders[0]
    entity = holder.entity
    count = holder.value
    if count <= 0:
        return None
    totals = [
        q for q in store.by_kind(Quantity)
        if q.owner == entity and reg.word_in_category(q.measure, "currency")
    ]
    if len(totals) != 1:
        return None
    grand_total = totals[0].value
    other_items = {
        q.measure for q in store.by_kind(Quantity)
        if q.entity == entity and q.measure != item
        and reg.word_in_category(q.verb, "purchase")
    }
    if other_items:
        other_total = _purchase_total(store, reg, entity, log, exclude_item=item)
        if other_total is None:
            return None
    else:
        other_total = 0.0
    residual = evaluate(
        f"{grand_total} - {other_total}", {}, log, source="unit-price-from-total"
    )
    if residual < 0:
        return None
    unit_price = evaluate(
        f"{residual} / {count}", {}, log, source="unit-price-from-total"
    )
    return entity, unit_price, count


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
    accumulate signed by the verb's category polarity.

    PERCENT CHANGE (mining candidate percent-change-values): an in-play
    PercentChange fact (model.PercentChange, USE-gated for value
    accounting like Discount/Rate/Price/Goal/GroupTotal) for this SAME
    entity scales the state+event total by (1 +/- its stated fraction),
    applied in ASCENDING SENTENCE ORDER — the same strict-sentence-order
    chaining convention the fraction/rest machinery already uses, so a
    "decreased by 15%, increased by 40%" pair composes correctly instead
    of arbitrarily. This is UNCONDITIONAL, not an opt-in parameter: the
    fact kind is brand new, so no PercentChange fact could ever have
    existed for ANY pre-increment caller — every existing call site's
    behavior is untouched by construction, and only a genuinely NEW
    percent-change event for this exact entity ever changes the answer
    (the HANDOFF shared-function-blast-radius discipline, satisfied here
    by the new fact's own non-existence everywhere else rather than by a
    threaded flag). Scoped to 'currency'-category measures only — every
    structural sample this increment targets is monetary, and the
    emitting pattern rule itself gates its dobj to `cat: currency`, so a
    non-currency fold never even has a PercentChange fact to find. Two
    percent-change events for the SAME entity in the SAME sentence share
    one `occurrence` and collide at facts.py's ordinary same-key path
    (quarantined) — checked here exactly like Discount's own compounding
    guard, so an unmodeled same-sentence pair declines rather than
    silently picking one."""
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
    if reg.word_in_category(measure, "currency"):
        changes = [pc for pc in store.by_kind(PercentChange) if pc.entity == entity]
        if changes:
            if any(
                isinstance(f, PercentChange) and f.entity == entity
                for f in store.quarantined
            ):
                return None  # a same-sentence compounding pair — ambiguous, decline
            for pc in sorted(
                changes, key=lambda p: p.occurrence if p.occurrence is not None else 0
            ):
                op = "+" if pc.sign > 0 else "-"
                expr = f"({expr}) * (1 {op} {pc.value})"
    return evaluate(expr, {}, log, source="fold")


def _conversion_factor(reg: Registry, from_unit: str, to_unit: str) -> float | None:
    """mining candidate dimension-difference-asks: a MULTI-HOP factor
    from_unit -> to_unit over the `reg.conversions` graph (BFS; the table
    itself is small — a handful of declared pairs, both directions already
    stored by the registry build). Handles chains reg.conversions never
    states directly ("yard" -> "foot" -> "inch": the pack declares
    yard/foot and foot/inch, never yard/inch) without inventing a second
    conversions table. Returns None when NO declared path connects the two
    units at all (e.g. 'dog' has no relationship to 'inch') — the caller's
    signal that the units are simply unrelated, not that a conversion is
    missing."""
    if from_unit == to_unit:
        return 1.0
    seen = {from_unit}
    frontier = [(from_unit, 1.0)]
    while frontier:
        next_frontier = []
        for unit, factor in frontier:
            for (a, b), f in reg.conversions.items():
                if a == unit and b not in seen:
                    total = factor * f
                    if b == to_unit:
                        return total
                    seen.add(b)
                    next_frontier.append((b, total))
        frontier = next_frontier
    return None


def _entity_total_convertible(
    store: FactStore, reg: Registry, entity: str, measure: str, log: ArithmeticLog
) -> float | None:
    """mining candidate dimension-difference-asks: the opt-in sibling of
    `_entity_total` for a difference ask whose measure is a UNIT ("inches")
    that a compound-stated holder splits across TWO OR MORE separate
    Quantity facts for the SAME entity ("Vlad is 6 feet, 3 inches tall" —
    foot=6 and inch=3, two facts, one entity). The bare `_entity_total
    (entity, 'inch')` fold only ever sees the 3, discarding the feet
    entirely — the naive prototype's confident-wrong (75/34 read as
    3/10 — a 41-inch gap answered as 7). Folds every STATE quantity this
    entity holds whose measure has a declared `_conversion_factor` path to
    the target measure into one total; a quantity under a measure with NO
    such path (an unrelated holding, e.g. "has 3 dogs") is left OUT of the
    fold entirely rather than guessed at. Declines (returns None) the
    instant NOTHING this entity holds converts to the target measure at
    all — the same definitive-or-decline discipline `_entity_total` itself
    keeps, now over the WHOLE convertible family rather than one bare
    measure, so a holder whose only stated quantity is genuinely
    unconvertible to what's asked stays declined rather than committing a
    wrong from an empty fold.

    Never called except when a caller opts in (`difference`'s
    `fold_units` query flag, set only by the NEW unit-qualified
    dimension/age-comparative asks) — every PRE-EXISTING `difference` ask
    keeps calling the bare `_entity_total` exactly as before (the shared-
    function blast-radius invariant: this fold is felt by nobody who
    didn't ask for it)."""
    state = [q for q in store.by_kind(Quantity) if q.entity == entity and q.is_state]
    if not state:
        return None
    if len({q.time for q in state}) > 1:
        return None  # facts from DIFFERENT times — time arithmetic is unbuilt
    parts: list[str] = []
    for q in state:
        factor = _conversion_factor(reg, q.measure, measure)
        if factor is None:
            continue  # unrelated to this measure entirely — never folded
        parts.append(str(q.value) if factor == 1.0 else f"{q.value} * {factor}")
    if not parts:
        return None
    return evaluate(" + ".join(parts), {}, log, source="dimension-fold")


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


def _qualified_variant_total(
    store: FactStore, reg: Registry, entity: str, measure: str, log: ArithmeticLog
) -> float | None:
    """Bare-measure roll-up over attribute-qualified measure variants
    (mining candidate qualified-measure-keys, gap (c)): 'Sam has 30 red
    balls. Sam has 36 green balls. How many balls does Sam have?' — no
    bare 'ball' fact exists (facts.py's admit-time measure-qualifier split,
    increment 70, already re-keyed both into 'ball[red]'/'ball[green]'),
    so the ordinary bare-key lookup the `single-entity` consumer already
    tries comes back empty. Reached ONLY once that lookup (and every other
    fallback) has already failed, and only for an ask that opted in via
    `sum_measure_variants` (never a blanket widening of this consumer —
    the HANDOFF shared-path invariant).

    Every `measure[qualifier]` sibling this ENTITY holds is summed via
    `_entity_total` (so an ambiguous per-sibling fold — mixed times,
    unsigned events — declines the WHOLE aggregate, exactly like
    `_purchase_total`/`_superordinate_total`: definitive or decline,
    never a partial sum). Fewer than two siblings is not a roll-up at
    all — a single qualified fact answering a bare-measure ask would
    silently assume no other variant exists — so this declines rather
    than guess. A stated `GroupTotal` for the same bare measure means the
    document already names an explicit total some OTHER mechanism should
    reconcile against (mirroring the existing distributive-each guard
    elsewhere in this module): summing the qualified variants here too
    would risk double-counting against it, so this declines instead."""
    if any(g.measure == measure for g in store.by_kind(GroupTotal)):
        return None
    prefix = f"{measure}["
    siblings = sorted({
        q.measure for q in store.by_kind(Quantity)
        if q.entity == entity and q.measure.startswith(prefix) and q.measure.endswith("]")
    })
    if len(siblings) < 2:
        return None
    parts: list[str] = []
    for sibling in siblings:
        subtotal = _entity_total(store, reg, entity, sibling, log)
        if subtotal is None:
            return None
        parts.append(str(subtotal))
    return evaluate(" + ".join(parts), {}, log, source="qualified-variant-total")


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
    # `dimension_measure` (mining candidate dimension-aggregate-asks):
    # bound ONLY by the new imperative-headed / dimension-adjective
    # totality asks ("calculate their combined height", "how long is the
    # total X") — a no-op for every other 'combined'/'average' ask, which
    # never sets this key and keeps calling `_resolve_measure` exactly as
    # before. See `_resolve_dimension_measure`'s own docstring.
    if query.get("dimension_measure"):
        singular = _resolve_dimension_measure(measure, store, reg, journal=log.journal)
    else:
        singular = _resolve_measure(measure, store, reg, journal=log.journal)
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
        # mining candidate distributive-holder-enum: an entity whose OWN
        # Quantity(measure=singular) was CONSUMED by a bridging synth
        # (synth/container-contents, synth/distributive-container-total —
        # see ArithmeticLog.consumed_rate_keys's own docstring) to derive
        # some OTHER holder's total is a per-unit RATE-DEFINING artifact,
        # not an independent holding — "each row holds 5 chairs" must not
        # be summed alongside the bridged per-holder totals it was
        # composed into (the documented oversum: packs/core-english/
        # categories/core.yaml's time_measure note, gold 40 vs 44). This
        # can only ever DROP a spurious extra holder the synth already
        # proved was consumed elsewhere — it never adds one, and a holder
        # set that falls below two still hits the exact same decline below
        # exactly as before this fix.
        entities = [
            e for e in entities if (e, singular) not in log.consumed_rate_keys
        ]
        # SUPERORDINATE fallback (subtype-total over an aggregate ask): "how many
        # pieces of litter did they pick up altogether?" — no entity holds the
        # asked measure ('piece', or 'litter' itself) DIRECTLY, but that measure
        # or its partitive substance is a pack-declared SUPERORDINATE whose
        # subtypes (bottle, can) ARE held. The aggregate marker means "all of
        # it", which for a superordinate is the subtype sum, so reuse the
        # single-entity `_superordinate_total` per subtype-holder (verb-scoped,
        # definitive-or-decline). This is the ONLY path that reads a superordinate
        # through the combined/aggregate ask — `_superordinate_total` was
        # otherwise reachable only from the single-entity consumer.
        if not entities:
            super_measure = next(
                (c for c in (singular, measure_substance)
                 if c and c in reg.superordinate_categories),
                None,
            )
            if super_measure is not None:
                members = set(reg.category_members.get(super_measure, ()))
                sub_holders = sorted(
                    {q.entity for q in store.by_kind(Quantity) if q.measure in members}
                )
                v = query.get("verb", "have")
                verb_arg = None if (
                    v in ("have", "be") or reg.word_in_category(v, "state")
                ) else v
                sub_totals: list[float] | None = []
                for e in sub_holders:
                    t = _superordinate_total(store, reg, e, super_measure, log, verb=verb_arg)
                    if t is None:
                        sub_totals = None
                        break
                    sub_totals.append(t)
                if sub_totals:
                    return sub_holders, sub_totals
        if len(entities) < 2 and not (
            len(entities) == 1 and query.get("subject_number") == "singular"
        ):
            # "how many do THEY have ALTOGETHER" asserts plurality — a
            # one-entity sum usually means a mangled parse (the permissive
            # scan's Σ-over-one artifact), and declining costs no real
            # coverage.
            #
            # EXCEPT a SINGULAR subject ("how much does HE have total"): the
            # aggregate marker there sums that ONE holder's OWN state+event
            # holdings (Henry had $54 and got $2 -> $56), never a multi-holder
            # combination, so exactly one holder is correct, not a mangled
            # parse. The >=2 guard's missed-second-holder rationale is a PLURAL
            # concern. Surfaced by the subject-gapping fix: with the second
            # clause's subject correctly attributed to Henry (not the object
            # 'toys'), the lucky two-holder sum that used to answer this
            # collapses to the real single holder.
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
    # `holder_count` (mining candidate combined-ask-holder-surfaces,
    # widened by mining candidate dimension-aggregate-asks to cover the
    # 'average' consumer too): bound ONLY by the cardinal-holder-set asks
    # ("the three of them have ... in total", "the average height of the
    # four people") via `holder_count: "{n.value}"`; a no-op for every
    # other 'combined'/'average' ask, which never sets this key. Those
    # asks bind no a/b, so entities above enumerates EVERY holder of the
    # measure — the ask's stated cardinal never selects which entities are
    # summed, it only ASSERTS how many there should be. When the premises
    # under-read a holder (a relation left one of N named holders
    # unresolved), the enumeration comes back short of the stated
    # cardinal and silently summing/averaging that subset would be a
    # confident wrong — decline instead. Checked HERE, in the SHARED
    # helper, rather than duplicated per consumer: 'combined' already had
    # this exact check inline; 'average' never did (a pre-existing gap —
    # no 'average' ask ever bound `holder_count` before this candidate's
    # own cardinal-holder-set ask, ask/imperative-average-dimension,
    # which is what surfaced it on dev-holdout: "average height of the
    # FOUR people" over premises that only resolve three holders averaged
    # the wrong three instead of declining). Moving the check here is
    # BEHAVIOR-PRESERVING for every existing 'combined' caller (same
    # condition, same decline) and closes the gap for 'average' for free.
    holder_count = query.get("holder_count")
    if holder_count is not None and int(float(holder_count)) != len(entities):
        return Answer(
            "decline", None,
            f"ask names {holder_count} holders; premises give "
            f"{len(entities)} ({entities})",
        )
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

    if consumer == "geometry":
        # Formula-selection (difg geometry domain): "what is the AREA of a CIRCLE
        # with RADIUS 5?" -> look up the (shape, quantity) formula in the pack's
        # declarative table, bind the named dimensions from the ask, evaluate.
        # NO per-domain Python (constitution): the formulas are DATA, this branch
        # is the generic evaluator. Definitive-or-decline: a formula whose named
        # dimensions are not all bound (wrong/missing dimension for the shape)
        # evaluates to a NameError and declines rather than guess.
        shape, quantity = query.get("shape"), query.get("quantity")
        expr = reg.geometry_formulas.get((shape, quantity))
        if expr is None:
            return Answer(
                "decline", None,
                f"no geometry formula for {quantity!r} of a {shape!r}",
            )
        env = {"pi": 3.141592653589793}
        for d, v in ((query.get("dim1"), query.get("val1")),
                     (query.get("dim2"), query.get("val2"))):
            if d and v not in (None, ""):
                env[d] = float(v)
        try:
            value = evaluate(expr, env, log, source="geometry")
        except Exception:
            return Answer(
                "decline", None,
                f"{quantity!r} of a {shape!r} needs dimensions its given ones "
                "do not supply",
            )
        # A pi-bearing area/volume is irrational; present it to 2 decimals, the
        # conventional precision for a geometry answer (and difg's own gold
        # rounding). Exact integer results (rectangle area 24, cube volume 27)
        # are unchanged by the round.
        return Answer(
            "number", round(value, 2), f"geometry: {quantity} of {shape} = {expr}"
        )

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
        # mining candidate qualified-measure-keys: the MEASURE-side mirror
        # of `qualifier` above, one field over — "how many GREEN apples
        # does Sam have?" resolves the bare measure ("apple") the same way
        # UNLESS a same-key VALUE conflict forced facts.py to re-key it to
        # "apple[green]" (increment 70). Read off the ask's OWN `item`
        # token's qualifier feature (bound only on ask ids that opt in via
        # `measure_qualifier: "{item.qualifier}"` — a no-op empty string
        # everywhere else), never the entity-level `entity_qualifier`.
        measure_qualifier = query.get("measure_qualifier")
        singular = _resolve_measure(measure, store, reg, journal=log.journal)
        if singular is None:
            return Answer("decline", None,
                          f"measure {measure!r} is ambiguous across the facts")
        req_unit = query.get("req_unit")
        if not _check_req_unit(req_unit, singular, store, reg, journal=log.journal):
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
        # distributive-container consumer — the single-entity mirror of the
        # unique-entity GroupTotal branch below (line ~1548). A `GroupTotal`
        # for this SAME measure is a distributive WHOLE ("150 shelves, each with
        # 15 books" -> saturate's book=2250). When the NAMED entity is itself a
        # counted container ("there were 150 shelves" -> a Quantity whose MEASURE
        # is this entity) that also HOLDS the asked measure directly ("each shelf
        # had 15 books"), its own Quantity is the PER-CONTAINER RATE, and the ask
        # ("how many books were on the shelves") wants the WHOLE — the GroupTotal
        # is exactly it. Commit it. This is SAFE ONLY because the group total is
        # now trustworthy: saturate's distributive-container-total synth was
        # tightened (learn.py provenance.distributive gate) so a SPECIFIC
        # instance's count ("bucket B has 30", "the first warehouse has 400") no
        # longer masquerades as a per-container rate — those garbage totals are
        # gone, so preferring the total no longer risks committing one. Stays
        # TIGHT: fires ONLY on the container signature, so a named holder whose
        # fold is genuinely correct and merely coexists with an unrelated
        # document total ("Tom has 15 books" + a stated total) is untouched —
        # `tom` is not a counted measure. Two rival totals stay a decline.
        matching_totals = [gt for gt in store.by_kind(GroupTotal) if gt.measure == singular]
        if matching_totals:
            holds_rate = any(
                q.entity == entity and q.measure == singular
                for q in store.by_kind(Quantity)
            )
            entity_is_counted = any(
                q.measure == entity for q in store.by_kind(Quantity)
            )
            if holds_rate and entity_is_counted:
                if len(matching_totals) == 1:
                    total = evaluate(
                        f"{matching_totals[0].value}", {}, log, source="group-total"
                    )
                    return Answer(
                        "number", total,
                        f"group total of {singular!r} over the counted {entity!r} containers",
                    )
                return Answer(
                    "decline", None,
                    f"{entity!r} holds a per-container rate of {singular!r} but "
                    "several rival group totals exist — cannot tell which whole is meant",
                )
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
        # mining candidate qualified-measure-keys: scopes the generic
        # bare-measure fallback to compatible siblings only, exactly like
        # `qualifier_store` above but keyed on `measure_qualifier` instead
        # of `qualifier` — a bare 'apple' fact tagged 'red' must NEVER
        # answer a question asking specifically about GREEN apples just
        # because a same-key collision never happened to force the split.
        measure_qualifier_store = store
        if measure_qualifier:
            measure_qualifier_store = FactStore(facts=[
                q for q in store.by_kind(Quantity)
                if q.measure != singular
                or q.measure_qualifier is None
                or q.measure_qualifier == measure_qualifier
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
            if total is None and measure_qualifier:
                total = _verb_total(store, entity, f"{singular}[{measure_qualifier}]", ask_verb, log)
            if total is None:
                scoped = (
                    owner_store if owner
                    else qualifier_store if qualifier
                    else measure_qualifier_store
                )
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
        if total is None and measure_qualifier:
            # mining candidate qualified-measure-keys: the exact qualified
            # key first (the conflict-split case) — mirrors the owner/
            # entity_qualifier two-lookup shape above, keyed on the
            # MEASURE's own qualifier instead of the entity's.
            total = _entity_total(store, reg, entity, f"{singular}[{measure_qualifier}]", log)
        if total is None:
            scoped = (
                owner_store if owner
                else qualifier_store if qualifier
                else measure_qualifier_store
            )
            total = _entity_total(scoped, reg, entity, singular, log)
        if total is None and query.get("sum_measure_variants") and not measure_qualifier:
            # gap (c), mining candidate qualified-measure-keys: "Sam has 30
            # red balls. Sam has 36 green balls. How many balls does Sam
            # have?" — no bare 'ball' fact exists (facts.py's admit-time
            # qualifier split already re-keyed both into
            # 'ball[red]'/'ball[green]'), so every lookup above comes back
            # empty. Opt-in per ask id (never a blanket widening of this
            # consumer) and only for a BARE ask (`not measure_qualifier`):
            # a question naming one SPECIFIC variant must never silently
            # roll up every colour instead.
            total = _qualified_variant_total(store, reg, entity, singular, log)
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
        # container-contents + loose composition ("Beth has 4 packs of crayons.
        # Each pack has 10 crayons. She also has 6 extra crayons. How many crayons
        # altogether?" -> 4*10 + 6 = 46). The fold above gave the holder's LOOSE
        # amount of the measure; if the holder ALSO owns containers whose contents
        # are exactly a synthesized GroupTotal for this measure, that whole is a
        # DISJOINT part the loose fold missed — add it. TIGHT on two counts: the
        # group total must equal THIS holder's own container-count times the
        # per-container rate (G == N*r), which both attributes the holder-less
        # total to this holder and confirms it is the containers' contents; and it
        # never fires when the loose fold already equals the whole (G == total),
        # so a fold that already absorbed the container contents (via
        # synth/container-contents, when the holder held no loose amount) is not
        # double-counted. Only the container-contents family reaches here.
        group_totals = [gt for gt in store.by_kind(GroupTotal) if gt.measure == singular]
        if len(group_totals) == 1 and abs(group_totals[0].value - total) > 1e-9:
            g = group_totals[0].value
            for c_fact in store.by_kind(Quantity):
                if c_fact.entity != entity or c_fact.measure == singular:
                    continue
                rates = [
                    q for q in store.by_kind(Quantity)
                    if q.entity == c_fact.measure and q.measure == singular
                ]
                if len(rates) == 1 and abs(c_fact.value * rates[0].value - g) < 1e-9:
                    composed = evaluate(
                        f"{total} + {g}", {}, log, source="container-plus-loose"
                    )
                    return Answer(
                        "number", composed,
                        f"{entity!r}'s loose {singular!r} ({total:g}) plus its "
                        f"{c_fact.measure!r} contents (group total {g:g})",
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

    if consumer == "age-projected":
        # mining candidate relation-standard-frames: "How old will X be in/
        # after N years?" / "...N years from now?" — a PROJECTED age ask,
        # sibling of ask/how-old-is: the SAME current-age quantity
        # (_entity_total, measure read from `query["measure"]` — constitution
        # rule 1, never a hardcoded 'year' literal; the ask's own `resolves:`
        # block commits `measure: year` exactly as ask/how-old-is does)
        # plus the stated offset named IN THE QUESTION ITSELF, added rather
        # than compared. Gated on this ask id alone (via the `consumer`
        # key), never a widening of `single-entity`'s own state-ask branch:
        # a projected ask's offset is not a measure/entity slot that
        # branch's owner/qualifier machinery could even express.
        entity, measure = query["entity"], query["measure"]
        offset_raw = query.get("offset")
        if offset_raw is None:
            return Answer(
                "decline", None, "projected age ask has no stated year offset",
            )
        offset = evaluate(str(offset_raw), {}, log, source="age-projected-offset")
        base = _entity_total(store, reg, entity, measure, log)
        if base is None:
            return Answer(
                "decline", None, f"no {measure} quantity known for {entity!r}",
            )
        return Answer(
            "number", base + offset,
            f"{entity!r}'s current {measure} {base} + stated offset {offset}",
        )

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
        singular = _resolve_measure(measure, store, reg, journal=log.journal)
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
        # An ENTITY-LESS ask ("how many balloons are left?") has, by construction, no
        # reference point: the origo it wants is the narrative present, and there is
        # none. Hence the empty Origo(). Constant metric => byte-identical to the
        # `len(entities) != 1` it replaces; the decline reason is preserved verbatim.
        if deixis.resolve(
            [deixis.Referent(dimension=deixis.PERSON, key=e) for e in entities],
            deixis.Origo(),
            deixis.constant,
            dimension=deixis.PERSON,
            journal=log.journal,
            source="answer/unique-entity",
        ) is None:
            return Answer(
                "decline", None,
                f"{len(entities)} entities hold {singular!r} — an entity-less "
                "ask needs exactly one",
            )
        entity_less_totals = [gt for gt in store.by_kind(GroupTotal) if gt.measure == singular]
        if entity_less_totals:
            # mining candidate distributive-each-totals: a GroupTotal for this
            # SAME measure means the lone entity's own Quantity is a PER-CONTAINER
            # rate ("20 chairs in each row"), not the group's whole. An entity-less
            # ask ("how many chairs are there IN ALL?") wants the whole — the
            # GroupTotal is exactly it, so COMMIT it. This shipped first as a
            # DECLINE (folding the lone rate as the total is the confident wrong
            # GroupTotal exists to prevent); the entity-less mirror of the
            # single-entity container consumer above, it can commit now for the
            # SAME reason that path can: saturate's synth was tightened
            # (Provenance.distributive) so a specific instance's count no longer
            # masquerades as a per-container rate, so the surviving total is
            # trustworthy. Two rival totals stay a decline.
            if len(entity_less_totals) == 1:
                total = evaluate(
                    f"{entity_less_totals[0].value}", {}, log, source="group-total"
                )
                return Answer(
                    "number", total,
                    f"group total of {singular!r} over the counted containers",
                )
            return Answer(
                "decline", None,
                f"{singular!r} has several rival group totals — "
                "an entity-less ask cannot tell which whole is meant",
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
        # `holder_count` is checked inside `_combined_holder_totals`
        # itself (see that function's own comment) — shared by this
        # branch and 'average' below.
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
        singular = _resolve_measure(measure, store, reg, journal=log.journal)
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
        # mining candidate partitive-measure-asks: the SAME opt-in
        # decline-safety guard `single-entity`/`unique-entity`/`combined`
        # already call (answer.py's `_measure_substance_guard`,
        # partitive-measure-ask-slot) — a partitive-tail difference ask
        # ("how many more PAIRS OF SHOES does Ann have than Bob?") binds
        # `measure_substance` only per its own ask id (every existing,
        # non-partitive `difference` ask leaves it unset, so this call is
        # a no-op for them — `measure_substance` is never truthy). Scoped
        # to exactly the two resolved holders: Bob's own quantity being a
        # DIFFERENT substance under the same bare measure noun ("Bob has 5
        # pairs of SOCKS") must decline rather than silently answer a
        # 'shoes' question from Bob's sock count — the identical sibling-
        # borrow hazard `_measure_substance_guard`'s own docstring names.
        measure_substance = query.get("measure_substance")
        if measure_substance:
            guard = _measure_substance_guard(store, singular, measure_substance, entities=[a, b])
            if guard is not None:
                return guard
        ask_verb = query.get("verb", "have")
        # mining candidate dimension-difference-asks: opt-in fold across
        # convertible sibling units (see `_entity_total_convertible`'s own
        # docstring) — set ONLY by the new unit-qualified dimension/age-
        # comparative asks. Every pre-existing `difference` ask (how-many-
        # more, what-is-the-difference-named/-pronoun, the partitive
        # sibling) never binds `fold_units`, so this branch is dead code
        # for all of them — zero behavior change (shared-function
        # blast-radius invariant).
        fold_units = query.get("fold_units") == "true"
        if ask_verb in ("have", "be") or reg.word_in_category(ask_verb, "state"):
            if fold_units:
                ta = _entity_total_convertible(store, reg, a, singular, log)
                tb = _entity_total_convertible(store, reg, b, singular, log)
            else:
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

    if consumer == "label-difference":
        # mining candidate ratio-split-premises: the LABEL-comparand
        # sibling of 'difference' — "how many more BOYS than GIRLS are
        # there?" names no holder at all; `a`/`b` are plain measure
        # nouns, each resolved independently via the SAME exactly-one-
        # holder discipline the 'unique-entity' consumer already uses
        # (definitive-or-decline, never guessed), then required to share
        # exactly ONE holder — the shape every ratio-derived label pair
        # has by construction (both labels are shares of the SAME
        # collection's SAME holder). Two labels that resolve to two
        # DIFFERENT holders decline rather than subtract two unrelated
        # entities' totals ("Tom has 5 apples. Jerry has 3 oranges." must
        # never silently answer 2 for "how many more apples than
        # oranges?"). This is a BRAND-NEW consumer id — every existing
        # `difference` ask keeps its own a/b as ENTITY NAMES, resolved by
        # the branch above, completely untouched by this one.
        measure_a = reg.plural_to_singular.get(query["a"], query["a"])
        measure_b = reg.plural_to_singular.get(query["b"], query["b"])
        entities_a = sorted(
            {q.entity for q in store.by_kind(Quantity) if q.measure == measure_a}
        )
        entities_b = sorted(
            {q.entity for q in store.by_kind(Quantity) if q.measure == measure_b}
        )
        if len(entities_a) != 1 or len(entities_b) != 1 or entities_a != entities_b:
            return Answer(
                "decline", None,
                f"{measure_a!r}/{measure_b!r} need exactly one SHARED holder "
                f"— found {entities_a} / {entities_b}",
            )
        (holder,) = entities_a
        ta = _entity_total(store, reg, holder, measure_a, log)
        tb = _entity_total(store, reg, holder, measure_b, log)
        if ta is None or tb is None:
            return Answer(
                "decline", None, f"missing a total for {measure_a!r} or {measure_b!r}"
            )
        return Answer(
            "number",
            evaluate(f"abs({ta} - {tb})", {}, log, source="label-difference"),
            f"|{measure_a} - {measure_b}| on {holder!r}",
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
        # A THIRD unique-holder site the deixis.md inventory missed. Same shape, same
        # empty origo, same rule.
        if deixis.resolve(
            [deixis.Referent(dimension=deixis.PERSON, key=e) for e in entities],
            deixis.Origo(),
            deixis.constant,
            dimension=deixis.PERSON,
            journal=log.journal,
            source="answer/partition-total-holder",
        ) is None:
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
        # mining candidate generic-unit-price-premises: reading MORE price
        # frames (subject-side generics, floating-each relative clauses)
        # means the SAME per-unit price can now legitimately be RESTATED
        # via two different surface forms in one document ("A mug costs 8
        # dollars. Mugs are 8 dollars each.") — two Price facts that fully
        # AGREE on value are the same fact said twice, not an ambiguity;
        # facts.py's key() differs (verb/occurrence) so they never dedupe
        # at admission. Only a genuine VALUE disagreement is still the
        # increment-19 ambiguity this guard exists to catch.
        distinct_values = {p.value for p in prices}
        if len(distinct_values) != 1:
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

    if consumer == "unit-price-from-total":
        # "how much does/did each ITEM cost?" / "what is the cost of N
        # ITEM?" (mining candidate unit-price-from-total, re-cut of the
        # batch-47 review kill): the per-unit price is never stated —
        # `_unit_price_from_total` recovers it from a stated GRAND TOTAL
        # minus every other already-priced line item, divided by the
        # asked item's own purchased count (definitive-or-decline, the
        # increment-10 discipline traveling through `_purchase_total`
        # unchanged). The ask's own stated quantity (`qty_value`, when
        # present — "cost of N ITEM") multiplies the recovered unit price;
        # a bare "each ITEM" ask (no stated quantity) leaves it at 1.
        item = reg.plural_to_singular.get(query["item"], query["item"])
        resolved = _unit_price_from_total(store, reg, item, log)
        if resolved is None:
            return Answer(
                "decline", None,
                f"no resolvable grand-total residual for {item!r} — needs "
                "exactly one buyer, one owned grand total, and every "
                "other purchased item priced",
            )
        entity, unit_price, _count = resolved
        qty_raw = query.get("qty_value")
        if qty_raw is None:
            return Answer(
                "number", unit_price,
                f"{entity!r}'s grand total minus other priced purchases, "
                f"divided by {item!r}'s purchased count",
            )
        qty = evaluate(str(qty_raw), {}, log, source="unit-price-from-total-qty")
        total = evaluate(
            f"{qty} * {unit_price}", {}, log, source="unit-price-from-total"
        )
        return Answer(
            "number", total,
            f"{qty} * {unit_price} — question qty x recovered unit price "
            f"of {item!r}",
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
        singular = _resolve_measure(measure, store, reg, journal=log.journal)
        if singular is None:
            return Answer("decline", None,
                          f"measure {measure!r} is ambiguous across the facts")
        req_unit = query.get("req_unit")
        if not _check_req_unit(req_unit, singular, store, reg, journal=log.journal):
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
        singular = _resolve_measure(measure, store, reg, journal=log.journal)
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
