"""`molar-mass` unit tests — the guards extraction made reachable.

Four of this consumer's guards had NO probe in the golden master, and mining
could not produce one: they are unreachable through ordinary input BY DESIGN.
numbers.py validates every symbol against the same table the consumer
re-checks, so "no atomic mass known" cannot fire from text; the ask's rate slot
is `type: counted`, so "a cost needs a numeric rate" cannot either; and the
weight branch's table check cannot fire on a project that loads difg-mined.

They are DEFENSIVE guards, and inside a 3,479-line if-chain there was no way to
call them. That is the argument for the extraction stated as a test: these
tests exist because the consumer is now a function.
"""

from pathlib import Path

import pytest

from rulekit.data.project import load_project
from rulekit.kernel.consumers import CONSUMERS, ConsumerContext

ROOT = Path(__file__).resolve().parents[1]


@pytest.fixture(scope="module")
def reg():
    return load_project(ROOT / "projects" / "difg").registry


def call(reg, **query):
    """Invoke the consumer directly. `store`/`question`/`match`/`ask` are None:
    this consumer reads only `query`, `reg` and `log`, and passing None for the
    rest documents that — if a future edit starts reading them, these tests
    fail loudly rather than silently exercising a different path."""
    from rulekit.kernel.evaluate import ArithmeticLog

    return CONSUMERS["molar-mass"](ConsumerContext(
        query=query, question=None, store=None, reg=reg,
        log=ArithmeticLog(), match=None, ask=None,
    ))


# --- the answering paths, as a control ------------------------------------


def test_molar_mass_of_a_formula(reg):
    got = call(reg, formula="H2O")
    assert got.kind == "number"
    assert got.value == pytest.approx(2 * 1.008 + 15.999)


def test_moles_from_grams(reg):
    got = call(reg, op="moles_from_grams", formula="H2O", amount="36.03")
    assert got.value == pytest.approx(2.0, rel=1e-3)


# --- THE GUARDS: unreachable from text, reachable from here ---------------


def test_an_unknown_symbol_declines(reg):
    # numbers.py would never mint this formula — it validates against the same
    # table. The re-check exists because the reader and the consumer are
    # reached by different paths, and this is the only way to exercise it.
    got = call(reg, formula="Zq2O")
    assert got.kind == "decline"
    assert "no atomic mass known for 'Zq'" in got.reason


def test_an_unreadable_formula_declines(reg):
    got = call(reg, formula="")
    assert got.kind == "decline"
    assert "not a readable formula" in got.reason


def test_a_non_numeric_amount_declines(reg):
    got = call(reg, op="moles_from_grams", formula="H2O", amount="lots")
    assert got.kind == "decline"
    assert "needs a numeric amount" in got.reason


def test_a_non_numeric_rate_declines(reg):
    # the ask binds `rate` with `type: counted`, so text cannot reach this
    got = call(reg, op="cost_of_moles", formula="H2O", amount="2", rate="cheap")
    assert got.kind == "decline"
    assert "a cost needs a numeric rate" in got.reason


def test_an_unsupported_op_declines(reg):
    got = call(reg, op="enthalpy_of_moles", formula="H2O", amount="2")
    assert got.kind == "decline"
    assert "unsupported molar-mass operation" in got.reason


def test_weight_declines_without_the_tables_it_needs(reg):
    # the branch reads the gram->kilogram factor and the `weight` formula from
    # pack data precisely so no constant lives in Python — which means a
    # project declaring neither must decline rather than invent one. Only a
    # direct call can strip them.
    class _Stripped:
        atomic_masses = reg.atomic_masses
        conversions: dict = {}
        quantity_formulas: dict = {}

    got = call(_Stripped(), op="weight_of_moles", formula="H2O", amount="2")
    assert got.kind == "decline"
    assert "weight needs the gram->kilogram conversion" in got.reason


def test_a_broken_weight_formula_declines(reg):
    class _Broken:
        atomic_masses = reg.atomic_masses
        conversions = {("gram", "kilogram"): 0.001}
        quantity_formulas = {"weight": "mass * * 9.8"}

    got = call(_Broken(), op="weight_of_moles", formula="H2O", amount="2")
    assert got.kind == "decline"
    assert "weight formula failed" in got.reason
