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


@pytest.mark.parametrize('opening, charges, payer, expected', [
    ('Four workers worked at a workshop and bought',
     '4 cartons of paper priced at $3 each; and 4 pens costing $2 each', 'worker', 5),
    ('Three teams purchased',
     '3 pairs of shoes selling for $9 each; and 3 bags of socks that cost $3 in total', 'team', 10),
    ('Two students attended a meeting at the library and ordered',
     '2 boxes of pencils priced at $6 each; and 2 books costing $4 each', 'student', 10),
    ('Two students took a trip and ordered', '2 tickets priced at $6 each', 'student', 6),
    ('Two companies met at the office and purchased', '2 cases of batteries costing $6 each', 'company', 6),
    ('Three artists purchased',
     '3 portions of clay costing $4 each; and 6 slices of foam priced at $2 each', 'artist', 8),
    ('Two workers bought', '2 scoops of sand costing $6 in total', 'worker', 3),
    ('Four artists shopped at a market and bought', '4 sets of pens listed at $8 in total', 'artist', 2),
    ('Two workers bought', '2 cups of water costing $1 each; and 2 bottles of tea priced at $4 in total', 'worker', 3),
    ('Two students ate at school and ordered', '2 pieces of cake costing $3 each', 'student', 3),
])
def test_itemized_activity_and_package_prices(reg, opening, charges, payer, expected):
    text = (f'{opening} the following: {charges}. '
            f'They split the invoice equally. How much does each {payer} pay?')
    result = solve(text, reg)
    assert result.value == expected, result.answer
    assert not result.deficiencies()


@pytest.mark.parametrize('before, after', [
    ('arrived at school', 'arrived at a jar'),
    ('arrived at school', 'ate a meeting at school'),
    ('arrived at school', 'attended a trip at school'),
    ('workers arrived at school', 'companies ate at school'),
    ('workers arrived at school', 'companies ate lunch at school'),
    ('workers arrived at school', 'boxes arrived at school'),
    ('arrived at school', 'works at school'),
    ('arrived at school', 'attends a meeting at school'),
    ('and ordered', 'and orders'),
    ('pairs of shoes', 'pairs of paper'),
    ('pairs of shoes', 'servings of batteries'),
    ('pairs of shoes', 'slices of pens'),
    ('split the invoice equally', 'split the invoice'),
])
def test_itemized_cost_requires_compatible_evidence(reg, before, after):
    text = ('Two workers arrived at school and ordered the following: '
            '2 pairs of shoes costing $5 each; and 2 books costing $3 each. '
            'They split the invoice equally. How much will each of them pay?')
    assert solve(text.replace(before, after), reg).answer.kind == 'decline'


@pytest.mark.parametrize('package, item', [('carton', 'paper'), ('pair', 'shoes')])
def test_named_activity_prices_use_the_same_units(reg, package, item):
    text = (f'Nora and Iris attended a meeting. A {package} of {item} costs $4. '
            f'Nora had 2 {package}s of {item}. Iris had 3 {package}s of {item}. '
            'What did their meeting cost?')
    result = solve(text, reg)
    assert result.value == 20, result.answer
    assert not result.deficiencies()
    different_unit = text.replace(f'A {package} of', 'A box of')
    assert not solve(different_unit, reg).answer.committed
    assert not solve(text.replace(package, 'serving'), reg).answer.committed


def test_each_payer_refers_to_the_counted_group(reg):
    text = ('Three teams purchased the following: 3 pairs of shoes costing $12 each. '
            'How much does each team pay if they split the invoice equally?')
    assert solve(text, reg).value == 12
    assert not solve(text.replace('each team', 'each player'), reg).answer.committed
