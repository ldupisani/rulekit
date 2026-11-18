"""Compare the unit prices of two offers for the same goods."""

from dataclasses import replace

from . import consumer
from ..answer import Answer, AnswerAssumption
from ..composition_evidence import closed_evidence, finish_batch_answer
from ..evaluate import evaluate
from ..model import BatchEvidence
from ..rate_calculation import convert_units
from ..reference_identity import constrains


@consumer("packaged-unit-price",
    applicable=lambda store: any(row.kind == "packaged-offer" for row in store.by_kind(BatchEvidence)),
)
def packaged_unit_price(ctx):
    rows = list(ctx.store.by_kind(BatchEvidence))
    if (len(rows) != 2 or any(row.kind != "packaged-offer" or row.provenance.assumption
                            or row.container != ctx.query["unit"] or row.per_member <= 0
                            or not float(row.per_member).is_integer() for row in rows)):
        return Answer("decline", None, "two comparable offers need explicit counts in the requested unit")
    first, second = sorted(rows, key=lambda row: row.provenance.sentence)
    target = ctx.query_reference("target")
    first_goods, second_goods = first.acquisition_ref, second.acquisition_ref
    if second.marker and second_goods is not None:
        second_goods = replace(second_goods, qualifiers=tuple(
            word for word in second_goods.qualifiers
            if not ctx.reg.word_in_category(word, "uniform_quantity_attribute")
        ))
    if (first.entity_ref is None or second.entity_ref is None
            or first.entity_ref == second.entity_ref
            or first_goods is None or second_goods != first_goods
            or first.marker or not first_goods.resolved
            or not closed_evidence(ctx, rows, [(row, [row.value, row.per_member]) for row in rows])):
        return Answer("decline", None, "both offers must name the same goods and complete prices")
    candidates = [row for row in rows if target is not None and constrains(target, row.entity_ref)]
    if len(candidates) != 1:
        return Answer("decline", None, "one seller must be identified by the question")
    selected = candidates[0]
    standard = next(row for row in rows if row is not selected)
    amounts = [convert_units(row.value, row.measure, ctx.query["measure"], ctx.reg, ctx.log,
                             source="offer-price-currency") for row in (selected, standard)]
    if None in amounts:
        return Answer("decline", None, "both prices must convert to the requested currency unit")
    selected_total, standard_total = amounts
    value = evaluate(
        "target / target_count - standard / standard_count",
        dict(target=selected_total, target_count=selected.per_member,
             standard=standard_total, standard_count=standard.per_member),
        ctx.log, source="quoted-unit-price-difference",
    )
    if value < -1e-9:
        return Answer("decline", None, "the named offer does not have the higher unit price")
    assumptions = ()
    if second.marker:
        assumptions = (
            AnswerAssumption(
                "offer-count-covered-by-quote",
                "Treat the separately stated item count as the quantity covered by that offer price.",
                (second.provenance.sentence,),
            ),
        )
    return finish_batch_answer(ctx, rows, max(0, value), "compare the two quoted prices per item",
                               assumptions=assumptions)
