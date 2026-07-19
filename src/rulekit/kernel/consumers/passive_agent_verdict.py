"""`passive-agent-verdict` — A passive-agent conclusion: is X <verb>ed by a <cls>?

Moved out of `answer.py` UNCHANGED. The only edits are `query`/`reg`/`store`/
`question`/`log`/`_match`/`ask` becoming `ctx.` lookups.

⚠ TIME-SCOPED: this consumer lived BELOW the temporal origo, so it has
always received the time-FILTERED store. It registers `time_scoped=True`
and is dispatched after the origo; without the flag it would silently
answer from unfiltered facts.
"""

from __future__ import annotations

from . import ConsumerContext, consumer


@consumer("passive-agent-verdict", time_scoped=True)
def passive_agent_verdict(ctx: ConsumerContext):
    from ..answer import Answer

    # S2 (composition-design.md): "Is it true that X is <participle> by
    # a CLS?" — the MEMBERSHIP BRIDGE, ∃-intro over the agent: a
    # VerbalRelation whose obj is the question's subject and whose agent
    # holds the class atom (saturated + decomposed variants included,
    # so 'a British architect who…' still counts). Sound for ANY verb —
    # the premise itself supplies the witness; no monotonicity
    # assumption. Open world: no relation found is 'undetermined',
    # never 'no' (¬∃ is unprovable from absence). An indefinite-object
    # relation ("designed a tower") never matches the question's
    # definite subject (indef_obj). Full-read as the consumers above.
    from ..model import Atom, VerbalRelation
    from ..patterns import SKIPPABLE_SENSES

    unread = [
        u.surface
        for u in ctx.question.units
        if u.sense() not in SKIPPABLE_SENSES and u.uid not in ctx.match.consumed
    ]
    if unread:
        return Answer(
            "decline", None,
            f"question states {unread!r} but the passive query never read it",
        )
    entity, verb, cls_p = ctx.query["entity"], ctx.query["verb"], ctx.query["cls"]
    for f in ctx.store.by_kind(VerbalRelation):
        if (
            f.verb == verb and f.obj == entity
            and f.polarity and not f.indef_obj
        ):
            for a in ctx.store.by_kind(Atom):
                if a.entity == f.entity and a.pred == cls_p and a.polarity:
                    return Answer(
                        "verdict", "yes",
                        f"agent {f.entity!r} ({verb!r} -> {entity!r}) "
                        f"is {cls_p!r} via {a.provenance.source}",
                    )
    return Answer(
        "verdict", "undetermined", "no agent relation decides it"
    )
