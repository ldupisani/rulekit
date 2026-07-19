"""`existential-verdict` — An existential conclusion, answered by a witness search.

Moved out of `answer.py` UNCHANGED. The only edits are `query`/`reg`/`store`/
`question`/`log`/`_match`/`ask` becoming `ctx.` lookups.

⚠ TIME-SCOPED: this consumer lived BELOW the temporal origo, so it has
always received the time-FILTERED store. It registers `time_scoped=True`
and is dispatched after the origo; without the flag it would silently
answer from unfiltered facts.
"""

from __future__ import annotations

from . import ConsumerContext, consumer


@consumer("existential-verdict", time_scoped=True)
def existential_verdict(ctx: ConsumerContext):
    from ..answer import Answer

    # "Is it true that some CLS are [not] PRED?" — ∃-introduction at
    # query time (Stage 4): 'yes' from a stated Existential echo or from
    # a WITNESS entity holding both atoms; 'no' ONLY from a matching
    # NEGATIVE universal (∀¬ soundly refutes ∃); otherwise undetermined —
    # open world, and no existential import from positive universals
    # ("all dogs are animals" proves no dog exists). Full-read as the
    # verdict consumers above.
    from ..model import Atom, Existential, Quantified
    from ..patterns import SKIPPABLE_SENSES

    unread = [
        u.surface
        for u in ctx.question.units
        if u.sense() not in SKIPPABLE_SENSES and u.uid not in ctx.match.consumed
    ]
    if unread:
        return Answer(
            "decline", None,
            f"question states {unread!r} but the existential query never read it",
        )
    cls_p, pred = ctx.query["cls"], ctx.query["pred"]
    pol = ctx.query.get("polarity", "true") == "true"
    for f in ctx.store.by_kind(Existential):
        if f.cls == cls_p and f.pred == pred:
            return Answer(
                "verdict", "yes" if f.polarity == pol else "undetermined",
                f"existential {cls_p!r}/{pred!r} "
                f"({'+' if f.polarity else '-'}) via {f.provenance.source}",
            )
    # Phase 0: an indefinite-premise atom never witnesses a definite-
    # description pred (same contract as logic-verdict above)
    from ..patterns import field_definite_common

    q_defcom = field_definite_common(ctx.ask, "pred", ctx.match, ctx.question, ctx.reg)
    in_cls = {f.entity for f in ctx.store.by_kind(Atom) if f.pred == cls_p and f.polarity}
    for f in ctx.store.by_kind(Atom):
        if q_defcom and f.indef_obj:
            continue
        if f.entity in in_cls and f.pred == pred and f.polarity == pol:
            return Answer(
                "verdict", "yes",
                f"witness {f.entity!r}: {cls_p!r} and "
                f"{'not ' if not pol else ''}{pred!r}",
            )
    if pol:
        for f in ctx.store.by_kind(Quantified):
            if f.cls == cls_p and f.pred == pred and f.polarity is False:
                return Answer(
                    "verdict", "no",
                    f"negative universal {cls_p!r}/{pred!r} refutes the "
                    f"existential via {f.provenance.source}",
                )
    return Answer("verdict", "undetermined", "no witness and no refuting universal")
