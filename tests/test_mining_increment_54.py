"""Mining candidate named-pair-combined: named-pair combined holdings asks
— a named pair of holders joined by 'and', with an aggregate tail
(together/in total/altogether), asking for the combined amount of some
measure the two of them hold. Previously declined because the existing
combined asks only bind a pronoun subject ('they'/'we').

Two new ask ids — ask/how-many-combined-named and ask/how-much-combined-
named — mirror ask/how-many-combined/ask/how-much-combined's shape (item,
aux, aggregate tail) but bind the two named holders DIRECTLY via `a`/`b`
slots joined by 'and', the same named-pair binding ask/what-is-the-
difference-named already uses. Both route to the EXISTING 'combined'
consumer (answer.py's `_combined_holder_totals`), additively extended to
sum EXACTLY the two named holders when `a`/`b` are bound — never the
enumerate-all-holders fallback the pronoun form ('they'/'we') still uses
unchanged, so a third, unnamed holder mentioned elsewhere in the passage
can never silently inflate the named pair's sum.

Synthetic only."""

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


def test_named_pair_how_many_together(full_registry):
    r = solve(
        "Ravi has 18 buttons. Tomas has 7 buttons. "
        "How many buttons do Ravi and Tomas have together?",
        full_registry,
    )
    assert r.answer.value == 25


def test_named_pair_how_many_singular_does_remains_consume_compatible(full_registry):
    # The generator is stricter and never emits singular `does` for a
    # coordinated subject. Reading remains tolerant because established
    # corpus questions use this non-standard agreement while preserving an
    # otherwise unambiguous quantitative interpretation.
    r = solve(
        "Ravi has 18 buttons. Tomas has 7 buttons. "
        "How many buttons does Ravi and Tomas have in total?",
        full_registry,
    )
    assert r.answer.value == 25


def test_named_pair_how_much_altogether(full_registry):
    r = solve(
        "Ravi has 18 dollars. Tomas has 7 dollars. "
        "How much money do Ravi and Tomas have altogether?",
        full_registry,
    )
    assert r.answer.value == 25


def test_named_pair_ignores_unnamed_third_holder(full_registry):
    # a third holder of the same measure, mentioned elsewhere in the
    # passage, must NEVER be silently folded into a named pair's sum —
    # the enumerate-all-holders fallback is only for the pronoun form
    r = solve(
        "Ravi has 18 buttons. Tomas has 7 buttons. Greta has 200 buttons. "
        "How many buttons do Ravi and Tomas have together?",
        full_registry,
    )
    assert r.answer.value == 25


def test_named_pair_declines_when_one_side_unresolvable(full_registry):
    # only one of the two named entities has a resolvable total — a
    # confident-wrong here would be worse than a decline
    r = solve(
        "Ravi has 18 buttons. "
        "How many buttons do Ravi and Tomas have together?",
        full_registry,
    )
    assert r.answer.kind == "decline"


def test_pronoun_form_still_enumerates_all_holders(full_registry):
    # decline-safety / regression guard: the pre-existing pronoun path
    # (ask/how-many-combined) must be completely unchanged — it still
    # enumerates every holder of the measure, so three holders sum to 225
    r = solve(
        "Ravi has 18 buttons. Tomas has 7 buttons. Greta has 200 buttons. "
        "How many buttons do they have altogether?",
        full_registry,
    )
    assert r.answer.value == 225
