"""Invented comparison examples exercise shared semantic-role boundaries."""
from dataclasses import replace

import pytest
from pydantic import ValidationError

from rulekit.data.project import load_project
from rulekit.data.schemas import ModifierHostCompatibilityPredicate
from rulekit.generation import generate_candidate, retest_candidate
from rulekit.generation.reviews import review_needs_attention
from rulekit.kernel.engine import solve
from rulekit.kernel.model import Relation


@pytest.fixture(scope='module')
def project():
    return load_project('projects/curated')


PHRASES = ['as many', 'twice as many', 'half as many',
           '3 fewer than twice as many', '3 fewer than half as many']


@pytest.mark.parametrize('phrase', PHRASES)
@pytest.mark.parametrize('frame', [
    'The cottage deletes {phrase} cats as Nora.',
    'Mira deletes {phrase} paperbacks as Nora.',
    'The bench uses {phrase} books as Nora.',
    'The road delivered {phrase} books as Nora.',
    'Mira deletes {phrase} files into the box as Nora.',
    'The road has {phrase} trees as her child Owen.',
    'Mira has {phrase} books as her person Owen.',
    'The teacher delete {phrase} files as Nora.',
])
def test_incompatible_roles_do_not_emit_comparisons(project, phrase, frame):
    result = solve(frame.format(phrase=phrase), project.registry)
    assert not result.store.by_kind(Relation)


@pytest.mark.parametrize('phrase', PHRASES)
@pytest.mark.parametrize('frame', [
    'Mira deleted {phrase} files as Nora.',
    'The computer deletes {phrase} images as Mira.',
    'Mira uses {phrase} books throughout December as Nora.',
    'Mira delivered {phrase} books into the box as Nora.',
    'Mira has {phrase} books as her brother Owen.',
    'The road has {phrase} trees as the park.',
    'Mira bought {phrase} books at the park as Nora.',
    'Mira has {phrase} books in the cupboard as Nora.',
    'Mira owns {phrase} books about the topic as Nora.',
    'The pantry has {phrase} books as my teacher Nora.',
])
def test_compatible_roles_and_stative_holders_survive(project, phrase, frame):
    result = solve(frame.format(phrase=phrase), project.registry)
    assert len(result.store.by_kind(Relation)) == 1
    assert not result.deficiencies(), result.deficiencies()


@pytest.mark.parametrize('seed', [0, 17, 29])
def test_generated_affine_reading_has_licensed_offset_and_multiplier(project, seed):
    candidate = generate_candidate(project, rule_id='arithmetic/affine-times-as-many', seed=seed)
    assert candidate.target_status in {'matched', 'shadowed'}
    assert candidate.requested_bindings['k'].lower() not in {'once', 'double', 'triple'}
    assert not any('quantifies' in d for d in candidate.deficiencies)
    assert candidate.to_json()['clean_reading'] == candidate.clean_reading


def test_matching_with_gaps_is_not_clean_reusable_evidence(project):
    candidate = retest_candidate(project, rule_id='arithmetic/affine-times-as-many',
        sentence='Mira has 3 fewer than twice as many books as Nora.', seed=0,
        origin='reading')
    assert candidate.clean_reading
    dirty = replace(candidate, deficiencies=('an unresolved reference',))
    assert not dirty.clean_reading
    review = {'verdict': 'valid', 'target_rule': candidate.target_rule,
              'premise_evidence': {'target_status': 'matched', 'deficiencies': list(dirty.deficiencies)}}
    assert review_needs_attention(review)
    assert not review_needs_attention({**review, 'premise_evidence': {'target_status':'matched'}})
    assert review_needs_attention({**review, 'premise_evidence': {'target_status':'absent'}})
    assert not replace(candidate, generation_mode='lexical_boundary').clean_reading


def test_verbal_modifier_requires_object():
    with pytest.raises(ValidationError, match='requires its object'):
        ModifierHostCompatibilityPredicate(modifier='prep', host='verb', host_type='verb')


def test_adposition_roles_are_shared_with_the_registry(project):
    reg = project.registry
    assert reg.modifier_frame_compatible('into', 'delivered', 'box', host_type='verb')
    assert not reg.modifier_frame_compatible('into', 'deleted', 'box', host_type='verb')
    assert reg.modifier_frame_compatible('throughout', 'deleted', 'december', host_type='verb')
    assert reg.modifier_frame_compatible('from', 'deleted', 'computer', host_type='verb')


def test_unnamed_personal_relation_standard_remains_supported(project):
    result = solve('Mira has twice as many books as her brother.', project.registry)
    relations = result.store.by_kind(Relation)
    assert len(relations) == 1
    assert relations[0].standard == 'brother'


def test_generation_preserves_licensed_verbal_prepositional_phrase(project):
    candidate = generate_candidate(
        project, rule_id='arithmetic/affine-times-as-many', seed=7,
        locked_bindings={'who': 'Aven', 'verb': 'delivered', 'item': 'books',
                         'pp_prep': 'into', 'pp_obj': 'the box', 'std': 'Bira'},
    )
    assert candidate.target_status in {'matched', 'shadowed'}
    assert 'into the box' in candidate.sentence
    assert any('delivery-goal' in item.reason for item in candidate.premises)


@pytest.mark.parametrize('role', ['brother', 'parent', 'guardian', 'partner', 'student'])
def test_shared_personal_roles_support_named_apposition(project, role):
    result = solve(f'Mira has twice as many books as her {role} Owen.', project.registry)
    assert len(result.store.by_kind(Relation)) == 1


def test_animal_can_have_a_named_sibling(project):
    result = solve('The dog has twice as many toys as its sister Nora.', project.registry)
    assert len(result.store.by_kind(Relation)) == 1


def test_overlapping_location_frames_emit_one_role(project):
    assert project.registry.matching_adposition_roles('in', 'garden', 'traveled') == ('spatial-location',)
