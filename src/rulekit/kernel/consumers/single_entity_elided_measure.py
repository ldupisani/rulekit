"""`single-entity-elided-measure` — A single-entity total whose measure is elided.

Moved out of `answer.py` UNCHANGED. The only edits are `query`/`reg`/`store`/
`question`/`log`/`_match`/`ask` becoming `ctx.` lookups.

⚠ TIME-SCOPED: this consumer lived BELOW the temporal origo, so it has
always received the time-FILTERED store. It registers `time_scoped=True`
and is dispatched after the origo; without the flag it would silently
answer from unfiltered facts.
"""

from __future__ import annotations

from . import ConsumerContext, consumer


@consumer("single-entity-elided-measure", time_scoped=True)
def single_entity_elided_measure(ctx: ConsumerContext):
    from ..answer import Answer
    from ..model import Quantity, Relation
    from ..totals import _entity_total, _verb_total

    # mining candidate elided-measure-entity-asks: the question has NO
    # item/measure noun at all ("How many does Tom have?", "How many
    # did Tom make?") — unlike `single-entity` above, which always
    # binds `measure` from an `item` slot. The measure is supplied as
    # the UNIQUE measure for which the asked entity holds ANY fact —
    # the same unique-pool-in-play discipline `unique-entity` above
    # uses (there the entity is elided and the measure given; here
    # it's the mirror image). More than one measure in play for the
    # entity is genuinely ambiguous ("Tom has 5 marbles and 3
    # pencils. How many does Tom have?") and must decline, never guess
    # document-level.
    entity = ctx.query["entity"]
    # The question omits its measure, so ambiguity is determined by every
    # measure the discourse puts in play for this entity—not only by already
    # resolved Quantity facts.  An unresolved Relation still names a distinct
    # measure ("Eron sold 3 eggs and twice as many teachers as ..."). Ignoring
    # it lets the one direct Quantity masquerade as the only possible object
    # and produces a confident partial answer.
    candidates = sorted(
        {q.measure for q in ctx.store.by_kind(Quantity) if q.entity == entity}
        | {
            relation.measure
            for relation in ctx.store.by_kind(Relation)
            if relation.subject == entity
            and isinstance(relation.measure, str)
            and relation.measure
        }
    )
    if len(candidates) != 1:
        return Answer(
            "decline", None,
            f"{entity!r} holds {len(candidates)} measures — an "
            "elided-measure ask needs exactly one",
        )
    measure = candidates[0]
    ask_verb = ctx.query.get("verb", "have")
    is_state_ask = ask_verb in ("have", "be") or ctx.reg.word_in_category(ask_verb, "state")
    if not is_state_ask:
        # mirrors the single-entity event branch, minus the
        # owner/qualifier and derived-total (spend/wage) paths — this
        # ask never binds a possessive/qualified subject or a
        # currency-category measure (there is no `item` slot to carry
        # one), so none of that machinery applies here.
        total = _verb_total(ctx.store, entity, measure, ask_verb, ctx.log)
        if total is not None:
            return Answer(
                "number", total, f"Σ {ask_verb!r} events of {entity!r}/{measure!r}"
            )
        return Answer(
            "decline", None,
            f"no {ask_verb!r} events known for {entity!r}/{measure!r}",
        )
    total = _entity_total(ctx.store, ctx.reg, entity, measure, ctx.log)
    if total is None:
        return Answer(
            "decline", None,
            f"no quantity known for {entity!r} of {measure!r} (ask {ctx.ask.id})",
        )
    return Answer("number", total, f"fold over {entity!r}/{measure!r}")
