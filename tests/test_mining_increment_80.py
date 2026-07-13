"""Mining increment 80: asked-item resolution for the
inverse-span duration asks (ask/how-long-take-span and
ask/how-many-timeunit-take-span, increments 51/55) — the payoff for the
extraposed-duration-rates enabler (increment 79).

Three coordinated, additive widenings, all on the two EXISTING inverse-span
asks and the EXISTING rate-span-inverse consumer (answer.py) — the forward
'rate-span' consumer/branch stays byte-for-byte untouched:

1. TOTALITY ITEM: two new sibling ask ids (ask/how-long-take-span-
   totality-item, ask/how-many-timeunit-take-span-totality-item) let the
   asked item be a totality marker ("all (of) (the) ITEM") instead of a
   stated numeral. rate-span-inverse resolves the count from the entity's
   own UNIQUELY stated Quantity of that measure — read either directly off
   the entity or off something the entity OWNS (Quantity.owner, the same
   possessive-merge field the single-entity consumer's own owner fallback
   already reads) — declining on zero or ambiguous totals (the
   increment-10/16 whole-total-decline discipline). A brand-new ask id,
   never a widened `item` slot on the base ask: the base ask's own
   `item_value: "{item.value}"` template would silently break on an
   unnumbered noun.
2. ASKED-UNIT CONVERSION: when the ask names a time unit that differs from
   the committing Rate's `per` unit, rate-span-inverse now applies the SAME
   static `reg.conversions` table the forward rate-span consumer already
   applies (in the reverse direction — the computed span is stated in the
   rate's own per-unit and gets converted INTO the asked unit) instead of
   declining outright. An asked unit with no defined conversion still
   declines.
3. FOR-VARIANT: an optional `{lit: for}` between 'take' and `who` on all
   four ask ids ("how long does it take FOR WHO to VERB...") — pure
   grammatical skeleton, the same extraposed-infinitive construction these
   asks already document; a question without 'for' matches exactly as
   before.

The conjoined-item-list class (a duration-rate premise stating TWO or more
per-item rates in one sentence, and an ask summing item_i / rate_i over a
list) is explicitly OUT of scope for this increment — it requires widening
the SHARED SVO compound-rate scan (learn.py's `_compound_rate_span`) and a
new multi-item ask/consumer shape, both flagged high blast-radius in this
candidate's own brief; left for a follow-on candidate.

Synthetic only — every name/number/item below is invented, none borrowed
from any GSM8K item."""

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


# ---------------------------------------------------------------------
# 1. TOTALITY ITEM
# ---------------------------------------------------------------------


def test_totality_item_direct_entity(full_registry):
    # "all of the X" resolved against a Quantity stated directly on the
    # asked entity: 3 cookies / 4 minutes = 0.75 cookies/min;
    # 60 / 0.75 = 80 minutes.
    r = solve(
        "It takes Nora 4 minutes to bake 3 cookies. Nora has 60 cookies. "
        "How long does it take Nora to bake all of the cookies?",
        full_registry,
    )
    assert r.answer.kind == "number"
    assert r.answer.value == pytest.approx(80.0)


def test_totality_item_via_owned_possessive(full_registry):
    # "Marco's tray" states the total on something Marco OWNS, not on
    # Marco directly (Quantity.owner == 'marco') — the totality lookup
    # must still resolve it: 2 donuts / 5 minutes = 0.4 donuts/min;
    # 40 / 0.4 = 100 minutes.
    r = solve(
        "It takes Marco 5 minutes to bake 2 donuts. Marco's tray has 40 "
        "donuts. How many minutes will it take Marco to bake all of the "
        "donuts?",
        full_registry,
    )
    assert r.answer.kind == "number"
    assert r.answer.value == pytest.approx(100.0)


