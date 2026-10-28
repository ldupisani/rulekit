"""Invented variations of recurring costs, measured balances, and stored losses."""
from dataclasses import replace
from pathlib import Path

import pytest

from rulekit.data.project import load_project
from rulekit.kernel.engine import solve
from test_resource_composition_families import (
    area_story, assert_number, cyclic_story, distribution_story, purchase_story, stored_story,
)
from test_measured_resources_and_allocations import CASES, EXPECTED, resource_question


@pytest.fixture(scope='module')
def registry():
    return load_project(Path('projects/curated')).registry


@pytest.mark.parametrize('goods, service', [('baseball supplies', 'mowing lawns'), ('clothes', 'washing cars')])
def test_affording_a_goal_reuses_the_complementary_window(registry, goods, service):
    target = 'supplies' if goods == 'baseball supplies' else goods
    text = cyclic_story().replace('baseball supplies', goods).replace('her supplies?', 'her ' + target + '?')
    text = text.replace('mowing lawns', service).replace('to save for her', 'to afford her')
    assert_number(text, registry, 4)


@pytest.mark.parametrize('after', ['by mowing lawns. ', 'She charges $5 for each. '])
def test_activity_duration_declaration_can_follow_the_saving_plan(registry, after):
    text = cyclic_story().replace('Her season is 3 months long. ', '')
    text = text.replace(after, after + 'Her baseball season is 3 months long. ')
    assert_number(text, registry, 4)
    assert not solve(text.replace('Her baseball season', 'Her tennis season'), registry).answer.committed


@pytest.mark.parametrize('resource', ['fuel', 'wood'])
def test_an_unrelated_recurring_expense_needs_its_own_period_scope(registry, resource):
    text = cyclic_story().replace('baseball supplies', resource).replace('her supplies?', f'her {resource}?')
    text = text.replace('She wants to save during the remaining months by mowing lawns.',
                        'She wants to use the months she is not playing baseball to save by mowing lawns.')
    result = solve(text, registry)
    assert not result.answer.committed
    assert 'unrelated recurring expense' in result.answer.reason


@pytest.mark.parametrize('material', ['cloth', 'paper', 'wood'])
@pytest.mark.parametrize('purpose', ['to make panels', 'for panels', ''])
def test_fabrication_context_does_not_require_a_production_infinitive(registry, material, purpose):
    text = area_story(material).replace(' to make panels', ' ' + purpose if purpose else '')
    assert_number(text, registry, 87)


@pytest.mark.parametrize('ask', [
    'How much cloth remains in square feet?',
    'How much uncut cloth is left in square feet?',
    'How much remaining cloth is left in square feet?',
    'How much cloth is left?',
    'How much cloth remains?',
    'How much uncut cloth is left?',
])
def test_area_question_variations_select_the_same_measured_balance(registry, ask):
    text = area_story().split('How much')[0] + ask
    assert_number(text, registry, 87)


@pytest.mark.parametrize('unit, expected', [
    ('meters', 8.08256448), ('metres', 8.08256448),
    ('centimeters', 80825.6448), ('centimetres', 80825.6448),
    ('millimeters', 8082564.48), ('millimetres', 8082564.48), ('mm', 8082564.48),
])
def test_area_conversion_follows_existing_edges_and_squares_the_factor(registry, unit, expected):
    assert_number(area_story().replace('square feet?', 'square ' + unit + '?'), registry, expected)


@pytest.mark.parametrize('case', ['metal', 'foam', 'wire', 'clay'])
def test_bare_amount_queries_use_only_the_unique_common_declared_basis(registry, case):
    assert_number(resource_question(case, f'How much {case} is left?'), registry, EXPECTED[case])


def test_multiple_registered_bases_make_an_elided_dimension_ambiguous(registry):
    formulas = {**registry.geometry_formulas, ('rectangle', 'perimeter'): '2 * (length + width)'}
    ambiguous = replace(registry, geometry_formulas=formulas)
    assert not solve(area_story().replace(' in square feet', ''), ambiguous).answer.committed
    assert_number(area_story(), ambiguous, 87)


