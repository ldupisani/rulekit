"""The shared dimensional-algebra module (`kernel/dimensions.py`).

SYNTHETIC ONLY (constitution rule 3): invented units and magnitudes, never a
benchmark string. The module is the extraction increment — the one home of
the conversion primitives that previously lived as separate, drifting copies
(`totals._conversion_factor`, `learn._is_measure_unit`,
`measurement_reading._substance_conversion_factor`, and the physics bind
loop). These tests pin each moved contract at its new home:

- `conversion_factor`: multi-hop BFS over declared pairs; None when no path.
- `substance_conversion_factor`: one bridge composition per candidate, at
  most one direct ordinary edge per side; candidate disagreement -> None.
- `is_measure_unit`: membership on either side of a declared pair.
- `bind_count_to_dimension`: direct dimension hit, scale-to-canonical,
  ambiguity refusal, bindable-but-unread refusal.
"""

from types import SimpleNamespace

import pytest

from rulekit.data.project import load_project
from rulekit.kernel.dimensions import (
    bind_count_to_dimension,
    conversion_factor,
    is_measure_unit,
    substance_conversion_factor,
)


@pytest.fixture(scope="module")
def reg():
    return load_project("projects/difg").registry


# --- conversion_factor ---------------------------------------------------

def test_direct_declared_pair_returns_its_factor(reg):
    assert conversion_factor(reg, "meter", "centimeter") == 100.0
    assert conversion_factor(reg, "centimeter", "meter") == 0.01


def test_same_unit_is_identity(reg):
    assert conversion_factor(reg, "meter", "meter") == 1.0


def test_multi_hop_chain_the_table_never_states_directly(reg):
    # yard/foot and foot/inch are declared; yard/inch is not.
    assert conversion_factor(reg, "yard", "inch") == pytest.approx(36.0)


def test_unrelated_units_return_none(reg):
    assert conversion_factor(reg, "dog", "inch") is None


# --- substance_conversion_factor -----------------------------------------

def test_substance_bridge_composes_direct_edges_on_both_sides(reg):
    # water: kilogram <-> liter, factor 1 (core-english conversions.yaml).
    assert substance_conversion_factor(reg, "water", "kilogram", "liter") == 1.0
    assert substance_conversion_factor(reg, "water", "liter", "kilogram") == 1.0


def test_substance_bridge_needs_the_matching_substance(reg):
    # A bridge is scoped: another substance must not traverse water's row.
    assert substance_conversion_factor(reg, "oil", "kilogram", "liter") is None


def test_substance_bridge_requires_a_complete_scoped_path(reg):
    assert substance_conversion_factor(reg, "water", "kilogram", "meter") is None


def _two_path_substance_registry(*, second_bridge_factor: float) -> SimpleNamespace:
    return SimpleNamespace(
        conversions={
            ("crate", "mass-base"): 2.0,
            ("volume-base", "tank"): 3.0,
            ("crate", "mass-alternate"): 4.0,
            ("volume-alternate", "tank"): 1.5,
        },
        substance_conversions={
            ("sap", "mass-base", "volume-base"): 5.0,
            (
                "sap",
                "mass-alternate",
                "volume-alternate",
            ): second_bridge_factor,
        },
    )


def test_substance_bridge_accepts_multiple_agreeing_candidates():
    reg = _two_path_substance_registry(second_bridge_factor=5.0)
    assert substance_conversion_factor(reg, "sap", "crate", "tank") == 30.0


def test_substance_bridge_rejects_conflicting_candidates():
    reg = _two_path_substance_registry(second_bridge_factor=6.0)
    assert substance_conversion_factor(reg, "sap", "crate", "tank") is None


# --- is_measure_unit -----------------------------------------------------

def test_declared_unit_lemmas_are_measure_units(reg):
    assert is_measure_unit(reg, "pound")
    assert is_measure_unit(reg, "gallon")


def test_container_nouns_are_never_measure_units(reg):
    assert not is_measure_unit(reg, "box")
    assert not is_measure_unit(reg, "bag")


# --- bind_count_to_dimension ---------------------------------------------

READ = {"distance", "time"}


def test_direct_hit_binds_by_the_units_own_dimension_unscaled(reg):
    assert bind_count_to_dimension(
        reg, value=100.0, lemma="meter", qualifier=None, label=None, read_names=READ,
    ) == ("distance", 100.0)


def test_qualifier_binds_when_the_noun_itself_is_not_a_unit(reg):
    # "a 2 kg object": lemma 'object' is no unit; the qualifier carries it.
    assert bind_count_to_dimension(
        reg, value=2.0, lemma="object", qualifier="kilogram", label=None, read_names=READ,
    ) is None  # mass is not a READ dimension here — bindable != read
    assert bind_count_to_dimension(
        reg,
        value=100.0, lemma="object", qualifier="centimeter", label=None, read_names=READ,
    ) == ("distance", pytest.approx(1.0))


def test_scale_to_canonical_reaches_the_dimension_through_declared_pairs(reg):
    # Preserve the historical plural canonical time identity. The singular
    # duration noun reaches it through an explicit conversion below.
    assert bind_count_to_dimension(
        reg, value=2.0, lemma="seconds", qualifier=None, label=None, read_names=READ,
    ) == ("time", 2.0)
    # The singular duration noun now has an explicit conversion to the
    # historical plural canonical identity; no inflection is guessed.
    assert bind_count_to_dimension(
        reg, value=2.0, lemma="second", qualifier=None, label=None, read_names=READ,
    ) == ("time", 2.0)



def test_a_singular_declared_pair_scales_a_singular_lemma(reg):
    # 'foot' is not a difg dimension unit, but the declared foot->meter
    # pair reaches the distance dimension's canonical unit.
    assert bind_count_to_dimension(
        reg, value=3.0, lemma="foot", qualifier=None, label=None, read_names=READ,
    ) == ("distance", pytest.approx(0.9144))


def test_ambiguity_refuses_to_bind():
    reg = SimpleNamespace(
        unit_dimension={"stride": "distance", "tick": "time"},
        conversions={
            ("span", "stride"): 2.0,
            ("span", "tick"): 3.0,
        },
        affine_scales={},
    )
    # The invented unit is known and binds when only one reachable dimension
    # is read by the formula.
    assert bind_count_to_dimension(
        reg,
        value=7.0,
        lemma="span",
        qualifier=None,
        label=None,
        read_names={"distance"},
    ) == ("distance", 14.0)
    # The same unit reaches two canonical dimensions when both are read, so
    # the binder must refuse rather than choose one.
    assert bind_count_to_dimension(
        reg,
        value=7.0,
        lemma="span",
        qualifier=None,
        label=None,
        read_names=READ,
    ) is None


def test_an_unknown_unit_binds_nothing(reg):
    assert bind_count_to_dimension(
        reg, value=7.0, lemma="furlong", qualifier=None, label=None, read_names=READ,
    ) is None


def test_a_dimension_the_expression_does_not_reference_is_not_a_reading(reg):
    # 'meter' maps to distance, but this expression reads only time:
    # bindable != read.
    assert bind_count_to_dimension(
        reg, value=100.0, lemma="meter", qualifier=None, label=None, read_names={"time"},
    ) is None


def test_affine_label_reaches_a_temperature_dimension():
    from pathlib import Path

    greg = load_project(Path("projects/gsm8k")).registry
    bound = bind_count_to_dimension(
        greg,
        value=100.0, lemma="degree", qualifier=None, label="celsius",
        read_names={"temperature"},
    )
    # (100 + 273.15) * 1 -> kelvin per the affine table.
    assert bound == ("temperature", pytest.approx(373.15))
