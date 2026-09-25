"""A closed, single-account liability equation over explicit source entries."""

from collections import Counter
from math import isfinite

from . import ConsumerContext, consumer
from ..answer import Answer, AnswerProof, ProofStep, SemanticNode
from ..model import AccountEntry
from ..numeric_evidence import audit_numeric_mentions
from ..resource_equations import resource_residual
from ..source_coverage import uncovered_units


@consumer("liability-remainder")
def liability_remainder(ctx: ConsumerContext):
    def decline(reason):
        return Answer("decline", None, reason)

    entries = sorted(ctx.store.by_kind(AccountEntry),
                     key=lambda e: (e.provenance.sentence, int(e.position)))
    if not entries or ctx.store.quarantined or ctx.store.collisions:
        return decline("liability accounting needs unambiguous account evidence")
    entity = ctx.query.get("entity")
    if any(any(value and value != entity for value in (e.entity, e.owner, e.reference_owner))
           for e in entries):
        return decline("liability entries must identify the same borrower")
    if any(e.provenance.assumption for e in entries):
        return decline("liability entries must describe asserted amounts and payments")
    openings = [e for e in entries if e.kind in {"limit", "liability"}]
    draws = [e for e in entries if e.kind == "full-draw"]
    terms = [e for e in entries if e.kind == "settlement"]
    if len(openings) != 1 or len(terms) > 1:
        return decline("liability accounting needs one opening account and at most one deadline")
    opening = openings[0]
    if opening.entity != entity or opening.value is None:
        return decline("the opening liability must name its borrower and amount")
    if any(e.kind == "limit" and e.description.casefold() != e.account or
           e.kind == "full-draw" and e.description.casefold() != f"{e.qualifier} {e.account}"
           for e in entries):
        return decline("qualified credit accounts need an exact account identity")
    if entries[0] is not opening:
        return decline("repayments cannot precede the opening liability")
    if opening.kind == "limit":
        if len(draws) != 1 or entries.index(draws[0]) <= entries.index(opening):
            return decline("a credit limit needs explicit use before it becomes debt")
        debt = draws[0]
    else:
        if draws:
            return decline("a stated debt cannot be combined with another unscoped draw")
        debt = opening
    if terms:
        term = terms[0]
        distance = term.provenance.sentence - opening.provenance.sentence
        required_distance = {"relative": 0, "adjacent": 1}.get(term.attachment)
        if distance != required_distance or entries.index(term) != 1:
            return decline("the settlement requirement must attach to the opening account")
    deadline = ctx.query.get("deadline", "")
    if deadline and (not terms or terms[0].deadline != deadline
                     or ctx.query.get("owner") != entity):
        return decline("the asked deadline needs the same explicit settlement requirement")
    payments = []
    previous = None
    for entry in entries:
        if entry.value is not None and (not isfinite(entry.value) or entry.value < 0
                                        or entry.measure != opening.measure):
            return decline("liability amounts must be nonnegative and use one currency")
        if entry.kind in {"repayment", "coordinated-repayment", "continued-repayment"}:
            if entries.index(entry) <= entries.index(debt):
                return decline("repayments must follow the stated use of credit")
            if not entry.entity:
                allowed = {"repayment", "coordinated-repayment", "continued-repayment"}
                if entry.kind == "coordinated-repayment":
                    allowed.update({"full-draw", "liability"})
                if (previous is None or previous.kind not in allowed
                        or previous.provenance.sentence != entry.provenance.sentence):
                    return decline("an elided repayment needs a same-sentence account antecedent")
            payments.append(entry)
        previous = entry
    expected = {}
    for entry in entries:
        if entry.value is not None:
            expected.setdefault(entry.provenance.sentence, Counter()).update([entry.value])
    if audit_numeric_mentions((*ctx.premises, ctx.question), expected,
                              missing="missing", duplicate="duplicate"):
        return decline("every stated amount must belong to the liability equation")
    # Do not ignore an extra charge, a planned payment, or a condition after
    # the account begins. Leading nonfinancial context can establish a name;
    # numeric context is independently checked above. Inside the interval,
    # every nontrivial unit must have been read by a rule.
    for reading in ctx.premises:
        for unit in uncovered_units(reading):
            before_opening = (reading.sentence_index < opening.provenance.sentence or
                              reading.sentence_index == opening.provenance.sentence
                              and unit.span[0] < opening.position)
            if before_opening:
                word = unit.features.get("lemma", unit.features.get("fold", ""))
                if (unit.sense() not in {"modal", "negator", "complementizer", "conjunction"}
                        and not any(ctx.reg.word_in_category(word, cat) for cat in (
                            "liability_state", "liability_use_verb", "payment_verb", "repayment_verb",
                            "resource_budget_noun", "transaction_adjustment_noun"))):
                    continue
            return decline("the liability interval contains an unread event or condition")
    if uncovered_units(ctx.question, ctx.match.consumed):
        return decline("the liability question has an unread restriction")
    result = resource_residual([opening.value], [p.value for p in payments],
                               ctx.log, source="liability-after-repayments")
    if not isfinite(result) or result < 0:
        return decline("repayments cannot exceed the stated liability")
    ctx.log.consumed_account_entry_keys.update(e.key() for e in entries)
    target = SemanticNode("liability-remainder", (("entity", entity), ("measure", opening.measure)))
    proof = AnswerProof(target, (
        ProofStep("opening-liability", target, (opening, debt),
                  "A limit becomes debt only through explicit full use; a stated debt is already owed."),
        ProofStep("actual-repayments", target, tuple(payments),
                  "Subtract each source-local repayment once; dates and settlement terms remain evidence."),
        ProofStep("settlement-terms", target, tuple(terms),
                  "A requirement to pay is not an actual payment."),
    ))
    return Answer("number", result, f"{result:g} {opening.measure} still owed", proof=proof)
