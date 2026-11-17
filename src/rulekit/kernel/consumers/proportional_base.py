"""Recover a base from scoped proportional evidence."""
from collections import Counter, defaultdict
from math import isclose, isfinite
from . import consumer
from ..answer import Answer, AnswerAssumption, AnswerProof, ProofStep, SemanticNode
from ..composition_evidence import closed_evidence, finish_batch_answer
from ..model import BatchEvidence, ProportionalBaseEvidence
from ..numeric_evidence import audit_numeric_mentions
from ..source_coverage import uncovered_document_units
from ..evaluate import evaluate


_NESTED_SHARE_KINDS = {"subset-nested-share", "subset-nested-attribute-share"}


@consumer("proportional-base", applicable=lambda store: bool(store.by_kind(ProportionalBaseEvidence)))
def consume(ctx):
    def decline(reason):
        return Answer("decline", None, reason)
    rows = list(ctx.store.by_kind(ProportionalBaseEvidence))
    by_kind = {k: [r for r in rows if r.kind == k]
               for k in ("prior-share", "base-increase", "invariant-share")}
    if len(rows) != 3 or any(len(rs) != 1 for rs in by_kind.values()):
        return decline("a changing base needs two shares of one invariant expense and one additive change")
    prior, change, later = (by_kind[k][0] for k in by_kind)
    if (not ctx.query["entity"] or any(r.entity != ctx.query["entity"] for r in rows)
            or prior.owner != prior.entity
            or prior.resource != later.resource or ctx.query["resource"] != prior.resource
            or Counter(prior.scope) != Counter(later.scope) or not prior.scope
            or len(set(prior.scope)) != len(prior.scope) or prior.period != later.period
            or not prior.provenance.sentence < change.provenance.sentence <= later.provenance.sentence):
        return decline("the fractions and change need the same owner, periodic income and unchanged expense bundle")
    if (any(r.provenance.assumption for r in rows) or ctx.store.collisions or ctx.store.quarantined
            or not ctx.reg.word_in_category(change.resource, "periodic_income_noun")
            or not ctx.reg.word_in_category(change.measure, "currency_measure")
            or not all(isfinite(r.value) for r in rows)
            or not 0 < later.value < prior.value <= 1 or change.value <= 0):
        return decline("the increase must be positive and the invariant expense's fractional share must decrease")
    expected = defaultdict(Counter)
    for row in rows:
        expected[row.provenance.sentence][row.value] += 1
    if (uncovered_document_units(ctx.premises, ctx.question, ctx.match.consumed)
            or audit_numeric_mentions((*ctx.premises, ctx.question), expected, missing="missing", duplicate="duplicate")):
        return decline("the proportional change has unread conditions or amounts")
    value = evaluate("new_share * increase / (old_share - new_share)",
                     {"new_share": later.value, "increase": change.value, "old_share": prior.value},
                     ctx.log, source="invariant-expense-base")
    ctx.log.consumed_proportional_base_keys.update(r.key() for r in rows)
    node = SemanticNode("proportional-base", (("entity", prior.entity), ("resource", prior.resource)))
    detail = f"{prior.value:g} × prior = {later.value:g} × (prior + {change.value:g}); prior = {value:g}"
    return Answer("number", value, detail, proof=AnswerProof(node, (ProofStep("invariant-expense-equation", node, tuple(rows), detail),)))


def has_nested_subset(store):
    return any(row.kind in _NESTED_SHARE_KINDS for row in store.by_kind(BatchEvidence))


def nested_subset(ctx):
    def decline(reason):
        return Answer("decline", None, reason)

    rows = list(ctx.store.by_kind(BatchEvidence))
    populations = [row for row in rows if row.kind == "subset-population"]
    partitions = [row for row in rows if row.kind in _NESTED_SHARE_KINDS]
    counts = [row for row in rows if row.kind in {"subset-observed-count", "subset-observed-attribute-count"}]
    if len(populations) != 1 or len(partitions) != 1:
        return decline("one collection and one nested share are required")
    population, shares = populations[0], partitions[0]
    flavor = shares.kind == "subset-nested-share"
    if not counts and not flavor:
        return decline("the observed count must identify both attributes of the nested subset")
    if len(rows) != 3 or len(counts) != 1:
        return decline("one observed count and a complete nested subset are required")
    observed = counts[0]
    holder = ctx.query_reference("holder")
    verb = ctx.match.slots["verb"]
    if (holder is None or not holder.resolved or population.entity_ref != holder
            or ctx.query.get("measure_substance")
            or not ctx.reg.word_in_category(verb.surface.casefold(), "plural_copula")
            or population.measure != ctx.query["measure"] or shares.measure != population.measure
            or observed.measure and observed.measure != population.measure
            or not population.provenance.sentence < shares.provenance.sentence < observed.provenance.sentence
            or population.provenance.assumption or shares.provenance.assumption
            or shares.container_ref is None or shares.container_ref.qualifiers != (shares.attribute,)
            or observed.value <= 0 or not float(observed.value).is_integer()
            or not closed_evidence(ctx, rows, [(shares, [shares.value, shares.fraction]), (observed, [observed.value])])):
        return decline("the observed count must belong to the same named nested subset")

    if flavor:
        if (observed.kind != "subset-observed-count" or observed.marker != shares.marker
                or observed.attribute not in ("", shares.attribute)):
            return decline("the observed flavor must match the stated nested share")
    elif (observed.kind != "subset-observed-attribute-count"
          or {observed.attribute, observed.marker} != {shares.attribute, shares.marker}
          or observed.container_ref is not None and observed.container_ref.qualifiers != (observed.attribute,)):
        return decline("the observed count must identify both attributes of the nested subset")
    parent_count = evaluate("count / share", dict(count=observed.value, share=shares.fraction),
                            ctx.log, source="nested-subset-parent")
    total = evaluate("parent / share", dict(parent=parent_count, share=shares.value),
                     ctx.log, source="nested-subset-population")
    if any(not isfinite(count) or not isclose(count, round(count), abs_tol=1e-9, rel_tol=0)
           for count in (parent_count, total)):
        return decline("each nested share must describe a whole population")
    value = round(total)
    assumptions = (
        AnswerAssumption("observed-subtype-within-parent",
                         f"The observed {observed.marker} flavor count is entirely within the {shares.attribute} subset.",
                         (shares.provenance.sentence, observed.provenance.sentence)),
    ) if flavor and not observed.attribute else ()
    return finish_batch_answer(ctx, rows, value, "divide the observed subset count by both nested shares",
                               assumptions=assumptions)
