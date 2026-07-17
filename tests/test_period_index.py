"""Period-identified nouns — "the year 1946", "week 3": a timeperiod noun
followed by an integer is an IDENTIFIER appositive, not a quantity ("year
1946" is not 1946 years). condense.py's merge-period-index folds the pair
into one labeled noun, the numeric twin of merge-label ("Jar B").

The two contracts pinned here are the DANGEROUS directions:
  - a count BEFORE a noun is untouched ("1946 apples" still counts) — the
    construction is count+noun, a different pass entirely;
  - a count that could quantify a FOLLOWING noun is never stolen ("Every
    year 500 people visit" leaves 500 with 'people') — the merge is blocked
    outright by a following noun, so the ambiguous "In the year 1946 books
    were sold" stays unmerged and decline-safe.

Increment-74 declared digit indices out of scope because folding a
value_kind 'count' away can hide a genuinely-unread number from
value-accounting; this pass takes exactly that step, gated to the
timeperiod CATEGORY (members live in packs) where the number is
semantically an identifier, plus the following-noun block. Synthetic only.
"""

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


def _unit_folds(result):
    return [u.features.get("fold") for r in result.premises for u in r.units]


def test_year_appositive_merges_and_frees_the_commit(full_registry):
    # the payoff: the dangling year no longer trips value-accounting, so the
    # real count commits — and the year's digits never leak into the answer
    r = solve(
        "Tom bought 3 apples in the year 1946. How many apples did Tom buy?",
        full_registry,
    )
    assert r.answer.committed
    assert r.answer.value == 3


def test_count_before_noun_still_counts(full_registry):
    # the mirror construction is count+noun and must be untouched
    r = solve(
        "Tom bought 1946 apples. How many apples did Tom buy?",
        full_registry,
    )
    assert r.answer.committed
    assert r.answer.value == 1946


def test_period_index_label_lands_on_the_noun(full_registry):
    r = solve("Tom read a book in the year 1946.", full_registry)
    labeled = [
        u for prem in r.premises for u in prem.units
        if u.features.get("label") == "1946"
    ]
    assert len(labeled) == 1
    assert labeled[0].features.get("lemma") == "year"


def test_following_noun_blocks_the_steal(full_registry):
    # "Every year 500 people ..." — 500 quantifies 'people'; the period
    # index merge must not fire, and the counted noun must survive intact
    r = solve("Every year 500 people read 3 books.", full_registry)
    folds = _unit_folds(r)
    assert "year 500" not in folds
    assert any(
        u.features.get("value") == 500 and "people" in (u.features.get("fold") or "")
        for prem in r.premises for u in prem.units
    )


def test_plural_period_noun_does_not_merge(full_registry):
    # "the years 1946 ..." — an enumeration head, not an appositive; the
    # singular gate keeps it out
    r = solve("Tom read books in the years 1946 and 1947.", full_registry)
    assert "years 1946" not in _unit_folds(r)


def test_fraction_after_period_noun_does_not_merge(full_registry):
    # only integers are identifiers; "a day 2.5 ..." can never be a label
    r = solve("Tom worked each day 2.5 hours of the week.", full_registry)
    assert "day 2.5" not in _unit_folds(r)
