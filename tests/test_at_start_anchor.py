"""`at_start` — the opt-in match anchor (schemas.MatchToken, patterns._try_match_at).

A match sequence is CONTIGUOUS modulo SKIPPABLE_SENSES, but it FLOATS: match_all
retries at every start offset. So a shape mined on one construction lands on any
later construction containing the same token run — which is how `is <name>
<noun>`, written for the fronted interrogative "Is Mary a student?", came to
misread the embedded declarative "...that Jim is a Knicks player".

`at_start` pins a token to the front. It is STRUCTURE, not lexicon: it constrains
WHERE a token may match, never which words exist.

This file tests the MECHANISM against invented pack fixtures, deliberately apart
from the ask that motivated it — it is shared matcher machinery and the next
caller will not be ask/is-membership. Synthetic only.
"""

from dataclasses import dataclass, field

import pytest
from pydantic import ValidationError

from rulekit.data.schemas import AskRule, MatchToken
from rulekit.kernel.patterns import _try_match_at


@dataclass
class _FakeUnit:
    """The minimum _try_match_at reads for a literal token: a sense, a fold and
    a uid. Faked rather than parsed because the anchor's skippable-prefix rule is
    not reachable from natural text today (a leading quote/paren kills question
    detection upstream), and an untested branch is a claim, not a behavior."""

    fold: str
    _sense: str
    uid: int = 0
    features: dict = field(default_factory=dict)

    def __post_init__(self):
        self.features = {"fold": self.fold}

    def sense(self) -> str:
        return self._sense


def _match(units, tokens, start=0):
    """Note `start`: _try_match_at is CONTIGUOUS from wherever it is told to
    begin. The floating this anchor exists to stop is match_all's retry loop
    (`for begin in range(...)`) calling this at successive offsets — so an
    offset is exactly what a test of the anchor has to supply."""
    return _try_match_at(units, start, tokens, reg=None, slots={}, consumed=[])


def test_at_start_defaults_off():
    """The whole safety argument for touching a shared matcher: every existing
    token must be byte-identical, so the anchor has to be opt-in."""
    assert MatchToken(lit="is").at_start is False


def test_at_start_rejects_an_opt_group():
    """Optional AND anchored to the start is a contradiction — the token means
    nothing either way, so it fails at load rather than matching silently."""
    with pytest.raises(ValidationError, match="does not qualify an `opt` group"):
        MatchToken(opt=[MatchToken(lit="is")], at_start=True)


def test_an_anchor_on_a_later_token_is_rejected_at_load():
    """A dead rule reads as a clean 0 SOLVED on every gate, which is why this
    must fail loudly: token N>0 anchored to the start would need tokens 0..N-1
    to match BEFORE the start, so the ask silently matches nothing forever."""
    with pytest.raises(ValidationError, match="only meaningful on the FIRST token"):
        AskRule(
            id="ask/bad-anchor",
            match={"question": [
                MatchToken(lit="is"),
                MatchToken(lit="true", at_start=True),
            ]},
            resolves={"consumer": "membership-verdict"},
        )


def test_an_anchor_on_the_first_token_loads():
    """The sanctioned form — the one ask/is-membership uses."""
    rule = AskRule(
        id="ask/good-anchor",
        match={"question": [
            MatchToken(lit="is", at_start=True),
            MatchToken(slot="member", type="name"),
        ]},
        resolves={"consumer": "membership-verdict"},
    )
    assert rule.match["question"][0].at_start is True


# --- the matcher's half of the contract -----------------------------------

def test_an_anchored_token_matches_at_the_front():
    units = [_FakeUnit("is", "verb", 0), _FakeUnit("mary", "name", 1)]
    assert _match(units, [MatchToken(lit="is", at_start=True)]) == 1


def test_an_anchored_token_refuses_a_retry_past_the_front():
    """The bug at the mechanism level. match_all walks `begin` forward until
    something matches; at begin=1 this 'is' is a declarative copula, not the
    fronted auxiliary, and the anchor is what tells the two apart."""
    units = [_FakeUnit("jim", "name", 0), _FakeUnit("is", "verb", 1)]
    assert _match(units, [MatchToken(lit="is", at_start=True)], start=1) is None
    # ...while the UNANCHORED token still matches on that same retry — the
    # floating every other rule relies on, unchanged. This is the pair that
    # makes the anchor opt-in rather than a behavior change.
    assert _match(units, [MatchToken(lit="is")], start=1) == 2


def test_skippables_stay_invisible_to_the_anchor():
    """Skippables are invisible to the token loop, so they must be invisible to
    the anchor too — otherwise a leading article would silently mean a different
    rule than the author wrote. Documented in schemas.MatchToken.at_start."""
    units = [_FakeUnit("the", "article", 0), _FakeUnit("is", "verb", 1)]
    assert _match(units, [MatchToken(lit="is", at_start=True)]) == 2
