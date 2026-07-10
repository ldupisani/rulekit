"""The mined difg pack must compile clean and never change curated behavior
(enrichment is diff-neutral: new vocabulary may only ever move an item
decline -> correct, never touch existing outcomes)."""

from pathlib import Path

import pytest

from rulekit.data.packs import load_packs
from rulekit.data.registry import compile_registry
from rulekit.data.project import load_project
from rulekit.harness.bench import run_suite

REPO = Path(__file__).resolve().parent.parent
MINED = REPO / "packs/difg-mined"


@pytest.fixture(scope="module")
def full_registry():
    if not MINED.exists():
        pytest.skip("difg-mined not generated (run tools/migrate_difg.py)")
    return compile_registry(
        load_packs([REPO / "packs/core-english", REPO / "packs/arithmetic", MINED])
    )


def test_compiles_with_substance(full_registry):
    assert len(full_registry.lexicon) > 2000
    assert len(full_registry.quarantine) > 50
    assert full_registry.conversions[("hour", "minute")] == 60
    assert full_registry.conversions[("minute", "hour")] == pytest.approx(1 / 60)


def test_quarantine_is_not_vocabulary(full_registry):
    for word in full_registry.quarantine:
        assert word not in full_registry.lexicon


def test_noun_lemma_unifies_number_forms(full_registry):
    # 'coins' had its own difg entry; the lemma must still be 'coin'
    from rulekit.kernel.engine import analyze

    reading = analyze("Tom lost 2 coins.", full_registry)
    coins = next(u for u in reading.units if "coins" in u.features.get("fold", ""))
    assert coins.features["lemma"] == "coin"


def test_enrichment_is_diff_neutral_on_curated(full_registry):
    project = load_project(REPO / "projects/curated")
    items = project.suite_items()
    lean = run_suite(items, project.registry)
    full = run_suite(items, full_registry)
    for a, b in zip(lean.results, full.results):
        if a.outcome == "correct":
            assert (b.outcome, b.got) == (a.outcome, a.got), f"enrichment broke {a.id}"
        else:
            assert b.outcome != "wrong", f"enrichment made {a.id} confidently wrong"
