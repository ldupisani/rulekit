"""Invented analogues for compositional costs, durations and comparisons."""
import pytest
from rulekit.data.project import load_project
from rulekit.kernel.engine import solve


@pytest.fixture(scope='module')
def reg():
    return load_project('projects/curated').registry


def check(reg, text, value):
    result = solve(text, reg)
    assert result.answer.value == pytest.approx(value), result.answer
    assert not result.deficiencies()


@pytest.mark.parametrize('verb,item,topic', [
    ('memorized', 'digits', ' of pi'), ('memorised', 'words', ''),
    ('collected', 'shells', ''), ('bought', 'books', ''),
])
@pytest.mark.parametrize('difference_tail', ['repeated', 'auxiliary', 'elided'])
@pytest.mark.parametrize('multiple_tail', ['repeated', 'auxiliary', 'elided'])
@pytest.mark.parametrize('anchor_qualified', [False, True])
@pytest.mark.parametrize('conditional', [False, True])
def test_backward_comparison_chain(reg, verb, item, topic, difference_tail, multiple_tail, anchor_qualified, conditional):
    endings = {'repeated': f' {verb}', 'auxiliary': ' did', 'elided': ''}
    bare = {'memorized':'memorize', 'memorised':'memorise', 'collected':'collect', 'bought':'buy'}[verb]
    intro, anchor_topic = ('If ' if conditional else ''), (topic if anchor_qualified else '')
    punctuation = ', how' if conditional else '. How'
    check(reg, f'Nora {verb} 5 more {item}{topic} than Ezra{endings[difference_tail]}. '
          f'Lena {verb} three times as many {item}{topic} as Ezra{endings[multiple_tail]}. '
          f'{intro}Lena {verb} 18 {item}{anchor_topic}{punctuation} many {item} did Nora {bare}?', 11)


@pytest.mark.parametrize('verb,bare,comparison,expected', [
    ('bought', 'buy', '5 more', 17),
    ('collected', 'collect', 'twice as many', 24),
])
@pytest.mark.parametrize('conditional', [False, True])
def test_content_comparison_inherits_omitted_predicate(reg, verb, bare, comparison, expected, conditional):
    join = 'as' if comparison == 'twice as many' else 'than'
    anchor = (f'If Ezra {verb} 12 pictures, how many pictures did Nora {bare}?' if conditional else
              f'Ezra {verb} 12 pictures of town. How many pictures did Nora {bare}?')
    check(reg, f'Nora {verb} {comparison} pictures of town {join} Ezra. '
          + anchor, expected)


def test_content_comparison_can_decrease_with_omitted_predicate(reg):
    check(reg, 'Nora memorized 5 fewer digits of pi than Ezra. '
          'Ezra memorized 12 digits of pi. How many digits did Nora memorize?', 7)


@pytest.mark.parametrize('text', [
    'Nora memorized 5 more digits of pi than Ezra collected. Ezra memorized 12 digits of pi. How many digits did Nora memorize?',
    'Nora memorized twice as many digits of pi as Ezra collected. Ezra memorized 12 digits of pi. How many digits did Nora memorize?',
    'Nora memorized 5 more digits of pi than Ezra. Ezra collected 12 digits of pi. How many digits did Nora memorize?',
    'Nora memorized 5 more digits of pi than Ezra. Ezra memorized 12 words. How many digits did Nora memorize?',
    'Nora memorized 5 more digits of pi than Nora. Nora memorized 12 digits of pi. How many digits did Nora memorize?',
    'Nora memorized 5 more digits of pi than Ezra. Lena memorized 12 digits of pi. How many digits did Nora memorize?',
    'Nora bought 5 more pictures of town than Ezra. Ezra bought 12 pictures of the park. How many pictures did Nora buy?',
])
def test_omitted_comparison_predicate_preserves_scope(reg, text):
    assert not solve(text, reg).answer.committed


@pytest.mark.parametrize('item', ['shells', 'books', 'apples'])
@pytest.mark.parametrize('prefix', ['', 'got a late start and only ', 'got an early start and only '])
def test_fraction_of_elided_event(reg, item, prefix):
    check(reg, f'Nora collected twice as many {item} as Ezra did. '
          f'Ezra {prefix}collected a quarter of what Lena did. '
          f'If Lena collected 48 {item} how many did Nora collect?', 24)


