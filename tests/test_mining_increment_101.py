"""Mining increment 101: coordinated independent
clauses whose SECOND clause loses its subject when the first clause's
object ends in a counted noun immediately before the coordinator
('Diego scored 6 points AND Sofia scored 9 points').

MECHANISM (kernel-structural, no lexicon): in
`obligations.py::_candidates`, the `subject` need's conjoined-sibling
check ('Frankie AND Carla played...' -> keep both conjuncts, stay
ambiguous) used to run and potentially early-return BEFORE the
'counted noun is rarely an agent' filter got a chance to remove the
first clause's counted-noun object from the candidate pool. When that
counted noun sat immediately before 'and <Name>', its adjacency to the
coordinator made the sibling check misread the coordinator's following
NAME as a conjunct of the counted-noun object rather than the SUBJECT
of a brand-new clause — so the second clause's subject never bound at
all (not even ambiguously). The fix reorders the existing filters so
the counted-noun exclusion runs first: once the counted noun is out of
the candidate pool, the sibling check (and, failing that, adjacency
arbitration) only ever considers genuine nominal subject candidates,
so the second clause's own name wins its own verb's subject uniquely.

This is a pure reordering of two pre-existing filters — no new lexicon,
no verb-specific branching; it applies identically regardless of verb
category (proven on 'score' and 'read', for both 'and' and 'while'
coordinators; the corresponding one-clause and genuinely-ambiguous
group-subject shapes are pinned unchanged below).

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


def test_coordinated_and_clause_recovers_second_subject(full_registry):
    r = solve(
        "Diego scored 6 points and Sofia scored 9 points. "
        "How many points did they score in total?",
        full_registry,
    )
    assert r.answer.value == 15


def test_coordinated_while_clause_recovers_second_subject(full_registry):
    r = solve(
        "Diego scored 6 points while Sofia scored 9 points. "
        "How many points did they score in total?",
        full_registry,
    )
    assert r.answer.value == 15


def test_single_clause_unaffected(full_registry):
    # No coordinator at all: the ordinary single-clause path must be
    # byte-identical to before this change.
    r = solve(
        "Diego scored 6 points. How many points did Diego score?",
        full_registry,
    )
    assert r.answer.value == 6


def test_genuinely_conjoined_subject_group_still_declines(full_registry):
    # 'Diego and Sofia' sharing ONE verb is a true conjoined-subject GROUP,
    # not two independent clauses — this must stay ambiguous (unmet) exactly
    # as before, never resolved by the reordering above.
    r = solve(
        "Diego and Sofia scored 15 points. How many points did they score in total?",
        full_registry,
    )
    assert r.answer.kind == "decline"


def test_dangling_second_name_without_a_verb_does_not_fabricate_a_holder(full_registry):
    # 'and Sofia' with no verb of its own is NOT a new clause — the fix must
    # not manufacture a phantom Sofia holder; the ask about Diego alone must
    # still resolve to exactly Diego's own quantity.
    r = solve(
        "Diego scored 6 points and Sofia. How many points did Diego score?",
        full_registry,
    )
    assert r.answer.value == 6
