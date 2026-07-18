"""Molar mass (difg): a chemical formula is ONE unit, summed from pack data.

SYNTHETIC ONLY (constitution rule 3): invented formulas where possible, and
never a difg CASE string.

THE FUSION IS IN `condense`, NOT THE TOKENIZER, and that is the whole design.
"CO2" and "MP3" are structurally identical — capitals then a digit — so only
the ELEMENT TABLE separates a compound from an MP3 player, and the tokenizer
has no registry. A tokenizer-level pattern was tried first and it fused 'MP3',
costing two GSM8K items.
"""

from pathlib import Path

import pytest

from rulekit.data.project import load_project
from rulekit.kernel import condense, numbers, senses, tokenize
from rulekit.kernel.engine import solve


@pytest.fixture(scope="module")
def reg():
    return load_project(Path("projects/difg")).registry


def _units(text, reg):
    r = tokenize.tokenize(text)
    numbers.annotate_numbers(r, reg)
    senses.annotate_senses(r, reg)
    condense.condense(r, reg)
    return r.units


def _formulas(text, reg):
    return [u.features.get("components") for u in _units(text, reg)
            if u.features.get("value_kind") == "formula"]


# --- the reader ------------------------------------------------------------


@pytest.mark.parametrize("text", ["CO2", "NH3", "CaCO3", "NaCl"])
def test_a_formula_becomes_one_unit(text, reg):
    assert _formulas(f"the {text} sample", reg) == [text]


def test_a_multi_capital_group_still_fuses(reg):
    # 'SO' tokenizes as one two-capital unit, so the run is reassembled from
    # SURFACES and validated as a whole rather than symbol by symbol
    assert _formulas("the H2SO4 sample", reg) == ["H2SO4"]


def test_a_formula_carries_no_scalar(reg):
    # same contract as a date or a coordinate tuple: not a quantity, so
    # value-accounting must never demand it be consumed as one
    u = next(u for u in _units("the CO2 sample", reg)
             if u.features.get("value_kind") == "formula")
    assert "value" not in u.features


# --- THE REFUSALS: what the element table and the lexicon keep out ---------


def test_an_mp3_player_is_not_a_molecule(reg):
    # the case that cost two GSM8K items when this lived in the tokenizer.
    # 'M' is not an element, so the run fails validation.
    assert _formulas("an MP3 player for 120 euros", reg) == []


@pytest.mark.parametrize("word", ["He", "I", "As", "At", "No", "In", "Be"])
def test_element_symbols_that_are_english_words_stay_words(word, reg):
    # every one of these is a real symbol AND a lexicon word. A LONE unit must
    # be senseless to fuse, so the lexicon wins.
    assert _formulas(f"{word} walked home", reg) == []


def test_a_lexicon_word_may_join_a_run_that_has_a_SUBSCRIPT(reg):
    # 'so' is a conjunction, but "H2SO4" carries a digit — the structural
    # evidence that a formula is meant. That asymmetry is the contract.
    assert _formulas("the H2SO4 sample", reg) == ["H2SO4"]
    assert _formulas("So Anna left", reg) == []


def test_an_unknown_symbol_blocks_the_whole_run(reg):
    # 'Xx' is not in the table, so nothing fuses even though the shape fits
    assert _formulas("the Xx2O sample", reg) == []


def test_a_project_with_no_element_table_cannot_reach_the_pass():
    # the pass is DATA-gated: gsm8k loads difg-mined so it does have the table,
    # but a pack set without one must be untouched
    from rulekit.data.packs import load_packs
    from rulekit.data.registry import compile_registry

    root = Path(__file__).resolve().parents[1]
    bare = compile_registry(load_packs([root / "packs/core-english"]))
    assert not bare.atomic_masses
    assert _formulas("the CO2 sample", bare) == []


# --- the sum ---------------------------------------------------------------


@pytest.mark.parametrize(
    "formula, want",
    [
        ("CO2", 12.011 + 2 * 15.999),
        ("NH3", 14.007 + 3 * 1.008),
        ("CaCO3", 40.078 + 12.011 + 3 * 15.999),
    ],
)
def test_molar_mass_sums_the_table(reg, formula, want):
    got = solve(f"What is the molar mass of {formula}?", reg).answer.value
    assert got == pytest.approx(want)


def test_an_implicit_subscript_is_one(reg):
    assert solve("What is the molar mass of NaCl?", reg).answer.value == (
        pytest.approx(22.990 + 35.45)
    )


def test_the_atomic_masses_are_pack_data(reg):
    # constitution rule 1 — no element is named in the consumer. If this table
    # ever moves into Python, this is the test that should start failing.
    assert reg.atomic_masses["H"] == 1.008
    assert reg.atomic_masses["Na"] == 22.990


# --- quantities derived from the molar mass --------------------------------
# SYNTHETIC amounts throughout (never difg's 36 g / 3 mol / 2 mol).


def test_moles_from_grams(reg):
    # 90.075 g of H2O is 5 mol (molar mass 18.015)
    assert solve("How many moles are in 90.075 grams of H2O?", reg).answer.value == (
        pytest.approx(5.0)
    )


def test_cost_of_moles(reg):
    # 4 mol NaCl = 4 * 58.44 g = 233.76 g, at $2/g
    assert solve(
        "What is the cost of 4 moles of NaCl at $2 per gram?", reg
    ).answer.value == pytest.approx(467.52)


def test_weight_of_moles(reg):
    # 5 mol H2O = 90.075 g = 0.090075 kg, x 9.8
    assert solve("What is the weight of 5 moles of H2O?", reg).answer.value == (
        pytest.approx(0.090075 * 9.8)
    )


def test_no_constant_lives_in_the_consumer(reg):
    # THE contract for the weight op: the gram->kilogram factor and g both come
    # from pack tables the engine already had. If either moved into Python this
    # test is what should start failing.
    assert reg.conversions[("gram", "kilogram")] == pytest.approx(0.001)
    assert reg.quantity_formulas["weight"] == "mass * 9.8"


def test_the_derived_ops_still_decline_on_an_unknown_symbol(reg):
    assert solve(
        "How many moles are in 90 grams of Xx2O?", reg
    ).answer.kind == "decline"


def test_the_plain_molar_mass_ask_is_unaffected(reg):
    # the derived ops share one consumer via a structural opcode; the default
    # op must keep answering the bare question
    assert solve("What is the molar mass of CO2", reg).answer.value == (
        pytest.approx(12.011 + 2 * 15.999)
    )


def test_the_mole_SINGULAR_is_deliberately_unknown(reg):
    # 'mole' the ANIMAL appears in ASDiv; admitting the singular would change
    # how those items read, and every chemistry question says "moles"
    assert "mole" not in reg.lexicon
    assert "moles" in reg.lexicon
