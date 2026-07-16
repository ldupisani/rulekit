"""Vector domain (difg): magnitude and dot product over a spaced tuple.

SYNTHETIC ONLY (constitution rule 3): invented components, not difg CASES.

A SPACED tuple "(1, 2, 3)" is three loose number tokens — the tokenizer drops
the parens and splits on whitespace — so this family reads the question's whole
number list (the `list-statistic` template) rather than binding a `point` the
way tests/test_coordinate.py's "(1,2)" single-token form does.

Also pins the `bare: true` gate the dot product forced: a compound noun keeps
its HEAD's lemma, so before it, "the dot product of ..." matched the
`statistic`-gated ask as "the product of ..." and committed the product of every
component.
"""

from pathlib import Path

import pytest

from rulekit.data.project import load_project
from rulekit.kernel.engine import solve


@pytest.fixture(scope="module")
def reg():
    return load_project(Path("projects/difg")).registry


@pytest.mark.parametrize(
    "question, want",
    [
        ("What is the magnitude of the vector (6, 8)?", 10.0),
        ("What is the magnitude of (8, 15)?", 17.0),
        # arity is free: the consumer reads however many components are there
        ("What is the magnitude of the vector (2, 3, 6)?", 7.0),
        ("What is the dot product of (2, 3) and (4, 5)?", 23.0),
        ("What is the dot product of (1, 0, 2) and (3, 7, 4)?", 11.0),
    ],
)
def test_operation(reg, question, want):
    r = solve(question, reg, tracing=False)
    assert r.answer.committed, (r.answer.reason or "")
    assert r.answer.value == pytest.approx(want)


def test_odd_component_count_declines(reg):
    """Definitive-or-decline: an odd count cannot be two equal-length vectors,
    so the consumer declines rather than guessing where to split."""
    r = solve("What is the dot product of (1, 2, 3) and (4, 5)?", reg, tracing=False)
    assert not r.answer.committed


# --- the `bare: true` gate ------------------------------------------------


def test_dot_product_is_not_a_product(reg):
    """REGRESSION: a compound noun keeps its HEAD's lemma, so a `statistic`-gated
    slot could not tell "the dot product" from "the product" — and answered the
    product of all six components. The dot product of (2,3) and (4,5) is 23; the
    product of 2,3,4,5 is 120. Pin that it is 23 and never 120."""
    r = solve("What is the dot product of (2, 3) and (4, 5)?", reg, tracing=False)
    assert r.answer.committed, (r.answer.reason or "")
    assert r.answer.value == pytest.approx(23.0)
    assert r.answer.value != pytest.approx(120.0)


def test_bare_statistic_still_reads(reg):
    """`bare: true` must reject ONLY the modified form. An unmodified statistic
    name is the overwhelmingly common case and must be untouched."""
    r = solve("What is the product of 2, 3, and 4?", reg, tracing=False)
    assert r.answer.committed, (r.answer.reason or "")
    assert r.answer.value == pytest.approx(24.0)


def test_a_compound_is_still_its_head_elsewhere(reg):
    """`bare` is OPT-IN for a reason: for most categories a compound IS its head
    — a chocolate cake IS a cake, and every entity/superordinate gate depends on
    that. Only the operation-naming slot sets `bare`, so ordinary compound-noun
    reading must be untouched."""
    r = solve(
        "Sam has 4 chocolate cakes and 3 pies. How many cakes does Sam have?",
        reg, tracing=False,
    )
    assert r.answer.committed, (r.answer.reason or "")
    assert r.answer.value == pytest.approx(4.0)
