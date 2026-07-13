"""Mining candidate age-asks: age asks (how old is WHO, over stated ages and
older/younger relations). Two additions: (1) arithmetic/stated-age reads the
copula age predicate "WHO is N years old" as a Quantity(measure='year'); (2)
ask/how-old-is resolves "how old is WHO" via the existing single-entity
consumer, chaining through the already-shipped anchored-relation-postfix
synthesizer for "X is N years older/younger than Y". A third rule,
arithmetic/dangling-comparative-relation, closes a precision hole this
candidate's own ask surfaced: "X is N years older" with NO "than Y" anchor
must decline (an implicit-anchor comparative is a different, unbuilt
mechanism) rather than let the general SVO fold misread "is [N years]" as a
bare stated Quantity of N. Synthetic only."""

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


def test_stated_age_lookup(full_registry):
    r = solve("Sara is 4 years old. How old is Sara?", full_registry)
    assert r.answer.value == 4


def test_older_than_relation_chains_to_stated_age(full_registry):
    r = solve(
        "Emma is 2 years older than Liam. Liam is 20 years old. "
        "How old is Emma?",
        full_registry,
    )
    assert r.answer.value == 22


def test_younger_than_relation_chains_to_stated_age(full_registry):
    r = solve(
        "Liam is 20 years old. Emma is 2 years younger than Liam. "
        "How old is Emma?",
        full_registry,
    )
    assert r.answer.value == 18


def test_relation_order_independent_of_narration(full_registry):
    r = solve(
        "Emma is 2 years older than Liam. Liam is 20 years old. "
        "How old is Emma?",
        full_registry,
    )
    assert r.answer.value == 22


def test_dangling_comparative_declines(full_registry):
    # NO "than Y" anchor: an implicit-anchor comparative is out of scope —
    # this must decline, never silently answer with the bare delta (2).
    r = solve(
        "Liam is 20 years old. Emma is 2 years older. How old is Emma?",
        full_registry,
    )
    assert not r.answer.committed


def test_future_age_now_resolves(full_registry):
    # mining candidate relation-standard-frames: "in N years" projected-age
    # asks were out of scope when this test was first written (no consumer
    # read the stated offset); ask/how-old-will-be-projected + the
    # age-projected consumer now close that gap deliberately — this
    # boundary intentionally moved from decline to a correct commit.
    r = solve(
        "Sara is 4 years old. How old will Sara be in 5 years?",
        full_registry,
    )
    assert r.answer.value == 9


def test_future_age_without_stated_current_age_declines(full_registry):
    # the projected-age consumer still needs a KNOWN current age to add
    # the offset to — with none stated anywhere, this must stay declined,
    # never guess.
    r = solve(
        "How old will Sara be in 5 years?",
        full_registry,
    )
    assert not r.answer.committed
