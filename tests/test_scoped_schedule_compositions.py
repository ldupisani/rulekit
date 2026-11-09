"""Invented schedule, measured-partition and closed contribution accounts."""
from pathlib import Path

import pytest

from rulekit.data.project import load_project
from rulekit.kernel.engine import solve


@pytest.fixture(scope='module')
def reg():
    return load_project(Path('projects/curated')).registry


def number(reg, text, expected):
    result = solve(text, reg)
    assert result.answer.committed, result.answer
    assert result.value == pytest.approx(expected)
    assert not result.deficiencies()
    return result


def wages():
    return ('Nora earns $12 an hour while working at her main job. '
            'She earns 25% less while working her second job. '
            'She works 40 hours at her main job and half that much at her second job. '
            'How much does she earn per week?')


@pytest.mark.parametrize('before,after,expected', [
    ('25% less', '25% less', 660), ('25% less', '25% more', 780),
    ('while working at', 'at', 660),
    ('while working her', 'at her', 660),
    ('main job', 'primary project', 660),
    ('second job', 'secondary assignment', 660),
    ('an hour', 'per hour', 660),
    ('40 hours', '2400 minutes', 660),
    ('How much does', 'How much money does', 660),
])
def test_scoped_rates_and_relative_extents(reg, before, after, expected):
    number(reg, wages().replace(before, after), expected)


@pytest.mark.parametrize(
    'comparison,expected',
    [('twice as much', 1200), ('three fourths that much', 750), ('50% that amount', 660)],
)
def test_scoped_extents_share_fractional_and_multiplier_ratios(reg, comparison, expected):
    number(reg, wages().replace('half that much', comparison), expected)


def test_independently_quoted_components_and_extents(reg):
    text = wages().replace('She earns 25% less while working her second job.',
                          'She earns $9 an hour at her second job.')
    text = text.replace('and half that much at her second job', '. Nora works 20 hours at her second job')
    number(reg, text, 660)


def production():
    return ('The machine makes 10 toys per hour while working at the first station. '
            'The machine makes 20% more while working at the second station. '
            'The machine works 10 hours at the first station and half that much at the second station. '
            'How many toys does the machine make per day?')


def test_production_components_reuse_the_same_rate_account(reg):
    number(reg, production(), 160)


def test_output_count_cannot_answer_a_monetary_question(reg):
    assert not solve(production().replace('How many toys', 'How much money'), reg).answer.committed


@pytest.mark.parametrize('before,after', [
    ('25% less', '125% less'), ('40 hours', '-40 hours'),
    ('half that much', 'half'), ('second job', 'main job'),
    ('at her second job', 'at his second job'),
    ('She earns 25%', 'Ezra earns 25%'),
    ('40 hours at', '40 liters at'),
    ('40 hours at', '40 hours per day at'),
    ('per week?', 'per meter?'),
    ('earns $12', 'might earn $12'),
    ('She earns 25% less', 'She does not earn 25% less'),
])
def test_scoped_rate_identity_units_and_missing_standards(reg, before, after):
    assert not solve(wages().replace(before, after), reg).answer.committed


def attendance():
    return ("Nora's three sons play basketball on different teams. "
            'They each have 5 games this season. '
            'Each team practices 3 hours for every game they play. '
            'Each game lasts for 1 hour. '
            'How many hours will Nora spend at the park watching her sons play and practice altogether?')


@pytest.mark.parametrize('before,after', [
    ('different', 'different'), ('different', 'separate'),
    ('for every', 'for each'), ('game they play', 'game'),
    ('lasts for', 'lasts'), ('this season', ''),
    ('will Nora', 'does Nora'), (' at the park', ''),
    ('3 hours', '180 minutes'),
])
def test_distributive_event_and_preparation_attendance(reg, before, after):
    number(reg, attendance().replace(before, after), 60)


