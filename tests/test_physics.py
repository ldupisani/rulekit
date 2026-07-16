"""Physics domain (difg): a named physical quantity from the stated parameters.

SYNTHETIC ONLY (constitution rule 3): invented magnitudes, not difg CASES.

The formulas and the unit->dimension map are DATA (packs/difg-mined/formulas.yaml);
answer.py's `physics` consumer is the generic evaluator — the geometry template
with the shape dropped. It names no quantity, no unit and no formula.
"""

from pathlib import Path

import pytest

from rulekit.data.project import load_project
from rulekit.kernel.engine import solve


@pytest.fixture(scope="module")
def reg():
    return load_project(Path("projects/difg")).registry


@pytest.mark.parametrize(
    "question, want",
    [
        ("What is the speed of an object that travels 60 meters in 4 seconds?", 15.0),
        ("What is the weight of a 3 kg object on Earth?", 29.4),
        ("What is the voltage across a 7 ohm resistor with a current of 3 amps?", 21.0),
    ],
)
def test_quantity(reg, question, want):
    r = solve(question, reg, tracing=False)
    assert r.answer.committed, (r.answer.reason or "")
    assert r.answer.value == pytest.approx(want)


# --- the property the whole design exists for ------------------------------


def test_operands_bind_by_unit_not_by_position(reg):
    """THE point of the dimensions map. Each number is bound by the DIMENSION OF
    ITS OWN UNIT, so word order cannot fool it. The cheap alternative — fill the
    formula's params from the numbers positionally — reads difg's phrasing right
    and answers 0.05 here with total confidence. Both orders must give 15."""
    a = solve("What is the speed of an object that travels 60 meters in 4 seconds?",
              reg, tracing=False)
    b = solve("What is the speed of an object that took 4 seconds to travel 60 meters?",
              reg, tracing=False)
    assert a.answer.value == pytest.approx(15.0)
    assert b.answer.committed, (b.answer.reason or "")
    assert b.answer.value == pytest.approx(15.0)


def test_unit_may_be_the_qualifier_not_the_head(reg):
    """"a 3 kg object" folds to ONE counted unit whose LEMMA is 'object' — the
    unit survives only as the QUALIFIER ('kilogram'). Reading the lemma alone
    would bind nothing and decline."""
    r = solve("What is the weight of a 3 kg object on Earth?", reg, tracing=False)
    assert r.answer.committed, (r.answer.reason or "")
    assert r.answer.value == pytest.approx(29.4)


# --- definitive-or-decline --------------------------------------------------


def test_missing_dimension_declines(reg):
    """An unsupplied parameter leaves its name unbound and `evaluate` raises —
    the same decline path geometry uses. No guard is needed for it."""
    assert not solve("What is the speed of an object that travels 60 meters?",
                     reg, tracing=False).answer.committed


def test_shredded_compound_unit_declines(reg):
    """The phantom-exponent trap, pinned. The tokenizer shreds "3 m/s^2" into the
    numbers [3, 2] — the EXPONENT becomes a free-standing number. A consumer that
    read the number list positionally would bind it as an operand. Binding by
    unit means no 'acceleration' ever appears, so `force` declines."""
    r = solve("What is the force on a mass of 10 kg accelerating at 3 m/s^2?",
              reg, tracing=False)
    assert not r.answer.committed


def test_ambiguous_dimension_declines(reg):
    """Two values for ONE dimension: the question states more than the formula
    can consume and picking either is a guess."""
    r = solve("What is the speed of an object that travels 60 meters then 50 meters in 4 seconds?",
              reg, tracing=False)
    assert not r.answer.committed


def test_ambiguous_dimension_declines_even_when_the_values_are_EQUAL(reg):
    """REGRESSION (constitution review). The guard first read `env[dim] != value`
    and so let the equal case through: "60 meters then 60 meters in 4 seconds"
    committed 15.0 when the distance is 120 and the answer is 30. Same-value
    collisions defeat accounting guards — the lesson guards.py's own Counter
    exists for — and a test using 60-then-50 passes straight over it."""
    r = solve("What is the speed of an object that travels 60 meters then 60 meters in 4 seconds?",
              reg, tracing=False)
    assert not r.answer.committed


