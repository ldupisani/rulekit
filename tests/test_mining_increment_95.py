"""Mining increment 95: sum-constraint premise
surfaces (a stated group total phrased as "the sum of their AGES is N",
"Together, they have N ITEM", "a combined AGE of N") feeding the EXISTING
synth/sum-constraint linear-system solver (saturate.py, unchanged in its
2x2-solve logic).

Mechanism: YAML-first, three new pattern rules in packs/arithmetic/rules/
core.yaml, all emitting the pre-existing GroupTotal fact:

- arithmetic/group-total-leading-marker: the same "SUBJ VERB N ITEM" tail
  arithmetic/group-total-leading already reads, fronted by a BARE `cat:
  aggregate` marker ('together'/'combined'/'altogether'/'total') instead of
  that rule's own required literal "in total" — "Together, they have 40
  marbles." previously declined outright (no aggregate premise rule's
  skeleton matched it at all).
- arithmetic/group-total-sum-of-age: a COPULAR "the sum of their ages is N"
  constraint — 'sum'/'of' framing with the age noun and the value on
  OPPOSITE sides of the copula, a shape no existing group-total-* rule
  reads. Gated on a new single-word `age_noun` category (packs/core-
  english/categories/core.yaml + packs/difg-mined/categories/semantic.yaml
  for the member itself, mirroring 'child'/'toy'/'fish') so it can emit the
  hardcoded DATA measure 'year' the age family already commits to
  everywhere (arithmetic/stated-age, ask/how-old-is) — never a bare 'age'
  measure key nothing else would match.
- arithmetic/group-total-of-age: an AGGREGATE-QUALIFIED age NP — "a
  combined age of N" — generalizing arithmetic/group-total-of's literal
  'total' to the full `aggregate` category, restricted to `age_noun` so it
  never collides with group-total-of's own ordinary "a total of N ITEM"
  shape.

Plus one saturate.py change: synth/sum-constraint's measure-matching now
also tries the pre-existing interchangeable-category bridge
(_resolve_measure_against, answer.py — the SAME 'money'->'dollar' bridge a
bare how-much ask already uses) when no EXACT measure match exists, so a
relation stated as "three times as much MONEY as" resolves against a group
total stated as a bare "$N" (which senses.py already reads as the DATA
measure 'dollar'). The exact-match path is untouched and always unioned
with the bridged one, so a genuinely ambiguous pairing (an exact match AND
a bridged one both present) still declines exactly like two exact matches
already do.

Synthetic only.
"""

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


def test_copular_sum_of_ages_solves_offset_relation(full_registry):
    # arithmetic/group-total-sum-of-age: "the sum of their ages is N" —
    # standard(Omar) = (40 - 6) / 2 = 17, subject(Priya) = 40 - 17 = 23.
    r = solve(
        "Priya is 6 years older than Omar. "
        "If the sum of their ages is 40, how old is Priya?",
        full_registry,
    )
    assert r.answer.kind == "number"
    assert r.answer.value == 23


def test_leading_bare_marker_together_solves_offset_relation(full_registry):
    # arithmetic/group-total-leading-marker: a bare 'together' fronting the
    # clause, no literal "in total" anywhere — declined on main before this
    # candidate. standard(Kai) = (40 - 8) / 2 = 16, subject(Zoe) = 24.
    r = solve(
        "Zoe has 8 more marbles than Kai. "
        "Together, they have 40 marbles. "
        "How many marbles does Zoe have?",
        full_registry,
    )
    assert r.answer.kind == "number"
    assert r.answer.value == 24


def test_leading_bare_marker_combined_no_comma(full_registry):
    # the same rule, a different `aggregate` word ('combined') and no comma
    # after it at all — punctuation is optional, never required.
    # standard(Zane) = (50 - 10) / 2 = 20, subject(Mia) = 50 - 20 = 30.
    r = solve(
        "Mia has 10 more pens than Zane. "
        "Combined they have 50 pens. "
        "How many pens does Mia have?",
        full_registry,
    )
    assert r.answer.kind == "number"
    assert r.answer.value == 30


