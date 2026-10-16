"""Core-owned vocabulary for ordinary generated arithmetic premises."""

from dataclasses import fields, replace
from pathlib import Path

import pytest

from rulekit.data.project import load_project
from rulekit.data.registry import compile_registry
from rulekit.data.schemas import CategoriesDoc
from rulekit.generation import generate_candidate, retest_candidate
from rulekit.generation.exploration import exploration_status
from rulekit.kernel.engine import solve


CURATED = Path(__file__).resolve().parents[1] / "projects" / "curated"
GSM8K = Path(__file__).resolve().parents[1] / "projects" / "gsm8k"
CORE_LEXICON = (
    Path(__file__).resolve().parents[1]
    / "packs"
    / "core-english"
    / "lexicon"
    / "core.yaml"
).resolve()
AGE_LITERAL_WORDS = {"ago", "be", "old"}


def _matched_rules(text: str, registry) -> set[str]:
    result = solve(text, registry)
    return {
        match.match.rule.id
        for matches in result.document.rule_results.values()
        for match in matches
    }


@pytest.mark.parametrize(
    ("word", "plural"),
    [
        ("drum", "drums"),
        ("bench", "benches"),
        ("cupboard", "cupboards"),
        ("envelope", "envelopes"),
        ("gardener", "gardeners"),
        ("grape", "grapes"),
        ("guardian", "guardians"),
        ("key", "keys"),
        ("librarian", "librarians"),
        ("apricot", "apricots"),
        ("pantry", "pantries"),
        ("paper", "papers"),
        ("pear", "pears"),
        ("alpaca", "alpacas"),
        ("shopper", "shoppers"),
        ("puzzle", "puzzles"),
        ("storeroom", "storerooms"),
        ("tomato", "tomatoes"),
        ("violinist", "violinists"),
    ],
)
def test_core_count_vocabulary_declares_plural_morphology(
    word: str, plural: str, registry
) -> None:
    assert registry.singular_to_plural[word] == plural
    assert registry.plural_to_singular[plural] == word


@pytest.mark.parametrize(
    "word", ["gardener", "guardian", "librarian", "shopper", "violinist"]
)
def test_new_person_nouns_are_quantity_event_participants(
    word: str, registry
) -> None:
    assert registry.word_in_category(word, "animate")
    assert registry.word_in_category(word, "quantity_event_participant")


@pytest.mark.parametrize("word", ["clay", "paper", "sand", "wool"])
def test_new_mass_nouns_have_the_mass_and_nonholder_boundaries(
    word: str, registry
) -> None:
    assert registry.word_in_category(word, "mass_quantity_noun")
    assert registry.word_in_category(word, "non_quantity_holder")


def test_new_vocabulary_supports_ordinary_count_and_mass_comparisons(
    registry,
) -> None:
    assert "arithmetic/as-many" in _matched_rules(
        "The gardener buys as many pears as the librarian.", registry
    )
    assert "arithmetic/times-as-much" in _matched_rules(
        "Tom buys twice as much sand as Mary.", registry
    )


def test_new_location_and_colour_compatibility_is_explicit(registry) -> None:
    assert "arithmetic/times-as-many" in _matched_rules(
        "Tom buys twice as many pears in his pantry as Mary.", registry
    )
    assert "arithmetic/partition-attribute-of-noun" in _matched_rules(
        "3 of the drums are violet.", registry
    )


def test_new_core_words_are_reachable_generator_fillers() -> None:
    project = load_project(CURATED)
    status = exploration_status(project)
    identities = {item["identity"] for item in status["fillers"]}

    assert len(identities) == 826
    assert {"neighborhood", "neighbourhood"} <= identities
    assert {"family", "household", "team"} <= identities
    assert {"portion", "serving"} <= identities
    assert {"brine", "seawater", "salt", "milliliter", "ml"} <= identities
    assert {"road", "lane", "avenue", "boulevard"} <= identities
    assert "pickle" in identities
    assert "letter" in identities
    assert {
        "ago",
        "able",
        "be",
        "drum",
        "bench",
        "fridge",
        "clay",
        "bucket",
        "barrel",
        "beaker",
        "bottle",
        "bowl",
        "boy",
        "canister",
        "girl",
        "container",
        "color",
        "flask",
        "jar",
        "jug",
        "tank",
        "vessel",
        "vial",
        "scale",
        "water",
        "vinegar",
        "sugar",
        "gram",
        "kilogram",
        "liter",
        "weight",
        "weigh",
        "put",
        "different",
        "purple",
        "yellow",
        "gardener",
        "paper",
        "pear",
        "sand",
        "alpaca",
        "turquoise",
        "old",
        "head",
        "parent",
        "grandparent",
        "purpose",
        "wallet",
        "topic",
        "university",
        "teach",
        "business",
        "course",
        "enroll",
        "humanities",
        "percentage",
        "remaining",
        "science",
        "individually",
        "last",
        "or",
        "which",
        "aboard",
        "because of",
        "next to",
        "out of",
        "earn",
        "examine",
        "make",
        "just",
        "only",
        "babysitting",
        "gardening",
        "tutoring",
        "read",
        "begin",
        "start",
        "tall",
    } <= identities


