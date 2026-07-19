"""`unique-entity` — A total for the sole holder of a measure.

Moved out of `answer.py` UNCHANGED. The only edits are `query`/`reg`/`store`/
`question`/`log`/`_match`/`ask` becoming `ctx.` lookups.

⚠ TIME-SCOPED: this consumer lived BELOW the temporal origo, so it has
always received the time-FILTERED store. It registers `time_scoped=True`
and is dispatched after the origo; without the flag it would silently
answer from unfiltered facts.
"""

from __future__ import annotations

from . import ConsumerContext, consumer


@consumer("unique-entity", time_scoped=True)
def unique_entity(ctx: ConsumerContext):
    from ..answer import Answer
    from .. import deixis
    from ..evaluate import evaluate
    from ..model import GroupTotal, Quantity
    from ..answer import _entity_total, _measure_substance_guard, _resolve_measure

    # an ENTITY-LESS ask ("how many balloons are left?") resolves iff
    # exactly one entity holds the measure — definitive-or-decline
    measure = ctx.query["measure"]
    singular = _resolve_measure(measure, ctx.store, ctx.reg, journal=ctx.log.journal)
    if singular is None:
        return Answer("decline", None,
                      f"measure {measure!r} is ambiguous across the facts")
    measure_substance = ctx.query.get("measure_substance")
    if measure_substance:
        guard = _measure_substance_guard(ctx.store, singular, measure_substance)
        if guard is not None:
            return guard
    entities = sorted(
        {q.entity for q in ctx.store.by_kind(Quantity) if q.measure == singular}
    )
    # An ENTITY-LESS ask ("how many balloons are left?") has, by construction, no
    # reference point: the origo it wants is the narrative present, and there is
    # none. Hence the empty Origo(). Constant metric => byte-identical to the
    # `len(entities) != 1` it replaces; the decline reason is preserved verbatim.
    if deixis.resolve(
        [deixis.Referent(dimension=deixis.PERSON, key=e) for e in entities],
        deixis.Origo(),
        deixis.constant,
        dimension=deixis.PERSON,
        journal=ctx.log.journal,
        source="answer/unique-entity",
    ) is None:
        return Answer(
            "decline", None,
            f"{len(entities)} entities hold {singular!r} — an entity-less "
            "ask needs exactly one",
        )
    entity_less_totals = [gt for gt in ctx.store.by_kind(GroupTotal) if gt.measure == singular]
    if entity_less_totals:
        # mining candidate distributive-each-totals: a GroupTotal for this
        # SAME measure means the lone entity's own Quantity is a PER-CONTAINER
        # rate ("20 chairs in each row"), not the group's whole. An entity-less
        # ask ("how many chairs are there IN ALL?") wants the whole — the
        # GroupTotal is exactly it, so COMMIT it. This shipped first as a
        # DECLINE (folding the lone rate as the total is the confident wrong
        # GroupTotal exists to prevent); the entity-less mirror of the
        # single-entity container consumer above, it can commit now for the
        # SAME reason that path can: saturate's synth was tightened
        # (Provenance.distributive) so a specific instance's count no longer
        # masquerades as a per-container rate, so the surviving total is
        # trustworthy. Two rival totals stay a decline.
        if len(entity_less_totals) == 1:
            total = evaluate(
                f"{entity_less_totals[0].value}", {}, ctx.log, source="group-total"
            )
            return Answer(
                "number", total,
                f"group total of {singular!r} over the counted containers",
            )
        return Answer(
            "decline", None,
            f"{singular!r} has several rival group totals — "
            "an entity-less ask cannot tell which whole is meant",
        )
    total = _entity_total(ctx.store, ctx.reg, entities[0], singular, ctx.log)
    if total is None:
        return Answer("decline", None, f"{entities[0]!r} has no resolvable total")
    return Answer("number", total, f"unique-entity fold over {entities[0]!r}/{singular!r}")
