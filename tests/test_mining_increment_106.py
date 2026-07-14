"""Mining candidate temporal-offset-age-recut: leading-temporal-offset
equative age relations ("In N years, A will be K times as old as B" / "N
years ago, A was K times as old as B").

Three new pattern rules (packs/arithmetic/rules/core.yaml):

- arithmetic/temporal-offset-times-as-old-as-future: the bare future form,
  "In N years, WHO will be K times as old as STD" — both sides of the
  ratio inherit the sentence's own future offset.
- arithmetic/temporal-offset-times-as-old-as-future-std-now: the sibling
  where the standard is explicitly pinned to the present ("...as STD is
  now" / "...as STD today") — only the subject carries the offset.
- arithmetic/temporal-offset-times-as-old-as-past: the past mirror, "N
  years ago, WHO was K times as old as STD" — both sides inherit the
  sentence's own NEGATIVE offset.

All three emit the existing Relation fact plus two new signed-year fields,
`subject_offset`/`standard_offset` (model.py, default 0.0 = today, included
in `key()`). `_relations_synth` (saturate.py) resolves the general equation
age(subject)+subject_offset = factor*(age(standard)+standard_offset)+offset
in either direction — forward (standard known, solve subject) or inverse
(subject known, solve standard) — with a genuinely negative resolved age
declining rather than being committed, scoped to offset-bearing relations
only. A self-referential (same lemma AND label) relation also declines
rather than attempting a linear solve this synth does not perform.

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


def test_bare_future_forward_resolves_subject_from_standard(full_registry):
    # bare comparative, no trailing "is now"/"today" marker on the
    # standard — both sides inherit the sentence's own future offset (6).
    # Odalys's current age (4) resolves Farrukh's: 3*(4+6)-6 = 24.
    r = solve(
        "In 6 years, Farrukh will be three times as old as Odalys. Odalys "
        "is 4 now. How old is Farrukh now?",
        full_registry,
    )
    assert r.answer.kind == "number"
    assert r.answer.value == pytest.approx(24.0)


def test_bare_future_inverse_resolves_standard_from_subject(full_registry):
    # the INVERSE direction: Wilhelmina's own current age is stated, and
    # Thaddeus (the standard) is what the ask wants.
    # ((30+4)-0)/2 - 4 = 13.
    r = solve(
        "In 4 years, Wilhelmina will be twice as old as Thaddeus. "
        "Wilhelmina is 30 now. How old is Thaddeus now?",
        full_registry,
    )
    assert r.answer.kind == "number"
    assert r.answer.value == pytest.approx(13.0)


def test_future_standard_pinned_to_now_with_copula(full_registry):
    # "...as old as Zephyr IS NOW" pins standard_offset to 0 while the
    # subject still carries the sentence's own future offset (8).
    # 3*(5+0) - 8 = 7.
    r = solve(
        "In 8 years, Priyanka will be three times as old as Zephyr is "
        "now. Zephyr is 5 now. How old is Priyanka now?",
        full_registry,
    )
    assert r.answer.kind == "number"
    assert r.answer.value == pytest.approx(7.0)


def test_future_standard_pinned_to_today_bare_adverb(full_registry):
    # the bare trailing-adverb form ("...as Deshawn TODAY", no copula) —
    # same standard-pinned equation as the "is now" form above.
    # 2*(12+0) - 10 = 14.
    r = solve(
        "In 10 years, Marisol will be twice as old as Deshawn today. "
        "Deshawn is 12 now. How old is Marisol now?",
        full_registry,
    )
    assert r.answer.kind == "number"
    assert r.answer.value == pytest.approx(14.0)


def test_past_offset_bare_resolves_subject(full_registry):
    # the past mirror: both sides inherit the sentence's own NEGATIVE
    # offset (-5). Emeka's current age (10) resolves Rosalind's:
    # 3*(10-5) - (-5) = 15 + 5 = 20.
    r = solve(
        "5 years ago, Rosalind was three times as old as Emeka. Emeka is "
        "10 now. How old is Rosalind now?",
        full_registry,
    )
    assert r.answer.kind == "number"
    assert r.answer.value == pytest.approx(20.0)


def test_self_referential_standard_declines(full_registry):
    # decline-safety: subject and standard are the SAME token — the
    # rule's own `distinct: [who, std]` where-clause blocks emission
    # entirely, so no Relation ever forms and the item stays declined
    # rather than solving a nonsense self-referential equation.
    r = solve(
        "In 5 years, Xiomara will be twice as old as Xiomara. How old is "
        "Xiomara now?",
        full_registry,
    )
    assert r.answer.kind == "decline"


def test_negative_resolved_age_declines(full_registry):
    # decline-safety: the future-std-now forward equation resolves to a
    # NEGATIVE age (2*(3+0) - 10 = -4) — a malformed/unrealistic premise
    # that must be declined, never committed as a confident-wrong answer.
    r = solve(
        "In 10 years, Consuelo will be twice as old as Bertrand is now. "
        "Bertrand is 3 now. How old is Consuelo now?",
        full_registry,
    )
    assert r.answer.kind == "decline"
