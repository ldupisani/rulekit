"""The total folds: every helper that turns facts into ONE number.

Moved out of `answer.py` UNCHANGED (session-4 refactor, step C) — each
function is byte-for-byte the one that lived there, and the consumer golden
master (tests/test_consumer_golden_master.py) plus the full eight-slice gate
pinned the move. `answer.py` keeps the dispatch (`answer()`), the `Answer`
type and the question-side reader (`_question_reference_time`); this module
holds the store-side arithmetic: the signed entity fold and its variants,
purchase/revenue/superordinate/qualified totals, the combined-holder
enumeration, and the conversion plumbing they share.

The import direction is one-way BY DESIGN: totals -> answer (for `Answer`)
and totals -> nothing else in the kernel above it. `answer.py` must never
import this module back — `_unit_price_from_total` lives HERE rather than
there for exactly that reason (it folds `_purchase_total`).
"""

from __future__ import annotations

from ..data.registry import Registry
from .evaluate import ArithmeticLog, evaluate
from .facts import FactStore
from .model import (
    Discount,
    GroupTotal,
    PercentChange,
    Predication,
    Price,
    Quantity,
    Rate,
)
from .answer import Answer
from .measures import (
    _measure_substance_guard,
    _resolve_dimension_measure,
    _resolve_measure,
)


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
    store: FactStore, reg: Registry, entity: str, measure: str, log: ArithmeticLog,
    invert_events: bool = False,
) -> float | None:
    """The single-entity fold: state quantities anchor, event quantities
    accumulate signed by the verb's category polarity.

    `invert_events` (OPT-IN, default False — every existing caller is
    byte-identical) folds the START state instead of the current one: the stated
    quantity is the END state, so the events are UNDONE rather than applied.
    "Paco ate 19 cookies and had 35 cookies left" folds to 35 + (-19) = 16 today,
    which is the right answer to "how many does he have" and the WRONG answer to
    "how many did he have IN THE BEGINNING" (54 = 35 - (-19)). Only an ask that
    consumes a start-state marker binds it (rules/start-state.yaml); every other
    ask leaves it unset, exactly as `place_fallback_entity` is bound by one ask.

    It applies ONLY where the asked entity holds the events itself. "Rachel picked
    3 apples FROM HER TREE" folds as rachel/apple/3 — the TREE has no event, so
    there is nothing to undo and inverting returns the same wrong answer. That is
    source-marked transfer, a different mechanism (docs/negative-results.md).

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
    # THE WHOLE IS THE SUM OF ITS PARTS — with two guards.
    #
    # "Gino has 15 brown bears and 24 white bears. How many bears?" holds
    # only PARTS (bear[brown], bear[white]); a BARE ask asks for the whole,
    # and folding the bare key alone finds nothing. Qualified siblings are
    # not a different measure — they are this measure's parts.
    #
    # (1) FAIL CLOSED ON A STATED WHOLE: only when NO bare state exists,
    #     because a stated bare holding IS the whole and adding the parts
    #     would DOUBLE-COUNT ("14 blue + 26 purple, and 200 jellybeans in
    #     the jar" must stay 200, never 280).
    #
    # (2) FAIL CLOSED ON AN UNATTRIBUTABLE EVENT: if a BARE event also
    #     exists, decline outright. "A farmer had 105 green tomatoes and 71
    #     red tomatoes ... picked 137 tomatoes" cannot be folded: the engine
    #     cannot know WHICH part the bare pick depletes, and 'pick' is
    #     (correctly) an `acquire` for the picker, so folding it yields 313
    #     against a gold of 39. Answering that needs SOURCE-MARKED TRANSFER
    #     (the garden is debited), a mechanism docs/negative-results.md
    #     records as deliberately absent. Declining is the honest outcome,
    #     and it is what keeps this fold from manufacturing a confident-wrong
    #     the moment a pronoun binds.
    if not state:
        parts = [
            q for q in store.by_kind(Quantity)
            if q.entity == entity
            and q.is_state
            and str(q.measure).split("[")[0] == measure
            and str(q.measure) != measure
        ]
        if parts:
            if events:
                return None  # guard (2): a bare event over parts-only state
            state = parts
    # A CHANGE TO A PART IS A CHANGE TO THE WHOLE. "Ana bought 2 purple
    # grapes and 2 green grapes. She already had 3 grapes." holds a bare
    # STATE (3) plus two qualified BUY events; she now has 3+2+2. Unlike the
    # state branch there is no double-count to fail closed against — an event
    # is a delta, never a restatement of the whole.
    events.extend(
        q for q in store.by_kind(Quantity)
        if q.entity == entity
        and not q.is_state
        and str(q.measure).split("[")[0] == measure
        and str(q.measure) != measure
    )
    if not state and not events:
        return None
    if invert_events and not events and any(
        q.measure == measure and q.entity != entity and not q.is_state
        for q in store.by_kind(Quantity)
    ):
        # A NARRATED CHANGE THIS FOLD CANNOT SEE.
        #
        # Undoing nothing returns the CURRENT state. That is the right answer
        # when the document narrates no change at all ("Tomas has 30 red grapes
        # ... how many did he have in the beginning?" — nothing happened, so the
        # start IS 30), and a confident-wrong when a change WAS narrated and this
        # entity's fold simply did not receive it: "Rachel picked 3 apples FROM
        # HER TREE. Now the tree has 4" answers 4 (true: 7) because the pick
        # folds as rachel/apple/3 and the TREE holds no event to undo.
        #
        # So the test is not "this entity has no events" — that would decline the
        # legitimately-changeless case above, and it did (it broke
        # test_a_specific_variant_is_not_rolled_up). It is: an event of this
        # MEASURE exists on ANOTHER entity, so a change was narrated that this
        # fold cannot account for. Being unable to tell whether it was sourced
        # from this entity is exactly the reason to refuse — reading that is
        # SOURCE-MARKED TRANSFER ("from her tree" must debit the tree), a
        # mechanism that does not exist (rules/start-state.yaml).
        #
        # Deliberately conservative: it also declines a foreign event that is
        # genuinely irrelevant ("Mary ate 2 apples" while asking about Tom's
        # start). Without source-reading the two are indistinguishable, and a
        # decline is the safe half of that trade — 333 of the 336 marker items
        # across all six corpora already decline, so the coverage cost is ~0.
        #
        # Scoped by the opt-in parameter: unreachable for every non-start-state
        # caller, so the shared fold stays byte-identical.
        return None
    if len({q.time for q in state + events}) > 1:
        return None  # facts from DIFFERENT times — time arithmetic is unbuilt
    if any(_sign(q.verb, reg, strict=True) is None for q in events):
        return None  # an event with UNKNOWN polarity cannot be signed — decline
    # UNDOING an event is negating its polarity; nothing else about the fold
    # changes, so the anchor/ordering/percent-change machinery below is shared.
    def _esign(verb: str) -> int:
        s_ = _sign(verb, reg)
        return -s_ if invert_events else s_
    if not state:
        # AN EVENTS-ONLY FOLD HAS NO ANCHOR, and two shapes prove the
        # implicit zero unfounded (the SVAMP campaign's second live wrong,
        # "Randy has some blocks. He uses 52... how many did he have at
        # the start?" answered -52):
        #
        # (1) The holding was STATED WITHOUT A VALUE — a state-category
        # Predication for this exact (entity, measure) whose dobj was
        # bound by a bare quantifier (`dobj_unquantified`: "has SOME
        # blocks") with no state Quantity. The text itself says the
        # anchor exists and is unknown, so folding events from zero is
        # unfounded in EITHER direction ("has some, buys 4" is as
        # unanswerable as "has some, uses 4"). The `state` category is
        # referenced as STRUCTURE (constitution rule 1's named
        # exemption); no verb is enumerated here. The flag is what keeps
        # this off modal have-artifacts — "Jerry HAD TO SELL boxes"
        # mints the same have/box Predication shape with no quantifier,
        # and Jerry's anchorless '10 he started with minus 5 sold' fold
        # is correct and must survive (an ASDiv BROKE caught exactly
        # this before the flag existed).
        #
        # (2) The signed events SUM NEGATIVE — consumption exceeding
        # stated acquisitions presupposes prior holdings the text never
        # quantified ("Rina uses 4 blocks. How many does Rina have?"
        # answered -4). A negative HOLDING from positive stated counts is
        # never a reading, only an artifact of the zero anchor. Summed in
        # plain Python, not `evaluate` — a declined probe must not enter
        # the arithmetic log's value accounting.
        #
        # An anchorless fold of pure acquisitions ("bought 4 and 3, how
        # many does she have?" = 7) is the standard word-problem reading
        # and stays untouched: no Predication, non-negative sum.
        if any(
            p.polarity and p.subject == entity and p.dobj == measure
            and p.dobj_unquantified
            and reg.word_in_category(p.verb, "state")
            for p in store.by_kind(Predication)
        ):
            return None
        if sum(_esign(q.verb) * q.value for q in events) < 0:
            return None
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
        parts.append(f"{'+' if _esign(q.verb) > 0 else '-'} {q.value}")
    if state:
        expr = " + ".join(str(q.value) for q in state)
        if events:
            expr += " " + " ".join(
                f"{'+' if _esign(q.verb) > 0 else '-'} {q.value}" for q in events
            )
    else:
        expr = " ".join(
            f"{'+' if _esign(q.verb) > 0 else '-'} {q.value}" for q in events
        ).lstrip("+ ")
        if expr.startswith("- "):
            expr = "0 " + " ".join(
                f"{'+' if _esign(q.verb) > 0 else '-'} {q.value}" for q in events
            )
    if reg.word_in_category(measure, "currency"):
        changes = [pc for pc in store.by_kind(PercentChange) if pc.entity == entity]
        if changes and invert_events:
            # A PercentChange is an EVENT — it SCALES the running total by
            # (1 +/- fraction). `invert_events` negates the polarity of event
            # QUANTITIES; it says nothing about a multiplicative event, and
            # undoing one is a DIVISION, not a sign flip. Applying it forward on
            # top of an inverted fold would be a confident-wrong, so a start-state
            # question over an entity carrying a percent change declines.
            #
            # This is the same call as `_qualified_variant_total` and
            # `_superordinate_total` — opt out of a path that folds an EVENT in
            # ignorance of the flag — and deliberately NOT the call made for the
            # container-plus-loose composition, which touches only STATES and is
            # therefore already correct. What a helper FOLDS decides it, not
            # whether it has heard of the flag.
            return None
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
    than guess. A compatible stated `GroupTotal` for the same bare measure
    means the document already names an explicit total some OTHER mechanism
    should reconcile against (mirroring the existing distributive-each guard
    elsewhere in this module): summing the qualified variants here too would
    risk double-counting against it, so this declines instead. A total
    explicitly scoped to another entity is not compatible and cannot block
    this entity's roll-up."""
    if any(
        g.measure == measure and (g.scope is None or g.scope == entity)
        for g in store.by_kind(GroupTotal)
    ):
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

