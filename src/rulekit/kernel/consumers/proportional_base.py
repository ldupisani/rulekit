"""Recover a changing base from two shares of one invariant scoped amount."""
from collections import Counter, defaultdict
from math import isfinite
from . import consumer
from ..answer import Answer, AnswerProof, ProofStep, SemanticNode
from ..model import ProportionalBaseEvidence
from ..numeric_evidence import audit_numeric_mentions
from ..source_coverage import uncovered_document_units
from ..evaluate import evaluate


@consumer("proportional-base")
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
