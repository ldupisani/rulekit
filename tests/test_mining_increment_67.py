"""Mining increment 67: plural-NP / collective-subject totality asks.

Four new ask ids, all routing to EXISTING consumers (no new fact kind):

- ask/how-many-plural-combined: "how many ITEM do/does/did (THE) PLURAL-
  COMMON-NOUN have TOTAL-MARKER?" — a definite plural common noun subject
  ("the boys", "the two boys") standing in for two or more holders named
  earlier. `who, type: plural` (no new slot type) matches a bare plural
  noun OR a cardinal-merged one identically, since condense.py's count-
  merge keeps the head noun's `number: plural` feature. `who` is captured
  only to consume the subject NP structurally — never bound to a query
  field — so this routes to the same entity-less enumeration the 'combined'
  consumer already performs when no a/b is bound.

- ask/how-many-all-combined: the plural-pronoun sibling — "how many ITEM
  do/does/did ALL OF THEM have TOTAL-MARKER?" A separate ask id from
  ask/how-many-combined (not a widened `who` slot there): that ask's own
  opt group binds [aux, who, verb] as one inseparable subsequence, so
  inserting "all of" between `aux` and `who` makes it fail to match at all.

- ask/how-many-combined-named-elided-measure: "how many do/does/did NAME
  and NAME have TOTAL-MARKER?" with NO item slot — the named-pair sibling
  of ask/how-many-entity-elided-measure (increment 62), routed to a NEW
  consumer (`combined-elided-measure`, answer.py) that resolves the elided
  measure as the ONE measure BOTH named holders share (set intersection),
  declining unless exactly one is common, then reuses
  `_combined_holder_totals` exactly as the named-pair ask already does.

- ask/how-many-there-combined gained an optional trailing group ("...are
  there in total IN THE TWO LAKES?"): never binds a new query field, exists
  solely so the collective NP's own cardinal is CONSUMED (the `{grp.value}`
  precedent) rather than left as an unaccounted stated count that trips
  value-accounting.

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


def test_plural_common_noun_subject_with_cardinal(full_registry):
    r = solve(
        "Priya has 14 marbles and Wendell has 9 marbles. "
        "How many marbles do the two boys have in total?",
        full_registry,
    )
    assert r.answer.value == 23


def test_plural_common_noun_subject_bare(full_registry):
    r = solve(
        "Priya has 14 marbles and Wendell has 9 marbles. "
        "How many marbles do the boys have altogether?",
        full_registry,
    )
    assert r.answer.value == 23


def test_plural_subject_declines_with_one_holder(full_registry):
    # a collective subject still asserts plurality -- one holder in play
    # means decline, not a one-entity "sum"
    r = solve(
        "Priya has 14 marbles. How many marbles do the boys have in total?",
        full_registry,
    )
    assert r.answer.kind == "decline"


def test_all_of_them_plural_pronoun_subject(full_registry):
    r = solve(
        "Priya has 14 marbles and Wendell has 9 marbles. "
        "How many marbles does all of them have combined?",
        full_registry,
    )
    assert r.answer.value == 23


def test_bare_they_pronoun_form_still_works_unchanged(full_registry):
    # decline-safety / regression guard: the pre-existing pronoun path
    # (ask/how-many-combined) is completely unchanged by the new "all of
    # them" ask id
    r = solve(
        "Priya has 14 marbles and Wendell has 9 marbles. "
        "How many marbles do they have combined?",
        full_registry,
    )
    assert r.answer.value == 23


def test_named_pair_elided_measure_combined(full_registry):
    r = solve(
        "Priya has 14 marbles. Wendell has 9 marbles. "
        "How many do Priya and Wendell have combined?",
        full_registry,
    )
    assert r.answer.value == 23


def test_named_pair_elided_measure_resolves_the_shared_one(full_registry):
    # Priya holds two measures, Wendell holds one -- the elided measure
    # resolves to the ONE measure they share (marbles), not pencils
    r = solve(
        "Priya has 14 marbles and 5 pencils. Wendell has 9 marbles. "
        "How many do Priya and Wendell have combined?",
        full_registry,
    )
    assert r.answer.value == 23


def test_named_pair_elided_measure_declines_when_ambiguous(full_registry):
    # both hold two measures each, both shared -- genuinely ambiguous
    # which one the ask means, must decline rather than guess
    r = solve(
        "Priya has 14 marbles and 5 pencils. Wendell has 9 marbles and 2 pencils. "
        "How many do Priya and Wendell have combined?",
        full_registry,
    )
    assert r.answer.kind == "decline"


def test_entityless_there_combined_with_trailing_collective_group(full_registry):
    # ask/how-many-there-combined's new optional trailing group: the
    # collective NP's own cardinal ("two") must be consumed, not left as
    # an unaccounted stated count that trips value-accounting
    r = solve(
        "Crystal Lake has 14 fish. Blue Lake has 9 fish. "
        "How many fish are there in total in the two lakes?",
        full_registry,
    )
    assert r.answer.value == 23


def test_entityless_there_combined_without_trailing_group_still_works(full_registry):
    # regression guard: the pre-existing bare form (no trailing group) is
    # completely unchanged
    r = solve(
        "Crystal Lake has 14 fish. Blue Lake has 9 fish. "
        "How many fish are there in total?",
        full_registry,
    )
    assert r.answer.value == 23
