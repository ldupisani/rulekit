"""Remaining components of disjoint named participants' divisible wholes."""
from collections import Counter, defaultdict
from dataclasses import replace
from math import isclose, isfinite
from . import consumer
from ..answer import Answer, AnswerProof, ProofStep, SemanticNode
from ..model import BatchEvidence, FractionQuantity
from ..numeric_evidence import audit_numeric_mentions
from ..source_coverage import uncovered_document_units
from ..evaluate import evaluate
from ..resource_equations import resource_residual
from ..reference_identity import ReferenceIdentity, reference_from_unit, constrains


def has_portions(store):
    return any(f.kind == "component-population" for f in store.by_kind(BatchEvidence))


@consumer("portion-remainder", applicable=has_portions)
def consume(ctx):
    def decline(reason):
        return Answer("decline", None, reason)

    rows = list(ctx.store.by_kind(BatchEvidence))
    populations = [r for r in rows if r.kind == "component-population"]
    shares = [r for r in rows if r.kind == "component-share"]
    if len(populations) != 1 or not shares or len(rows) != 1 + len(shares):
        return decline("portions need one named population and explicit subgroup shares")
    population = populations[0]
    # A single explicitly established population licenses later less-specific
    # references. Every overt modifier must still constrain that same population.
    def whole_reference(row):
        ref = row.entity_ref or ReferenceIdentity(row.entity)
        if ref.label or (ref.owner and not ctx.reg.word_in_category(
                ref.owner.head, "group_possessive_determiner")):
            return None
        if not ref.resolved and not (ref.owner and row.attribute and
                ctx.reg.word_in_category(row.attribute, "group_possessive_determiner")):
            return None
        if any(not ctx.reg.attribute_applies_to(q, ref.head) for q in ref.qualifiers):
            return None
        # The named subgroup supplies the group-possessive scope explicitly.
        return replace(ref, owner=None, resolved=True)

    population_ref = whole_reference(population)
    parts_ref = reference_from_unit(ctx.match.slots["parts"])
    whole_heads = [q for q in parts_ref.qualifiers
                   if ctx.reg.word_in_category(q, "decomposable_quantity_whole")]
    if (ctx.store.collisions or ctx.store.quarantined or population.provenance.assumption
            or population.measure != ctx.query["measure"] or population_ref is None
            or parts_ref.owner or parts_ref.label or not parts_ref.resolved
            or parts_ref.qualifiers and len(whole_heads) != 1):
        return decline("the requested components need one consistent whole and measure")
    if whole_heads:
        asked = ReferenceIdentity(whole_heads[0], qualifiers=tuple(
            q for q in parts_ref.qualifiers if q != whole_heads[0]))
        if not constrains(asked, population_ref):
            return decline("the requested pieces describe a different whole")
    if (not isfinite(population.value) or population.value <= 0
            or not float(population.value).is_integer()
            or len(set(population.members)) != len(population.members)):
        return decline("each named participant needs a positive whole-number piece count")
    covered = []
    used = []
    expected = defaultdict(Counter)
    expected[population.provenance.sentence][population.value] += 1
    for share in shares:
        share_ref = whole_reference(share)
        if (share_ref is None or not constrains(share_ref, population_ref) or not 0 <= share.value <= 1
                or not isfinite(share.value) or not share.members
                or share.provenance.sentence <= population.provenance.sentence):
            return decline("each subgroup needs a valid fraction of the same earlier wholes")
        if share.attribute and not ctx.reg.word_in_category(share.attribute, "group_possessive_determiner"):
            return decline("the consumed wholes must belong to the named subgroup")
        covered.extend(share.members)
        expected[share.provenance.sentence][share.value] += 1
        amount = evaluate("members * parts * fraction",
                          {"members": len(share.members), "parts": population.value, "fraction": share.value},
                          ctx.log, source="subgroup-consumed-pieces")
        # Pieces need not be distributed evenly within a subgroup, but a
        # fractional remaining piece is outside this whole-piece question.
        if not isclose(amount, round(amount), abs_tol=1e-8):
            return decline("the subgroup fraction does not describe whole pieces")
        used.append(amount)
    if Counter(covered) != Counter(population.members):
        return decline("the named subgroups must be disjoint and exhaust the population")
    if (uncovered_document_units(ctx.premises, ctx.question, ctx.match.consumed)
            or audit_numeric_mentions((*ctx.premises, ctx.question), expected, missing="missing", duplicate="duplicate")):
        return decline("all content and amounts must belong to this portion partition")
    total = evaluate("members * parts", {"members": len(population.members), "parts": population.value},
                     ctx.log, source="initial-pieces")
    value = resource_residual([total], used, ctx.log, source="uneaten-pieces")
    # A singleton can also have the generic fraction-of-pool reading. Account
    # for it only when it describes precisely the same checked portion event.
    fractions = list(ctx.store.by_kind(FractionQuantity))
    for fraction in fractions:
        matches = [share for share in shares
                   if share.members == (fraction.entity,)
                   and share.provenance.sentence == fraction.provenance.sentence
                   and share.entity == fraction.measure
                   and share.value == fraction.fraction
                   and (not fraction.pool_qualifier or fraction.pool_qualifier in
                        (share.entity_ref.qualifiers if share.entity_ref else ()))
                   and ctx.reg.word_in_category(fraction.verb, "eating_quantity_verb")]
        if len(matches) != 1:
            return decline("a fractional event does not match a checked individual portion")
    ctx.log.consumed_fraction_keys.update(f.key() for f in fractions)
    ctx.log.consumed_batch_keys.update(r.key() for r in rows)
    node = SemanticNode("portion-remainder", (("whole", population.entity), ("measure", population.measure)))
    detail = f"{total:g} initial pieces minus {sum(used):g} consumed = {value:g}"
    return Answer("number", value, detail, proof=AnswerProof(node, (ProofStep("disjoint-portion-partition", node, tuple(rows), detail),)))
