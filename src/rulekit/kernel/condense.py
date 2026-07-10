"""Condensation: merge local structures into richer single units, to a
fixpoint. Merge is the structural move (adjective+noun = one restricted
concept, "mango trees" = one compound, "New York" = one name); binding is
the relational one — merge only when the result is genuinely one concept.

Order matters: NOMINAL merges run to a fixpoint first (so "mango trees" is
one compound before a count claims it), then the count+noun merge attaches
values to the completed nominals.
"""

from __future__ import annotations

from ..data.registry import Registry
from .model import Reading, Unit


def _merge(reading: Reading, i: int, head_features_from: Unit, kind: str, reason: str,
           extra: dict | None = None) -> Unit:
    units = reading.units
    a, b = units[i], units[i + 1]
    merged = reading.new_unit(a.words + b.words, dict(head_features_from.features))
    merged.features["fold"] = f"{a.features['fold']} {b.features['fold']}"
    units[i : i + 2] = [merged]
    reading.record(kind, merged, extra or {}, reason)
    return merged


def _nominal_pass(reading: Reading, reg: Registry) -> bool:
    units = reading.units
    for i in range(len(units) - 1):
        a, b = units[i], units[i + 1]
        # adjective + noun -> restricted noun ("red apple")
        if a.sense() == "adjective" and b.sense() == "noun":
            attrs = list(b.features.get("attributes", []))
            attrs.append(a.features.get("lemma", a.features["fold"]))
            _merge(reading, i, b, "merge-attribute",
                   f"adjective {a.surface!r} restricts {b.surface!r}",
                   {"attributes": attrs})
            return True
        # noun + noun -> compound, head = the RIGHT noun ("mango trees")
        if (
            a.sense() == "noun" and b.sense() == "noun"
            and "value" not in a.features
        ):
            attrs = list(b.features.get("attributes", []))
            attrs.append(a.features.get("lemma", a.features["fold"]))
            _merge(reading, i, b, "merge-compound",
                   f"compound noun: {a.surface!r} modifies head {b.surface!r}",
                   {"attributes": attrs})
            return True
        # CAPITALIZED adjective + name -> one name ("Tall Tuna"): the
        # capitalization, not the part of speech, is the naming signal
        if (
            a.sense() == "adjective"
            and a.surface[:1].isupper()
            and b.sense() == "name"
        ):
            merged = _merge(reading, i, b, "merge-name",
                            f"capitalized {a.surface!r} is part of the name {b.surface!r}")
            merged.features["lemma"] = merged.features["fold"]
            return True
        # name + name -> one name ("New York")
        if a.sense() == "name" and b.sense() == "name":
            merged = _merge(reading, i, a, "merge-name",
                            f"consecutive names {a.surface!r} {b.surface!r} = one name")
            merged.features["lemma"] = merged.features["fold"]
            return True
    return False


def _count_pass(reading: Reading, reg: Registry) -> bool:
    units = reading.units
    for i in range(len(units) - 1):
        a, b = units[i], units[i + 1]
        # count + noun -> one counted noun ("3 apples" is one concept);
        # multipliers/fractions stay separate (they scale a referent)
        if (
            a.features.get("value_kind") == "count"
            and a.sense() != "noun"
            and b.sense() == "noun"
            and not a.features.get("pattern_consumed")
        ):
            _merge(reading, i, b, "merge-count",
                   f"count {a.surface!r} quantifies {b.surface!r} — one concept",
                   {"value": a.features["value"], "value_kind": "count"})
            return True
    return False


def condense(reading: Reading, reg: Registry) -> Reading:
    while _nominal_pass(reading, reg):
        pass
    while _count_pass(reading, reg):
        pass
    return reading
