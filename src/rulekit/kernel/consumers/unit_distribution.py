"""Count recipients once and convert between packages, wholes and their units."""

from collections import Counter, defaultdict
from math import isfinite
from . import consumer
from ..answer import (
    Answer,
    AnswerAssumption,
    ClarificationOption,
    ClarificationRequest,
    SemanticNode,
)
from ..evaluate import evaluate
from ..model import BatchEvidence, Quantity
from ..numeric_evidence import audit_numeric_mentions
from ..reference_identity import ReferenceIdentity, constrains, reference_from_unit
from ..source_coverage import quantity_ledger_source_units, uncovered_units


@consumer(
    "unit-distribution",
    applicable=lambda s: any(
        r.kind in {"distribution-stock", "distribution-capacity", "distribution-partition"}
        for r in s.by_kind(BatchEvidence)
    ),
)
def consume(ctx):
    def decline(reason):
        return Answer("decline", None, reason)

    rows = list(ctx.store.by_kind(BatchEvidence))
    population = [r for r in rows if r.kind == "distribution-population"]
    contexts = [r for r in rows if r.kind == "distribution-context"]
    capacities = [r for r in rows if r.kind == "distribution-capacity"]
    stocks = [r for r in rows if r.kind == "distribution-stock"]
    partitions = [r for r in rows if r.kind == "distribution-partition"]
    servings = [r for r in rows if r.kind == "distribution-serving"]
    requirements = [r for r in rows if r.kind == "distribution-per-recipient"]
    opening_quantities = list(ctx.store.by_kind(Quantity))
    if (
        not population
        or ctx.store.collisions
        or ctx.store.quarantined
        or len(rows) + len(opening_quantities) != len(ctx.store.facts)
        or len(rows)
        != sum(
            map(
                len,
                (
                    population,
                    contexts,
                    capacities,
                    stocks,
                    partitions,
                    servings,
                    requirements,
                ),
            )
        )
        or any(
            not isfinite(r.value) or r.value < 0 or not float(r.value).is_integer()
            for r in rows
        )
    ):
        return decline(
            "one complete stock or package specification and a counted recipient roster are required"
        )
    expected = defaultdict(Counter)
    covered = defaultdict(set)
    assumptions = ()
    for row in population:
        # An overt singular role establishes one person without a numeric token.
        if not row.container:
            expected[row.provenance.sentence][row.value] += 1
    if len({(r.measure, r.container) for r in population}) != len(population):
        return decline(
            "recipient groups must be distinct; repeated groups could overlap"
        )
    count = evaluate(
        " + ".join(str(r.value) for r in population),
        {},
        ctx.log,
        source="recipient-count",
    )
    if ctx.query["mode"] == "packages":
        if (
            len(capacities) != 1
            or len(contexts) != 1
            or stocks
            or opening_quantities
            or partitions
            or servings
        ):
            return decline(
                "package coverage needs one product specification and a complete recipient roster"
            )
        capacity, context = capacities[0], contexts[0]
        who = reference_from_unit(ctx.match.slots["who"])
        if (
            context.entity_ref != who
            or capacity.container != ctx.query["package"]
            or capacity.acquisition != ctx.query["item"]
            or context.measure != ctx.query["item"]
            or capacity.value <= 0
            or any(
                r.entity_ref != who
                or not constrains(context.container_ref, r.container_ref)
                for r in population
            )
        ):
            return decline(
                "the requested packages, product and recipient groups must agree"
            )
        expected[capacity.provenance.sentence][capacity.value] += 1
        # Group population rows preserve a team scope, not an extra numeric operand.
        for row in population:
            expected[row.provenance.sentence][row.value] += 1
        units = 1.0
        if requirements:
            if (
                len(requirements) != 1
                or requirements[0].measure != capacity.measure
                or any(
                    not (
                        r.measure == requirements[0].container
                        or ctx.reg.category_term_contains(
                            requirements[0].container, r.measure
                        )
                    )
                    for r in population
                )
            ):
                return decline(
                    "the unit requirement must cover every listed recipient class"
                )
            units = requirements[0].value
            expected[requirements[0].provenance.sentence][units] += 1
        elif ctx.interpretation != "one-unit-each" and not (
            ctx.reg.word_in_category(capacity.attribute, "individual_unit_attribute")
            or (
                not capacity.attribute
                and ctx.reg.word_in_category(
                    capacity.measure, "individual_serving_measure"
                )
            )
        ):
            return Answer(
                "decline",
                None,
                "the required number of units per recipient must be specified",
                clarification=ClarificationRequest(
                    "Should every listed recipient receive one unit?",
                    (
                        ClarificationOption(
                            "one-unit-each",
                            "One unit each",
                            "Count all the listed groups and allocate one unit per person.",
                            SemanticNode("per-recipient-units", (("value", 1),)),
                        ),
                    ),
                ),
            )
        value = evaluate(
            "(required + capacity - 1) // capacity",
            {
                "required": evaluate(
                    "people * units",
                    {"people": count, "units": units},
                    ctx.log,
                    source="required-distribution-units",
                ),
                "capacity": capacity.value,
            },
            ctx.log,
            source="whole-package-coverage",
        )
    else:
        if (
            len(stocks) + len(opening_quantities) != 1
            or len(partitions) != 1
            or len(servings) != 1
            or capacities
            or contexts
            or requirements
        ):
            return decline(
                "a piece remainder needs one stock, partition and explicit per-recipient serving"
            )
        stock = (stocks or opening_quantities)[0]
        partition, serving = partitions[0], servings[0]
        if opening_quantities:
            source = next(r for r in ctx.premises if r.sentence_index == stock.provenance.sentence)
            footprint = quantity_ledger_source_units(source, [stock], ctx.reg)
            whole_ref = stock.measure_ref or ReferenceIdentity(
                stock.measure, qualifiers=(stock.measure_qualifier,) if stock.measure_qualifier else (),
            )
            if (
                (not footprint and uncovered_units(source))
                or stock.provenance.assumption
                or not ctx.reg.word_in_category(stock.verb, "possession_state")
                or stock.time or stock.owner or stock.label or stock.qualifier
                or stock.content_ref
                or not isfinite(stock.value) or stock.value < 0
                or not ctx.reg.word_in_category(stock.measure, "decomposable_quantity_whole")
                or not float(stock.value).is_integer()
                or not all(
                    source.sentence_index < row.provenance.sentence < partition.provenance.sentence
                    and row.acquisition_ref is not None
                    and (not row.acquisition_ref.resolved or constrains(row.acquisition_ref, whole_ref))
                    for row in population
                )
            ):
                return decline("the sharing clause needs one previously identified opening stock")
            covered[source.sentence_index].update(footprint)
        else:
            whole_ref = stock.container_ref
        if ctx.query.get("recipient"):
            if ctx.query_reference("recipient") != stock.entity_ref:
                return decline("the requested recipient must be the holder of the remaining stock")
            assumptions = (
                AnswerAssumption(
                    "stock-holder-keeps-unallocated-units",
                    "The stock holder can take all unallocated units.",
                    (stock.provenance.sentence, partition.provenance.sentence),
                ),
            )
        if (
            partition.entity_ref != stock.entity_ref
            or serving.entity_ref != stock.entity_ref
            or any(r.entity_ref != stock.entity_ref for r in population)
            or partition.container != stock.measure
            or not constrains(partition.container_ref, whole_ref)
            or partition.measure != ctx.query["measure"]
            or serving.marker != "include-owner"
            or partition.value <= 0
        ):
            return decline(
                "stock, explicit participant list and subdivision must identify one distribution"
            )
        groups = [r for r in population if not r.container]
        named = [r for r in population if r.container]
        if (
            len(groups) != 1
            or len(named) != 1
            or named[0].container_ref == stock.entity_ref
            or groups[0].measure != serving.acquisition
            or named[0].container_ref != serving.container_ref
        ):
            return decline(
                "the serving list must repeat the counted group and the same named individual"
            )
        # Count the owner because the explicit serving roster includes the owner.
        count = evaluate(
            "recipients + owner",
            {"recipients": count, "owner": 1},
            ctx.log,
            source="explicit-owner-recipient",
        )
        # Different piece words can identify the same unique stated subdivision.
        if serving.measure != partition.measure and not all(
            ctx.reg.word_in_category(word, "component_quantity_measure")
            for word in (serving.measure, partition.measure)
        ):
            return decline("the serving unit must identify the stated subdivision")
        expected[stock.provenance.sentence][stock.value] += 1
        expected[partition.provenance.sentence][partition.value] += 1
        expected[serving.provenance.sentence][serving.value] += 1
        value = evaluate(
            "wholes * pieces - people * serving",
            {
                "wholes": stock.value,
                "pieces": partition.value,
                "people": count,
                "serving": serving.value,
            },
            ctx.log,
            source="distributed-piece-remainder",
        )
        if value < 0:
            return decline("the stated stock cannot supply the complete serving roster")
    if (
        any(uncovered_units(reading, covered[reading.sentence_index]) for reading in ctx.premises)
        or uncovered_units(ctx.question, ctx.match.consumed)
        or audit_numeric_mentions(
            (*ctx.premises, ctx.question),
            expected,
            missing="missing",
            duplicate="duplicate",
        )
    ):
        return decline(
            "every package, recipient group and serving condition must be accounted for"
        )
    ctx.log.consumed_batch_keys.update(r.key() for r in rows)
    reason = "count the explicit recipients once, then apply the stated units per whole and per recipient"
    if ctx.query["mode"] == "packages" and not requirements:
        reason += "; treating the listed groups as the complete roster, with one individual unit per recipient"
        if ctx.interpretation != "one-unit-each":
            assumptions = (
                AnswerAssumption(
                    "one-individual-unit-per-recipient",
                    "The listed groups form the complete roster, with one individual unit per recipient.",
                    tuple(sorted({r.provenance.sentence for r in population})),
                ),
            )
    return Answer("number", value, reason, assumptions=assumptions)
