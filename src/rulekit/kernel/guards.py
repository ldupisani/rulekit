"""Guards: decline-safety checks between the pipeline and a committed answer.

Guards read only DECLARED properties (consumed unit ids, the arithmetic log,
unit features) — never rule identities. Config (guards.yaml) can enable or
tune a guard but cannot reference rules; that entanglement class is banned.
"""

from __future__ import annotations

from collections import Counter
from dataclasses import dataclass, replace

from ..data.registry import Registry
from .answer import _ACCOUNTED_VALUE_KINDS, Answer
from .evaluate import ArithmeticLog
from .facts import FactStore
from .model import Reading

_NUMERIC_FACT_FIELDS = ("value", "factor", "offset", "fraction")
# Consumers that read every accounted value in the question by construction
# and log each as an operand — so value-accounting must not demand a separate
# fact for values the query itself consumes. A CONSUMER name is
# structure, never an English word (constitution rule 1). See the use site for
# the contract a member must satisfy.
#
# MEMBERSHIP IS A TRADE, NOT A CONVENIENCE: a member takes this guard's
# protection and therefore OWNS the accounting itself — ALL of it, meaning every
# kind in `_ACCOUNTED_VALUE_KINDS`, not just the counts. `list-statistic` and
# `vector` earn it by folding every count into their result. `physics` earns it
# differently — it binds counts by unit, so a value it cannot read is not an
# operand at all; it discharges the duty by DECLINING on any unread accounted
# value rather than committing a number that ignored one. The content-progress
# remainder consumer binds the question's one fraction and uses it in the
# logged final multiplication.
#
# The two cases that proved this, both invisible to every corpus gate: "travels
# 60 meters in 4 seconds and 3 MINUTES" committed 15 (an unread COUNT), and then
# "travels HALF of 60 meters in 4 seconds" still committed 15 (an unread
# FRACTION) after the first fix re-implemented only the count third. That is why
# the kind tuple is imported rather than re-listed: a contract with two copies
# has already drifted.
_WHOLE_LIST_CONSUMERS = (
    "content-progress-remainder-fraction",
    "list-statistic",
    "vector",
    "physics",
)
# A stricter subset that audits accounted values across PREMISES as well as the
# question. Membership is safe only while the consumer scans every reading and
# declines on any value its expression cannot use; `physics` owns that contract.
_WHOLE_DOCUMENT_CONSUMERS = ("physics",)
# Consumers whose query explicitly enumerates every period in answer scope.
# These consumers still undergo answer accounting, but same-holder facts from
# periods outside the list are intentionally out of scope rather than ignored.
# Membership is a contract: the consumer must require direct evidence for every
# listed period and account for every matching fact inside those periods.
_EXPLICIT_PERIOD_LIST_CONSUMERS = ("event-period-total",)


@dataclass
class GuardVeto:
    guard: str
    reason: str


def _enabled(reg: Registry, name: str) -> bool:
    cfg = reg.guard_config.get(name)
    return bool(cfg.get("enabled", True)) if cfg is not None else True


def _fact_values_by_sentence(store: FactStore) -> dict[int, "Counter[float]"]:
    """Numeric fields of admitted facts, keyed by originating sentence —
    a value is only accounted by facts its OWN sentence produced (a same
    number appearing in another sentence's fact must not mask an unread).

    A MULTISET (Counter), not a set: N stated mentions of the same value need
    N facts carrying it. "walked nine miles on Monday and nine more on Tuesday"
    states 'nine' twice but the elided second mention forms no fact, so the
    sentence supplies value 9 ONCE — the caller decrements per mention and vetoes
    the unmatched second, exactly as the distinct-value sibling ("...seven more...")
    already declines. Set membership masked this: a single 9 fact satisfied both.

    RATE, PRICE, GOAL, GROUP_TOTAL, DISCOUNT and PERCENT_CHANGE facts are
    excluded: a rate, price, goal, group total, discount, or percent-change
    that merely EXISTS has not been used — "makes $18 an hour" must not
    unlock a fold that ignores the wage, "$10 each" must not unlock one
    that ignores the price, "wants to collect 30 stamps" must not unlock
    one that ignores the goal, "there are 160 toys altogether" must not
    unlock one that ignores the stated total, "gets a 15% discount" must
    not unlock one that ignores the discount, and "puts 20% more money in"
    (mining candidate percent-change-values) must not unlock one that
    ignores the percent change. Their values count as read only when the
    arithmetic consumed them (the caller checks the log for rate/price/
    goal/group-total/discount/percent-change values)."""
    from .model import (
        Discount,
        Expenditure,
        ResourceAllocation,
        Goal,
        GroupTotal,
        MeasuredContentChange,
        PercentChange,
        Price,
        Rate,
    )

    out: dict[int, "Counter[float]"] = {}
    for fact in store.facts:
        if isinstance(
            fact,
            (
                Rate,
                Price,
                Goal,
                GroupTotal,
                Discount,
                PercentChange,
                MeasuredContentChange,
                Expenditure,
                ResourceAllocation,
            ),
        ):
            continue
        values = out.setdefault(fact.provenance.sentence, Counter())
        for field_name in _NUMERIC_FACT_FIELDS:
            v = getattr(fact, field_name, None)
            if isinstance(v, (int, float)):
                values[float(v)] += 1
    # Agreement preserves the provenance of repeated assertions, not a second
    # quantity. Only an exact surviving Quantity with that semantic key/value
    # can account for the duplicate statement; quarantined facts cannot.
    from .model import Quantity
    for agreement in store.agreement_ambiguities:
        survivor = next((fact for fact in store.by_kind(Quantity)
                         if fact.key() == agreement.key
                         and fact.value_part() == agreement.value
                         and fact.provenance == agreement.retained), None)
        if survivor is not None and survivor.entity_ref.resolved:
            out.setdefault(agreement.deduped.sentence, Counter())[float(survivor.value)] += 1
    return out


