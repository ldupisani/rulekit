"""Ordered holding comparisons and activity-qualified component populations.

All examples here are invented; explicit parts do not imply ownership or an
unstated action on those parts. Depictions have their own reported scope.
"""

import pytest
from rulekit.data.project import load_project
from rulekit.kernel.engine import solve
from rulekit.kernel.answer import assumption_records
from rulekit.kernel.model import AllocationRatio


@pytest.fixture(scope='module')
def reg():
    return load_project('projects/curated').registry


def share(intro='compared with Quinn', total='they have 120 in total',
          withdrawal='half of her coins', ask='How many will Quinn have left over?'):
    return (f'The ratio of coins that Paige has {intro} is 2:3. '
            f'If {total}, and Quinn spends {withdrawal} on toys, {ask}')


def number(reg, text, expected):
    result = solve(text, reg)
    assert result.value == pytest.approx(expected), result.answer
    assert not result.deficiencies()
    return result


@pytest.mark.parametrize('intro', [
    'compared with Quinn', 'compared to Quinn',
    'compared with that which Quinn has',
    ', compared to that which Quinn has,',
    'to that which Quinn has', 'to Quinn',
])
def test_ordered_holder_comparison_forms(reg, intro):
    result = number(reg, share(intro=intro), 36)
    ratio, = result.store.by_kind(AllocationRatio)
    assert (ratio.first, ratio.second) == ('paige', 'quinn')


@pytest.mark.parametrize('total', [
    'they have 120 in total', 'they have 120 coins in total',
    'the total number of coins they have is 120',
])
@pytest.mark.parametrize('withdrawal', ['half of her coins', 'half of what she has',
                                      "half of Quinn's coins"])
@pytest.mark.parametrize('ask', ['How many will she remain with?',
                                 'How many coins will she remain with?',
                                 'How many will she have left?',
                                 'How many coins will she have left over?',
                                 'How many coins can she still spend?'])
def test_share_resource_ellipsis_owned_withdrawal_and_residual_questions(reg, total, withdrawal, ask):
    number(reg, share(total=total, withdrawal=withdrawal, ask=ask), 36)


def test_share_comparison_and_remainder_are_not_specific_to_currency(reg):
    text = share().replace('coins', 'beads').replace('spends', 'uses')
    text = text.replace('How many will Quinn have left over?', 'How many beads will Quinn have left over?')
    number(reg, text, 36)
    number(reg, text.replace('Quinn uses', 'Paige uses').replace('her beads', "Paige's beads")
           .replace('will Quinn', 'will Paige'), 24)


@pytest.mark.parametrize('before,after', [
    ('they have 120 in total', 'they have is 120 in total'),
    ('her coins', 'her beads'), ('her coins', "Paige's coins"),
    ('her coins', 'his coins'), ('her coins', 'their coins'),
    ('120', '121'), ('2:3', '0:0'),
    ('her coins', 'her red coins'), ('coins that Paige', 'red coins that Paige'),
    ('will she have', 'will they have'), ('will she have', 'will Ezra have'),
    ('compared with Quinn', 'compared with Paige'),
    ('they have', 'she has'), ('left over?', 'left over tomorrow?'),
])
def test_share_boundaries_preserve_resource_group_ownership_and_scope(reg, before, after):
    text = share(ask='How many coins will she have left over?')
    assert before in text
    assert not solve(text.replace(before, after), reg).answer.committed


def population(activity='collected', ask=None):
    if ask is None:
        ask = f'How many legs do the animals she {activity} have in total?'
    return (f'Paige {activity} 3 beetles with 6 legs each and one crab with 12 legs. ' + ask)


@pytest.mark.parametrize('activity', ['collected', 'painted', 'observed'])
@pytest.mark.parametrize('shape', ['relative', 'participle'])
@pytest.mark.parametrize('punctuation', ['?', ''])
def test_component_populations_identified_by_activity(reg, activity, shape, punctuation):
    ask = (f'How many legs do the animals she {activity} have in total' if shape == 'relative'
           else f'How many legs do the {activity} animals have in total') + punctuation
    number(reg, population(activity, ask), 30)


@pytest.mark.parametrize('activity,bare', [('painted', 'paint')])
def test_direct_depiction_question_reports_component_scope(reg, activity, bare):
    result = number(reg, population(activity, f'How many legs did she {bare}?'), 30)
    assert assumption_records(result.answer) == [{
        'id': 'explicitly-depicted-components',
        'description': 'Count the explicitly described parts as included in the depictions of the whole objects.',
        'sentences': [0],
    }]


@pytest.mark.parametrize('activity', ['painted', 'observed', 'assembled'])
def test_manufactured_component_populations_reuse_the_same_account(reg, activity):
    text = (f'Paige {activity} 2 cars with 4 wheels each and one bicycle with 3 wheels. '
            f'How many wheels do the {activity} vehicles have in total?')
    number(reg, text, 11)


@pytest.mark.parametrize('before,after', [
    ('she collected', 'she observed'), ('the animals', 'the vehicles'),
    ('6 legs each', '6 legs'), ('one crab', 'two crabs'),
    ('she collected', 'Ezra collected'),
    ('How many legs do the animals she collected have in total?', 'How many legs did she collect?'),
    ('have in total?', 'have in total tomorrow?'),
])
def test_component_activity_does_not_imply_other_events_or_populations(reg, before, after):
    assert not solve(population().replace(before, after), reg).answer.committed


def test_activity_nominal_cannot_conflate_different_participants(reg):
    text = ('Paige observed 3 beetles with 6 legs each. Quinn observed one crab with 12 legs. '
            'How many legs do the observed animals have in total?')
    assert not solve(text, reg).answer.committed


def test_components_and_actual_possession_remain_distinct(reg):
    text = population('observed', 'How many animals does Paige have?')
    assert not solve(text, reg).answer.committed


def test_comparison_phrase_does_not_break_an_actual_perfect_comparison(reg):
    from rulekit.kernel.engine import analyze
    reading = analyze('Paige has compared the ages.', reg)
    assert any(d.kind == 'merge-perfect' for d in reading.decisions)


@pytest.mark.parametrize('rule_id', [
    'arithmetic/named-holder-ratio-comparison',
    'arithmetic/joint-holder-elided-count',
    'arithmetic/joint-holder-resource-count',
    'arithmetic/fraction-of-owned-holding-spent',
])
def test_new_share_grammar_round_trips_through_generation(rule_id):
    from rulekit.generation import generate_candidate
    candidate = generate_candidate(load_project('projects/curated'), rule_id=rule_id, seed=17)
    assert candidate.target_status == 'matched'
    assert candidate.facts


@pytest.mark.parametrize('ask_id', [
    'ask/named-share-left-over', 'ask/named-share-still-available',
    'ask/activity-components-participle-total', 'ask/depicted-components-total',
])
def test_new_queries_round_trip_without_inventing_evidence(ask_id):
    from rulekit.generation import generate_ask_scenario
    candidate = generate_ask_scenario(load_project('projects/curated'), ask_id=ask_id,
                                      seed=17, scenario_mode='ask_only')
    assert candidate.target_ask == ask_id
    assert candidate.answer_shape == 'decline'


def test_ordinary_stock_remainders_keep_their_existing_consumer(reg):
    number(reg, 'Paige has 80 marbles. Paige gives away 22 marbles. '
           'How many marbles will Paige have left?', 58)
