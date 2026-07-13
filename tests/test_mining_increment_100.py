"""Mining candidate that-relative-clause-binding: restrictive relative
clauses headed by 'that' on a numeral antecedent ("5 candles that each
cost $3", "10 lessons that cost $10 each") — the clause's own verb was
previously mis-read as a NOUN.

Mechanism:
  1. `obligations.py::_relative_clause_subject_antecedent` — a price/
     measure verb's `subject` obligation is normally blocked from
     crossing a 'that' complementizer (`_crosses_clause_boundary`), which
     leaves the obligation permanently unmet and tips coverage
     arbitration into a NOUN reading (merged with its trailing value by
     condense's compound pass) before any fold ever runs. This adds a
     single, narrowly gated override inside `_candidates`: a 'that'
     immediately following a COUNTED noun is a relative pronoun on that
     noun (never a subordinating complementizer, which is preceded by a
     VERB, e.g. "found out THAT 7 caps weigh..."), and the verb whose
     clause that SAME 'that' introduces may bind its subject to that
     antecedent. This is consulted from BOTH disambiguation's own
     coverage-scoring trial (pre-condense, where "counted" is read off a
     value's already-bound `quantifies` obligation) and the real, final
     bind pass (post-condense, where "counted" is the merged noun's
     `value_kind` feature) — both call the identical function.
  2. `learn.py::_relative_clause_distributive_price` — a floating 'each'/
     'every' immediately after that SAME 'that' and immediately before
     the price_verb is the distributive determiner scoped over the
     antecedent, joining the existing `_has_distributive_determiner`/
     trailing-each/bare-measure/indefinite-singular gates in the
     price_verb branch. A quantifier's own `collection` obligation is
     direction=right only, so it can never reach the antecedent the way
     `subject` now can; this is a narrow, local adjacency check (mirror
     of #1's gate) rather than a widening of the shared `collection`
     candidate search.

Both are structural: no lexicon, no per-problem branching. A 'which'-
headed relative clause (already working, tests/test_mining_increment_91.py)
and an ordinary subordinating 'that'-clause ("found out that 7 caps
weigh...") are unaffected — see the decline-safety tests below.

Synthetic only."""

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


def test_that_headed_floating_each_price(full_registry):
    # "5 candles THAT EACH cost $P" — the class's headline shape.
    r = solve(
        "Priya buys 6 candles that each cost $4. How much does Priya pay?",
        full_registry,
    )
    assert r.answer.value == 24


def test_that_headed_trailing_each_price(full_registry):
    # "N lessons THAT cost $P each" — the trailing-each mirror; the
    # ordinary _is_rate/_price_each_value scan already handles the token
    # shape once the subject can bind at all.
    r = solve(
        "Priya buys 8 lessons that cost $5 each. How much does Priya pay?",
        full_registry,
    )
    assert r.answer.value == 40


def test_that_headed_price_with_discount(full_registry):
    # a second premise (a percent discount) proves the Price fact is
    # genuinely readable downstream, not just present in isolation —
    # the structural sample this candidate targets (item 0b70dc5a080f).
    r = solve(
        "Priya buys 5 candles that each cost $3. "
        "She gets a 20% discount. How much did she pay for everything?",
        full_registry,
    )
    assert r.answer.value == 12


def test_which_headed_still_works(full_registry):
    # the already-working sibling (increment 91) must be completely
    # unaffected by this change: 'which' was never blocked by
    # _crosses_clause_boundary in the first place (not a complementizer).
    r = solve(
        "Priya buys 6 candles which each cost $4. How much does Priya pay?",
        full_registry,
    )
    assert r.answer.value == 24


def test_subordinating_that_clause_declines():
    # decline-safety: an ORDINARY subordinating 'that'-clause is preceded
    # by a VERB ("found out"), never a counted noun — the antecedent gate
    # must not fire here, so the clause's own verb still cannot borrow a
    # subject it was never given.
    mined = REPO / "packs/difg-mined"
    if not mined.exists():
        pytest.skip("difg-mined not generated")
    reg = compile_registry(
        load_packs([REPO / "packs/core-english", REPO / "packs/arithmetic", mined])
    )
    r = solve(
        "Omar found out that 7 caps weigh 3 pounds. How many caps does Omar have?",
        reg,
    )
    assert r.answer.kind == "decline"


def test_bare_relative_clause_no_each_still_declines(full_registry):
    # a 'that'-relative clause stating a LUMP SUM (no distributive
    # quantifier at all) is not a per-unit price — must still decline,
    # exactly like the 'which' sibling (increment 91's own invariant).
    r = solve(
        "Priya buys 6 candles that cost $24 in total. How much does Priya pay?",
        full_registry,
    )
    assert r.answer.kind == "decline"
