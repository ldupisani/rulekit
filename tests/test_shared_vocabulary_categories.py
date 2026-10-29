"""Shared vocabulary supports declared roles without manufacturing relationships."""

from pathlib import Path

import pytest

from rulekit.data.project import load_project
from rulekit.kernel.engine import solve
from rulekit.kernel.model import RegionEvidence


@pytest.fixture(scope="module")
def registry():
    return load_project(Path("projects/curated")).registry


@pytest.mark.parametrize("word,categories", [
    ("doctor", ["person", "animate", "quantity_event_participant"]),
    ("scientist", ["person", "animate", "situated_role"]),
    ("crab", ["animal", "edible_quantity_object"]),
    ("blueberry", ["fruit", "edible_quantity_object"]),
    ("parrot", ["bird", "animal"]),
    ("pufferfish", ["fish", "animal"]),
    ("grasshoppers", ["insect", "animal"]),
    ("lilac", ["flower", "plantable_quantity_object"]),
    ("jacket", ["clothes", "clothing", "ownable_quantity_object"]),
    ("backpack", ["quantity_container", "quantity_interior_location", "ownable_quantity_object"]),
    ("brush", ["instrument_noun", "ownable_quantity_object", "droppable_quantity_object"]),
    ("library", ["building", "quantity_interior_location", "quantity_site_location"]),
    ("laptop", ["computing_device", "quantity_holder", "ownable_quantity_object"]),
    ("milk", ["mass_quantity_noun", "measured_content_substance", "volume_partitive_substance"]),
    ("gallon", ["volume_measure", "measure_unit", "non_quantity_holder"]),
    ("t-shirt", ["clothes", "clothing", "ownable_quantity_object"]),
    ("turtle", ["animal", "quadruped"]),
    ("thermos", ["quantity_container", "measurement_container", "quantity_interior_location"]),
    ("vase", ["quantity_container", "ownable_quantity_object"]),
    ("tailor", ["person", "situated_role", "animate"]),
    ("waitress", ["person", "situated_role", "animate"]),
    ("tooth", ["body_part", "linear_dimension_holder"]),
    ("whisker", ["body_part", "linear_dimension_holder"]),
    ("van", ["vehicle", "four_wheeled_vehicle", "journey_vehicle"]),
    ("train", ["vehicle", "journey_vehicle", "means_noun"]),
    ("textbook", ["information_quantity_object", "publication_product", "topical_quantity_host"]),
    ("yarn", ["material_resource", "mass_quantity_noun", "weighable_partitive_substance"]),
    ("yard", ["length_unit", "length_measure", "measure_unit", "non_quantity_holder"]),
    ("watt", ["measure_unit", "non_quantity_holder"]),
])
def test_words_have_multiple_independently_justified_roles(registry, word, categories):
    for category in categories:
        assert registry.word_in_category(word, category), (word, category)


@pytest.mark.parametrize("word,plural", [
    ("lilac", "lilacs"), ("parrot", "parrots"), ("chef", "chefs"),
    ("fisherman", "fishermen"), ("housewife", "housewives"),
    ("scarf", "scarves"), ("scarf", "scarfs"), ("backpack", "backpacks"),
    ("smartphone", "smartphones"), ("salesman", "salesmen"),
    ("task", "tasks"), ("tee", "tees"), ("tooth", "teeth"),
    ("thermos", "thermoses"), ("tribe", "tribes"), ("triple-flip", "triple-flips"),
    ("umbrella", "umbrellas"), ("unit", "units"), ("watermelon", "watermelons"),
    ("whisker", "whiskers"), ("wick", "wicks"), ("watch", "watches"),
])
def test_count_morphology_is_explicit(registry, word, plural):
    assert registry.plural_to_singular[plural] == word


