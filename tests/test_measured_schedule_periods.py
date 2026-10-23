"""Explicit duration modifiers on calendar periods do not define calendar defaults."""
import pytest
from rulekit.data.project import load_project
from rulekit.kernel.engine import solve


@pytest.fixture(scope='module')
def reg():
    return load_project('projects/curated').registry


@pytest.mark.parametrize('period', ['three week month', '3 week month', 'three-week month', '3-week month'])
@pytest.mark.parametrize('activity,ask', [
    ('practices the piano for 15 minutes a day and the guitar for twice as long', 'spend practicing'),
    ('studies the book for 15 minutes a day and the poem for twice as long', 'spend studying'),
    ('practices the piano for 15 minutes a day and the guitar for twice as long', 'practice'),
])
def test_measured_month(reg, period, activity, ask):
    verb = 'studies' if activity.startswith('studies') else 'practices'
    result = solve(f'Nora {activity}. She {verb} 4 days a week. '
                   f'How many minutes does she {ask} in a {period}?', reg)
    assert result.answer.value == 540, result.answer
    assert not result.deficiencies()


@pytest.mark.parametrize('period', ['five day week', 'five-day week'])
def test_other_explicit_periods_and_simple_rates(reg, period):
    result = solve(f'Nora studies 12 minutes a day. How many minutes does Nora study in a {period}?', reg)
    assert result.answer.value == 60, result.answer
    assert not result.deficiencies()


@pytest.mark.parametrize('period', ['a month', 'three months', 'three week months', 'a three-hour month'])
def test_no_default_or_incompatible_period_conversion(reg, period):
    result = solve('Nora practices 15 minutes a day. She practices 4 days a week. '
                   f'How many minutes does Nora practice in {period}?', reg)
    assert not result.answer.committed