def test_academic_group_schedules_reuse_the_same_attendance_composition(reg):
    text = ("Nora's three students study writing in different classes. "
            'They each have 5 lessons. Each class practices 2 hours for every lesson they study. '
            'Each lesson lasts 1 hour. '
            'How many hours will Nora spend watching her students study and practice altogether?')
    number(reg, text, 45)


@pytest.mark.parametrize('period', ['season', 'week', 'month', 'year', 'semester', 'weekend'])
@pytest.mark.parametrize('context', ['sport', 'study'])
def test_distributive_schedule_counts_retain_generic_periods(reg, period, context):
    text = attendance().replace('this season', f'this {period}').replace('5 games', '2 games')
    expected = 24
    if context == 'study':
        text = (text.replace('sons', 'students').replace('play', 'study')
                .replace('basketball', 'writing').replace('teams', 'classes')
                .replace('team', 'class').replace('games', 'lessons').replace('game', 'lesson')
                .replace('on different classes', 'in different classes'))
    result = number(reg, text, expected)
    events = next(fact for fact in result.facts() if getattr(fact, 'kind', '') == 'scheduled-event-count')
    assert events.container == period
    assert events.container_ref.head == period


@pytest.mark.parametrize('scope', ['this team', 'this park', 'per week', 'each month', 'this 2 years'])
def test_calendar_context_does_not_license_other_objects_or_recurring_counts(reg, scope):
    assert not solve(attendance().replace('this season', scope), reg).answer.committed


def test_generic_schedule_period_generates_through_its_named_slot():
    from rulekit.generation import generate_candidate
    candidate = generate_candidate(
        load_project(Path('projects/curated')),
        rule_id='arithmetic/distributive-scheduled-event-count',
        seed=581,
        max_attempts=2,
        locked_bindings={
            'group': 'they', 'each': 'each', 'have': 'have',
            'events': '2 games', 'period': 'weekend',
        },
    )
    assert candidate.target_status == 'matched'
    assert not candidate.grammar_deficiencies
    assert any(row.slot == 'period' and row.binding == 'weekend' for row in candidate.premises)


def test_homograph_verb_agreement_keeps_the_noun_reading_independent(reg):
    from rulekit.generation.sample import _lexical_fillers
    noun = next(item for item in _lexical_fillers(reg, sense='noun') if item.surface == 'practice')
    verb = next(item for item in _lexical_fillers(reg, sense='verb') if item.surface == 'practice')
    assert noun.number == 'singular'
    assert verb.number == 'plural'


@pytest.mark.parametrize('before,after', [
    ('different teams', 'the same team'), ('different teams', 'teams'),
    ("Nora's three sons", "Nora's sons"),
    ('They each', 'They'), ('They each', 'He each'),
    ('Each game lasts for 1 hour.', ''),
    ('5 games', '5 lessons'), ('will Nora', 'will Ezra'),
    ('watching her sons', 'watching her daughters'),
    ('for every game', 'for every lesson'),
    ('game they play', 'game they study'),
    ('Each team practices', 'Each team practice'),
    ('sons play and practice', 'sons practice and practice'),
])
def test_attendance_does_not_invent_population_distribution_or_shared_event_identity(reg, before, after):
    assert not solve(attendance().replace(before, after), reg).answer.committed


def holder_partition():
    return ('There are 150 liters of water in 12 bottles. '
            'If 4 of the bottles are holding 10 liters each, '
            'how much water is each of the remaining bottles holding?')


@pytest.mark.parametrize('before,after', [
    ('are holding', 'are holding'), ('are holding', 'hold'),
    ('are holding', 'contain'), ('holding?', 'containing?'),
    ('bottles', 'cans'),
])
def test_remaining_measured_holders_use_the_requested_uniform_share(reg, before, after):
    number(reg, holder_partition().replace(before, after), 13.75)


