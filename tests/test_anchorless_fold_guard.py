"""`_entity_total`'s anchorless-fold guards (the SVAMP campaign's second
live confident-wrong class).

SYNTHETIC ONLY (constitution rule 3) — invented entities and containers,
never a benchmark string.

WHY IT EXISTS. An events-only fold has no state anchor, and the implicit
zero it folds from is unfounded in two witnessed shapes:
(1) the holding was stated WITHOUT a value ("has SOME blocks") — the text
    says the anchor exists and is unknown, so events cannot reconstruct
    the holding in either direction;
(2) the signed events sum NEGATIVE ("uses 4 blocks" with no prior
    holding) — consumption presupposes prior holdings the text never
    quantified, and the engine committed the artifact (-4) confidently.

THE MODAL EXEMPTION is load-bearing: "had to sell boxes" mints the same
have/box Predication shape as "has some blocks" with no quantifier
anywhere — only a Predication whose dobj was bound by a quantifier-sensed
determiner (`dobj_unquantified`) may block the fold. An ASDiv item broke
on exactly this before the flag existed.
"""

from pathlib import Path

import pytest

from rulekit.data.project import load_project
from rulekit.kernel.engine import solve
from rulekit.kernel.model import Predication


@pytest.fixture(scope="module")
def reg():
    return load_project(Path("projects/gsm8k")).registry


def test_some_quantified_holding_blocks_the_events_only_fold(reg):
    """Shape (1), consumption direction: 'has some' + 'uses 4' must decline
    (it committed -4 before the guard)."""
    r = solve(
        "Vera has some blocks. She uses 4 blocks to build a tower. "
        "How many blocks does Vera have?",
        reg, tracing=False,
    )
    assert not r.answer.committed, (
        f"committed {r.answer.value!r}: {r.answer.reason!r}"
    )


def test_some_quantified_holding_blocks_the_positive_direction_too(reg):
    """Shape (1), acquisition direction: 'has some' + 'buys 4' is exactly
    as unanswerable — the guard reads the stated-unknown anchor, not the
    sign of the events."""
    r = solve(
        "Vera has some blocks. She buys 4 blocks. How many blocks does Vera have?",
        reg, tracing=False,
    )
    assert not r.answer.committed, (
        f"committed {r.answer.value!r}: {r.answer.reason!r}"
    )


def test_negative_events_only_fold_declines_without_any_predication(reg):
    """Shape (2): consumption with NO holding statement at all folded from
    the implicit zero to a negative count. Never a reading."""
    r = solve(
        "Vera uses 4 blocks to build a tower. How many blocks does Vera have?",
        reg, tracing=False,
    )
    assert not r.answer.committed, (
        f"committed {r.answer.value!r}: {r.answer.reason!r}"
    )


def test_modal_have_predication_does_not_block_the_fold(reg):
    """THE MODAL EXEMPTION. 'had to deliver boxes' mints a have/box
    Predication (an artifact of modal 'have to'), but no quantifier binds
    the dobj — the anchorless '10 started with minus 4 sold' fold is
    correct and must survive."""
    r = solve(
        "Vera had to sell boxes of pencils. She started out with 10 "
        "boxes and then sold 4. How many boxes did she have left?",
        reg, tracing=False,
    )
    have_preds = [
        p for p in r.store.by_kind(Predication)
        if p.verb == "have" and p.dobj == "box"
    ]
    assert have_preds and not any(p.dobj_unquantified for p in have_preds), (
        "precondition: the modal have-Predication must exist, unflagged"
    )
    assert r.answer.committed, (r.answer.reason or "")
    assert r.answer.value == 6.0


def test_dobj_unquantified_is_minted_from_the_quantifier_obligation(reg):
    """The flag itself: 'has some blocks' marks the Predication; the role
    is checked structurally (a quantifier obligation targeting the dobj),
    never a word list."""
    r = solve("Vera has some blocks. How many towers are there?", reg, tracing=False)
    preds = [
        p for p in r.store.by_kind(Predication)
        if p.subject == "vera" and p.dobj == "block"
    ]
    assert preds and all(p.dobj_unquantified for p in preds), preds


def test_acquisitions_only_fold_still_commits(reg):
    """Regression floor: an anchorless fold of pure acquisitions is the
    standard word-problem reading and stays untouched."""
    r = solve(
        "Vera bought 4 blocks and 3 blocks. How many blocks does Vera have?",
        reg, tracing=False,
    )
    assert r.answer.committed, (r.answer.reason or "")
    assert r.answer.value == 7.0


def test_anchored_fold_still_commits(reg):
    """Regression floor: with a state anchor both guards are inert."""
    r = solve(
        "Vera has 10 blocks. She uses 4 blocks to build a tower. "
        "How many blocks does Vera have?",
        reg, tracing=False,
    )
    assert r.answer.committed, (r.answer.reason or "")
    assert r.answer.value == 6.0
