"""Start-state asks: "how many did X have IN THE BEGINNING?"

SYNTHETIC ONLY (constitution rule 3): invented names and magnitudes, not corpus
strings.

The stated quantity is the END state, so the events are UNDONE, not applied:
"ate 19 and had 35 left" folds to 35 + (-19) = 16 for "how many does he have",
and must fold to 35 - (-19) = 54 for "how many did he have in the beginning".
`_entity_total(invert_events=True)` is a defaulted-off parameter bound ONLY by
the start-state asks.
"""

from pathlib import Path

import pytest

from rulekit.data.project import load_project
from rulekit.kernel.engine import solve


@pytest.fixture(scope="module")
def reg():
    return load_project(Path("projects/gsm8k")).registry


def test_start_state_undoes_a_loss(reg):
    r = solve(
        "Tomas ate 12 grapes and had 30 grapes left. How many grapes did Tomas have in the beginning?",
        reg, tracing=False,
    )
    assert r.answer.committed, (r.answer.reason or "")
    assert r.answer.value == pytest.approx(42.0)  # 30 - (-12)


def test_start_state_undoes_a_gain(reg):
    """The inversion is a SIGN FLIP, not "add the events" — an acquired event has
    to be subtracted back out, or the mechanism is just a second bug."""
    r = solve(
        "Nadia found 8 shells and had 20 shells left. How many shells did Nadia have in the beginning?",
        reg, tracing=False,
    )
    assert r.answer.committed, (r.answer.reason or "")
    assert r.answer.value == pytest.approx(12.0)  # 20 - (+8)


def test_the_same_premises_without_the_marker_are_UNCHANGED(reg):
    """THE blast-radius test. `invert_events` defaults off, so the identical
    premises under an ordinary ask must fold exactly as they always did. If this
    ever flips, the parameter has leaked out of its one caller."""
    r = solve(
        "Tomas ate 12 grapes and had 30 grapes left. How many grapes does Tomas have?",
        reg, tracing=False,
    )
    assert r.answer.committed, (r.answer.reason or "")
    assert r.answer.value == pytest.approx(18.0)  # 30 + (-12), the CURRENT state


def test_an_if_clause_start_premise_does_not_trigger_it(reg):
    """9 GSM8K TEST items carry a question-position marker and most are `if`-clause
    PREMISES — they STATE a start, they do not ASK for one. An if-clause is split
    off as a premise before the ask is tried, so the marker never reaches question
    position. The whole increment's TEST safety rests on this.

    Uses the IMPLEMENTED marker on purpose: the first version of this test said
    "originally", which cannot match {lit: in}{lit: beginning} and so passed
    vacuously — it pinned nothing while claiming to pin everything (caught by the
    constitution review)."""
    r = solve(
        "Tomas ate 12 grapes. If Tomas had 30 grapes in the beginning, how many grapes does Tomas have?",
        reg, tracing=False,
    )
    # the inverted reading (42) must be unreachable: this states a start, it does
    # not ask for one. Asserted unconditionally — not behind `if committed`, which
    # would pass vacuously the day the shape stops committing.
    assert r.answer.value != pytest.approx(42.0)


def test_a_specific_variant_is_not_rolled_up(reg):
    """REGRESSION (constitution review). The ask dropped `measure_qualifier`, so
    the qualified-key retry was skipped and the consumer rolled up every variant:
    "how many RED grapes did Tomas have in the beginning?" answered 36 (red+green)
    where the SAME question without the marker correctly answers 30. The marker
    alone turned a correct answer into a wrong one."""
    r = solve(
        "Tomas has 30 red grapes. Tomas has 6 green grapes. "
        "How many red grapes did Tomas have in the beginning?",
        reg, tracing=False,
    )
    assert r.answer.committed, (r.answer.reason or "")
    assert r.answer.value == pytest.approx(30.0)


def test_a_non_state_verb_falls_through_to_the_base_ask(reg):
    """REGRESSION (constitution review). The verb slot was `type: verb` while the
    consumer was handed a hardcoded `verb: have`, so "how many grapes did Tomas
    EAT in the beginning?" answered the HAVE-fold (42) instead of the eating (12).
    The slot is now `cat: state`, so a non-state verb never reaches this ask."""
    r = solve(
        "Tomas ate 12 grapes and had 30 grapes left. How many grapes did Tomas eat in the beginning?",
        reg, tracing=False,
    )
    assert r.answer.committed, (r.answer.reason or "")
    assert r.answer.value == pytest.approx(12.0)


def test_superordinate_rollup_declines_rather_than_un_inverting(reg):
    """REGRESSION (constitution review). `_superordinate_total` is reachable from
    this ask and gated by NO query field, so it could not be opted out of from
    YAML the way `sum_measure_variants` was. It sums subtype holdings knowing
    nothing of `invert_events`, so "bought 5 toy soldiers, had 3 toy cars left —
    how many TOYS in the beginning?" committed 8.0, un-inverted. It now declines."""
    r = solve(
        "Tomas bought 5 toy soldiers. Tomas had 3 toy cars left. "
        "How many toys did Tomas have in the beginning?",
        reg, tracing=False,
    )
    assert not r.answer.committed


def test_container_plus_loose_STILL_composes_under_inversion(reg):
    """REGRESSION, and it pins a fix I got BACKWARDS. I gated this path on
    `invert` too — and that was a confident-wrong: a GroupTotal is a STATE (an
    anchor), and the inversion only ever negates EVENTS, so the composition was
    already right. 40 (packs) + 12 (inverted loose fold) = 52; gating it answered
    12 and silently dropped the packs. Not every path needs the opt-out — only
    those that fold EVENTS without knowing about it."""
    r = solve(
        "Beth has 4 packs of crayons. Each pack has 10 crayons. "
        "Beth ate 6 crayons and had 6 crayons left. "
        "How many crayons did Beth have in the beginning?",
        reg, tracing=False,
    )
    assert r.answer.committed, (r.answer.reason or "")
    assert r.answer.value == pytest.approx(52.0)


