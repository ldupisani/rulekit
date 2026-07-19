"""`logic-disjunction-verdict` — A disjunctive conclusion under case analysis.

Moved out of `answer.py` UNCHANGED. The only edits are `query`/`reg`/`store`/
`question`/`log`/`_match`/`ask` becoming `ctx.` lookups.

⚠ TIME-SCOPED: this consumer lived BELOW the temporal origo, so it has
always received the time-FILTERED store. It registers `time_scoped=True`
and is dispatched after the origo; without the flag it would silently
answer from unfiltered facts.
"""

from __future__ import annotations

from . import ConsumerContext, consumer


@consumer("logic-disjunction-verdict", time_scoped=True)
def logic_disjunction_verdict(ctx: ConsumerContext):
    from ..answer import Answer

    # A disjunctive conclusion, semantics MEASURED from folio DEV golds
    # (Stage 3): bare 'or' is INCLUSIVE, 'either...or' is EXCLUSIVE (the
    # James minimal pair — both disjuncts true golds the bare form True
    # and the either form False). Open-world throughout: an unknown
    # disjunct truth yields 'undetermined', never a guess. Same full-read
    # contract as logic-verdict above.
    from ..model import Atom, Disjunction
    from ..patterns import SKIPPABLE_SENSES

    unread = [
        u.surface
        for u in ctx.question.units
        if u.sense() not in SKIPPABLE_SENSES and u.uid not in ctx.match.consumed
    ]
    if unread:
        return Answer(
            "decline", None,
            f"question states {unread!r} but the disjunction query never read it",
        )
    entity = ctx.query["entity"]
    left, right = ctx.query["left"], ctx.query["right"]
    exclusive = ctx.query.get("exclusive", "false") == "true"
    # a premise ECHO decides it outright when the surface form matches
    for f in ctx.store.by_kind(Disjunction):
        if (
            f.entity == entity and f.left == left and f.right == right
            and f.exclusive == exclusive
        ):
            return Answer(
                "verdict", "yes",
                f"disjunction {entity!r} {left!r}/{right!r} stated "
                f"({'either' if exclusive else 'or'}) via {f.provenance.source}",
            )
    lt = rt = None
    for f in ctx.store.by_kind(Atom):
        if f.entity == entity and f.pred == left:
            lt = f.polarity
        elif f.entity == entity and f.pred == right:
            rt = f.polarity
    if exclusive:
        if lt is not None and rt is not None:
            return Answer(
                "verdict", "yes" if lt != rt else "no",
                f"xor over atoms {left!r}={lt} {right!r}={rt}",
            )
        return Answer(
            "verdict", "undetermined",
            "exclusive-or needs BOTH disjunct truths; open world has "
            f"{left!r}={lt} {right!r}={rt}",
        )
    if lt is True or rt is True:
        return Answer(
            "verdict", "yes",
            f"inclusive-or over atoms {left!r}={lt} {right!r}={rt}",
        )
    if lt is False and rt is False:
        return Answer(
            "verdict", "no",
            f"inclusive-or over atoms {left!r}=False {right!r}=False",
        )
    return Answer(
        "verdict", "undetermined",
        f"inclusive-or undecided; open world has {left!r}={lt} {right!r}={rt}",
    )