@pytest.mark.parametrize("items,collection,subtype", [
    ("6 roses, 9 lilacs, 15 lilies, 8 blueberries, 4 doctors, and 11 crabs", "flowers", "roses"),
    ("6 robins, 9 crows, 15 pigeons, 8 beetles, and 4 bakers", "birds", "robins"),
    ("6 dolphins, 9 crabs, 15 koalas, 8 lilies, and 4 oranges", "animals", "dolphins"),
    ("6 jackets, 9 skirts, 15 sweaters, 8 roses, and 4 doctors", "clothes", "jackets"),
    ("30 people, 6 scientists, 8 lilies, and 11 oranges", "people", "scientists"),
    ("6 roses, 9 tulips, 15 daisies, 8 tailors, and 4 warehouses", "flowers", "roses"),
    ("6 turtles, 9 tadpoles, 15 worms, 8 t-shirts, and 4 vans", "animals", "turtles"),
    ("6 t-shirts, 9 shirts, 15 dresses, 8 turtles, and 4 vans", "clothes", "t-shirts"),
    ("6 vets, 9 tailors, 15 waitresses, 8 roses, and 4 vans", "people", "vets"),
])
def test_category_inventories_use_shared_vocabulary(registry, items, collection, subtype):
    result = solve(f"There are {items}. What percent of the {collection} are not {subtype}?", registry)
    assert result.value == 80, result.answer
    assert result.deficiencies() == []


def test_an_object_role_does_not_prove_a_botanical_type(registry):
    result = solve("There are 6 roses, 9 tulips, 15 daisies, 8 backpacks, and 4 apples. "
                   "What percent of the flowers are not roses?", registry)
    assert not result.answer.committed


@pytest.mark.parametrize("item", ["notebooks", "erasers", "bracelets", "jackets", "backpacks",
                                 "t-shirts", "thermoses", "toothpicks", "vases", "woodblocks", "watches"])
def test_ordinary_purchase_events_reuse_quantity_arithmetic(registry, item):
    result = solve(f"Fia has 6 {item}. Fia bought 4 {item}. How many {item} does Fia have?", registry)
    assert result.value == 10, result.answer
    assert result.deficiencies() == []


@pytest.mark.parametrize("word", ["player", "reader", "pupil", "boxer", "cardinal", "collector"])
def test_ambiguous_heads_do_not_gain_personal_reference_eligibility(registry, word):
    assert not registry.word_in_category(word, "animate")
    assert not registry.category_terms_disjoint("flower", word)


@pytest.mark.parametrize("action", ["needs", "repairs", "borrows"])
def test_recognizing_a_verb_does_not_invent_possession(registry, action):
    result = solve(f"Fia {action} 5 laptops. How many laptops does Fia have?", registry)
    assert not result.answer.committed


@pytest.mark.parametrize("action", ["shares", "splits"])
def test_sharing_verbs_keep_their_base_verb_accounting_boundary(registry, action):
    result = solve(f"A notebook costs $7. Fia {action} the cost with Ben. "
                   "How much did Fia pay for 5 notebooks?", registry)
    assert not result.answer.committed
    assert "cost-splitting" in result.answer.reason


@pytest.mark.parametrize("name", ["Mark", "Robin", "Jay", "Lily", "Daisy", "Basil", "Baker", "Cash", "Hunter",
                                   "Lake", "Mason", "Myrtle", "Olive", "Penny", "River", "Scout", "Star", "Eve", "Herb", "Caesar"])
def test_declared_name_homographs_keep_sentence_initial_personal_references(registry, name):
    result = solve(f"{name} has 8 erasers. His brother has 5 erasers. He bought 3 erasers. "
                   f"How many erasers does {name} have?", registry)
    assert result.value == 11, result.answer
    assert result.deficiencies() == []


@pytest.mark.parametrize("noun", ["mark", "robin", "jay", "lily", "daisy", "basil", "cash",
                                   "lake", "myrtle", "olive", "penny", "river", "scout", "star"])
def test_name_homographs_do_not_make_determined_nouns_people(registry, noun):
    result = solve(f"The {noun} has 8 erasers. He bought 3 erasers. "
                   "How many erasers does he have?", registry)
    assert not result.answer.committed


