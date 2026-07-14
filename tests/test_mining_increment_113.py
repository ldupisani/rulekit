"""Mining increment 113: a collection split by a STATED
RATIO ('the ratio of A to B is m:n') — a new RatioQuantity premise fact
(model.py) resolved by its own synthesizer (saturate.py's
`_ratio_split_synth`) against the UNIQUE known collection measure as of
the ratio clause's own sentence (inclusive, unlike the fraction/partition
pool machinery's strictly-prior-sentence convention), plus a new
entity-less existential label-vs-label comparative ask ('how many more A
than B are there?') routed to a brand-new `label-difference` consumer
(answer.py) that never touches the pre-existing `difference` consumer's
own name-comparand slots. Synthetic only."""

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


def test_ratio_split_two_way_same_sentence_anchor(full_registry):
    # the anchor and the ratio clause share ONE sentence, joined by 'and' —
    # the case `_pool_before`'s strictly-prior convention cannot handle,
    # which is why RatioQuantity gets its own synth.
    r = solve(
        "There are 40 animals on the farm and the ratio of ducks to "
        "cows is 3:1. How many more ducks than cows are there?",
        full_registry,
    )
    assert r.answer.kind == "number"
    assert r.answer.value == 20  # 30 ducks - 10 cows


def test_ratio_split_reversed_comparand_order_and_was_verb(full_registry):
    # a different entity/label pair, the past-tense copula ('were'/'is'),
    # and the ask naming the SECOND ratio part first.
    r = solve(
        "There were 50 students in the classroom and the ratio of boys "
        "to girls is 2:3. How many more girls than boys are there?",
        full_registry,
    )
    assert r.answer.kind == "number"
    assert r.answer.value == 10  # 30 girls - 20 boys


def test_ratio_split_declines_with_no_known_anchor(full_registry):
    # no collection total anywhere in the text — the ratio synthesizer
    # finds zero candidate anchor measures and never resolves either label.
    r = solve(
        "The ratio of cats to dogs is 3:2. How many more cats than dogs "
        "are there?",
        full_registry,
    )
    assert r.answer.kind == "decline"


def test_ratio_split_declines_when_anchor_is_its_own_label(full_registry):
    # a part is never its own whole: 'cat' already has a stated Quantity,
    # but it is ALSO one of the ratio's own two labels, so it must never be
    # treated as the collection total for sizing 'dog' — this is a
    # deliberately different (harder) anchor shape this candidate declines
    # rather than guesses at.
    r = solve(
        "There are 30 cats at the shelter and the ratio of cats to dogs "
        "is 3:2. How many more dogs than cats are there?",
        full_registry,
    )
    assert r.answer.kind == "decline"


def test_ratio_split_declines_with_ambiguous_anchor(full_registry):
    # two equally-plausible collection totals known before the ratio
    # clause — definitive-or-decline, never guessed.
    r = solve(
        "There are 20 cats and 15 dogs at the shelter. The ratio of birds "
        "to fish is 3:2. How many more birds than fish are there?",
        full_registry,
    )
    assert r.answer.kind == "decline"


def test_label_difference_ask_declines_across_different_holders(full_registry):
    # the new label-difference consumer requires BOTH labels to resolve to
    # the SAME single holder — two unrelated entities' totals must never be
    # silently subtracted just because the noun phrases look comparable.
    r = solve(
        "Tom has 5 apples. Jerry has 3 oranges. How many more apples than "
        "oranges are there?",
        full_registry,
    )
    assert r.answer.kind == "decline"
