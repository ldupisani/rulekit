"""Cross-domain boundaries for benefit receipt, item operations, roles and partitions."""
import pytest
from rulekit.data.project import load_project
from rulekit.kernel.engine import solve
from rulekit.generation import generate_candidate
from rulekit.generation.sample import GenerationError

@pytest.fixture(scope='module')
def project():
    return load_project('projects/curated')

def matched(project, text, prefix):
    r=solve(text,project.registry)
    return any(f.provenance.source.startswith(prefix)
               for f in r.store.facts)

@pytest.mark.parametrize('verb',['received','got','obtained','earned'])
@pytest.mark.parametrize('item',['tickets','books'])
def test_benefit_receipt(project,verb,item):
    singular=item[:-1]
    q=(f'A {singular} costs $20. Mira bought 6 {item} and {verb} a 25% discount on each {singular} above 4. '
       'How much did Mira pay in all?')
    assert solve(q,project.registry).answer.value==110

@pytest.mark.parametrize('verb,share',[('purchased','half'),('bought','20%'),('received','five halves'),('received','150%')])
def test_invalid_discount_relation(project,verb,share):
    q=f'Mira bought 6 books and {verb} a {share} discount on each book above 4.'
    assert not matched(project,q,'arithmetic/purchase-discount-above-threshold')

@pytest.mark.parametrize('acquire,item,dispose,expected',[
 ('downloaded','files','deleted',12),('collected','bananas','discarded',12),
 ('received','books','rejected',12),('downloaded','bananas','discarded',None),
 ('collected','bananas','deleted',None),('received','books','deleted',None),
])
@pytest.mark.parametrize('separate',[False,True])
def test_operation_theme_in_explicit_and_anaphoric_batches(project,acquire,item,dispose,expected,separate):
    join='. She ' if separate else ' and '
    q=f'Mira {acquire} 24 {item}{join}{dispose} half of them. How many {item} remain?'
    r=solve(q,project.registry)
    if expected is None:assert not r.answer.committed,r.answer
    else:assert r.answer.value==expected,r.answer


def test_question_local_deletion_resolves_the_item_type(project):
    q=('Mira collected 24 books and realized that half of them were irrelevant. '
       'How many books remain after deleting the irrelevant books?')
    assert not solve(q,project.registry).answer.committed
    assert solve(q.replace('deleting','discarding'),project.registry).answer.value==12

@pytest.mark.parametrize('text',[
 'Mira was brother at the park.','Mira was a brother at the park.',
 'Mira was a teacher at the road.','Mira was teacher at the school.',
])
def test_role_language_needs_role_site_and_determiner(project,text):
    assert not matched(project,text,'arithmetic/personal-role-at-')

@pytest.mark.parametrize('role,place',[('teacher','school'),('worker','company'),('painter','park')])
def test_meaningful_roles_across_domains(project,role,place):
    assert matched(project,f'Mira was a {role} at the {place}.','arithmetic/personal-role-at-')


def test_office_title_can_omit_article(project):
    assert matched(project,'Mira was president at the company.','arithmetic/office-role-at-')

@pytest.mark.parametrize('first,last,item',[
 ('next','left','roses'),('red','large','balls'),('red','red','balls'),
])
def test_inventory_is_not_an_arbitrary_modifier_partition(project,first,last,item):
    assert not matched(project,f'In a box there are 12 {first} {item} and 8 {last} {item}.','arithmetic/located-inventory-')

@pytest.mark.parametrize('first,last,item',[('red','blue','balls'),('large','small','boxes'),('ripe','unripe','apples')])
def test_declared_partition_family(project,first,last,item):
    q=(f'In a truck there are 12 {first} {item} and 8 {last} {item}. '
       f'Mira removes 2 {first} {item}. Calculate the total number of {item} that remain in the truck.')
    assert solve(q,project.registry).answer.value==18

@pytest.mark.parametrize('rule,bindings',[
 ('arithmetic/purchase-discount-above-threshold',{'get':'purchased'}),
 ('arithmetic/after-acquisition-discard-reason',{'acquire':'downloading','item':'12 bananas'}),
 ('arithmetic/after-acquisition-discard-reason',{'acquire':'collecting','item':'12 bananas','verb':'deletes'}),
 ('arithmetic/personal-role-at-definite-location',{'role':'brother'}),
 ('arithmetic/personal-role-at-definite-location',{'place':'avenue'}),
 ('arithmetic/located-inventory-two-subtypes',{'first':'12 next roses','last':'8 left roses'}),
 ('arithmetic/located-inventory-two-subtypes',{'first':'12 red balls','last':'8 large balls'}),
])
def test_strict_generation_refuses_reviewed_combination(project,rule,bindings):
    with pytest.raises(GenerationError):
        generate_candidate(project,rule_id=rule,seed=7,locked_bindings=bindings,max_attempts=4)

@pytest.mark.parametrize('family',['size','ripeness'])
@pytest.mark.parametrize('count',['two'])
def test_new_partition_variants_generate(project,family,count):
    c=generate_candidate(project,rule_id=f'arithmetic/located-inventory-{count}-subtypes-{family}',seed=7)
    assert c.target_status=='matched'


@pytest.mark.parametrize("verb,item", [("received", "books"), ("collected", "coins"), ("downloaded", "files")])
def test_complete_verb_frames_preserve_comparisons(project, verb, item):
    q=(f"Mira {verb} 4 {item}. Owen {verb} twice as many {item} as Mira. "
       f"How many {item} did Owen { {'received':'receive','collected':'collect','downloaded':'download'}[verb] }?")
    assert solve(q, project.registry).answer.value == 8


def test_receipt_of_currency_is_not_narrowed_to_batch_goods(project):
    result=solve("Mira received $40. How much money did Mira receive?", project.registry)
    assert result.answer.value == 40
