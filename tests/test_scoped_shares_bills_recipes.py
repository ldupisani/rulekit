"""Invented examples for threshold complements and scoped proportional accounts."""
from pathlib import Path
import pytest
from rulekit.data.project import load_project
from rulekit.kernel.engine import solve,analyze
from rulekit.kernel.model import SpecificationEvidence

@pytest.fixture(scope='module')
def reg():return load_project(Path('projects/curated')).registry

def threshold(label='C',percent='25%',total=48,head='Grade',assessment='final grade'):
    return (f'Ms. Vale found out that {percent} of her {head} 4 students received a {assessment} below {label}. '
            f'How many of her students received a {assessment} of {label} and above if she has {total} students in {head} 4?')

def earnings(total=96,share='half',relative='half'):
    return (f'Mira, Tess, and Nora earned ${total} from washing cars all week. '
            f'However, {share} of the ${total} was earned by Mira. '
            f'Nora earned {relative} of what Mira earned. How much more money did Mira earn than Nora?')


def bill():
    return ('Four friends eat at a restaurant and order the following: '
            '4 pieces of cake that cost $2 each; 3 cups of coffee that cost $2; '
            'and 2 plates of spaghetti that cost $1 each. '
            'How much will each of them pay if they share the bill equally?')


def recipe(product='coffee',unit='ounce',reference=10,ingredient=2,people=5,size=6):
    return (f'Mira is making {product} for a party. '
            f'She knows her mom drinks a {reference}-{unit} cup of {product} and uses {ingredient} {unit}s of {product}. '
            'She will use the same ratio for the party. '
            f'The party has {people} people there and each of them wants a {size}-{unit} cup of {product}. '
            f'How many {unit}s of {product} does she need?')


def yields(a=9,b=7,first=30,second=35,site='neighborhood',item='candy'):
    return (f'Mira goes trick-or-treating in a {site} where she gets {a} pieces of {item} per house. '
            f'Her brother Owen goes trick-or-treating in a neighboring {site} where he gets {b} pieces of {item} per house. '
            f'If the first {site} has {first} houses and the second {site} has {second} houses, '
            f'how many more pieces of {item} does Mira get?')


def check(reg,text,value):
    result=solve(text,reg)
    assert result.answer.kind=='number',result.answer
    assert result.answer.value==pytest.approx(value),result.answer
    assert not result.deficiencies(),result.deficiencies()
    return result

@pytest.mark.parametrize('label',['A','B','C','D','F'])
@pytest.mark.parametrize('head,assessment',[('Grade','final grade'),('level','rating')])
def test_threshold_labels_are_scoped_not_quantities(reg,label,head,assessment):
    check(reg,threshold(label=label,head=head,assessment=assessment),36)

@pytest.mark.parametrize('percent,total,expected',[('50%',30,15),('1/4',80,60),('0%',20,20),('100%',20,0)])
def test_threshold_fraction_variants(reg,percent,total,expected):
    check(reg,threshold(percent=percent,total=total),expected)

@pytest.mark.parametrize('edit',[
 lambda q:q.replace('grade of C and above','grade above C'),
 lambda q:q.replace('grade of C and above','grade of B and above'),
 lambda q:q.replace('48 students in Grade 4','48 students in Grade 6'),
 lambda q:q.replace('48 students in Grade 4','48 students in Level 4'),
 lambda q:q.replace('25%','125%'),
 lambda q:q.replace('48 students','47 students'),
 lambda q:q.replace('she has 48','Tess has 48'),
 lambda q:q.replace('final grade of C','rating of C'),
 lambda q:q.replace('of her students','of your students'),
])
def test_threshold_boundaries(reg,edit):assert solve(edit(threshold()),reg).answer.kind=='decline'


def test_threshold_strict_query_and_upper_complement(reg):
    check(reg,threshold().replace('of C and above','below C'),12)
    check(reg,threshold().replace('below C','above C').replace('of C and above','of C and below'),36)

@pytest.mark.parametrize('total,share,relative,expected',[(96,'half','half',24),(120,'25%','1/3',20),(180,'1/3','25%',45)])
def test_joint_earning_shares(reg,total,share,relative,expected):check(reg,earnings(total,share,relative),expected)


