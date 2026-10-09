"""Source-local numeric accounting shared by composed calculations."""

from collections import Counter


def numeric_mentions(reading, *, additional_kinds=()):
    from .answer import _ACCOUNTED_VALUE_KINDS
    return Counter(float(u.features["value"]) for u in reading.units
                   if u.features.get("value_kind") in (*_ACCOUNTED_VALUE_KINDS, *additional_kinds))


def audit_numeric_mentions(readings, expected, *, missing, duplicate, additional_kinds=()):
    """Every numeric mention needs one source-local use, including repeats."""
    for reading in readings:
        actual = numeric_mentions(reading, additional_kinds=additional_kinds)
        captured = expected.get(reading.sentence_index, Counter())
        if actual - captured:
            return missing
        if captured - actual:
            return duplicate
    return None
