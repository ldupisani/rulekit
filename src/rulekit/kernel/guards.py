"""Guards: decline-safety checks between the pipeline and a committed answer.

Guards read only DECLARED properties (consumed unit ids, the arithmetic log,
unit features) — never rule identities. Config (guards.yaml) can enable or
tune a guard but cannot reference rules; that entanglement class is banned.
"""

from __future__ import annotations

from collections import Counter
from dataclasses import dataclass

from ..data.registry import Registry
from .answer import Answer
from .evaluate import ArithmeticLog
from .facts import FactStore
from .model import Reading

_NUMERIC_FACT_FIELDS = ("value", "factor", "offset", "fraction")
# Consumers that read the WHOLE question number list by construction and log
# every count as an operand — so value-accounting must not demand that each
# count bind its own ask slot (only the first does). A CONSUMER name is
# structure, never an English word (constitution rule 1). See the use site for
# the contract a member must satisfy.
_WHOLE_LIST_CONSUMERS = ("list-statistic", "vector")


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
    from .model import Discount, Goal, GroupTotal, PercentChange, Price, Rate

    out: dict[int, "Counter[float]"] = {}
    for fact in store.facts:
        if isinstance(fact, (Rate, Price, Goal, GroupTotal, Discount, PercentChange)):
            continue
        values = out.setdefault(fact.provenance.sentence, Counter())
        for field_name in _NUMERIC_FACT_FIELDS:
            v = getattr(fact, field_name, None)
            if isinstance(v, (int, float)):
                values[float(v)] += 1
    return out


def check(
    premises: list[Reading],
    consumed_uids: dict[int, set[int]],  # sentence index -> consumed unit uids
    log: ArithmeticLog,
    reg: Registry,
    proposed: Answer,
    store: FactStore | None = None,
    question: Reading | None = None,
) -> GuardVeto | None:
    """Run all enabled guards against a proposed committed answer.
    Returns the first veto, or None. Only 'number' answers are guarded —
    a decline is already safe."""
    if not proposed.committed:
        return None
    readings = premises + ([question] if question is not None else [])

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
        from .model import Discount, Goal, GroupTotal, PercentChange, Price, Rate

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
            if store is not None else set()
        )
        # A consumer that reads the WHOLE question number list by construction
        # (list-statistic: "the average of 4, 8, 15, 16, and 42"; vector: "the dot
        # product of (1, 2, 3) and (4, 5, 6)") accounts for every count in the
        # question — but only the FIRST binds an ask slot, so the per-count fact
        # check below would wrongly veto the rest. Exempt the question reading for
        # those consumers (the ask is re-derived, as answer-accounting does).
        # Every arithmetic ask still checks its question.
        #
        # Membership is the CONSUMER's contract, not a convenience: a consumer
        # belongs here only if it reads every count in the question and logs them
        # all as operands. Both do (each calls `evaluate` over its whole list).
        # Adding one that does NOT would silently disable the guard for its asks.
        exempt_question = None
        if question is not None:
            from .patterns import match_ask
            qm = match_ask(question, reg)
            if qm is not None and qm[1].get("consumer") in _WHOLE_LIST_CONSUMERS:
                exempt_question = question
        for reading in readings:
            if reading is exempt_question:
                continue
            used = consumed_uids.get(reading.sentence_index, set())
            # a MUTABLE per-reading copy: each stated mention CLAIMS one fact of
            # its value, so a sentence supplying value V once cannot account for
            # two mentions of V (the same-value blind spot the Counter closes).
            own_values = Counter(fact_values.get(reading.sentence_index, ()))
            for unit in reading.units:
                kind = unit.features.get("value_kind")
                if kind not in ("count", "multiplier", "fraction"):
                    continue
                value = float(unit.features["value"])
                # NO global arithmetic-log fallback here: the fold's own sum
                # would mask a same-number unread from another sentence.
                # Facts-from-own-sentence and explicit consumption are the
                # only honest evidence. Independently-accounted mentions (a
                # consumed uid, a pattern-consumed unit) never claim a fact slot.
                if unit.uid in used or unit.features.get("pattern_consumed"):
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
        from .model import Quantity
        from .patterns import match_ask

        matched = match_ask(question, reg)
        if matched is not None:
            _ask, query, _m = matched
            asked = query.get("measure")
            holder = query.get("entity")
            qualifier = query.get("measure_qualifier")
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
                for fact in store.by_kind(Quantity):
                    if fact.entity != holder:
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

    if _enabled(reg, "unresolved-derivation") and store is not None:
        # a FractionQuantity/RestQuantity the synthesizers could NOT resolve
        # means part of the text was read but not computed — committing
        # around it is how "ate half the sandwiches" silently vanishes
        from .model import (
            AnchorQuantity,
            FractionQuantity,
            PartitionQuantity,
            Quantity,
            RestQuantity,
        )

        derived = {
            (q.entity, q.verb, q.occurrence)
            for q in store.by_kind(Quantity)
            if q.provenance.source.startswith("synth/")
        }
        for f in store.by_kind(FractionQuantity):
            if (f.entity, f.verb, f.occurrence) not in derived:
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
        known_measures = {q.measure for q in store.by_kind(Quantity)}
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
