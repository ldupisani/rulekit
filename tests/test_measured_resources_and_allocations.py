"""Invented resource balances, recipient roles and quantity-question constructions."""
from pathlib import Path
import pytest
from rulekit.data.project import load_project
from rulekit.kernel.engine import solve

@pytest.fixture(scope="module")
def registry():
    return load_project(Path("projects/curated")).registry

CASES = {
    'metal': (
        'A rectangular sheet of metal measures 12 meters by 8 meters. Two separate rectangles '
        'measuring 3 by 4 meters and 2 by 5 meters are cut out. How much metal remains in square '
        'meters?'
    ),
    'glass': (
        'A pane of glass measures 9 feet by 6 feet. Rectangles measuring 3 by 2 feet and 2 by 2 '
        'feet are removed. What area of glass remains?'
    ),
    'wire': (
        'A spool holds 30 meters of wire. A technician cuts off 8 meters and then another 7 meters. '
        'What total length remains?'
    ),
    'foam': (
        'A rectangular block of foam measures 10 by 6 by 4 centimeters. A block measuring 2 by 3 by '
        '4 centimeters is removed. How many cubic centimeters remain?'
    ),
    'clay': (
        'A workshop has 20 kilograms of clay. It uses 3 kilograms for one model and 4 kilograms for '
        'another. What mass of clay remains?'
    ),
    'machine': (
        'Pat had 8 boxes of bolts with the same number of bolts in each box. Pat kept 16 bolts and '
        'distributed the remaining bolts equally among 4 machines. Each machine received 12 bolts. '
        'How many bolts were originally in each box?'
    ),
    'pump': (
        'A pump transfers 900 liters of water equally into 3 tanks. How much water does each tank '
        'receive?'
    ),
    'server': (
        'A server distributes 360 files equally across 9 computers. How many files does each '
        'computer receive?'
    ),
    'money': (
        'A business has $180. It retains $30 and divides the remainder equally among 3 accounts. '
        'How much money goes into each account?'
    ),
}

EXPECTED = {'metal': 74, 'glass': 44, 'wire': 15, 'foam': 216, 'clay': 13, 'machine': 8, 'pump': 300, 'server': 40, 'money': 50}

def number(text, registry, expected):
    result = solve(text, registry)
    assert result.answer.committed, (result.answer.reason, result.deficiencies())
    assert result.value == pytest.approx(expected)
    assert result.deficiencies() == []
    return result

@pytest.mark.parametrize("case", CASES)
def test_proposed_expansion_examples(registry, case):
    number(CASES[case], registry, EXPECTED[case])

@pytest.mark.parametrize("ask", [
    "How many square meters of metal remain?",
    "How many square meters of metal are left?",
    "What area of metal remains?",
    "What is the remaining area of the metal?",
    "What amount of metal remains in square meters?",
    "What quantity of metal remains in square meters?",
    "How much metal is left in square meters?",
])
def test_equivalent_area_question_constructions(registry, ask):
    text = CASES["metal"].rsplit("How much", 1)[0] + ask
    number(text, registry, 74)

@pytest.mark.parametrize("before,after,value", [
    ("metal", "rubber", 74),
    ("metal", "wood", 74),
    ("square meters?", "square centimeters?", 740000),
])
def test_material_independence_and_squared_unit_conversion(registry, before, after, value):
    number(CASES["metal"].replace(before, after), registry, value)

@pytest.mark.parametrize("ask", [
    "What volume of foam remains?",
    "How many cubic centimeters of foam remain?",
    "How much foam is left in cubic centimeters?",
])
def test_volume_question_constructions(registry, ask):
    number(CASES["foam"].split("How many")[0] + ask, registry, 216)

@pytest.mark.parametrize("noun", ["clay", "sand", "sugar"])
def test_direct_mass_is_a_resource_balance(registry, noun):
    number(CASES["clay"].replace("clay", noun), registry, 13)

@pytest.mark.parametrize("recipient", ["machines", "robots", "schools", "tanks", "accounts"])
def test_inverse_distribution_accepts_recipient_roles(registry, recipient):
    singular = recipient[:-1]
    text = CASES["machine"].replace("machines", recipient).replace("Each machine", "Each " + singular)
    number(text, registry, 8)

@pytest.mark.parametrize("verb", ["distributes", "allocates", "assigns", "routes"])
def test_digital_allocations_share_transfer_arithmetic(registry, verb):
    number(CASES["server"].replace("distributes", verb), registry, 40)

@pytest.mark.parametrize("ask,value", [
    ("How many milliliters of water does each tank receive?", 300000),
    ("How many liters of water does each tank receive?", 300),
])
def test_measured_allocations_keep_output_units(registry, ask, value):
    number(CASES["pump"].split("How much")[0] + ask, registry, value)

