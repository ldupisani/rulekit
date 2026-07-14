"""mining candidate dimension-aggregate-asks: aggregate asks whose measure
is named by a DIMENSION NOUN ('height'/'weight'/'age'/'distance'/
'balance'/'earnings'/'cost') or, via the same family-resolution mechanism,
a unit-family CATEGORY NAME bound directly by an ask — never the UNIT
lemma itself ('foot'/'pound'/'year'/'dollar'). Two new imperative-headed
ask ids ("Calculate/Determine ... combined/average <dimension noun> ...",
gated on the new `compute_verb` category) route to the EXISTING 'combined'/
'average' consumers unchanged, resolving the measure via a NEW opt-in
function (`answer.py`'s `_resolve_dimension_measure`, triggered only by
`dimension_measure: true`) that looks up which unit FAMILY
('length_measure'/'mass_measure'/'time_measure'/'currency_measure', each
`dimension: true`) the dimension noun belongs to, then finds the UNIQUE
in-store unit of that family — UNIQUE-OR-DECLINE, never a guess. This also
exercises a general fix moved into the shared `_combined_holder_totals`
helper: the `holder_count` cardinal-holder-set guard (pre-existing for
'combined') now applies to 'average' too. Synthetic only."""

from pathlib import Path

import pytest

from rulekit.data.packs import load_packs
from rulekit.data.registry import compile_registry
from rulekit.kernel.engine import solve

REPO = Path(__file__).resolve().parent.parent


@pytest.fixture(scope="module")
def full_registry():
    mined = REPO / "packs/difg-mined"
    if not mined.exists():
        pytest.skip("difg-mined not generated")
    return compile_registry(
        load_packs([REPO / "packs/core-english", REPO / "packs/arithmetic", mined])
    )


def test_combined_height_pronoun_holders(full_registry):
    # a dimension relation ('taller') plus one stated height, exactly the
    # premise shape the brief's own evidence names: the relation synth
    # already emits BOTH people's foot-Quantities, so 'height' just needs
    # to resolve to 'foot' and sum them.
    r = solve(
        "Priya is 5 feet tall. Omar is 3 feet taller than Priya. "
        "Calculate their combined height.",
        full_registry,
    )
    assert r.answer.value == 13


def test_average_weight_cardinal_holders(full_registry):
    # three stated weights, a bare cardinal holder set ("of the three")
    # instead of a pronoun — reuses the cardinal `holder_count` slot.
    r = solve(
        "Ravi weighs 70 pounds. Suki weighs 50 pounds. Devon weighs 60 pounds. "
        "Determine the average weight of the three.",
        full_registry,
    )
    assert r.answer.value == 60


def test_combined_age_via_determine(full_registry):
    # 'age' resolves through the SAME time-unit family as the concrete
    # unit 'year' — no fact is ever literally keyed 'age'.
    r = solve(
        "Lena is 30 years old. Kofi is 40 years old. "
        "Determine their combined age.",
        full_registry,
    )
    assert r.answer.value == 70


def test_combined_balance_via_currency_family(full_registry):
    # a currency dimension noun ('balance') resolves via the SEPARATE
    # `currency_measure` family, never the pre-existing `currency`
    # (interchangeable) category — proves the two never interact.
    r = solve(
        "Marco has $40 in his account. Yuki has $25 in her account. "
        "Calculate their combined balance.",
        full_registry,
    )
    assert r.answer.value == 65


def test_holder_count_mismatch_declines_average(full_registry):
    # the ask names FOUR holders but only THREE are resolvable in the
    # premises — averaging the resolved three would silently answer the
    # wrong group; the (mining candidate) `holder_count` guard, now
    # shared by 'average' too, must decline instead of committing.
    r = solve(
        "Ana weighs 50 pounds. Beto weighs 60 pounds. Cleo weighs 70 pounds. "
        "Determine the average weight of the four people.",
        full_registry,
    )
    assert r.answer.kind == "decline"


def test_single_holder_declines_combined_height(full_registry):
    # a combined/average ask asserts plurality — exactly one holder of the
    # resolved measure must decline, not silently answer that one value.
    r = solve(
        "Priya is 5 feet tall. Calculate their combined height.",
        full_registry,
    )
    assert r.answer.kind == "decline"


def test_mixed_unit_family_declines_average_weight(full_registry):
    # two DIFFERENT mass units both present ('pound' and 'kilogram') means
    # the family has no UNIQUE in-store member — ambiguous, must decline
    # rather than guess which unit the average is over.
    r = solve(
        "Ravi weighs 70 pounds. Suki weighs 50 kilograms. "
        "Determine the average weight of the two.",
        full_registry,
    )
    assert r.answer.kind == "decline"
