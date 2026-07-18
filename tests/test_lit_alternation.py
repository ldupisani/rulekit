"""`lit` alternation — the OR primitive over match tokens.

`packs/arithmetic/rules/core.yaml` named this gap outright ("there is no OR
primitive over match tokens") and worked around it with a scoped literal tail.
It exists because a CATEGORY cannot always express the choice: a category roots
at exactly ONE sense, so a word carrying an off-class sense can never join one
('any' is article-sensed, 'many' is interrogative, 'second'/'average' are the
documented lexicon traps).

Like test_at_start_anchor.py, this tests the MECHANISM against invented
fixtures, deliberately apart from the rules that motivated it — it is shared
matcher machinery and the next caller will not be ask/trig-sine. Synthetic only.

The load-bearing claim is RANK NEUTRALITY: an alternation must score exactly as
the N sibling rules it replaces, or collapsing them stops being a provable
no-op. That is pinned here, not argued in a comment.
"""

from dataclasses import dataclass, field

import pytest
from pydantic import ValidationError

from rulekit.data.schemas import AskRule, MatchToken, PatternRule
from rulekit.kernel.patterns import _try_match_at


@dataclass
class _FakeUnit:
    fold: str
    _sense: str = "noun"
    uid: int = 0
    features: dict = field(default_factory=dict)

    def __post_init__(self):
        self.features = {"fold": self.fold}

    def sense(self) -> str:
        return self._sense


def _match(units, tokens, start=0):
    return _try_match_at(units, start, tokens, reg=None, slots={}, consumed=[])


# --- the option set -------------------------------------------------------


def test_a_scalar_literal_is_a_one_element_option_tuple():
    # the whole design: scalar and alternation take the IDENTICAL code path in
    # the matcher, the prefilter and the overlap linter
    assert MatchToken(lit="the").lit_options == ("the",)
    assert MatchToken(lit=["sine", "sin"]).lit_options == ("sine", "sin")
    assert MatchToken(slot="x", type="number").lit_options == ()


# --- matching --------------------------------------------------------------


@pytest.mark.parametrize("word", ["sine", "sin"])
def test_an_alternation_matches_each_option(word):
    units = [_FakeUnit(word)]
    assert _match(units, [MatchToken(lit=["sine", "sin"])]) == 1


def test_an_alternation_matches_nothing_else(self_check=None):
    units = [_FakeUnit("cosine")]
    assert _match(units, [MatchToken(lit=["sine", "sin"])]) is None


def test_an_alternation_consumes_exactly_ONE_unit():
    # rank neutrality depends on this: `len(match.consumed)` is the PRIMARY key
    # of both _ask_rank and specificity, so an alternation must consume what the
    # single literal it replaces consumed
    consumed: list = []
    units = [_FakeUnit("sin"), _FakeUnit("tail")]
    end = _try_match_at(units, 0, [MatchToken(lit=["sine", "sin"])], reg=None,
                        slots={}, consumed=consumed)
    assert end == 1
    assert len(consumed) == 1


def test_a_scalar_literal_is_unchanged():
    assert _match([_FakeUnit("plus")], [MatchToken(lit="plus")]) == 1
    assert _match([_FakeUnit("minus")], [MatchToken(lit="plus")]) is None


# --- consume_skipped: the site that makes the a/an merges possible ---------


@pytest.mark.parametrize("article", ["a", "an"])
def test_consume_skipped_claims_whichever_option_is_present(article):
    # Without membership in the SKIP LOOP, `{lit: [a, an], consume_skipped}`
    # would walk straight past both articles and fail. This is the site the
    # logic pack's a/an collapse rests on.
    units = [_FakeUnit(article, _sense="article"), _FakeUnit("dog")]
    toks = [MatchToken(lit=["a", "an"], consume_skipped=True),
            MatchToken(lit="dog")]
    assert _match(units, toks) == 2


def test_consume_skipped_alternation_still_skips_OTHER_skippables():
    # only the named options are claimed; an unnamed article is still skipped
    units = [_FakeUnit("the", _sense="article"), _FakeUnit("dog")]
    assert _match(units, [MatchToken(lit="dog")]) == 2


