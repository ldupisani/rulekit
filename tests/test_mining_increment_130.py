"""Mining increment 130: role-licensed calendar-point event totals.

All examples are synthetic.  The matrix pins one complete vertical boundary:
calendar vocabulary ownership, exact postverbal temporal-point preservation,
period-specific selection, safe cross-period event totals, and conservative
declines for neighbouring temporal and unresolved constructions.
"""

from __future__ import annotations

from dataclasses import fields, replace
from pathlib import Path

import pytest

from rulekit.data.project import load_project
from rulekit.data.registry import compile_registry
from rulekit.data.schemas import CategoriesDoc
from rulekit.kernel.engine import analyze, solve
from rulekit.kernel.learn import _sentence_time
from rulekit.kernel.model import Quantity


ROOT = Path(__file__).resolve().parents[1]
CURATED = ROOT / "projects" / "curated"
GSM8K = ROOT / "projects" / "gsm8k"
CORE_LEXICON = (ROOT / "packs/core-english/lexicon/core.yaml").resolve()
CORE_CATEGORIES = (ROOT / "packs/core-english/categories/core.yaml").resolve()
CALENDAR_POINTS = {
    "monday",
    "tuesday",
    "wednesday",
    "thursday",
    "friday",
    "saturday",
    "sunday",
    "january",
    "february",
    "march",
    "april",
    "june",
    "july",
    "august",
    "september",
    "october",
    "november",
    "december",
}


@pytest.fixture(scope="module")
def curated_project():
    return load_project(CURATED)


@pytest.fixture(scope="module")
def registry(curated_project):
    return curated_project.registry


def _quantities(result) -> list[Quantity]:
    return list(result.store.by_kind(Quantity))


@pytest.mark.parametrize(("period", "expected"), [("Monday", 4.0), ("Tuesday", 6.0)])
def test_period_specific_event_ask_selects_only_the_exact_period(
    registry, period: str, expected: float
) -> None:
    result = solve(
        "Dara sold 4 books on Monday. Dara sold 6 books on Tuesday. "
        f"How many books did Dara sell on {period}?",
        registry,
    )

    assert result.answer.kind == "number"
    assert result.answer.value == expected
    assert {(q.value, q.time) for q in _quantities(result)} == {
        (4.0, "monday"),
        (6.0, "tuesday"),
    }


def test_answer_accounting_uses_the_same_temporal_origo_as_the_consumer(registry) -> None:
    result = solve(
        "Dara sold 4 books on Monday. Dara sold 6 books on Tuesday. "
        "How many books did Dara sell on Tuesday?",
        registry,
    )

    assert result.answer.value == 6.0
    assert result.veto is None


def test_unscoped_total_sums_explicit_same_verb_event_periods(registry) -> None:
    result = solve(
        "Dara sold 4 books on Monday. Dara sold 6 books on Tuesday. "
        "How many books did Dara sell in total?",
        registry,
    )

    assert result.answer.kind == "number"
    assert result.answer.value == 10.0


def test_state_snapshots_do_not_become_an_unscoped_total(registry) -> None:
    result = solve(
        "Dara had 4 books on Monday. Dara had 6 books on Tuesday. "
        "How many books did Dara have in total?",
        registry,
    )

    assert result.answer.kind == "decline"


def test_period_specific_state_ask_selects_the_exact_snapshot(registry) -> None:
    result = solve(
        "Dara had 4 books on Monday. Dara had 6 books on Tuesday. "
        "How many books did Dara have on Tuesday?",
        registry,
    )

    assert result.answer.kind == "number"
    assert result.answer.value == 6.0


def test_period_ask_declines_mixed_timed_and_untimed_events(registry) -> None:
    result = solve(
        "Dara sold 4 books. Dara sold 6 books on Tuesday. "
        "How many books did Dara sell on Tuesday?",
        registry,
    )

    assert result.answer.kind == "decline"


def test_unscoped_event_ask_declines_cross_verb_timed_evidence(registry) -> None:
    result = solve(
        "Dara sold 4 books on Monday. Dara had 6 books on Tuesday. "
        "How many books did Dara sell?",
        registry,
    )

    assert result.answer.kind == "decline"


@pytest.mark.parametrize("marker", ["before", "after", "by", "during", "from", "until"])
def test_nonpoint_temporal_roles_are_not_stamped_as_exact_time(
    registry, marker: str
) -> None:
    reading = analyze(f"Dara sold 4 books {marker} Monday.", registry)

    assert _sentence_time(reading, registry) is None