def test_a_percent_change_declines_rather_than_applying_forward(reg):
    """REGRESSION (constitution review, probing INSIDE the fold). A PercentChange
    is an EVENT — it SCALES the running total by (1 +/- fraction). `invert_events`
    negates the polarity of event QUANTITIES and says nothing about a
    multiplicative event; undoing one is a DIVISION, not a sign flip. Applying it
    forward on an inverted fold is a confident-wrong, so it declines.

    Note which side of the line this falls: it folds an EVENT in ignorance of the
    flag (opt out), unlike container-plus-loose which touches only STATES (leave
    alone). What a helper FOLDS decides it — not whether it has heard of the flag."""
    r = solve(
        "Tomas had 100 dollars. Tomas spent 20 dollars and his money decreased by 10 percent. "
        "How many dollars did Tomas have in the beginning?",
        reg, tracing=False,
    )
    assert not r.answer.committed

    # The review's own witness, and the one that fails LOUDLY: the fold
    # half-honoured the inversion — events undone (100 - (-10)) but the
    # multiplier still APPLIED rather than divided out — which is incoherent
    # rather than merely un-inverted.
    r = solve(
        "Susie spent 10 dollars and had 100 dollars left. "
        "Susie puts 20% more dollars into her piggy bank. "
        "How many dollars did Susie have in the beginning?",
        reg, tracing=False,
    )
    assert not r.answer.committed  # was 132.0 = (100 + 10) * 1.2


def test_a_percent_change_WITHOUT_the_marker_is_untouched(reg):
    """The percent-change machinery is only opted out of UNDER inversion; the
    ordinary reading must be byte-identical."""
    r = solve(
        "Susie had 100 dollars. Susie puts 20% more dollars into her piggy bank. "
        "How many dollars does Susie have?",
        reg, tracing=False,
    )
    assert r.answer.committed, (r.answer.reason or "")
    assert r.answer.value == pytest.approx(120.0)


def test_source_transfer_is_NOT_this_mechanism(reg):
    """Deliberately NOT fixed (docs/negative-results.md). "picked 3 pears FROM HER
    TREE" folds as an event on NADIA; the tree holds only its anchor, so there is
    nothing to undo. Inverting returns the same wrong answer — the reason this ask
    family must not be widened to reach these items."""
    r = solve(
        "Nadia picked 3 pears from her tree. Now the tree has 4 pears still on it. "
        "How many pears did the tree have in the beginning?",
        reg, tracing=False,
    )
    # 7 is the right answer; the point is that inversion cannot produce it.
    # Asserted unconditionally, not behind `if committed`.
    assert r.answer.value != pytest.approx(7.0)


# --- a narrated change the fold cannot see ---------------------------------
#
# Two shapes were added (common-noun holder, in-place) because the BASE asks
# matched their questions and SILENTLY IGNORED the marker — the same bug this
# file's first increment fixed for "in the beginning", one shape over.
#
# The guard behind them is NOT "no events means decline". That premise is wrong
# and the test above (`test_a_specific_variant_is_not_rolled_up`) proves it: a
# document that narrates no change at all has start == current, and answering is
# correct. The predicate is that an event of the same MEASURE exists on ANOTHER
# entity — a change was narrated that this entity's fold never received.

def test_a_common_noun_holder_start_state_declines_a_source_transfer(reg):
    """"Rachel picked 3 apples FROM HER TREE" folds as rachel/apple/3, so the
    TREE holds no event to undo and inverting returns the CURRENT state. The base
    ask used to answer exactly that, ignoring the marker."""
    r = solve(
        "Dana picked three plums from her bush. Now the bush has four plums still on it. "
        "How many plums did the bush have to begin with?",
        reg, tracing=False,
    )
    assert not r.answer.committed, r.answer.value


def test_an_in_place_start_state_declines_a_source_transfer(reg):
    """The in-place shape ("how many X were in the TANK to start with"), and the
    other marker verb — both route through the one `start_marker_verb` category."""
    r = solve(
        "Nadia took sixteen newts out of her pond. Now there are three newts in the pond. "
        "How many newts were in the pond to start with?",
        reg, tracing=False,
    )
    assert not r.answer.committed, r.answer.value


def test_a_changeless_document_still_answers_its_start_state(reg):
    """THE BOUNDARY, and a first attempt got it wrong: with NO change narrated
    anywhere, start == current and the ask must still answer. Guarding on "this
    entity has no events" declined this and was rejected by the suite."""
    r = solve(
        "Ivo has 30 red marbles. Ivo has 6 green marbles. "
        "How many red marbles did Ivo have to begin with?",
        reg, tracing=False,
    )
    assert (r.answer.kind, r.answer.value) == ("number", 30.0)


def test_the_marker_verbs_share_one_category_not_two_asks(reg):
    """'begin' and 'start' are both `verb`, so "to _ with" is ONE ask per shape
    rather than (2 markers x N shapes). If a future marker word is not a verb it
    needs its own literal ask — see the category's notes."""
    for marker in ("to begin with", "to start with"):
        r = solve(
            f"Ivo has 30 red marbles. Ivo has 6 green marbles. "
            f"How many red marbles did Ivo have {marker}?",
            reg, tracing=False,
        )
        assert (r.answer.kind, r.answer.value) == ("number", 30.0), marker