@pytest.mark.parametrize("first,first_material,second,second_material", [
    ("kilograms", "clay", "liters", "foam"),
    ("liters", "foam", "kilograms", "clay"),
    ("kilograms", "clay", "meters", "wire"),
])
def test_coordinated_purchases_are_not_elliptical_resource_removals(
    registry, first, first_material, second, second_material,
):
    singular = {"kilograms": "kilogram", "liters": "liter", "meters": "meter"}
    text = (f"Fia bought 3 {first} of {first_material} and 2 {second} of {second_material}. "
            f"A {singular[first]} of {first_material} costs $4 and "
            f"a {singular[second]} of {second_material} costs $5. "
            "How much will Fia pay in all?")
    result = solve(text, registry)
    assert result.value == 22, result.answer
    assert result.store.by_kind(RegionEvidence) == []


@pytest.mark.parametrize("sentence,quantity,unit,material", [
    ("Fia uses 3 kilograms and 4 kilograms.", "mass", "kilograms", "clay"),
    ("Fia uses 3 liters and 4 liters.", "volume", "liters", "foam"),
    ("Fia uses 3 meters and 4 meters.", "length", "meters", "wire"),
    ("Fia cuts off 3 meters and 4 meters.", "length", "meters", "wire"),
])
def test_measured_removal_continuations_keep_their_governing_action(
    registry, sentence, quantity, unit, material,
):
    text = f"Fia has 20 {unit} of {material}. {sentence} What {quantity} of {material} remains?"
    result = solve(text, registry)
    assert result.value == 13, result.answer


def test_continuation_does_not_search_past_an_intervening_purchase(registry):
    result = solve("Fia uses 3 liters of foam and buys 2 notebooks and 4 liters of milk.", registry)
    removals = [r for r in result.store.by_kind(RegionEvidence) if r.stage == "removal"]
    assert len(removals) == 1
    assert removals[0].value == 3


@pytest.mark.parametrize("noun", ["baker", "hunter", "mason"])
def test_personal_noun_homographs_keep_their_common_noun_reading(registry, noun):
    from rulekit.kernel.engine import analyze
    reading = analyze(f"The {noun} has 8 erasers.", registry)
    unit = next(u for u in reading.units if u.features.get("lemma") == noun)
    assert unit.sense() == "noun"


def test_volume_classification_does_not_supply_an_unstated_conversion(registry):
    from rulekit.kernel.dimensions import substance_conversion_factor
    assert registry.word_in_category("gallon", "volume_measure")
    assert substance_conversion_factor(registry, "water", "kilogram", "liter") == 1
    assert substance_conversion_factor(registry, "water", "kilogram", "gallon") is None
    assert substance_conversion_factor(registry, "foam", "kilogram", "liter") is None


@pytest.mark.parametrize('marker,item', [('After', 'notebooks'), ('When', 'roses')])
def test_shared_temporal_markers_still_route_an_ordinary_quantity_clause(registry, marker, item):
    result = solve(f'Fia has 6 {item}. {marker} Fia finds 4 {item}, how many {item} does Fia have?', registry)
    assert result.value == 10, result.answer


@pytest.mark.parametrize('verb', ['know', 'knows', 'knew', 'cough', 'coughed'])
def test_an_animate_subject_constraint_does_not_grant_a_quantity_predicate(registry, verb):
    assert registry.word_in_category(verb, 'animate_subject_verb')
    assert not registry.word_in_category(verb, 'quantity_ask_verb')
    assert not registry.word_in_category(verb, 'quantity_comparison_verb')


@pytest.mark.parametrize('verb', ['own', 'owns', 'enroll', 'enrolled', 'teach', 'teaches', 'take', 'takes', 'took'])
def test_existing_quantitative_predicates_keep_their_independent_licence(registry, verb):
    assert registry.word_in_category(verb, 'quantity_ask_verb')
    assert registry.word_in_category(verb, 'animate_subject_verb')


