"""Mining candidate temporal-offset-age-premises: "In N years, WHO will be
M years old" / "N years ago, WHO was M years old" — a temporal-offset age
premise states the entity's age at a FUTURE or PAST point N years away, not
a direct current holding. Two new pattern rules (packs/arithmetic/rules/
core.yaml) emit the SAME Quantity shape arithmetic/stated-age already does
(measure 'year', a state fact), computed as stated-age MINUS the offset for
the future form and PLUS the offset for the past form — so the unchanged
ask/how-old-is machinery, and the existing relation synthesizers, both
chain through it with no new fact kind and no new consumer.

Decline-safety: a relational/multiplier marker ("twice as old", "half of
X's age") anywhere in the SAME sentence aborts emission (reusing the
`relational_marker`/`multiplier_marker` categories) — those clauses are
left for the relation/ratio machinery.

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


def test_future_offset_age_resolves_current_age(full_registry):
    r = solve(
        "In 4 years, Priya will be 19 years old. How old is Priya now?",
        full_registry,
    )
    assert r.answer.value == 15


def test_past_offset_age_resolves_current_age(full_registry):
    r = solve(
        "Six years ago, Soren was 25 years old. How old is Soren now?",
        full_registry,
    )
    assert r.answer.value == 31


def test_offset_age_chains_through_existing_relation(full_registry):
    # the relation ("Ivy is 3 years older than Wren is now") is stated in a
    # SEPARATE sentence from the offset premise — the abort gate only
    # blocks emission when a relational/multiplier marker shares the SAME
    # sentence as the offset clause, so the offset premise still resolves
    # Ivy's current age, and the existing relation-inverse synthesizer
    # (unchanged) resolves Wren's from it.
    r = solve(
        "Ivy is 3 years older than Wren is now. In 5 years, Ivy will be "
        "30 years old. How old is Wren now?",
        full_registry,
    )
    assert r.answer.value == 22


def test_relational_marker_in_same_clause_declines(full_registry):
    # "twice as old" is a MULTIPLICATIVE age relation, not a plain stated
    # age — the same-sentence relational_marker/multiplier_marker gate
    # must abort emission rather than read the bare "30" as a plain
    # current-minus-offset age.
    r = solve(
        "In 5 years, Oskar will be twice as old as Talia is now. Talia is "
        "9 now. How old is Oskar now?",
        full_registry,
    )
    assert r.answer.kind == "decline"


def test_bare_future_statement_without_years_old_declines(full_registry):
    # no trailing 'years old' anchor at all — outside this pattern's
    # literal-'old' skeleton, must stay declined rather than guess.
    r = solve(
        "In 4 years, Priya will be 19. How old is Priya now?",
        full_registry,
    )
    assert r.answer.kind == "decline"
