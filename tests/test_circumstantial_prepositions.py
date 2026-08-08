"""Governed accompaniment, instrument, means, manner, cause, and purpose PPs."""

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


def test_adposition_role_table_is_declarative_and_source_indexed() -> None:
    project = load_project(CURATED)
    source = (ROOT / "packs/core-english/categories/core.yaml").resolve()

    assert set(project.registry.adposition_roles) == {
        "accompaniment",
        "cause",
        "instrument",
        "manner",
        "means",
        "purpose",
        "spatial-goal",
        "spatial-location",
        "spatial-path",
        "spatial-source",
        "temporal-after",
        "temporal-approximate",
        "temporal-before",
        "temporal-deadline",
        "temporal-duration",
        "temporal-end",
        "temporal-point",
        "temporal-start",
    }
    assert {
        ref.path.resolve() for ref in project.source_index.adposition_roles.values()
    } == {source}


@pytest.mark.parametrize(
    ("sentence", "role", "marker", "obj", "indefinite"),
    [
        ("Tom worked with Mary.", "accompaniment", "with", "mary", False),
        ("Tom wrote with a pencil.", "instrument", "with", "pencil", True),
        ("Tom traveled by train.", "means", "by", "train", False),
        ("Tom worked with speed.", "manner", "with", "speed", False),
        ("Tom died from an accident.", "cause", "from", "accident", True),
        ("Tom died because of an accident.", "cause", "because of", "accident", True),
        ("Tom died due to an accident.", "cause", "due to", "accident", True),
        ("Tom worked for a purpose.", "purpose", "for", "purpose", True),
    ],
)
def test_governed_circumstance_emits_one_typed_exact_relation(
    sentence: str,
    role: str,
    marker: str,
    obj: str,
    indefinite: bool,
) -> None:
    relation = _relations(sentence)[0]

    assert relation.entity == "tom"
    assert relation.role == role
    assert relation.prep == marker
    assert relation.obj == obj
    assert relation.indef_obj is indefinite


@pytest.mark.parametrize(
    "sentence",
    [
        "Tom bought with a pencil.",  # verb does not license an instrument
        "Tom worked with a pencil.",  # work does not license an instrument
        "Tom wrote with Mary.",  # write does not license accompaniment
        "Tom traveled with a pencil.",  # motion alone does not imply instrument
        "Tom worked for the garden.",  # arbitrary noun is not a purpose
        "Tom died from the garden.",  # arbitrary noun is not a cause
    ],
)
def test_marker_without_governed_role_compatibility_emits_nothing(
    sentence: str,
) -> None:
    assert _relations(sentence) == []