def test_multiple_distinct_temporal_point_attachments_are_not_arbitrated(registry) -> None:
    reading = analyze("Dara sold 4 books on Monday and on Tuesday.", registry)

    assert _sentence_time(reading, registry) is None


@pytest.mark.parametrize(
    ("sentence", "expected"),
    [
        ("On Monday, Dara sold 4 books.", "monday"),
        ("By Monday, Dara sold 4 books.", "monday"),
        ("Monday, Dara sold 4 books.", "monday"),
        ("Last year Dara sold 4 books.", "last year"),
        ("This year Dara sold 4 books.", "this year"),
    ],
)
def test_sentence_initial_time_behavior_is_unchanged(
    registry, sentence: str, expected: str
) -> None:
    assert _sentence_time(analyze(sentence, registry), registry) == expected


def test_unresolved_comparative_period_does_not_return_earlier_partial_evidence(
    registry,
) -> None:
    result = solve(
        "Dara sold 4 books on Monday. "
        "Dara sold twice as many books as Eira on Tuesday. "
        "How many books did Dara sell in total?",
        registry,
    )

    assert result.answer.kind == "decline"


def test_unresolved_pronominal_period_does_not_return_earlier_partial_evidence(
    registry,
) -> None:
    result = solve(
        "Dara sold 4 books on Monday. They sold 6 books on Tuesday. "
        "How many books did Dara sell in total?",
        registry,
    )

    assert result.answer.kind == "decline"


def test_month_points_work_in_the_core_only_curated_project(registry) -> None:
    result = solve(
        "Dara sold 4 books in January. Dara sold 6 books in February. "
        "How many books did Dara sell in February?",
        registry,
    )

    assert result.answer.kind == "number"
    assert result.answer.value == 6.0


def test_calendar_vocabulary_and_membership_are_core_owned(curated_project) -> None:
    assert {
        word: curated_project.source_index.lexicon[word].path.resolve()
        for word in CALENDAR_POINTS
    } == {word: CORE_LEXICON for word in CALENDAR_POINTS}
    assert {
        word: curated_project.source_index.category_members[("timeperiod", word)]
        .path.resolve()
        for word in CALENDAR_POINTS
    } == {word: CORE_CATEGORIES for word in CALENDAR_POINTS}
    assert CALENDAR_POINTS <= {
        word
        for word in curated_project.registry.lexicon
        if curated_project.registry.word_in_category(word, "timeperiod")
    }


def test_calendar_vocabulary_is_not_quarantined_or_multiply_owned() -> None:
    project = load_project(GSM8K)
    core, _arithmetic, mined = project.packs

    assert CALENDAR_POINTS <= set(core.lexicon)
    assert CALENDAR_POINTS.isdisjoint(mined.lexicon)
    assert CALENDAR_POINTS.isdisjoint(project.registry.quarantine)
    # May was admitted later as a context-disambiguated modal/month surface;
    # it is deliberately outside this increment's legacy ownership comparison.
    assert "may" not in CALENDAR_POINTS
    assert set(project.registry.lexicon["may"].senses) == {"modal", "noun"}
    assert project.registry.word_in_category("may", "timeperiod")
    assert project.registry.word_in_category("may", "named_month")


def test_combined_registry_semantics_match_the_legacy_mined_ownership() -> None:
    project = load_project(GSM8K)
    core, arithmetic, mined = project.packs
    legacy_core = replace(
        core,
        lexicon={
            word: entry
            for word, entry in core.lexicon.items()
            if word not in CALENDAR_POINTS
        },
        lexicon_sources={
            word: source
            for word, source in core.lexicon_sources.items()
            if word not in CALENDAR_POINTS
        },
        categories=[
            doc.model_copy(
                update={
                    "members": {
                        category: [
                            word
                            for word in words
                            if not (
                                category == "timeperiod"
                                and word in CALENDAR_POINTS
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
            **{word: core.lexicon[word] for word in CALENDAR_POINTS},
        },
        lexicon_sources={
            **mined.lexicon_sources,
            **{word: core.lexicon_sources[word] for word in CALENDAR_POINTS},
        },
        categories=[
            *mined.categories,
            CategoriesDoc.model_validate(
                {
                    "format": "rulekit/categories@1",
                    "members": {"timeperiod": sorted(CALENDAR_POINTS)},
                }
            ),
        ],
    )
    legacy = compile_registry([legacy_core, arithmetic, legacy_mined])
    compared_fields = {
        field.name for field in fields(project.registry) if field.name != "fingerprint"
    }

    assert {
        name
        for name in compared_fields
        if getattr(project.registry, name) != getattr(legacy, name)
    } == set()