def check(
    premises: list[Reading],
    consumed_uids: dict[int, set[int]],  # sentence index -> consumed unit uids
    log: ArithmeticLog,
    reg: Registry,
    proposed: Answer,
    store: FactStore | None = None,
    question: Reading | None = None,
    clause_split: bool = False,
) -> GuardVeto | None:
    """Run all enabled guards against a proposed committed answer.
    Returns the first veto, or None. A decline is already safe, so only
    commitments are guarded — and each answer KIND gets its own guard set:

    - `number` answers get the numeric guards below (unknown-word,
      value-accounting, unresolved-derivation, ...), unchanged.
    - `verdict` answers get `_check_verdict` INSTEAD. Value-accounting is
      deliberately NOT applied to verdict premises: FOL entailment is
      MONOTONIC — a premise correctly read but unused can never invalidate a
      derived True/False — so "every stated number reached the output" is the
      wrong contract. What a verdict must prove instead is that no
      TRUTH-SCOPING operator (quantifier / conjunction / negator) in the
      premises went unread by a logic rule, because an operator the reading
      ignored is exactly how a disjunct or an antecedent gets asserted as a
      ground fact (the FOLIO if-antecedent leak, Phase 0a).
    """
    if not proposed.committed:
        return None
    if proposed.kind == "verdict":
        return _check_verdict(premises, consumed_uids, reg, clause_split)
    if proposed.kind == "witnesses":
        for reading in premises + ([question] if question is not None else []):
            if reading.unknown_words():
                return GuardVeto(
                    "witness-fragment",
                    f"cannot select witnesses while {reading.unknown_words()} "
                    f"are unknown (sentence {reading.sentence_index})",
                )
            unresolved = [
                (unit.surface, obligation.need)
                for unit in reading.units
                for obligation in unit.unmet()
            ]
            if unresolved:
                return GuardVeto(
                    "witness-fragment",
                    f"cannot select witnesses with unresolved structure "
                    f"{unresolved!r} (sentence {reading.sentence_index})",
                )
        return _check_verdict(premises, consumed_uids, reg, clause_split)
    readings = premises + ([question] if question is not None else [])
    return _check_number(
        readings, consumed_uids, log, reg, store, question, premises, proposed
    )


# senses that SCOPE truth. Sense NAMES are kernel structure (constitution rule
# 1 allows exactly this); the words carrying them live in the packs.
_TRUTH_SCOPING_SENSES = ("quantifier", "conjunction", "negator")


def _check_verdict(
    premises: list[Reading],
    consumed_uids: dict[int, set[int]],
    reg: Registry,
    clause_split: bool,
) -> GuardVeto | None:
    """The supported-fragment guard: a verdict may only commit when every
    truth-scoping operator in the premises was CONSUMED by a rule that
    understood it. Introduced deliberately WEAK — each new logic extraction
    rule consumes its own operator words, which widens the commit pool
    without touching this guard (capability relaxes it, never edits)."""
    if clause_split:
        # the textual clause pre-split promotes coordinated clauses to
        # stand-alone premises and the boundary word is no longer visible to
        # this guard — a promoted DISJUNCT would read as an asserted fact.
        # Coarse and safe: decline the whole story.
        return GuardVeto(
            "verdict-fragment",
            "premises were clause-split before reading; a promoted disjunct "
            "is indistinguishable from an asserted fact",
        )
    for reading in premises:
        consumed = consumed_uids.get(reading.sentence_index, set())
        for unit in reading.units:
            if unit.sense() not in _TRUTH_SCOPING_SENSES or unit.uid in consumed:
                continue
            obligations = unit.obligations()
            if (
                unit.sense() == "negator"
                and obligations
                and all(o.met for o in obligations)
            ):
                # a NEGATOR that bound what it scopes was read structurally
                # (the difg #26 negation-is-an-obligation contract — the same
                # binding that flips the fold's polarity). ONLY negators get
                # this exemption: a bound quantifier/conjunction has been
                # attached, not UNDERSTOOD — nothing propagates its scope into
                # a fact a verdict consumer reads, so it must still veto.
                continue
            return GuardVeto(
                "verdict-fragment",
                f"{unit.surface!r} (sentence {reading.sentence_index}) "
                f"scopes truth but no logic rule read it",
            )
    return None


