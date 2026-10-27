"""Structured authoring diagnostics preserve the reader's completion contract."""

from rulekit.generation.candidate import (
    reading_context_requirements,
    reading_grammar_deficiencies,
)
from rulekit.kernel.model import Obligation, PATTERN, Reading, Word


def test_typed_diagnostics_keep_unknowns_grammar_and_context_without_hiding_gaps():
    reading = Reading("invented", sentence_index=3)
    reference = reading.new_unit((Word("sample", 0),), {
        "obligations": [Obligation("pronoun", "refers")],
    })
    number = reading.new_unit((Word("seven", 1),), {
        "obligations": [Obligation("value", "quantifies")],
    })
    unknown = reading.new_unit((Word("zindle", 2),), {"unknown": True})
    reading.units = [reference, number, unknown]

    details = reading.deficiency_details()
    assert [(gap.unit_uid, gap.need) for gap in details] == [
        (reference.uid, "refers"), (number.uid, "quantifies"), (unknown.uid, None),
    ]
    assert reading.deficiencies() == [
        "'sample' (pronoun) needs a refers and none was found.",
        "'seven' (value) needs a quantifies and none was found.",
        "I have no information about the word 'zindle'.",
    ]
    context = reading_context_requirements(reading)
    assert [(r.sentence_index, r.unit_uid, r.surface, r.need) for r in context] == [
        (3, reference.uid, "sample", "refers"),
    ]
    assert list(reading_grammar_deficiencies(reading)) == reading.deficiencies()[1:]
    assert not reading.saturated
    assert reference.unmet()[0].target is None
    assert reading.decisions == []


def test_optional_and_met_obligations_remain_outside_both_diagnostic_groups():
    reading = Reading("invented")
    unit = reading.new_unit((Word("sample", 0),), {
        "obligations": [
            Obligation("pronoun", "refers", target=PATTERN),
            Obligation("verb", "object", optional=True),
        ],
    })
    reading.units = [unit]

    assert reading.deficiency_details() == []
    assert reading.deficiencies() == []
    assert reading_context_requirements(reading) == ()
    assert reading_grammar_deficiencies(reading) == ()
    assert reading.saturated