@pytest.mark.parametrize('ask', [
    "How much Cato's uncut cloth is left?",
    'How much uncut red cloth is left?',
    'How much uncut cloth is left in cubic feet?',
    'How long is the remaining cloth?',
])
def test_elision_does_not_discard_identity_or_choose_a_side_length(registry, ask):
    assert not solve(area_story().split('How much')[0] + ask, registry).answer.committed


def test_implicit_basis_still_needs_an_unambiguous_output_unit(registry):
    text = resource_question('wire', 'How much wire is left?').replace('another 7 meters', 'another 7 centimeters')
    assert not solve(text, registry).answer.committed


@pytest.mark.parametrize('item, people', [('marbles', 'friends'), ('pencils', 'workers')])
@pytest.mark.parametrize('preposition', ['among', 'amongst'])
def test_per_recipient_observations_and_distribution_synonyms(registry, item, people, preposition):
    text = distribution_story(item=item, people=people).replace('with her', preposition + ' her')
    text = text.replace(f'Her {people} received three {item} each.', f'Each {people[:-1]} got three {item}.')
    assert_number(text, registry, 3)


@pytest.mark.parametrize('first, second, unit, plural', [
    ('books', 'marbles', 'box', 'boxes'),
    ('ice cream', 'frozen yogurt', 'tub', 'tubs'),
    ('water', 'vinegar', 'bottle', 'bottles'),
])
def test_content_first_and_package_first_unit_quotes_compose(registry, first, second, unit, plural):
    text = purchase_story(first, second, unit, plural)
    text = text.replace(f'Each {unit} of {first} costs $8', f'{first.capitalize()} cost $8 per {unit}')
    assert_number(text, registry, 14)


@pytest.mark.parametrize('before, after', [
    ('per box', 'per bag'), ('per box', 'per pound'), ('per box', ''),
    ('3 boxes', '3.5 boxes'), ('bought', 'wants'),
])
def test_package_quotes_cannot_change_the_purchase_basis(registry, before, after):
    text = purchase_story().replace('Each box of books costs $8', 'Books cost $8 per box')
    assert not solve(text.replace(before, after), registry).answer.committed


@pytest.mark.parametrize('destination', [
    'in a savings account', 'into her savings account', 'into savings', 'in her piggy bank',
])
def test_reserve_destinations_retain_the_unallocated_wallet_balance(registry, destination):
    assert_number(stored_story().replace('in her savings account', destination), registry, 10)


def test_work_context_has_optional_geography(registry):
    text = stored_story().replace('Dena received $30.', 'Dena earned $30 working odd jobs.')
    assert_number(text, registry, 10)


@pytest.mark.parametrize('actor, action', [
    ('Her dog', 'shredded'), ('Her cat', 'ate'), ('Her grandma', 'stole'), ('The machine', 'destroyed'),
])
@pytest.mark.parametrize('location', ['in', 'inside'])
@pytest.mark.parametrize('exception', ['but', 'except', 'except for'])
def test_owner_loss_is_shared_across_scoped_removal_events(registry, actor, action, location, exception):
    old = 'Her cat got ahold of her wallet and destroyed all the money inside except $2.'
    new = f'{actor} {action} all the money {location} the wallet {exception} $2.'
    assert_number(stored_story().replace(old, new), registry, 10)


@pytest.mark.parametrize('exception', ['but', 'except', 'except for'])
def test_coordinated_loss_reuses_the_explicit_access_context(registry, exception):
    assert_number(stored_story().replace('except $2', exception + ' $2'), registry, 10)


def test_unlocated_reserve_and_an_account_may_be_the_same_pool(registry):
    text = stored_story().replace('in her savings account', 'into savings')
    text = text.replace('in her wallet.', 'in her savings account.')
    text = text.replace('ahold of her wallet', 'ahold of her savings account')
    assert not solve(text, registry).answer.committed


@pytest.mark.parametrize('before, after', [
    ('inside the wallet', 'inside a wallet'),
    ('inside the wallet', 'inside the other wallet'),
    ('inside the wallet', 'inside the purse'),
    ('stole all', 'might steal all'),
    ('stole all', 'stolen all'),
    ('except $2', 'but for $2'),
    ('except $2', 'except for $20'),
    ('Dena lose?', 'Dena steal?'),
    ('Dena lose?', 'the cat destroy?'),
])
def test_loss_requires_an_actual_event_and_the_identified_owners_store(registry, before, after):
    old = 'Her cat got ahold of her wallet and destroyed all the money inside except $2.'
    text = stored_story().replace(old, 'Her grandma stole all the money inside the wallet except $2.')
    assert not solve(text.replace(before, after), registry).answer.committed


