"""Recover an indexed term of a bounded affine recurrence from its sum.

Cadence determines the number of terms, not their amounts. No vocabulary or
surface parsing lives here: ordinary rules supply typed source facts.
"""

from collections import Counter
from math import isclose, isfinite

from . import ConsumerContext, consumer
from ..answer import Answer, AnswerProof, ProofStep, SemanticNode
from ..evaluate import evaluate, EvaluationError
from ..model import ORDERED_SEQUENCE_KINDS as SEQUENCE_KINDS
from ..source_coverage import uncovered_document_units
from ..numeric_evidence import audit_numeric_mentions
from ..rate_calculation import convert_duration
from ..predicate_compatibility import predicate_concepts


MAX_TERMS = 1000


def affine_terms_from_total(total, count, factor, offset, log):
    """Represent each term as a*x+b, sum coefficients, then solve once.

    The same calculation handles growing/shrinking ratios, additive steps,
    and constant sequences. It never creates anonymous Quantity holders.
    """
    if (not isinstance(count, int) or not 1 <= count <= MAX_TERMS
            or not all(isfinite(v) for v in (total, factor, offset))
            or total < 0 or factor <= 0):
        return None
    try:
        coefficients = [(1.0, 0.0)]
        for _ in range(1, count):
            a, b = coefficients[-1]
            a = evaluate(f"{a} * {factor}", {}, log, source="sequence-coefficient")
            b = evaluate(f"{b} * {factor} + {offset}", {}, log, source="sequence-offset")
            if not isfinite(a) or not isfinite(b):
                return None
            coefficients.append((a, b))
        a_sum = evaluate(" + ".join(str(a) for a, _ in coefficients), {}, log,
                         source="sequence-coefficient-sum")
        b_sum = evaluate(" + ".join(str(b) for _, b in coefficients), {}, log,
                         source="sequence-offset-sum")
        first = evaluate(f"({total} - {b_sum}) / {a_sum}", {}, log,
                         source="sequence-first-term")
        terms = [evaluate(f"{a} * {first} + {b}", {}, log,
                          source="sequence-term") for a, b in coefficients]
    except (ArithmeticError, EvaluationError, RecursionError):
        return None
    if any(not isfinite(v) or v < 0 for v in terms):
        return None
    return terms


