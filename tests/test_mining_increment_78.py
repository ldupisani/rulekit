"""Mining candidate subtype-total-asks: superordinate totality asks over
same-holder subtype comparatives ("twice as many daughters as sons ... how
many children").

Mechanism, three pieces:
(1) saturate.py `_relations_synth` gains a same-holder SUBTYPE anchor branch,
    strictly additional to the pre-existing ENTITY anchor: when a Relation's
    `standard` is not another entity's own holding of the measure, but IS a
    DIFFERENT measure the relation's own SUBJECT already holds, the relation
    resolves against that subject-held quantity instead. The pre-existing
    saturate() fixpoint driver reruns every synth each round, so a chained
    standard (subtype A derived from subtype B, subtype C derived from
    subtype A) resolves over successive rounds with no extra loop.
(2) A pack-declared, EXPLICITLY opted-in `superordinate: true` category
    (data/schemas.py CategoryDef; packs/core-english/categories/core.yaml +
    packs/difg-mined/categories/semantic.yaml) names the superordinate word
    itself and lists its exhaustive subtype members ('child': daughter/son;
    'toy': soldier/car; 'fish': goldfish/angelfish/guppy).
(3) A new answer.py consumer, `_superordinate_total`, sums an entity's own
    subtype holdings into the asked superordinate measure's total — but
    ONLY for a category the pack marks `superordinate: true`. This is a
    separate, mandatory opt-in flag from merely "the category has members":
    pre-existing categories like 'animal'/'pet' also declare members, for
    an unrelated purpose (decline-safety regression coverage), with a
    deliberately PARTIAL, non-exhaustive list — reading `members` alone
    would silently under-count whenever the text mentions an uncaptured
    sibling measure.

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


def test_multiplicative_subtype_state_ask(full_registry):
    # "K times as many A as B" where B is a raw stated count of the
    # SUBJECT'S OWN holding — the same-holder subtype anchor resolves A,
    # and the superordinate consumer sums A + B into the asked total.
    r = solve(
        "Priya has five times as many sons as daughters. "
        "If she currently has two daughters, how many children does she have?",
        full_registry,
    )
    assert r.answer.value == 12  # daughters=2, sons=5*2=10, children=2+10


def test_event_verb_subtype_ask_with_prenominal_marker(full_registry):
    # an EVENT-verb ('buy') ask, with the aggregate marker sitting
    # PRENOMINALLY ("how many total toys") rather than trailing — routed to
    # the single-entity consumer's verb-scoped superordinate fallback.
    r = solve(
        "Marcus buys three times as many toy soldiers as toy cars. "
        "He buys 7 toy cars. How many total toys does he buy?",
        full_registry,
    )
    assert r.answer.value == 28  # cars=7, soldiers=3*7=21, toys=7+21


def test_chained_subtype_relation_three_hops(full_registry):
    # THREE subtypes chained through two relations: the second relation's
    # own standard is itself derived by the first — the fixpoint driver
    # (not a bespoke loop in the synth itself) resolves the second hop only
    # after the first hop lands in an earlier saturation round.
    r = solve(
        "Devon has 5 goldfish in his tank. He has 3 more angelfish than "
        "goldfish. Also, he has three times as many guppies as angelfish. "
        "How many fish does Devon have in his tank?",
        full_registry,
    )
    assert r.answer.value == 37  # goldfish=5, angelfish=5+3=8, guppies=3*8=24


def test_non_superordinate_category_stays_declined(full_registry):
    # decline-safety: 'pet' declares members (dog/cat/hamster) for an
    # UNRELATED purpose and is deliberately NOT marked `superordinate` — an
    # entity holding only declared 'pet' members must still decline, never
    # silently answer as if 'pet' were an author-vetted exhaustive
    # superordinate the way 'child'/'toy'/'fish' are.
    r = solve("Naomi has 3 dogs and 5 cats. How many pets does Naomi have?", full_registry)
    assert r.answer.kind == "decline"


def test_single_subtype_alone_stays_declined(full_registry):
    # decline-safety: only ONE declared subtype held is not "every subtype"
    # — a bare restatement must not be answered as if it were the whole
    # superordinate total.
    r = solve("Owen has four daughters. How many children does he have?", full_registry)
    assert r.answer.kind == "decline"


def test_unrelated_measure_alongside_subtypes_stays_declined(full_registry):
    # decline-safety: an entity holding a measure OUTSIDE the declared
    # subtype set (alongside genuine subtypes) must decline the whole
    # total rather than silently drop the unaccounted-for measure.
    r = solve(
        "Owen has four daughters, two sons, and ten dollars. "
        "How many children does he have?",
        full_registry,
    )
    assert r.answer.kind == "decline"