def test_a_trailing_exception_is_not_assigned_back_across_another_event(registry):
    old = 'Her cat got ahold of her wallet and destroyed all the money inside except $2.'
    new = ('Her grandma stole all the money inside the wallet and spent it on lottery tickets, '
           'except for $2.')
    assert not solve(stored_story().replace(old, new), registry).answer.committed


@pytest.mark.parametrize('rule_id', [
    'arithmetic/material-fabrication-context',
    'arithmetic/resource-receipt-with-work-context',
    'arithmetic/coordinated-fraction-of-remainder-transfer',
    'arithmetic/per-package-price-quote',
    'arithmetic/coordinated-stored-resource-loss-except-for',
    'arithmetic/explicit-stored-resource-loss-except-for',
    'arithmetic/referential-stored-resource-loss-except',
    'arithmetic/referential-stored-resource-loss-except-for',
])
def test_extended_premise_families_have_generation_witnesses(rule_id):
    from rulekit.generation import generate_candidate
    project = load_project(Path('projects/curated'))
    candidate = generate_candidate(project, rule_id=rule_id, seed=1423)
    assert candidate.target_status in {'matched', 'shadowed'}


@pytest.mark.parametrize('ask_id, locks, consumer, quantity', [
    ('ask/cyclic-saving-average-tasks-funding-goal',
     {'tasks': 'jobs', 'who': 'Dena', 'fund': 'afford', 'target': 'supplies'},
     'cyclic-saving-average', None),
    ('ask/measured-remainder-how-much-inferred',
     {'amount_word': 'much', 'material': 'cloth', 'be': 'is', 'remnant': 'left'},
     'material-region-remainder', 'inferred'),
    ('ask/measured-remainder-how-much-remains-inferred',
     {'amount_word': 'much', 'material': 'cloth', 'remain': 'remains'},
     'material-region-remainder', 'inferred'),
    ('ask/measured-remainder-qualified-how-much-inferred',
     {'amount_word': 'much', 'material': 'uncut cloth', 'be': 'is', 'remnant': 'left'},
     'material-region-remainder', 'inferred'),
    ('ask/measured-remainder-qualified-how-much-area',
     {'amount_word': 'much', 'material': 'uncut cloth', 'be': 'is', 'remnant': 'left',
      'power': 'square', 'unit': 'feet'},
     'material-region-remainder', 'area'),
])
def test_extended_questions_roundtrip_to_the_existing_consumer_contract(ask_id, locks, consumer, quantity):
    from rulekit.generation import generate_ask_scenario
    candidate = generate_ask_scenario(load_project(Path('projects/curated')), ask_id=ask_id,
                                      seed=1423, scenario_mode='ask_only', locked_bindings=locks)
    assert candidate.consumer == consumer
    if quantity:
        assert candidate.query['quantity'] == quantity
        assert candidate.query['material'] == 'cloth'


def test_promoted_vocabulary_is_owned_by_shared_core():
    project = load_project(Path('projects/curated'))
    for word in ('afford', 'fuel', 'grandma', 'lottery', 'millimeter', 'piggy bank', 'steal', 'tub', 'uncut'):
        assert 'core-english' in project.source_index.lexicon[word].path.parts
    for surface, lemma in [('metres', 'meter'), ('centimetres', 'centimeter'), ('millimetres', 'millimeter')]:
        assert project.registry.plural_to_singular[surface] == lemma


def test_content_first_quotes_can_both_be_coordinated(registry):
    text = purchase_story().replace('Each box of books costs $8 and each box of marbles costs $2.',
                                    'Books cost $8 per box and marbles cost $2 per box.')
    assert_number(text, registry, 14)


@pytest.mark.parametrize('prefix', ['If ', 'Dena thinks '])
def test_unasserted_quotes_do_not_complete_a_purchase_ledger(registry, prefix):
    text = purchase_story().replace('Each box of books costs $8', prefix + 'books cost $8 per box')
    assert not solve(text, registry).answer.committed
