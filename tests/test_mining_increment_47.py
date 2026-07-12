"""Mining candidate unit-parenthetical-asks: parenthetical unit-qualified
questions (", in dollars," / ", in minutes," inserted mid-question, e.g.
"How much money, in dollars, does WHO have?"). An optional `[in, req_unit]`
group is added to ask/how-much-noun-entity and ask/how-much-money-entity-
left — the surrounding commas are already globally-skippable punct, so the
group need only match the literal 'in' plus a structural noun slot, no new
vocabulary. When bound, answer.py's single-entity and money-left consumers
check the bound unit against the measure they actually resolve and decline
on a mismatch (asked one unit, facts state a different, non-interchangeable
one) rather than silently answering in the wrong unit. Synthetic only."""

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


def test_parenthetical_unit_on_bare_holding(full_registry):
    r = solve(
        "Priya has 8 dollars. Omar gives her another 5 dollars. "
        "How much money, in dollars, does Priya have?",
        full_registry,
    )
    assert r.answer.value == 13


def test_parenthetical_unit_matches_ask_without_it(full_registry):
    # the identical question minus the parenthetical must answer the same
    with_unit = solve(
        "Priya has 8 dollars. Omar gives her another 5 dollars. "
        "How much money, in dollars, does Priya have?",
        full_registry,
    )
    without_unit = solve(
        "Priya has 8 dollars. Omar gives her another 5 dollars. "
        "How much money does Priya have?",
        full_registry,
    )
    assert with_unit.answer.value == without_unit.answer.value == 13


def test_parenthetical_unit_on_money_left(full_registry):
    r = solve(
        "Wanda has $60. She buys a toy for $20 and a book for $15. "
        "How much money, in dollars, does Wanda have left?",
        full_registry,
    )
    assert r.answer.value == 25


def test_mismatched_unit_declines(full_registry):
    # facts are stated in a DIFFERENT, non-interchangeable unit (coins,
    # not currency) from the one bound in the parenthetical — this must
    # decline rather than silently answer in the wrong denomination
    r = solve(
        "Priya has 8 quarters. Omar gives her 5 more quarters. "
        "How much money, in dollars, does Priya have?",
        full_registry,
    )
    assert r.answer.kind == "decline"