def test_an_unread_count_declines(reg):
    """REGRESSION (constitution review). This consumer takes the value-accounting
    exemption (_WHOLE_LIST_CONSUMERS), so NOTHING downstream catches a number the
    formula silently ignored: "60 meters in 4 seconds AND 3 MINUTES" committed
    15.0 when the true answer is 0.33 — 'minute' denominates no dimension here.
    Taking the exemption means owning the accounting: every stated count is read
    or the commit goes."""
    r = solve("What is the speed of an object that travels 60 meters in 4 seconds and 3 minutes?",
              reg, tracing=False)
    assert not r.answer.committed


@pytest.mark.parametrize(
    "question",
    [
        # a stated FRACTION the formula cannot read ("half of 60 meters" is
        # ordinary English, and the 0.5 is a fully-read unit, not an artifact)
        "What is the speed of an object that travels half of 60 meters in 4 seconds?",
        # a stated MULTIPLIER, before and after the operand
        "What is the speed of an object that travels 60 meters in twice 4 seconds?",
        "What is the speed of an object that travels 60 meters in 4 seconds three times?",
    ],
)
def test_an_unread_multiplier_or_fraction_declines(reg, question):
    """REGRESSION (constitution review, SECOND pass). The first fix for the
    unread-count hole re-implemented only the `count` third of the guard's duty,
    so a stated multiplier/fraction still slipped through and committed 15.0 when
    the true answers are 7.5. The consumer now reads `_ACCOUNTED_VALUE_KINDS`
    from guards.py rather than re-listing the kinds — a contract with two copies
    drifts. The lesson: fix the CLASS the witness belongs to, not the witness."""
    assert not solve(question, reg, tracing=False).answer.committed


def test_a_bindable_but_unused_value_declines(reg):
    """REGRESSION (constitution review, THIRD pass — and the subtlest of the
    three). Declining on values that cannot BIND is not the duty; the duty is
    that every stated value is READ. Those sets differ: "the weight of a 3 kg
    object THAT TRAVELS 60 METERS IN 4 SECONDS" binds distance and time, but
    `mass * 9.8` never references them — so nothing declined and it committed
    29.4 while ignoring two stated quantities. The consumer now derives the read
    set from the EXPRESSION's own names.

    Latent for these three formulas (travel really is irrelevant to weight), and
    live the moment a formula's bindable set exceeds its operands — which is
    exactly what the `_TOKEN` increment's velocity/acceleration dimensions do."""
    r = solve("What is the weight of a 3 kg object that travels 60 meters in 4 seconds?",
              reg, tracing=False)
    assert not r.answer.committed


def test_the_log_records_what_was_read_not_what_was_bindable(reg):
    """The logging vehicle must not LAUNDER an ignored value: other guards
    consult `log.uses_value()` as evidence. Only expr-referenced dimensions may
    reach the log."""
    r = solve("What is the weight of a 3 kg object on Earth?", reg, tracing=False)
    assert r.answer.committed
    logged = " ".join(e.expression for e in r.log.entries)
    assert "3" in logged and "60" not in logged


def test_one_unit_per_dimension_is_a_compile_error(reg):
    """The docstring's "ONE canonical unit per dimension" is ENFORCED, not
    asserted: a second unit is a second SCALE, and the consumer multiplies
    whatever it binds ("the weight of a 300 g object" -> 2940 N, not 2.94)."""
    from rulekit.data.schemas import FormulasDoc

    with pytest.raises(Exception, match="one canonical unit"):
        FormulasDoc(
            format="rulekit/formulas@1",
            dimensions={"mass": ["kilogram", "gram"]},
            formulas=[],
        )


def test_unknown_quantity_declines(reg):
    """The category gates the ask to quantities the table can compute."""
    assert not solve("What is the enthalpy of a 3 kg object?", reg, tracing=False).answer.committed


# --- the 'power' collision --------------------------------------------------


def test_arithmetic_power_is_untouched(reg):
    """'power' is an arithmetic operator word AND was a candidate physics
    quantity. ask/arith-power consumes 7 units and must keep winning."""
    r = solve("What is 2 to the power of 10?", reg, tracing=False)
    assert r.answer.committed, (r.answer.reason or "")
    assert r.answer.value == pytest.approx(1024.0)