def test_active_share_and_plain_joint_total(reg):
    q=earnings().replace(' from washing cars all week','').replace('However, half of the $96 was earned by Mira.','Mira earned half of the $96.')
    check(reg,q,24)

@pytest.mark.parametrize('edit',[
 lambda q:q.replace('half of the $96','half of the $90'),
 lambda q:q.replace('by Mira','by Eva'),
 lambda q:q.replace('Nora earned half','Nora earned 150%'),
 lambda q:q.replace('Nora earned half of what Mira earned','Mira earned half of what Nora earned'),
 lambda q:q.replace('half of the $96','90% of the $96'),
 lambda q:q.replace('than Nora','than Tess'),
 lambda q:q.replace('from washing cars all week','from washing 5 cars all week'),
])
def test_joint_share_scope_boundaries(reg,edit):assert solve(edit(earnings()),reg).answer.kind=='decline'


def test_itemized_bill(reg):check(reg,bill(),4)


def test_itemized_line_total_overrides_unit_quote(reg):
    check(reg,bill().replace('3 cups of coffee that cost $2','3 cups of coffee that cost $2 in total'),3)


def test_itemized_direct_objects_and_named_payer(reg):
    q=bill().replace('4 pieces of cake','4 cakes').replace('2 plates of spaghetti','2 hamburgers').replace('will each of them pay','does each friend pay')
    check(reg,q,4)

@pytest.mark.parametrize('edit',[
 lambda q:q.replace('Four friends','Zero friends'),
 lambda q:q.replace('Four friends','2.5 friends'),
 lambda q:q.replace('equally',''),
 lambda q:q.replace('3 cups','3.5 cups'),
 lambda q:q.replace('$2 each','2 liters each'),
 lambda q:q.replace('and 2 plates','and 7 unknown-items and 2 plates'),
 lambda q:q.replace('bill equally','bill equally with a $2 fee'),
])
def test_itemized_bill_boundaries(reg,edit):assert solve(edit(bill()),reg).answer.kind=='decline'

@pytest.mark.parametrize('product,unit',[('coffee','ounce'),('tea','gram')])
@pytest.mark.parametrize('reference,ingredient,people,size,expected',[(10,2,5,6,6),(12,3,8,6,12),(20,5,3,10,7.5)])
def test_recipe_scaling_keeps_input_and_output_roles(reg,product,unit,reference,ingredient,people,size,expected):
    result=check(reg,recipe(product,unit,reference,ingredient,people,size),expected)
    assert len(result.store.by_kind(SpecificationEvidence))==4


def test_direct_reference_recipe(reg):
    q=recipe().replace('She knows her mom drinks a 10-ounce cup of coffee and uses','A 10-ounce cup of coffee uses')
    check(reg,q,6)

@pytest.mark.parametrize('edit',[
 lambda q:q.replace('same ratio','different ratio'),
 lambda q:q.replace('She will use the same ratio for the party. ',''),
 lambda q:q.replace('a 10-ounce cup','a 0-ounce cup'),
 lambda q:q.replace('has 5 people','has 5.5 people'),
 lambda q:q.replace('a 6-ounce cup of coffee','a 6-ounce cup of tea'),
 lambda q:q.replace('How many ounces of coffee','How many ounces of tea'),
 lambda q:q.replace('does she need','does Nora need'),
 lambda q:q.replace('a 6-ounce cup','a 6-house cup'),
])
def test_recipe_scope_boundaries(reg,edit):assert solve(edit(recipe()),reg).answer.kind=='decline'

@pytest.mark.parametrize('site,item',[('neighborhood','candy'),('subdivision','cookie'),('road','cake'),('street','hamburger')])
def test_located_yield_comparison(reg,site,item):check(reg,yields(site=site,item=item),25)


def test_plain_located_yields_and_explicit_standard(reg):
    q=('Mira gets 9 pieces of candy per house in a neighborhood. Owen gets 7 pieces of candy per house in a neighborhood. '
       'The first neighborhood has 30 houses and the second neighborhood has 35 houses. '
       'How many more pieces of candy does Mira get than Owen?')
    check(reg,q,25)


def test_reversed_yield_comparison(reg):
    q=yields().replace('more pieces of candy does Mira','fewer pieces of candy does Owen')
    check(reg,q,25)