def test_measured_additions_are_not_newly_acquired_opening_stock(registry):
    from rulekit.kernel.model import MeasuredContentChange
    text = ('Fia placed the jug on the scale. '
            'Fia put enough sand into the jug to bring the weight to 5 pounds. '
            'Fia added 2 kilograms of water. How many liters of water are in the jug?')
    result = solve(text, registry)
    assert result.value == pytest.approx(2), result.answer
    assert len(result.store.by_kind(MeasuredContentChange)) == 2
    assert result.store.by_kind(RegionEvidence) == []
    unavailable = solve(text.replace('liters of water', 'gallons of water'), registry)
    assert not unavailable.answer.committed
    assert "no known 'water' conversion" in unavailable.answer.reason


@pytest.mark.parametrize('action', ['bought', 'received', 'collected'])
@pytest.mark.parametrize('unit,material', [('kilograms', 'clay'), ('meters', 'wire')])
def test_measured_acquisitions_still_establish_opening_stock(registry, action, unit, material):
    result = solve(f'Fia {action} 10 {unit} of {material}.', registry)
    rows = result.store.by_kind(RegionEvidence)
    assert len(rows) == 1
    assert (rows[0].stage, rows[0].material, rows[0].value) == ('opening', material, 10)


@pytest.mark.parametrize('verb', ['hit', 'hits', 'inspect', 'inspected', 'inspects'])
def test_counted_object_operations_keep_their_quantitative_role(registry, verb):
    assert registry.word_in_category(verb, 'discrete_object_event_verb')
    assert registry.word_in_category(verb, 'quantity_ask_verb')


@pytest.mark.parametrize('word,sense', [
    ('vertically', 'adverb'), ('yet', 'adverb'), ('whatever', 'pronoun'),
    ('unloaded', 'verb'), ('thirty-five', 'value'),
])
def test_corrected_lexical_roles_are_available_without_a_spurious_noun(registry, word, sense):
    assert sense in registry.lexicon[word].senses
    assert 'noun' not in registry.lexicon[word].senses


@pytest.mark.parametrize('word,lemma', [
    ('thinking', 'think'), ('thought', 'think'), ('telling', 'tell'),
    ('thrown', 'throw'), ('ties', 'tie'), ('unloaded', 'unload'),
    ('vacuumed', 'vacuum'), ('withdrew', 'withdraw'), ('wrapping', 'wrap'),
])
def test_verb_morphology_keeps_explicit_canonical_roots(registry, word, lemma):
    assert registry.lexicon[word].verb.lemma == lemma
    assert 'verb' in registry.lexicon[lemma].senses


@pytest.mark.parametrize('word,excluded', [
    ('tick', 'insect'), ('tadpole', 'fish'), ('tee', 'clothes'),
    ('train', 'four_wheeled_vehicle'), ('television', 'information_quantity_object'),
])
def test_primary_classification_does_not_supply_an_unstated_subtype(registry, word, excluded):
    assert not registry.word_in_category(word, excluded)


def test_animal_classification_does_not_supply_missing_anatomy(registry):
    assert registry.attribute_value('turtles', 'legs') == 4
    for word in ('ticks', 'tadpoles'):
        assert registry.attribute_value(word, 'legs') is None
    assert registry.attribute_value('tricycles', 'wheels') == 3
    assert registry.attribute_value('trains', 'wheels') is None


@pytest.mark.parametrize('noun', ['waitress', 'vet', 'wife'])
def test_unambiguous_personal_heads_reuse_existing_coreference(registry, noun):
    result = solve(f'The {noun} has 8 vases. She bought 3 vases. '
                   f'How many vases does the {noun} have?', registry)
    assert result.value == 11, result.answer
    assert result.deficiencies() == []


@pytest.mark.parametrize('noun', ['visitor', 'watcher', 'turtle', 'towel'])
def test_ambiguous_or_nonpersonal_heads_do_not_gain_personal_coreference(registry, noun):
    result = solve(f'The {noun} has 8 vases. He bought 3 vases. '
                   'How many vases does he have?', registry)
    assert not result.answer.committed


