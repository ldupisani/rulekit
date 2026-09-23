"""Explicit construction links are independent of pronoun-form compatibility."""

from pathlib import Path

import pytest
from pydantic import ValidationError

from rulekit.data.packs import LoadedPack
from rulekit.data.project import load_project
from rulekit.data.registry import CompileError, compile_registry
from rulekit.data.schemas import LexiconEntry, PackDoc, PatternRule, RulesDoc
from rulekit.kernel.model import Obligation, PATTERN, Unit, Word
from rulekit.kernel.reference_bindings import anaphoric_forms_agree, project_references
from rulekit.kernel.reference_identity import reference_from_unit


@pytest.fixture(scope="module")
def reg():
    return load_project("projects/curated").registry


def unit(uid, surface, sense, **features):
    return Unit(uid, (Word(surface, uid),), {
        "senses": [sense], "lemma": surface.casefold(), "number": "singular", **features,
    })


@pytest.mark.parametrize("forms,number,expected", [
    (["her", "she"], "singular", True),
    (["his", "he", "him"], "singular", True),
    (["their", "they"], "singular", True),
    (["their", "they"], "plural", True),
    (["its", "it"], "singular", True),
    (["her", "she"], "plural", False),
    (["his", "they"], "singular", False),
    (["her", "he"], "singular", False),
    (["missing", "missing"], "singular", False),
    (["she", "missing"], "singular", False),
    (["my", "she"], "singular", False),
    ([], "singular", False),
])
def test_form_agreement_is_positive_lexical_evidence(reg, forms, number, expected):
    assert anaphoric_forms_agree(forms, number, reg) is expected


def test_projection_is_pure_and_preserves_real_target_and_owned_identity(reg):
    target = unit(0, "Aven", "name")
    poss = unit(1, "her", "pronoun", obligations=[Obligation("pronoun", "refers")])
    noun = unit(2, "nickname", "noun", owner="her", owner_resolved=False, owner_ref_uid=1)
    outcome = unit(3, "she", "pronoun", obligations=[Obligation("pronoun", "refers")])
    slots = {"who": target, "poss": poss, "attribute": noun, "outcome": outcome}
    projected = project_references({"poss": "who", "outcome": "who"}, slots, reg)
    assert projected is not None
    assert projected["outcome"].obligations()[0].target is target
    assert reference_from_unit(projected["attribute"]).owner == reference_from_unit(target)
    assert not poss.obligations()[0].met
    assert not outcome.obligations()[0].met
    assert noun.features["owner"] == "her"


@pytest.mark.parametrize("target_kind", ["different", "group", "sentinel"])
def test_explicit_links_do_not_overwrite_conflicting_prior_references(reg, target_kind):
    target, other = unit(0, "Aven", "name"), unit(1, "Bira", "name")
    prior = {"different": other, "group": (target, other), "sentinel": PATTERN}[target_kind]
    source = unit(2, "she", "pronoun", obligations=[Obligation("pronoun", "refers", prior)])
    assert project_references({"source": "target"}, {"source": source, "target": target}, reg) is None
    assert source.obligations()[0].target is prior


def test_explicit_name_must_be_same_identity_and_missing_forms_fail(reg):
    target, other = unit(0, "Aven", "name"), unit(1, "Bira", "name")
    assert project_references({"source": "target"}, {"source": other, "target": target}, reg) is None
    assert project_references({"source": "target"}, {"target": target}, reg) is None
    assert project_references({"source": "target"}, {"source": target, "target": target}, reg)


def test_resolved_pronoun_anchor_keeps_form_agreement_separate_from_referent_number(reg):
    name = unit(0, "Aven", "name")
    target = unit(1, "they", "pronoun", number="plural",
                  obligations=[Obligation("pronoun", "refers", name)])
    source = unit(2, "their", "pronoun", obligations=[Obligation("pronoun", "refers")])
    projected = project_references({"source": "target"}, {"source": source, "target": target}, reg)
    assert projected is not None
    assert reference_from_unit(projected["source"]) == reference_from_unit(name)
    incompatible = unit(3, "his", "pronoun", obligations=[Obligation("pronoun", "refers")])
    assert project_references({"source": "target"}, {"source": incompatible, "target": target}, reg) is None


@pytest.mark.parametrize("references", [{"x": "x"}, {"x": "y", "y": "x"}, {"x": ""}])
def test_reference_schema_rejects_cycles_or_empty_bindings(references):
    with pytest.raises(ValidationError, match="direct target slots"):
        PatternRule(id="test", match={"sentence": []}, references=references)


def test_reference_binding_cannot_discard_its_target_with_satisfaction():
    with pytest.raises(ValidationError, match="sentinel"):
        PatternRule(id="test", match={"sentence": []}, references={"x": "y"}, satisfies={"x": ["refers"]})


@pytest.mark.parametrize("entry", [
    {"senses": ["noun"], "anaphoric_form": {"paradigm": "p", "referent_numbers": ["singular"]}},
    {"senses": ["pronoun"], "anaphoric_form": {"paradigm": "", "referent_numbers": ["singular"]}},
    {"senses": ["pronoun"], "anaphoric_form": {"paradigm": "p", "referent_numbers": []}},
    {"senses": ["pronoun"], "anaphoric_form": {"paradigm": "p", "referent_numbers": ["singular", "singular"]}},
])
def test_invalid_pronoun_metadata_fails_schema(entry):
    with pytest.raises(ValidationError):
        LexiconEntry.model_validate(entry)


@pytest.mark.parametrize("source,target", [
    ({"slot": "source", "type": "number"}, {"slot": "target", "type": "name"}),
    ({"slot": "source", "type": "pronoun"}, {"slot": "target", "type": "number"}),
    ({"slot": "wrong", "type": "pronoun"}, {"slot": "target", "type": "name"}),
])
def test_invalid_reference_slots_fail_compilation(source, target):
    rules = RulesDoc.model_validate({"format": "rulekit/rules@1", "rules": [{
        "id": "test/reference", "match": {"sentence": [source, target]},
        "references": {"source": "target"},
    }]})
    pack = LoadedPack("test", Path("."), PackDoc(format="rulekit/pack@1", name="test"), rules=[rules])
    with pytest.raises(CompileError, match="reference"):
        compile_registry([pack])