def test_totality_item_bare_all_no_of_the(full_registry):
    # "all X" (no 'of', no 'the') binds identically to "all of the X".
    r = solve(
        "It takes Nora 4 minutes to bake 3 cookies. Nora has 60 cookies. "
        "How long does it take Nora to bake all cookies?",
        full_registry,
    )
    assert r.answer.kind == "number"
    assert r.answer.value == pytest.approx(80.0)


def test_totality_item_ambiguous_total_declines(full_registry):
    # TWO stated totals for the same measure/entity — decline rather than
    # guess which one the totality marker means.
    r = solve(
        "It takes Marco 5 minutes to bake 2 donuts. Marco's tray has 40 "
        "donuts. Marco's box has 20 donuts. How many minutes will it take "
        "Marco to bake all of the donuts?",
        full_registry,
    )
    assert r.answer.kind == "decline"


def test_totality_item_no_total_declines(full_registry):
    # no stated total at all for the measure — decline, never invent one.
    r = solve(
        "It takes Nora 4 minutes to bake 3 cookies. How long does it take "
        "Nora to bake all of the cookies?",
        full_registry,
    )
    assert r.answer.kind == "decline"


# ---------------------------------------------------------------------
# 2. ASKED-UNIT CONVERSION
# ---------------------------------------------------------------------


def test_asked_unit_converts_via_static_table(full_registry):
    # 96 carrots / (12/30 carrots-per-minute) = 240 minutes = 4 hours.
    r = solve(
        "Owen can cut 12 carrots in 30 minutes. How many hours will it "
        "take Owen to cut 96 carrots?",
        full_registry,
    )
    assert r.answer.kind == "number"
    assert r.answer.value == pytest.approx(4.0)


def test_asked_unit_no_conversion_declines(full_registry):
    # 'lesson' has no defined conversion to 'minute' — decline, never
    # guess a factor.
    r = solve(
        "Rex reads 5 pages per lesson. How many minutes does it take Rex "
        "to read 20 pages?",
        full_registry,
    )
    assert r.answer.kind == "decline"


# ---------------------------------------------------------------------
# 3. FOR-VARIANT
# ---------------------------------------------------------------------


def test_for_variant_how_long(full_registry):
    # "how long does it take FOR WHO to VERB..." — the optional dative
    # 'for' before `who`; 2 cupcakes / 8 minutes = 0.25 cupcakes/min;
    # 10 / 0.25 = 40 minutes.
    r = solve(
        "It takes Talia 8 minutes to bake 2 cupcakes. How long does it "
        "take for Talia to bake 10 cupcakes?",
        full_registry,
    )
    assert r.answer.kind == "number"
    assert r.answer.value == pytest.approx(40.0)


def test_for_variant_how_many_timeunit(full_registry):
    r = solve(
        "It takes Talia 8 minutes to bake 2 cupcakes. How many minutes "
        "will it take for Talia to bake 10 cupcakes?",
        full_registry,
    )
    assert r.answer.kind == "number"
    assert r.answer.value == pytest.approx(40.0)


def test_without_for_still_matches(full_registry):
    # the plain (no 'for') form is unaffected by the widening.
    r = solve(
        "It takes Talia 8 minutes to bake 2 cupcakes. How long does it "
        "take Talia to bake 10 cupcakes?",
        full_registry,
    )
    assert r.answer.kind == "number"
    assert r.answer.value == pytest.approx(40.0)


# ---------------------------------------------------------------------
# Decline-safety: a conjoined item list (out of scope for this candidate)
# must not be misread as a single item.
# ---------------------------------------------------------------------


def test_conjoined_item_list_declines_not_wrong(full_registry):
    # two per-item rates in one sentence, plus a conjoined asked-item list
    # — explicitly out of scope; must stay a safe decline, never guess a
    # single-item answer from a partial read.
    r = solve(
        "Priya can bake a cupcake in 2 hours and a donut in 3 hours. How "
        "long does it take for Priya to bake 4 cupcakes and 2 donuts?",
        full_registry,
    )
    assert r.answer.kind == "decline"
