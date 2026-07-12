"""Mining candidate entityless-total-recut: totality-marked entity-less
there-asks (multi-holder sum), re-cut.

ask/how-many-there-combined is a NEW ask id, the totality-marked sibling of
ask/how-many-there: "how many X are/were there in total/altogether/together/
combined?" requires a trailing aggregate marker and routes to the SAME
'combined' consumer (answer.py) the pronoun/named-pair combined asks already
use, summing every holder of the measure — the marker is explicit license to
do what the bare "how many X are there?" form (unique-entity consumer, still
byte-unchanged) correctly refuses on 2+ holders.

This is a re-cut of the parked candidate entityless-total-there-asks: the
mechanism is the same, but the bare `world` scene-holder exclusion is no
longer a Python-side boolean constant. answer.py's `_combined_holder_totals`
gained an opt-in `exclude_entity` parameter (default None, every pre-existing
caller unchanged) that takes an ENTITY NAME, not a flag — the ask alone
supplies that name as pack data (`exclude_entity: world` in its own
`resolves` block), so the literal `world` lives only in YAML (both in the
existential-premise-bare rule that produces the fact and in this ask's
resolves block), never as a hardcoded string inside answer.py itself.

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


def test_two_named_holders_in_total(full_registry):
    r = solve(
        "Priya has 14 marbles and Wendell has 9 marbles. "
        "How many marbles are there in total?",
        full_registry,
    )
    assert r.answer.value == 23


def test_two_named_holders_altogether(full_registry):
    r = solve(
        "Priya has 14 marbles and Wendell has 9 marbles. "
        "How many marbles are there altogether?",
        full_registry,
    )
    assert r.answer.value == 23


def test_two_named_holders_combined_literal(full_registry):
    r = solve(
        "Priya has 14 marbles and Wendell has 9 marbles. "
        "How many marbles are there combined?",
        full_registry,
    )
    assert r.answer.value == 23


def test_bare_there_ask_without_marker_still_declines(full_registry):
    # ask/how-many-there itself is unchanged: 2 holders, no totality
    # marker -> decline (never a silent partial read of one holder)
    r = solve(
        "Priya has 14 marbles and Wendell has 9 marbles. "
        "How many marbles are there?",
        full_registry,
    )
    assert r.answer.kind == "decline"


def test_single_holder_with_marker_declines(full_registry):
    # a totality marker over exactly one holder still asserts plurality --
    # only one holder in play means decline, not a one-entity "sum"
    r = solve(
        "Priya has 14 marbles. How many marbles are there in total?",
        full_registry,
    )
    assert r.answer.kind == "decline"


def test_bare_existential_world_holder_not_summed_with_named_entity(full_registry):
    # "There are N X" with no location creates a bare `world` scene-holder
    # (arithmetic/existential-premise-bare) -- summing it alongside a real
    # named holder would double-count a scene-level restatement as an
    # independent third holding. Must decline, never guess. This is the
    # exact confident-wrong the parked candidate's holdout gate caught;
    # `exclude_entity: world` (pack data on this ask alone) prevents it.
    r = solve(
        "Wendell has 9 marbles. There are 14 marbles. "
        "How many marbles are there in total?",
        full_registry,
    )
    assert r.answer.kind == "decline"


def test_pre_existing_combined_ask_still_sums_world_holder(full_registry):
    # `exclude_entity` defaults to None everywhere else: a PRE-EXISTING
    # combined ask (pronoun form, no `exclude_entity` binding) must still
    # be free to sum a bare `world` holder alongside a named one -- this
    # increment must not narrow any other ask's behaviour.
    r = solve(
        "Wendell has 9 marbles. There are 14 marbles. "
        "How many marbles do they have combined?",
        full_registry,
    )
    assert r.answer.value == 23
