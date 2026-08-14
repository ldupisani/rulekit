"""Generic temporal-perspective helpers.

Surface forms remain pack data. The kernel only knows the structural category
names that classify a bound form as present, past, or future.
"""

from __future__ import annotations

from ..data.registry import Registry


PRESENT = "present"
PAST = "past"
FUTURE = "future"


def normalize_perspective(raw: object, reg: Registry) -> str | None:
    """Normalize a declared perspective or category-governed surface form."""

    if raw is None:
        return None
    value = str(raw).strip().casefold()
    if value in {PRESENT, PAST, FUTURE}:
        return value
    if reg.word_in_category(value, "present_copula"):
        return PRESENT
    if reg.word_in_category(value, "past_copula"):
        return PAST
    if reg.word_in_category(value, "future_modal"):
        return FUTURE
    return None


def perspectives_match(
    required: object, evidence: object, reg: Registry
) -> bool:
    """True only when both declarations resolve to the same perspective."""

    wanted = normalize_perspective(required, reg)
    actual = normalize_perspective(evidence, reg)
    return wanted is not None and actual is not None and wanted == actual
