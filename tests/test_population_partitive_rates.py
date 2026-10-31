"""Invented counted population parts and activities that establish a statistic's scope."""
from pathlib import Path

import pytest

from rulekit.data.project import load_project
from rulekit.generation import generate_candidate, generate_ask_scenario
from rulekit.kernel.engine import solve
from rulekit.kernel.model import BatchEvidence


@pytest.fixture(scope='module')
def project():
    return load_project(Path('projects/curated'))


def total(project, text, expected):
    result = solve(text, project.registry)
    assert result.answer.committed, result.answer
    assert result.value == pytest.approx(expected)
    assert not result.deficiencies()
    return result


def partition(fraction='two thirds', population='36 farm workers'):
    return (f'{fraction} of {population} receive an average of $9 per day '
            'while the rest gets an average of $3 a day')


def inquiry(activity='is calculating', frequency='daily '):
    return (f'A teacher {activity} the average {frequency}allowance of farm workers. '
            'Two thirds of the workers receive an average of $9 allowance per day '
            'while the rest gets an average of $3 a day. '
            'If she surveyed 36 workers, what is the total amount of money those 36 workers get per day?')


@pytest.mark.parametrize('activity', ['is calculating', 'was calculating', 'calculates', 'calculated',
                                     'is determining', 'was determining', 'determines', 'determined'])
@pytest.mark.parametrize('frequency', ['daily ', ''])
def test_assessment_activity_is_context_not_an_extra_receipt(project, activity, frequency):
    result = total(project, inquiry(activity, frequency), 252)
    contexts = [r for r in result.store.by_kind(BatchEvidence) if r.kind == 'population-rate-inquiry']
    assert len(contexts) == 1
    assert contexts[0].container_ref.qualifiers == ('farm',)


def test_plural_assessors_keep_finite_agreement_without_an_unbound_pronoun(project):
    text = inquiry('calculate').replace('A teacher', 'The teachers').replace('If she surveyed', 'The teachers surveyed').replace(', what is', '. What is')
    total(project, text, 252)


@pytest.mark.parametrize('fraction,expected', [('2/3', 252), ('two thirds', 252), ('two-thirds', 252),
                                              ('half', 216), ('1/2', 216), ('50%', 216)])
@pytest.mark.parametrize('prefix', ['', 'If '])
@pytest.mark.parametrize('question', [
    'What is the total amount of money the workers get per day?',
    'What is the total amount of money those farm workers get in a day?',
    'How much money do these workers receive each day?',
    'How much money do those farm workers receive in a day?',
    'What is the total amount of money those 36 workers get per day?',
])
def test_counted_partitives_and_population_references(project, fraction, expected, prefix, question):
    result = total(project, prefix + partition(fraction) + '. ' + question, expected)
    wholes = [r for r in result.store.by_kind(BatchEvidence) if r.kind == 'population-rate-whole']
    assert len(wholes) == 1
    assert wholes[0].value == 36
    assert wholes[0].container_ref.qualifiers == ('farm',)
    assert wholes[0].provenance.assumption == bool(prefix)


def test_comma_conditional_reuses_the_same_scoped_assumption(project):
    total(project, 'If ' + partition() + ', what is the total amount of money the workers get per day?', 252)


def test_nonliving_recipients_and_other_periods_reuse_the_weighted_total(project):
    text = ('If three fourths of 12 machines receive an average of $8 per hour '
            'while the rest gets an average of $4 an hour. '
            'What is the total amount of money the machines get per day?')
    total(project, text, 2016)


def test_mixed_compatible_rate_periods_are_converted_independently(project):
    text = partition().replace('$3 a day', '$3 an hour') + '. '
    total(project, text + 'What is the total amount of money the workers get per day?', 1080)


def test_an_inline_whole_can_have_an_explicit_inquiry_context(project):
    text = ('A teacher is calculating the average daily allowance of farm workers. '
            + partition().replace('$9 per day', '$9 allowance per day')
            + '. What is the total amount of money the workers get per day?')
    total(project, text, 252)


