"""Owned textual extents use the ordinary affine-relation saturation path."""

from math import isclose, isfinite

from . import ConsumerContext, consumer
from ..answer import Answer, AnswerAssumption, AnswerProof, ProofStep, SemanticNode
from ..evaluate import evaluate
from ..model import Quantity, Relation, TextPrefixSplit, TextValue
from ..reference_identity import flat_reference
from ..source_coverage import uncovered_document_units
from ..text_evidence import prefix_remainder


@consumer("text-extent")
def text_extent(ctx: ConsumerContext):
    def decline(reason):
        return Answer("decline", None, reason)

    if ctx.store.quarantined or ctx.store.collisions:
        return decline("the textual attributes have conflicting evidence")
    if uncovered_document_units(ctx.premises, ctx.question, ctx.match.consumed):
        return decline("the text-length problem contains an unread condition or edit")
    if any(not isinstance(f, (TextValue, TextPrefixSplit, Quantity, Relation))
           for f in ctx.store.facts):
        return decline("text extents cannot discard a different kind of evidence")
    measure = ctx.query["measure"]
    quantities = ctx.store.by_kind(Quantity)
    if any(q.measure != measure or not q.is_state or q.time is not None
           or not q.entity_ref.resolved or not q.entity_ref.owner
           or not ctx.reg.word_in_category(q.entity_ref.head, "textual_attribute")
           or not isfinite(q.value) or q.value < 0 or not float(q.value).is_integer()
           for q in quantities):
        return decline("a textual extent must be a nonnegative whole letter count for one owner")

    def quantity(reference):
        candidates = [q for q in quantities if q.entity_ref == reference]
        return candidates[0] if len(candidates) == 1 else None

    # A contradictory relation must not disappear because its subject already
    # has a quantity. Saturation materializes numbers; this verifies every
    # stated equation, including those it did not need to materialize.
    steps = []
    assumptions = []
    for value in ctx.store.by_kind(TextValue):
        count = quantity(value.entity_ref)
        if count is None:
            return decline("a literal text has no unique letter count")
        steps.append(ProofStep("count-written-letters", SemanticNode("text-extent", (
            ("entity", value.entity_ref.display()), ("value", count.value))), (value,),
            f"{value.text!r} contains {count.value:g} letters; only alphabetic characters count, not spaces or hyphens."))
    for split in ctx.store.by_kind(TextPrefixSplit):
        part = quantity(flat_reference(split.part, split.owner))
        wholes = [v for v in ctx.store.by_kind(TextValue)
                  if v.entity_ref == flat_reference(split.whole, split.owner)
                  and v.measure == split.measure]
        if (part is None or len(wholes) != 1
                or prefix_remainder(wholes[0].text, split.prefix, split.layout) is None):
            return decline("the text does not establish the declared component layout")
        remainder = prefix_remainder(wholes[0].text, split.prefix, split.layout)
        interpretation = (
            "Capitalization convention: intervening capitalized parts are given/middle names; "
            "lowercase prefixes immediately before the final capitalized part belong to the surname."
            if split.layout == "capitalized-tail" else
            "Two whitespace-delimited parts; the first matches the independently named prefix."
        )
        steps.append(ProofStep("explicit-prefix-split", SemanticNode("text-component", (
            ("entity", part.entity_ref.display()),)), (split,),
            f"{interpretation} Extracted component: {remainder!r}."))
        assumptions.append(AnswerAssumption("name-component-layout", interpretation,
                                            (split.provenance.sentence,)))
    for relation in ctx.store.by_kind(Relation):
        subject, standard = quantity(relation.subject_ref), quantity(relation.standard_ref)
        if relation.measure != measure or subject is None or standard is None:
            return decline("every text-length comparison needs an exact owned anchor")
        if (not isfinite(relation.factor) or relation.factor <= 0
                or not isfinite(relation.offset) or not float(relation.offset).is_integer()
                or relation.subject_offset or relation.standard_offset
                or relation.measure_qualifier or relation.standard_qualifier):
            return decline("text comparisons require whole-letter changes and an unqualified positive ratio")
        expected = evaluate("factor * standard + offset", {
            "factor": relation.factor, "standard": standard.value,
            "offset": relation.offset,
        }, ctx.log, source="text-extent-relation-check")
        if not isclose(subject.value, expected, abs_tol=1e-9):
            return decline("the text-length comparisons disagree with the stated lengths")
        steps.append(ProofStep("affine-text-extent", SemanticNode("text-extent", (
            ("entity", subject.entity_ref.display()), ("value", subject.value))),
            (relation, standard),
            f"{subject.value:g} = {relation.factor:g} × {standard.value:g} + {relation.offset:g}; original lengths, not edit events."))
    target = quantity(flat_reference(ctx.query["entity"], ctx.query["entity_owner"]))
    if target is None:
        return decline("the requested owned text has no determined letter count")
    return Answer("number", target.value,
                  f"{target.value:g} letters in {target.entity_ref.display()}",
                  proof=AnswerProof(SemanticNode("text-extent", (
                      ("entity", target.entity_ref.display()), ("value", target.value))), tuple(steps)),
                  assumptions=tuple(assumptions))
