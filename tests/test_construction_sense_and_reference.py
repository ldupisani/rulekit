"""Construction-local sense selection and lossless pronoun-chain projection."""
from pathlib import Path

import pytest
from pydantic import ValidationError

from rulekit.data.project import load_project
from rulekit.data.schemas import AskRule
from rulekit.kernel.document import _local_possessive_subject_candidates
from rulekit.kernel.engine import solve
from rulekit.kernel.learn import _lemma
from rulekit.kernel.model import Obligation, Reading, Unit, Word
from rulekit.kernel.patterns import _lemma_of
from rulekit.kernel.reference_identity import reference_from_unit


@pytest.fixture(scope="module")
def reg():
    return load_project(Path("projects/curated")).registry


@pytest.mark.parametrize("tokens,selection", [
    ([{"lit": "how"}], ["missing"]),
    ([{"slot": "x", "type": "noun"}], ["x"]),
    ([{"slot": "x", "cat": "noun", "span": True}], ["x"]),
    ([{"slot": "x", "cat": "noun"}], ["x", "x"]),
])
def test_ask_sense_selection_requires_unique_category_slots(tokens, selection):
    with pytest.raises(ValidationError):
        AskRule.model_validate({"id": "invented", "match": {"question": tokens},
                                "disambiguates": selection, "resolves": {"consumer": "invented"}})


def test_selected_complete_area_frame_commits_only_its_declared_senses(reg):
    r = solve("The sheet of paper is 8 feet by 6 feet. "
              "Fia cuts a 2 foot by 3 foot rectangle of paper. "
              "How much paper is left in square feet?", reg)
    assert r.value == 42
    selected = [d for d in r.question.decisions if d.kind == "pattern-select-sense"]
    assert {d.target_surface for d in selected} == {"much", "left", "square"}
    assert all(d.rule_id == "ask/material-area-remainder" for d in selected)


def test_incomplete_frame_does_not_select_senses(reg):
    r = solve("How much paper is left in feet?", reg)
    assert not r.answer.committed
    assert not any(d.kind == "pattern-select-sense" for d in r.question.decisions)


@pytest.mark.parametrize("head", ["dena", "teacher"])
def test_pronoun_chain_projects_the_final_identity_in_both_fact_paths(head):
    noun = Unit(0, (Word(head, 0),), {"lemma": head, "senses": ["name" if head == "dena" else "noun"]})
    prior = Unit(1, (Word("her", 1),), {"lemma": "her", "senses": ["pronoun"],
        "obligations": [Obligation("pronoun", "refers", noun)]})
    latest = Unit(2, (Word("she", 2),), {"lemma": "she", "senses": ["pronoun"],
        "obligations": [Obligation("pronoun", "refers", prior)]})
    assert reference_from_unit(latest).head == head
    assert _lemma_of(latest) == _lemma(latest) == head


def test_circular_pronouns_do_not_resolve_to_an_identity():
    a = Unit(0, (Word("her", 0),), {"lemma": "her", "senses": ["pronoun"]})
    b = Unit(1, (Word("she", 1),), {"lemma": "she", "senses": ["pronoun"],
        "obligations": [Obligation("pronoun", "refers", a)]})
    a.features["obligations"] = [Obligation("pronoun", "refers", b)]
    assert not reference_from_unit(a).resolved
    assert _lemma_of(a) == _lemma(a) == "her"


@pytest.mark.parametrize("head,possessive,eligible", [
    ("teacher", "her", True), ("basket", "her", False),
    ("dog", "her", False), ("cat", "his", False), ("basket", "its", True),
])
def test_local_possessive_uses_pack_person_eligibility(reg, head, possessive, eligible):
    reading = Reading("")
    subject = Unit(0, (Word(head, 0),), {"lemma": head, "senses": ["noun"]})
    verb = Unit(1, (Word("has", 1),), {"lemma": "have", "senses": ["verb"],
        "obligations": [Obligation("verb", "subject", subject)]})
    owner = Unit(2, (Word(possessive, 2),), {"lemma": possessive, "senses": ["pronoun"]})
    owned = Unit(3, (Word("box", 3),), {"lemma": "box", "senses": ["noun"], "owner_ref_uid": 2})
    reading.units = [subject, verb, owner, owned]
    assert bool(_local_possessive_subject_candidates(reading, owner, reg)) is eligible


def test_lexical_holder_compatibility_is_shared_by_numeric_variations():
    from types import SimpleNamespace
    from rulekit.generation.sample import _Filler, _measure_holder_assignment_compatible
    calls = []
    reg = SimpleNamespace(measure_applies_to_holder=lambda *args: calls.append(args) or True)
    memo = {}
    holder = _Filler("tree", "tree", kind="noun")
    options = dict(allow_proper_name=False, proper_name_measure_categories=(),
                   when_declared=False, reg=reg, memo=memo)
    for count in (2, 5, 9):
        assert _measure_holder_assignment_compatible(
            _Filler(f"{count} inches", "inch", value=count), holder,
            _Filler("taller", "taller"), **options)
    assert calls == [("inch", "tree", "taller")]
    assert _measure_holder_assignment_compatible(
        _Filler("2 inches", "inch", value=2), holder,
        _Filler("shorter", "shorter"), **options)
    assert calls[-1] == ("inch", "tree", "shorter") and len(calls) == 2


def test_explicit_new_owner_can_use_a_different_possessive_paradigm(reg):
    result = solve("Dena has 6 dollars in her wallet. Cato has 8 dollars in his wallet.", reg)
    for reading, expected in zip(result.premises, ("dena", "cato")):
        wallet = next(u for u in reading.units if u.features.get("lemma") == "wallet")
        assert reference_from_unit(wallet).owner.head == expected