def test_excursion_background(reg):
    check(reg, 'On a school trip to the park, Nora and her friends collected shells. '
          'Nora collected twice as many shells as Ezra did. '
          'Ezra collected half of what Lena collected. Lena collected 18 shells. '
          'How many shells did Nora collect?', 18)


@pytest.mark.parametrize('first,second,verb', [('piano','guitar','practices'), ('book','poem','studies')])
@pytest.mark.parametrize('cadence', ['a', 'per', 'each', 'every'])
def test_schedule_composition(reg, first, second, verb, cadence):
    progressive = 'practicing' if verb == 'practices' else 'studying'
    check(reg, f'Nora {verb} the {first} for 15 minutes {cadence} day and the {second} for twice as long. '
          f'If she {verb} 4 days {cadence} week, how many minutes does she spend {progressive} in 3 weeks?', 540)


@pytest.mark.parametrize('subject,measure,verb,bare', [('file','megabytes','downloads','download'), ('tank','liters','fills','fill')])
@pytest.mark.parametrize('compact', [False, True])
@pytest.mark.parametrize('rate_frame', ['', 'the rate of '])
@pytest.mark.parametrize('comma', ['', ','])
def test_successive_process_rates(reg, subject, measure, verb, bare, compact, rate_frame, comma):
    opening = (f'A {subject} of 120 {measure}{comma} {verb} at ' if compact else
               f'The {subject}, 120 {measure} in size, {verb} at ')
    opening += rate_frame
    check(reg, opening + f'6 {measure} per second for its first 30 {measure}, and then 15 {measure} per second thereafter. '
          f'How many seconds does it take to {bare} entirely?', 11)


@pytest.mark.parametrize('frame,first,remainder', [
    ('the rate of', '130 megabytes', '15 megabytes'),
    ('the rate of', '30 megabytes', '15 liters'),
])
def test_successive_process_rate_frame_preserves_boundaries(reg, frame, first, remainder):
    result = solve(
        f'A file of 120 megabytes, downloads at {frame} 6 megabytes per second '
        f'for its first {first}, and then {remainder} per second thereafter. '
        'How many seconds does it take to download entirely?', reg)
    assert not result.answer.committed


@pytest.mark.parametrize('item,collection,goods', [('box','goods','books'), ('piñata','treats','candy')])
def test_fixed_and_packaged_purchases(reg, item, collection, goods):
    check(reg, f'Nora bought a {item} for $8. Nora bought 2 bags of {goods} for $3 per bag, '
          f'and 4 bags of {goods} for $5 per bag. How much did the {item} and the {collection} cost altogether?', 34)


def test_apostrophized_product_is_not_an_owner(reg):
    check(reg, "Nora bought a piñata for $8. Nora bought 2 bags of Reese's for $3 per bag, "
          'and 4 bags of Skittles for $5 per bag. How much did the piñata and the treats cost altogether?', 34)


@pytest.mark.parametrize('text', [
    'Nora collected twice as many shells as Ezra sold. Ezra collected 12 shells. How many shells did Nora collect?',
    'Nora memorized 5 more digits of pi than Ezra memorized. Ezra memorized 12 words. How many digits did Nora memorize?',
    'Nora collected half of what Ezra did. Ezra collected 12 shells and 8 books. How many did Nora collect?',
    'Nora bought a box for $8. Nora bought 2 bags of books for $3 per bottle. How much did the box and the goods cost altogether?',
    'Nora bought a box for $8. Ezra bought 2 bags of books for $3 per bag. How much did the box and the goods cost altogether?',
    'Nora bought a piñata for $8. Nora bought 2 bags of books for $3 per bag. How much did the piñata and the treats cost altogether?',
    'The file, 20 megabytes in size, downloads at the rate of 5 megabytes per second for its first 30 megabytes, and then 10 megabytes per second thereafter. How many seconds does it take to download entirely?',
    'The file, 60 megabytes in size, downloads at the rate of 0 megabytes per second for its first 30 megabytes, and then 10 megabytes per second thereafter. How many seconds does it take to download entirely?',
    'The file, 60 megabytes in size, downloads at the rate of 5 megabytes per minute for its first 30 megabytes, and then 10 megabytes per second thereafter. How many seconds does it take to download entirely?',
    'Nora practices the piano for 15 minutes a day and the violin for twice as long. She practices 4 days a week. How many minutes does she spend practicing in 3 months?',
    'Nora practices the piano for 15 minutes a day and the violin for twice as long. Ezra practices 4 days a week. How many minutes does Nora spend practicing in 3 weeks?',
])
def test_missing_or_incompatible_scope_declines(reg, text):
    assert not solve(text, reg).answer.committed


