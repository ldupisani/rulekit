"""distributive 'each' container totals (mining candidate
distributive-each-totals): a per-container RATE ("there are N ITEM in
EACH container", "each container has N item") composes with the
container's own stated COUNT into the group's total content via a new
saturate.py plugin, `synth/distributive-container-total`, emitting a
GroupTotal(measure=content, value=count*rate) — chained transitively
across saturation rounds when the middle noun of a two-hop chain is
itself both a rate's content and the next rate's container.

THE PRECISION FIX this increment ships (constitution rule 4): before this
plugin existed, the lone per-container Quantity (entity=container) was
the ONLY fact known for the content measure, so answer.py's unique-entity
fold read it as if it were the group's whole total — a CONFIDENT WRONG.
answer.py's unique-entity consumer now declines whenever a GroupTotal
exists for the measure it is about to fold a lone holder over, converting
that latent wrong into a safe decline. No ask shape reads GroupTotal
directly yet (that is a separate, later increment) — this increment
SOLVES 0 items by design; it only removes a latent wrong and makes the
composed total available to later machinery.

A second, independent half (the distributive EVENT form, "gave N item
EACH to M recipient") teaches the general SVO fold to read the per-
recipient count as an event total (N*M) instead of silently dropping the
value, reusing the existing distributive-'each' detection in `_is_rate`
(never widening that shared scan itself).

Synthetic only — every scenario below is invented from scratch."""

from pathlib import Path

import pytest

from rulekit.data.packs import load_packs
from rulekit.data.registry import compile_registry
from rulekit.kernel.engine import solve
from rulekit.kernel.model import GroupTotal, Quantity

REPO = Path(__file__).resolve().parent.parent


@pytest.fixture(scope="module")
def full_registry():
    mined = REPO / "packs/difg-mined"
    if not mined.exists():
        pytest.skip("difg-mined not generated")
    return compile_registry(
        load_packs([REPO / "packs/core-english", REPO / "packs/arithmetic", mined])
    )


def test_distributive_container_total_now_commits_the_whole(full_registry):
    # Increment 86 shipped the SYNTH (the GroupTotal fact) and made the
    # unique-entity consumer DECLINE this rather than commit the confident-wrong
    # 12 (the per-box rate). The "separate, later increment" its docstring names
    # has now landed: with saturate tightened so the total is trustworthy
    # (Provenance.distributive), the entity-less consumer COMMITS the whole 360.
    # Never the per-box rate 12.
    r = solve(
        "There are 30 boxes of apples. There are 12 apples in each box. "
        "How many apples are there?",
        full_registry,
    )
    assert r.answer.kind == "number"
    assert r.answer.value == 360


def test_sibling_container_ask_is_unaffected(full_registry):
    # the SAME two premises, asked about the CONTAINER noun instead of the
    # content noun, must still resolve correctly — the new plugin must
    # never shadow an ask this document already answered correctly.
    r = solve(
        "There are 30 boxes of apples. There are 12 apples in each box. "
        "How many boxes are there?",
        full_registry,
    )
    assert r.answer.kind == "number"
    assert r.answer.value == 30


def test_group_total_fact_carries_the_composed_value(full_registry):
    r = solve(
        "There are 30 boxes of apples. There are 12 apples in each box. "
        "How many apples are there?",
        full_registry,
    )
    totals = [
        gt for gt in r.store.by_kind(GroupTotal)
        if gt.measure == "apple"
    ]
    assert len(totals) == 1
    assert totals[0].value == 360
    assert totals[0].provenance.sentence == -1  # use-gated, never a real sentence


def test_chained_two_hop_distributive_total(full_registry):
    # 'box' is simultaneously the CONTENT of one rate (shelf/box) and the
    # CONTAINER of the next (box/bottle) — the second hop must use the
    # COMPOSED shelf*box total (15*4=60), never the stale per-shelf rate
    # (4), even though both facts share measure='box'.
    r = solve(
        "There are 15 shelves of boxes. There are 4 boxes on each shelf. "
        "Each box holds 6 bottles. How many bottles are there in total?",
        full_registry,
    )
    box_totals = [gt for gt in r.store.by_kind(GroupTotal) if gt.measure == "box"]
    bottle_totals = [gt for gt in r.store.by_kind(GroupTotal) if gt.measure == "bottle"]
    assert len(box_totals) == 1 and box_totals[0].value == 60
    assert len(bottle_totals) == 1 and bottle_totals[0].value == 360


def test_ambiguous_container_count_declines(full_registry):
    # two INDEPENDENT groups both counted in the same container noun ('bag')
    # — the container count is ambiguous, so the plugin must not guess
    # which one the per-bin rate belongs to (and the ordinary fold below
    # must not commit a wrong number either).
    r = solve(
        "There are 10 bags in the garden. There are 20 bags in the "
        "store. Each bag holds 5 crayons. How many crayons are there?",
        full_registry,
    )
    # Both places must actually be read as quantity locations. Otherwise this
    # test only checks missing evidence, not ambiguity between two counts.
    assert {(q.entity, q.value) for q in r.store.by_kind(Quantity)
            if q.measure == "bag"} == {("garden", 10), ("store", 20)}
    assert r.answer.kind != "number"
    crayon_totals = [gt for gt in r.store.by_kind(GroupTotal) if gt.measure == "crayon"]
    assert crayon_totals == []


def test_unread_container_location_cannot_launder_an_incomplete_total(full_registry):
    r = solve(
        "There are 10 bags in the warehouse. There are 20 bags in the "
        "store. Each bag holds 5 crayons. How many crayons are there?",
        full_registry,
    )
    assert r.answer.kind != "number"
    assert "value-accounting" in r.answer.reason


def test_distributive_event_recipient_count_multiplies(full_registry):
    # 'gave N item EACH to M recipient' — the event's own Quantity value
    # must become N*M (24), not the bare per-recipient count (6), and
    # never a wrong commit: this document's own numbers ('6', '4') are
    # not otherwise individually accounted, so the overall answer still
    # safely declines — but the fold itself must carry the right value.
    r = solve(
        "Maria had 50 buttons. Maria gave 6 buttons each to 4 students. "
        "How many buttons are left?",
        full_registry,
    )
    assert r.answer.kind != "number"
    event_quantities = [
        q for q in r.store.by_kind(Quantity)
        if q.measure == "button" and q.verb == "give"
    ]
    assert len(event_quantities) == 1
    assert event_quantities[0].value == 24


def test_distributive_event_declines_without_recipient_count(full_registry):
    # 'for EACH of his students' names no counted recipient at all — this
    # must keep declining exactly as it did before this increment, never
    # fabricate a recipient count.
    r = solve(
        "Maria bought 6 buttons for each of her students. "
        "How many buttons are left?",
        full_registry,
    )
    assert r.answer.kind != "number"
    event_quantities = [
        q for q in r.store.by_kind(Quantity)
        if q.measure == "button" and q.verb in ("buy", "give")
    ]
    assert event_quantities == []
