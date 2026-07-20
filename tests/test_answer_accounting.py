"""The answer-accounting guard: FACTS -> ANSWER (the other half of value accounting).

SYNTHETIC ONLY (constitution rule 3). No GSM8K or ASDiv string appears here.

WHY IT EXISTS. `value-accounting` checks NUMBERS -> FACTS: every stated value must
reach a fact. It never checks that the ANSWER then USED those facts, so a fact can
be extracted perfectly and silently dropped by the consumer with nothing objecting.
GSM8K could not reveal the hole — its ask shapes happen to consume everything. A
different corpus of the SAME TASK (ASDiv, different authors) exposed it as 9
confident wrongs out of 46 commits: 80.4% precision against GSM8K's 100%.

The failure shape, in synthetic form: a holder owns several QUALIFIED quantities of
one measure ("15 brown bears, 24 white bears, 27 black bears") plus a bare one, the
ask resolves the bare key, and the engine confidently returns ONE of them.
"""

from pathlib import Path

import pytest

from rulekit.data.project import load_project
from rulekit.kernel.engine import solve


@pytest.fixture(scope="module")
def reg():
    return load_project(Path("projects/gsm8k")).registry


def test_qualified_parts_are_summed_never_partially_committed(reg):
    """The core case. The holder owns three colour-qualified quantities of one
    measure and the ask names the bare measure. Committing ANY SINGLE ONE of
    them is the confident wrong this guard exists to stop.

    ⚠ THIS TEST USED TO ASSERT A DECLINE, and it was passing for a reason
    DOWNSTREAM OF A BUG. The qualifier split was pairwise, so an odd-length
    part list stranded the last conjunct under the BARE key ('hat'=4); the
    guard then correctly saw two unused qualified siblings and declined. With
    the split made order-independent all three parts are keyed, the bare ask
    sums them, and 9 is simply the right answer — a decline here would now be
    a coverage loss, not a safety win.

    The guard's real concern is UNCHANGED and is asserted directly: no single
    part may ever be committed. `test_a_stated_whole_over_parts_still_
    declines` keeps the shape this file's docstring actually describes."""
    r = solve(
        "Ann has 2 red hats, 3 blue hats, and 4 green hats. How many hats does Ann have?",
        reg, tracing=False,
    )
    assert r.value == 9.0
    assert r.value not in (2.0, 3.0, 4.0), "committed a single part"


def test_a_stated_whole_over_parts_still_declines(reg):
    """The shape this file's docstring names — qualified siblings PLUS a bare
    holding of the same measure. Which is the whole and which the parts is
    genuinely ambiguous, so the guard must still refuse."""
    r = solve(
        "Ann has 2 red hats, 3 blue hats and 4 green hats. Ann has 20 hats. "
        "How many hats does Ann have?",
        reg, tracing=False,
    )
    assert not r.answer.committed, f"committed {r.answer.value!r} on a partial reading"
    assert "answer-accounting" in (r.answer.reason or "")


def test_a_complete_reading_still_commits(reg):
    """The guard must not simply suppress everything. One holder, one quantity,
    fully consumed — commits exactly as before."""
    r = solve("Ann has 5 hats. How many hats does Ann have?", reg, tracing=False)
    assert r.answer.committed
    assert r.answer.value == 5.0


def test_a_different_holders_quantity_is_not_a_partial_reading(reg):
    """SCOPED TO THE ANSWERING HOLDER, and this pins why.

    A measure-scoped first cut BROKE 4 correct items: asked about one person, it
    vetoed because ANOTHER person's quantity of the same measure went unused. A
    sibling that belongs to someone else is not an ignored fact — it is simply not
    what was asked. Narrowing to the holder is what made the guard land at 0 BROKE.
    """
    r = solve(
        "Ann has 5 hats. Bob has 3 hats. How many hats does Ann have?",
        reg, tracing=False,
    )
    assert r.answer.committed, (r.answer.reason or "")
    assert r.answer.value == 5.0
