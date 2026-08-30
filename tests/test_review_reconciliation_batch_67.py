"""Review batch 67: positive verb boundaries for mass comparisons."""

from pathlib import Path

import pytest

from rulekit.data.project import load_project
from rulekit.data.schemas import WherePredicate
from rulekit.generation import generate_candidate
from rulekit.kernel.engine import solve


CURATED = Path(__file__).resolve().parents[1] / "projects" / "curated"

MASS_COMPARISON_RULES = (
    "arithmetic/times-as-much",
    "arithmetic/times-as-much-elided",
    "arithmetic/times-as-much-elided-standard",
    "arithmetic/fraction-as-much",
    "arithmetic/fraction-as-much-elided",
    "arithmetic/fraction-as-much-elided-standard",
    "arithmetic/affine-times-as-much",
    "arithmetic/affine-times-as-much-elided",
)


@pytest.fixture(scope="module")
def curated():
    return load_project(CURATED)


def _matched_rules(text: str, registry) -> set[str]:
    result = solve(text, registry)
    return {
        match.match.rule.id
        for matches in result.document.rule_results.values()
        for match in matches
    }


@pytest.mark.parametrize(
    "sentence",
    (
        "Dena reading third as much rest as Cato.",
        "Mary containing six ninths as much vinegar during saturday as their shopper Bira.",
        "Eron knew two ninths as much sand on their bench as Cato.",
        "John adding tenth as much clay during your year as Bira.",
        "Mary enrolled five ninths as much water throughout march as her teacher John.",
    ),
)
def test_latest_reviewed_mass_comparisons_are_rejected(curated, sentence: str) -> None:
    assert "arithmetic/fraction-as-much" not in _matched_rules(
        sentence, curated.registry
    )


@pytest.mark.parametrize(
    ("rule_id", "sentence"),
    (
        ("arithmetic/times-as-much", "Mary knows twice as much sand as Cato."),
        ("arithmetic/times-as-much-elided", "Mary knows twice as much as Cato."),
        ("arithmetic/times-as-much-elided-standard", "Mary knows twice as much sand."),
        ("arithmetic/fraction-as-much", "Mary knows half as much sand as Cato."),
        ("arithmetic/fraction-as-much-elided", "Mary knows half as much as Cato."),
        ("arithmetic/fraction-as-much-elided-standard", "Mary knows half as much sand."),
        (
            "arithmetic/affine-times-as-much",
            "Mary knows 2 more than twice as much sand as Cato.",
        ),
        (
            "arithmetic/affine-times-as-much-elided",
            "Mary knows 2 more than twice as much as Cato.",
        ),
    ),
)
def test_mass_comparison_family_requires_a_supported_quantity_verb(
    curated, rule_id: str, sentence: str
) -> None:
    assert rule_id not in _matched_rules(sentence, curated.registry)


@pytest.mark.parametrize(
    ("sentence", "matched"),
    (
        ("Mary added half as much clay as Cato.", True),
        ("Mary has half as much water as Cato.", True),
        ("Mary bought half as much sugar as Cato.", True),
        ("Mary gave half as much money as Cato.", True),
        ("Mary ate half as much sugar as Cato.", True),
        ("Mary lost half as much rest as Cato.", True),
        ("Mary ate half as much money as Cato.", False),
        ("Mary gave half as much rest as Cato.", False),
        ("Mary enrolled half as much water as Cato.", False),
        ("Mary contains half as much vinegar as Cato.", False),
        ("Mary fits half as much water as Cato.", False),
        ("Mary finished half as much water as Cato.", False),
    ),
)
def test_mass_comparison_reuses_category_owned_object_frames(
    curated, sentence: str, matched: bool
) -> None:
    assert (
        "arithmetic/fraction-as-much"
        in _matched_rules(sentence, curated.registry)
    ) is matched


def test_context_recoverable_finish_stays_in_the_elided_family(curated) -> None:
    assert "arithmetic/fraction-as-much-elided" in _matched_rules(
        "Mary finished half as much as Cato.", curated.registry
    )


def test_temporal_possessive_boundary_shapes_generation_only(curated) -> None:
    sentence = "Mary had half as much water during your year as Cato."
    assert "arithmetic/fraction-as-much" in _matched_rules(
        sentence, curated.registry
    )

    for rule_id in (
        "arithmetic/times-as-much",
        "arithmetic/times-as-much-elided-standard",
        "arithmetic/fraction-as-much",
        "arithmetic/fraction-as-much-elided-standard",
        "arithmetic/affine-times-as-much",
    ):
        for seed in range(24):
            candidate = generate_candidate(curated, rule_id=rule_id, seed=seed)
            bindings = candidate.requested_bindings
            pp_object = bindings.get("pp_obj")
            assert not (
                "pp_det" in bindings
                and pp_object is not None
                and curated.registry.word_in_category(
                    pp_object.casefold(), "timeperiod"
                )
            )


def test_mass_comparison_generation_uses_finite_supported_verbs(curated) -> None:
    for rule_id in MASS_COMPARISON_RULES:
        for seed in range(12):
            candidate = generate_candidate(curated, rule_id=rule_id, seed=seed)
            verb = candidate.requested_bindings["verb"]

            assert not verb.casefold().endswith("ing")
            assert curated.registry.word_in_category(
                verb.casefold(), "quantity_comparison_verb"
            )


def test_declared_frame_requirement_is_an_explicit_schema_option() -> None:
    predicate = WherePredicate(
        verb_roles_compatible={
            "verb": "verb",
            "roles": {"actor": ["who"], "theme": ["item"]},
            "require_declared_frame": True,
        }
    )

    compatibility = predicate.verb_roles_compatible
    assert compatibility is not None
    assert compatibility.require_declared_frame
