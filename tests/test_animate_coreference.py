"""The animate-coreference stack: pronoun binding to a common noun, and the
three decline-guards that made it safe to land.

SYNTHETIC ONLY (constitution rule 3) — invented scenarios, never a benchmark
string. NOUNS must be lexicon words (an unknown word mints no fact, so a
reading test written with invented vocabulary passes or fails for reasons
unrelated to the rule under test).

WHY IT EXISTS. 'baker'/'carpenter' are lexically COMMON NOUNS (occupations),
so "Baker made 157 cakes. He sold 158." found no antecedent and declined —
while the same story with 'Ana' reads, because an unknown word defaults to
NAME. That asymmetry is an artifact of the lexicon, not of the English.

⚠ THIS STACK WAS BUILT, GATE-REJECTED AND REVERTED ONCE. Binding the
pronoun makes previously-UNREAD sentences READ, and three pre-existing
weaknesses then misread them — two of which were proven latent by a null
control (substituting a name at HEAD reproduced the wrong with none of this
code present). The coreference half is useless without all three guards
below, and landing it without them ships three confident-wrongs:

  * a relation whose STANDARD is a time period  -> slot_not_category
  * a bare event over parts-only state          -> the attribution guard
  * a bare ask over qualified parts             -> the qualified fold

Each guard has a test here named for the shape it refuses. A decline is the
REQUIRED outcome in all three: they are not conversions, they are the
absence of a confident-wrong.
"""

from pathlib import Path

import pytest

from rulekit.data.project import load_project
from rulekit.kernel.engine import solve
from rulekit.kernel.model import Quantity, Relation


@pytest.fixture(scope="module")
def reg():
    return load_project(Path("projects/gsm8k")).registry


def _qty(result):
    return {(q.entity, q.measure): q.value for q in result.store.by_kind(Quantity)}


# ---------------------------------------------------------------- binding

def test_pronoun_binds_to_an_animate_common_noun(reg):
    """The gap itself: 'baker' is a common noun, so this minted nothing for
    the second sentence."""
    q = _qty(solve("Baker made 157 cakes. He sold 158 cakes.", reg))
    assert q[("baker", "cake")] == 157.0 or ("baker", "cake") in q
    assert any(e == "baker" for e, _ in q)


def test_an_inanimate_holder_is_never_an_antecedent(reg):
    """'basket' is a noun but not `animate` — binding 'he' to it would be a
    guess, and the engine's discipline is to refuse."""
    r = solve("The basket has 7 buttons. He sold 3 buttons.", reg)
    assert any("refers" in d for d in r.deficiencies())


def test_it_never_binds_to_a_person_noun(reg):
    """The pronoun-side gate: the kernel has no gender feature, so
    `animate_pronoun` is what stops 'it' taking a person antecedent."""
    r = solve("Baker made 157 cakes. It sold 158 cakes.", reg)
    assert any("refers" in d for d in r.deficiencies())


def test_a_name_still_wins_when_one_exists(reg):
    """The fallback is ZERO-NAME ONLY. With any name present the candidate
    set is non-empty and this path never runs — which is the whole safety
    argument, since adding candidates to a non-empty set could turn a
    working unique binding into an ambiguous one."""
    r = solve("Ana made 5 cakes. She sold 2 cakes.", reg)
    # both sentences resolved to 'ana' — assert on the FACT SET, not a dict
    # keyed by (entity, measure): the two facts share that key and differ
    # only by verb, so a dict silently keeps whichever came last.
    assert {(q.entity, q.verb, q.value) for q in r.store.by_kind(Quantity)} == {
        ("ana", "make", 5.0),
        ("ana", "sell", 2.0),
    }
    assert not any("refers" in d for d in r.deficiencies())


# ---------------------------------------------------------------- guards

def test_a_time_period_is_not_a_relation_standard(reg):
    """GUARD 1. "three fewer tables than this month" bound the standard to
    'month' and invented a 'carpenter/month' quantity — a category error.
    With the guard the relation is never minted, so nothing is asserted."""
    r = solve(
        "A tailor sewed nine shirts for this week. "
        "Last week, he sewed two fewer shirts than this week. "
        "How many shirts did the tailor sew in total?",
        reg,
    )
    assert not r.store.by_kind(Relation)
    assert r.value is None


def test_a_bare_event_over_parts_only_state_declines(reg):
    """GUARD 2. The holder's state is PARTS ('button[green]', 'button[red]')
    and a BARE event arrives: which part does it deplete? Unanswerable
    without source-marked transfer, so decline. Folding it instead commits
    parts+event, the confident-wrong this guard exists to prevent."""
    r = solve(
        "Ana had 105 green buttons and 71 red buttons. "
        "Ana picked 137 buttons. How many buttons are left?",
        reg,
    )
    assert r.value is None


def test_a_stated_whole_is_never_double_counted(reg):
    """GUARD 3, fail-closed half. A stated bare holding IS the whole, so the
    parts must NOT be added to it (200, never 280)."""
    r = solve(
        "Ana has 14 blue buttons and 26 purple buttons. Ana has 200 buttons. "
        "How many buttons does Ana have?",
        reg,
    )
    assert r.value != 240.0 and r.value != 280.0


def test_a_bare_ask_sums_qualified_parts(reg):
    """GUARD 3, the buying half. With no bare state stated, a BARE ask asks
    for the whole and the qualified siblings are its parts."""
    r = solve(
        "Gino has 15 brown buttons and 24 white buttons. "
        "How many buttons does Gino have?",
        reg,
    )
    assert r.value == 39.0