@pytest.mark.parametrize('edit',[
 lambda q:q.replace('second neighborhood','first neighborhood'),
 lambda q:q.replace('35 houses','35 shops'),
 lambda q:q.replace('7 pieces of candy','7 pieces of cake'),
 lambda q:q.replace('neighboring neighborhood','neighboring road'),
 lambda q:q.replace('does Mira get','does Eva get'),
 lambda q:q.replace('30 houses','20 houses'),
 lambda q:q.replace('9 pieces','9.5 pieces'),
 lambda q:q.replace('gets 7 pieces','loses 7 pieces'),
])
def test_located_yield_scope_boundaries(reg,edit):assert solve(edit(yields()),reg).answer.kind=='decline'


def test_numeric_class_index_does_not_count_following_students(reg):
    units=analyze('Grade 8 students',reg).units
    assert any(u.features.get('lemma')=='grade' and u.features.get('label')=='8' for u in units)
    assert all('value' not in u.features for u in units)
    ordinary=analyze('Every year 8 students arrive',reg).units
    assert any(u.features.get('lemma')=='student' and u.features.get('value')==8 for u in ordinary)


def test_independently_stated_threshold_population(reg):
    check(reg,'Nora has 48 students in Level 4. 25% of her Level 4 students received a rating below C. How many of her students received a rating of C and above?',36)


def test_earning_shares_reuse_existing_comparison_grammar(reg):
    check(reg,earnings().replace('half of what Mira earned','half as much as Mira'),24)
    check(reg,earnings(total=120,share='25%').replace('Nora earned half of what Mira earned','Nora earned twice as much as Mira').replace('did Mira earn than Nora','did Nora earn than Mira'),30)


def test_fronted_equal_split_assumption(reg):
    check(reg,bill().replace('How much will each of them pay if they share the bill equally?', 'If they will split the bill equally, how much will each of them pay?'),4)


def test_equal_split_must_be_stated_for_short_question(reg):
    short=bill().replace('How much will each of them pay if they share the bill equally?', 'How much will each of them pay?')
    assert solve(short,reg).answer.kind=='decline'
    check(reg,short.replace('How much','They split the bill equally. How much'),4)


def test_recipe_requirement_and_present_reuse_paraphrases(reg):
    check(reg,recipe().replace('wants','needs').replace('there and','and').replace('will use the same','uses the same'),6)


def test_local_yield_receipt_paraphrase(reg):
    check(reg,yields().replace('gets','receives').replace(' get?',' receive?'),25)


@pytest.mark.parametrize('verb', ['order', 'buy', 'purchase'])
@pytest.mark.parametrize('items', [
    '4 pencils that cost $2 each; and 2 books that cost $4 each',
    '4 boxes of pencils that cost $2 each; and 2 packs of paper that cost $4 each',
    '4 shirts that cost $2 each; and 2 hats that cost $4 each',
])
def test_shared_purchase_account_is_independent_of_dining(reg, verb, items):
    from rulekit.kernel.model import Expenditure
    q = (f'Four friends {verb} the following: {items}. '
         'They divide the bill equally. How much does each friend pay?')
    result = check(reg, q, 4)
    expenses = result.store.by_kind(Expenditure)
    assert len(expenses) == 2
    assert all(e.basis == 'quote' and e.unit_price is not None for e in expenses)


def test_shared_account_whole_package_cost(reg):
    check(reg, 'Three friends buy the following: 4 boxes of pencils that cost $9 in total; '
          'and 3 books that cost $2 each. They share the bill equally. '
          'How much does each friend pay?', 5)


def test_individual_earnings_keep_existing_holdings_path(reg):
    check(reg, 'Mira earned $24. How much money did Mira earn?', 24)


@pytest.mark.parametrize('tail', [
    'They also pay a $6 fee.',
    'Two friends buy the following: 2 books that cost $6 each.',
    'Nora paid $6 for a book.',
])
def test_shared_account_rejects_unallocated_charges_and_other_groups(reg, tail):
    q = ('Three friends buy the following: 3 books that cost $6 each. '
         f'{tail} They split the bill equally. How much does each friend pay?')
    assert solve(q, reg).answer.kind == 'decline'


