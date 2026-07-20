"""Physics domain (difg): a named physical quantity from the stated parameters.

SYNTHETIC ONLY (constitution rule 3): invented magnitudes, not difg CASES.

The formulas and the unit->dimension map are DATA (packs/difg-mined/formulas.yaml);
answer.py's `physics` consumer is the generic evaluator — the geometry template
with the shape dropped. It names no quantity, no unit and no formula.
"""

import math
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


def test_eponymic_quantity_binds_a_scaled_energy_operand(reg):
    """A named multiword quantity selects pack DATA, while the operand binds by
    its unit and is scaled to the formula's canonical dimension. The invented
    magnitude keeps this synthetic; it is not a SciBench case string."""
    r = solve(
        "Calculate the de Broglie wavelength for an electron with a kinetic "
        "energy of 144 eV?",
        reg,
        tracing=False,
    )
    assert r.answer.committed, (r.answer.reason or "")
    assert r.answer.value == pytest.approx(0.10220216384651244)


def test_an_unregistered_eponymic_quantity_declines(reg):
    """The grammar is general, but formula selection is exact pack data."""
    r = solve(
        "Calculate the de Rowan wavelength for an electron with a kinetic "
        "energy of 144 eV?",
        reg,
        tracing=False,
    )
    assert not r.answer.committed


def test_eponymic_quantity_still_rejects_an_extra_count(reg):
    """The physics consumer continues to own whole-list accounting: a time the
    formula does not read cannot be laundered by the new ask."""
    r = solve(
        "Calculate the de Broglie wavelength for an electron with a kinetic "
        "energy of 144 eV in 2 seconds?",
        reg,
        tracing=False,
    )
    assert not r.answer.committed


def test_qualified_quantity_reads_dimensioned_operands_from_premises(reg):
    """A formula may read unit-bearing operands stated before the final ask.
    Invented magnitudes keep this synthetic rather than copying a corpus row."""
    r = solve(
        "A ball is thrown at an angle of 37 degrees to the ground. "
        "If the ball lands 121 meters away, what was the initial speed of the ball?",
        reg,
        tracing=False,
    )
    assert r.answer.committed, (r.answer.reason or "")
    want = (121 * 9.80665 / math.sin(2 * math.radians(37))) ** 0.5
    assert r.answer.value == pytest.approx(want)


def test_qualified_quantity_formula_key_keeps_the_modifier(reg):
    """Another qualifier cannot borrow the buyer's formula merely because
    both compounds have the same `speed` head."""
    r = solve(
        "A ball is thrown at an angle of 37 degrees to the ground. "
        "If the ball lands 121 meters away, what was the final speed of the ball?",
        reg,
        tracing=False,
    )
    assert not r.answer.committed


def test_whole_document_physics_rejects_an_unused_premise_value(reg):
    """Taking the premise value-accounting exemption means physics owns every
    stated value there: an irrelevant duration may not be silently ignored."""
    r = solve(
        "A ball is thrown at an angle of 37 degrees for 3 seconds to the ground. "
        "If the ball lands 121 meters away, what was the initial speed of the ball?",
        reg,
        tracing=False,
    )
    assert not r.answer.committed


def test_whole_document_physics_rejects_a_duplicate_dimension(reg):
    """Two range values in separate premises are still ambiguous; document
    scope must not turn first/last mention order into an implicit role."""
    r = solve(
        "A ball is thrown at an angle of 37 degrees to the ground. "
        "The range is 119 meters. "
        "If the ball lands 121 meters away, what was the initial speed of the ball?",
        reg,
        tracing=False,
    )
    assert not r.answer.committed


def test_formula_operand_scope_is_declarative_and_question_safe_by_default(reg):
    """Old formulas remain question-scoped unless their pack definition opts
    into the stronger whole-document accounting contract."""
    assert reg.quantity_formula_scopes["speed"] == "question"
    assert reg.quantity_formula_scopes["initial speed"] == "document"
    assert reg.quantity_formula_scopes["frequency"] == "document"


def test_imperative_quantity_reads_a_wavelength_from_a_premise(reg):
    """The general imperative ask selects formula data; the document-scoped
    distance operand reaches canonical meters through conversion data."""
    r = solve(
        "A laser emits light at 480 nanometers. Calculate the frequency of the laser.",
        reg,
        tracing=False,
    )
    assert r.answer.committed, (r.answer.reason or "")
    assert r.answer.value == pytest.approx(2.99792458e-6 / (480e-9))


def test_frequency_accepts_the_nanometer_symbol(reg):
    """A symbol is a declarative number-form of its unit, not a kernel branch."""
    r = solve(
        "A laser emits light at 512 nm. Calculate the frequency of the laser.",
        reg,
        tracing=False,
    )
    assert r.answer.committed, (r.answer.reason or "")
    assert r.answer.value == pytest.approx(2.99792458e-6 / (512e-9))


def test_frequency_rejects_an_extra_premise_value(reg):
    """A document-scoped formula owns every accounted premise value."""
    r = solve(
        "A laser emits light at 480 nanometers for 2 seconds. "
        "Calculate the frequency of the laser.",
        reg,
        tracing=False,
    )
    assert not r.answer.committed


def test_frequency_rejects_values_without_a_distance_dimension(reg):
    """Numbers in a reachable sibling cannot bind by position."""
    r = solve(
        "A laser emits light for 3 seconds. Calculate the frequency of the laser.",
        reg,
        tracing=False,
    )
    assert not r.answer.committed


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
