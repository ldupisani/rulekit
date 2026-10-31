"""Review-led calendar, possessive, multiplier, and event-role boundaries."""

from pathlib import Path

import pytest

from rulekit.data.project import load_project
from rulekit.generation import generate_candidate, retest_candidate
from rulekit.kernel.engine import solve


CURATED = Path(__file__).resolve().parents[1] / "projects" / "curated"
GSM8K = Path(__file__).resolve().parents[1] / "projects" / "gsm8k"


@pytest.fixture(scope="module")
def project():
    return load_project(CURATED)


@pytest.fixture(scope="module")
def gsm8k_project():
    return load_project(GSM8K)


def _matched_rules(text: str, registry) -> set[str]:
    result = solve(text, registry)
    return {
        match.match.rule.id
        for matches in result.document.rule_results.values()
        for match in matches
    }


REVIEWED_REJECTIONS = [
    (
        "arithmetic/anaphoric-multiplier-conjunct-many",
        "The shopper owns 18 businesses throughout friday and once that many.",
    ),
    (
        "arithmetic/anaphoric-multiplier-conjunct-many",
        "The university has 15 animals at his bench and twice that many.",
    ),
    (
        "arithmetic/affine-times-as-many",
        (
            "The animal began 90 less than once as many inches during the "
            "july as their shopper Bira."
        ),
    ),
    (
        "arithmetic/affine-times-as-many",
        (
            "The guardian found 11 less than twice as many teachers "
            "throughout my tuesday as the rabbit."
        ),
    ),
    (
        "arithmetic/affine-times-as-many",
        (
            "The hamster began 80 less than triple as many shoppers as your "
            "violinist Bira."
        ),
    ),
    (
        "arithmetic/affine-times-as-many",
        (
            "Bira traveled 13 more than double as many times by its june as "
            "my gardener Dena."
        ),
    ),
    (
        "arithmetic/affine-times-as-many",
        (
            "The area earns 8 more than double as many alpacas at wednesday "
            "as its violinist Dena."
        ),
    ),
    (
        "arithmetic/affine-times-as-many",
        (
            "The topic makes 3 less than twice as many pencils in sunday as "
            "her violinist Eron."
        ),
    ),
    (
        "arithmetic/affine-times-as-many",
        (
            "The pantry earns 9 less than once as many cupboards at the "
            "august as the violinist."
        ),
    ),
    (
        "arithmetic/affine-times-as-many",
        (
            "The university starts 11 less than thrice as many envelopes at "
            "their friday as the rabbit."
        ),
    ),
    (
        "arithmetic/affine-times-as-many",
        (
            "The shopper earned 20 fewer than twice as many prices at your "
            "tuesday as the garden."
        ),
    ),
    (
        "arithmetic/affine-times-as-many",
        (
            "The hamster began 3 fewer than twice as many numbers as your "
            "shopper Mary."
        ),
    ),
    (
        "arithmetic/affine-times-as-many",
        (
            "The teacher began 7 more than thrice as many coins throughout "
            "my august as Cato."
        ),
    ),
    (
        "arithmetic/affine-times-as-many",
        (
            "The topic starts 70 fewer than thrice as many books at april as "
            "her guardian Mary."
        ),
    ),
]


@pytest.mark.parametrize(("rule_id", "sentence"), REVIEWED_REJECTIONS)
def test_reviewed_surfaces_retest_absent(
    project, rule_id: str, sentence: str
) -> None:
    candidate = retest_candidate(
        project,
        rule_id=rule_id,
        sentence=sentence,
        seed=0,
        origin="generated",
    )

    assert candidate.target_status == "absent"
    assert rule_id not in _matched_rules(sentence, project.registry)


@pytest.mark.parametrize(
    "sentence",
    [
        "The teacher began 2 more than twice as many courses as Cato.",
        "The shopper earned 2 more than twice as many dollars as Cato.",
        "The teacher made 2 more than twice as many pencils as Cato.",
    ],
)
def test_event_role_boundaries_keep_valid_actor_object_neighbours(
    project, sentence: str
) -> None:
    assert "arithmetic/affine-times-as-many" in _matched_rules(
        sentence, project.registry
    )


def test_corpus_owned_production_object_keeps_the_shared_role_boundary(
    gsm8k_project,
) -> None:
    assert gsm8k_project.registry.word_in_category(
        "button", "producible_quantity_object"
    )
    assert "arithmetic/affine-times-as-many" in _matched_rules(
        "Aven made 4 more than five times as many buttons as Cato.",
        gsm8k_project.registry,
    )


@pytest.mark.parametrize(
    "sentence",
    [
        "The teacher has 2 more than twice as many books on Wednesday as Cato.",
        "The teacher has 2 more than twice as many books in April as Cato.",
        (
            "The teacher has 2 more than twice as many books throughout "
            "Friday as Cato."
        ),
        "The teacher has 2 more than twice as many books during July as Cato.",
        "The teacher has 2 more than twice as many books by June as Cato.",
    ],
)
def test_named_calendar_neighbours_keep_governed_bare_forms(
    project, sentence: str
) -> None:
    assert "arithmetic/affine-times-as-many" in _matched_rules(
        sentence, project.registry
    )