def test_leading_in_total_still_resolves_unchanged(full_registry):
    # regression: the pre-existing literal "in total" rule (arithmetic/
    # group-total-leading) must keep working byte-identically alongside
    # the new bare-marker sibling — same numbers as the 'together' test.
    r = solve(
        "Zoe has 8 more marbles than Kai. "
        "In total, they have 40 marbles. "
        "How many marbles does Zoe have?",
        full_registry,
    )
    assert r.answer.kind == "number"
    assert r.answer.value == 24


def test_combined_age_of_solves_offset_relation(full_registry):
    # arithmetic/group-total-of-age: "a combined age of N" — the aggregate
    # word qualifies the age noun directly, fronting the bare number, a
    # token order arithmetic/group-total-of's own literal-'total' skeleton
    # cannot match. Same solve as the copular test above: Priya = 23.
    r = solve(
        "Priya is 6 years older than Omar. "
        "They have a combined age of 40. "
        "How old is Priya?",
        full_registry,
    )
    assert r.answer.kind == "number"
    assert r.answer.value == 23


def test_combined_age_of_with_trailing_unit_word(full_registry):
    # the same rule when the number condenses with a trailing 'years' noun
    # ("...of 40 years") instead of standing bare — the hardcoded 'year'
    # measure below never depended on capturing that unit word at all.
    r = solve(
        "Priya is 6 years older than Omar. "
        "They have a combined age of 40 years. "
        "How old is Priya?",
        full_registry,
    )
    assert r.answer.kind == "number"
    assert r.answer.value == 23


def test_currency_bridge_money_relation_dollar_total(full_registry):
    # the saturate.py bridge: a relation stated as "three times as much
    # MONEY as" resolves against a group total stated as a bare "$N"
    # (DATA measure 'dollar') via the pre-existing interchangeable-
    # category machinery. standard(Omar) = 120 / 4 = 30, subject(Priya) =
    # 120 - 30 = 90.
    r = solve(
        "Priya has three times as much money as Omar. "
        "They have a combined total of $120. "
        "How much money does Priya have?",
        full_registry,
    )
    assert r.answer.kind == "number"
    assert r.answer.value == 90


def test_sum_of_non_age_noun_declines(full_registry):
    # decline-safety: arithmetic/group-total-sum-of-age is gated on the
    # single-word `age_noun` category — a DIFFERENT noun after "the sum of
    # their..." never satisfies it, so no GroupTotal is emitted and the
    # ordinary ask still correctly declines rather than guessing.
    r = solve(
        "Zane has 5 more sandwiches than Wren. "
        "The sum of their snacks is 21. "
        "How many sandwiches does Zane have?",
        full_registry,
    )
    assert r.answer.kind != "number"


def test_currency_bridge_ambiguous_with_two_relations_declines(full_registry):
    # decline-safety: an EXACT-measure 'dollar' relation and a BRIDGED
    # 'money' relation both present for the same total is genuinely
    # ambiguous (the plugin cannot guess which pair the total spans) — the
    # bridge must never override the pre-existing "exactly one relation"
    # ambiguity guard.
    r = solve(
        "Priya has three times as much money as Omar. "
        "Zane has 5 more dollars than Wren. "
        "They have a combined total of $120. "
        "How much money does Priya have?",
        full_registry,
    )
    assert r.answer.kind != "number"


def test_leading_bare_marker_without_relation_declines(full_registry):
    # decline-safety: a GroupTotal alone, with no Relation over the same
    # measure anywhere in the passage, must never manufacture an answer —
    # synth/sum-constraint's own "exactly one relation" guard still applies
    # unchanged to a GroupTotal emitted by this new rule.
    r = solve(
        "Together, they have 40 marbles. "
        "How many marbles does Zoe have?",
        full_registry,
    )
    assert r.answer.kind != "number"
