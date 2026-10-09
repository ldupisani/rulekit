"""`difference` — The difference between two entities' totals.

Moved out of `answer.py` UNCHANGED. The only edits are `query`/`reg`/`store`/
`question`/`log`/`_match`/`ask` becoming `ctx.` lookups.

⚠ TIME-SCOPED: this consumer lived BELOW the temporal origo, so it has
always received the time-FILTERED store. It registers `time_scoped=True`
and is dispatched after the origo; without the flag it would silently
answer from unfiltered facts.
"""

from __future__ import annotations

from . import ConsumerContext, consumer


@consumer("difference", time_scoped=True)
def difference(ctx: ConsumerContext):
    from ..answer import Answer
    from ..evaluate import evaluate
    from ..model import Quantity
    from ..measures import _measure_substance_guard, _resolve_measure
    from ..totals import _entity_total, _entity_total_convertible, _verb_total

    from .joint_shares import has_joint_shares, difference as joint_difference
    if has_joint_shares(ctx.store):
        return joint_difference(ctx)

    measure = ctx.query["measure"]
    singular = _resolve_measure(measure, ctx.store, ctx.reg, journal=ctx.log.journal)
    if singular is None:
        return Answer("decline", None,
                      f"measure {measure!r} is ambiguous across the facts")
    a, b = ctx.query.get("a"), ctx.query.get("b")
    if a is None or b is None:
        # ask/what-is-the-difference-pronoun names no pair ("...ITEM
        # they have?") — mirrors the 'combined' consumer's holder
        # enumeration, but a difference is inherently BINARY: decline
        # unless EXACTLY two entities hold the measure (the established
        # exactly-one/exactly-two-or-decline discipline).
        entities = sorted(
            {q.entity for q in ctx.store.by_kind(Quantity) if q.measure == singular}
        )
        if len(entities) != 2:
            return Answer(
                "decline", None,
                f"a pronoun difference ask needs exactly two holders of "
                f"{singular!r}; found {entities}",
            )
        a, b = entities
    if a == b:
        # A DIFFERENCE IS BETWEEN TWO THINGS. |X - X| is 0 for every X, so
        # this branch can never carry information: a self-comparison is
        # always the ask having MISREAD the sentence, never a question
        # whose answer is 0.
        #
        # The witness is an EVENT comparative: "Josh had 3 marbles. He found
        # 6 while he LOST 5. How many more marbles did he FIND than those he
        # LOST?" compares two events on ONE person, but this consumer
        # compares two ENTITIES under one `ask_verb` — so both slots resolved
        # to 'josh' and it committed |josh - josh| = 0 against a gold of 1.
        # Reading that properly needs a verb-vs-verb consumer (a capability
        # increment, and a separate one); refusing to answer it needs only
        # the observation that the two sides are the same entity.
        #
        # This is the pattern rules' `distinct: [who, std]` predicate, which
        # asks never had. It compares the RESOLVED entities, which is the
        # only reason it is safe to compare them bare: every ask reaching
        # this consumer binds `a`/`b` through `type: name` slots, so a
        # LABELED entity ("jar A" vs "jar B" — one unit, lemma 'jar', label
        # in a separate feature) can never bind them and cannot be collapsed
        # here. That distinction is load-bearing: a bare-lemma distinctness
        # check on the PATTERN side once silently declined every labeled
        # relation. The collapse this catches comes from PRONOUN resolution
        # instead, which legitimately maps two mentions onto one entity.
        return Answer(
            "decline", None,
            f"a difference ask resolved both sides to {a!r} — a self-"
            f"comparison is a misreading, not a question with answer 0",
        )
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
    measure_substance = ctx.query.get("measure_substance")
    if measure_substance:
        guard = _measure_substance_guard(ctx.store, singular, measure_substance, entities=[a, b])
        if guard is not None:
            return guard
    ask_verb = ctx.query.get("verb", "have")
    # mining candidate dimension-difference-asks: opt-in fold across
    # convertible sibling units (see `_entity_total_convertible`'s own
    # docstring) — set ONLY by the new unit-qualified dimension/age-
    # comparative asks. Every pre-existing `difference` ask (how-many-
    # more, what-is-the-difference-named/-pronoun, the partitive
    # sibling) never binds `fold_units`, so this branch is dead code
    # for all of them — zero behavior change (shared-function
    # blast-radius invariant).
    fold_units = ctx.query.get("fold_units") == "true"
    if ask_verb in ("have", "be") or ctx.reg.word_in_category(ask_verb, "state"):
        if fold_units:
            ta = _entity_total_convertible(ctx.store, ctx.reg, a, singular, ctx.log)
            tb = _entity_total_convertible(ctx.store, ctx.reg, b, singular, ctx.log)
        else:
            ta = _entity_total(ctx.store, ctx.reg, a, singular, ctx.log)
            tb = _entity_total(ctx.store, ctx.reg, b, singular, ctx.log)
    else:
        # "how many more did Quincy SELL than Jake" — activity totals,
        # never the signed holdings fold (selling is not owning)
        ta = _verb_total(ctx.store, a, singular, ask_verb, ctx.log)
        tb = _verb_total(ctx.store, b, singular, ask_verb, ctx.log)
    if ta is None or tb is None:
        return Answer("decline", None, f"missing a total for {a!r} or {b!r}")
    return Answer(
        "number",
        evaluate(f"abs({ta} - {tb})", {}, ctx.log, source="difference"),
        f"|{a} - {b}| of {singular!r}",
    )