@pytest.mark.parametrize(
    "sentence",
    [
        "The teacher has 2 more than twice as many books at Wednesday as Cato.",
        "The teacher has 2 more than twice as many books in Sunday as Cato.",
        "The teacher has 2 more than twice as many books at April as Cato.",
        "The teacher has 2 more than twice as many books in the August as Cato.",
        "The teacher has 2 more than twice as many books on your Tuesday as Cato.",
    ],
)
def test_named_calendar_forms_reject_wrong_governors_and_determiners(
    project, sentence: str
) -> None:
    assert "arithmetic/affine-times-as-many" not in _matched_rules(
        sentence, project.registry
    )


def test_subject_owned_third_person_pp_requires_an_animate_subject(project) -> None:
    rule_id = "arithmetic/anaphoric-multiplier-conjunct-many"

    assert rule_id in _matched_rules(
        "The teacher owns 15 animals at his bench and twice that many.",
        project.registry,
    )
    assert rule_id in _matched_rules(
        "The university has 15 animals at its bench and twice that many.",
        project.registry,
    )
    assert rule_id not in _matched_rules(
        "The university has 15 animals at his bench and twice that many.",
        project.registry,
    )


def test_anaphoric_that_many_requires_a_nonunit_multiplier(project) -> None:
    rule_id = "arithmetic/anaphoric-multiplier-conjunct-many"

    assert rule_id not in _matched_rules(
        "The shopper owns 18 businesses throughout Friday and once that many.",
        project.registry,
    )
    assert rule_id in _matched_rules(
        "The shopper owns 18 businesses throughout Friday and twice that many.",
        project.registry,
    )


@pytest.mark.parametrize(
    "identity_bindings",
    [
        {"who": "teacher", "verb": "begin", "item": "course", "std": "cato"},
        {"who": "shopper", "verb": "earn", "item": "dollar", "std": "cato"},
        {"who": "teacher", "verb": "make", "item": "pencil", "std": "cato"},
        {
            "who": "teacher",
            "verb": "have",
            "item": "book",
            "pp_prep": "in",
            "pp_obj": "april",
            "std": "cato",
        },
    ],
)
def test_affine_rule_generates_each_new_boundary_neighbour(
    project, identity_bindings: dict[str, str]
) -> None:
    candidate = generate_candidate(
        project,
        rule_id="arithmetic/affine-times-as-many",
        seed=11,
        identity_bindings=identity_bindings,
    )

    assert candidate.target_status in {"matched", "shadowed"}


def test_anaphoric_rule_generates_compatible_subject_owned_pp(project) -> None:
    candidate = generate_candidate(
        project,
        rule_id="arithmetic/anaphoric-multiplier-conjunct-many",
        seed=11,
        identity_bindings={
            "who": "teacher",
            "verb": "own",
            "item1": "animal",
            "pp_prep": "at",
            "pp_det": "his",
            "pp_obj": "bench",
            "k": "twice",
        },
    )

    assert candidate.target_status in {"matched", "shadowed"}
    assert " at his bench " in candidate.sentence.casefold()


def test_pack_declares_calendar_and_event_role_boundaries(project) -> None:
    registry = project.registry

    assert registry.word_in_category("wednesday", "temporal_on_point_object")
    assert not registry.attribute_applies_to("at", "wednesday")
    assert registry.attribute_applies_to("on", "wednesday")
    assert registry.attribute_applies_to("in", "april")
    assert registry.word_in_category("april", "named_calendar_period")
    assert registry.word_in_category("began", "initiation_quantity_verb")
    assert registry.word_in_category("course", "initiable_quantity_object")
    assert registry.word_in_category("earned", "earning_quantity_verb")
    assert registry.word_in_category("dollar", "earnable_quantity_object")
    assert registry.word_in_category("made", "production_quantity_verb")
    assert registry.word_in_category("pencil", "producible_quantity_object")


def test_all_quantitative_pp_slots_keep_named_calendar_objects_bare(project) -> None:
    pp_tokens = [
        token
        for rule in project.registry.rules
        for sequence in rule.match.values()
        for token in _walk_tokens(sequence)
        if token.bare_reference_category == "bare_pp_object"
        # Strictly spatial noun domains do not admit calendar objects. The
        # determinerless calendar contract belongs to slots that can admit one.
        and any(
            project.registry.word_in_category(word, token.cat or token.common_noun_cat or "noun")
            for word in project.registry.cat_members_deep("named_calendar_period")
        )
    ]

    assert pp_tokens
    assert all(
        token.determinerless_category == "named_calendar_period"
        for token in pp_tokens
    )


def _walk_tokens(sequence):
    for token in sequence:
        if isinstance(token, list):
            yield from _walk_tokens(token)
            continue
        yield token
        if token.opt is not None:
            yield from _walk_tokens(token.opt)
