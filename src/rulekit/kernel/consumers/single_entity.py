"""`single-entity` — The total a single named entity holds — the widest ask family.

Moved out of `answer.py` UNCHANGED. The only edits are `query`/`reg`/`store`/
`question`/`log`/`_match`/`ask` becoming `ctx.` lookups.

⚠ TIME-SCOPED: this consumer lived BELOW the temporal origo, so it has
always received the time-FILTERED store. It registers `time_scoped=True`
and is dispatched after the origo; without the flag it would silently
answer from unfiltered facts.
"""

from __future__ import annotations

from . import ConsumerContext, consumer


@consumer("single-entity", time_scoped=True)
def single_entity(ctx: ConsumerContext):
    from ..answer import Answer
    from ..evaluate import evaluate
    from ..facts import FactStore
    from ..model import GroupTotal, Quantity
    from ..measures import (
        _check_req_unit,
        _resolve_category_measure,
        _measure_substance_guard,
        _resolve_dimension_measure,
        _resolve_measure,
    )
    from ..totals import _entity_total, _purchase_total, _qualified_variant_total, _revenue_total, _superordinate_total, _verb_total

    entity, measure = ctx.query["entity"], ctx.query["measure"]
    from ..model import BatchEvidence
    if ctx.store.by_kind(BatchEvidence):
        from .portion_remainder import individual_stock_view
        projection = individual_stock_view(ctx)
        if projection is not None:
            from dataclasses import replace
            view, rows = projection
            result = single_entity(replace(ctx, store=view))
            if result.committed:
                ctx.log.consumed_batch_keys.update(r.key() for r in rows)
            return result
        if (any(r.kind == "transfer-opening" for r in ctx.store.by_kind(BatchEvidence))
                and ctx.reg.word_in_category(ctx.query.get("verb", ""), "purchase")):
            from .recipient_stock_reconstruction import consume as opening_transfers
            return opening_transfers(ctx)
        if any(r.kind == "item-relation" for r in ctx.store.by_kind(BatchEvidence)):
            from .relative_item_total import consume as relative_inventory
            return relative_inventory(ctx)
        from dataclasses import replace
        from .batch_outcomes import ACQUIRED_BATCH_KINDS, consume
        if (all(r.kind in ACQUIRED_BATCH_KINDS
                for r in ctx.store.by_kind(BatchEvidence))
                and any(ctx.reg.word_in_category(ctx.query.get("verb", ""), category)
                        for category in ("possession_state", "batch_acquisition_verb"))):
            mode = "retained" if ctx.reg.word_in_category(ctx.query.get("verb", ""), "possession_state") else "acquired"
            return consume(replace(ctx, query={**ctx.query, "scope": "acquired", "item": measure, "mode": mode}))
        return consume(replace(ctx, query={**ctx.query, "item": measure, "mode": "selected"}))
    from ..purchase_totals import has_relative_purchase_prices, relative_purchase_total
    if (has_relative_purchase_prices(ctx.store)
            and ctx.reg.word_in_category(ctx.query.get("verb", ""), "spend_verb")
            and (measure == "currency" or ctx.reg.word_in_category(measure, "currency"))):
        return relative_purchase_total(ctx)
    if (ctx.reg.word_in_category(ctx.query.get("verb", ""), "spend_verb")
            and (measure == "currency" or ctx.reg.word_in_category(measure, "currency"))
            and any(u.sense() == "verb" and u.uid not in ctx.match.consumed
                    for u in ctx.question.units)):
        # A recognized main spending verb cannot stand in for an unread
        # activity complement or condition. Its target may be only a subset
        # of the purchases; summing the whole ledger would erase that scope.
        return Answer("decline", None, "the spending ask contains an unread activity or condition")
    from ..model import AccumulationWindow
    if ctx.store.by_kind(AccumulationWindow):
        from .earnings_account import earnings_account
        return earnings_account(ctx)
    # Structured work schedules can answer an ordinary named-currency ask.
    # Keep the existing event-total route when no such evidence is present.
    from dataclasses import replace
    from ..repeated_rates import has_rate_structure
    if (has_rate_structure(ctx.store)
            and ctx.reg.word_in_category(ctx.query.get("verb", ""), "wage_verb")
            and (measure == "currency" or ctx.reg.word_in_category(measure, "currency"))):
        from .rate_span import rate_span
        return rate_span(replace(ctx, query={**ctx.query, "measure": "currency"}))
    if ctx.query.get("other_entity"):
        return Answer(
            "decline",
            None,
            "a single-dimension ask must name exactly one entity",
        )
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
    owner = ctx.query.get("entity_owner")
    # increment 34's mirror of `owner`: an attribute-qualified subject
    # ("the coconut tree") resolves bare ("tree") the same way UNLESS a
    # same-key VALUE conflict forced facts.py to re-key it to
    # "tree[coconut]" — same two-lookup, owner-scoped-fallback shape,
    # gated on `qualifier` instead. An ask binds at most one of
    # `entity_owner`/`entity_qualifier` (each comes from a distinct ask
    # id), so the two never compete for the same query.
    qualifier = ctx.query.get("entity_qualifier")
    location_source_store = ctx.store
    if owner and ctx.query.get("require_entity_owner_evidence") == "true":
        # Scope every path, including exact-key and aggregate fallbacks, to
        # this owner. A generic per-container class rate proves nothing about
        # a possessed instance. Owner and attribute restrictions intersect;
        # they are not alternative lookups when both occur in the question.
        ctx = replace(ctx, store=FactStore(facts=[
            fact for fact in ctx.store.facts
            if (
                isinstance(fact, Quantity)
                and fact.owner == owner
                and (not qualifier or fact.qualifier == qualifier)
                and (
                    not ctx.query.get("measure_qualifier")
                    or fact.measure.split("[", 1)[0] != measure
                    or fact.measure_qualifier == ctx.query["measure_qualifier"]
                )
            ) or not isinstance(fact, (Quantity, GroupTotal))
        ]))
    # mining candidate qualified-measure-keys: the MEASURE-side mirror
    # of `qualifier` above, one field over — "how many GREEN apples
    # does Sam have?" resolves the bare measure ("apple") the same way
    # UNLESS a same-key VALUE conflict forced facts.py to re-key it to
    # "apple[green]" (increment 70). Read off the ask's OWN `item`
    # token's qualifier feature (bound only on ask ids that opt in via
    # `measure_qualifier: "{item.qualifier}"` — a no-op empty string
    # everywhere else), never the entity-level `entity_qualifier`.
    measure_qualifier = ctx.query.get("measure_qualifier")
    ask_verb = ctx.query.get("verb", "have")
    measure_category = ctx.query.get("measure_category")
    if measure_category:
        singular = _resolve_category_measure(
            measure_category,
            ctx.store,
            ctx.reg,
            entities=[entity],
            verb=ask_verb,
            journal=ctx.log.journal,
        )
    elif ctx.query.get("dimension_measure"):
        singular = _resolve_dimension_measure(
            measure,
            ctx.store,
            ctx.reg,
            journal=ctx.log.journal,
            entities=[entity],
        )
    else:
        singular = _resolve_measure(
            measure, ctx.store, ctx.reg, journal=ctx.log.journal
        )
    if singular is None:
        return Answer("decline", None,
                      f"measure {measure!r} is ambiguous across the facts")
    if measure_qualifier and any(
        q.entity == entity and q.measure_qualifier == singular
        and ctx.reg.partitive_applies_to(q.measure.split("[", 1)[0], singular)
        for q in ctx.store.by_kind(Quantity)
    ):
        # A count of grouped/substance units is not a sized attribute subset.
        # The bare total cannot answer a qualified subset ask while the only
        # breakdown is stated in another unit (pairs versus items, for
        # example). That needs an explicit conversion and partition proof.
        return Answer("decline", None, "a qualified subset needs item-level evidence, not an unconverted partitive count")
    req_unit = ctx.query.get("req_unit")
    if not _check_req_unit(req_unit, singular, ctx.store, ctx.reg, journal=ctx.log.journal):
        return Answer(
            "decline", None,
            f"asked unit {req_unit!r} does not match resolved measure {singular!r}",
        )
    measure_substance = ctx.query.get("measure_substance")
    if measure_substance:
        guard = _measure_substance_guard(
            ctx.store, singular, measure_substance, entities=[entity]
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
    matching_totals = [
        gt for gt in ctx.store.by_kind(GroupTotal)
        if gt.measure == singular and (gt.scope is None or gt.scope == entity)
    ]
    if matching_totals and not measure_qualifier:
        # the held Quantity must genuinely STATE a per-container rate
        # (saturate's `_distributive_rate_source`, the same gate the two
        # container synths use): 'The second chapter is 36 pages long'
        # holds the identical (entity, measure) shape as 'each shelf had
        # 15 books' but states ONE instance's count, and reading it as a
        # rate committed a stated whole-total to an ask about one member
        # ('...how many pages are in the FIRST chapter?' answered 67).
        from ..saturate import _distributive_rate_source

        holds_rate = any(
            q.entity == entity and q.measure == singular
            and _distributive_rate_source(q)
            for q in ctx.store.by_kind(Quantity)
        )
        entity_is_counted = any(
            q.measure == entity for q in ctx.store.by_kind(Quantity)
        )
        if holds_rate and entity_is_counted:
            if len(matching_totals) == 1:
                total = evaluate(
                    f"{matching_totals[0].value}", {}, ctx.log, source="group-total"
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
    owner_store = ctx.store
    if owner:
        require_owner_evidence = (
            ctx.query.get("require_entity_owner_evidence") == "true"
        )
        owner_store = FactStore(facts=[
            q
            for q in ctx.store.by_kind(Quantity)
            if q.owner == owner or (q.owner is None and not require_owner_evidence)
        ])
    qualifier_store = ctx.store
    if qualifier:
        qualifier_store = FactStore(facts=[
            q for q in ctx.store.by_kind(Quantity)
            if q.qualifier is None or q.qualifier == qualifier
        ])
    is_state_ask = ask_verb in ("have", "be") or ctx.reg.word_in_category(ask_verb, "state")
    def qualified_total(*, invert_events=False):
        # An explicit ask modifier is a constraint, never its own evidence.
        # Share the comparison projection, including bare-extra-event safety.
        from ..reference_identity import ReferenceIdentity
        from ..totals import _item_evidence
        raw = ctx.query.get("evidence_entity_reference")
        reference = ReferenceIdentity.from_dict(raw) if raw else ReferenceIdentity(entity)
        projected = _item_evidence(ctx.store, reference, singular, ask_verb,
                                   measure_qualifier, (reference,), ctx.reg, ctx.log)
        if projected is None:
            return Answer("decline", None, "qualified item needs compatible subset evidence")
        evidence, _, selected_measure = projected
        total = (_entity_total(evidence, ctx.reg, reference.head, selected_measure, ctx.log,
                               invert_events=invert_events) if is_state_ask else
                 _verb_total(evidence, reference.head, selected_measure, ask_verb, ctx.log))
        return Answer("number", total, "total from identified item subset") if total is not None else Answer(
            "decline", None, "qualified item has no complete compatible total")

    if not is_state_ask:
        if measure_qualifier:
            return qualified_total()
        # An EVENT ask ("how many apples did Mary EAT?") sums only that
        # verb's own event quantities — a holdings fold answering an
        # eat-question with a buy-total is a category error (the
        # question's verb is part of the query, difg playbook lesson).
        total = (
            _verb_total(ctx.store, f"{entity}[{owner}]", singular, ask_verb, ctx.log)
            if owner else None
        )
        if total is None and qualifier:
            total = _verb_total(ctx.store, f"{entity}[{qualifier}]", singular, ask_verb, ctx.log)
        if total is None:
            scoped = (
                owner_store if owner
                else qualifier_store if qualifier
                else ctx.store
            )
            total = _verb_total(scoped, entity, singular, ask_verb, ctx.log)
        if total is not None:
            return Answer("number", total, f"Σ {ask_verb!r} events of {entity!r}/{singular!r}")
        # "how much did X pay/spend?" over priced purchases ("3 toys at
        # $10 each") is a DERIVED total, not a literal 'pay'/'spend'
        # event — gated to money asks over spend-family verbs only.
        is_currency_ask = singular == "currency" or ctx.reg.word_in_category(singular, "currency")
        if is_currency_ask and ctx.reg.word_in_category(ask_verb, "spend_verb"):
            total = _purchase_total(ctx.store, ctx.reg, entity, ctx.log)
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
        if is_currency_ask and ctx.reg.word_in_category(ask_verb, "wage_verb"):
            total = _revenue_total(ctx.store, ctx.reg, entity, ctx.log)
            if total is not None:
                return Answer(
                    "number", total, f"Σ price × qty over {entity!r}'s sales"
                )
        # superordinate-totality fallback (mining candidate subtype-
        # total-asks), verb-scoped sibling of the state-ask fallback
        # below: "James buys twice as many toy soldiers as toy cars...
        # how many total toys does he buy?" — see `_superordinate_
        # total`'s own docstring for the guard.
        total = _superordinate_total(ctx.store, ctx.reg, entity, singular, ctx.log, verb=ask_verb)
        if total is not None:
            return Answer(
                "number", total, f"Σ {ask_verb!r} subtype events of {entity!r}/{singular!r}"
            )
        return Answer(
            "decline", None,
            f"no {ask_verb!r} events known for {entity!r}/{singular!r}",
        )
    # START STATE (opt-in, bound only by the start-state asks —
    # rules/start-state.yaml): the question asks what the entity held BEFORE
    # the narrated events, so the fold UNDOES them instead of applying them.
    # Unset for every other ask, which therefore folds byte-identically (the
    # `place_fallback_entity` precedent: a shared consumer widened for one
    # caller via a defaulted-off parameter, never globally).
    invert = ctx.query.get("start_state") == "true"
    if invert and measure_qualifier:
        # A qualified current anchor does not prove that a differently
        # qualified event is outside its history. "new toy cars" currently
        # carries only the nearest scalar qualifier while an ask about "toy
        # cars" carries another; silently dropping the purchase would return
        # the current 40 for "how many ... originally?" instead of undoing it.
        # Conversely, blindly folding every differently qualified event would
        # mix genuinely disjoint variants such as red and green. Until modifier
        # nesting is represented losslessly, either choice is a guess.
        #
        # State facts are harmless sibling anchors and remain eligible for the
        # existing exact-qualified lookup. Only a same-holder, same-base-measure
        # EVENT with a different explicit qualifier makes the start history
        # ambiguous. This applies to every declarative start-state ask, not to a
        # rule id or an English-word exception.
        ambiguous_events = [
            q
            for q in ctx.store.by_kind(Quantity)
            if q.entity == entity
            and q.measure == singular
            and q.measure_qualifier not in (None, measure_qualifier)
            and not ctx.reg.word_in_category(q.verb, "state")
        ]
        if ambiguous_events:
            return Answer(
                "decline",
                None,
                "qualified start state has differently qualified events; "
                "modifier scope is ambiguous",
            )
    if measure_qualifier:
        return qualified_total(invert_events=invert)
    total = (
        _entity_total(ctx.store, ctx.reg, f"{entity}[{owner}]", singular, ctx.log, invert_events=invert)
        if owner else None
    )
    if total is None and qualifier:
        total = _entity_total(ctx.store, ctx.reg, f"{entity}[{qualifier}]", singular, ctx.log, invert_events=invert)
    if total is None:
        scoped = (
            owner_store if owner
            else qualifier_store if qualifier
            else ctx.store
        )
        total = _entity_total(scoped, ctx.reg, entity, singular, ctx.log, invert_events=invert)
    if total is None and ctx.query.get("sum_measure_variants") and not measure_qualifier:
        # gap (c), mining candidate qualified-measure-keys: "Sam has 30
        # red balls. Sam has 36 green balls. How many balls does Sam
        # have?" — no bare 'ball' fact exists (facts.py's admit-time
        # qualifier split already re-keyed both into
        # 'ball[red]'/'ball[green]'), so every lookup above comes back
        # empty. Opt-in per ask id (never a blanket widening of this
        # consumer) and only for a BARE ask (`not measure_qualifier`):
        # a question naming one SPECIFIC variant must never silently
        # roll up every colour instead.
        variant_store = (
            owner_store
            if owner
            else qualifier_store
            if qualifier
            else ctx.store
        )
        total = _qualified_variant_total(
            variant_store, ctx.reg, entity, singular, ctx.log
        )
    fallback_entity = ctx.query.get("place_fallback_entity")
    # `not invert` mirrors the superordinate fallback below, and it is a
    # MECHANISM rather than a note because the failure is silent: this branch
    # calls `_entity_total` WITHOUT `invert_events`, so under a start-state
    # ask it would answer the fallback entity's CURRENT total while wearing
    # that ask's name — the same defect `sum_measure_variants` is opted out
    # of in rules/start-state.yaml. It is unreachable today (only
    # ask/how-many-in-place binds `place_fallback_entity`, and it sets no
    # `start_state`), and that is exactly why it needed pinning: the next
    # in-place start-state ask to bind the field would ship a confident-wrong
    # with nothing to stop it. Prose does not enforce.
    if total is None and fallback_entity and not invert:
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
        holders = {q.entity for q in ctx.store.by_kind(Quantity) if q.measure == singular}
        if holders == {fallback_entity}:
            total = _entity_total(ctx.store, ctx.reg, fallback_entity, singular, ctx.log)
    if total is None and not invert:
        # superordinate-totality fallback (mining candidate subtype-
        # total-asks): the asked measure has ZERO facts of its own but
        # every measure this entity holds is a pack-declared subtype of
        # it — see `_superordinate_total`'s own docstring for the guard.
        #
        # NOT taken for a START-STATE ask: this helper sums subtype
        # holdings and knows nothing of `invert_events`, so it would
        # return a confidently UN-inverted total under a question asking
        # for the start. Declining is the safe half of that trade, and is
        # the same call made for `sum_measure_variants` in
        # rules/start-state.yaml. Threading the inversion through here
        # first is what it would take to widen this.
        total = _superordinate_total(ctx.store, ctx.reg, entity, singular, ctx.log)
    # A subject-owned location ask has two established fact
    # representations. Newer location-aware premises key quantities to the
    # owned place and reach the primary fold above. Older locative holding
    # premises key them to the grammatical subject while preserving the PP
    # only as sentence structure. One ask opts into this fallback explicitly:
    # it is reached only when the exact owner-qualified place has no usable
    # total, so real place evidence always wins and holdings elsewhere are
    # never added to it.
    holder_fallback = ctx.query.get("owned_place_holder_fallback")
    if (total is None and holder_fallback and not invert
            and not qualifier and not measure_qualifier):
        total = _entity_total(
            location_source_store, ctx.reg, holder_fallback, singular, ctx.log
        )
        if (
            total is None
            and ctx.query.get("sum_measure_variants")
            and not measure_qualifier
        ):
            total = _qualified_variant_total(
                location_source_store, ctx.reg, holder_fallback, singular, ctx.log
            )
        if total is None:
            total = _superordinate_total(
                location_source_store, ctx.reg, holder_fallback, singular, ctx.log
            )
    if total is None:
        return Answer(
            "decline", None,
            f"no quantity known for {entity!r} of {singular!r} (ask {ctx.ask.id})",
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
    # DELIBERATELY NOT gated on `invert` — the composition is ALREADY correct
    # for a start-state ask, and gating it here was a confident-wrong I had to
    # revert: a GroupTotal is a STATE (an anchor), and the inversion only ever
    # negates EVENTS, so "Beth has 4 packs of 10 crayons. Beth ate 6 and had 6
    # left. How many did she have in the beginning?" composes 40 + 12 = 52,
    # which is right. Dropping the packs answered 12. Not every path needs the
    # opt-out — only those that fold events without knowing about it.
    group_totals = [
        gt for gt in ctx.store.by_kind(GroupTotal)
        if gt.measure == singular and (gt.scope is None or gt.scope == entity)
    ]
    if len(group_totals) == 1 and abs(group_totals[0].value - total) > 1e-9:
        g = group_totals[0].value
        for c_fact in ctx.store.by_kind(Quantity):
            if c_fact.entity != entity or c_fact.measure == singular:
                continue
            rates = [
                q for q in ctx.store.by_kind(Quantity)
                if q.entity == c_fact.measure and q.measure == singular
            ]
            if len(rates) == 1 and abs(c_fact.value * rates[0].value - g) < 1e-9:
                composed = evaluate(
                    f"{total} + {g}", {}, ctx.log, source="container-plus-loose"
                )
                return Answer(
                    "number", composed,
                    f"{entity!r}'s loose {singular!r} ({total:g}) plus its "
                    f"{c_fact.measure!r} contents (group total {g:g})",
                )
    return Answer("number", total, f"fold over {entity!r}/{singular!r}")
