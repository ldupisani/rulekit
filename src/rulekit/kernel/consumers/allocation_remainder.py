"""One participant's ratio-allocated share after a stated expense."""

from collections import Counter
from math import isfinite

from ..source_coverage import uncovered_units

from . import consumer
from ..model import AllocationRatio, Quantity
from ..rate_calculation import apply_rate
from ..numeric_evidence import audit_numeric_mentions
from ..resource_equations import resource_residual


@consumer("allocation-remainder")
def consume(ctx):
    from ..answer import Answer, AnswerProof, ProofStep, SemanticNode

    def decline(reason):
        return Answer("decline", None, reason)

    ratios = list(ctx.store.by_kind(AllocationRatio))
    amounts = list(ctx.store.by_kind(Quantity))
    if len(ratios) != 1 or len(amounts) != 1:
        return decline("the allocation needs one ratio and one participant's received share")
    ratio, anchor = ratios[0], amounts[0]
    entity = ctx.query["entity"]
    if (ratio.first == ratio.second or entity not in (ratio.first, ratio.second)
            or anchor.entity not in (ratio.first, ratio.second) or anchor.entity == entity
            or not ctx.reg.word_in_category(anchor.verb, "acquire")
            or anchor.owner or anchor.qualifier or anchor.measure_qualifier or anchor.label
            or anchor.measure != ctx.query["measure"]
            or ratio.provenance.sentence >= anchor.provenance.sentence
            or ratio.provenance.assumption):
        return decline("the received amount must identify the other participant's share of this allocation")
    expense = float(ctx.query["expense"])
    if (ratio.group_size != 2 or not all(isfinite(v) and v > 0
                                         for v in (ratio.numerator, ratio.denominator))
            or not all(isfinite(v) and v >= 0 for v in (anchor.value, expense))):
        return decline("allocation parts must be positive and currency amounts nonnegative")
    for reading in (*ctx.premises, ctx.question):
        if reading.sentence_index == anchor.provenance.sentence:
            # The ordinary receipt fold is reusable evidence, but only a
            # complete simple subject-verb-amount statement can anchor it.
            units = [u for u in reading.units if u.sense() not in {"article", "punct"}]
            if (len(units) != 3 or units[0].features.get("lemma") != anchor.entity
                    or units[1].features.get("lemma") != anchor.verb
                    or units[2].features.get("value") != anchor.value):
                return decline("the share receipt has an unread condition or competing scope")
            continue
        covered = ctx.match.consumed if reading is ctx.question else frozenset()
        if uncovered_units(reading, covered):
            return decline("the allocation has an unread condition or transaction")
    expected = {
        ratio.provenance.sentence: Counter([ratio.group_size, ratio.numerator, ratio.denominator]),
        anchor.provenance.sentence: Counter([anchor.value]),
        ctx.question.sentence_index: Counter([expense]),
    }
    error = audit_numeric_mentions((*ctx.premises, ctx.question), expected,
                                   missing="a stated amount lies outside the allocation",
                                   duplicate="allocation evidence repeats a source amount")
    if error:
        return decline(error)
    share = apply_rate(ratio, anchor.value, ctx.log, source="allocated-share",
                       inverse=entity == ratio.second)
    remaining = resource_residual([share], [expense], ctx.log, source="allocation-remainder")
    if remaining < 0:
        return decline("the stated expense exceeds this participant's allocated share")
    ctx.log.consumed_allocation_ratio_keys.add(ratio.key())
    node = SemanticNode("allocation-remainder", (("entity", entity),
                         ("resource", ratio.resource), ("source", ratio.source),
                         ("measure", anchor.measure)))
    detail = (f"{entity}'s allocated share is {share:g}; after spending {expense:g} "
              f"on {ctx.query['item']}, {remaining:g} remains in that share. "
              "This is not a claim about total personal wealth.")
    return Answer("number", remaining, detail, proof=AnswerProof(node, (
        ProofStep("proportional-allocation-remainder", node, (ratio, anchor), detail),)))