@consumer("ordered-sequence")
def ordered_sequence(ctx: ConsumerContext):
    def decline(reason):
        return Answer("decline", None, reason)

    rows = [ctx.store.by_kind(kind) for kind in SEQUENCE_KINDS]
    if any(len(row) != 1 for row in rows) or ctx.store.quarantined:
        return decline("an ordered series needs one cadence, one total and one adjacent-term relation")
    cadence, total, step = (row[0] for row in rows)
    series = str(ctx.query.get("series", ""))
    measure = str(ctx.query.get("measure", ""))
    if series != cadence.series or series != step.series or measure != total.measure or measure != step.measure:
        return decline("the carrier and measured contents must agree across the sequence and ask")
    if total.entity != cadence.entity:
        if not (ctx.reg.word_in_category(total.entity, "sequence_singular_anaphor")
                and cadence.provenance.sentence < total.provenance.sentence):
            return decline("the cadence and total need the same uniquely identified participant")
    if ctx.query.get("entity", cadence.entity) != cadence.entity:
        return decline("the asked participant does not own this sequence")
    if any(q and q != cadence.entity_qualifier for q in (
        total.entity_qualifier, ctx.query.get("entity_qualifier", ""),
    )):
        return decline("the qualified participant does not match the cadence actor")
    verbs = (cadence.verb, total.verb, ctx.query.get("verb", cadence.verb))
    concepts = [predicate_concepts(verb, series, ctx.reg, fallback_to_verb=True) for verb in verbs]
    if len(frozenset.intersection(*concepts)) != 1:
        return decline("the cadence, total and asked event must have one compatible meaning")
    if cadence.value != 1:
        return decline("indexing an interval requires exactly one carrier event per interval")
    if not all(isfinite(v) and v > 0 for v in (cadence.elapsed, total.elapsed)):
        return decline("a sequence needs positive finite cadence and observation durations")
    elapsed = convert_duration(total.elapsed, total.unit, cadence.unit, ctx.reg, ctx.log,
                               source="sequence-duration-unit")
    if elapsed is None:
        return decline("the observation duration is not convertible to the cadence unit")
    count = evaluate(f"{elapsed} / {cadence.elapsed} * {cadence.value}", {}, ctx.log,
                     source="sequence-event-count")
    if not isfinite(count) or not float(count).is_integer() or not 1 <= count <= MAX_TERMS:
        return decline("the observation must contain a bounded integral number of complete intervals")
    requested_period = ctx.query.get("period")
    if requested_period is not None:
        try:
            requested_period = float(requested_period)
        except (TypeError, ValueError):
            return decline("the asked interval needs a numeric duration")
        period = convert_duration(requested_period, ctx.query.get("unit"), cadence.unit,
                                  ctx.reg, ctx.log, source="sequence-asked-interval")
        if period is None or not isclose(period, cadence.elapsed):
            return decline("the asked interval must identify exactly one cadence period")
    index = ctx.reg.attrs.get(ctx.query.get("index", ""), {}).get("sequence_index")
    if index is None or not isfinite(index) or not float(index).is_integer():
        return decline("the ask needs a declared ordinal index")
    if index == -1:
        index = count
    if not 1 <= index <= count:
        return decline("the requested index is outside the observed sequence")

    # A complete source footprint, not merely matching numbers, is required.
    # This refuses exceptions, partial events, different totals, and extra
    # evidence even when their values happen to equal an existing operand.
    expected = {}
    for fact, operands in ((cadence, (cadence.value, cadence.elapsed)),
                           (total, (total.elapsed, total.value))):
        expected.setdefault(fact.provenance.sentence, Counter()).update(operands)
    # The step may state a multiplier or a signed additive magnitude. Defaults
    # are algebraic identities and are not invented source mentions.
    from ..numeric_evidence import numeric_mentions
    step_reading = next((r for r in ctx.premises if r.sentence_index == step.provenance.sentence), None)
    step_mentions = numeric_mentions(step_reading) if step_reading else Counter()
    if not step_mentions and step.factor == 1 and step.offset == 0:
        operands = Counter()  # A plain equative states no numeric operand.
    else:
        operands = Counter([step.factor]) if step_mentions == Counter([step.factor]) and step.offset == 0 else Counter([abs(step.offset)])
    expected.setdefault(step.provenance.sentence, Counter()).update(operands)
    expected[ctx.question.sentence_index] = Counter(
        [float(requested_period)] if requested_period is not None else []
    )
    if audit_numeric_mentions((*ctx.premises, ctx.question), expected,
                              missing="missing", duplicate="duplicate"):
        return decline("the sequence must account for every source-local numeric mention")
    if uncovered_document_units(ctx.premises, ctx.question, ctx.match.consumed):
        return decline("the sequence has an unread condition, event or complement")
    if any(not isinstance(f, SEQUENCE_KINDS) for f in ctx.store.facts):
        return decline("additional facts are not explained by the bounded sequence")
    terms = affine_terms_from_total(total.value, int(count), step.factor, step.offset, ctx.log)
    if terms is None:
        return decline("the recurrence does not determine finite nonnegative term amounts")
    # These ask shapes count discrete contents; fractional people/items are
    # inconsistent evidence, not a quantity to round into a plausible answer.
    if any((0 < v < 1 - 1e-8) or not isclose(v, round(v), abs_tol=1e-8, rel_tol=0) for v in terms):
        return decline("the stated total and recurrence imply fractional discrete contents")
    value = terms[int(index) - 1]
    ctx.log.consumed_sequence_keys.update(f.key() for row in rows for f in row)
    detail = (f"{int(count)} complete intervals; one whole {series} per event; "
              f"the {total.value:g} {measure} total covers those carriers' contents")
    proof = AnswerProof(
        SemanticNode("sequence-term", (("series", series), ("measure", measure), ("index", int(index)))),
        (ProofStep("bounded-carrier-interpretation", SemanticNode("event-count", (("value", int(count)),)),
                   (cadence, total), detail),
         ProofStep("affine-sequence-from-total", SemanticNode("sequence-term", (("value", value),)),
                   (step, total), f"next = {step.factor:g} × previous + {step.offset:g}")),
    )
    return Answer("number", value,
                  f"Term {int(index)} is {value:g} {measure}; interpreting {detail}.", proof=proof)
