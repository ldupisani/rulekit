"""Noun inflections share semantic membership without changing grammatical senses."""
from pathlib import Path

import pytest

from rulekit.data.packs import LoadedPack
from rulekit.data.project import load_project
from rulekit.data.registry import compile_registry
from rulekit.data.schemas import CategoriesDoc, LexiconEntry, PackDoc
from rulekit.data.schemas import MatchToken
from rulekit.generation.sample import _domain, _load_fixtures
from rulekit.kernel.engine import analyze, solve


def morphology_registry():
    return compile_registry([LoadedPack(
        name='morphology', root=Path('morphology'),
        manifest=PackDoc(format='rulekit/pack@1', name='morphology'),
        lexicon={
            'mouse': LexiconEntry(senses=['noun'], plural='mice'),
            'scarf': LexiconEntry(senses=['noun'], plural=['scarfs', 'scarves']),
            'duck': LexiconEntry(senses=['noun', 'verb'], plural='ducks'),
            'ducks': LexiconEntry(senses=['verb'], verb={'lemma': 'duck'}),
            'time': LexiconEntry(senses=['noun'], plural='times'),
            'cattle': LexiconEntry(senses=['noun'], number='plural'),
        },
        categories=[CategoriesDoc(format='rulekit/categories@1', categories={
            'animal': {'parent': 'noun'},
            'pet': {'parent': 'animal'},
            'garment': {'parent': 'noun'},
            'allocation_target': {'parent': 'noun', 'includes': ['animal', 'garment']},
            'motion': {'parent': 'verb'},
            'evasion': {'parent': 'verb'},
            'multiplier_marker': {'parent': 'noun'},
        }, members={
            'animal': ['cattle', 'duck'], 'pet': ['mouse'], 'garment': ['scarf'],
            'motion': ['duck'], 'evasion': ['ducks'], 'multiplier_marker': ['times'],
        })], fingerprint='morphology',
    )])


def test_declared_plural_membership_reaches_parents_and_included_roles():
    r = morphology_registry()
    for surface in ('mouse', 'mice'):
        for category in ('noun', 'pet', 'animal', 'allocation_target'):
            assert r.word_in_category(surface, category)
    for surface in ('scarf', 'scarfs', 'scarves'):
        assert r.word_in_category(surface, 'garment')
        assert r.word_in_category(surface, 'allocation_target')
    assert r.category_membership_path('mice', 'allocation_target') == (
        'mouse', 'pet', 'animal', 'allocation_target')


def test_member_enumeration_includes_exactly_the_declared_noun_inflections():
    r = morphology_registry()
    assert r.cat_members_deep('animal') == ['cattle', 'duck', 'ducks', 'mice', 'mouse']
    assert r.cat_members_deep('allocation_target') == [
        'cattle', 'duck', 'ducks', 'mice', 'mouse', 'scarf', 'scarfs', 'scarves']
    assert not r.word_in_category('mouses', 'animal')
    assert not r.word_in_category('cattle', 'pet')
    assert 'cattle' not in r.plural_to_singular


def test_noun_plural_links_do_not_supply_verb_categories():
    r = morphology_registry()
    assert r.word_in_category('ducks', 'noun')
    assert r.word_in_category('ducks', 'verb')
    assert r.word_in_category('ducks', 'animal')
    assert not r.word_in_category('ducks', 'motion')
    assert r.word_in_category('ducks', 'evasion')
    assert r.cat_members_deep('motion') == ['duck']
    assert r.category_membership_path('ducks', 'evasion') == ('ducks', 'evasion')
    assert not r.word_in_category('mice', 'verb')


def test_explicit_surface_markers_do_not_inherit_back_to_the_singular():
    r = morphology_registry()
    assert r.word_in_category('times', 'multiplier_marker')
    assert not r.word_in_category('time', 'multiplier_marker')
    assert r.cat_members_deep('multiplier_marker') == ['times']
    assert r.category_membership_path('times', 'multiplier_marker') == (
        'times', 'multiplier_marker')


@pytest.fixture(scope='module')
def curated():
    return load_project(Path('projects/curated')).registry


@pytest.mark.parametrize('singular,plural,category', [
    ('snail', 'snails', 'pet'), ('clown', 'clowns', 'person'),
    ('giraffe', 'giraffes', 'animal'), ('chihuahua', 'chihuahuas', 'animal'),
    ('hen', 'hens', 'bird'), ('lion', 'lions', 'animal'),
    ('hare', 'hares', 'animal'), ('lizard', 'lizards', 'animal'),
    ('delegate', 'delegates', 'person'), ('grasshopper', 'grasshoppers', 'insect'),
    ('hog', 'hogs', 'animal'), ('husband', 'husbands', 'person'),
    ('nephew', 'nephews', 'person'), ('nerd', 'nerds', 'person'),
    ('grandchild', 'grandchildren', 'person'),
])
def test_shared_count_nouns_have_a_canonical_lexeme(curated, singular, plural, category):
    assert curated.plural_to_singular[plural] == singular
    for surface in (singular, plural):
        assert curated.word_in_category(surface, category)
        assert surface in curated.cat_members_deep(category)


@pytest.mark.parametrize('surface,lemma,number', [
    ('snail', 'snail', 'singular'), ('snails', 'snail', 'plural'),
    ('grandchild', 'grandchild', 'singular'), ('grandchildren', 'grandchild', 'plural'),
    ('cattle', 'cattle', 'plural'),
])
def test_shared_membership_preserves_grammatical_number(curated, surface, lemma, number):
    unit, = analyze(surface, curated).units
    assert unit.features['lemma'] == lemma
    assert unit.features['number'] == number


@pytest.mark.parametrize('singular,plural,category', [
    ('snail', 'snails', 'pet'), ('grandchild', 'grandchildren', 'person'),
])
def test_generation_selects_number_without_duplicating_category_membership(
    curated, singular, plural, category,
):
    fixtures = _load_fixtures(Path('projects/curated'))
    for number, surface in (('singular', singular), ('plural', plural)):
        domain = _domain(MatchToken(slot='item', cat=category, number=number), curated, fixtures)
        forms = [(f.surface, f.number) for f in domain if f.identity == singular]
        assert forms == [(surface, number)]


@pytest.mark.parametrize('items,collection,excluded', [
    ('6 snails, 9 cats, and 15 dogs', 'pets', 'snails'),
    ('6 giraffes, 9 hens, and 15 lions', 'animals', 'giraffes'),
    ('6 clowns, 9 delegates, and 15 nephews', 'people', 'clowns'),
])
def test_canonical_categories_support_plural_inventory_questions(curated, items, collection, excluded):
    result = solve(f'There are {items}. What percent of the {collection} are not {excluded}?', curated)
    assert result.value == 80, result.answer
    assert result.deficiencies() == []
