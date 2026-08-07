"""Phase B reader 3: negative two-article indefinite generics.

The reader owns exactly ``A/An CLS is not a/an PRED``. It produces a
negative universal, not a ground atom and not an existential claim.
"""

from pathlib import Path

import pytest

from rulekit.data.packs import load_packs
from rulekit.data.registry import compile_registry
from rulekit.kernel import engine
from rulekit.kernel.model import Atom, Quantified


ROOT = Path(__file__).resolve().parents[1]


@pytest.fixture(scope="module")
def logic_reg():
    return compile_registry(
        load_packs([
            ROOT / "packs/core-english",
            ROOT / "packs/arithmetic",
            ROOT / "packs/difg-mined",
            ROOT / "packs/logic",
        ])
    )


def _verdict(text, reg):
    result = engine.solve(text, reg, tracing=False)
    return result.answer.value if result.answer.kind == "verdict" else result.answer.kind


def test_negative_indefinite_generic_emits_exact_universal(logic_reg):
    result = engine.solve("A trout is not a flyer.", logic_reg, tracing=False)

    facts = list(result.store.by_kind(Quantified))
    assert [(fact.cls, fact.pred, fact.polarity) for fact in facts] == [
        ("trout", "flyer", False),
    ]
    assert not list(result.store.by_kind(Atom))


def test_positive_minimal_pair_emits_no_negative_universal(logic_reg):
    result = engine.solve("A trout is a flyer.", logic_reg, tracing=False)

    assert not [fact for fact in result.store.by_kind(Quantified) if not fact.polarity]


def test_negative_indefinite_generic_composes_with_instantiation(logic_reg):
    assert _verdict(
        "A trout is not a flyer. Rex is a trout. "
        "Is it true that Rex is a flyer?",
        logic_reg,
    ) == "no"


def test_articleless_predicate_stays_unread(logic_reg):
    result = engine.solve("A trout is not swift.", logic_reg, tracing=False)

    assert not list(result.store.by_kind(Quantified))


def test_larger_coordinated_predicate_refuses_partial_read(logic_reg):
    result = engine.solve(
        "A trout is not both a flyer and a swimmer.", logic_reg, tracing=False
    )

    assert not list(result.store.by_kind(Quantified))
