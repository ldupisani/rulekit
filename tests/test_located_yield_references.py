"""Scoped yields across sentence boundaries and elided ordinal site heads."""
from pathlib import Path
import pytest
from rulekit.data.project import load_project
from rulekit.kernel.engine import solve, analyze

@pytest.fixture(scope='module')
def reg():
    return load_project(Path('projects/curated')).registry


def story(site='neighbourhood', descriptor='different'):
    return (f'Mira goes trick-or-treating in her {site}. '
            'She gets 9 pieces of candy per house. '
            f'Her brother Owen goes trick-or-tricking in a {descriptor} {site} '
            'where he gets 7 pieces of candy per house. '
            f'If the first {site} has 30 houses and the second has 35 houses, '
            'how many more pieces of candy does Mira get?')


@pytest.mark.parametrize('site',['neighbourhood','neighborhood','subdivision','road','street'])
@pytest.mark.parametrize('descriptor',['different','neighboring','neighbouring'])
def test_separate_rate_and_elided_site(reg,site,descriptor):
    r=solve(story(site,descriptor),reg)
    assert r.answer.value==25,r.answer
    assert not r.deficiencies(),r.deficiencies()


@pytest.mark.parametrize('edit',[
    lambda q:q.replace('She gets','Mira gets'),
    lambda q:q.replace('the second has','the second neighbourhood has'),
    lambda q:q.replace('in her neighbourhood','in a neighbourhood'),
    lambda q:q.replace('in her neighbourhood',"in Mira's neighbourhood"),
    lambda q:q.replace('per house','per shop').replace('houses','shops'),
    lambda q:q.replace('candy','cookies'),
    lambda q:q.replace('more pieces of candy does Mira','fewer pieces of candy does Owen'),
    lambda q:q.replace('in her neighbourhood. She gets','in her neighbourhood where she gets'),
    lambda q:q.replace('where he gets 7 pieces of candy per house.',
                       '. Owen gets 7 pieces of candy per house.'),
])
def test_located_yield_paraphrases(reg,edit):
    r=solve(edit(story()),reg)
    assert r.answer.value==25,r.answer
    assert not r.deficiencies(),r.deficiencies()


@pytest.mark.parametrize('edit',[
    lambda q:q.replace('She gets','Tess gets'),
    lambda q:q.replace('Mira goes trick-or-treating in her neighbourhood. ',''),
    lambda q:q.replace('She gets','Mira has 2 books. She gets'),
    lambda q:q.replace('the first neighbourhood','the first'),
    lambda q:q.replace('the second has','the third has'),
    lambda q:q.replace('the second has','the first has'),
    lambda q:q.replace('different neighbourhood','different road'),
    lambda q:q.replace('35 houses','35 shops'),
    lambda q:q.replace('7 pieces of candy','7 pieces of cake'),
    lambda q:q.replace('35 houses','35.5 houses'),
    lambda q:q.replace('different neighbourhood','large neighbourhood'),
    lambda q:q.replace('She gets','She loses'),
    lambda q:q.replace('9 pieces','9.5 pieces'),
])
def test_unbound_or_incompatible_site_references_decline(reg,edit):
    assert solve(edit(story()),reg).answer.kind=='decline'


@pytest.mark.parametrize('singular,plural', [('neighborhood','neighborhoods'), ('neighbourhood','neighbourhoods')])
def test_american_and_british_site_inflections(reg,singular,plural):
    assert reg.word_in_category(singular,'local_yield_site')
    for phrase,value in ((f'1 {singular}',1),(f'3 {plural}',3)):
        reading=analyze(phrase,reg)
        assert any(u.features.get('lemma')==singular and u.features.get('value')==value
                   for u in reading.units)
