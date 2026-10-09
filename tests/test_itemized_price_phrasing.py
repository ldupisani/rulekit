"""Explicit quote paraphrases share unit/lot arithmetic; valuation is not cost."""
from pathlib import Path
import pytest
from rulekit.data.project import load_project
from rulekit.kernel.engine import solve

@pytest.fixture(scope='module')
def reg():
    return load_project(Path('projects/curated')).registry


def account(item, phrase, ending=''):
    return (f'Four friends order the following: {item} {phrase} $3{ending}; '
            'and 2 cups of coffee that cost $2 each. '
            'How much will each of them pay if they split the bill equally?')


@pytest.mark.parametrize('item', ['4 portions of cake', '4 cakes', '4 boxes of books'])
@pytest.mark.parametrize('phrase', ['that cost', 'costing', 'priced at', 'listed at', 'selling for'])
@pytest.mark.parametrize('ending,expected', [('', 4), (' each', 4), (' in total', 1.75)])
def test_itemized_price_paraphrases(reg, item, phrase, ending, expected):
    result=solve(account(item, phrase, ending),reg)
    assert result.answer.kind=='number', result.answer
    assert result.answer.value==pytest.approx(expected)
    assert not result.deficiencies(),result.deficiencies()


@pytest.mark.parametrize('phrase', ['costing', 'priced at', 'listed at', 'selling for'])
def test_single_quote_in_mixed_price_list(reg, phrase):
    result=solve(account('1 platter of spaghetti', phrase),reg)
    assert result.answer.value==pytest.approx(1.75),result.answer
    assert not result.deficiencies(),result.deficiencies()


@pytest.mark.parametrize('phrase', ['priced', 'listed', 'selling', 'costing at',
                                    'priced for', 'listed for', 'selling at',
                                    'that costing', 'that priced at', 'valued at', 'worth', 'estimated at'])
def test_incomplete_price_frames_and_values_do_not_establish_bill(reg, phrase):
    assert solve(account('4 cakes', phrase),reg).answer.kind=='decline'


@pytest.mark.parametrize('ending', [' each in total', ' in total each', ' each plus $2'])
def test_conflicting_or_extra_charges_are_not_ignored(reg, ending):
    assert solve(account('4 cakes', 'priced at', ending),reg).answer.kind=='decline'
