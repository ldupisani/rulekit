"""`deficit` — How many more are needed to reach a goal.

Moved out of `answer.py` UNCHANGED. The only edits are `query`/`reg`/`store`/
`question`/`log`/`_match`/`ask` becoming `ctx.` lookups.

⚠ TIME-SCOPED: this consumer lived BELOW the temporal origo, so it has
always received the time-FILTERED store. It registers `time_scoped=True`
and is dispatched after the origo; without the flag it would silently
answer from unfiltered facts.
"""

from __future__ import annotations

from . import ConsumerContext, consumer


@consumer("deficit", time_scoped=True)
def deficit(ctx: ConsumerContext):
    from ..answer import Answer
    from ..evaluate import evaluate
    from ..model import Goal, Quantity
    from ..measures import _resolve_measure

    # "how many more X does WHO need" — goal minus the entity's single
    # CURRENT holding (a stated STATE quantity, never the general event
    # fold: the desire verb's own spurious event Quantity, and the
    # target-verb's, both sit in the store unsignable/signed by
    # whatever the generic SVO scan gave them — reading the entity's
    # raw stated holding directly sidesteps that noise rather than
    # risking it). Commits only when EXACTLY one Goal fact and exactly
    # one current holding resolve; anything else is a genuine ambiguity.
    entity, measure = ctx.query["entity"], ctx.query["measure"]
    singular = _resolve_measure(measure, ctx.store, ctx.reg, journal=ctx.log.journal)
    if singular is None:
        return Answer("decline", None,
                      f"measure {measure!r} is ambiguous across the facts")
    goals = [
        g for g in ctx.store.by_kind(Goal)
        if g.entity == entity and g.measure == singular
    ]
    if len(goals) != 1:
        return Answer(
            "decline", None,
            f"{len(goals)} goal facts known for {entity!r}/{singular!r} — "
            "a deficit ask needs exactly one",
        )
    holdings = [
        q for q in ctx.store.by_kind(Quantity)
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
        f"{goal.value} - {holding.value}", {}, ctx.log, source="deficit"
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