@pytest.mark.parametrize('edit', [
    ('36 farm workers', 'farm workers'),
    ('36 farm workers', '35 farm workers'),
    ('36 farm workers', '36.5 farm workers'),
    ('36 farm workers', '0 farm workers'),
    ('36 farm workers', '-36 farm workers'),
    ('two thirds', '0%'), ('two thirds', '100%'), ('two thirds', '4/3'),
    ('the workers get', 'the students get'),
    ('the workers get', 'the school workers get'),
    ('the workers get', 'the worker gets'),
    ('the workers get', 'those 40 workers get'),
    ('the workers get', 'those 36 students get'),
    ('two thirds of', 'two thirds'),
    ('while the rest gets an average of $3 a day', ''),
    ('while the rest gets an average of $3 a day', 'while the rest gets $3 a day'),
    ('receive an average', 'might receive an average'),
    ('receive an average', 'do not receive an average'),
    ('$3 a day', '$3 per meter'),
    ('get per day?', 'get?'),
])
def test_missing_or_inconsistent_wholes_and_incomplete_partitions_decline(project, edit):
    text = 'If ' + partition() + '. What is the total amount of money the workers get per day?'
    assert not solve(text.replace(*edit), project.registry).answer.committed


def test_a_question_count_does_not_invent_a_missing_premise_whole(project):
    text = partition(population='the workers') + '. How much money do those 36 workers receive per day?'
    assert not solve(text, project.registry).answer.committed


def test_an_unqualified_whole_does_not_establish_a_queried_subgroup(project):
    text = partition(population='36 workers') + '. How much money do the farm workers receive per day?'
    assert not solve(text, project.registry).answer.committed


def test_two_populations_or_two_independent_counts_are_not_merged(project):
    for extra in [partition('half', '12 machines') + '. ', 'Fia surveyed 36 workers. ']:
        text = partition() + '. ' + extra + 'What is the total amount of money the workers get per day?'
        assert not solve(text, project.registry).answer.committed


def test_a_detached_conditional_must_be_adjacent_and_complete(project):
    for extra in ['Fia has 2 books. ', 'A teacher calculates the average daily allowance of workers. ']:
        text = 'If ' + partition() + '. ' + extra + 'What is the total amount of money the workers get per day?'
        assert not solve(text, project.registry).answer.committed


@pytest.mark.parametrize('activity', ['might calculate', 'is not calculating', 'was calculated',
                                     'calculate', 'are calculating'])
def test_inquiry_activity_cannot_hide_negation_modality_or_bad_agreement(project, activity):
    assert not solve(inquiry(activity), project.registry).answer.committed


@pytest.mark.parametrize('rule_id', ['arithmetic/population-rate-assessment-progressive',
                                   'arithmetic/population-rate-assessment-finite',
                                   'arithmetic/population-average-rates-counted-whole'])
def test_new_context_and_partition_rules_generate_complete_matches(project, rule_id):
    candidate = generate_candidate(project, rule_id=rule_id, seed=428)
    assert candidate.target_status == 'matched', candidate
    assert not candidate.grammar_deficiencies


@pytest.mark.parametrize('ask_id', ['ask/population-total-periodic-amount-reference',
                                  'ask/population-total-periodic-amount-rate-reference',
                                  'ask/population-total-periodic-money-reference',
                                  'ask/population-total-periodic-money-interval-reference'])
def test_reference_questions_generate_without_inventing_a_count(project, ask_id):
    candidate = generate_ask_scenario(project, ask_id=ask_id, seed=429)
    assert candidate.target_ask == ask_id
    assert not candidate.query.get('population')


def test_an_observation_count_also_supports_a_later_uncounted_reference(project):
    text = ('Fia surveyed 36 farm workers. Two thirds of the workers receive an average of $9 per day '
            'while the rest gets an average of $3 a day. '
            'What is the total amount of money the workers get per day?')
    total(project, text, 252)