def test_recipe_input_unit_conversion_preserves_roles(reg):
    check(reg, recipe().replace('How many ounces', 'How many kilograms'), 0.17009713875)


def test_enumeration_minimum_requires_an_enumeration_contract():
    from pydantic import ValidationError
    from rulekit.data.schemas import MatchToken
    with pytest.raises(ValidationError, match='requires enumeration_cat'):
        MatchToken(slot='people', span=True, enumeration_min_members=2)


@pytest.mark.parametrize('cost_noun', ['bill', 'cost', 'expense'])
def test_shared_cost_noun_paraphrases(reg, cost_noun):
    check(reg, f'Three friends purchase the following: 3 books that cost $6 each. '
          f'They share the {cost_noun} equally. How much does each friend pay?', 6)


@pytest.mark.parametrize('tense', [('had', 'bought'), ('has', 'buys')])
def test_itemized_quotes_do_not_intercept_ordinary_purchases(reg, tense):
    have, buy = tense
    result = solve(f'Mira {have} $30. She {buy} 2 books that cost $4 each. '
                   'How much money does Mira have left?', reg)
    assert result.answer.value == 22


def test_unallocated_itemized_quote_cannot_be_ignored(reg):
    q = ('Mira has $30. The following: 2 books that cost $4 each. '
         'How much money does Mira have left?')
    assert solve(q, reg).answer.kind == 'decline'


@pytest.mark.parametrize('spec', ['blueprint', 'formula', 'method', 'prescription', 'procedure', 'recipe', 'plan'])
@pytest.mark.parametrize('ratio', ['requires 3 pages for every 2 books', 'uses 3 pages per 2 books'])
def test_generic_specification_scales_counted_inputs(reg, spec, ratio):
    check(reg, f'A {spec} {ratio}. Mira uses this {spec} to make 8 books. '
          'How many pages does Mira need?', 12)


@pytest.mark.parametrize('spec', ['formula', 'method', 'procedure', 'blueprint'])
def test_generic_specification_scales_measured_inputs(reg, spec):
    check(reg, f'A {spec} requires 3 kilograms of clay for every 2 jars. '
          f'Mira uses this {spec} to make 8 jars. How many grams of clay does Mira need?', 12000)


@pytest.mark.parametrize('edit', [
    lambda q: q.replace('this blueprint', 'this method'),
    lambda q: q.replace('8 books', '8 houses'),
    lambda q: q.replace('does Mira need', 'does Nora need'),
    lambda q: q.replace('many pages', 'many books'),
    lambda q: q.replace('every 2', 'every 0'),
    lambda q: q.replace('for every 2', 'for 2'),
    lambda q: q.replace('this blueprint', 'a different blueprint'),
    lambda q: q.replace('this blueprint', 'a blueprint'),
    lambda q: q.replace('8 books.', '8 books with 2 extra pages.'),
])
def test_specification_requires_matching_explicit_application(reg, edit):
    q = ('A blueprint requires 3 pages for every 2 books. '
         'Mira uses this blueprint to make 8 books. How many pages does Mira need?')
    assert solve(edit(q), reg).answer.kind == 'decline'


def test_specification_noun_alone_does_not_assert_a_ratio(reg):
    assert solve('Mira uses a procedure to make 8 books. How many pages does Mira need?', reg).answer.kind == 'decline'


def test_specification_application_can_follow_a_method(reg):
    check(reg, 'A method uses 3 pages per 2 books. Nora follows this method to make 8 books. '
          'How many pages does Nora need?', 12)


def test_specification_measured_output_preserves_material_and_unit(reg):
    check(reg, 'A formula requires 3 grams of salt for every 2 liters of water. '
          'Nora uses the formula to make 8 liters of water. '
          'How many grams of salt does Nora need?', 12)


def test_specification_counted_input_for_measured_output(reg):
    check(reg, 'A procedure requires 3 bottles per 2 liters of water. '
          'Nora follows that procedure to make 8 liters of water. '
          'How many bottles does Nora need?', 12)