@pytest.mark.parametrize("case,before,after", [
    ("metal", "square meters?", "meters?"),
    ("metal", "12 meters", "0 meters"),
    ("metal", "Two separate rectangles", "Three separate rectangles"),
    ("metal", "3 by 4 meters", "30 by 4 meters"),
    ("metal", "2 by 5 meters", "2 by 5 hours"),
    ("foam", "cubic centimeters", "square centimeters"),
    ("foam", "cubic centimeters", "kilograms"),
    ("clay", "4 kilograms", "40 kilograms"),
    ("clay", "What mass", "What volume"),
    ("clay", "It uses", "It needs"),
    ("pump", "transfers", "can transfer"),
    ("pump", "equally ", ""),
    ("pump", "3 tanks", "0 tanks"),
    ("pump", "each tank", "each computer"),
    ("server", "360 files", "361 files"),
    ("machine", "Each machine received", "Each machine needs"),
    ("machine", "Each machine received", "Each machine can hold"),
    ("money", "$30", "$300"),
    ("money", "equally ", ""),
])
def test_ambiguity_and_actuality_boundaries(registry, case, before, after):
    assert not solve(CASES[case].replace(before, after), registry).answer.committed

def test_tank_capacity_does_not_establish_an_actual_allocation(registry):
    text = "A tank holds 900 liters of water. There are 3 tanks. How much water does each tank receive?"
    assert not solve(text, registry).answer.committed

def test_multiple_material_stocks_need_an_explicit_source(registry):
    text = CASES["metal"].replace("Two separate", "A sheet of rubber measures 8 meters by 6 meters. Two separate")
    assert not solve(text, registry).answer.committed

def test_nonpersonal_subject_reference_needs_one_actor(registry):
    text = CASES["clay"].replace("It uses", "A business has 5 kilograms of clay. It uses")
    assert not solve(text, registry).answer.committed

def test_measurement_powers_convert_each_geometric_axis(registry):
    number(CASES["foam"].replace("cubic centimeters remain?", "cubic meters remain?"), registry, 0.000216)

@pytest.mark.parametrize("sentence", [
    "900 liters of water are distributed equally among 3 tanks.",
    "900 liters of water are poured equally into 3 tanks.",
    "A pump pours 900 liters of water equally into 3 tanks.",
    "A pump assigns 900 liters of water equally to 3 tanks.",
])
def test_active_and_passive_material_allocations(registry, sentence):
    number(sentence + " How much water does each tank receive?", registry, 300)


def test_passive_digital_allocation(registry):
    number("360 files are distributed equally across 9 computers. "
           "How many files does each computer receive?", registry, 40)


def test_passive_actual_placement_reuses_inverse_distribution(registry):
    text = CASES["machine"].replace("4 machines", "4 bins").replace(
        "Each machine received 12 bolts.", "12 bolts were placed in each bin.")
    number(text, registry, 8)


@pytest.mark.parametrize("before,after", [
    ("are cut out", "are cuts out"),
    ("are cut out", "are cutting out"),
])
def test_passives_require_participles(registry, before, after):
    assert not solve(CASES["metal"].replace(before, after), registry).answer.committed


def test_material_transfer_verbs_do_not_pour_digital_objects(registry):
    assert not solve(CASES["server"].replace("distributes", "pours"), registry).answer.committed


def test_count_allocations_need_counted_objects_and_units_are_preserved(registry):
    assert not solve("A pump distributes 900 water equally among 3 tanks. "
                     "How much water does each tank receive?", registry).answer.committed


def test_actual_use_by_another_actor_does_not_reduce_the_stated_stock(registry):
    text = CASES["clay"].replace("It uses", "Cato uses")
    assert not solve(text, registry).answer.committed


def test_coordinated_linear_cuts_inherit_the_same_stock_reference(registry):
    number(CASES["wire"].replace("and then another", "and another"), registry, 15)


def test_mixed_linear_units_are_converted_before_computing_area(registry):
    number(CASES["metal"].replace("8 meters", "800 centimeters"), registry, 74)


def test_a_question_cannot_select_an_unstated_recipient_subgroup(registry):
    text = CASES["server"].replace("each computer", "each red computer")
    assert not solve(text, registry).answer.committed


def test_nonliving_actors_can_cut_an_explicit_material(registry):
    number("The sheet of metal is 12 meters by 8 meters. "
           "The machine cuts a 3 meter by 4 meter rectangle of metal. "
           "How much metal is left in square meters?", registry, 84)


def test_question_local_opening_dimensions_preserve_existing_cut_scope(registry):
    text = ("Fia is cutting cloth to make panels. "
            "She cuts a 5 foot by 3 foot rectangle for the bedroom. "
            "If the roll of cloth is 12 feet by 9 feet, how much cloth is left in square feet?")
    number(text, registry, 93)


def test_measurement_activity_does_not_establish_an_owned_stock(registry):
    text = CASES["clay"].replace("has 20 kilograms", "measures 20 kilograms")
    assert not solve(text, registry).answer.committed


def test_counted_purposes_do_not_multiply_an_explicit_usage_amount(registry):
    number(CASES["clay"].replace("one model", "two models"), registry, 13)


