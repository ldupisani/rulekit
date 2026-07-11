"""Guards: decline-safety checks between the pipeline and a committed answer.

Guards read only DECLARED properties (consumed unit ids, the arithmetic log,
unit features) — never rule identities. Config (guards.yaml) can enable or
tune a guard but cannot reference rules; that entanglement class is banned.
"""

from __future__ import annotations

from dataclasses import dataclass

from ..data.registry import Registry
from .answer import Answer
from .evaluate import ArithmeticLog
from .facts import FactStore
from .model import Reading

_NUMERIC_FACT_FIELDS = ("value", "factor", "offset", "fraction")


@dataclass
class GuardVeto:
    guard: str
    reason: str


def _enabled(reg: Registry, name: str) -> bool:
    cfg = reg.guard_config.get(name)
    return bool(cfg.get("enabled", True)) if cfg is not None else True


def _fact_values_by_sentence(store: FactStore) -> dict[int, set[float]]:
    """Numeric fields of admitted facts, keyed by originating sentence —
    a value is only accounted by facts its OWN sentence produced (a same
    number appearing in another sentence's fact must not mask an unread).

    RATE, PRICE and GOAL facts are excluded: a rate, price, or goal that
    merely EXISTS has not been used — "makes $18 an hour" must not unlock a
    fold that ignores the wage, "$10 each" must not unlock one that ignores
    the price, and "wants to collect 30 stamps" must not unlock one that
    ignores the goal. Their values count as read only when the arithmetic
    consumed them (the caller checks the log for rate/price/goal values)."""
    from .model import Goal, Price, Rate

    out: dict[int, set[float]] = {}
    for fact in store.facts:
        if isinstance(fact, (Rate, Price, Goal)):
            continue
        values = out.setdefault(fact.provenance.sentence, set())
        for field_name in _NUMERIC_FACT_FIELDS:
            v = getattr(fact, field_name, None)
            if isinstance(v, (int, float)):
                values.add(float(v))
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
        from .model import Goal, Price, Rate

        # values from USE-GATED fact kinds (Rate, Price, Goal): existence
        # alone doesn't count as read, but the arithmetic log having
        # consumed the value does
        rate_values = (
            {float(r.value) for r in store.by_kind(Rate)}
            | {float(p.value) for p in store.by_kind(Price)}
            | {float(g.value) for g in store.by_kind(Goal)}
            if store is not None else set()
        )
        for reading in readings:
            used = consumed_uids.get(reading.sentence_index, set())
            own_values = fact_values.get(reading.sentence_index, set())
            for unit in reading.units:
                kind = unit.features.get("value_kind")
                if kind not in ("count", "multiplier", "fraction"):
                    continue
                value = float(unit.features["value"])
                # NO global arithmetic-log fallback here: the fold's own sum
                # would mask a same-number unread from another sentence.
                # Facts-from-own-sentence and explicit consumption are the
                # only honest evidence.
                if (
                    unit.uid in used
                    or unit.features.get("pattern_consumed")
                    or value in own_values
                    or (value in rate_values and log.uses_value(value))
                ):
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

    if _enabled(reg, "unresolved-derivation") and store is not None:
        # a FractionQuantity/RestQuantity the synthesizers could NOT resolve
        # means part of the text was read but not computed — committing
        # around it is how "ate half the sandwiches" silently vanishes
        from .model import FractionQuantity, PartitionQuantity, Quantity, RestQuantity

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
        # untouched. A partition also counts as resolved when its
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
            if p.is_fraction:
                resolved = (p.attribute, p.verb, p.provenance.sentence) in resolved_by_shape
            else:
                resolved = (
                    p.attribute, p.value, p.verb, p.provenance.sentence
                ) in resolved_by_value
            if not resolved:
                return GuardVeto(
                    "unresolved-derivation",
                    f"'{p.value} of them are {p.attribute}' never resolved "
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
