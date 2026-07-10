"""Condensation: merge local structures into richer single units, to a
fixpoint. Merge is the structural move (adjective+noun = one restricted
concept, "New York" = one name); binding is the relational one — merge only
when the result is genuinely one concept.
"""

from __future__ import annotations

from ..data.registry import Registry
from .model import Reading


def condense(reading: Reading, reg: Registry) -> Reading:
    changed = True
    while changed:
        changed = False
        units = reading.units
        for i in range(len(units) - 1):
            a, b = units[i], units[i + 1]
            # count + noun -> one counted noun ("3 apples" is one concept);
            # a multiplier/fraction stays separate (it scales a referent)
            if (
                a.features.get("value_kind") == "count"
                and b.sense() == "noun"
                and not a.features.get("pattern_consumed")
            ):
                merged = reading.new_unit(a.words + b.words, dict(b.features))
                merged.features["fold"] = f"{a.features['fold']} {b.features['fold']}"
                units[i : i + 2] = [merged]
                reading.record(
                    "merge-count", merged,
                    {"value": a.features["value"], "value_kind": "count"},
                    f"count {a.surface!r} quantifies {b.surface!r} — one concept",
                )
                changed = True
                break
            # adjective + noun -> noun carrying the adjective as attribute
            if a.sense() == "adjective" and b.sense() == "noun":
                merged = reading.new_unit(a.words + b.words, dict(b.features))
                merged.features["fold"] = f"{a.features['fold']} {b.features['fold']}"
                attrs = list(b.features.get("attributes", []))
                attrs.append(a.features.get("lemma", a.features["fold"]))
                units[i : i + 2] = [merged]
                reading.record(
                    "merge-attribute", merged,
                    {"attributes": attrs},
                    f"adjective {a.surface!r} restricts {b.surface!r}",
                )
                changed = True
                break
            # name + name -> one name ("New York")
            if a.sense() == "name" and b.sense() == "name":
                merged = reading.new_unit(a.words + b.words, dict(a.features))
                merged.features["fold"] = f"{a.features['fold']} {b.features['fold']}"
                merged.features["lemma"] = merged.features["fold"]
                units[i : i + 2] = [merged]
                reading.record(
                    "merge-name", merged, {},
                    f"consecutive names {a.surface!r} {b.surface!r} = one name",
                )
                changed = True
                break
    return reading