def test_direct_schedule_question(reg):
    check(reg, 'Nora practices the piano for 10 minutes a day and the guitar for three times as long. '
          'She practices 5 days a week. How many minutes does she practice in 2 weeks?', 400)


@pytest.mark.parametrize('intro', ["It's", 'It is'])
def test_occasion_and_filling_are_nonquantitative(reg, intro):
    check(reg, f"{intro} Nora's birthday party. Her parents bought a red piñata for $8 and filled it with all of her favorite treats. "
          "They bought 2 bags of Reese’s for $3 per bag, and 4 bags of candy for $5 per bag. "
          'How much did the red piñata and the treats cost altogether?', 34)


@pytest.mark.parametrize('text', [
    'Nora bought a box for $8. They bought 2 bags of books for $3 per bag. How much did the box and the goods cost altogether?',
    'Nora bought a box for $8. Nora bought 2 bags of books for $3 per bag and pencils. How much did the box and the goods cost altogether?',
    'The file, 60 liters in size, downloads at the rate of 5 liters per second for its first 30 liters, and then 10 liters per second thereafter. How many seconds does it take to download entirely?',
    'The tank, 60 liters in size, fills at the rate of 5 liters per second for its first 30 liters, and then 10 liters per second thereafter. How many seconds does it take to download entirely?',
    'Nora practices the piano for 15 minutes a day and the violin for twice as long. She practices 4 days a week. She has 8 books. How many minutes does she practice in 3 weeks?',
])
def test_complete_source_and_reference_boundaries(reg, text):
    assert not solve(text, reg).answer.committed


def test_fixed_purchase_keeps_inventory_and_unit_price(reg):
    check(reg, 'Nora bought a hat for $8. How many hats did Nora buy?', 1)
    check(reg, 'Nora bought a hat for $8. How much did the hat cost?', 8)
    check(reg, 'Nora has $30. Nora buys a book for $8 and a hat for $3. How much money does Nora have left?', 19)


def test_inanimate_activity_subject_is_not_a_schedule(reg):
    text = ('The file practices the piano for 10 minutes a day and the guitar for twice as long. '
            'The file practices 4 days a week. How many minutes does the file practice in 3 weeks?')
    assert not solve(text, reg).answer.committed


@pytest.mark.parametrize('text, expected', [
    ('Nora practices 5 days a week. How many days does Nora practice in 3 weeks?', 15),
    ('Nora practices 45 minutes a day. She practices 5 days a week. How many minutes does Nora practice in 2 weeks?', 450),
    ('Nora studies 30 minutes a day. She studies 4 days a week. How many minutes does Nora study in 3 weeks?', 360),
    ('Nora practices the piano for 10 minutes a day and the guitar for twice as long. How many minutes does Nora practice in 4 days?', 120),
])
def test_simplified_explicit_schedule_rates(reg, text, expected):
    check(reg, text, expected)


@pytest.mark.parametrize('text', [
    'Nora practices 45 minutes a day. Ezra practices 5 days a week. How many minutes does Nora practice in 2 weeks?',
    'Nora practices 45 minutes a day. She studies 5 days a week. How many minutes does Nora practice in 2 weeks?',
    'Nora practices 45 minutes a day. She practices 8 days a week. How many minutes does Nora practice in 2 weeks?',
    'Nora practices 45 minutes a day. She practices 5 days a week. How many minutes does Nora practice in 2 months?',
])
def test_schedule_chain_boundaries(reg, text):
    assert not solve(text, reg).answer.committed


@pytest.mark.parametrize('opening', [30, 100])
def test_unconsumed_purchase_cannot_disappear_from_cash_balance(reg, opening):
    text = f'Nora has ${opening}. Nora bought a hat for $30. How much money does Nora have?'
    assert not solve(text, reg).answer.committed


def test_explicit_cash_events_keep_their_existing_accounting(reg):
    check(reg, 'Nora has $20. She spends $6. How much money does Nora have left?', 14)


def test_filling_context_requires_a_container(reg):
    text = ('Nora bought a pencil for $8 and filled it with all of her favorite treats. '
            'Nora bought 2 bags of candy for $3 per bag. '
            'How much did the pencil and the treats cost altogether?')
    assert not solve(text, reg).answer.committed
