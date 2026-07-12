"""Mining candidate chained-relations: chained inverse relation resolution
(2-hop "times as many"/"times older than" chains anchored at the top).

Two things are established here, not one:

1. `saturate.py`'s existing round-based fixpoint loop (`saturate()`) ALREADY
   resolves a multi-hop relation chain, forward or inverse, with NO kernel
   change — each round re-invokes `synth/relation-to-quantity` over the
   store as it stood after the previous round's admissions, so a derived
   (not only stated) quantity becomes available to the NEXT hop on the NEXT
   round. This is verified directly below (test_two_hop_inverse_chain_...,
   test_three_hop_mixed_chain_...) using ONLY rules that already ship on
   main (times-as-many, anchored-relation-postfix) — no saturate.py edit is
   part of this candidate.
2. The actual gap blocking the traced dev-train evidence (age chains like
   "Thor is 13 times older than Captain America. Captain America is 7 times
   older than Peter Parker...") was never the fixpoint depth — it was that
   "X is N times older/younger than Y" (a MULTIPLICATIVE age comparative
   with NO stated noun) never produced a Relation fact at all. This file's
   only production change, `arithmetic/times-comparative-age-relation`
   (packs/arithmetic/rules/core.yaml) plus the new `age_comparative`
   category (packs/core-english/categories/core.yaml, members in
   packs/difg-mined/categories/semantic.yaml), closes exactly that
   extraction gap, scoped to 'older'/'younger' only. Once the Relation fact
   exists, the already-working fixpoint above finishes the job.

Synthetic only.
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


def test_times_older_relation_forward(full_registry):
    # standard known first -> subject derived forward (factor * standard)
    r = solve(
        "Odette is 20 years old. Priya is 3 times older than Odette. "
        "How old is Priya?",
        full_registry,
    )
    assert r.answer.value == 60


def test_times_older_relation_inverse(full_registry):
    # subject known -> standard derived via inverse ((subject) / factor)
    r = solve(
        "Priya is 3 times older than Odette. Priya is 60 years old. "
        "How old is Odette?",
        full_registry,
    )
    assert r.answer.value == 20


def test_times_younger_relation_inverts_the_ratio(full_registry):
    # 'younger' flips the direction: subject = standard / factor
    r = solve(
        "Marcus is 25 years old. Odette is 5 times younger than Marcus. "
        "How old is Odette?",
        full_registry,
    )
    assert r.answer.value == 5


def test_two_hop_inverse_chain_multiplicative_age(full_registry):
    # the traced dev-train shape (Thor/Captain America/Peter Parker,
    # renamed and shortened to 2 hops): both hops are multiplicative
    # 'times older' relations, resolved top-down via TWO rounds of the
    # existing saturate.py fixpoint — no kernel change in this candidate.
    r = solve(
        "Marcus is 13 times older than Odette. Odette is 7 times older "
        "than Quill. Marcus is 1456 years old. How old is Quill?",
        full_registry,
    )
    assert r.answer.value == 16


def test_three_hop_mixed_additive_and_multiplicative_chain(full_registry):
    # mixes an existing additive relation (anchored-relation-postfix) with
    # two new multiplicative ones, anchored at the top by a stated age —
    # exactly the class named at ship time, and proof the new rule composes
    # with pre-existing relation machinery through the shared fixpoint.
    r = solve(
        "Marcus is 1456 years old. Marcus is 13 times older than Odette. "
        "Odette is 7 times older than Quill. Priya is 32 years older than "
        "Quill. How old is Priya?",
        full_registry,
    )
    assert r.answer.value == 48


def test_two_hop_forward_as_many_chain_unaffected(full_registry):
    # the "times as many" (non-age) sibling relation already chains
    # correctly on main with no code change — regression-checked here so a
    # future edit to saturate.py can't silently narrow the fixpoint back to
    # one hop without this test noticing.
    r = solve(
        "Odette has 4 times as many marbles as Priya. Priya has 3 times "
        "as many marbles as Quill. Odette has 60 marbles. How many "
        "marbles does Quill have?",
        full_registry,
    )
    assert r.answer.value == 5


def test_general_comparative_word_does_not_get_an_implicit_age(full_registry):
    # 'faster' is a general magnitude comparative (delta/higher), NOT a
    # member of the new age_comparative category — "N times faster than Y"
    # must NOT silently acquire an implicit measure='year' relation; it
    # stays declined rather than answer a confident wrong.
    r = solve(
        "Odette is 20 years old. Priya is 3 times faster than Odette. "
        "How old is Priya?",
        full_registry,
    )
    assert not r.answer.committed


def test_no_anchor_at_all_declines(full_registry):
    # neither end of the relation has a known age anywhere in the text —
    # must decline, never guess.
    r = solve(
        "Priya is 3 times older than Odette. How old is Priya?",
        full_registry,
    )
    assert not r.answer.committed