@pytest.mark.parametrize("verb", ["receives", "got"])
def test_receipt_inflections_share_the_same_allocation_role(registry, verb):
    number(CASES["machine"].replace("received", verb), registry, 8)


def test_past_transfers_preserve_the_measured_pool(registry):
    number(CASES["pump"].replace("transfers", "transferred"), registry, 300)


def test_singular_recipient_generation_has_an_agreeing_verb():
    from rulekit.generation import generate_candidate
    candidate = generate_candidate(load_project(Path("projects/curated")),
                                   rule_id="arithmetic/recipient-content-singular-each", seed=1423)
    assert candidate.target_status in {"matched", "shadowed"}
    assert all(row.slot != "owner" for row in candidate.premises)


def resource_question(case, ask):
    """Keep the measured premises fixed while varying the question grammar."""
    return CASES[case].rsplit('. ', 1)[0] + '. ' + ask


@pytest.mark.parametrize('material', ['wire', 'cloth'])
@pytest.mark.parametrize('ask, expected', [
    ('How long is the remaining {material}?', 15),
    ('How long is the {material} left?', 15),
    ('How long is the {material} remaining?', 15),
    ('How long is the {material} that remains?', 15),
    ('How long is the remaining {material} in centimeters?', 1500),
    ('How long is the {material} left in centimeters?', 1500),
    ('How long is the {material} that remains in centimeters?', 1500),
])
def test_predicative_length_queries_reuse_resource_balances(registry, material, ask, expected):
    text = resource_question('wire', ask.format(material=material)).replace('wire', material)
    number(text, registry, expected)


@pytest.mark.parametrize('case, dimension', [
    ('wire', 'length'), ('metal', 'area'), ('foam', 'volume'), ('clay', 'mass'),
])
@pytest.mark.parametrize('ask', [
    'What is the {dimension} of {material} left?',
    'What is the {dimension} of {material} remaining?',
    'What is the {dimension} of the remaining {material}?',
    'What is the {dimension} of {material} that remains?',
    'What {dimension} of {material} is left?',
    'What {dimension} of {material} is remaining?',
    'What is the remaining {dimension} of {material}?',
])
def test_remnant_material_questions_preserve_the_requested_dimension(registry, case, dimension, ask):
    number(resource_question(case, ask.format(dimension=dimension, material=case)),
           registry, EXPECTED[case])


@pytest.mark.parametrize('case, ask', [
    ('wire', 'How big is the remaining wire?'),
    ('wire', 'How long does the remaining wire last?'),
    ('wire', 'How long is the remaining wire in hours?'),
    ('wire', 'How long is the remaining wire in square meters?'),
    ('wire', 'How long is the wire?'),
    ('wire', 'How long are the remaining wire?'),
    ('wire', 'How long is the wire that remain?'),
    ('wire', 'How long is the remaining cloth?'),
    ('wire', "How long is Pat's remaining wire?"),
    ('wire', 'How long is the remaining new wire?'),
    ('wire', 'What is the size of the remaining wire?'),
    ('wire', 'What is the volume of wire left?'),
    ('metal', 'How long is the remaining metal?'),
    ('metal', 'What is the volume of metal left?'),
    ('foam', 'How long is the remaining foam?'),
    ('foam', 'What is the mass of foam left?'),
    ('foam', 'What is the volume of foam?'),
    ('foam', 'What are the volume of foam left?'),
    ('foam', 'What is the volumes of foam left?'),
    ('foam', 'What is the volume of foam that remain?'),
    ('foam', 'What is the volume of left foam?'),
    ('foam', 'What is the volume of foam left by Pat?'),
    ('foam', "What is the volume of Pat's remaining foam?"),
    ('foam', 'What is the volume of the remaining new foam?'),
    ('clay', 'What is the volume of the remaining clay?'),
])
def test_remnant_question_ambiguity_boundaries(registry, case, ask):
    assert not solve(resource_question(case, ask), registry).answer.committed


@pytest.mark.parametrize('ask', [
    'How long is the remaining wire?',
    'How long is the wire left?',
    'How long is the wire that remains?',
    'What is the length of wire left?',
])
def test_new_questions_do_not_choose_between_output_units_or_stocks(registry, ask):
    text = resource_question('wire', ask)
    mixed_units = text.replace('another 7 meters', 'another 7 centimeters')
    assert not solve(mixed_units, registry).answer.committed
    another_stock = 'A spool holds 10 meters of wire. ' + text
    assert not solve(another_stock, registry).answer.committed
    assert not solve(ask, registry).answer.committed


def test_predicative_length_can_select_an_explicit_unit_for_mixed_inputs(registry):
    text = resource_question('wire', 'How long is the remaining wire in centimeters?')
    number(text.replace('another 7 meters', 'another 7 centimeters'), registry, 2193)


def test_remaining_material_is_a_reviewed_qualifier(registry):
    assert registry.attribute_applies_to('remaining', 'wire')
    assert registry.attribute_applies_to('remaining', 'foam')
