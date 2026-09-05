"""'plants' is a plural NOUN as well as a verb — a difg-mined sense gap.

difg's miner gave `plants` the sense list [verb] ALONE, while `plant` already
declares `plural: plants`. So the plural map resolved plants -> plant correctly
and a REDUNDANT SECOND IDENTITY shadowed it — the exact failure the HANDOFF
records for 'average' ("a redundant second identity is the bug"), and the reason
to check `plural_to_singular` before trusting a mined plural.

The cascade it caused: "Maggie bought 9 books ABOUT PLANTS and 1 book about
fish" read 'plants' as a verb, so the preposition 'about' could not bind it as
its object and reached past it to '1 book' instead; 'plants' then took '1 book'
as its own dobj. The fish book landed under verb='plants', the purchase-total
consumer sums only purchases, and the item committed 155 (9x15 + 10x2) against a
gold of 170.

It now DECLINES on ambiguity rather than committing 155 — arbitration cannot
choose between the two readings, and refusing is the honest outcome. Solving it
would need arbitration to prefer the noun after a preposition: core sense
machinery under every corpus, deliberately not attempted here.

TEST LOOK SPENT and HELD at 12/1 = 92.3% (15 GSM8K TEST items contain 'plants',
so this could not be proven byte-neutral the way the session's other precision
fixes were — it had to be measured).

Synthetic only — invented fixtures.
"""

from pathlib import Path

import pytest

from rulekit.data.packs import load_packs
from rulekit.data.registry import compile_registry
from rulekit.kernel.engine import analyze, solve

REPO = Path(__file__).resolve().parent.parent


@pytest.fixture(scope="module")
def full_registry():
    mined = REPO / "packs/difg-mined"
    if not mined.exists():
        pytest.skip("difg-mined not generated")
    return compile_registry(
        load_packs([REPO / "packs/core-english", REPO / "packs/arithmetic", mined])
    )


def test_plants_carries_a_noun_sense(full_registry):
    """The entry itself. A verb-only 'plants' is a mining error, not a fact
    about English."""
    entry = full_registry.lexicon["plants"]
    assert "noun" in entry.senses and "verb" in entry.senses


def test_the_plural_resolves_to_its_singular(full_registry):
    """`plant` declares `plural: plants`, so the map already knew. The lesson is
    to CHECK it before adding a second identity."""
    assert full_registry.plural_to_singular["plants"] == "plant"


def test_the_verb_form_lemmatizes(full_registry):
    """'planted'/'planting' carry `verb: {lemma: plant}` and 'plants' did not —
    which is why its fact recorded verb='plants', a lemma no category tags."""
    assert full_registry.lexicon["plants"].verb.lemma == "plant"


def test_a_priced_noun_reading_no_longer_commits_a_partial_total(full_registry):
    """The regression, synthetic: a prepositional 'about NOUN' after a counted
    purchase must not let the second conjunct fall under a verb reading and be
    dropped from the total. It declines (ambiguity) rather than committing the
    partial sum."""
    r = solve(
        "Dara bought 9 books about plants and 1 book about fish. "
        "Each book cost $15. How much did Dara spend in all?",
        full_registry,
    )
    assert not r.answer.committed, r.answer.value


def test_nonbare_homograph_after_finite_verb_is_an_object_noun(full_registry):
    reading = analyze(
        "Mira planted plants of three different colors.", full_registry
    )
    plants = next(unit for unit in reading.units if unit.surface == "plants")

    assert plants.senses() == ["noun"]


def test_nonbare_homograph_remains_a_verb_in_predicate_position(full_registry):
    reading = analyze("Mira plants flowers.", full_registry)
    plants = next(unit for unit in reading.units if unit.surface == "plants")

    assert plants.senses() == ["verb"]
