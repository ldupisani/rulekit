"""Cross-domain composition reuse and boundaries, using invented examples."""

from pathlib import Path
from types import SimpleNamespace

import pytest

from rulekit.data.project import load_project
from rulekit.kernel.engine import solve
from rulekit.kernel.evaluate import ArithmeticLog
from rulekit.kernel.affine_graph import dependency_graph, AffineError
from rulekit.kernel.resource_equations import FractionalAllocation, FractionBasis
from rulekit.kernel.rate_calculation import apply_ratio
from rulekit.kernel.composition_evidence import finish_batch_answer


@pytest.fixture(scope="module")
def reg():
    return load_project(Path("projects/curated")).registry


def number(reg, text, expected):
    got = solve(text, reg)
    assert got.answer.committed, got.answer
    assert got.value == pytest.approx(expected)
    return got


@pytest.mark.parametrize(
    "first,second,unit", [("resin", "clay", "kilograms"), ("wire", "wood", "meters")]
)
def test_nonculinary_component_dependencies(reg, first, second, unit):
    text = (
        f"Nora needs 4 {unit} of {first} and twice as many {unit} of {second} as {unit} of {first}. "
        f"Calculate the combined total number of {unit} of {first} and {unit} of {second} that she needs."
    )
    result = number(reg, text, 12)
    assert not result.deficiencies()
    assert not solve(
        text.replace(f"as {unit} of {first}", "as kilograms of metal"), reg
    ).answer.committed


@pytest.mark.parametrize("whole", ["panels", "sheets", "rolls"])
def test_nonfood_component_depletion(reg, whole):
    text = (
        f"Nora and Iris each buy {whole} cut into 8 pieces. "
        f"Nora and Iris use 50% of their {whole}. How many pieces are left?"
    )
    result = number(reg, text, 8)
    assert not result.deficiencies()
    assert not solve(text.replace("use 50%", "eat 50%"), reg).answer.committed
    assert not solve(text.replace("left?", "left uneaten?"), reg).answer.committed
    assert not solve(
        text.replace("Nora and Iris use", "Nora and Theo use"), reg
    ).answer.committed


@pytest.mark.parametrize(
    "ask,expected",
    [
        ("How much does the mug cost?", 8),
        ("How much did Nora pay for 2 mugs?", 16),
        ("How many mugs can Nora buy with $24?", 3),
    ],
)
def test_agreeing_price_restatements(reg, ask, expected):
    number(reg, "A mug costs $8. Mugs are $8 each. " + ask, expected)
    assert not solve("A mug costs $8. Mugs are $9 each. " + ask, reg).answer.committed
    assert not solve("A mug costs $8. Mugs are £8 each. " + ask, reg).answer.committed


@pytest.mark.parametrize("item", ["mug", "pencil"])
def test_equivalent_denominations_are_not_conflicting_quotes(reg, item):
    text = (
        f"A {item} costs $2. {item}s are 200 cents each. How much does the {item} cost?"
    )
    number(reg, text, 2)
    assert not solve(text.replace("200 cents", "201 cents"), reg).answer.committed


@pytest.mark.parametrize(
    "text,value",
    [
        ("How much to fence a 2 meter by 300 centimeter yard at $4 per meter?", 40),
        ("How much to fence a 2 meter by 3 meter yard at $4 per meter?", 40),
        ("How much to fence a 2 by 3 meter yard at $4 per meter plus 25% tax?", 50),
    ],
)
def test_geometric_quote_uses_physical_units(reg, text, value):
    number(reg, text, value)
    assert not solve(text.replace("per meter", "per kilogram"), reg).answer.committed


def test_directed_graph_keeps_scope_and_requires_an_anchored_dag():
    log = ArithmeticLog()
    a, b, c = ("job A", "metal"), ("job A", "resin"), ("job B", "resin")
    graph = dependency_graph([(a, 4), (c, 99)], [(b, a, 2, 0)], log)
    assert graph.value(b) == 8 and graph.value(c) == 99
    assert dependency_graph([(a, 4)], [(b, a, 0, 0)], log).value(b) == 0
    with pytest.raises(AffineError):
        dependency_graph([], [(b, a, 0, 0)], log)
    with pytest.raises(AffineError):
        dependency_graph([], [(a, b, 2, 0), (b, a, 0.5, 0)], log)


def test_fraction_basis_controls_the_remaining_amount():
    opening = FractionalAllocation(100, ArithmeticLog())
    opening.allocate(0.5, FractionBasis.OPENING, source="test")
    opening.allocate(0.25, FractionBasis.OPENING, source="test")
    assert opening.balance == 25
    remainder = FractionalAllocation(100, ArithmeticLog())
    remainder.allocate(0.5, FractionBasis.OPENING, source="test")
    remainder.allocate(0.25, FractionBasis.REMAINDER, source="test")
    assert remainder.balance == 37.5
    with pytest.raises(ValueError):
        remainder.allocate(0.5, None, source="test")
    with pytest.raises(ValueError):
        opening.allocate(0.5, FractionBasis.OPENING, source="test")


@pytest.mark.parametrize(
    "num,den,amount,expected", [(3, 2, 10, 15), (0, 2, 10, 0), (3, 0, 10, None)]
)
def test_explicit_ratio_retains_both_operands(num, den, amount, expected):
    log = ArithmeticLog()
    assert apply_ratio(num, den, amount, log, source="test") == expected
    if expected is not None:
        assert log.entries


