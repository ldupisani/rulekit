"""Relative reporting scopes, distinct from elapsed work and rate cadence."""

from dataclasses import dataclass
from math import isfinite


@dataclass(frozen=True)
class ReportingPeriod:
    unit: str
    offset: float

    def precedes(self, other):
        # Different grains require dates or an explicit containment relation.
        return self.unit == other.unit and self.offset < other.offset


def reporting_period(reference, reg):
    """Normalize a declared deictic marker or a qualified singular period.

    Bare unit references are supplied only by grammar with an explicit
    current-period determiner. Owners, labels and compounded restrictions
    cannot silently become reporting scope.
    """
    if (
        reference is None
        or not reference.resolved
        or reference.owner
        or reference.label
        or len(reference.qualifiers) > 1
    ):
        return None
    head = reg.plural_to_singular.get(reference.head, reference.head)
    if reg.word_in_category(head, "reporting_time_marker"):
        days = {
            reg.plural_to_singular.get(word, word)
            for word in reg.cat_members_deep("calendar_day_unit")
        }
        offset = reg.temporal_offsets.get(head)
        if reference.qualifiers or len(days) != 1 or offset is None:
            return None
        return ReportingPeriod(next(iter(days)), offset)
    if not reg.word_in_category(head, "reporting_period_unit"):
        return None
    offset = 0
    if reference.qualifiers:
        (qualifier,) = reference.qualifiers
        if not reg.word_in_category(qualifier, "relative_period_attribute"):
            return None
        offset = reg.attribute_value(qualifier, "relative_period_offset")
    if offset is None or not isfinite(offset) or not float(offset).is_integer():
        return None
    return ReportingPeriod(head, offset)


def period_annotation(reference):
    """Render preserved source qualifiers for existing temporal metadata."""
    return " ".join((*reference.qualifiers, reference.head))
