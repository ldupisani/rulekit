"""Phase B reader 6: the negative-antecedent same-entity ground conditional.

``If NAME is not P, then NAME is Q`` -> GroundConditional(entity, P, Q):
¬P(e) → Q(e), a dedicated GROUND fact — never a name smuggled into
Conditional.cls. Fired only by synth/ground-conditional-fire on an explicit
negative atom; an undecided antecedent licenses nothing (open world).

Pronoun consequents stay unread until coreference is represented as evidence;
a literal ``he`` cannot safely be assumed to denote the antecedent subject.
"""

from pathlib import Path

import pytest

from rulekit.data.packs import load_packs
from rulekit.data.registry import compile_registry
from rulekit.kernel import engine
from rulekit.kernel.model import GroundConditional


ROOT = Path(__file__).resolve().parents[1]
SOURCES = (
    "logic/ground-conditional-not-then-name-is",
)


@pytest.fixture(scope="module")
def logic_reg():
    return compile_registry(
        load_packs([
            ROOT / "packs/core-english",
            ROOT / "packs/arithmetic",
            ROOT / "packs/difg-mined",
            ROOT / "projects/scratch/packs/logic",
        ])
    )


def _ground_conditionals(text, reg):
    result = engine.solve(text, reg, tracing=False)
    return list(result.store.by_kind(GroundConditional))


def _facts(text, reg):
    return [
        fact for fact in _ground_conditionals(text, reg)
        if fact.provenance.source in SOURCES
    ]


def _verdict(text, reg):
    result = engine.solve(text, reg, tracing=False)
    return result.answer.value if result.answer.kind == "verdict" else result.answer.kind


def test_repeated_name_emits_exact_ground_conditional(logic_reg):
    facts = _facts("If Rex is not a dog, then Rex is a cat.", logic_reg)

    assert [
        (f.entity, f.pred, f.then_pred, f.then_polarity) for f in facts
    ] == [("rex", "dog", "cat", True)]


def test_anaphoric_subject_pronoun_stays_unread(logic_reg):
    assert _ground_conditionals(
        "If Rex is not a dog, then he is a cat.", logic_reg
    ) == []


def test_ambiguous_pronoun_does_not_assert_about_antecedent_subject(logic_reg):
    assert _verdict(
        "If Alice is not taller than Bob, then he is happy. "
        "Alice is not taller than Bob. Is it true that Alice is happy?",
        logic_reg,
    ) == "undetermined"


def test_cross_entity_consequent_stays_unread(logic_reg):
    assert _facts("If Rex is not a dog, then Tom is a cat.", logic_reg) == []


def test_positive_antecedent_is_not_this_reader(logic_reg):
    assert _facts("If Rex is a dog, then Rex is a cat.", logic_reg) == []


def test_coordinated_antecedent_refuses_partial_read(logic_reg):
    assert _facts(
        "If Rex is not a dog and a pet, then Rex is a cat.", logic_reg
    ) == []


def test_negative_consequent_variant_stays_banked(logic_reg):
    assert _facts("If Rex is not a dog, then Rex is not a cat.", logic_reg) == []


def test_explicit_negative_antecedent_fires_the_consequent(logic_reg):
    assert _verdict(
        "If Rex is not a dog, then Rex is a cat. Rex is not a dog. "
        "Is it true that Rex is a cat?",
        logic_reg,
    ) == "yes"


def test_undecided_antecedent_fires_nothing_open_world(logic_reg):
    assert _verdict(
        "If Rex is not a dog, then Rex is a cat. Is it true that Rex is a cat?",
        logic_reg,
    ) == "undetermined"


def test_contrapositive_comes_free_via_reductio(logic_reg):
    # (¬P → Q) ∧ ¬Q ⊢ P needs NO dedicated synth: the Stage 9i reductio
    # engine assumes ¬P, the unless-free fire synth emits Q, Q collides
    # with the stated ¬Q, and the refuted hypothesis commits P. This pin
    # is why the fire synth must never grow an `unless`.
    assert _verdict(
        "If Rex is not a dog, then Rex is a cat. Rex is not a cat. "
        "Is it true that Rex is a dog?",
        logic_reg,
    ) == "yes"


def test_contradictory_consequent_collides_and_declines(logic_reg):
    # No `unless` on the fire synth: the emitted consequent must COLLIDE
    # with its stored opposite so contradictory premises quarantine and the
    # item declines rather than answering through either side.
    result = engine.solve(
        "If Rex is not a dog, then Rex is a cat. Rex is not a dog. "
        "Rex is not a cat. Is it true that Rex is a cat?",
        logic_reg,
        tracing=False,
    )

    assert result.answer.kind != "verdict" or result.answer.value not in ("yes", "no")
    assert result.store.quarantined
