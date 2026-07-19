"""`label-difference` — The difference between two labelled subsets.

Moved out of `answer.py` UNCHANGED. The only edits are `query`/`reg`/`store`/
`question`/`log`/`_match`/`ask` becoming `ctx.` lookups.

⚠ TIME-SCOPED: this consumer lived BELOW the temporal origo, so it has
always received the time-FILTERED store. It registers `time_scoped=True`
and is dispatched after the origo; without the flag it would silently
answer from unfiltered facts.
"""

from __future__ import annotations

from . import ConsumerContext, consumer


@consumer("label-difference", time_scoped=True)
def label_difference(ctx: ConsumerContext):
    from ..answer import Answer
    from ..evaluate import evaluate
    from ..model import Quantity
    from ..answer import _entity_total

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
    measure_a = ctx.reg.plural_to_singular.get(ctx.query["a"], ctx.query["a"])
    measure_b = ctx.reg.plural_to_singular.get(ctx.query["b"], ctx.query["b"])
    entities_a = sorted(
        {q.entity for q in ctx.store.by_kind(Quantity) if q.measure == measure_a}
    )
    entities_b = sorted(
        {q.entity for q in ctx.store.by_kind(Quantity) if q.measure == measure_b}
    )
    if len(entities_a) != 1 or len(entities_b) != 1 or entities_a != entities_b:
        return Answer(
            "decline", None,
            f"{measure_a!r}/{measure_b!r} need exactly one SHARED holder "
            f"— found {entities_a} / {entities_b}",
        )
    (holder,) = entities_a
    ta = _entity_total(ctx.store, ctx.reg, holder, measure_a, ctx.log)
    tb = _entity_total(ctx.store, ctx.reg, holder, measure_b, ctx.log)
    if ta is None or tb is None:
        return Answer(
            "decline", None, f"missing a total for {measure_a!r} or {measure_b!r}"
        )
    return Answer(
        "number",
        evaluate(f"abs({ta} - {tb})", {}, ctx.log, source="label-difference"),
        f"|{measure_a} - {measure_b}| on {holder!r}",
    )
