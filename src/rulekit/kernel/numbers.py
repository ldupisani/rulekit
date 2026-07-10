"""Number annotation: digits, word-numbers, scales, multipliers, fractions.

Every value-carrying unit gets features {"value": float, "value_kind": ...}.
value_kind distinguishes how the value may be consumed:
- "count"      — a stated cardinal ("7", "seven", "1,200", "$5", "20%")
- "multiplier" — twice/triple/"3 times" (scales a referent, not a count)
- "fraction"   — half/"one third"/"1/2"
Value accounting (guards.py) requires every "count" to be consumed.
"""

from __future__ import annotations

import re

from ..data.registry import Registry
from .model import Reading, Word

_DIGIT = re.compile(r"^\$?(\d[\d,]*(?:\.\d+)?)(%?)$")


def annotate_numbers(reading: Reading, reg: Registry) -> Reading:
    units = reading.units
    i = 0
    while i < len(units):
        unit = units[i]
        fold = unit.features.get("fold", "")
        m = _DIGIT.match(fold)
        if m:
            value = float(m.group(1).replace(",", ""))
            kind = "count"
            changes: dict = {"value": value, "value_kind": kind}
            if m.group(2) == "%":
                changes = {"value": value / 100.0, "value_kind": "fraction", "percent": True}
            if fold.startswith("$"):
                changes["currency"] = True
            reading.record("annotate-number", unit, changes, f"digit token {unit.surface!r}")
        elif fold in reg.numbers:
            value = reg.numbers[fold]
            # word-number compounds: "twenty five" -> 25 (merge right unit)
            if (
                i + 1 < len(units)
                and units[i + 1].features.get("fold") in reg.numbers
                and value >= 20
                and reg.numbers[units[i + 1].features["fold"]] < 10
            ):
                nxt = units.pop(i + 1)
                merged = reading.new_unit(unit.words + nxt.words, dict(unit.features))
                merged.features["fold"] = f"{fold} {nxt.features['fold']}"
                units[i] = merged
                reading.record(
                    "merge-number", merged,
                    {"value": value + reg.numbers[nxt.features["fold"]], "value_kind": "count"},
                    f"compound word-number {merged.surface!r}",
                )
            else:
                reading.record(
                    "annotate-number", unit,
                    {"value": value, "value_kind": "count"},
                    f"word-number {unit.surface!r}",
                )
        elif fold in reg.multipliers:
            reading.record(
                "annotate-number", unit,
                {"value": reg.multipliers[fold], "value_kind": "multiplier"},
                f"multiplier word {unit.surface!r}",
            )
        elif fold in reg.fractions:
            reading.record(
                "annotate-number", unit,
                {"value": reg.fractions[fold], "value_kind": "fraction"},
                f"fraction word {unit.surface!r}",
            )
        elif fold in reg.scales and i > 0 and "value" in units[i - 1].features:
            prev = units[i - 1]
            scaled = prev.features["value"] * reg.scales[fold]
            merged = reading.new_unit(prev.words + unit.words, dict(prev.features))
            merged.features["fold"] = f"{prev.features['fold']} {fold}"
            units[i - 1 : i + 1] = [merged]
            reading.record(
                "merge-scale", merged,
                {"value": scaled, "value_kind": "count"},
                f"scale word {unit.surface!r} applied to {prev.surface!r}",
            )
            i -= 1
        # "a" as the count 1 before a scale/fraction handled in senses stage
        i += 1

    # word-number cascade: "one hundred" + "forty four" -> 144. Merge an
    # adjacent pair of WORD-derived counts when the right side is a smaller
    # magnitude than the left's scale (digits never cascade).
    changed = True
    while changed:
        changed = False
        units = reading.units
        for j in range(len(units) - 1):
            a, b = units[j], units[j + 1]
            if (
                a.features.get("value_kind") == "count"
                and b.features.get("value_kind") == "count"
                and not any(ch.isdigit() for ch in a.features.get("fold", ""))
                and not any(ch.isdigit() for ch in b.features.get("fold", ""))
                and a.features["value"] >= 100
                and b.features["value"] < 100
            ):
                merged = reading.new_unit(a.words + b.words, dict(a.features))
                merged.features["fold"] = f"{a.features['fold']} {b.features['fold']}"
                units[j : j + 2] = [merged]
                reading.record(
                    "merge-number", merged,
                    {"value": a.features["value"] + b.features["value"], "value_kind": "count"},
                    f"word-number cascade {merged.surface!r}",
                )
                changed = True
                break

    # "N times" -> multiplier ("3 times" scales like "triple")
    for j, unit in enumerate(reading.units[:-1]):
        nxt = reading.units[j + 1]
        if (
            unit.features.get("value_kind") == "count"
            and nxt.features.get("fold") == "times"
        ):
            reading.record(
                "annotate-number", unit,
                {"value_kind": "multiplier"},
                f"'{unit.surface} times' reads as a multiplier",
            )
    return reading
