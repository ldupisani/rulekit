"""`verbal-obj-class-verdict` — A verbal conclusion whose object is a class.

Moved out of `answer.py` UNCHANGED. The only edits are `query`/`reg`/`store`/
`question`/`log`/`_match`/`ask` becoming `ctx.` lookups.

⚠ TIME-SCOPED: this consumer lived BELOW the temporal origo, so it has
always received the time-FILTERED store. It registers `time_scoped=True`
and is dispatched after the origo; without the flag it would silently
answer from unfiltered facts.
"""

from __future__ import annotations

from . import ConsumerContext, consumer


@consumer("verbal-obj-class-verdict", time_scoped=True)
def verbal_obj_class_verdict(ctx: ConsumerContext):
    from ..answer import Answer

    # S1 (composition-design.md): "Is it true that X does not <v> <prep>
    # a CLS?" — the question claims ∃ (polarity true) or ¬∃ (false) over
    # the PP object's class. A stored VerbalRelation whose object is in
    # the class (saturated + decomposed atoms — 'football club along
    # with Braga' drops to 'football club') is the ∃ witness: 'yes' to
    # the positive claim, 'no' to the negated one. Open world: absence
    # of a relation proves NOTHING in either direction — ¬∃ is never
    # 'yes' from silence. An indefinite-object relation never witnesses
    # (its object is not a referent to look up a class for). Full-read
    # as the verdict consumers above.
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
            f"question states {unread!r} but the relation query never read it",
        )
    entity, verb, prep = ctx.query["entity"], ctx.query["verb"], ctx.query["prep"]
    cls_p = ctx.query["cls"]
    pol = ctx.query.get("polarity", "true") == "true"
    for f in ctx.store.by_kind(VerbalRelation):
        if (
            f.entity == entity and f.verb == verb and f.prep == prep
            and f.polarity and not f.indef_obj
        ):
            for a in ctx.store.by_kind(Atom):
                if a.entity == f.obj and a.pred == cls_p and a.polarity:
                    return Answer(
                        "verdict", "yes" if pol else "no",
                        f"witness {f.obj!r} ∈ {cls_p!r} "
                        f"({entity!r} {verb!r} {prep!r} it) "
                        f"via {a.provenance.source}",
                    )
    return Answer(
        "verdict", "undetermined", "no object-class relation decides it"
    )
