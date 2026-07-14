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

from dataclasses import dataclass

from rulekit.harness.bench import _judge
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
