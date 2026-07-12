"""mining candidate sum-constraint-relations: sum-constraint linear systems
(a stated relation between two holders plus a stated group total).

Mechanism: a new GroupTotal fact (model.py), emitted by two premise shapes
in packs/arithmetic/rules/core.yaml — the bare existential "there are N
ITEM <aggregate>" (arithmetic/existential-premise-total, the totality-
marked sibling of existential-premise-bare's own `absent: {cat: aggregate}`
refusal) and the general "... a total of N ITEM" tail
(arithmetic/group-total-of, matched anywhere in the sentence so it fires
regardless of the subject/tense preceding it). A new saturate.py plugin
(synth/sum-constraint) then solves the textbook 2x2 system whenever exactly
one Relation and exactly one GroupTotal share a measure and no third entity
already holds it: standard = (T - offset) / (1 + factor), subject =
T - standard — emitted as ordinary Quantity facts the existing single-
entity consumer answers with no consumer change. GroupTotal is USE-gated
for value accounting (like Rate/Price/Goal), and the plugin declines
(emits nothing) on ambiguity or a negative solution rather than guess.

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


def test_bare_existential_total_solves_named_pair(full_registry):
    # arithmetic/existential-premise-total: "There are N ITEM altogether"
    # (the totality-marked existential) + an anchored offset relation.
    # standard = (48 - 12) / 2 = 18, subject = 48 - 18 = 30.
    r = solve(
        "The Skyline Tower has 12 more chairs than the Harbor Depot. "
        "There are 48 chairs altogether. "
        "How many chairs does the Skyline Tower have?",
        full_registry,
    )
    assert r.answer.kind == "number"
    assert r.answer.value == 30


def test_total_of_phrasing_solves_offset_relation(full_registry):
    # arithmetic/group-total-of: "... a total of N ITEM" anywhere in the
    # sentence, here trailing a pronoun subject ("Together they have").
    # standard(Omar) = (90 - 20) / 2 = 35.
    r = solve(
        "Priya has 20 more stickers than Omar. "
        "Together they have a total of 90 stickers. "
        "How many stickers does Omar have?",
        full_registry,
    )
    assert r.answer.kind == "number"
    assert r.answer.value == 35


def test_total_of_phrasing_solves_multiplicative_relation(full_registry):
    # arithmetic/times-as-many's pure-ratio Relation (factor=3, offset=0)
    # resolved against the same "a total of N ITEM" GroupTotal.
    # standard(Leo) = 48 / (1 + 3) = 12.
    r = solve(
        "Mia has thrice as many stickers as Leo. "
        "Together they have a total of 48 stickers. "
        "How many stickers does Leo have?",
        full_registry,
    )
    assert r.answer.kind == "number"
    assert r.answer.value == 12


def test_two_relations_over_same_measure_declines(full_registry):
    # ambiguous: two DIFFERENT relations both claim 'marble' — the plugin
    # never guesses which pair the total spans.
    r = solve(
        "Nora has 6 more marbles than Pilar. "
        "Ezra has 3 more marbles than Nora. "
        "There are 40 marbles altogether. "
        "How many marbles does Nora have?",
        full_registry,
    )
    assert r.answer.kind != "number"


def test_third_holder_of_the_measure_declines(full_registry):
    # Mateo already holds 'pencil' independently of the relation pair —
    # the total's span is ambiguous (does it include Mateo or not?), so
    # the plugin declines rather than assume it doesn't.
    r = solve(
        "Jon has 4 more pencils than Kira. "
        "Mateo has 10 pencils. "
        "There are 30 pencils altogether. "
        "How many pencils does Jon have?",
        full_registry,
    )
    assert r.answer.kind != "number"


def test_negative_solution_declines(full_registry):
    # the stated offset (50) exceeds the stated total (20): a physically
    # impossible split — the plugin must decline, never commit a negative
    # holding.
    r = solve(
        "Beto has 50 more badges than Sana. "
        "There are 20 badges altogether. "
        "How many badges does Sana have?",
        full_registry,
    )
    assert r.answer.kind != "number"
