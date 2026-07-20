"""`FactStore.admit`'s measure-qualifier split is order-independent.

SYNTHETIC ONLY (constitution rule 3) — invented scenarios, never a benchmark
string. Nouns and adjectives are lexicon words (an unknown one mints no fact,
so the test would pass or fail for reasons unrelated to the split).

WHY IT EXISTS. The qualifier split fired only on a KEY COLLISION, and
re-keying both sides REMOVED the bare key they collided on. The third
qualified sibling then found nothing to collide with and was stored BARE — a
SILENTLY DROPPED QUALIFIER, not a decline:

    "15 brown buttons, 24 white buttons and 27 black buttons"
      brown -> stored bare 'button'
      white -> COLLIDES -> both re-keyed (button[brown], button[white])
      black -> no bare 'button' remains -> stored bare      <-- the bug

⚠ THE DEFECT WAS PARITY, and that is what made it diagnosable: n=3 and n=5
stranded the last conjunct while n=4 and n=6 were clean, because the 4th
collides with the stranded 3rd and rescues it. `test_every_arity_splits`
pins all four counts — a fix that only handled 3 would pass a 3-only test
and still strand the 5th.

The fix makes the keying ORDER-INDEPENDENT rather than adding another
pairwise case, and copies the split's own `no bare sibling` condition
verbatim: a stated unqualified holding IS the whole, so splitting alongside
it would misread the whole as another part
(`test_a_stated_whole_still_blocks_the_split`).
"""

from pathlib import Path

import pytest

from rulekit.data.project import load_project
from rulekit.kernel.engine import solve
from rulekit.kernel.model import Quantity


@pytest.fixture(scope="module")
def reg():
    return load_project(Path("projects/gsm8k")).registry


def _measures(text, reg):
    return [q.measure for q in solve(text, reg).store.by_kind(Quantity)]


@pytest.mark.parametrize(
    "text, expected",
    [
        ("Ana has 15 brown bears and 24 white bears.", 2),
        ("Ana has 15 brown bears, 24 white bears and 27 black bears.", 3),
        ("Ana has 15 brown bears, 24 white bears, 27 black bears "
         "and 9 red bears.", 4),
        ("Ana has 15 brown bears, 24 white bears, 27 black bears, "
         "9 red bears and 3 green bears.", 5),
    ],
)
def test_every_arity_splits(text, expected, reg):
    """NO arity may strand a bare key — the odd counts are the regression."""
    measures = _measures(text, reg)
    assert "bear" not in measures, f"stranded a bare key: {measures}"
    assert len(measures) == expected
    assert len(set(measures)) == expected  # each qualifier keeps its own key


def test_a_stated_whole_still_blocks_the_split(reg):
    """The split's own guard, inherited verbatim: an unqualified holding IS
    the whole, so the parts must not be re-keyed alongside it and summed."""
    r = solve(
        "Ana has 14 blue bears and 26 purple bears. Ana has 200 bears. "
        "How many bears does Ana have?",
        reg,
    )
    assert r.value != 240.0


def test_a_bare_ask_reads_an_odd_length_part_list(reg):
    """The buyer: with the third conjunct keyed correctly the qualified fold
    sees three parts and a bare ask sums them. This item answered from the
    stranded bare key before."""
    r = solve(
        "Ana has 15 brown buttons, 24 white buttons and 27 black buttons. "
        "How many buttons does Ana have?",
        reg,
    )
    assert r.value == 66.0
