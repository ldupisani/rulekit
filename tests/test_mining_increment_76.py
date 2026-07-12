"""Mining increment 76: complement-labeled subset
asks (the ask names the COMPLEMENTARY label of a stated partition, not its
negation). A pack-declared complementary-pair relation (boy<->girl, two
singleton categories linked by `antonym:` — packs/core-english/categories/
core.yaml + packs/difg-mined/categories/semantic.yaml) licenses a new
saturate.py synth plugin (`synth/partition-complement-quantity`): once a
MEMBERSHIP partition ("N of them are boys") resolves its collection to a
real measure with exactly one holder, and the asked label ('girl') is the
declared complement of the stated one ('boy'), a real Quantity for the
complement is emitted directly (total - subset), keyed on the collection's
own holder entity — never an arbitrary unstated sibling noun (increment
16's exhaustive-enumeration refusal still applies to any UNPAIRED word).

Two new ask-side pieces ride on that fact: (1) a partitive ask form "how
many OF THE COLLECTION are LABEL?" routed to the pre-existing entity-less
'unique-entity' consumer (no new consumer); (2) a decline-safe fallback on
ask/how-many-in-place's single-entity consumer, opt-in via
`place_fallback_entity: world` (pack data, mirroring the pre-existing
`exclude_entity: world` precedent) — when the named place holds no facts of
the measure and `world` is the SOLE holder anywhere in the document (a bare
existential collection introduced by a leading place PP that never actually
bound to the named place), answer from `world` instead of declining.

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


def test_complement_label_in_place_ask(full_registry):
    # collection total held by the SAME place the ask names — the
    # complement quantity's holder matches the ask's entity directly, no
    # fallback needed.
    r = solve(
        "The school has 24 kids. 9 of them are boys. "
        "How many girls are in the school?",
        full_registry,
    )
    assert r.answer.value == 15


def test_complement_label_partitive_ask(full_registry):
    # the "how many OF THE COLLECTION are LABEL" partitive surface, routed
    # to the pre-existing entity-less unique-entity consumer.
    r = solve(
        "A school has 40 students. 12 of them are boys. "
        "How many of the students are girls?",
        full_registry,
    )
    assert r.answer.value == 28


def test_complement_label_resolves_fractional_partition(full_registry):
    # a FRACTIONAL membership partition sizes against the collection's own
    # total first (the pre-existing synth/partition-of-collection fixpoint
    # step), then the complement synth fires on the resolved cardinal in a
    # later saturation round.
    r = solve(
        "A class has 50 students. 40% of them are boys. "
        "How many of the students are girls?",
        full_registry,
    )
    assert r.answer.value == 30


def test_complement_label_in_place_falls_back_to_world(full_registry):
    # a bare existential collection (no named holder — entity `world`)
    # introduced ahead of a place the question later names: the place
    # itself holds NO facts of the asked measure, so the single-entity
    # consumer's opt-in `place_fallback_entity: world` converts what would
    # otherwise be a decline into a commit, reading from the sole `world`
    # holder instead.
    r = solve(
        "There are 45 kids this summer. 18 of them are boys. "
        "How many girls are at the school?",
        full_registry,
    )
    assert r.answer.value == 27


def test_fallback_never_fires_for_a_named_entity_ask(full_registry):
    # decline-safety: the SAME fallback must never apply to an ordinary
    # named-entity ask (single-entity consumer's other callers never bind
    # `place_fallback_entity`) — a hypothetical single OTHER holder of the
    # measure must never stand in for a named entity's own empty holding.
    r = solve(
        "Priya has 5 pencils. Omar has 20 pencils. How many crayons does Priya have?",
        full_registry,
    )
    assert r.answer.kind == "decline"


def test_second_stated_subset_declines_the_complement(full_registry):
    # a THIRD-way split over the same collection is not a clean complement
    # — increment 16's exhaustive-enumeration refusal, still honored here.
    r = solve(
        "There are 30 campers. 12 of them are boys. 6 of them are adults. "
        "How many girls are there?",
        full_registry,
    )
    assert r.answer.kind == "decline"


def test_unpaired_noun_never_treated_as_a_complement(full_registry):
    # 'dog' has NO declared complementary pair — the general entity-less
    # ask over an unrelated noun ('cat') must still decline exactly as it
    # did before this candidate (increment 17's own discipline), never
    # guessing a complement for an arbitrary sibling noun.
    r = solve(
        "There are 18 animals. 7 of them are cats. How many dogs are there?",
        full_registry,
    )
    assert r.answer.kind == "decline"


def test_ambiguous_holder_declines_the_complement(full_registry):
    # two entities both hold the collection's measure — the complement
    # synth must not guess which holder the derived quantity belongs to.
    r = solve(
        "Mateo has 14 marbles. Lena has 10 marbles. 6 of them are boys. "
        "How many of the marbles are girls?",
        full_registry,
    )
    assert r.answer.kind == "decline"


def test_inconsistent_premise_declines(full_registry):
    # the stated subset exceeds the collection total — never commit a
    # negative complement count.
    r = solve(
        "A school has 10 kids. 15 of them are boys. "
        "How many of the kids are girls?",
        full_registry,
    )
    assert r.answer.kind == "decline"