@pytest.mark.parametrize('member', ['apples', 'books', 'workers'])
@pytest.mark.parametrize('boundary', ['C', '80'])
def test_threshold_partition_is_independent_of_school(reg, member, boundary):
    check(reg, f'Nora has 48 {member} in Batch 4. 25% of her Batch 4 {member} received a rating below {boundary}. '
          f'How many of her {member} received a rating of {boundary} and above?', 36)


@pytest.mark.parametrize('edit', [
    lambda q: q.replace('rating of 80', 'rating of 85'),
    lambda q: q.replace('rating of 80 and above', 'rating above 80'),
    lambda q: q.replace('48 apples in Batch 4', '48 apples in Batch 5'),
    lambda q: q.replace('her Batch 4 apples', 'her Batch 4 books'),
    lambda q: q.replace('rating of 80', 'final grade of 80'),
    lambda q: q.replace('25%', '30%'),
])
def test_generic_threshold_partition_boundaries(reg, edit):
    q = ('Nora has 48 apples in Batch 4. 25% of her Batch 4 apples received a rating below 80. '
         'How many of her apples received a rating of 80 and above?')
    assert solve(edit(q), reg).answer.kind == 'decline'


def test_numeric_threshold_upper_complement(reg):
    check(reg, 'Nora has 40 books in Batch 2. Half of her Batch 2 books received a rating above 75. '
          'How many of her books received a rating of 75 and below?', 20)


def test_reported_numeric_partition_with_conditional_population(reg):
    check(reg, 'Nora found out that 25% of her Batch 4 apples received a rating below 80. '
          'How many of her apples received a rating of 80 and above if she has 48 apples in Batch 4?', 36)


@pytest.mark.parametrize('activity,site', [('worked', 'office'), ('arrive', 'school')])
def test_non_dining_activity_uses_same_itemized_account_rule(reg, activity, site):
    result = check(reg, f'Four friends {activity} at the {site} and buy the following: '
                   '4 books that cost $2 each; and 2 pencils that cost $4 each. '
                   'They share the cost equally. How much does each friend pay?', 4)
    assert any(f.provenance.source == 'arithmetic/activity-itemized-account-population'
               for f in result.facts())


@pytest.mark.parametrize('participant', ['people', 'machines'])
def test_non_food_population_demand_uses_shared_specification_rules(reg, participant):
    q = ('Mira is making clay for a project. An 8-kilogram box of clay requires 1 kilogram of water. '
         'She uses the same ratio for the project. '
         f'The project has 12 {participant} and each of them needs a 6-kilogram box of clay. '
         'How many kilograms of water does Mira need?')
    check(reg, q, 9)


def test_non_food_observed_ratio_uses_same_reference_rule(reg):
    q = ('Mira is making clay for a project. '
         'She knows a machine produces an 8-kilogram box of clay and uses 1 kilogram of water. '
         'She uses the same ratio for the project. '
         'The project has 12 people and each of them needs a 6-kilogram box of clay. '
         'How many kilograms of water does Mira need?')
    result = check(reg, q, 9)
    assert any(f.provenance.source == 'arithmetic/observed-input-output-ratio'
               for f in result.facts())


@pytest.mark.parametrize('record', ['bill', 'invoice', 'statement', 'check', 'tab', 'account'])
@pytest.mark.parametrize('division', ['split', 'share', 'divide'])
@pytest.mark.parametrize('separate', [False, True])
def test_charge_records_share_explicit_itemized_costs(reg, record, division, separate):
    text = ('Four friends buy the following: 4 books that cost $2 each; '
            'and 2 pencils that cost $4 each. ')
    if separate:
        text += f'They {division} the {record} equally. How much does each friend pay?'
    else:
        text += f'How much will each of them pay if they {division} the {record} equally?'
    check(reg, text, 4)


@pytest.mark.parametrize('record', ['invoice', 'statement', 'check', 'tab', 'account'])
def test_charge_record_without_charges_does_not_create_balance(reg, record):
    text = (f'Four friends buy 4 books. They split the {record} equally. '
            'How much does each friend pay?')
    assert solve(text, reg).answer.kind == 'decline'


def test_check_retains_verb_reading(reg):
    reading = analyze('They check the books.', reg)
    assert any(unit.sense() == 'verb' and unit.features.get('lemma') == 'check'
               for unit in reading.units)