def test_length_resources_in_remaining_stock_holders(reg):
    text = holder_partition().replace('liters', 'meters').replace('water', 'wire').replace('bottles', 'spools')
    number(reg, text, 13.75)


@pytest.mark.parametrize('predicate', ['is holding', 'holds', 'contains'])
def test_one_member_of_the_known_subset_takes_singular_agreement(reg, predicate):
    text = holder_partition().replace('4 of the bottles are holding', f'1 of the bottles {predicate}')
    number(reg, text, 140 / 11)


@pytest.mark.parametrize('before,after', [
    ('4 of the bottles are', '1 of the bottles are'),
    ('4 of the bottles are', '4 of the bottles is'),
])
def test_subset_agreement_tracks_the_count_and_not_the_plural_partitive(reg, before, after):
    assert not solve(holder_partition().replace(before, after), reg).answer.committed


@pytest.mark.parametrize('question', [
    'How many liters of water is each of the remaining bottles holding?',
    'How much water does each remaining bottle hold?',
    'How many liters of water does each remaining bottle hold?',
])
def test_remaining_holder_question_frames_reuse_the_same_partition(reg, question):
    prefix = holder_partition().split(', how', 1)[0] + '. '
    number(reg, prefix + question, 13.75)


@pytest.mark.parametrize('before,after', [
    ('4 of the', '12 of the'), ('4 of the', '13 of the'), ('4 of the', '4.5 of the'),
    ('150 liters', '30 liters'), ('10 liters', '10 kilograms'),
    ('remaining bottles', 'remaining jars'),
    ('each of the remaining', 'the remaining'),
    ('is each', 'are each'),
])
def test_remaining_holder_partition_boundaries(reg, before, after):
    assert not solve(holder_partition().replace(before, after), reg).answer.committed


def shortfall():
    return ("Nora's workout goal is 20 situps. "
            'On Monday, Nora was only able to do 7 situps, so she decided that she would '
            'make up for the rest on Tuesday. However, she was only able to do 9 situps on Tuesday. '
            "How many situps would Nora have to do on Wednesday to meet her minimum goal "
            "and make up for the ones she didn't do?")


@pytest.mark.parametrize('before,after', [
    ('workout goal', 'workout goal'), ('workout goal', 'daily goal'),
    ('workout goal', 'goal'), ('situps', 'pushups'),
    ('only able', 'able'), ('However, ', ''),
    ('would Nora', 'will Nora'),
    ('would Nora have to', 'must Nora'),
    ('would Nora have to', 'does Nora need to'),
    ('on Tuesday. However', 'on Wednesday. However'),
])
def test_minimums_and_missed_work_carry_between_named_days(reg, before, after):
    number(reg, shortfall().replace(before, after), 44)


def test_production_shortfalls_use_the_same_daily_goal_account(reg):
    text = shortfall().replace('workout goal', 'project goal').replace('situps', 'pages')
    number(reg, text, 44)


def test_daily_shortfalls_do_not_require_an_intention_or_limited_ability_clause(reg):
    text = ("Nora's daily goal is 20 pages. On Monday, Nora did 7 pages. "
            'On Tuesday, Nora did 9 pages. How many pages would Nora have to do on Wednesday '
            "to meet her minimum goal and make up for the ones she didn't do?")
    number(reg, text, 44)


def test_completed_work_can_clear_earlier_arrears_without_prepaying_a_future_minimum(reg):
    number(reg, shortfall().replace('9 situps', '35 situps'), 20)


@pytest.mark.parametrize('before,after', [
    ('20 situps.', '20 situps per week.'),
    ('on Tuesday. However', 'on Monday. However'),
    ('9 situps on Tuesday', '9 situps on Monday'),
    ('on Wednesday to meet', 'on Thursday to meet'),
    ('9 situps', '9 pushups'), ('7 situps', '-7 situps'),
    ('However, she', 'However, Ezra'),
    ('her minimum goal', 'his minimum goal'),
])
def test_make_up_minimum_requires_complete_days_and_matching_activity(reg, before, after):
    assert not solve(shortfall().replace(before, after), reg).answer.committed


