"""ask/is-membership reads only a FRONTED interrogative, and reads all of it.

TWO mechanisms at two levels, and the second is only half the story:

1. `at_start` on the ask's 'is' (packs/arithmetic/rules/core.yaml). English
   inverts subject and auxiliary to ask ("IS Mary a student?"), so the subject
   FOLLOWS the copula — the only reason `is <name> <noun>` reads a membership
   question at all. An EMBEDDED DECLARATIVE ("...that Jim is a Knicks player")
   leaves the copula in place, so its subject PRECEDES it. A match sequence
   FLOATS (match_all retries at every start offset), so unanchored the shape
   landed on the second construction and bound the complement's proper-noun
   modifier ('Knicks') as the member. Two grammars, one token run.

2. An unread NAME declines (answer.py) — value-accounting's "BINDABLE is not
   READ" for a value kind with no digits. It catches a question that STATES
   something the query never read ("a student AT YALE").

THE ORDER THEY WERE BUILT IN IS THE LESSON. (2) came first, written against the
witness "Is it true that Jim is a Knicks player?", and it was INCOMPLETE: keyed
on an unread NAME, it sailed straight past "...that THE PILOT is a Knicks
player" — no name to be unread — which still committed 'no' about the Knicks.
Closing the witness left the class open, ONE VALUE-KIND OVER. Only (1) fixes the
construction; (2) is not a weaker version of it but a different question.

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


def test_the_unread_name_guard_still_has_its_own_class(full_registry):
    """Guard (2) is NOT subsumed by the anchor — it answers a different question.

    A FRONTED interrogative that states a restriction the query never read: the
    ask binds member='mary'/coll='student' and reads nothing of 'at Yale', so
    answering about Mary-as-student-generally would assert past the question. If
    this ever starts committing, the anchor was widened, not this guard.
    """
    r = solve("Mary is a student. Is Mary a student at Yale?", full_registry)
    assert r.answer.kind == "decline"
    assert "unread name" in r.answer.reason


def test_no_verdict_is_committed_about_a_subject_the_engine_never_read(full_registry):
    """The null control that FOUND this, pinned at the strength it actually
    holds. Originally, swapping the subject for a name absent from the premises
    returned the same committed 'no' — an answer invariant to its own question.
    Both now decline, so they are still invariant; the property worth pinning is
    therefore NOT 'the answers differ' (they must not differ — the engine knows
    nothing about either name) but that NEITHER commits."""
    shape = "Every Rovers player is a captain. Is it true that {who} is a Rovers player?"
    for who in ("Ana", "Zoe"):
        a = solve(shape.format(who=who), full_registry).answer
        assert a.kind == "decline" and not a.committed, who


def test_an_embedded_declarative_is_not_a_membership_question(full_registry):
    """THE CLASS THE UNREAD-NAME GUARD MISSED, and the reason `at_start` exists.

    A common-noun subject leaves NO name to be unread, so guard (2) is inert and
    this committed 'no' about the Rovers while ignoring 'the pilot' entirely.
    The construction is the defect, so the construction is what must not match.
    """
    for subject in ("the pilot", "the captain"):
        r = solve(
            f"Every Rovers player is a captain. "
            f"Is it true that {subject} is a Rovers player?",
            full_registry,
        )
        assert r.answer.kind == "decline", subject
        assert not r.answer.committed, subject


def test_the_anchor_declines_at_the_ask_layer_not_the_consumer(full_registry):
    """WHERE it declines is the assertion. An embedded declarative must fail to
    MATCH — if it reached the consumer and declined there, the shape would still
    be misreading the sentence and any future consumer reusing it inherits the
    bug. The reason string is the only evidence of which layer refused."""
    r = solve(
        "Every Rovers player is a captain. Is it true that Ana is a Rovers player?",
        full_registry,
    )
    assert r.answer.kind == "decline"
    assert "no ask shape" in r.answer.reason


def test_undetermined_survives_when_nothing_is_unread(full_registry):
    """The guard must not cannibalize the epistemic square's 'I don't know'.
    With no unread name and no fact either way, 'undetermined' is still the
    right non-commitment — a decline here would be a different claim."""
    r = solve("Ana is a captain. Is Ana a student?", full_registry)
    assert (r.answer.kind, r.answer.value) == ("verdict", "undetermined")