@pytest.mark.parametrize('rule', [
    'arithmetic/threshold-share-numeric',
    'arithmetic/threshold-share-numeric-unindexed',
    'arithmetic/threshold-share-reported-numeric',
    'arithmetic/indexed-population-count',
])
@pytest.mark.parametrize('seed', [0, 1357])
def test_generated_population_indices_round_trip(rule, seed):
    from rulekit.generation import generate_candidate
    candidate = generate_candidate(load_project(Path('projects/curated')), rule_id=rule, seed=seed)
    assert candidate.target_status in {'matched', 'shadowed'}
    if 'cohort' in candidate.requested_bindings:
        assert any(char.isdigit() for char in candidate.requested_bindings['cohort'])


@pytest.mark.parametrize('owner,pronoun,possessive', [
    ('Mr. Vale', 'he', 'his'), ('Ms. Reed', 'she', 'her'), ('Nora', 'she', 'her'),
])
@pytest.mark.parametrize('cohort,members,assessment,boundary', [
    ('Grade 3', 'students', 'final grade', 'C'),
    ('Batch 2', 'workers', 'rating', '80'),
    ('Batch 4', 'books', 'rating', 'C'),
])
@pytest.mark.parametrize('conditional', [False, True])
def test_named_owner_of_indexed_population_remains_a_discourse_referent(
        reg, owner, pronoun, possessive, cohort, members, assessment, boundary, conditional):
    share = f"25% of {owner}'s {cohort} {members} received a {assessment} below {boundary}. "
    question = f'How many of {possessive} {members} received a {assessment} of {boundary} and above'
    total = f'{pronoun} has 48 {members} in {cohort}'
    text = share + (question + ' if ' + total + '?' if conditional
                    else total.capitalize() + '. ' + question + '?')
    check(reg, text, 36)


@pytest.mark.parametrize('prefix', ['Nora has a book. ', "Nora's Batch 1 workers received a rating below 80. "])
def test_indexed_population_owner_does_not_erase_competing_names(reg, prefix):
    text = (prefix + "25% of Mira's Batch 2 workers received a rating below 80. "
            'How many of her workers received a rating of 80 and above '
            'if she has 48 workers in Batch 2?')
    assert solve(text, reg).answer.kind == 'decline'


@pytest.mark.parametrize('owner,pronoun,possessive', [
    ('Mr. Vale', 'he', 'his'), ('Ms. Reed', 'she', 'her'), ('Nora', 'she', 'her'),
])
@pytest.mark.parametrize('members,assessment,boundary', [
    ('students', 'grade', 'C'), ('workers', 'rating', '80'), ('books', 'rating', 'C'),
])
@pytest.mark.parametrize('conditional', [False, True])
def test_unindexed_population_reuses_ordinary_ownership_count(
        reg, owner, pronoun, possessive, members, assessment, boundary, conditional):
    share = f"25% of {owner}'s {members} received a {assessment} below {boundary}. "
    question = f'How many of {possessive} {members} received a {assessment} of {boundary} and above'
    total = f'{pronoun} has 48 {members}'
    text = share + (question + ' if ' + total + '?' if conditional
                    else total.capitalize() + '. ' + question + '?')
    check(reg, text, 36)


@pytest.mark.parametrize('edit', [
    lambda q: q.replace('she has 48 workers', 'Mira has 48 workers'),
    lambda q: q.replace('she has 48 workers', 'she has 48 books'),
    lambda q: q.replace('she has 48 workers', 'she has 48 workers in Batch 2'),
    lambda q: q.replace("Nora's workers", "Nora's Batch 2 workers"),
    lambda q: q.replace('rating of 80', 'rating of 85'),
    lambda q: q.replace('rating of 80 and above', 'rating above 80'),
    lambda q: q.replace('she has 48 workers', 'she has 48 skilled workers'),
    lambda q: 'Mira has a book. ' + q,
    lambda q: q.replace('she has 48 workers', 'she has 48 workers and 12 books'),
    lambda q: q.replace('25%', '30%'),
])
def test_unindexed_population_preserves_owner_scope_and_boundary(reg, edit):
    text = ("25% of Nora's workers received a rating below 80. "
            'How many of her workers received a rating of 80 and above if she has 48 workers?')
    assert solve(edit(text), reg).answer.kind == 'decline'


