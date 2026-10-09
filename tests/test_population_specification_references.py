"""Group-scoped ratio adoption retains ownership and explicit populations."""
from pathlib import Path
import pytest
from rulekit.data.project import load_project
from rulekit.kernel.engine import solve
from rulekit.kernel.model import SpecificationEvidence

@pytest.fixture(scope='module')
def reg():
    return load_project(Path('projects/curated')).registry


def plan(group='family', adoption='everyone'):
    return (f'Mira is making coffee for her {group}. '
            'She knows her mom drinks a 10-ounce cup of coffee and uses 2 ounces of coffee. '
            f'She will use this same ratio for {adoption}. '
            f'Her {group} has 5 people and each of them wants a 6-ounce cup of coffee. '
            'How many ounces of coffee does she need?')


@pytest.mark.parametrize('group', ['family', 'household', 'team'])
@pytest.mark.parametrize('adoption', ['everyone', 'her {group}', "Mira's {group}"])
def test_owned_group_and_reference_variants(reg, group, adoption):
    result=solve(plan(group,adoption.format(group=group)),reg)
    assert result.answer.value==pytest.approx(6),result.answer
    assert not result.deficiencies(),result.deficiencies()
    scoped=[r for r in result.store.by_kind(SpecificationEvidence) if r.kind in ('context','target')]
    assert len(scoped)==2
    assert all(r.scope_ref.owner.head=='mira' for r in scoped)


@pytest.mark.parametrize('group', ['family', 'household', 'team'])
def test_named_owner_and_unowned_group(reg, group):
    for text in (plan(group).replace('her '+group,"Mira's "+group).replace('Her '+group,"Mira's "+group),
                 plan(group).replace('her '+group,'the '+group).replace('Her '+group,'The '+group)):
        result=solve(text,reg)
        assert result.answer.value==pytest.approx(6),result.answer
        assert not result.deficiencies(),result.deficiencies()


@pytest.mark.parametrize('edit', [
    lambda q:q.replace('Her family has',"Nora's family has"),
    lambda q:q.replace('Her family has','Her team has'),
    lambda q:q.replace('Her family has','The family has'),
    lambda q:q.replace('for everyone',"for Nora's family"),
    lambda q:q.replace('same ratio','different ratio'),
    lambda q:q.replace('5 people','5 machines'),
    lambda q:q.replace('5 people','5.5 people'),
    lambda q:q.replace('Her family has 5 people','Her family has 5 people and 3 children'),
    lambda q:q.replace('a 6-ounce cup of coffee','a 6-ounce cup of tea'),
    lambda q:q.replace('She will use this same ratio for everyone. ',''),
    lambda q:q.replace('Mira is making coffee for her family. ',''),
    lambda q:q.replace('Her family has','Her large family has'),
])
def test_scope_and_universal_reference_boundaries(reg, edit):
    assert solve(edit(plan()),reg).answer.kind=='decline'


def test_universal_population_reference_is_not_food_specific(reg):
    text=('Mira is making clay for her team. '
          'An 8-kilogram box of clay requires 1 kilogram of water. '
          'She uses the same ratio for everyone. '
          'Her team has 12 workers and each of them needs a 6-kilogram box of clay. '
          'How many kilograms of water does Mira need?')
    result=solve(text,reg)
    assert result.answer.value==9,result.answer
    assert not result.deficiencies(),result.deficiencies()
