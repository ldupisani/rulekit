"""Thirty-first Designer review reconciliation.

The eight reviewed strict surfaces expose older premise families that had not
yet adopted the positive holder, finite-form, continuation, and lexical-role
boundaries used by their newer siblings.  The review ledger remains append-
only; these synthetic neighbours preserve the inferred general contracts.
"""

from pathlib import Path

import pytest

from rulekit.data.project import load_project
from rulekit.kernel.engine import solve
from rulekit.kernel.patterns import is_bare_verb_form


@pytest.fixture(scope="module")
def registry():
    return load_project(Path("projects/gsm8k")).registry


def _matched_rules(text: str, registry) -> set[str]:
    result = solve(text, registry)
    return {
        match.match.rule.id
        for matches in result.document.rule_results.values()
        for match in matches
    }


@pytest.mark.parametrize(
    ("rule_id", "sentence"),
    [
        (
            "arithmetic/anchored-relation-conjoined-measures",
            "Ticket attends 6 older diagonals and 5 older scientists than buyer.",
        ),
        (
            "arithmetic/times-as-many-possessive-kinship-standard",
            "The bench visited quadruple as many films in her bench as my ft.",
        ),
        (
            "arithmetic/anaphoric-multiplier-standard-as-many",
            "Salt stayed twice as many.",
        ),
        (
            "arithmetic/anaphoric-multiplier-standard-much",
            "Merry-go-round cough once this much.",
        ),
        (
            "arithmetic/fraction-of-pool",
            "Eron met zero fourths of saturday.",
        ),
        (
            "arithmetic/times-as-many-elided",
            "The hamster knows twice as many as the basketball.",
        ),
        (
            "arithmetic/periodic-rate-every-span",
            "The quart would drinking 3 tricycles every 30 hours.",
        ),
        (
            "arithmetic/percent-change-event-count",
            "Photo changed seven thirds more pounds.",
        ),
    ],
)
def test_reviewed_invalid_surface_no_longer_matches_target(
    rule_id: str, sentence: str, registry
) -> None:
    assert rule_id not in _matched_rules(sentence, registry)


def test_invalid_possessive_standard_cannot_fall_back_to_elision(registry) -> None:
    matched = _matched_rules(
        "The bench visited quadruple as many films in her bench as my ft.",
        registry,
    )

    assert "arithmetic/times-as-many-possessive-kinship-standard" not in matched
    assert "arithmetic/times-as-many-elided-standard" not in matched


@pytest.mark.parametrize(
    ("rule_id", "sentence"),
    [
        (
            "arithmetic/anchored-relation-conjoined-measures",
            "Arden has 6 fewer apples and 5 more pencils than Briar.",
        ),
        (
            "arithmetic/times-as-many-possessive-kinship-standard",
            "Arden has quadruple as many films in her bench as her sister.",
        ),
        (
            "arithmetic/anaphoric-multiplier-standard-as-many",
            "Arden stayed twice as many.",
        ),
        (
            "arithmetic/anaphoric-multiplier-standard-much",
            "Arden paid once this much.",
        ),
        (
            "arithmetic/fraction-of-pool",
            "Eron met one fourth of the teachers.",
        ),
        (
            "arithmetic/times-as-many-elided",
            "The hamster knows twice as many as the teacher.",
        ),
        (
            "arithmetic/periodic-rate-every-span",
            "Arden would produce 3 pages every 30 hours.",
        ),
        (
            "arithmetic/percent-change-event-count",
            "The store has one third more pounds.",
        ),
    ],
)
def test_review_boundaries_preserve_valid_neighbours(
    rule_id: str, sentence: str, registry
) -> None:
    assert rule_id in _matched_rules(sentence, registry)


def test_fraction_pool_requires_a_definite_compatible_object(registry) -> None:
    assert "arithmetic/fraction-of-pool" not in _matched_rules(
        "Eron met one fourth of teachers.", registry
    )
    assert "arithmetic/fraction-of-pool" not in _matched_rules(
        "Eron met one fourth of the saturday.", registry
    )


def test_reviewed_unit_and_progressive_share_their_lexical_lemmas(registry) -> None:
    assert registry.plural_to_singular["ft"] == "foot"
    assert registry.word_in_category("ft", "length_measure")
    assert registry.verb_lemmas["drinking"] == "drink"
    assert not is_bare_verb_form("drinking", registry.verb_lemmas["drinking"])
    assert "arithmetic/periodic-rate-every-span" not in _matched_rules(
        "Arden would drinking 3 tricycles every 30 hours.", registry
    )
