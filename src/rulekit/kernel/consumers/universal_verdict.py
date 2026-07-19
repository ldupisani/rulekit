"""`universal-verdict` — A universal conclusion over the quantified facts.

Moved out of `answer.py` UNCHANGED. The only edits are `query`/`reg`/`store`/
`question`/`log`/`_match`/`ask` becoming `ctx.` lookups.

⚠ TIME-SCOPED: this consumer lived BELOW the temporal origo, so it has
always received the time-FILTERED store. It registers `time_scoped=True`
and is dispatched after the origo; without the flag it would silently
answer from unfiltered facts.
"""

from __future__ import annotations

from . import ConsumerContext, consumer


@consumer("universal-verdict", time_scoped=True)
def universal_verdict(ctx: ConsumerContext):
    from ..answer import Answer

    # "Is it true that all/no CLS are PRED?" — read the SATURATED
    # Quantified closure (synth/universal-chain materializes
    # transitivity, so an echo test covers chains too). Open-world and
    # WITHOUT existential import in either direction: "No A are B" never
    # falsifies "All A are B" by itself — over an empty class both are
    # vacuously true in FOL, and FOLIO golds are FOL-verified. 'no' comes
    # ONLY from a counterexample witness (an entity in the class holding
    # the pred at the opposite polarity); when the class has a member,
    # saturation instantiates the opposite universal into exactly that
    # witness atom, so the witness path is complete without the unsound
    # shortcut. Full-read contract as the verdict consumers above.
    from ..model import Atom, Quantified
    from ..patterns import SKIPPABLE_SENSES

    unread = [
        u.surface
        for u in ctx.question.units
        if u.sense() not in SKIPPABLE_SENSES and u.uid not in ctx.match.consumed
    ]
    if unread:
        return Answer(
            "decline", None,
            f"question states {unread!r} but the universal query never read it",
        )
    cls_p, pred = ctx.query["cls"], ctx.query["pred"]
    pol = ctx.query.get("polarity", "true") == "true"  # True = ∀, False = ∀¬
    for f in ctx.store.by_kind(Quantified):
        if f.cls == cls_p and f.pred == pred and f.polarity == pol:
            return Answer(
                "verdict", "yes",
                f"universal {cls_p!r}/{pred!r} "
                f"({'+' if pol else '-'}) via {f.provenance.source}",
            )
    # Phase 0: an indefinite-premise atom is no counterexample to a
    # definite-description pred (composition-design.md)
    from ..patterns import field_definite_common

    q_defcom = field_definite_common(ctx.ask, "pred", ctx.match, ctx.question, ctx.reg)
    in_cls = {f.entity for f in ctx.store.by_kind(Atom) if f.pred == cls_p and f.polarity}
    for f in ctx.store.by_kind(Atom):
        if q_defcom and f.indef_obj:
            continue
        if f.entity in in_cls and f.pred == pred and f.polarity == (not pol):
            return Answer(
                "verdict", "no",
                f"counterexample {f.entity!r}: {cls_p!r} and "
                f"{'not ' if pol else ''}{pred!r}",
            )
    return Answer(
        "verdict", "undetermined", "no universal fact and no counterexample"
    )
