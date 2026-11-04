"""Plural noun morphology and construction-based noun/verb sense selection.

An explicit adposition licenses a nominal object without erasing the same
surface's independent finite verb reading. Purchase totals retain every
coordinated item after that selection.
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
    dropped from the total. Both complete counts contribute at the unit quote."""
    r = solve(
        "Dara bought 9 books about plants and 1 book about fish. "
        "Each book cost $15. How much did Dara spend in all?",
        full_registry,
    )
    assert r.answer.committed, r.answer.reason
    assert r.value == 150
    assert next(u for u in r.premises[0].units if u.surface == "plants").sense() == "noun"


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
