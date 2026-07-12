"""Mining candidate common-noun-relation-subjects: relation premises whose
subject or standard is a definite/possessive common noun ("Her cousin has 6
fewer rubber bands than he has").

YAML-only widening in packs/arithmetic/rules/core.yaml: the `who`/`std`
slots on `arithmetic/anchored-relation`, `arithmetic/anchored-relation-
postfix`, `arithmetic/times-as-many`, `arithmetic/fraction-as-many`,
`arithmetic/affine-times-as-many`, and `arithmetic/affine-fraction-as-many`
widen from `type: name` to the EXISTING `type: entity` slot type (anything
that can HOLD a quantity: a name, a common noun, or a resolved pronoun --
src/rulekit/kernel/patterns.py `_slot_ok`, already general and unchanged).
No kernel edit was needed: `_slot_ok`'s `entity` branch and the relation
synthesizer (saturate.py `_relations_synth`) already key Relation facts by
bare entity lemma regardless of whether that lemma came from a name or a
common noun, so a possessive/definite common-noun subject or standard now
mints a Relation fact exactly like a named one did before.

A possessive PRONOUN subject ("Her cousin has...") is NOT merged into a
single owner-tagged unit the way a genitive-s phrase ("Kennedy's house") is
-- condense.py's merge-possessive only fires on OWNER 's NOUN. "Her cousin"
stays two units (pronoun "her" + noun "cousin"); the relation rule's
`entity` slot simply binds the bare noun "cousin" as its own holder, which
is exactly what the fold and combined-ask consumer already key on. There is
still no ask shape that can query a bare common-noun subject BY NAME ("how
many ribbons does the cousin have?") -- ask/how-many-entity is deliberately
`type: name`-only (its own comment: widening it to `entity` was tried and
dropped, a specificity tie with the possessed/qualified sibling asks). That
gap is out of scope here; every test below queries the common-noun-anchored
relation through an ask shape that already exists: the general pronoun
combined ask ("do they have together"), or a name-side query when the
common noun is the STANDARD.

Each widened rule also gained a `distinct: [item, std]` where-clause: the
widening opens a DIFFERENT collision the mechanism must reject -- "has 2
fewer animal stickers than flower stickers" bare-folds `item` and `std` to
the SAME measure lemma ('sticker'), because that sentence compares two
MEASURES of the speaker's own holding (elliptical for "than [he has] flower
stickers"), not two holders' quantities of one measure. Without the guard
this mints a self-referential Relation whose standard IS the measure being
counted (caught on dev-train during landing: "Victor has 8 flower stickers.
He has 2 fewer animal stickers than flower stickers." previously declined,
would otherwise become confident-wrong).

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


def test_possessive_common_noun_subject_anchored_relation(full_registry):
    # "Her cousin has N fewer ITEM than she has" -- the brief's own class:
    # a possessive common noun ('cousin') as the relation SUBJECT, the
    # anchored-relation prefix shape, resolved via the general combined
    # ask (no ask shape can query a bare common noun by name -- see the
    # module docstring).
    r = solve(
        "Nadia has 15 ribbons. Her cousin has 4 fewer ribbons than she "
        "has. How many ribbons do they have together?",
        full_registry,
    )
    assert r.answer.value == 26


def test_possessive_common_noun_subject_anchored_relation_postfix(full_registry):
    # the POSTFIX comparative order ("N ITEM fewer than X picked") with a
    # possessive common-noun subject -- arithmetic/anchored-relation-postfix.
    r = solve(
        "Nadia picked 15 apples. Her cousin picked 4 apples fewer than "
        "Nadia picked. How many apples did they pick in total?",
        full_registry,
    )
    assert r.answer.value == 26


def test_definite_common_noun_standard_times_as_many(full_registry):
    # a definite common noun ('the teacher') as the relation STANDARD, in
    # the times-as-many ratio shape -- queried by NAME, an ask shape that
    # already exists (ask/how-many-entity).
    r = solve(
        "The teacher has 6 pencils. Marco has three times as many "
        "pencils as the teacher. How many pencils does Marco have?",
        full_registry,
    )
    assert r.answer.value == 18


def test_possessive_common_noun_subject_fraction_as_many(full_registry):
    # a possessive common-noun subject ('his brother') in the
    # fraction-as-many ratio shape, resolved via the combined ask.
    r = solve(
        "Wesley has 20 marbles. His brother has half as many marbles as "
        "Wesley. How many marbles do they have in total?",
        full_registry,
    )
    assert r.answer.value == 30


def test_common_noun_relation_self_reference_declines(full_registry):
    # decline-safety: "N fewer ITEM1 than ITEM2" bare-folds item and std to
    # the same measure lemma ('sticker') -- comparing two measures of the
    # SAME holding, not two holders' quantities. The `distinct: [item,
    # std]` guard must keep this declined, never mint a self-referential
    # Relation whose standard is the measure itself.
    r = solve(
        "Victor has 8 flower stickers. He has 2 fewer animal stickers "
        "than flower stickers. How many stickers does Victor have in "
        "total?",
        full_registry,
    )
    assert r.answer.kind == "decline"


def test_common_noun_standard_without_resolvable_quantity_declines(full_registry):
    # decline-safety: the common-noun standard's own quantity is never
    # stated anywhere in the text -- nothing to resolve the relation
    # against, so the combined ask must decline (only one holder ever
    # gets a quantity) rather than guess.
    r = solve(
        "Her cousin has 4 fewer ribbons than the neighbor has. How many "
        "ribbons do they have together?",
        full_registry,
    )
    assert r.answer.kind == "decline"
