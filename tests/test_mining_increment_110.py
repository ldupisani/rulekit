"""Mining increment 110: comparative-DIFFERENCE asks
over a physical dimension or an age ("how many inches taller is A than B",
"how much older is A than B", "how much taller is A than B in inches").

The RELATION half of this family (arithmetic/anchored-relation-postfix-
dimension, arithmetic/times-comparative-age-relation) already existed; this
candidate adds the missing ASK side, routed to the existing `difference`
consumer. Two new mechanisms ship with it:

- an opt-in leading-possessive-pronoun slot before the standard, so "than
  his sister" resolves the STANDARD to the noun ("sister"), never back to
  the pronoun's own antecedent (the subject itself) — a single-unit `std`
  slot would otherwise bind the pronoun first and silently difference an
  entity against itself;
- `_entity_total_convertible` (answer.py), an opt-in fold (query flag
  `fold_units`) that sums an entity's quantities across CONVERTIBLE SIBLING
  UNITS ("6 feet, 3 inches" is two separate Quantity facts for one entity)
  through `reg.conversions` before differencing, declining rather than
  guessing when nothing the entity holds converts to the asked measure.

Synthetic only — every name/number below is invented, none reused from any
GSM8K item."""

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


def test_leading_unit_dimension_ask_folds_compound_height(full_registry):
    # "5 feet, 4 inches" = 64 inches; "4 feet, 9 inches" = 57 inches.
    r = solve(
        "Priya is 5 feet, 4 inches tall. Her cousin is 4 feet, 9 inches tall. "
        "How many inches taller is Priya than her cousin?",
        full_registry,
    )
    assert r.answer.value == 7


def test_trailing_unit_dimension_ask_folds_compound_height(full_registry):
    # the sibling surface order: unit named AFTER the standard, not before
    # the comparative. "5 feet, 0 inches" = 60; "5 feet, 6 inches" = 66.
    r = solve(
        "Delia is 5 feet, 0 inches tall and Farid is 5 feet, 6 inches tall. "
        "How much taller is Farid than Delia in inches?",
        full_registry,
    )
    assert r.answer.value == 6


def test_age_comparative_ask_no_unit_needed(full_registry):
    # measure 'year' is a pack-owned constant, exactly like stated-age's own
    # implicit 'old' anchor — no unit noun appears in this ask at all.
    r = solve(
        "Milo is 14 years old. Priya is 11 years old. "
        "How much older is Milo than Priya?",
        full_registry,
    )
    assert r.answer.value == 3


def test_possessive_standard_does_not_rebind_to_the_subject(full_registry):
    # "than her cousin" must resolve the STANDARD to 'cousin' (the entity
    # the premise actually keyed the fact on), never back to whichever name
    # the leading possessive pronoun refers to (Priya herself) — the naive
    # bug this candidate's brief specifically names: a single-unit `std`
    # slot binding the PRONOUN first would difference Priya against
    # herself (0), not against her cousin (7).
    r = solve(
        "Priya is 5 feet, 4 inches tall. Her cousin is 4 feet, 9 inches tall. "
        "How many inches taller is Priya than her cousin?",
        full_registry,
    )
    assert r.answer.value != 0
    assert r.answer.value == 7


def test_unconvertible_sibling_measure_declines_rather_than_commits(full_registry):
    # Noor's height is a clean feet+inches compound (foldable), but her
    # brother's ONLY stated quantity is an unrelated measure (pounds) with
    # no declared conversion to inches at all — the whole ask must decline,
    # never guess a total for him from an empty (unconvertible) fold.
    r = solve(
        "Noor is 5 feet, 2 inches tall. Her brother weighs 90 pounds. "
        "How many inches taller is Noor than her brother?",
        full_registry,
    )
    assert r.answer.kind == "decline"


def test_bare_name_standard_still_works_without_a_pronoun(full_registry):
    # the optional leading-pronoun slot must not become REQUIRED — a bare
    # name standard ("than Farid") is unaffected.
    r = solve(
        "Delia is 5 feet, 0 inches tall and Farid is 5 feet, 6 inches tall. "
        "How much taller is Farid than Delia in inches?",
        full_registry,
    )
    assert r.answer.kind == "number"