@pytest.mark.parametrize('sentence', [
    'Fia watched 5 turtles.', 'Fia visited 5 theaters.', 'Fia unloaded 5 boxes.',
])
def test_recognizing_observation_attendance_or_handling_does_not_assert_ownership(registry, sentence):
    measure = {'watched': 'turtles', 'visited': 'theaters', 'unloaded': 'boxes'}[sentence.split()[1]]
    result = solve(f'{sentence} How many {measure} does Fia have?', registry)
    assert not result.answer.committed


def test_a_negative_conditional_is_not_an_asserted_purchase(registry):
    assert not registry.word_in_category('unless', 'clause_marker')
    result = solve('Fia has 8 tokens. Unless Fia buys 3 tokens, how many tokens does Fia have?', registry)
    assert not result.answer.committed


@pytest.mark.parametrize('initial,fraction,expected', [
    ('thirty-five', 'three-fifths', 21), ('twenty-eight', 'three-quarters', 21),
    ('thirty-six', 'two-thirds', 24), ('thirty-five', 'two-fifths', 14),
])
def test_compound_number_words_and_fractions_share_the_core_number_tables(registry, initial, fraction, expected):
    result = solve(f'Fia has {initial} tokens. Ben has {fraction} as many tokens as Fia. '
                   'How many tokens does Ben have?', registry)
    assert result.value == pytest.approx(expected), result.answer
    assert result.deficiencies() == []


@pytest.mark.parametrize('material', ['yarn', 'tape'])
def test_new_measured_materials_reuse_length_balances_and_yard_conversion(registry, material):
    result = solve(f'Fia has 7 yards of {material}. Fia cuts off 2 feet of {material}. '
                   f'How long is the remaining {material} in feet?', registry)
    assert result.value == pytest.approx(19), result.answer
    assert result.deficiencies() == []


def test_measurement_vocabulary_does_not_imply_a_density(registry):
    from rulekit.kernel.dimensions import substance_conversion_factor
    assert substance_conversion_factor(registry, 'yarn', 'kilogram', 'liter') is None


def test_shared_vocabulary_migration_preserves_quarantine_and_one_owner(registry):
    from ruamel.yaml import YAML
    root = Path(__file__).resolve().parents[1]
    quarantine = YAML(typ='safe').load((root/'packs/difg-mined/quarantine.yaml').read_text())['words']
    assert 'teammates' in quarantine
    assert 'teammates' not in registry.lexicon
    assert 'teammates' not in registry.plural_to_singular
    for filename in ('a-f.yaml', 'g-m.yaml', 'n-s.yaml', 't-z.yaml'):
        assert not (root/'packs/difg-mined/lexicon'/filename).exists()


def test_a_homographic_verb_keeps_its_own_agreement_after_noun_selection(registry):
    from rulekit.kernel.engine import analyze
    reading = analyze('Fia watches 5 turtles.', registry)
    verb = next(unit for unit in reading.units if unit.features.get('fold') == 'watches')
    assert verb.sense() == 'verb'
    assert verb.features['number'] == 'singular'
    nominal = analyze('Fia owns 5 watches.', registry)
    item = next(unit for unit in nominal.units if unit.features.get('lemma') == 'watch')
    assert item.sense() == 'noun'
    assert item.features['number'] == 'plural'
    assert item.features['value'] == 5


@pytest.mark.parametrize('noun,plural', [('t-shirt', 't-shirts'), ('dog-walker', 'dog-walkers')])
def test_declared_hyphenated_plural_forms_keep_their_identity(registry, noun, plural):
    from rulekit.kernel.engine import analyze
    reading = analyze(f'Fia has 5 {plural}.', registry)
    item = next(unit for unit in reading.units if unit.features.get('lemma') == noun)
    assert item.sense() == 'noun'
    assert item.features['number'] == 'plural'
    assert item.features['value'] == 5


def test_fraction_compound_does_not_change_a_counted_currency_noun(registry):
    from rulekit.kernel.engine import analyze
    reading = analyze('Fia has 3 quarters.', registry)
    item = next(unit for unit in reading.units if unit.features.get('lemma') == 'quarter')
    assert item.sense() == 'noun'
    assert item.features['value'] == 3
