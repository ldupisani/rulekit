"""Increment 88 — weekday names are period NOUNS, not proper names.

The bug (live on main before this increment): weekday words carried an inert
`time` sense that nothing in the kernel reads, and — being always capitalized by
English convention — senses.py's capitalization heuristic ALWAYS overrode them to
`name`. A weekday adjunct therefore injected a spurious second proper name into the
document's antecedent pool, which could steal a following pronoun's binding and
silently drop the real holder's quantity.

The fix is structural, not lexical: weekday words are retagged `time` -> `noun` and
admitted to the PRE-EXISTING `timeperiod` category (alongside morning/week/year), and
senses.py exempts `timeperiod`-category words from the capitalization override. The
kernel names a CATEGORY, never a word (constitution rule 1).

The invariant these tests pin: a weekday adjunct behaves exactly like any other period
adjunct. Synthetic strings only (NEVER benchmark items).
"""

from pathlib import Path

import pytest

from rulekit.data.packs import load_packs
from rulekit.data.registry import compile_registry
from rulekit.kernel.engine import solve

REPO = Path(__file__).resolve().parent.parent

WEEKDAYS = ["Monday", "Tuesday", "Wednesday", "Thursday", "Friday", "Saturday", "Sunday"]


@pytest.fixture(scope="module")
def full_registry():
    """Weekday words live in difg-mined, so the 2-pack `registry` fixture cannot see them."""
    mined = REPO / "packs/difg-mined"
    if not mined.exists():
        pytest.skip("difg-mined not generated")
    return compile_registry(
        load_packs([REPO / "packs/core-english", REPO / "packs/arithmetic", mined])
    )


@pytest.mark.parametrize("day", WEEKDAYS)
def test_weekday_is_a_noun_not_a_name(day, full_registry):
    """The sense itself. `name` here is the bug."""
    result = solve(f"On {day}, Sam had 12 apples. How many apples does Sam have?", full_registry)
    unit = next(u for u in result.premises[0].units if u.surface.lower() == day.lower())
    assert unit.sense() == "noun", f"{day} sensed {unit.sense()!r} — a capitalized weekday must not read as a proper name"


@pytest.mark.parametrize("day", WEEKDAYS)
def test_weekday_adjunct_behaves_like_any_other_period_adjunct(day, full_registry):
    """The invariant that matters.

    "On Monday, ..." and "In the morning, ..." are the same shape — a temporal
    adjunct — and must read the same way. Before the fix they did not: the weekday
    became a rival proper name, stole the following pronoun's antecedent, and the real
    holder's quantity was lost ("no quantity known for 'sam'"), while the `morning`
    control attached it correctly.
    """
    weekday = solve(
        f"On {day}, Sam had 12 apples. He found 5 apples. How many apples does Sam have?",
        full_registry,
    )
    control = solve(
        "In the morning, Sam had 12 apples. He found 5 apples. How many apples does Sam have?",
        full_registry,
    )
    assert weekday.answer.kind == control.answer.kind
    assert weekday.answer.value == control.answer.value
    assert "no quantity known" not in (weekday.answer.reason or ""), (
        f"the {day} adjunct lost the holder's quantity — the capitalization override "
        "stole the binding again"
    )


@pytest.mark.parametrize("day", ["Monday", "Sunday"])
def test_weekday_does_not_become_a_rival_antecedent(day, full_registry):
    """A weekday must not enter the document's proper-name pool."""
    result = solve(
        f"On {day}, Rita had 8 pears. She found 3 pears. How many pears does Rita have?",
        full_registry,
    )
    names = {
        u.features.get("fold")
        for r in result.premises
        for u in r.units
        if u.sense() == "name"
    }
    assert day.lower() not in names, f"{day} entered the antecedent pool as a proper name"


def test_a_genuine_name_still_wins_the_capitalization_override(full_registry):
    """The exemption must be NARROW: only `timeperiod` words are exempt.

    'Rose' is both a common noun and a plausible name — the capitalization heuristic
    exists for exactly this case and must STILL fire. If the exemption leaked beyond the
    timeperiod category, a capitalized 'Rose' would start reading as a flower.

    (Whether a name-sensed 'Rose' then resolves to a quantity is a separate, pre-existing
    limitation — it declines identically with and without this increment. This test pins
    the SENSE, which is what the increment touches.)
    """
    result = solve("Sam saw Rose. Rose had 4 apples. How many apples does Rose have?", full_registry)
    mid_sentence = [
        u
        for r in result.premises
        for u in r.units
        if u.surface.lower() == "rose" and u.words[0].index > 0
    ]
    assert mid_sentence, "expected a mid-sentence 'Rose' unit"
    assert all(u.sense() == "name" for u in mid_sentence), (
        "the capitalization override stopped firing for a genuine mid-sentence name — the "
        "timeperiod exemption has leaked beyond the category"
    )
    # (A sentence-INITIAL 'Rose' correctly stays a common noun: the heuristic only
    # overrides sentence-initial capitals when the word is absent as a common noun.
    # Unchanged by this increment.)
