"""Temporal preposition roles preserve their exact markers."""

from pathlib import Path

import pytest

from rulekit.data.project import load_project
from rulekit.kernel.document import run_document
from rulekit.kernel.engine import analyze
from rulekit.kernel.model import VerbalRelation


ROOT = Path(__file__).resolve().parents[1]
CURATED = ROOT / "projects" / "curated"
GSM8K = ROOT / "projects" / "gsm8k"


def _relations(sentence: str) -> list[VerbalRelation]:
    project = load_project(GSM8K)
    reading = analyze(sentence, project.registry, tracing=False)
    document = run_document([reading], project.registry)
    return list(document.store.by_kind(VerbalRelation))


def test_timeperiod_category_and_generic_year_are_core_owned() -> None:
    project = load_project(CURATED)
    source = (ROOT / "packs/core-english/categories/core.yaml").resolve()

    assert project.registry.word_in_category("year", "timeperiod")
    assert project.source_index.categories["timeperiod"].path.resolve() == source
    assert (
        project.source_index.category_members[("timeperiod", "year")].path.resolve()
        == source
    )


def test_temporal_role_categories_compose_under_one_root() -> None:
    project = load_project(CURATED)
    registry = project.registry

    expected = {
        "at": "temporal_point_preposition",
        "before": "temporal_before_preposition",
        "after": "temporal_after_preposition",
        "during": "temporal_duration_preposition",
        "from": "temporal_start_preposition",
        "until": "temporal_end_preposition",
        "by": "temporal_deadline_preposition",
        "about": "temporal_approximate_preposition",
    }
    for marker, role in expected.items():
        assert registry.word_in_category(marker, role)
        assert registry.word_in_category(marker, "temporal_preposition")
    assert not registry.word_in_category("inside", "temporal_preposition")


@pytest.mark.parametrize(
    ("sentence", "marker", "role"),
    [
        ("On Monday, Tom sold apples.", "on", "temporal-point"),
        ("By Monday, Tom sold apples.", "by", "temporal-deadline"),
        ("Tom sold apples before Monday.", "before", "temporal-before"),
        ("Tom sold apples following Monday.", "following", "temporal-after"),
        ("Tom sold apples since Monday.", "since", "temporal-start"),
        ("Tom worked during the year.", "during", "temporal-duration"),
    ],
)
def test_temporal_relation_keeps_the_stated_marker(
    sentence: str, marker: str, role: str
) -> None:
    relation = _relations(sentence)[0]

    assert relation.entity == "tom"
    assert relation.prep == marker
    assert relation.role == role
    assert relation.obj in {"monday", "year"}


def test_same_moment_with_different_markers_remains_distinguishable() -> None:
    on = _relations("On Monday, Tom sold apples.")[0]
    by = _relations("By Monday, Tom sold apples.")[0]

    assert on.obj == by.obj == "monday"
    assert on.prep == "on"
    assert by.prep == "by"
    assert on.key() != by.key()


@pytest.mark.parametrize(
    "sentence",
    [
        "Tom worked for 3 years.",  # counted duration needs a numeric fact
        "Tom worked during the garden.",  # spatial noun is not a timeperiod
        "On Monday Tom sold apples.",  # fronted adjunct needs its boundary
        "On Monday, Tom and Mary sold apples.",  # subject remains ambiguous
    ],
)
def test_unlicensed_temporal_interpretations_emit_no_relation(sentence: str) -> None:
    assert _relations(sentence) == []
