"""container-content bridge (mining increment 77):
a Quantity whose ENTITY is another Quantity's MEASURE bridges a holder's
container COUNT with a per-container content RATE into the holder's
derived content total — 'Priya bought 6 boxes of marbles. Each box has 9
marbles.' folds to two independently-true facts (Priya holds 6 boxes; a
box holds 9 marbles) that nothing previously connected into 'Priya bought
54 marbles'. `saturate._container_contents_synth` closes exactly that
structural gap: entity == another Quantity's measure, one-hop, raw-fold-
only composition. Infrastructure — this increment adds no new ask-shape
consumer, it only makes the bridged fact available to whichever consumer
already reads a plain Quantity(entity, measure, verb). Synthetic only."""

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


def test_container_count_times_per_container_rate(full_registry):
    r = solve(
        "Priya bought 6 boxes of marbles. Each box has 9 marbles. "
        "How many marbles did Priya buy?",
        full_registry,
    )
    assert r.answer.value == 54


def test_bridged_quantity_is_use_gated_not_sentence_tagged(full_registry):
    # the derived fact must never be tagged to a real premise sentence —
    # see the docstring in saturate.py for why (guards.py's
    # value-accounting masking risk)
    r = solve(
        "Priya bought 6 boxes of marbles. Each box has 9 marbles. "
        "How many marbles did Priya buy?",
        full_registry,
    )
    bridged = [
        q for q in r.store.by_kind(Quantity)
        if q.provenance.source == "synth/container-contents"
    ]
    assert len(bridged) == 1
    assert bridged[0].provenance.sentence == -1
    assert bridged[0].entity == "priya"
    assert bridged[0].measure == "marble"
    assert bridged[0].value == 54


def test_ambiguous_per_container_rate_declines(full_registry):
    # two DIFFERENT stated per-box rates for the same container/content
    # pair — the bridge must never guess which one to use, so no
    # synth/container-contents fact is emitted for marbles at all
    r = solve(
        "Priya bought 6 boxes of marbles. Each box has 9 marbles. "
        "Each box has 11 marbles. How many marbles did Priya buy?",
        full_registry,
    )
    bridged = [
        q for q in r.store.by_kind(Quantity)
        if q.provenance.source == "synth/container-contents"
    ]
    assert bridged == []
    assert r.answer.kind == "decline"


def test_holder_with_stated_total_is_never_overwritten(full_registry):
    # Priya's own marble total is already stated directly — the bridge
    # must not also derive a competing one from the box count, even though
    # the box/content structure is otherwise present
    r = solve(
        "Priya has 5 marbles. Priya bought 6 boxes of marbles. "
        "Each box has 9 marbles.",
        full_registry,
    )
    bridged = [
        q for q in r.store.by_kind(Quantity)
        if q.provenance.source == "synth/container-contents"
    ]
    assert bridged == []
