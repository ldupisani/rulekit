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

# A comma inside a digit token is a THOUSANDS SEPARATOR, and a thousands
# separator always groups exactly three digits ("1,234", "12,345,678"). The
# original pattern here was `\d[\d,]*`, which accepted ANY comma placement and
# then stripped the commas — so "3,4" silently read as the number 34. No English
# text means that; every real misread was a COORDINATE PAIR ("(3,4)") being
# flattened into a bogus scalar. Measured blast radius of the tightening: ZERO
# items across GSM8K / ASDiv / SVAMP / MAWPS (no word problem contains the
# pattern) — it only ever fired on difg coordinates and SciBench LaTeX.
#
# The two alternatives are ORDERED, and the order IS the ambiguity resolution:
# a validly-grouped token is a number first ("1,234" -> 1234, which GSM8K money
# depends on), and only a token that CANNOT be a thousands-separated number is
# offered to _TUPLE below. So "(1,234)" as a coordinate pair would read as the
# scalar 1234 — accepted and documented; no corpus item has that shape.
# The trailing `,?` is PUNCTUATION, not a separator, and it is load-bearing: in
# a spaced list ("the highest of 12, 45, 7, and 33") the tokenizer keeps the
# comma on the fold ("12,"), and the old permissive pattern absorbed it by
# accident. Dropping it broke three list_statistic items — the difg gate caught
# it (0 BROKE is the gate, and it earned its keep here).
_DIGIT = re.compile(r"^(-?)\$?(\d{1,3}(?:,\d{3})+(?:\.\d+)?|\d+(?:\.\d+)?)(%?),?$")
# A COORDINATE TUPLE: comma-separated numbers that are NOT a valid thousands
# grouping — "0,0", "3,4", "1,2". Structural (digit morphology), never a lexicon
# fact, exactly like _DIGIT and _ORDINAL. The surrounding parens are already
# stripped by the tokenizer, so the comma grouping is the only signal there is.
# Carries no `value`: a tuple is not a scalar, so guards.py's value-accounting
# never demands it be consumed as a quantity (the `ordinal` precedent above).
_TUPLE = re.compile(r"^(\d+(?:\.\d+)?(?:,\d+(?:\.\d+)?)+)$")
# An ISO DATE ("2024-01-01"), kept whole by tokenize.py. Structural digit
# morphology, never a lexicon fact -- the _TUPLE precedent exactly, and like a
# tuple it carries NO `value`: a date is not a scalar, so guards.py's
# value-accounting never demands it be consumed as a quantity.
_ISO_DATE = re.compile(r"^(\d{4})-(\d{2})-(\d{2})$")

_SLASH_FRACTION = re.compile(r"^(\d+)/(\d+)$")
# Fused ordinal ("5th", "21st", "3rd") — productive digit+suffix morphology,
# structural like digit parsing itself, not a lexicon fact. An ordinal is an
# INDEX/MODIFIER, never an operative count: it gets its own value_kind so
# senses.py gives it a distinct sense and guards.py's value-accounting never
# demands it be consumed as a quantity (kind not in count/multiplier/
# fraction) — the only effect is that it stops being an unknown word.
_ORDINAL = re.compile(r"^(\d[\d,]*)(?:st|nd|rd|th)$")


