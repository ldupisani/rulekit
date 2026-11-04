"""Close dependent stock, pooling and adjacent-period quantity accounts."""

from math import isfinite

from . import consumer
from ..composition_evidence import closed_evidence, finish_batch_answer
from ..affine_graph import AffineGraph, AffineError
from ..answer import Answer
from ..evaluate import evaluate
from ..model import BatchEvidence, Quantity, CommercialTerm
from ..learn import _bound
from ..reference_identity import reference_from_unit
from ..source_coverage import quantity_ledger_source_units


@consumer(
    "dependent-quantity-total",
    applicable=lambda store: any(
        r.kind in {"incremental-ratio", "qualified-pool", "previous-period-relative"}
        for r in store.by_kind(BatchEvidence)
    ),
)
def consume(ctx):
    def decline(reason):
        return Answer("decline", None, reason)

    rows = list(ctx.store.by_kind(BatchEvidence))
    observed = list(ctx.store.by_kind(Quantity))
    terms = list(ctx.store.by_kind(CommercialTerm))
    quantities = list(observed)
    if terms and ctx.query["operation"] != "periods":
        return decline(
            "an additional commercial term lies outside the quantity account"
        )
    for term in terms:
        reading = next(
            r for r in ctx.premises if r.sentence_index == term.provenance.sentence
        )
        verbs = [
            u
            for u in reading.units
            if u.sense() == "verb"
            and ctx.reg.word_in_category(u.features.get("lemma", ""), "sell")
        ]
        periods = [
            u
            for u in reading.units
            if ctx.reg.word_in_category(u.features.get("lemma", ""), "duration_measure")
            and u.features.get("qualifier")
        ]
        subject = _bound(verbs[0], "subject") if len(verbs) == 1 else None
        if (
            term.basis != "basket-count"
            or term.measure
            or term.qualifier
            or subject is None
            or len(periods) != 1
            or reference_from_unit(subject).head != term.entity
            or periods[0].features.get("lemma") != term.period
        ):
            return decline(
                "a commercial count needs an explicit participant and reporting period"
            )
        quantities.append(
            Quantity(
                provenance=term.provenance,
                entity=term.entity,
                entity_ref=reference_from_unit(subject),
                measure=term.item,
                value=term.value,
                verb=verbs[0].features["lemma"],
                time=periods[0].surface.casefold(),
            )
        )
    facts = rows + observed + terms
    operands = [(q, [q.value]) for q in quantities]
    covered = {}
    for reading in ctx.premises:
        local = [q for q in observed if q.provenance.sentence == reading.sentence_index]
        if local:
            footprint = quantity_ledger_source_units(reading, local, ctx.reg)
            if not footprint:
                return decline(
                    "each observed stock or period count needs its complete source clause"
                )
            covered[reading.sentence_index] = footprint
    if any(
        not isfinite(q.value) or q.value < 0 or not float(q.value).is_integer()
        for q in quantities
    ):
        return decline("observed discrete stocks must be nonnegative whole counts")
    mode = ctx.query["operation"]
    if mode == "pool":
        links = [r for r in rows if r.kind == "qualified-relative"]
        pools = [r for r in rows if r.kind == "qualified-pool"]
        if (
            len(pools) != 1
            or len(links) < 1
            or len(rows) != len(links) + 1
            or not quantities
        ):
            return decline(
                "an equal pool needs qualified stock comparisons and an explicit sharing event"
            )
        actors = {q.entity_ref for q in quantities}
        standards = {r.container_ref for r in links}
        recipients = {r.entity_ref for r in links}
        if (
            len(actors) != 1
            or actors != standards
            or len(recipients) != 1
            or actors == recipients
            or pools[0].measure != ctx.query["measure"]
            or any(r.measure != ctx.query["measure"] or not r.attribute for r in links)
            or any(
                q.measure.split("[", 1)[0] != ctx.query["measure"]
                or not q.measure_qualifier
                or not ctx.reg.word_in_category(q.verb, "possession_state")
                for q in quantities
            )
            or {q.measure_qualifier for q in quantities} != {r.attribute for r in links}
            or len(links) != len({r.attribute for r in links})
            or len(quantities) != len(links)
            or any(
                r.provenance.sentence <= max(q.provenance.sentence for q in quantities)
                for r in links
            )
            or pools[0].provenance.sentence <= max(r.provenance.sentence for r in links)
        ):
            return decline(
                "the pool must identify the same two holders and an exhaustive set of distinct item classes"
            )
        from ..document import _subject_group

        group = _subject_group(
            list(ctx.premises),
            pools[0].provenance.sentence,
            ctx.reg,
            frozenset(ref.head for ref in actors | recipients),
        )
        if (
            group is None
            or {reference_from_unit(u) for u in group[1]} != actors | recipients
        ):
            return decline(
                "the sharing pronoun needs the same unique complete holder group"
            )
        anchors = [((q.entity_ref, q.measure_qualifier), q.value) for q in quantities]
        edges = [
            ((r.entity_ref, r.attribute), (r.container_ref, r.attribute), r.fraction, 0)
            for r in links
        ]
        operands += [(r, [r.fraction]) for r in links]
        try:
            graph = AffineGraph(anchors, edges, ctx.log)
            values = [graph.value(node) for node in graph.forms]
            if any(v < 0 or not float(v).is_integer() for v in values):
                return decline(
                    "the qualified stocks must have nonnegative whole item counts"
                )
            total = graph.linear([(node, 1) for node in graph.forms])
        except AffineError as error:
            return decline(str(error))
        value = evaluate(
            "total / holders",
            dict(total=total, holders=len(actors | recipients)),
            ctx.log,
            source="equal-qualified-pool",
        )
        if not float(value).is_integer():
            return decline(
                "the stated indivisible stock cannot be shared equally in whole items"
            )
    elif mode == "incremental":
        ratios = [r for r in rows if r.kind == "incremental-ratio"]
        openings = [r for r in rows if r.kind == "incremental-opening"]
        if (
            len(ratios) != 1
            or len(openings) > 1
            or len(rows) != len(ratios) + len(openings)
        ):
            return decline(
                "an incremental acquisition needs one additional ratio and one initial stock"
            )
        ratio = ratios[0]
        who = reference_from_unit(ctx.match.slots["who"])
        if (
            ratio.entity_ref != who
            or ratio.container_ref == who
            or ratio.per_member <= 0
            or ratio.value < 0
            or ratio.measure != ctx.query["measure"]
        ):
            return decline(
                "the acquisition ratio must identify distinct buyers and the requested container unit"
            )
        owned = [q for q in quantities if q.entity_ref == who]
        standards = [q for q in quantities if q.entity_ref == ratio.container_ref]
        if len(standards) != 1 or len(owned) + len(standards) != len(quantities):
            return decline(
                "the additional ratio needs exactly one observed standard count"
            )
        standard = standards[0]
        if (
            standard.measure != ratio.measure
            or not ctx.reg.word_in_category(standard.verb, "purchase")
            or standard.measure_qualifier
            and (
                standard.content_ref is None
                or standard.measure_qualifier != standard.content_ref.head
            )
            or standard.time
        ):
            return decline(
                "the standard purchase must use the ratio's same container class"
            )
        if openings:
            opening = openings[0]
            if (
                owned
                or opening.entity_ref != who
                or opening.measure != ratio.measure
                or opening.container != ctx.query["content"]
                or opening.acquisition_ref != standard.entity_ref
                or ctx.query.get("site")
                and opening.marker != ctx.query["site"]
            ):
                return decline(
                    "the initial purchase, associated buyer and returned contents must agree"
                )
            operands.append((opening, [opening.value]))
            initial = opening.value
        else:
            if (
                len(owned) != 1
                or owned[0].measure != ratio.measure
                or owned[0].content_ref is None
                or standard.content_ref != owned[0].content_ref
                or owned[0].content_ref.head != ctx.query["content"]
                or not ctx.reg.word_in_category(owned[0].verb, "purchase")
            ):
                return decline(
                    "a simplified additional purchase needs explicit matching initial and standard contents"
                )
            opening, initial = owned[0], owned[0].value
        if not isfinite(initial) or initial < 0 or not float(initial).is_integer():
            return decline(
                "the opening stock must be a nonnegative whole container count"
            )
        if opening.provenance.sentence >= ratio.provenance.sentence:
            return decline("the initial stock must precede the additional acquisition")
        operands.append((ratio, [ratio.value, ratio.per_member]))
        factor = evaluate(
            "numerator / denominator",
            dict(numerator=ratio.value, denominator=ratio.per_member),
            ctx.log,
            source="additional-acquisition-ratio",
        )
        try:
            graph = AffineGraph(
                [("opening", initial), ("standard", standard.value)],
                [("additional", "standard", factor, 0)],
                ctx.log,
            )
            value = graph.linear([("opening", 1), ("additional", 1)])
        except AffineError as error:
            return decline(str(error))
        if not float(value).is_integer():
            return decline(
                "the acquisition ratio produces fractional indivisible containers"
            )
    elif mode == "periods":
        if (
            len(rows) != 1
            or rows[0].kind != "previous-period-relative"
            or len(quantities) != 1
        ):
            return decline(
                "an adjacent-period total needs one observed count and one preceding-period comparison"
            )
        edge, base = rows[0], quantities[0]
        who = reference_from_unit(ctx.match.slots["who"])
        if (
            edge.entity_ref != who
            or base.entity_ref != who
            or base.measure != ctx.query["measure"]
            or base.verb != ctx.query["verb"]
            or edge.verb != base.verb
            or ctx.query.get("period")
            and edge.marker != ctx.query["period"]
            or not base.time
            or "span_value" in ctx.query
            and float(ctx.query["span_value"]) != 2
            or base.provenance.sentence >= edge.provenance.sentence
        ):
            return decline(
                "the requested window must be exactly the two stated adjacent activity periods"
            )
        reading = next(
            r for r in ctx.premises if r.sentence_index == base.provenance.sentence
        )
        periods = [
            reference_from_unit(u)
            for u in reading.units
            if u.surface.casefold() == base.time.casefold()
        ]
        if (
            len(periods) != 1
            or periods[0].head != edge.marker
            or len(periods[0].qualifiers) != 1
            or not ctx.reg.word_in_category(
                periods[0].qualifiers[0], "prior_period_attribute"
            )
        ):
            return decline(
                "the observed count must establish the preceding period explicitly"
            )
        operands.append((edge, [edge.fraction]))
        try:
            graph = AffineGraph(
                [((who, 0), base.value)],
                [((who, -1), (who, 0), edge.fraction, 0)],
                ctx.log,
            )
            value = graph.linear([((who, 0), 1), ((who, -1), 1)])
        except AffineError as error:
            return decline(str(error))
        if not float(value).is_integer():
            return decline(
                "the relative period count must remain a whole number of items"
            )
    else:
        return decline("the dependent quantity operation is not declared")
    if not closed_evidence(ctx, facts, operands, covered=covered):
        return decline(
            "every stock, comparison, period and sharing condition must be accounted for"
        )
    ctx.log.consumed_commercial_term_keys.update(t.key() for t in terms)
    return finish_batch_answer(
        ctx,
        facts,
        value,
        "resolve the dependent quantities before totaling or sharing the complete account",
    )