def contributions():
    return ('A fox needs to gain 120 pounds. At the end of summer, the fox feasts on apples '
            'and small woodland birds. During autumn, it devours nuts and chicken. '
            'It gained a quarter of the weight it needed from apples during summer, and during autumn, '
            'it gained twice that amount from nuts. Chicken made up half of the remaining weight '
            'it had needed to gain. How many pounds did it gain eating small birds?')


@pytest.mark.parametrize('before,after', [
    ('pounds', 'pounds'), ('pounds', 'kilograms'), ('weight', 'mass'),
    ('a quarter', '25%'), ('apples', 'berries'), ('nuts', 'acorns'),
    ('made up', 'accounted for'), ('had needed', 'needed'),
    ('eating small birds', 'from small birds'),
    ('half of the remaining weight it had needed to gain', 'half of the rest'),
])
def test_closed_source_partitions_keep_original_relative_and_unassigned_bases(reg, before, after):
    number(reg, contributions().replace(before, after), 15)


def test_financial_source_partition_and_simplified_separate_statements(reg):
    text = ('Nora needs to earn 120 dollars. Nora receives from donations and grants. '
            'Nora receives from sales and fees. Nora earned a quarter of the money from donations. '
            'Nora earned twice that amount from sales. Fees accounted for half of the remaining money. '
            'How many dollars did Nora earn from grants?')
    number(reg, text, 15)
    number(reg, text.replace('a quarter of the money', '30 dollars'), 15)


def test_direct_source_amounts_also_support_the_simplest_lookup(reg):
    prefix = 'Nora earned 30 dollars from sales. Nora earned 1000 cents from sales. Nora earned 12 dollars from grants. '
    number(reg, prefix + 'How many dollars did Nora earn from sales?', 40)
    number(reg, prefix + 'How many dollars did Nora earn from grants?', 12)
    assert not solve(prefix + 'How many dollars did Ezra earn from sales?', reg).answer.committed


@pytest.mark.parametrize('before,after', [
    ('a quarter', '125%'), ('twice that amount', 'five times that amount'),
    ('eating small birds', 'eating rabbits'),
    ('the fox feasts', 'a fox feasts'),
    ('it devours', 'he devours'),
    ('during autumn, it gained', 'during winter, it gained'),
    ('weight it needed', 'volume it needed'),
    ('needs to gain', 'might need to gain'),
])
def test_source_partition_and_nonpersonal_reference_boundaries(reg, before, after):
    assert not solve(contributions().replace(before, after), reg).answer.committed


@pytest.mark.parametrize('rule_id', [
    'arithmetic/scoped-activity-rate',
    'arithmetic/contextual-relative-activity-rate',
    'arithmetic/coordinated-relative-activity-extent',
    'arithmetic/separate-participant-schedules',
    'arithmetic/per-event-preparation-duration',
    'arithmetic/distributive-event-duration',
    'arithmetic/measured-holder-whole',
    'arithmetic/measured-holder-subset-progressive',
    'arithmetic/fronted-performance-with-make-up-plan',
    'arithmetic/fronted-completed-performance',
    'arithmetic/preparation-with-contribution-target',
    'arithmetic/participant-from-source-inventory',
    'arithmetic/seasonal-on-source-inventory',
    'arithmetic/coordinated-source-relative-contribution',
    'arithmetic/attributed-remainder-contribution',
])
@pytest.mark.parametrize('seed', [581, 912])
def test_composition_premises_round_trip_through_generation(rule_id, seed):
    from rulekit.generation import generate_candidate
    candidate = generate_candidate(load_project(Path('projects/curated')), rule_id=rule_id, seed=seed)
    assert candidate.target_status == 'matched'
    assert not candidate.grammar_deficiencies