def test_an_unclaimed_alternation_is_still_skipped_past():
    # the flag is opt-in: without it the articles stay invisible
    units = [_FakeUnit("a", _sense="article"), _FakeUnit("dog")]
    assert _match(units, [MatchToken(lit="dog")]) == 2


# --- schema validation -----------------------------------------------------


@pytest.mark.parametrize(
    "bad, why",
    [
        ([], "at least two"),
        (["only"], "at least two"),   # a scalar written the long way
        (["a", "a"], "duplicate"),
        (["a", ""], "non-empty strings"),
    ],
)
def test_bad_alternations_are_rejected_by_the_validator(bad, why):
    with pytest.raises(ValidationError) as exc:
        MatchToken(lit=bad)
    assert why in str(exc.value)


@pytest.mark.parametrize("bad", [["a", 3], ["a", False], ["a", None]])
def test_non_string_options_are_rejected_by_the_TYPE_check(bad):
    # These never reach `_one_form` — pydantic's `list[str]` coercion rejects
    # them first, which is why the validator's own message does not appear.
    # Pinned at this layer deliberately: `lit: [no, off]` in YAML 1.1 arrives as
    # booleans, and what matters is that it FAILS AT LOAD, not which validator
    # says so.
    with pytest.raises(ValidationError) as exc:
        MatchToken(lit=bad)
    assert "valid string" in str(exc.value)


def test_an_alternation_is_still_exactly_one_form():
    # the lit/slot/opt discriminator is unchanged by the widening
    with pytest.raises(ValidationError):
        MatchToken(lit=["a", "an"], slot="x", type="number")


# --- RANK NEUTRALITY: the claim the collapses rest on ----------------------


def _ask(ident, tokens):
    return AskRule(id=ident, match={"question": tokens}, resolves={"consumer": "c"})


def test_an_alternation_ranks_identically_to_the_scalar_it_replaces(monkeypatch):
    from rulekit.kernel.patterns import _ask_rank, Match

    scalar = _ask("ask/x", [MatchToken(lit="sine"), MatchToken(slot="x", type="number")])
    alt = _ask("ask/x", [MatchToken(lit=["sine", "sin"]),
                         MatchToken(slot="x", type="number")])

    class _R:
        category_parents: dict = {}
        def cat_ancestors(self, c):
            return [c]

    m = Match(rule=None, slots={}, consumed=(1, 2))
    assert _ask_rank(m, scalar, _R()) == _ask_rank(m, alt, _R())


def test_an_alternation_counts_as_ONE_required_token():
    from rulekit.kernel.patterns import rule_specificity

    class _R:
        category_parents: dict = {}
        def cat_ancestors(self, c):
            return [c]

    scalar = PatternRule(
        id="r/scalar", phase="read",
        match={"sentence": [MatchToken(lit="sine"), MatchToken(slot="x", type="number")]},
        emits=[],
    )
    alt = PatternRule(
        id="r/alt", phase="read",
        match={"sentence": [MatchToken(lit=["sine", "sin"]),
                            MatchToken(slot="x", type="number")]},
        emits=[],
    )
    assert rule_specificity(scalar, _R()) == rule_specificity(alt, _R())


# --- the overlap linter must see through an alternation --------------------


def test_overlapping_alternations_intersect():
    from rulekit.lint.overlap import _tokens_intersect

    a = MatchToken(lit=["sine", "sin"])
    b = MatchToken(lit=["sin", "tangent"])
    disjoint = MatchToken(lit=["cosine", "tan"])
    # scalar equality would read False here and silently UNDER-report a real
    # overlap between two rules
    assert _tokens_intersect(a, b, reg=None) is True
    assert _tokens_intersect(a, disjoint, reg=None) is False
    assert _tokens_intersect(a, MatchToken(lit="sin"), reg=None) is True


def test_the_overlap_witness_is_deterministic():
    from rulekit.lint.overlap import _witness_word

    assert _witness_word(MatchToken(lit=["sine", "sin"]), reg=None) == "sine"
