"""An unread NAME is a decline (membership-verdict consumer).

`ask/is-membership` matches `is <name> <noun>` as a SUBSEQUENCE, so a proper
noun QUALIFYING the collection can bind the member slot while the real subject
is silently dropped. The consumer then answered from a fact about the wrong
entity, and the verdict did not depend on WHO the question asked about — the
null control failing outright: an answer invariant to the question is not an
answer.

This is value-accounting's "BINDABLE is not READ" contract applied to the one
kind of value this consumer binds. A dropped name carries no digits, so no
numeric guard can see it.

Found by projects/folio (the logic gate) on its first run, where it scored
CORRECT purely because that item's gold happened to be False.

Synthetic only — every fixture below is invented, so reading this file leaks no
corpus item. The SHAPE is what is pinned, not any real sentence.
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


def test_the_intended_shape_still_answers(full_registry):
    """The guard must not cost the prose the ask was mined on. The subject IS
    the bound member here, so nothing is unread and the verdict stands."""
    r = solve("Mary is a student. Is Mary a student?", full_registry)
    assert (r.answer.kind, r.answer.value) == ("verdict", "yes")


def test_a_name_qualified_collection_does_not_swallow_the_subject(full_registry):
    """The regression. 'Rovers' qualifies the collection and binds the member
    slot; 'Ana' is the real subject and goes unread — so the engine must not
    answer about the Rovers a question that was asked about Ana."""
    r = solve(
        "Every Rovers player is a captain. Is it true that Ana is a Rovers player?",
        full_registry,
    )
    assert r.answer.kind == "decline"
    assert "unread name" in r.answer.reason


def test_no_verdict_is_committed_about_a_subject_the_guard_never_read(full_registry):
    """The null control that FOUND this, pinned at the strength it actually
    holds. Before the guard, swapping the subject for a name absent from the
    premises returned the same committed 'no' — an answer invariant to its own
    question. Both now decline, so they are still invariant; the property worth
    pinning is therefore NOT 'the answers differ' (they must not differ — the
    engine knows nothing about either name) but that NEITHER commits."""
    shape = "Every Rovers player is a captain. Is it true that {who} is a Rovers player?"
    for who in ("Ana", "Zoe"):
        a = solve(shape.format(who=who), full_registry).answer
        assert a.kind == "decline" and not a.committed, who


def test_undetermined_survives_when_nothing_is_unread(full_registry):
    """The guard must not cannibalize the epistemic square's 'I don't know'.
    With no unread name and no fact either way, 'undetermined' is still the
    right non-commitment — a decline here would be a different claim."""
    r = solve("Ana is a captain. Is Ana a student?", full_registry)
    assert (r.answer.kind, r.answer.value) == ("verdict", "undetermined")
