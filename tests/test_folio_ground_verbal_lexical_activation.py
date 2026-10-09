"""Pack-local regular-past forms activate the existing ground reader."""

from pathlib import Path

import pytest

from rulekit.data.project import load_project
from rulekit.kernel.engine import solve
from rulekit.kernel.model import Atom


REGISTRY = load_project(Path("projects/scratch")).registry
SOURCE = "logic/ground-verbal"


def _facts(text: str) -> list[Atom]:
    return [
        fact
        for fact in solve(text, REGISTRY, tracing=False).store.by_kind(Atom)
        if fact.provenance.source == SOURCE
    ]


@pytest.mark.parametrize(
    ("surface", "expected"),
    [
        ("Ada supported the local artists.", ("ada", "support local artist", True)),
        ("Grace researched numerical methods.", ("grace", "research numerical method", True)),
    ],
)
def test_regular_past_forms_preserve_tense_normalized_keys(
    surface: str, expected: tuple[str, str, bool]
) -> None:
    facts = _facts(surface)
    assert [(f.entity, f.pred, f.polarity) for f in facts] == [expected]


@pytest.mark.parametrize(
    "surface",
    [
        "Ada did not support the local artists.",
        "Grace will research numerical methods.",
        "Numerical methods were researched by Grace.",
    ],
)
def test_adjacent_signed_modal_and_passive_forms_do_not_use_ground_reader(
    surface: str,
) -> None:
    assert _facts(surface) == []
