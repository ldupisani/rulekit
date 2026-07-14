"""Mining increment 111 (infrastructure): the elided
measure-noun anaphor 'ones' ("5 purple ONES") — a counted NP whose head
noun is the anaphor 'one(s)', resolving to the collection's already-
established head noun. condense.py's merge-measure-anaphor recognizes an
adjective immediately left of an indefinite 'ones' (never when an article
sits between them — that DEFINITE shape is fraction/partition territory,
not this candidate's) as a qualified but UNRESOLVED noun; document.py's
_bind_measure_anaphor then binds it, cross-sentence, to the UNIQUE prior
plural counted-noun lemma in the document — zero or two-or-more candidates
leaves it unresolved, and learn.py/patterns.py's _lemma helpers then return
a reserved sentinel no ask can ever match (a silent, harmless decline,
never a guess). This candidate cannot move a number alone — summing
multiple qualified variants is the conjunct-comparative class's job, built
on top of this — so these tests check the RESOLVED FACT directly (measure/
qualifier/value), plus one full end-to-end answer where the general
machinery already suffices. Synthetic only."""

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


def _quantities(result):
    return [f for f in result.facts() if isinstance(f, Quantity)]


def test_measure_anaphor_resolves_and_answers(full_registry):
    # 'guppy' is the unique prior plural noun in the document; "purple
    # ones" resolves to it, carrying its OWN qualifier ('purple') locally
    # rather than inheriting anything from the antecedent.
    r = solve(
        "Priya has an aquarium filled with guppies. "
        "She has 5 purple ones. How many guppies does Priya have?",
        full_registry,
    )
    assert r.answer.value == 5
    quantities = _quantities(r)
    assert any(
        q.entity == "priya" and q.measure == "guppy" and q.measure_qualifier == "purple"
        and q.value == 5
        for q in quantities
    ), quantities


def test_measure_anaphor_declines_with_ambiguous_antecedent(full_registry):
    # TWO distinct prior plural nouns (guppy, sticker) — the antecedent is
    # genuinely ambiguous, so it must stay unresolved rather than guess.
    r = solve(
        "Priya has an aquarium filled with guppies and a shelf full of "
        "stickers. There are 5 purple ones. How many guppies does Priya have?",
        full_registry,
    )
    assert r.answer.kind == "decline"
    quantities = _quantities(r)
    # the sentinel measure never matches any real entity/measure lookup
    assert all(q.measure != "guppy" for q in quantities if q.measure_qualifier == "purple")


def test_measure_anaphor_declines_with_no_antecedent(full_registry):
    # no prior noun mentioned anywhere — zero candidates, stays unresolved.
    r = solve(
        "There are 5 purple ones. How many guppies does Priya have?",
        full_registry,
    )
    assert r.answer.kind == "decline"


def test_measure_anaphor_definite_form_is_never_merged(full_registry):
    # "the PURPLE ones" is a DEFINITE subset reference (fraction/partition
    # territory), not this candidate's indefinite counted-NP shape — an
    # article immediately left of the adjective must block the merge
    # entirely, so this never satisfies fraction-of-pool's collection slot
    # and silently drop the qualifier against the WHOLE pool (the exact
    # regression this candidate's own dev-holdout gate caught and fixed).
    r = solve(
        "There were 400 marbles that were either purple or silver. They "
        "were split into equal groups and Priya took half of the purple "
        "ones home. How many marbles did Priya take home?",
        full_registry,
    )
    assert r.answer.kind == "decline"
    quantities = _quantities(r)
    # the whole (unqualified) pool must never be halved on this candidate's
    # account — no 200-valued fact may appear
    assert all(q.value != 200 for q in quantities)


def test_ordinary_adjective_noun_merge_is_unaffected(full_registry):
    # a plain, non-anaphoric counted noun phrase must merge and answer
    # exactly as before this candidate — no widening of merge-attribute's
    # ordinary path.
    r = solve(
        "Omar has 6 purple kites. How many kites does Omar have?",
        full_registry,
    )
    assert r.answer.value == 6
