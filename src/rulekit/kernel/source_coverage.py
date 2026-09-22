"""Inspectable language coverage for consumers requiring a complete source.

Only grammatical articles/punctuation, explicitly consumed rule units, and
the caller's exact evidence footprint are covered. Numeric accounting and
which facts/assumptions are admissible remain separate consumer policies.
"""


def uncovered_units(reading, covered=()):
    """Return the actual unread units, not just a yes/no completeness flag."""
    covered = frozenset(covered)
    return tuple(unit for unit in reading.units
                 if unit.uid not in covered
                 and not unit.features.get("pattern_consumed")
                 and unit.sense() not in {"article", "punct"})


def uncovered_document_units(premises, question, question_covered=()):
    """Keep sentence-local identities: ask coverage never covers a premise."""
    return tuple((reading.sentence_index, unit)
                 for reading in (*premises, question)
                 for unit in uncovered_units(
                     reading, question_covered if reading is question else ()))