def annotate_numbers(reading: Reading, reg: Registry) -> Reading:
    units = reading.units
    i = 0
    while i < len(units):
        unit = units[i]
        fold = unit.features.get("fold", "")
        # A declared ordinal modifying a compatible noun stays a lexical
        # modifier, preserving reference identity through ordinary condensation.
        # Counted fractions retain their existing interpretation.
        ordinal = reg.attrs.get(fold, {}).get("ordinal_index")
        head = units[i + 1].features.get("fold", "") if i + 1 < len(units) else ""
        head = reg.plural_to_singular.get(head, head)
        previous = units[i - 1].features if i else {}
        if (ordinal is not None and fold in reg.fractions and head
                and any(category == "holder_ordinal" for category, _ in
                        reg.attribute_compatibility_pairs(fold, head))
                and previous.get("value_kind") not in {"count", "fraction"}):
            reading.record("annotate-ordinal-modifier", unit,
                           {"ordinal_index": float(ordinal)},
                           "declared ordinal modifying a compatible noun")
            i += 1
            continue
        # the SURFACE, not the fold: symbols are case-significant ('Co' the
        # element vs 'CO' carbon monoxide), and the fold is lower-cased
        dm = _ISO_DATE.match(fold)
        if dm:
            reading.record(
                "annotate-number", unit,
                {"value_kind": "date", "components": fold},
                f"ISO date {unit.surface!r}",
            )
            i += 1
            continue
        sf = _SLASH_FRACTION.match(fold)
        if sf and int(sf.group(2)) != 0:
            reading.record(
                "annotate-number", unit,
                {"value": int(sf.group(1)) / int(sf.group(2)), "value_kind": "fraction"},
                f"slash fraction {unit.surface!r}",
            )
            i += 1
            continue
        om = _ORDINAL.match(fold)
        if om:
            reading.record(
                "annotate-number", unit,
                {"value": float(om.group(1).replace(",", "")), "value_kind": "ordinal"},
                f"fused ordinal {unit.surface!r}",
            )
            i += 1
            continue
        m = _DIGIT.match(fold)
        if m:
            value = float(m.group(2).replace(",", "")) * (-1 if m.group(1) else 1)
            kind = "count"
            changes: dict = {"value": value, "value_kind": kind}
            if m.group(3) == "%":
                changes = {"value": value / 100.0, "value_kind": "fraction", "percent": True}
            if fold.lstrip("-").startswith("$"):
                changes["currency"] = True
            reading.record("annotate-number", unit, changes, f"digit token {unit.surface!r}")
        elif _TUPLE.match(fold):
            # Reached ONLY when _DIGIT declined, i.e. the commas are not a valid
            # thousands grouping — see _TUPLE. Components stay a STRING because
            # every ask template interpolates to text (_slot_value); the
            # `coordinate` consumer splits them back out.
            comps = _TUPLE.match(fold).group(1)
            reading.record(
                "annotate-number", unit,
                {"value_kind": "tuple", "components": comps},
                f"coordinate tuple {unit.surface!r}",
            )
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
            singular = reg.fraction_plurals.get(fold)
            reading.record(
                "annotate-number", unit,
                {
                    "value": reg.fractions[fold],
                    "value_kind": "fraction",
                    "requires_count": singular is not None,
                    "fraction_lemma": singular or fold,
                },
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
        elif fold in reg.scales:
            # A bare scale denotes one scale ("hundred years", "dozen eggs").
            # Explicit preceding operands took the multiplication branch above.
            reading.record(
                "annotate-number", unit,
                {"value": reg.scales[fold], "value_kind": "count"},
                f"bare scale word {unit.surface!r}",
            )
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

    # word-count + word-fraction -> one fraction ("one half" = 0.5,
    # "three fourths" = 0.75; hyphens tokenize apart, so "one-fifth" lands
    # here too). Word-derived counts only — digits never merge. Mining
    # candidate relclause-subject-relations: this used a single-shot `for
    # ...: break` that merged only the FIRST occurrence in the whole
    # sentence — any second, independent word-fraction phrase in the same
    # sentence ("... half as many X as Y, who has a third as many Z as W")
    # was silently left unmerged. Same `changed`-fixpoint idiom as the
    # word-number cascade immediately above (re-scan after every merge,
    # since each merge shrinks/shifts `units`); a sentence with exactly one
    # occurrence re-scans once more, finds nothing, and exits — byte-
    # identical to the old single-shot behavior for every sentence that
    # only ever had one such phrase to begin with.
    changed = True
    while changed:
        changed = False
        units = reading.units
        for j in range(len(units) - 1):
            a, b = units[j], units[j + 1]
            if (
                a.features.get("value_kind") == "count"
                and b.features.get("value_kind") == "fraction"
                and not any(ch.isdigit() for ch in a.features.get("fold", ""))
                and not b.features.get("percent")
            ):
                merged = reading.new_unit(a.words + b.words, dict(b.features))
                merged.features["fold"] = f"{a.features['fold']} {b.features['fold']}"
                units[j : j + 2] = [merged]
                reading.record(
                    "merge-number", merged,
                    {"value": a.features["value"] * b.features["value"],
                     "value_kind": "fraction",
                     "requires_count": False,
                     "fraction_count": a.features["value"]},
                    f"word fraction {merged.surface!r}",
                )
                changed = True
                break

    # "N times" -> ONE multiplier unit ("four times as many" must present
    # [multiplier][as][many] to the patterns, not [multiplier][times][as]…)
    # Same fixpoint widening as the word-fraction block above and for the
    # same reason (mining candidate relclause-subject-relations): a
    # relative-clause-subject relation commonly carries a SECOND,
    # independent "N times" phrase in the same sentence as the outer
    # relation's own.
    changed = True
    while changed:
        changed = False
        units = reading.units
        for j in range(len(units) - 1):
            a, b = units[j], units[j + 1]
            if (
                a.features.get("value_kind") == "count"
                and reg.operators.get(b.features.get("fold", "")) == "*"
            ):
                marker = b.features["fold"]
                merged = reading.new_unit(a.words + b.words, dict(a.features))
                merged.features["fold"] = f"{a.features['fold']} {marker}"
                units[j : j + 2] = [merged]
                reading.record(
                    "merge-number", merged,
                    {"value": a.features["value"], "value_kind": "multiplier"},
                    f"{merged.surface!r} reads as one multiplier",
                )
                changed = True
                break

    # "N percent" (the word) -> fraction, factor from the percents data.
    # Same fixpoint widening as the two blocks above, same reason.
    changed = True
    while changed:
        changed = False
        units = reading.units
        for j in range(len(units) - 1):
            a, b = units[j], units[j + 1]
            factor = reg.percents.get(b.features.get("fold", ""))
            if a.features.get("value_kind") == "count" and factor is not None:
                merged = reading.new_unit(a.words + b.words, dict(a.features))
                merged.features["fold"] = f"{a.features['fold']} {b.features['fold']}"
                units[j : j + 2] = [merged]
                reading.record(
                    "merge-number", merged,
                    {"value": a.features["value"] * factor,
                     "value_kind": "fraction", "percent": True},
                    f"{merged.surface!r} reads as a fraction",
                )
                changed = True
                break
    return reading
