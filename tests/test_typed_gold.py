"""Typed gold — the Phase 0 comparator (docs/difg-corpus-plan.md).

SYNTHETIC ONLY (constitution rule 3). Not one string here comes from GSM8K or
from difg's corpus — every fixture is invented, so reading this file leaks no
TEST item from either project.

What is being pinned:
  1. The float path is UNTOUCHED — a bare-float gold never enters the typed
     branch. This is why the GSM8K snapshot is byte-identical, and if someone
     later "simplifies" _judge by routing floats through TypedGold, this fails.
  2. The comparator NEVER GUESSES. difg's own eval.py falls back to normalized
     string CONTAINMENT, which false-positives on short numeric answers — gold
     "5" is "contained in" a trace ending "...the answer is 15". Measured on
     difg's 167 corroborated golds, naive string equality reported 63 conflicts
     (all pure formatting) while a strict compare reports 1. The comparator
     decides which golds we trust, so containment is allowed ONLY for a
     non-numeric gold long enough that a match cannot be coincidental.
"""

import json
from dataclasses import dataclass

from rulekit.harness.bench import _gold_json, _judge
from rulekit.harness.firewall import TypedGold


@dataclass
class _Answer:
    kind: str
    value: object
    reason: str = ""
    unit: str | None = None

    @property
    def committed(self) -> bool:
        return self.kind == "number"


@dataclass
class _Result:
    answer: _Answer


def _judge_of(gold, kind, value, unit=None):
    return _judge(gold, _Result(_Answer(kind, value, unit=unit)))


# --- 1. the float path is untouched ---------------------------------------

def test_bare_float_gold_never_enters_the_typed_branch():
    """The Phase 0 guarantee. A float gold takes the pre-existing path."""
    assert _judge_of(7.0, "number", 7.0) == ("correct", 7.0)
    assert _judge_of(7.0, "number", 8.0) == ("wrong", 8.0)
    assert _judge_of(7.0, "decline", None) == ("declined", None)


def test_labelled_series_gold_compares_by_identity_not_position():
    expected = [
        {"entity": "aven", "measure": "apple", "value": 4},
        {"entity": "bira", "measure": "apple", "value": 7},
    ]
    reversed_but_labelled = [
        {"entity": "bira", "measure": "apple", "value": 7.0},
        {"entity": "aven", "measure": "apple", "value": 4.0},
    ]

    assert _judge_of(expected, "series", reversed_but_labelled) == (
        "correct",
        reversed_but_labelled,
    )


def test_labelled_series_gold_rejects_missing_or_duplicate_rows():
    expected = [
        {"entity": "aven", "measure": "apple", "value": 4},
        {"entity": "bira", "measure": "apple", "value": 7},
    ]
    missing = [{"entity": "aven", "measure": "apple", "value": 4}]
    duplicate = [
        {"entity": "aven", "measure": "apple", "value": 4},
        {"entity": "aven", "measure": "apple", "value": 4},
    ]

    assert _judge_of(expected, "series", missing)[0] == "wrong"
    assert _judge_of(expected, "series", duplicate)[0] == "wrong"
    assert _judge_of(expected, "number", 11)[0] == "wrong"


# --- 2. numeric types compare NUMERICALLY, never by substring --------------

def test_number_gold_matches_within_tolerance():
    assert _judge_of(TypedGold("number", 42.0), "number", 42.0)[0] == "correct"


def test_short_numeric_gold_is_not_matched_by_a_containing_number():
    """The containment trap, pinned. Gold 5 must NOT match an answer of 15.

    difg's agrees() would say True here ("5" is a substring of "15"). That is
    how a comparator silently blesses a wrong gold, and it is the single reason
    this judge exists rather than reusing eval.py wholesale.
    """
    assert _judge_of(TypedGold("number", 5.0), "number", 15.0) == ("wrong", 15.0)
    assert _judge_of(TypedGold("number", 5.0), "number", 0.5) == ("wrong", 0.5)


def test_quantity_gold_rejects_a_mismatched_unit():
    assert _judge_of(TypedGold("quantity", 2.0, unit="kg"), "number", 2.0, unit="kg")[0] == "correct"
    assert _judge_of(TypedGold("quantity", 2.0, unit="kg"), "number", 2.0, unit="lb")[0] == "wrong"


def test_quantity_gold_does_not_score_a_unitless_answer_as_a_unit_match():
    """An engine that produces no unit has not PROVED the unit. It must not be
    scored as though it had — but neither is it wrong on the value, so today it
    passes on the number alone. Pinned so the choice is deliberate and visible
    the day a unit-carrying answer kind lands (Phase 4+)."""
    assert _judge_of(TypedGold("quantity", 2.0, unit="kg"), "number", 2.0)[0] == "correct"


# --- 3. verdicts compare as BOOLEANS, not as strings -----------------------

def test_verdict_gold_compares_as_a_boolean():
    assert _judge_of(TypedGold("verdict", True), "verdict", "yes")[0] == "correct"
    assert _judge_of(TypedGold("verdict", True), "verdict", "no")[0] == "wrong"
    assert _judge_of(TypedGold("verdict", False), "verdict", "false")[0] == "correct"


