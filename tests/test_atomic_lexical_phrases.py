"""Explicit multiword identities are vocabulary, not Python word exceptions."""

from dataclasses import replace
from pathlib import Path

import pytest
from pydantic import ValidationError

from rulekit.data.project import load_project
from rulekit.data.registry import CompileError, compile_registry
from rulekit.data.schemas import LexiconEntry
from rulekit.kernel.engine import analyze


@pytest.fixture(scope="module")
def project():
    return load_project(Path("projects/curated"))


@pytest.mark.parametrize("surface,lemma,number", [
    ("jelly beans", "jelly bean", "plural"),
    ("gummy worm", "gummy worm", "singular"),
    ("care packages", "care package", "plural"),
    ("boarding school", "boarding school", "singular"),
])
def test_atomic_nouns_keep_full_identity_and_number(project, surface, lemma, number):
    reading = analyze(surface, project.registry)
    assert len(reading.units) == 1
    unit = reading.units[0]
    assert unit.sense() == "noun"
    assert unit.features["lemma"] == lemma
    assert unit.features["number"] == number
    assert not reading.deficiencies()


def test_repetition_idiom_does_not_inherit_component_number(project):
    reading = analyze("once again", project.registry)
    assert len(reading.units) == 1
    assert reading.units[0].sense() == "adverb"
    assert "value" not in reading.units[0].features
    ordinary = analyze("once a week", project.registry)
    assert ordinary.units[0].features["value"] == 1.0


def test_declared_phrase_does_not_reclassify_an_ordinary_head(project):
    assert project.registry.word_in_category("gummy worm", "measured_content_substance")
    assert not project.registry.word_in_category("worm", "measured_content_substance")


def test_quantity_determiner_blocks_cross_phrase_compounding(project):
    reading = analyze("into the jar enough jelly beans", project.registry)
    nouns = [u for u in reading.units if u.sense() == "noun"]
    assert [u.features["lemma"] for u in nouns] == ["jar", "jelly bean"]
    assert nouns[-1].features["qualifier"] == "enough"


@pytest.mark.parametrize("prefix", ["Next, Mira", "Next Mira", "Mira next"])
def test_sequence_adverb_positions_preserve_adjective_uses(project, prefix):
    reading = analyze(f"{prefix} added 4 pounds of sugar.", project.registry)
    marker = next(u for u in reading.units if u.features.get("lemma") == "next")
    assert marker.sense() == "adverb"
    reading = analyze("the next week", project.registry)
    assert not any(u.features.get("ambiguous") for u in reading.units)
    assert any(u.features.get("qualifier") == "next" for u in reading.units)


@pytest.mark.parametrize("senses", [["verb"], ["noun", "verb"], ["adjective", "adverb"]])
def test_atomic_phrase_schema_rejects_unsupported_senses(senses):
    with pytest.raises(ValidationError, match="one noun, adjective or adverb sense"):
        LexiconEntry(senses=senses, lexical_phrase=True)


def test_atomic_size_adjectives_retain_their_category_and_host(project):
    reading = analyze('6 equally sized baskets', project.registry)
    assert len(reading.units) == 1
    assert reading.units[0].features['value'] == 6
    assert reading.units[0].features['qualifier'] == 'equally sized'
    assert reading.units[0].features['lemma'] == 'basket'


@pytest.mark.parametrize("key", ["atomic", "two  words"])
def test_atomic_phrase_keys_must_be_normalized_multiword_entries(project, key):
    core = next(p for p in project.packs if p.name == "core-english")
    modified = replace(core, fingerprint=core.fingerprint + key, lexicon={
        **core.lexicon, key: LexiconEntry(senses=["noun"], lexical_phrase=True),
    })
    with pytest.raises(CompileError, match="normalized multiword"):
        compile_registry([modified if p.name == core.name else p for p in project.packs])
