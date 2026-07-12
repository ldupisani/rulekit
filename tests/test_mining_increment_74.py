"""Index-labeled entity identity — "Jar A has 28 marbles. Jar B has 15
marbles." both fold to the bare entity lemma 'jar' (condense.py never
merged the trailing capital letter into the noun before this candidate),
so two directly-stated holdings of the same bare noun, distinguished only
by an index label, collide as one fact-store key and decline the whole
item ("conflict: fold and fold disagree").

Mechanism: a condense.py merge pass mirroring increment 25 (merge-
possessive) BYTE-FOR-BYTE, one label kind over: a common noun immediately
followed by a single UPPERCASE letter fuses into ONE noun unit carrying a
`label` feature. The letter reaches this pass in one of two structural
forms, gated on SENSE names only (never a lexicon word list):
  - unknown: senses.py never guesses "name" for a one-character token (its
    capitalized-word branches require a non-empty lowercase remainder), so
    a bare capital letter with no lexicon entry of its own ("Jar B") stays
    `unknown`.
  - article: the one single-letter word that DOES carry a lexicon entry,
    "a" ("Jar A") — gated on the `article` SENSE, not the literal word; no
    other single-letter token carries that sense, and the indefinite
    article never immediately follows a noun in real text (it precedes the
    noun it introduces), so this can never be confused with ordinary "a
    jar" (lowercase, and on the other side of its noun).

Entity identity stays the bare lemma everywhere it already worked
(Quantity.entity is unchanged, so "the jar ... it ..." still
coreferences); the label is read ONLY by FactStore.admit's collision
handling, which re-keys a same-key VALUE conflict between two DIFFERENT
non-null labels to entity[label] and admits both separately instead of
quarantining — the increment-25 `owner` design, one field over. Digit
indices ("District 1", "house 3") are deliberately OUT of this
increment's scope: a bare cardinal digit already carries value_kind
'count' for the value-accounting guard, and folding it away silently
would risk hiding a genuinely-unread number; letters carry no such value
and are decline-safe by construction. Synthetic only.
"""

from pathlib import Path

import pytest

from rulekit.data.packs import load_packs
from rulekit.data.registry import compile_registry
from rulekit.kernel.engine import solve
from rulekit.kernel.model import Quantity

REPO = Path(__file__).resolve().parent.parent


@pytest.fixture(scope="module")
def full_registry():
    mined = REPO / "packs/difg-mined"
    if not mined.exists():
        pytest.skip("difg-mined not generated")
    return compile_registry(
        load_packs([REPO / "packs/core-english", REPO / "packs/arithmetic", mined])
    )


def test_two_labeled_holders_resolve_a_combined_ask(full_registry):
    # the payoff class: two directly-stated holdings of the same bare noun
    # ('jar'), distinguished only by their trailing letter — without the
    # split this collides ("fold and fold disagree") and declines the
    # whole item; with it, both re-key to jar[X]/jar[Y] and the
    # pre-existing entity-less combined-ask consumer sums them unchanged.
    r = solve(
        "Jar X has 19 lemons. Jar Y has 24 lemons. "
        "How many lemons are there in total?",
        full_registry,
    )
    assert r.answer.committed
    assert r.answer.value == 43


def test_three_labeled_holders_resolve(full_registry):
    r = solve(
        "Box P has 6 buttons. Box Q has 11 buttons. Box R has 3 buttons. "
        "How many buttons are there altogether?",
        full_registry,
    )
    assert r.answer.committed
    assert r.answer.value == 20


def test_label_a_matches_the_indefinite_article_fold(full_registry):
    # 'A' downcases to the indefinite article's own fold — the SENSE gate
    # (article), not a word list, is what lets this label through, and it
    # must resolve exactly like any other letter.
    r = solve(
        "Jar A has 40 seeds. Jar B has 12 seeds. "
        "How many seeds are there in total?",
        full_registry,
    )
    assert r.answer.committed
    assert r.answer.value == 52


def test_unlabeled_repeated_noun_still_collides_and_declines(full_registry):
    # decline-safety / no-regression: two DIRECT holdings of the same bare
    # noun with NO label at all must still collide exactly as before this
    # change (label is None on both sides, so the new collision branch
    # never fires and the item declines, never guesses which one is asked).
    r = solve(
        "Jar has 19 lemons. Jar has 24 lemons. "
        "How many lemons are there in total?",
        full_registry,
    )
    assert not r.answer.committed


def test_pronoun_i_never_merges_as_a_label(full_registry):
    # "I" has no lexicon entry of its own in most rulekit projects, which
    # makes it structurally indistinguishable from a genuine unknown index
    # letter — this project's core lexicon carries a dedicated `i: pronoun`
    # entry precisely so this never fuses. "The jar I have" must never mint
    # a spurious jar[I] entity, whatever else the item does with it.
    r = solve(
        "The jar I have contains 8 marbles. How many marbles are there?",
        full_registry,
    )
    entities = {q.entity for q in r.store.by_kind(Quantity)}
    assert "jar[I]" not in entities
    assert not any(e.endswith("[I]") or e.endswith("[i]") for e in entities)


def test_pronoun_i_does_not_block_unrelated_labeled_jars(full_registry):
    # decline-safety in combination: two REAL labeled holdings resolve
    # exactly as they would alone, undisturbed by an unrelated "I" mention
    # elsewhere never fusing into a third, spurious labeled entity.
    r = solve(
        "Jar A has 5 marbles. Jar B has 3 marbles. "
        "How many marbles are there in total?",
        full_registry,
    )
    assert r.answer.committed
    assert r.answer.value == 8


def test_title_initial_never_merges_across_the_period(full_registry):
    # "Mr. B" — a title and a following initial are never ADJACENT units
    # (the period between them is its own unit), so this must not fuse
    # into a label-distinguished noun. The whole item still declines (the
    # bare, unrelated unknown word "B" trips the pre-existing global
    # unknown-word guard — unaffected by this candidate either way), but
    # the fact this candidate is responsible for — whether "mr"/"jar" ever
    # fuses with the trailing initial — must not have happened.
    r = solve(
        "Jar A has 5 marbles. Mr. B has 3 coins. "
        "How many marbles does Jar A have?",
        full_registry,
    )
    entities = {q.entity for q in r.store.by_kind(Quantity)}
    assert not any(e.startswith("mr") for e in entities)
    assert entities == {"jar"}  # 'A' merges into the label; identity stays bare 'jar'


def test_single_labeled_holder_still_folds_normally(full_registry):
    # a lone labeled entity never collides with anything, so it must
    # answer exactly like an ordinary unlabeled holding — the label never
    # changes identity absent a real conflict.
    r = solve(
        "Jar M has 14 gallons. How many gallons are there?",
        full_registry,
    )
    assert r.answer.committed
    assert r.answer.value == 14