def _check_number(
    readings: list[Reading],
    consumed_uids: dict[int, set[int]],
    log: ArithmeticLog,
    reg: Registry,
    store: FactStore | None,
    question: Reading | None,
    premises: list[Reading],
    proposed: Answer | None = None,
) -> GuardVeto | None:
    """Numeric guards, including explicit use of allocation endpoints."""

    if _enabled(reg, "answer-accounting") and store is not None:
        from .model import JOURNEY_KINDS

        if any(f.key() not in log.consumed_journey_keys
               for kind in JOURNEY_KINDS for f in store.by_kind(kind)):
            return GuardVeto("answer-accounting", "a stated journey or schedule was not used")

        from .model import InventoryScope, InventoryWithdrawal

        if any(f.key() not in log.consumed_inventory_keys
               for kind in (InventoryScope, InventoryWithdrawal) for f in store.by_kind(kind)):
            return GuardVeto("answer-accounting", "a stated inventory or withdrawal was not used")

        from .model import Expenditure

        if any(e.basis == "quote" and e.key() not in log.consumed_expenditure_keys
               for e in store.by_kind(Expenditure)):
            return GuardVeto("answer-accounting", "an itemized cost quote was not used")

        from .model import AllocationRatio

        if any(f.key() not in log.consumed_allocation_ratio_keys
               for f in store.by_kind(AllocationRatio)):
            return GuardVeto("answer-accounting", "a stated allocation ratio was not used")

        from .model import CommercialTerm

        if any(f.key() not in log.consumed_commercial_term_keys
               for f in store.by_kind(CommercialTerm)):
            return GuardVeto("answer-accounting", "a stated production cost or sale quote was not used")

        from .model import EARNINGS_ACCOUNT_KINDS

        if any(f.key() not in log.consumed_earnings_account_keys
               for kind in EARNINGS_ACCOUNT_KINDS for f in store.by_kind(kind)):
            return GuardVeto("answer-accounting", "a stated earnings account was not used")

        from .model import ORDERED_SEQUENCE_KINDS

        if any(f.key() not in log.consumed_sequence_keys
               for kind in ORDERED_SEQUENCE_KINDS
               for f in store.by_kind(kind)):
            return GuardVeto("answer-accounting", "a stated ordered sequence was not used")

        from .repeated_rates import RATE_STRUCTURE_KINDS

        if any(f.key() not in log.consumed_rate_structure_keys
               for kind in RATE_STRUCTURE_KINDS
               for f in store.by_kind(kind)):
            return GuardVeto("answer-accounting", "a stated rate policy or repeated schedule was not used")

        from .model import AllocationGroup, IndexedPathEvidence, MeasuredComponent, SpecificationEvidence, PopulationEvidence
        if any(f.key() not in log.consumed_component_keys
               for kind in (AllocationGroup, IndexedPathEvidence, MeasuredComponent, SpecificationEvidence, PopulationEvidence)
               for f in store.by_kind(kind)):
            return GuardVeto("answer-accounting", "a scoped component was not used")

        from .model import ProportionalBaseEvidence
        if any(f.key() not in log.consumed_proportional_base_keys
               for f in store.by_kind(ProportionalBaseEvidence)):
            return GuardVeto("answer-accounting", "a stated proportional base was not used")

        from .model import MixtureEvidence

        if any(row.key() not in log.consumed_mixture_keys
               for row in store.by_kind(MixtureEvidence)):
            return GuardVeto("answer-accounting", "a stated mixture amount or share was not used")

        from .model import ResourceAllocation, ResourceBalance, AccountEntry, BatchEvidence

        if any(b.key() not in log.consumed_batch_keys for b in store.by_kind(BatchEvidence)):
            return GuardVeto("answer-accounting", "a stated batch outcome was not used")

        if any(b.key() not in log.consumed_account_entry_keys
               for b in store.by_kind(AccountEntry)):
            return GuardVeto("answer-accounting", "a liability entry was not used as account evidence")

        if any(b.key() not in log.consumed_resource_balance_keys
               for b in (*store.by_kind(ResourceBalance), *store.by_kind(ResourceAllocation))):
            return GuardVeto("answer-accounting", "a stated budget balance was not used as allocation evidence")

    if _enabled(reg, "answer-accounting") and store is not None:
        from .model import PurchaseTotal

        if any(total.key() not in log.consumed_purchase_total_keys
               for total in store.by_kind(PurchaseTotal)):
            return GuardVeto("answer-accounting", "a stated purchase total was not used")

    if _enabled(reg, "unknown-word"):
        for reading in readings:
            unknown = reading.unknown_words()
            if unknown:
                return GuardVeto(
                    "unknown-word",
                    f"cannot commit while {unknown} are unknown (sentence "
                    f"{reading.sentence_index})",
                )

    if _enabled(reg, "value-accounting"):
        # EVERY stated value — count, multiplier, fraction, percent, in a
        # premise OR the question — must reach the reading's OUTPUT: a rule
        # consumed it, a fact from its OWN sentence carries it, or the
        # arithmetic used it. A committed answer that silently ignored
        # "half as many", "twice", "40% more" or the question's "in 10
        # years" is exactly the confident-wrong this guard exists to stop.
        fact_values = _fact_values_by_sentence(store) if store is not None else {}
        from .model import Expenditure

        from .pricing import expenditure_mentions
        used_cost_mentions = {
            (e.provenance.sentence, position): value
            for e in store.by_kind(Expenditure)
            if e.key() in log.consumed_expenditure_keys
            for position, value in expenditure_mentions(e).items()
        } if store is not None else {}
        from .model import (
            Discount,
            Goal,
            GroupTotal,
            MeasuredContentChange,
            PercentChange,
            Price,
            Rate,
        )

        # values from USE-GATED fact kinds (Rate, Price, Goal, GroupTotal,
        # Discount, PercentChange): existence alone doesn't count as read,
        # but the arithmetic log having consumed the value does. A COMPOUND
        # Rate ("8 pages in 20 minutes") additionally offers its own raw
        # numerator/denominator here — the text stated TWO numbers, not the
        # derived quotient `value`, so a consumer that actually divides/
        # multiplies by those two raw numbers (rather than by the bare
        # `value`) is what counts as reading them; simple (non-compound)
        # Rates leave both None and contribute nothing new here.
        rate_values = (
            {float(r.value) for r in store.by_kind(Rate)}
            | {float(r.numerator) for r in store.by_kind(Rate) if r.numerator is not None}
            | {float(r.denominator) for r in store.by_kind(Rate) if r.denominator is not None}
            | {float(p.value) for p in store.by_kind(Price)}
            | {float(g.value) for g in store.by_kind(Goal)}
            | {float(t.value) for t in store.by_kind(GroupTotal)}
            | {float(d.value) for d in store.by_kind(Discount)}
            | {float(pc.value) for pc in store.by_kind(PercentChange)}
            | {float(change.value) for change in store.by_kind(MeasuredContentChange)}
            if store is not None else set()
        )
        # A consumer that reads the WHOLE question number list by construction
        # (list-statistic: "the average of 4, 8, 15, 16, and 42"; vector: "the dot
        # product of (1, 2, 3) and (4, 5, 6)") accounts for every value in the
        # question — but only the FIRST binds an ask slot, so the per-count fact
        # check below would wrongly veto the rest. The progress-remainder
        # consumer likewise reads the question's sole fraction directly and
        # logs it in its expression. Exempt the question reading for those
        # consumers (the ask is re-derived, as answer-accounting does).
        # Every arithmetic ask still checks its question.
        #
        # Membership is the CONSUMER's contract, not a convenience: a consumer
        # belongs here only if it reads every count in the question and logs them
        # all as operands. Every listed consumer calls `evaluate` over them.
        # Adding one that does NOT would silently disable the guard for its asks.
        exempt_question = None
        exempt_document = False
        if question is not None:
            from .patterns import match_ask
            qm = match_ask(question, reg, store=store)
            if qm is not None:
                matched_consumer = qm[1].get("consumer")
                if matched_consumer in _WHOLE_LIST_CONSUMERS:
                    exempt_question = question
                if matched_consumer in _WHOLE_DOCUMENT_CONSUMERS:
                    # Mirror physics' formula-key normalization: a bare
                    # "{q.qualifier} {q}" render has one leading space, while
                    # a qualified key keeps its modifier. The consumer and its
                    # document-accounting exemption must select the SAME row.
                    quantity = qm[1].get("quantity", "").strip()
                    exempt_document = (
                        reg.quantity_formula_scopes.get(quantity) == "document"
                    )
        for reading in readings:
            if exempt_document or reading is exempt_question:
                continue
            used = consumed_uids.get(reading.sentence_index, set())
            # a MUTABLE per-reading copy: each stated mention CLAIMS one fact of
            # its value, so a sentence supplying value V once cannot account for
            # two mentions of V (the same-value blind spot the Counter closes).
            own_values = Counter(fact_values.get(reading.sentence_index, ()))
            for unit in reading.units:
                kind = unit.features.get("value_kind")
                # SINGLE DEFINITION, shared with answer.py: a consumer that takes
                # the _WHOLE_LIST_CONSUMERS exemption below inherits exactly this
                # duty, and re-listing the kinds there let one copy drift (the
                # `physics` consumer discharged only the `count` third).
                if kind not in _ACCOUNTED_VALUE_KINDS:
                    continue
                value = float(unit.features["value"])
                # NO global arithmetic-log fallback here: the fold's own sum
                # would mask a same-number unread from another sentence.
                # Facts-from-own-sentence and explicit consumption are the
                # only honest evidence. Independently-accounted mentions (a
                # consumed uid, a pattern-consumed unit) never claim a fact slot.
                if unit.uid in used or unit.features.get("pattern_consumed"):
                    continue
                if used_cost_mentions.get((reading.sentence_index, unit.uid)) == value:
                    continue
                if own_values.get(value, 0) > 0:
                    own_values[value] -= 1
                    continue
                if value in rate_values and log.uses_value(value):
                    continue
                where = (
                    "the question"
                    if question is not None and reading is question
                    else f"sentence {reading.sentence_index}"
                )
                return GuardVeto(
                    "value-accounting",
                    f"stated {kind} {unit.surface!r} ({where}) reached no "
                    "fact and no arithmetic — declining rather than risk a "
                    "wrong commit",
                )

    if _enabled(reg, "answer-accounting") and store is not None and question is not None:
        # ANSWER ACCOUNTING — the FACTS -> ANSWER half of value accounting.
        #
        # `value-accounting` above checks NUMBERS -> FACTS: every stated value must
        # reach a fact. It does NOT check that the ANSWER then USED those facts. A
        # fact can be extracted perfectly and silently ignored by the consumer, and
        # nothing objects. On GSM8K the ask shapes happen to consume everything, so
        # the hole is invisible; on ASDiv (same task, different authors) it produced
        # 9 confident wrongs out of 46 commits — 80.4% precision against GSM8K's
        # 100%. See docs/negative-results.md, "THE 100% PRECISION IS AN ARTIFACT".
        #
        #   "Gino has 15 brown bears, 24 white bears, and 27 black bears."   gold 66
        #     facts: bear[brown]=15  bear[white]=24  bear=27
        #     answer: 27          <- the bare key shadowed its qualified siblings
        #
        #   "Maria took sixteen fish out. Now there are three fish."         gold 19
        #     facts: maria/fish=16  tank/fish=3
        #     answer: 3           <- the other fish fact was never consumed
        #
        # THE RULE: if the ANSWERING HOLDER owns another fact of the SAME BASE MEASURE
        # that the arithmetic never used, the reading is PARTIAL. A partial reading
        # DECLINES rather than commit a subset (rule 4: a confident-wrong is worse
        # than a decline). This can only ever turn a COMMIT into a DECLINE.
        #
        # SCOPED TO THE ANSWERING HOLDER — not merely to the measure. A first cut
        # scoped only by measure and BROKE 4 correct GSM8K items:
        #
        #   "Tapanga and Corey have 66 candies. Tapanga has 8 more than Corey.
        #    How many candies does COREY have?"     corey=29 (used)  tapanga=37 (unused)
        #
        # Tapanga's 37 is a DIFFERENT HOLDER. A question about Corey correctly ignores
        # it — that is not a partial reading, and vetoing it is a coverage loss for
        # nothing. The sibling that matters is the one the SAME holder owns:
        # `gino/bear[brown]` beside `gino/bear`.
        #
        # GroupTotal (holder-less, synth-derived) is DELIBERATELY NOT CHECKED. The
        # other 3 of those 4 breaks were unused GroupTotals carrying GARBAGE values
        # (60x60=3600 toys, 8x8=64 dolls, 50x50=2500 dolls) — a real synth bug this
        # guard surfaced, logged in docs/negative-results.md. Vetoing on a fact the
        # engine should never have emitted would punish the reading for a defect
        # elsewhere; fix the synth, do not launder it into a decline here.
        #
        # The ask is re-derived rather than threaded through `answer()`: match_ask is
        # deterministic, so it yields exactly the ask `answer()` used, and this runs
        # only for already-committed answers (~103 of 3,772 on dev-train).
        from . import deixis
        from .answer import _question_reference_time
        from .model import Quantity
        from .patterns import match_ask

        matched = match_ask(question, reg, store=store)
        if matched is not None:
            _ask, query, _m = matched
            from .measures import _resolve_measure_against
            expense_measure = _resolve_measure_against(
                query.get("measure", ""), {e.measure for e in store.by_kind(Expenditure)}, reg)
            if (reg.word_in_category(query.get("verb", ""), "possession_state")
                    and any(e.value is not None and e.entity == query.get("entity")
                            and e.measure == expense_measure
                            and e.key() not in log.consumed_expenditure_keys
                            and not any(
                                q.entity == e.entity and q.measure == e.measure
                                and q.value == e.value and q.verb == e.verb
                                and q.occurrence == e.event
                                and q.provenance.sentence == e.provenance.sentence
                                for q in store.by_kind(Quantity) if not q.is_state)
                            for e in store.by_kind(Expenditure))):
                # An expense may also be represented by an ordinary monetary
                # event. The existing quantity-accounting check below audits
                # that event; a price alone must never disappear from a balance.
                return GuardVeto("answer-accounting", "a stated expense affecting this balance was not used")
            accounting_store = store
            if query.get("evidence_entity_reference") is not None:
                from .reference_identity import scope_query_store
                accounting_store = scope_query_store(store, query)
                if accounting_store is None:
                    return GuardVeto("answer-accounting", "participant identity is ambiguous")
            explicit_periods = None
            if query.get("consumer") in _EXPLICIT_PERIOD_LIST_CONSUMERS:
                raw_periods = query.get("periods")
                if isinstance(raw_periods, list) and all(
                    isinstance(period, str) and period for period in raw_periods
                ):
                    explicit_periods = set(raw_periods)
            reference_time = None
            time_candidates = _question_reference_time(question, reg, _m)
            if time_candidates:
                origo = deixis.resolve(
                    time_candidates,
                    deixis.Origo(sentence=question.sentence_index),
                    deixis.constant,
                    dimension=deixis.TIME,
                )
                if origo is not None:
                    reference_time = origo.key
            asked = query.get("measure")
            holder = query.get("entity")
            holder_owner = query.get("entity_owner")
            require_holder_owner = (
                query.get("require_entity_owner_evidence") == "true"
            )
            qualifier = query.get("measure_qualifier")
            from .model import CollectionAttribute
            descriptions = [f for f in store.by_kind(CollectionAttribute)
                            if f.collection == asked and not qualifier]
            if not qualifier:
                for reading in premises:
                    if not any(u.features.get("lemma") == asked for u in reading.units):
                        continue
                    retained = {f.qualifier for f in descriptions
                                if f.provenance.sentence == reading.sentence_index}
                    for unit in reading.units:
                        named = unit.features.get("nominal_description_qualifiers", ())
                        if not set(named) <= retained:
                            return GuardVeto("answer-accounting", "a nominal description list was not completely retained")
            if descriptions:
                # Nominal descriptions name existing subsets, not counts or
                # an exhaustive partition. A whole-item answer must not drop
                # a described but uncounted subset or mix different facets.
                # Unscoped multi-holder descriptions need a separate binding
                # contract before they can participate in combined answers.
                if not holder or len({f.attribute for f in descriptions}) != 1:
                    return GuardVeto("answer-accounting", "collection descriptions have no single compatible scope")
                quantities = [q for q in accounting_store.by_kind(Quantity)
                              if q.entity == holder and q.measure.split("[", 1)[0] == asked
                              and q.verb == query.get("verb")
                              and (reference_time is None or q.time in (None, reference_time))]
                known = {q.measure_qualifier for q in quantities if q.value > 0}
                if not {f.qualifier for f in descriptions} <= known:
                    return GuardVeto("answer-accounting", "a described collection subset has no compatible positive count")
            # ONLY a BARE (unqualified) ask can be partially read.
            #
            # "How many cups of FLOUR are in the kitchen?" — the kitchen also holds
            # cup[sugar]=9, and it is CORRECT to ignore it: the question asked for a
            # PART, and the other parts are out of scope, not dropped. A first cut
            # missed this and broke four guard tests (increments 70, 103, 108) that
            # exist precisely to pin qualified-key resolution.
            #
            # The partial reading is the OPPOSITE shape: the question asks for the
            # WHOLE ("how many bears does Gino have?") while the holder's qualified
            # PARTS (bear[brown], bear[white]) sit unconsumed. Asking for the whole
            # and answering with one part is the confident-wrong; asking for a part
            # and ignoring the others is just reading the question.
            if qualifier:
                asked = None
            if asked and holder:
                base = lambda m: str(m).split("[")[0]
                target = base(asked)
                if target != str(asked):
                    # the ask itself resolved to a qualified key — a PART, as above
                    target = None
            if asked and holder and target:
                answer_value = (
                    float(proposed.value)
                    if isinstance(proposed.value, (int, float))
                    else None
                )
                asked_verb = query.get("verb")
                unused: list[str] = []
                for fact in accounting_store.by_kind(Quantity):
                    # An explicit period-list consumer asks for a bounded event
                    # set (for example, March AND April). Facts from June are
                    # not ignored operands; they are outside the question. The
                    # consumer owns all evidence inside the requested periods,
                    # so those facts remain subject to the checks below.
                    if (
                        explicit_periods is not None
                        and fact.time not in explicit_periods
                    ):
                        continue
                    # The consumer already ran below the shared temporal
                    # origo. Answer accounting must inspect that same evidence
                    # scope rather than vetoing a correct period-specific
                    # answer because another period was intentionally filtered.
                    if (
                        reference_time is not None
                        and fact.time not in (None, reference_time)
                    ):
                        continue
                    if fact.entity != holder:
                        continue
                    if holder_owner and (
                        fact.owner != holder_owner
                        and (fact.owner is not None or require_holder_owner)
                    ):
                        continue
                    if base(fact.measure) != target:
                        continue
                    # SCOPED TO THE ASKED EVENT as well as the holder and measure.
                    #
                    # "Tom bought 6 eggs. Tom ate 2 eggs. How many eggs did Tom EAT?"
                    # The bought 6 is not an ignored fact — it belongs to a DIFFERENT
                    # EVENT. Demanding the answer account for it declines a correct
                    # item (it broke exactly this curated suite case). A fact is only
                    # "ignored" if the question was actually about it: same holder,
                    # same measure, SAME VERB. A verb-less (state) fact is in scope
                    # for any ask, since a holding is what every ask ultimately reads.
                    fact_verb = getattr(fact, "verb", None)
                    if fact_verb is not None and asked_verb and fact_verb != asked_verb:
                        continue
                    value = float(fact.value)
                    if answer_value is not None and abs(value - answer_value) < 1e-9:
                        continue  # the answer itself is trivially used
                    if log.uses_value(value):
                        continue
                    unused.append(f"{fact.measure!r}={value:g}")
                if unused:
                    return GuardVeto(
                        "answer-accounting",
                        f"{holder!r} also holds {', '.join(sorted(unused))} of the asked "
                        f"measure {target!r}, and no arithmetic consumed them — a PARTIAL "
                        "reading declines rather than commit a subset",
                    )

    if _enabled(reg, "contradicted-relation") and store is not None:
        # Saturation avoids deriving a duplicate when both sides are known.
        # Validate that restatement rather than silently ignoring its equation.
        # State snapshots and activity totals have different evidence contracts;
        # both require exact participant identity and compatible time scope.
        from .model import Quantity as _Q
        from .model import Relation as _Rel

        from .reference_identity import scope_reference_store
        from .temporal import normalize_perspective
        from .totals import _entity_total, _relation_item_evidence, _resolve_relation, _verb_total
        for rel in store.by_kind(_Rel):
            if (rel.measure == rel.standard and rel.measure_qualifier
                    and rel.standard_qualifier):
                from .totals import _subtype_quantity
                private_log = replace(log, entries=[], journal=None)
                subj = _subtype_quantity(store, reg, rel, rel.measure, rel.measure_qualifier, private_log)
                std = _subtype_quantity(store, reg, rel, rel.standard, rel.standard_qualifier, private_log)
                if subj is None or std is None:
                    return GuardVeto("contradicted-relation", "the item-class comparison has no complete compatible amounts")
                if abs(subj.value - (rel.factor * std.value + rel.offset)) > 1e-6:
                    return GuardVeto("contradicted-relation", "the item-class amounts contradict their stated comparison")
                continue
            if not any(reg.word_in_category(rel.verb, category)
                       for category in ("state", "non_event_verb")):
                # A comparison restates the COMPLETE activity amounts, not
                # each independently asserted occurrence. Saturation avoids
                # deriving a duplicate event when both amounts already exist;
                # that suppression is not proof that the equation agrees.
                sides = []
                for reference in (rel.subject_ref, rel.standard_ref):
                    scoped = scope_reference_store(store, reference)
                    quantities = [] if scoped is None else [
                        q for q in scoped.by_kind(_Q)
                        if q.entity == reference.head and q.verb == rel.verb
                    ]
                    sides.append((scoped, quantities))
                if not all(quantities for _, quantities in sides):
                    continue  # not two known activity totals
                if rel.measure is None:
                    recovered = _resolve_relation(store, rel, replace(log, entries=[], journal=None))
                    if recovered is None:
                        return GuardVeto(
                            "contradicted-relation",
                            "the activity comparison has no unique compatible standard measure",
                        )
                    rel = recovered
                sides = [(scoped, [q for q in quantities if q.measure.split("[", 1)[0] == rel.measure])
                         for scoped, quantities in sides]
                if not all(quantities for _, quantities in sides):
                    continue
                totals = []
                perspective = normalize_perspective(rel.provenance.temporal_perspective, reg)
                for reference in (rel.subject_ref, rel.standard_ref):
                    projection = _relation_item_evidence(
                        store, rel, reference, rel.measure, reg, replace(log, entries=[], journal=None))
                    if projection is None:
                        totals.append(None)
                        continue
                    scoped, quantities, measure = projection
                    # Relation has no event-period field. Do not equate a
                    # dated subtotal or an offset with an unscoped total, or
                    # silently select one qualifier/tense among several.
                    if ((rel.subject_offset or 0) or (rel.standard_offset or 0)
                            or any(q.time is not None
                                   or normalize_perspective(q.provenance.temporal_perspective, reg)
                                      != perspective for q in quantities)):
                        totals.append(None)
                        continue
                    # Preserve the total fold's unknown-event and cross-verb
                    # temporal checks. A private log validates evidence without
                    # marking unrelated operands as used by the answer.
                    totals.append(_verb_total(
                        scoped, reference.head, measure, rel.verb, replace(log, entries=[])
                    ))
                subj, std = totals
                if subj is None or std is None:
                    return GuardVeto(
                        "contradicted-relation",
                        "the activity comparison has no complete, compatible totals "
                        "at one time; its stated amounts cannot validate the relation",
                    )
                if abs(subj - (rel.factor * std + rel.offset)) > 1e-6:
                    return GuardVeto(
                        "contradicted-relation",
                        f"the complete {rel.verb!r} total of {rel.subject!r} ({subj}) "
                        f"contradicts the relation to {rel.standard!r} ({std}): "
                        f"{rel.factor}x + {rel.offset}",
                    )
                continue
            if (rel.subject_offset or 0) or (rel.standard_offset or 0):
                continue  # asserted at ANOTHER time — not a contradiction at t=0
            # State equations validate snapshots, not current balances after
            # later events. They share item/identity resolution with anchors,
            # but deliberately do not borrow the activity accumulation fold.
            sides = []
            for reference in (rel.subject_ref, rel.standard_ref):
                scoped = scope_reference_store(store, reference)
                sides.append([] if scoped is None else [q for q in scoped.by_kind(_Q)
                             if q.entity == reference.head and q.is_state and q.time is None])
            if not all(sides):
                continue
            recovered = _resolve_relation(store, rel, replace(log, entries=[], journal=None))
            if recovered is None:
                return GuardVeto("contradicted-relation", "the state comparison has no unique standard measure")
            rel = recovered
            measure = rel.measure
            if not all(any(q.measure.split("[", 1)[0] == measure for q in side) for side in sides):
                continue
            totals = []
            for reference in (rel.subject_ref, rel.standard_ref):
                projection = _relation_item_evidence(
                    store, rel, reference, measure, reg, replace(log, entries=[], journal=None))
                if projection is None:
                    totals.append(None)
                    continue
                scoped, quantities, resolved_measure = projection
                snapshots = [q for q in quantities if q.is_state and q.time is None]
                evidence = FactStore(facts=snapshots, references=scoped.references)
                totals.append(_entity_total(evidence, reg, reference.head, resolved_measure,
                                            replace(log, entries=[], journal=None)))
            subj, std = totals
            if subj is None or std is None:
                return GuardVeto("contradicted-relation", "the state comparison has no compatible item snapshots")
            if abs(subj - (rel.factor * std + rel.offset)) > 1e-6:
                return GuardVeto(
                    "contradicted-relation",
                    f"the stated {rel.measure!r} of {rel.subject!r} ({subj}) "
                    f"contradicts the relation to {rel.standard!r} ({std}): "
                    f"{rel.factor}x + {rel.offset} — the document is "
                    "over-determined and does not add up at one time",
                )

    if _enabled(reg, "unresolved-derivation") and store is not None:
        # a FractionQuantity/RestQuantity the synthesizers could NOT resolve
        # means part of the text was read but not computed — committing
        # around it is how "ate half the sandwiches" silently vanishes
        from .model import (
            AnchorQuantity,
            Atom,
            CollectionContext,
            FractionQuantity,
            Membership,
            PartitionAggregateShare,
            PartitionQuantity,
            Quantity,
            QuantifiedAdjustment,
            RestQuantity,
            SequentialPartition,
            SequentialPartitionInitialShare,
            SequentialPartitionPrefix,
            SequentialPartitionRemainingShare,
            SequentialPartitionRemainder,
        )

        derived = {
            (q.entity, q.verb, q.occurrence)
            for q in store.by_kind(Quantity)
            if q.provenance.source.startswith("synth/")
        }
        for f in store.by_kind(FractionQuantity):
            if (f.entity, f.verb, f.occurrence) not in derived and f.key() not in log.consumed_fraction_keys:
                return GuardVeto(
                    "unresolved-derivation",
                    f"the fraction of {f.measure!r} ({f.entity!r}, {f.verb!r}) "
                    "never resolved against a unique pool",
                )
        for r in store.by_kind(RestQuantity):
            if (r.entity, r.verb, r.occurrence) not in derived:
                return GuardVeto(
                    "unresolved-derivation",
                    f"'the rest' ({r.entity!r}, {r.verb!r}) never resolved "
                    "against a unique pool",
                )
        # AnchorQuantity (mining candidate elided-measure-anchors): a bare
        # numeral with no measure noun at all ("who caught 2") that
        # `_anchor_quantity_synth` could NOT resolve against a unique
        # in-play measure — the SAME `derived` set already covers it
        # (populated from EVERY synth-sourced Quantity regardless of
        # source name, "synth/anchor-quantity" included), so an unresolved
        # anchor is caught here rather than silently laundered through as
        # a valueless Predication ever was.
        for a in store.by_kind(AnchorQuantity):
            if (a.entity, a.verb, a.occurrence) not in derived:
                return GuardVeto(
                    "unresolved-derivation",
                    f"the bare count {a.value!r} stated for {a.entity!r} "
                    f"({a.verb!r}) never resolved to a known measure",
                )
        # A class-wide additive adjustment is active only for an exact
        # positive member of that class. Once active, it must have produced
        # the one adjusted state Quantity; otherwise a missing/ambiguous
        # baseline must not be hidden by an unrelated quantity that happened
        # to answer the same ask.
        exact_memberships = {
            (fact.member, fact.collection)
            for fact in store.by_kind(Membership)
            if fact.polarity
        } | {
            (fact.entity, fact.pred)
            for fact in store.by_kind(Atom)
            if fact.polarity
        }
        adjusted = {
            (fact.entity, fact.measure, fact.verb)
            for fact in store.by_kind(Quantity)
            if fact.provenance.source.startswith(
                "synth/quantified-adjustment-materialization"
            )
        }
        adjusted.update(
            (ambiguity.key[1], ambiguity.key[2], ambiguity.key[3])
            for ambiguity in store.agreement_ambiguities
            if ambiguity.key[:1] == ("quantity",)
            and (
                ambiguity.retained.source.startswith(
                    "synth/quantified-adjustment-materialization"
                )
                or ambiguity.deduped.source.startswith(
                    "synth/quantified-adjustment-materialization"
                )
            )
        )
        for adjustment in store.by_kind(QuantifiedAdjustment):
            for entity, cls in sorted(exact_memberships):
                if cls != adjustment.cls:
                    continue
                if (
                    entity,
                    adjustment.measure,
                    adjustment.verb,
                ) not in adjusted:
                    return GuardVeto(
                        "unresolved-derivation",
                        f"the {adjustment.offset:+g} adjustment to "
                        f"{adjustment.measure!r} for class "
                        f"{adjustment.cls!r} never resolved against one "
                        "compatible class-wide baseline",
                    )
        # a PartitionQuantity resolves into ANOTHER PartitionQuantity (its
        # collection replaced by the real measure), never a Quantity — the
        # 'derived' set above doesn't cover it, so check separately. A
        # CARDINAL partition's value never changes across resolution, so it
        # matches on (attribute, value, verb, sentence) exactly as before.
        # A FRACTIONAL partition's value legitimately changes (the raw
        # fraction becomes a real count once sized against the collection's
        # total) — it matches on shape alone (attribute, verb, sentence);
        # dropping value from that key is strictly weaker and only ever
        # consulted for is_fraction=True facts, so cardinal matching is
        # untouched. A REST partition's value legitimately changes too (the
        # 0 placeholder becomes the collection-total-minus-siblings count —
        # mining candidate rest-partitions), so it shares the same
        # shape-only path as is_fraction. A partition also counts as
        # resolved when its
        # `collection` ALREADY names a known measure directly (the
        # definite-NP surface, "6 of the marbles are red" — the noun IS the
        # measure, nothing to resolve) — a declared fact-store property,
        # never a rule-identity check, so it applies uniformly to whichever
        # rule produced the fact.
        known_measures = {
            q.measure.split("[", 1)[0] for q in store.by_kind(Quantity)
        } | {
            context.collection
            for context in store.by_kind(CollectionContext)
        }
        resolved_by_value = {
            (p.attribute, p.value, p.verb, p.provenance.sentence)
            for p in store.by_kind(PartitionQuantity)
            if p.provenance.source == "synth/partition"
        }
        resolved_by_shape = {
            (p.attribute, p.verb, p.provenance.sentence)
            for p in store.by_kind(PartitionQuantity)
            if p.provenance.source == "synth/partition"
        }
        for p in store.by_kind(PartitionQuantity):
            if p.provenance.source == "synth/partition" or p.collection in known_measures:
                continue
            if p.is_fraction or p.is_rest:
                resolved = (p.attribute, p.verb, p.provenance.sentence) in resolved_by_shape
            else:
                resolved = (
                    p.attribute, p.value, p.verb, p.provenance.sentence
                ) in resolved_by_value
            if not resolved:
                what = "the rest" if p.is_rest else f"{p.value} of them"
                return GuardVeto(
                    "unresolved-derivation",
                    f"'{what} are {p.attribute}' never resolved "
                    "against a unique prior collection",
                )
        resolved_aggregate_shares = {
            (partition.provenance.sentence, partition.attribute)
            for partition in store.by_kind(PartitionQuantity)
            if partition.provenance.source
            == "synth/partition-aggregate-share"
        }
        for share in store.by_kind(PartitionAggregateShare):
            if (
                share.provenance.sentence,
                share.attribute,
            ) not in resolved_aggregate_shares:
                return GuardVeto(
                    "unresolved-derivation",
                    f"the {share.fraction:g} share for "
                    f"{share.attribute!r} never resolved against the two "
                    "named prior partitions",
                )
        sequential_resolutions = {
            (p.provenance.sentence, p.attribute, p.verb)
            for p in store.by_kind(PartitionQuantity)
            if p.provenance.source == "synth/sequential-partition"
        }
        for allocation in store.by_kind(SequentialPartition):
            expected = {
                (
                    allocation.provenance.sentence,
                    attribute,
                    allocation.verb,
                )
                for attribute in (
                    allocation.first_attribute,
                    allocation.second_attribute,
                    allocation.rest_attribute,
                )
            }
            if not expected <= sequential_resolutions:
                return GuardVeto(
                    "unresolved-derivation",
                    "the staged partition never resolved against exactly "
                    "one prior collection",
                )
        joined_allocations = [
            allocation
            for allocation in store.by_kind(SequentialPartition)
            if allocation.provenance.source
            == "synth/sequential-partition-join"
        ]
        complement_resolutions = {
            (partition.provenance.sentence, partition.attribute, partition.verb)
            for partition in store.by_kind(PartitionQuantity)
            if partition.provenance.source
            == "synth/sequential-partition-complement"
        }
        for prefix in store.by_kind(SequentialPartitionPrefix):
            if not any(
                allocation.provenance.sentence
                == prefix.provenance.sentence + 1
                and allocation.first_attribute == prefix.first_attribute
                and allocation.second_attribute == prefix.second_attribute
                and allocation.verb == prefix.verb
                for allocation in joined_allocations
            ):
                return GuardVeto(
                    "unresolved-derivation",
                    "the staged partition prefix was not completed by one "
                    "compatible immediately following rest clause",
                )
        for remainder in store.by_kind(SequentialPartitionRemainder):
            completed_staged_partition = any(
                allocation.provenance.sentence
                == remainder.provenance.sentence
                and allocation.rest_attribute == remainder.rest_attribute
                and allocation.verb == remainder.verb
                for allocation in joined_allocations
            )
            completed_complement = (
                remainder.provenance.sentence,
                remainder.rest_attribute,
                remainder.verb,
            ) in complement_resolutions
            if not (completed_staged_partition or completed_complement):
                return GuardVeto(
                    "unresolved-derivation",
                    "the rest clause did not complete one compatible staged "
                    "partition in the immediately preceding sentence",
                )
        joined_prefixes = [
            prefix
            for prefix in store.by_kind(SequentialPartitionPrefix)
            if prefix.provenance.source
            == "synth/sequential-partition-prefix-join"
        ]
        for initial in store.by_kind(SequentialPartitionInitialShare):
            continued_by_remaining_share = any(
                prefix.provenance.sentence
                == initial.provenance.sentence + 1
                and prefix.first_attribute == initial.first_attribute
                and prefix.verb == initial.verb
                for prefix in joined_prefixes
            )
            completed_complement = (
                initial.provenance.sentence + 1,
                initial.first_attribute,
                initial.verb,
            ) in complement_resolutions
            if not (continued_by_remaining_share or completed_complement):
                return GuardVeto(
                    "unresolved-derivation",
                    "the initial partition share was not completed by one "
                    "compatible adjacent remainder-share or rest clause",
                )
        for remaining in store.by_kind(SequentialPartitionRemainingShare):
            if not any(
                prefix.provenance.sentence
                == remaining.provenance.sentence
                and prefix.second_attribute == remaining.second_attribute
                and prefix.verb == remaining.verb
                for prefix in joined_prefixes
            ):
                return GuardVeto(
                    "unresolved-derivation",
                    "the remaining-pool share did not follow one compatible "
                    "initial partition share",
                )

    if _enabled(reg, "ambiguity"):
        for reading in readings:
            for unit in reading.units:
                if unit.features.get("ambiguous"):
                    return GuardVeto(
                        "ambiguity",
                        f"{unit.surface!r} stayed ambiguous (sentence "
                        f"{reading.sentence_index})",
                    )
    return None