def test_unindexed_population_strict_count_and_upper_complement(reg):
    text = "Half of Nora's books received a rating above 75. She has 40 books. "
    check(reg, text + 'How many of her books received a rating above 75?', 20)
    check(reg, text + 'How many of her books received a rating of 75 and below?', 20)


@pytest.mark.parametrize('reference', ['that amount', 'this amount', 'the amount', 'that number', 'that', 'this'])
@pytest.mark.parametrize('active', [False, True])
@pytest.mark.parametrize('share,relative,expected', [('half', 'half', 24), ('25%', '1/3', 16)])
def test_joint_share_amount_references(reg, reference, active, share, relative, expected):
    text = earnings(96, share, relative)
    if active:
        text = text.replace(f'However, {share} of the $96 was earned by Mira.',
                            f'Mira earned {share} of {reference}.')
    else:
        text = text.replace('the $96', reference)
    check(reg, text, expected)


@pytest.mark.parametrize('edit', [
    lambda q: q.replace('that amount', 'an amount'),
    lambda q: q.replace('that amount', 'that price'),
    lambda q: q.replace('that amount', 'that amount of money from Tess'),
    lambda q: q.replace('by Mira', 'by Eva'),
    lambda q: q.replace('However,', 'Tess earned $12. However,'),
    lambda q: q.replace('However,', 'Mira and Tess earned $40. However,'),
    lambda q: q.replace('However,', 'Tess earned half of the $96. However,'),
    lambda q: q.replace('from washing cars all week', 'from washing 5 cars all week'),
    lambda q: q.replace('half of that amount', '125% of that amount'),
    lambda q: q.replace(earnings().split('However,')[0], ''),
])
def test_joint_share_reference_scope_boundaries(reg, edit):
    text = earnings().replace('the $96', 'that amount')
    assert solve(edit(text), reg).answer.kind == 'decline'


@pytest.mark.parametrize('reference', ['that', 'this'])
@pytest.mark.parametrize('active', [False, True])
@pytest.mark.parametrize('edit', [
    lambda q: q.replace('However,', 'Tess earned $12. However,'),
    lambda q: q.replace('However,', 'Mira and Tess earned $40. However,'),
    lambda q: q.replace('However,', 'Tess earned half of the $96. However,'),
    lambda q: q.replace(earnings().split('However,')[0], ''),
])
def test_joint_share_bare_reference_ambiguity(reg, reference, active, edit):
    text = edit(earnings()).replace('the $96', reference)
    if active:
        text = text.replace(f'However, half of {reference} was earned by Mira.',
                            f'Mira earned half of {reference}.')
    assert solve(text, reg).answer.kind == 'decline'


@pytest.mark.parametrize('reference', ['the', 'a', 'that price', 'that amount of money from Tess'])
@pytest.mark.parametrize('active', [False, True])
def test_joint_share_bare_reference_requires_complete_demonstrative(reg, reference, active):
    text = earnings().replace('the $96', reference)
    if active:
        text = text.replace(f'However, half of {reference} was earned by Mira.',
                            f'Mira earned half of {reference}.')
    assert solve(text, reg).answer.kind == 'decline'


@pytest.mark.parametrize('measure', ['portion', 'serving'])
@pytest.mark.parametrize('price_basis,expected', [('', 4), (' each', 4), (' in total', 3)])
def test_itemized_serving_measures(reg, measure, price_basis, expected):
    text = bill().replace('3 cups of coffee that cost $2',
                          f'3 {measure}s of coffee that cost $2{price_basis}')
    check(reg, text, expected)


@pytest.mark.parametrize('measure', ['portion', 'serving'])
def test_itemized_single_serving_measure(reg, measure):
    text = bill().replace('3 cups of coffee that cost $2',
                          f'1 {measure} of coffee that costs $2')
    check(reg, text, 3)


@pytest.mark.parametrize('measure', ['portion', 'serving'])
@pytest.mark.parametrize('count', ['0.5', '-2'])
def test_itemized_serving_count_boundaries(reg, measure, count):
    text = bill().replace('3 cups of coffee', f'{count} {measure}s of coffee')
    assert solve(text, reg).answer.kind == 'decline'
