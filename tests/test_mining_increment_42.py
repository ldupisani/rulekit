"""Mining increment 42: wh-difference asks: "what is the difference (in/between the number of)
ITEM NAME and NAME have?" and its pronoun mirror ("...ITEM they have?"),
routed to the EXISTING 'difference' consumer already shared with
ask/how-many-more and ask/how-much-noun-more-than.

The named-pair form is pure YAML (a/b bind directly, same as the existing
asks). The pronoun form binds no pair, so the consumer resolves it itself
from the FACTS: mirrors the 'combined' consumer's holder enumeration, but a
difference is inherently BINARY — it commits only when EXACTLY two entities
hold the measure, and declines otherwise (the established exactly-one/
exactly-two-or-decline discipline). Synthetic only."""

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


def test_named_pair_difference(full_registry):
    r = solve(
        "Farid has 12 seashells. Mateus has 5 seashells. "
        "What is the difference in the number of seashells Farid and Mateus have?",
        full_registry,
    )
    assert r.answer.value == 7


def test_named_pair_difference_between_wording(full_registry):
    r = solve(
        "Farid has 12 seashells. Mateus has 5 seashells. "
        "What is the difference between the number of seashells Farid and Mateus have?",
        full_registry,
    )
    assert r.answer.value == 7


def test_pronoun_form_resolves_exactly_two_holders(full_registry):
    r = solve(
        "Farid has 12 seashells. Mateus has 5 seashells. "
        "What is the difference in the number of seashells they have?",
        full_registry,
    )
    assert r.answer.value == 7


def test_event_verb_activity_totals(full_registry):
    # a non-state verb ("sold") takes activity totals, never the signed
    # holdings fold — mirrors the existing difference consumer's own branch
    r = solve(
        "Farid sold 9 seashells. Mateus sold 4 seashells. "
        "What is the difference in the number of seashells Farid and Mateus sold?",
        full_registry,
    )
    assert r.answer.value == 5


def test_pronoun_form_declines_with_three_holders(full_registry):
    # a difference is inherently BINARY: three holders of the same measure
    # is genuinely ambiguous about which pair the pronoun means — decline,
    # never guess a pair
    r = solve(
        "Farid has 12 seashells. Mateus has 5 seashells. Ingrid has 3 seashells. "
        "What is the difference in the number of seashells they have?",
        full_registry,
    )
    assert r.answer.kind == "decline"


def test_named_pair_declines_when_one_side_unresolvable(full_registry):
    # only one of the two named entities has a resolvable seashell total —
    # a confident-wrong here would be worse than a decline
    r = solve(
        "Farid has 12 seashells. "
        "What is the difference in the number of seashells Farid and Mateus have?",
        full_registry,
    )
    assert r.answer.kind == "decline"