# --- 4. declines ------------------------------------------------------------

def test_typed_decline_is_correct_only_when_a_decline_was_expected():
    assert _judge_of(TypedGold("decline", None), "decline", None) == ("correct", None)
    assert _judge_of(TypedGold("number", 3.0), "decline", None) == ("declined", None)


# --- 5. text compares EXACTLY after normalization, never by containment -----

def test_text_gold_is_exact_after_normalization_not_contained():
    assert _judge_of(TypedGold("text", "Helium"), "text", "helium")[0] == "correct"
    # a SUPERSTRING must not pass: containment here is how a verbose wrong
    # answer ("helium and neon") would be blessed as correct.
    assert _judge_of(TypedGold("text", "Helium"), "text", "helium and neon")[0] == "wrong"


# --- 6. sets are order-insensitive but membership-exact ---------------------

def test_set_gold_is_order_insensitive_and_membership_exact():
    assert _judge_of(TypedGold("set", ("b", "a")), "set", ["A", "B"])[0] == "correct"
    assert _judge_of(TypedGold("set", ("a", "b")), "set", ["a"])[0] == "wrong"
    assert _judge_of(TypedGold("set", ("a",)), "set", ["a", "b"])[0] == "wrong"


# --- 7. a NON-COMMITMENT is never a wrong ----------------------------------

def test_undetermined_is_a_decline_not_a_wrong():
    """REGRESSION, found the first time this path met real data. 'undetermined'
    is the epistemic square's "I don't know". It arrives as a verdict-KIND
    answer, so it is not kind 'decline' — and the typed judge, which tested only
    `kind == "decline"`, scored it WRONG. That invented three confident-wrongs
    out of three honest declines, i.e. it reported the engine guessing where the
    engine had explicitly refused to guess. The float path below has always had
    this rule; the typed path was written without it."""
    assert _judge_of(TypedGold("number", 8.0), "verdict", "undetermined") == ("declined", "undetermined")
    assert _judge_of(TypedGold("text", "x**3"), "verdict", "undetermined") == ("declined", "undetermined")
    # against a DECLINE gold it is the right answer, exactly as on the float path
    assert _judge_of(TypedGold("decline", None), "verdict", "undetermined") == ("correct", None)


def test_a_committed_verdict_against_a_non_verdict_gold_is_WRONG():
    """The FOLIO Phase 1 flip, exactly as the old ⚠ REVISIT comment demanded:
    Answer.committed now admits yes/no, so a verdict asserted where a number
    was asked is a genuine confident-wrong — scoring it 'declined' would hide
    it. 'undetermined' stays a non-commitment and still declines."""
    assert _judge_of(TypedGold("number", 3.0), "verdict", "yes") == ("wrong", "yes")
    assert _judge_of(TypedGold("text", "x"), "verdict", "no") == ("wrong", "no")
    assert _judge_of(TypedGold("number", 3.0), "verdict", "undetermined") == (
        "declined", "undetermined")


def test_a_real_verdict_against_a_verdict_gold_is_still_judged():
    """The non-commitment rules above must not swallow a genuine verdict — that
    would defeat the whole point of typed gold for the boolean domains."""
    assert _judge_of(TypedGold("verdict", True), "verdict", "yes")[0] == "correct"
    assert _judge_of(TypedGold("verdict", True), "verdict", "no")[0] == "wrong"


# --- 5. the snapshot renders every gold kind ------------------------------
#
# `to_snapshot` fed the gold straight to json.dumps, so a `gold: typed` project
# raised TypeError and `bench --snapshot` — the input to the `rulekit diff` SHIP
# GATE — was unavailable for difg and folio. It failed silently in the sense
# that nothing announced the gate was missing; it was found by running it.

def test_a_typed_gold_survives_json_round_trip():
    """The regression itself: every typed kind must reach the snapshot."""
    for gold in (
        TypedGold("verdict", "true"),
        TypedGold("text", "Uncertain"),
        TypedGold("quantity", 68.04, unit="kg"),
        TypedGold("number", 7.0),
    ):
        rendered = _gold_json(gold)
        assert json.loads(json.dumps(rendered)) == rendered


def test_a_float_gold_renders_as_the_bare_float():
    """Byte-identity of the GSM8K snapshot is the constraint here, not taste: a
    stale-looking diff against a committed baseline is indistinguishable from a
    real regression. A float must not become a string or a wrapper dict."""
    assert _gold_json(7.0) == 7.0
    assert json.dumps(_gold_json(7.0)) == "7.0"


def test_a_typed_gold_renders_its_fields_not_its_repr():
    """The snapshot is a DIFF INPUT, so the rendering must stay stable if the
    dataclass ever gains a field — repr() would re-write every line of it."""
    assert _gold_json(TypedGold("quantity", 68.04, unit="kg")) == {
        "kind": "quantity", "value": 68.04, "unit": "kg",
    }
