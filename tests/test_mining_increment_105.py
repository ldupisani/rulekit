"""Mining increment 105: periodic-rate premises ("N ITEM
every K TIMEUNIT") plus modal/capability rate-span asks ("how many ITEM can
WHO VERB in K TIMEUNIT").

Two mechanisms, bundled on purpose:

(a) arithmetic/periodic-rate-every-span (packs/arithmetic/rules/core.yaml) —
    a new pattern rule mirroring the existing SVO compound-rate fold ("reads
    8 pages in 20 minutes", learn.py's `_compound_rate_span`), just marked
    with a quantifier ('every') instead of the `span_preposition` category
    ('in'). It SUBSUMES a latent precision hazard: today "makes N ITEM every
    K TIMEUNIT" reads as a bare (unrelated) Quantity/distributive-multiply
    fold instead of a Rate; this rule's match span marks the verb/item/span
    units `pattern_consumed`, so the general fold's junk reading disappears
    the moment it matches.

(b) ask/how-many-rate-span-modal / ask/how-much-rate-span-modal
    (packs/arithmetic/rules/core.yaml) — exact copies of the existing
    ask/how-many-rate-span / ask/how-much-rate-span with `{slot: aux, cat:
    capacity_modal}` instead of `type: auxiliary`. `capacity_modal` (a new
    category, packs/core-english/categories/core.yaml + packs/difg-mined/
    categories/semantic.yaml) covers the six capacity/hypothetical modals
    (can/could/should/may/might/must) and DELIBERATELY EXCLUDES will/would
    — a future-tense rate question can carry an un-modeled exception clause
    a genuinely hypothetical-capacity question does not (see that
    category's own comment in core.yaml).

Synthetic only."""

from pathlib import Path

import pytest

from rulekit.data.packs import load_packs
from rulekit.data.registry import compile_registry
from rulekit.kernel.engine import solve
from rulekit.kernel.model import Quantity, Rate

REPO = Path(__file__).resolve().parent.parent


@pytest.fixture(scope="module")
def full_registry():
    mined = REPO / "packs/difg-mined"
    if not mined.exists():
        pytest.skip("difg-mined not generated")
    return compile_registry(
        load_packs([REPO / "packs/core-english", REPO / "packs/arithmetic", mined])
    )


def test_periodic_rate_premise_non_modal_ask(full_registry):
    # "N ITEM every K TIMEUNIT" feeds the LIVE (non-modal) rate-span ask
    # unchanged: value = numerator * span / denominator = 12 * 20 / 4 = 60
    r = solve(
        "A machine makes 12 pages every 4 minutes. "
        "How many pages does the machine make in 20 minutes?",
        full_registry,
    )
    assert r.answer.value == 60


def test_periodic_rate_premise_subsumes_junk_quantity(full_registry):
    # the premise must emit exactly one Rate and NO stray Quantity for the
    # verb's dobj or the "every K TIMEUNIT" span — both would previously
    # leak into the store as unrelated facts
    r = solve(
        "A machine makes 12 pages every 4 minutes. "
        "How many pages does the machine make in 20 minutes?",
        full_registry,
    )
    quantities = [f for f in r.facts() if isinstance(f, Quantity)]
    assert quantities == []
    rates = [f for f in r.facts() if isinstance(f, Rate)]
    assert len(rates) == 1
    assert rates[0].entity == "machine"
    assert rates[0].measure == "page"
    assert rates[0].per == "minute"


def test_periodic_rate_premise_bare_span_means_one_unit(full_registry):
    # An uncounted singular frequency now uses the ordinary Rate model with
    # an implicit denominator of one, rather than fabricating a stated count.
    r = solve(
        "A machine makes 12 pages every day. "
        "How many pages does the machine make in 20 days?",
        full_registry,
    )
    assert r.answer.value == 240
    rates = [f for f in r.facts() if isinstance(f, Rate)]
    assert len(rates) == 1
    assert rates[0].value == 12
    assert rates[0].per == "day"
    assert rates[0].denominator is None


def test_indeterminate_periodic_frequency_still_declines(full_registry):
    r = solve(
        "A machine makes 12 pages every few days. "
        "How many pages does the machine make in 20 days?",
        full_registry,
    )
    assert r.answer.kind == "decline"


def test_modal_ask_reads_periodic_rate_capacity_modal(full_registry):
    # the bundled payoff: a CAPACITY-marked premise ("can bake ... every ...")
    # answered by the new modal ask — value = 9 * 15 / 3 = 45
    r = solve(
        "Marcus can bake 9 cookies every 3 hours. "
        "How many cookies can Marcus bake in 15 hours?",
        full_registry,
    )
    assert r.answer.value == 45


def test_how_much_rate_span_modal(full_registry):
    # the currency-measure twin of the how-many modal ask, same mechanism
    r = solve(
        "Delia should earn 15 dollars every 3 hours. "
        "How much should Delia earn in 9 hours?",
        full_registry,
    )
    assert r.answer.value == 45


def test_future_modal_excluded_decline_safety(full_registry):
    # decline-safety (this candidate's hardest-gated concern): a FUTURE-
    # tense question ("will") must NOT bind to the new modal asks — a
    # future-tense rate question can carry an un-modeled exception clause a
    # genuinely hypothetical-capacity question does not, so `capacity_modal`
    # deliberately excludes will/would. Neither the new modal ask (wrong
    # category) nor the original non-modal ask (wrong aux sense) matches,
    # so this safely declines rather than risks a wrong commit.
    r = solve(
        "Marcus can bake 9 cookies every 3 hours. "
        "How many cookies will Marcus bake in 15 hours?",
        full_registry,
    )
    assert r.answer.kind == "decline"


def test_capacity_ask_unaffected(full_registry):
    # regression: ask/how-many-capacity's own territory (a purchase-verb
    # budget question) is untouched — the new modal rate-span asks require
    # a trailing "in SPAN" clause capacity questions don't have
    r = solve(
        "Snacks cost 2 dollars each. How many snacks can Delia buy with 10 dollars?",
        full_registry,
    )
    assert r.answer.value == 5