def test_shared_composition_finalizer_rejects_nonfinite_values():
    ctx = SimpleNamespace(log=ArithmeticLog())
    for value in (None, float("inf"), float("nan")):
        got = finish_batch_answer(ctx, [], value, "test")
        assert got.kind == "decline"
        assert got.reason == "the calculated result must be finite"


def test_recipient_roles_do_not_imply_intentional_actors(reg):
    for noun in ("robot", "tank", "company", "child"):
        assert reg.word_in_category(noun, "allocation_participant")
    assert not reg.word_in_category("tank", "allocation_initiator")
    assert not reg.word_in_category("robot", "person")


def test_shape_costing_reuses_inherited_formula_bindings(reg):
    from math import pi

    result = number(
        reg,
        "How much to carpet a circle with radius 2 meters at $5 per square meter?",
        20 * pi,
    )
    assert not result.deficiencies()
    result = number(
        reg, "How much to tile a square of side 3 meters at $2 per square meter?", 18
    )
    assert not result.deficiencies()
    assert not solve(
        "How much to carpet a circle with side 2 meters at $5 per square meter?", reg
    ).answer.committed
    assert not solve(
        "How much to carpet a circle with radius 2 meters at $5 per meter?", reg
    ).answer.committed


@pytest.mark.parametrize(
    "query,slots,reason",
    [
        (
            {"shape": "circle", "op": "perimeter"},
            {},
            "costing needs a declared shape property",
        ),
        ({"shape": "circle"}, {}, "the dimensions do not identify the priced shape"),
        (
            {"dim1": "length", "val1": 2, "dim2": "length", "val2": 3},
            {},
            "each geometry parameter must be stated once",
        ),
        (
            {},
            {"d1": {"lemma": "kilogram", "value_kind": "count"}},
            "shape dimensions need compatible length units",
        ),
        (
            {},
            {"d1": {"lemma": "cup", "qualifier": "meter", "value_kind": "count"}},
            "the measured site needs an explicit costing role",
        ),
        (
            {},
            {"d1": {"lemma": "meter", "qualifier": "red", "value_kind": "count"}},
            "the geometric dimension has an unread restriction",
        ),
        (
            {"dim1": "height", "val1": 2, "dim2": "width", "val2": 3},
            {},
            "the priced property needs compatible dimensions",
        ),
        (
            {
                "dim1": "length",
                "val1": 2,
                "dim2": "width",
                "val2": 3,
                "dim3": "height",
                "val3": 4,
            },
            {"d1": {"lemma": "meter", "value_kind": "count"}},
            "all dimensions need a stated unit basis",
        ),
        (
            {},
            {"rate": {"lemma": "apple"}},
            "a cost quote needs a concrete monetary denomination",
        ),
    ],
)
def test_costing_defensive_dimensional_boundaries(reg, query, slots, reason):
    from rulekit.kernel.consumers import ConsumerContext, CONSUMERS

    q = {"op": "area", "d1": 2, "d2": 3, "rate": 4, **query}
    match = SimpleNamespace(
        slots={
            name: SimpleNamespace(features=features) for name, features in slots.items()
        }
    )
    got = CONSUMERS["measure-cost"](
        ConsumerContext(q, None, None, reg, ArithmeticLog(), match, None)
    )
    assert got.kind == "decline"
    assert got.reason.startswith(reason)


def test_closed_account_does_not_merge_unscoped_repeated_prices(reg):
    from rulekit.kernel.consumers import ConsumerContext, CONSUMERS
    from rulekit.kernel.facts import FactStore
    from rulekit.kernel.model import Price, Provenance, ResourceBalance

    p = Provenance(source="synthetic", sentence=0)
    store = FactStore(
        facts=[
            Price(p, "pen", 3, verb="cost"),
            Price(p, "pen", 3, verb="be"),
            ResourceBalance(p, "nora", "budget", "opening", "dollar", 30),
        ]
    )
    got = CONSUMERS["capacity"](
        ConsumerContext(
            {"entity": "nora", "item": "pen"},
            None,
            store,
            reg,
            ArithmeticLog(),
            None,
            None,
        )
    )
    assert got.kind == "decline"
    assert got.reason == "a scoped account requires one explicit unit-price source"


def test_explicit_allocation_recipients_can_be_nonliving(reg):
    text = (
        "The company shared money between 2 robots Nora and Iris. "
        "Nora received $12. Iris received $8. How much money did the company share?"
    )
    number(reg, text, 20)
    assert not solve(text.replace("company", "tank"), reg).answer.committed


def test_culinary_modifiers_do_not_spread_to_material_wholes(reg):
    for adjective in ("personal", "pan", "cookie"):
        assert reg.attribute_applies_to(adjective, "pizza")
        assert not reg.attribute_applies_to(adjective, "panel")


@pytest.mark.parametrize("item", ["sheets", "panels"])
def test_component_depletion_keeps_the_ordinary_stock_route(reg, item):
    text = f"Nora bought 10 {item}. Nora used half of the {item}. How many {item} does Nora have?"
    number(reg, text, 5)
    assert not solve(text.replace("Nora used", "Iris used"), reg).answer.committed


def test_scoped_fraction_does_not_erase_its_material_qualifier(reg):
    text = "Nora bought 10 red sheets. Nora used half of the red sheets. How many red sheets does Nora have?"
    number(reg, text, 5)
    assert not solve(text.replace("of the red", "of the blue"), reg).answer.committed
