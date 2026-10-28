"""Explicit active-period scopes for recurring expenses in a saving cycle."""
from pathlib import Path

import pytest

from rulekit.data.project import load_project
from rulekit.generation import generate_candidate, list_rule_availability, retest_candidate
from rulekit.kernel.engine import solve
from rulekit.kernel.model import BatchEvidence
from test_resource_composition_families import assert_number, cyclic_story


@pytest.fixture(scope='module')
def project():
    return load_project(Path('projects/curated'))


def scoped_story(scope='only during her three-month baseball season', *,
                 leading=False, resource='fuel', activity='baseball', named_plan=True):
    text = cyclic_story().replace('baseball supplies', resource).replace('her supplies?', f'her {resource}?')
    expense = 'Dena spends $60 per month on ' + resource
    text = text.replace(expense + '.',
                        scope.capitalize() + ', ' + expense + '.' if leading else expense + ' ' + scope + '.')
    text = text.replace('Her season is 3 months long. ', '')
    if named_plan:
        text = text.replace('She wants to save during the remaining months',
                            f'She wants to use the months she is not playing {activity} to save')
    return text


@pytest.mark.parametrize('scope', [
    'during her three-month baseball season',
    'only during her 3-month baseball season',
    'throughout her three month baseball season',
    'only during her three-month season',
    'during the three months of her baseball season',
    'only for the 3 months of her season',
])
def test_inline_duration_and_scope_feed_the_existing_saving_calculation(project, scope):
    result = assert_number(scoped_story(scope), project.registry, 4)
    assert '180 required' in result.answer.reason
    assert '9 saving periods' in result.answer.reason
    assert '1 year cycle' in result.answer.reason
    assert sum(isinstance(f, BatchEvidence) and f.kind == 'expense-active-period'
               for f in result.facts()) == 1


@pytest.mark.parametrize('scope', [
    'during her three-month baseball season',
    'throughout her three-month season',
    'during the three months of her baseball season',
])
def test_fronted_scope_binds_its_possessor_to_the_expense_subject(project, scope):
    assert_number(scoped_story(scope, leading=True), project.registry, 4)


@pytest.mark.parametrize('scope', ['during her baseball season', 'only during her season'])
@pytest.mark.parametrize('placement', ['before_plan', 'after_tariff'])
@pytest.mark.parametrize('leading', [False, True])
def test_named_expense_period_can_use_a_separate_duration_declaration(project, scope, placement, leading):
    text = scoped_story(scope, leading=leading)
    anchor = 'She wants' if placement == 'before_plan' else 'How many'
    text = text.replace(anchor, 'Her baseball season is three months long. ' + anchor)
    assert_number(text, project.registry, 4)


@pytest.mark.parametrize('resource, activity, service', [
    ('fuel', 'baseball', 'mowing lawns'),
    ('wood', 'gardening', 'raking lawns'),
    ('clothes', 'tennis', 'washing cars'),
])
@pytest.mark.parametrize('goal', ['to save for', 'to afford'])
def test_scope_is_independent_of_the_goods_and_the_offered_service(project, resource, activity, service, goal):
    text = scoped_story(f'only during her three-month {activity} season', resource=resource,
                        activity=activity, named_plan=False)
    text = text.replace('mowing lawns', service).replace('to save for', goal)
    assert_number(text, project.registry, 4)


@pytest.mark.parametrize('cadence', ['a', 'per', 'each', 'every'])
def test_expense_frequency_is_distinct_from_its_active_period(project, cadence):
    assert_number(scoped_story().replace('per month on', cadence + ' month on'), project.registry, 4)


@pytest.mark.parametrize('before, after', [
    ('three-month baseball season', 'three-month tennis season'),
    ('three-month baseball season', 'three-month red baseball season'),
    ('three-month baseball season', 'three-pound baseball season'),
    ('three-month baseball season', 'zero-month baseball season'),
    ('three-month baseball season', '12-month baseball season'),
    ('three-month baseball season', '13-month baseball season'),
    ('only during', 'only after'),
    ('only during', 'not during'),
    ('only during', 'outside'),
    ('on fuel only during', 'on fuel all year during'),
    ('Dena spends', 'Dena might spend'),
    ('Dena spends', 'Dena does not spend'),
    ('Dena spends', 'Dena never spends'),
    ('Her', "Cato's"),
    ('her fuel?', "Cato's fuel?"),
    ('She charges', 'Cato charges'),
    ('$5 for each', '$0 for each'),
    ('mowing lawns', 'mowing cars'),
])
def test_scope_never_overrides_conflicting_or_unasserted_evidence(project, before, after):
    text = scoped_story()
    if before == 'Her':
        text = scoped_story('only during her baseball season')
        text = text.replace('She wants', 'Her baseball season is three months long. She wants')
    assert before in text
    assert not solve(text.replace(before, after), project.registry).answer.committed


@pytest.mark.parametrize('declaration', [
    'Her tennis season is three months long.',
    "Cato's baseball season is three months long.",
    'Her baseball season is three pounds long.',
])
def test_a_duration_of_another_period_does_not_measure_the_expense_scope(project, declaration):
    text = scoped_story('only during her baseball season').replace('She wants', declaration + ' She wants')
    assert not solve(text, project.registry).answer.committed


def test_missing_duration_and_unscoped_fuel_remain_distinct_gaps(project):
    assert not solve(scoped_story('only during her baseball season'), project.registry).answer.committed
    text = cyclic_story().replace('baseball supplies', 'fuel').replace('her supplies?', 'her fuel?')
    text = text.replace('She wants to save during the remaining months',
                        'She wants to use the months she is not playing baseball to save')
    result = solve(text, project.registry)
    assert not result.answer.committed
    assert 'unrelated recurring expense' in result.answer.reason


def test_a_second_conflicting_duration_is_not_ignored(project):
    text = scoped_story().replace('She wants', 'Her baseball season is two months long. She wants')
    assert not solve(text, project.registry).answer.committed


@pytest.mark.parametrize('form', ['named', 'measured', 'counted', 'attributive'])
@pytest.mark.parametrize('placement', ['leading', 'trailing'])
def test_scoped_expense_grammar_has_a_generation_witness(project, form, placement):
    rule_id = f'arithmetic/periodic-purpose-expense-{form}-period-{placement}'
    if form == 'counted':
        # The reader retains a count on the full period when a second nominal
        # modifier intervenes. Generation does not yet realize that structure;
        # retain its explicit blocker and verify a manually authored witness.
        row = next(row for row in list_rule_availability(project) if row.id == rule_id)
        assert not row.supported
        assert row.blockers == ('no project-backed filler exists for season',)
        sentence = scoped_story('during her three-month baseball season',
                                leading=placement == 'leading').split('.')[0] + '.'
        candidate = retest_candidate(project, rule_id=rule_id, sentence=sentence, seed=1423)
    else:
        candidate = generate_candidate(project, rule_id=rule_id, seed=1423)
    assert candidate.target_status in {'matched', 'shadowed'}
