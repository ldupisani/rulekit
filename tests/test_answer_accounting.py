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


def test_partial_reading_over_qualified_siblings_declines(reg):
    """The core case. The holder owns three colour-qualified quantities of one
    measure; the ask names the bare measure. Committing ANY single one of them is a
    confident wrong — the engine must decline instead."""
    r = solve(
        "Ann has 2 red hats, 3 blue hats, and 4 green hats. How many hats does Ann have?",
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