def test_new_count_word_generates_through_the_equative_rule() -> None:
    candidate = generate_candidate(
        load_project(CURATED),
        rule_id="arithmetic/as-many",
        seed=0,
        locked_bindings={"item": "drums"},
    )

    assert candidate.target_status == "matched"
    assert "drums" in candidate.sentence


def test_required_age_literals_are_owned_by_core_english() -> None:
    project = load_project(CURATED)

    assert {
        word: project.source_index.lexicon[word].path.resolve()
        for word in AGE_LITERAL_WORDS
    } == {word: CORE_LEXICON for word in AGE_LITERAL_WORDS}
    assert project.registry.word_in_category("be", "non_event_verb")


def test_combined_pack_semantics_preserve_the_legacy_literal_ownership() -> None:
    project = load_project(GSM8K)
    core, arithmetic, physics, chemistry, mined = project.packs
    legacy_core = replace(
        core,
        lexicon={
            word: entry
            for word, entry in core.lexicon.items()
            if word not in AGE_LITERAL_WORDS
        },
        lexicon_sources={
            word: source
            for word, source in core.lexicon_sources.items()
            if word not in AGE_LITERAL_WORDS
        },
        categories=[
            doc.model_copy(
                update={
                    "members": {
                        category: [
                            word
                            for word in words
                            if not (
                                category == "non_event_verb" and word == "be"
                            )
                        ]
                        for category, words in doc.members.items()
                    }
                }
            )
            for doc in core.categories
        ],
    )
    legacy_mined = replace(
        mined,
        lexicon={
            **mined.lexicon,
            **{word: core.lexicon[word] for word in AGE_LITERAL_WORDS},
        },
        lexicon_sources={
            **mined.lexicon_sources,
            **{
                word: core.lexicon_sources[word]
                for word in AGE_LITERAL_WORDS
            },
        },
        categories=[
            *mined.categories,
            CategoriesDoc.model_validate(
                {
                    "format": "rulekit/categories@1",
                    "members": {"non_event_verb": ["be"]},
                }
            ),
        ],
    )
    legacy = compile_registry(
        [legacy_core, arithmetic, physics, chemistry, legacy_mined]
    )
    compared_fields = {
        field.name
        for field in fields(project.registry)
        if field.name != "fingerprint"
    }

    assert {
        name
        for name in compared_fields
        if getattr(project.registry, name) != getattr(legacy, name)
    } == set()


@pytest.mark.parametrize(
    ("rule_id", "sentence"),
    [
        (
            "arithmetic/temporal-offset-age-future",
            "In 3 years Dena will be 11 years old.",
        ),
        (
            "arithmetic/temporal-offset-age-past",
            "3 years ago Dena was 11 years old.",
        ),
        (
            "arithmetic/temporal-offset-times-as-old-as-future",
            "In 3 years Dena will be twice as old as Aven.",
        ),
    ],
)
def test_core_age_literal_rules_have_no_unknown_word_deficiency(
    rule_id: str, sentence: str
) -> None:
    candidate = retest_candidate(
        load_project(CURATED),
        rule_id=rule_id,
        sentence=sentence,
        seed=0,
        origin="reading",
    )

    assert candidate.target_status == "matched"
    assert candidate.deficiencies == ()


def test_an_unowned_age_tail_still_reports_a_real_unknown_word() -> None:
    candidate = retest_candidate(
        load_project(CURATED),
        rule_id="arithmetic/temporal-offset-age-future",
        sentence="In 3 years Dena will be 11 years zold.",
        seed=0,
        origin="reading",
    )

    assert candidate.target_status == "absent"
    assert candidate.deficiencies == (
        "I have no information about the word 'zold'.",
    )
