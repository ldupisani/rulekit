"""Complete-domain cost references over explicitly priced purchases."""
import pytest
from rulekit.data.project import load_project
from rulekit.kernel.engine import solve


@pytest.fixture(scope='module')
def reg():
    return load_project('projects/curated').registry


@pytest.mark.parametrize('ending', ['altogether', 'in total', ''])
@pytest.mark.parametrize('item,goods', [('banana', 'candy'), ('hat', 'books')])
def test_complete_basket_reference(reg, ending, item, goods):
    text = (f"Nora's parents bought a {item} for $8. They bought 2 bags of {goods} for $3 per bag, "
            f'and 4 bags of {goods} for $5 per bag. How much did everything cost {ending}?')
    result = solve(text, reg)
    assert result.answer.value == 34, result.answer
    assert not result.deficiencies()


@pytest.mark.parametrize('premises,expected', [
    ('Nora bought a hat for $8.', 8),
    ('Nora bought a hat for $8. Nora bought a book for $6.', 14),
    ('Nora bought 2 bags of candy for $3 per bag, and 4 bags of books for $5 per bag.', 26),
])
def test_complete_reference_needs_no_special_container_or_collection(reg, premises, expected):
    result = solve(premises + ' How much does everything cost altogether?', reg)
    assert result.answer.value == expected, result.answer
    assert not result.deficiencies()


@pytest.mark.parametrize('premises', [
    'Nora bought a hat for $8. Ezra bought 2 bags of books for $3 per bag.',
    'Nora bought a hat for $8. They bought 2 bags of books for $3 per bag.',
    'Nora bought a hat for $8. Nora bought books.',
    'Nora bought a hat for $8. Nora bought 2 bags of books for $3 per bottle.',
    'Nora bought a hat for $8. Nora has $20.',
    'They bought 2 bags of books for $3 per bag.',
])
def test_complete_reference_preserves_scope_and_completeness(reg, premises):
    assert not solve(premises + ' How much did everything cost altogether?', reg).answer.committed
