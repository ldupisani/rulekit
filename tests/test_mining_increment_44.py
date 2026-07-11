"""Mining candidate pronoun-entity-asks: pronoun-subject and common-noun-
subject single-entity asks ("how much money does she have?", "how much
money does the teacher have?", "how much money does he have left?").

Mechanism: the `who` slot on TWO specific single-entity ask ids widens from
`type: name` to `type: entity` (the same type already proven on
ask/how-many-rate-span, ask/how-much-rate-span, ask/earn-span, and
ask/how-many-capacity) — `entity` matches a name, a bare common noun, or a
RESOLVED pronoun (an unresolved one still declines: definitive-or-decline):

  - ask/how-much-noun-entity  ("how much money does WHO have?")
  - ask/how-much-money-entity-left  ("how much money does WHO have left?")

Two sibling ids in the same brief — ask/how-many-entity and
ask/how-much-bare-entity — were tried and DROPPED: widening them ties on
consumed-unit count with ask/how-many-entity-possessed/-qualified and
ask/how-much-item-cost respectively, and the alphabetical id tie-break then
silently shadows those narrower asks (caught by the existing
tests/test_mining_increment_25.py, _34.py, and _38.py). Those two ids are
left at `type: name`, unchanged from before this candidate.

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


def test_resolved_pronoun_subject_how_much_noun_entity(full_registry):
    # a single prior name antecedent lets the pronoun bind and speak as it
    r = solve(
        "Priya has 12 dollars. How much money does she have?",
        full_registry,
    )
    assert r.answer.value == 12
    assert r.answer.kind == "number"


def test_common_noun_subject_how_much_noun_entity(full_registry):
    # a bare common-noun subject ("the teacher"), never a proper name
    r = solve(
        "The teacher has 40 dollars. How much money does the teacher have?",
        full_registry,
    )
    assert r.answer.value == 40


def test_resolved_pronoun_subject_money_left(full_registry):
    r = solve(
        "Derek has 15 dollars. He buys a kite for 6 dollars. "
        "How much money does he have left?",
        full_registry,
    )
    assert r.answer.value == 9


def test_ambiguous_pronoun_antecedent_declines(full_registry):
    # decline-safety: TWO prior names means the pronoun's `refers`
    # obligation can never bind (document.py requires a UNIQUE antecedent),
    # so the widened ask must never guess which holder "she" means
    r = solve(
        "Priya has 12 dollars. Omar has 8 dollars. How much money does she have?",
        full_registry,
    )
    assert not r.answer.committed


def test_unmentioned_common_noun_subject_declines(full_registry):
    # decline-safety: "the teacher" is a syntactically valid entity subject
    # but no fact ever states the teacher's holding — the consumer must
    # decline, never borrow Omar's number just because recognition widened
    r = solve(
        "Omar has 5 dollars. How much money does the teacher have?",
        full_registry,
    )
    assert not r.answer.committed


def test_dropped_ids_still_name_only_no_possessed_shadow(full_registry):
    # regression guard for the DROPPED half of this brief: a possessive-
    # qualified subject must still route to ask/how-many-entity-possessed,
    # not fall through to the (deliberately unwidened) ask/how-many-entity
    r = solve(
        "Kendra's house has 7 rooms. Farrukh's house has 4 rooms. "
        "How many rooms does Kendra's house have?",
        full_registry,
    )
    assert r.answer.value == 7
